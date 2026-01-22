from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable

from .models import TaskNormalized

VAGUE_PREFIXES = [
    "plan",
    "figure out",
    "deal with",
    "work on",
    "organize",
    "look into",
    "think about",
]
BLOCKED_PHRASES = [
    "waiting for",
    "follow up",
    "blocked",
    "stuck",
    "pending",
]
BLOCKED_LABELS = {"waiting", "blocked", "waiting-for", "follow-up"}


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


def is_vague_task(content: str) -> bool:
    normalized = content.strip().lower()
    if not normalized:
        return False
    word_count = len(normalized.split())
    if word_count > 6:
        return False
    return any(normalized.startswith(prefix) for prefix in VAGUE_PREFIXES)


def is_blocked_task(content: str, labels: Iterable[str]) -> bool:
    normalized = content.strip().lower()
    if any(phrase in normalized for phrase in BLOCKED_PHRASES):
        return True
    normalized_labels = {label.strip().lower() for label in labels}
    return bool(normalized_labels & BLOCKED_LABELS)


def due_buckets(tasks: Iterable[TaskNormalized]) -> dict[str, int]:
    today = date.today()
    buckets = {
        "overdue": 0,
        "due_today": 0,
        "due_next_7": 0,
        "due_next_30": 0,
        "no_due": 0,
    }
    for task in tasks:
        due = _parse_due(task)
        if not due:
            buckets["no_due"] += 1
            continue
        if due < today:
            buckets["overdue"] += 1
        elif due == today:
            buckets["due_today"] += 1
        elif due <= today + timedelta(days=7):
            buckets["due_next_7"] += 1
        elif due <= today + timedelta(days=30):
            buckets["due_next_30"] += 1
        else:
            buckets["no_due"] += 1
    return buckets


def tasks_by_project(tasks: Iterable[TaskNormalized]) -> Counter:
    counter: Counter[str] = Counter()
    for task in tasks:
        name = task.project_name or "(No Project)"
        counter[name] += 1
    return counter


def tasks_by_label(tasks: Iterable[TaskNormalized]) -> Counter:
    counter: Counter[str] = Counter()
    for task in tasks:
        for label in task.labels:
            counter[label] += 1
    return counter


def tasks_top_urgency(tasks: Iterable[TaskNormalized], limit: int = 100) -> list[TaskNormalized]:
    today = date.today()

    def sort_key(task: TaskNormalized) -> tuple[int, date]:
        due = _parse_due(task)
        if not due:
            return (2, date.max)
        if due < today:
            return (0, due)
        if due <= today + timedelta(days=7):
            return (1, due)
        return (1, due)

    sorted_tasks = sorted(tasks, key=sort_key)
    return sorted_tasks[:limit]


def projects_with_no_due(tasks: Iterable[TaskNormalized]) -> list[tuple[str, int, int]]:
    counts = defaultdict(lambda: {"no_due": 0, "total": 0})
    for task in tasks:
        project = task.project_name or "(No Project)"
        counts[project]["total"] += 1
        if not _parse_due(task):
            counts[project]["no_due"] += 1
    result = []
    for project, data in counts.items():
        no_due = data["no_due"]
        total = data["total"]
        if total and no_due >= 5 and no_due / total >= 0.5:
            result.append((project, no_due, total))
    return sorted(result, key=lambda item: item[1], reverse=True)
