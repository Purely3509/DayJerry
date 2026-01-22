from pathlib import Path

from tb.diff import diff_snapshots
from tb.storage import write_json


def _write_snapshot(path: Path, tasks: list[dict]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    write_json(path / "tasks.json", tasks)


def test_diff_logic(tmp_path: Path):
    previous = tmp_path / "prev"
    current = tmp_path / "curr"

    previous_tasks = [
        {
            "id": "1",
            "content": "Task one",
            "description": None,
            "project_id": "10",
            "project_name": "Alpha",
            "labels": ["waiting"],
            "priority_api": 3,
            "due": {"date": "2024-01-01", "datetime": None, "timezone": None, "string": "Jan 1"},
            "created_at": "2023-12-01",
            "url": None,
        },
        {
            "id": "2",
            "content": "Task two",
            "description": None,
            "project_id": "11",
            "project_name": "Beta",
            "labels": ["finance"],
            "priority_api": 2,
            "due": None,
            "created_at": "2023-12-01",
            "url": None,
        },
    ]

    current_tasks = [
        {
            "id": "1",
            "content": "Task one",
            "description": None,
            "project_id": "10",
            "project_name": "Alpha",
            "labels": ["waiting", "blocked"],
            "priority_api": 3,
            "due": {"date": "2024-01-02", "datetime": None, "timezone": None, "string": "Jan 2"},
            "created_at": "2023-12-01",
            "url": None,
        },
        {
            "id": "3",
            "content": "Task three",
            "description": None,
            "project_id": "11",
            "project_name": "Beta",
            "labels": [],
            "priority_api": 1,
            "due": None,
            "created_at": "2023-12-02",
            "url": None,
        },
    ]

    _write_snapshot(previous, previous_tasks)
    _write_snapshot(current, current_tasks)

    diff_data = diff_snapshots(current, previous)

    assert {task.id for task in diff_data["added_tasks"]} == {"3"}
    assert {task.id for task in diff_data["removed_tasks"]} == {"2"}
    assert diff_data["label_changes"]
    assert diff_data["due_changes"]
