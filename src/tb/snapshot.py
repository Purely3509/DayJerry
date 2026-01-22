from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import DueInfo, Label, Project, SnapshotMeta, TaskNormalized
from .redact import redact_text
from .storage import ensure_dir, snapshot_dir, write_json
from .summarize import (
    due_buckets,
    is_blocked_task,
    is_vague_task,
    projects_with_no_due,
    tasks_by_label,
    tasks_by_project,
    tasks_top_urgency,
)
from .todoist_client import TodoistClient


@dataclass
class SnapshotFilters:
    include_projects: list[str]
    exclude_projects: list[str]
    include_labels: list[str]
    exclude_labels: list[str]
    due_window_days: int | None


@dataclass
class SnapshotResult:
    snapshot_path: Path
    counts: dict[str, int]
    warnings: list[str]


def _normalize_task(raw: dict[str, Any], project_lookup: dict[str, str]) -> TaskNormalized:
    due = raw.get("due") or {}
    due_info = None
    if due:
        due_info = DueInfo(
            date=due.get("date"),
            datetime=due.get("datetime"),
            timezone=due.get("timezone"),
            string=due.get("string"),
        )
    project_id = raw.get("project_id")
    return TaskNormalized(
        id=str(raw.get("id")),
        content=raw.get("content") or "",
        description=raw.get("description"),
        project_id=str(project_id) if project_id else None,
        project_name=project_lookup.get(str(project_id)) if project_id else None,
        labels=raw.get("labels") or [],
        priority_api=int(raw.get("priority", 1)),
        due=due_info,
        created_at=raw.get("created_at"),
        url=raw.get("url"),
    )


def _apply_redaction(task: TaskNormalized) -> TaskNormalized:
    task.content = redact_text(task.content)
    if task.description:
        task.description = redact_text(task.description)
    return task


def _matches_project(task: TaskNormalized, names_or_ids: list[str]) -> bool:
    if not names_or_ids:
        return True
    normalized = {item.lower() for item in names_or_ids}
    return (task.project_id and task.project_id in normalized) or (
        task.project_name and task.project_name.lower() in normalized
    )


def _matches_labels(task: TaskNormalized, labels: list[str]) -> bool:
    if not labels:
        return True
    normalized = {label.lower() for label in labels}
    return any(label.lower() in normalized for label in task.labels)


def _parse_due_window(value: str | None) -> int | None:
    if not value:
        return None
    if not value.endswith("d"):
        raise ValueError("Due window must be in the form Nd, e.g. 14d")
    return int(value[:-1])


def _within_due_window(task: TaskNormalized, days: int) -> bool:
    if not task.due:
        return False
    target_date: date | None = None
    if task.due.date:
        try:
            target_date = date.fromisoformat(task.due.date)
        except ValueError:
            return False
    elif task.due.datetime:
        try:
            target_date = datetime.fromisoformat(task.due.datetime).date()
        except ValueError:
            return False
    if not target_date:
        return False
    return target_date <= date.today() + timedelta(days=days)


def build_snapshot_from_data(
    tasks: list[dict[str, Any]],
    projects: list[dict[str, Any]],
    labels: list[dict[str, Any]] | None,
    redacted: bool,
    filters: SnapshotFilters,
) -> tuple[list[TaskNormalized], list[Project], list[Label], list[str]]:
    warnings: list[str] = []
    project_models = [Project(id=str(item["id"]), name=item["name"]) for item in projects]
    project_lookup = {project.id: project.name for project in project_models}

    normalized_tasks = [_normalize_task(task, project_lookup) for task in tasks]

    if filters.include_projects:
        normalized_tasks = [
            task for task in normalized_tasks if _matches_project(task, filters.include_projects)
        ]
    if filters.exclude_projects:
        normalized_tasks = [
            task for task in normalized_tasks if not _matches_project(task, filters.exclude_projects)
        ]
    if filters.include_labels:
        normalized_tasks = [
            task for task in normalized_tasks if _matches_labels(task, filters.include_labels)
        ]
    if filters.exclude_labels:
        normalized_tasks = [
            task for task in normalized_tasks if not _matches_labels(task, filters.exclude_labels)
        ]

    if redacted:
        normalized_tasks = [_apply_redaction(task) for task in normalized_tasks]

    if labels is None:
        inferred = sorted({label for task in normalized_tasks for label in task.labels})
        label_models = [Label(name=name) for name in inferred]
        warnings.append("Labels endpoint unavailable; inferred labels from tasks.")
    else:
        label_models = [Label(id=str(item.get("id")) if item.get("id") else None, name=item["name"]) for item in labels]

    return normalized_tasks, project_models, label_models, warnings


def run_snapshot(
    token: str,
    base_dir: Path,
    redacted: bool,
    filters: SnapshotFilters,
    diff_path: Path | None = None,
) -> SnapshotResult:
    client = TodoistClient(token)
    try:
        tasks = client.get_tasks()
        projects = client.get_projects()
        labels = None
        label_filename = "labels.json"
        label_warning: str | None = None
        try:
            labels = client.get_labels()
        except Exception as exc:  # noqa: BLE001 - surface as warning if labels unavailable
            label_warning = f"Labels endpoint unavailable: {exc}"
            labels = None
            label_filename = "inferred_labels.json"
        normalized_tasks, project_models, label_models, data_warnings = build_snapshot_from_data(
            tasks=tasks,
            projects=projects,
            labels=labels,
            redacted=redacted,
            filters=filters,
        )
        warnings = data_warnings
        if label_warning:
            warnings.append(label_warning)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        result = write_snapshot(
            base_dir=base_dir,
            timestamp=timestamp,
            tasks=normalized_tasks,
            projects=project_models,
            labels=label_models,
            redacted=redacted,
            filters=filters,
            warnings=warnings,
            label_filename=label_filename,
            due_window_days=filters.due_window_days,
        )
        if diff_path:
            from .diff import build_diff_md, diff_snapshots

            diff_data = diff_snapshots(result.snapshot_path, diff_path)
            diff_md = build_diff_md(diff_data)
            (result.snapshot_path / "DIFF.md").write_text(diff_md)
        return result
    finally:
        client.close()


def write_snapshot(
    base_dir: Path,
    timestamp: str,
    tasks: list[TaskNormalized],
    projects: list[Project],
    labels: list[Label],
    redacted: bool,
    filters: SnapshotFilters,
    warnings: list[str],
    label_filename: str,
    due_window_days: int | None,
) -> SnapshotResult:
    snap_dir = ensure_dir(snapshot_dir(base_dir, timestamp))

    counts = {
        "tasks": len(tasks),
        "projects": len(projects),
        "labels": len(labels),
    }

    meta = SnapshotMeta(
        timestamp=timestamp,
        tool_version="0.1.0",
        filters={
            "include_projects": filters.include_projects,
            "exclude_projects": filters.exclude_projects,
            "include_labels": filters.include_labels,
            "exclude_labels": filters.exclude_labels,
            "due_window_days": filters.due_window_days,
        },
        redacted=redacted,
        counts=counts,
        warnings=warnings,
    )

    write_json(snap_dir / "meta.json", meta.model_dump())
    write_json(snap_dir / "tasks.json", [task.model_dump() for task in tasks])
    write_json(snap_dir / "projects.json", [project.model_dump() for project in projects])
    write_json(snap_dir / label_filename, [label.model_dump() for label in labels])
    write_json(
        snap_dir / "local_notes.json",
        {task.id: {"notes": "", "assumptions": "", "tags": [], "last_updated": ""} for task in tasks},
    )

    summary_md = build_summary_md(tasks, projects)
    (snap_dir / "SUMMARY.md").write_text(summary_md)

    projects_md = build_projects_md(tasks, projects)
    (snap_dir / "PROJECTS.md").write_text(projects_md)

    tasks_top_md = build_tasks_top_md(tasks)
    (snap_dir / "TASKS_TOP.md").write_text(tasks_top_md)

    if due_window_days is not None:
        window_tasks = [task.model_dump() for task in tasks if _within_due_window(task, due_window_days)]
        write_json(snap_dir / "tasks_due_window.json", window_tasks)

    return SnapshotResult(snapshot_path=snap_dir, counts=counts, warnings=warnings)


def build_summary_md(tasks: list[TaskNormalized], projects: list[Project]) -> str:
    counts_by_project = tasks_by_project(tasks)
    top_projects = counts_by_project.most_common(20)
    due_counts = due_buckets(tasks)
    labels_counter = tasks_by_label(tasks)
    top_labels = labels_counter.most_common(30)
    vague = [task for task in tasks if is_vague_task(task.content)]
    blocked = [task for task in tasks if is_blocked_task(task.content, task.labels)]
    planning_debt = projects_with_no_due(tasks)

    lines = [
        "# Summary",
        "",
        "## Overview counts",
        f"- Tasks: {len(tasks)}",
        f"- Projects: {len(projects)}",
        "",
        "## Tasks by project (top 20 by count)",
    ]
    lines.extend([f"- {name}: {count}" for name, count in top_projects] or ["- None"])
    lines.extend(
        [
            "",
            "## Due distribution",
            f"- Overdue: {due_counts['overdue']}",
            f"- Due today: {due_counts['due_today']}",
            f"- Due next 7: {due_counts['due_next_7']}",
            f"- Due next 30: {due_counts['due_next_30']}",
            f"- No due: {due_counts['no_due']}",
            "",
            "## Top labels (top 30)",
        ]
    )
    lines.extend([f"- {name}: {count}" for name, count in top_labels] or ["- None"])

    lines.extend(["", "## Vague tasks"])
    if vague:
        lines.extend([f"- {task.id}: {task.content}" for task in vague])
    else:
        lines.append("- None")

    lines.extend(["", "## Waiting/Blocked candidates"])
    if blocked:
        lines.extend([f"- {task.id}: {task.content}" for task in blocked])
    else:
        lines.append("- None")

    lines.extend(["", "## Projects with many no-due tasks"])
    if planning_debt:
        lines.extend([f"- {name}: {no_due}/{total} no-due" for name, no_due, total in planning_debt])
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def build_projects_md(tasks: list[TaskNormalized], projects: list[Project]) -> str:
    by_project: dict[str, list[TaskNormalized]] = {}
    for project in projects:
        by_project[project.name] = []
    for task in tasks:
        name = task.project_name or "(No Project)"
        by_project.setdefault(name, []).append(task)

    lines = ["# Projects"]
    today = date.today()
    for name, project_tasks in sorted(by_project.items()):
        overdue = 0
        next_due: date | None = None
        labels_counter = Counter([label for task in project_tasks for label in task.labels])
        for task in project_tasks:
            due = None
            if task.due and task.due.date:
                try:
                    due = date.fromisoformat(task.due.date)
                except ValueError:
                    due = None
            elif task.due and task.due.datetime:
                try:
                    due = datetime.fromisoformat(task.due.datetime).date()
                except ValueError:
                    due = None
            if due:
                if due < today:
                    overdue += 1
                if not next_due or due < next_due:
                    next_due = due
        top_labels = ", ".join([label for label, _ in labels_counter.most_common(5)]) or "None"
        lines.extend(
            [
                "",
                f"## {name}",
                f"- Task count: {len(project_tasks)}",
                f"- Overdue count: {overdue}",
                f"- Next due date: {next_due.isoformat() if next_due else 'None'}",
                f"- Top labels: {top_labels}",
            ]
        )
    return "\n".join(lines) + "\n"


def build_tasks_top_md(tasks: list[TaskNormalized]) -> str:
    top_tasks = tasks_top_urgency(tasks)
    lines = ["# Top Tasks (by urgency)", "", "| ID | Project | Due | Labels | Priority | Content |", "| --- | --- | --- | --- | --- | --- |"]
    for task in top_tasks:
        due_value = ""
        if task.due:
            due_value = task.due.datetime or task.due.date or ""
        labels = ", ".join(task.labels)
        lines.append(
            f"| {task.id} | {task.project_name or '(No Project)'} | {due_value} | {labels} | {task.priority_api} | {task.content} |"
        )
    return "\n".join(lines) + "\n"
