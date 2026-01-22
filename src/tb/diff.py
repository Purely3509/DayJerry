from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .models import TaskNormalized
from .storage import read_json


def _load_tasks(snapshot_path: Path) -> list[TaskNormalized]:
    tasks_data = read_json(snapshot_path / "tasks.json")
    return [TaskNormalized.model_validate(item) for item in tasks_data]


def _parse_due(task: TaskNormalized) -> date | None:
    if not task.due:
        return None
    if task.due.date:
        try:
            return date.fromisoformat(task.due.date)
        except ValueError:
            return None
    if task.due.datetime:
        try:
            return datetime.fromisoformat(task.due.datetime).date()
        except ValueError:
            return None
    return None


def diff_snapshots(current_path: Path, previous_path: Path) -> dict[str, Any]:
    current_tasks = _load_tasks(current_path)
    previous_tasks = _load_tasks(previous_path)

    current_map = {task.id: task for task in current_tasks}
    previous_map = {task.id: task for task in previous_tasks}

    added_ids = set(current_map) - set(previous_map)
    removed_ids = set(previous_map) - set(current_map)
    shared_ids = set(current_map) & set(previous_map)

    added_tasks = [current_map[task_id] for task_id in added_ids]
    removed_tasks = [previous_map[task_id] for task_id in removed_ids]

    label_changes = []
    due_changes = []
    for task_id in shared_ids:
        current = current_map[task_id]
        previous = previous_map[task_id]
        if set(current.labels) != set(previous.labels):
            label_changes.append((task_id, previous.labels, current.labels))
        if _parse_due(current) != _parse_due(previous):
            due_changes.append((task_id, previous.due, current.due))

    new_overdue = []
    today = date.today()
    for task in added_tasks:
        due = _parse_due(task)
        if due and due < today:
            new_overdue.append(task)

    counts_by_project = Counter([task.project_name or "(No Project)" for task in current_tasks])

    return {
        "counts_by_project": counts_by_project,
        "added_tasks": added_tasks,
        "removed_tasks": removed_tasks,
        "new_overdue": new_overdue,
        "label_changes": label_changes,
        "due_changes": due_changes,
    }


def build_diff_md(diff_data: dict[str, Any]) -> str:
    lines = ["# Snapshot Diff", "", "## Counts by project"]
    for project, count in diff_data["counts_by_project"].most_common():
        lines.append(f"- {project}: {count}")

    lines.extend(["", "## Newly added tasks"])
    if diff_data["added_tasks"]:
        for task in diff_data["added_tasks"]:
            lines.append(f"- {task.id}: {task.content}")
    else:
        lines.append("- None")

    lines.extend(["", "## Removed tasks"])
    if diff_data["removed_tasks"]:
        for task in diff_data["removed_tasks"]:
            lines.append(f"- {task.id}: {task.content}")
    else:
        lines.append("- None")

    lines.extend(["", "## New overdue tasks"])
    if diff_data["new_overdue"]:
        for task in diff_data["new_overdue"]:
            lines.append(f"- {task.id}: {task.content}")
    else:
        lines.append("- None")

    lines.extend(["", "## Label changes"])
    if diff_data["label_changes"]:
        for task_id, previous, current in diff_data["label_changes"]:
            lines.append(f"- {task_id}: {previous} -> {current}")
    else:
        lines.append("- None")

    lines.extend(["", "## Due date changes"])
    if diff_data["due_changes"]:
        for task_id, previous, current in diff_data["due_changes"]:
            lines.append(f"- {task_id}: {previous} -> {current}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Limitations",
            "- Completed tasks are not included in active-only snapshots, so removals may include completed items.",
        ]
    )
    return "\n".join(lines) + "\n"
