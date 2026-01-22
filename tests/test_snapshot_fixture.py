import json
from pathlib import Path

from tb.snapshot import SnapshotFilters, build_snapshot_from_data


def _load_fixture(name: str):
    path = Path(__file__).parent / "fixtures" / name
    return json.loads(path.read_text())


def test_snapshot_builder_with_fixtures():
    tasks = _load_fixture("tasks.json")
    projects = _load_fixture("projects.json")
    labels = _load_fixture("labels.json")
    filters = SnapshotFilters(
        include_projects=[],
        exclude_projects=[],
        include_labels=[],
        exclude_labels=[],
        due_window_days=None,
    )

    normalized_tasks, project_models, label_models, warnings = build_snapshot_from_data(
        tasks=tasks,
        projects=projects,
        labels=labels,
        redacted=True,
        filters=filters,
    )

    assert len(normalized_tasks) == 3
    assert {project.name for project in project_models} == {"Alpha", "Beta"}
    assert {label.name for label in label_models} == {"waiting", "finance"}
    assert warnings == []
