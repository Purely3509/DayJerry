from __future__ import annotations

import os
from pathlib import Path

import httpx
import typer
from rich.console import Console

from .snapshot import SnapshotFilters, run_snapshot, _parse_due_window

app = typer.Typer(help="Todoist Snapshot + Context Pack CLI")
console = Console()


def _load_dotenv() -> None:
    import importlib.util
    import importlib

    if importlib.util.find_spec("dotenv") is None:
        return
    dotenv = importlib.import_module("dotenv")
    dotenv.load_dotenv()


@app.command()
def snapshot(
    no_redact: bool = typer.Option(False, "--no-redact", help="Disable redaction"),
    diff: Path | None = typer.Option(None, "--diff", help="Path to previous snapshot"),
    include_project: list[str] = typer.Option(None, "--include-project", help="Include project by name or id"),
    exclude_project: list[str] = typer.Option(None, "--exclude-project", help="Exclude project by name or id"),
    include_label: list[str] = typer.Option(None, "--include-label", help="Include label"),
    exclude_label: list[str] = typer.Option(None, "--exclude-label", help="Exclude label"),
    due_window: str | None = typer.Option(None, "--due-window", help="Due window like 14d"),
) -> None:
    """Create a Todoist snapshot."""
    _load_dotenv()
    token = os.getenv("TODOIST_API_TOKEN")
    if not token:
        raise typer.BadParameter("TODOIST_API_TOKEN is required in the environment.")

    base_dir = Path(os.getenv("TB_DATA_DIR", "./tb_data"))
    try:
        due_window_days = _parse_due_window(due_window)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    filters = SnapshotFilters(
        include_projects=include_project or [],
        exclude_projects=exclude_project or [],
        include_labels=include_label or [],
        exclude_labels=exclude_label or [],
        due_window_days=due_window_days,
    )

    try:
        result = run_snapshot(
            token=token,
            base_dir=base_dir,
            redacted=not no_redact,
            filters=filters,
            diff_path=diff,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            raise typer.BadParameter(\"TODOIST_API_TOKEN is invalid or unauthorized.\") from exc
        raise typer.BadParameter(f\"Todoist API error: {exc.response.status_code} {exc.response.text}\") from exc
    except httpx.RequestError as exc:
        raise typer.BadParameter(f\"Network error while connecting to Todoist: {exc}\") from exc

    console.print(f"Snapshot saved to: {result.snapshot_path}")
    console.print(
        f"Counts - Tasks: {result.counts['tasks']}, Projects: {result.counts['projects']}, Labels: {result.counts['labels']}"
    )
    if result.warnings:
        console.print("Warnings:")
        for warning in result.warnings:
            console.print(f"- {warning}")


if __name__ == "__main__":
    app()
