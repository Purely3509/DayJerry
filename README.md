# Todoist Snapshot + Context Pack (tb)

A minimal CLI that exports your current Todoist tasks, projects, and labels into a local snapshot folder with human-readable summaries.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Environment Variables

- `TODOIST_API_TOKEN` (required)
- `TB_DATA_DIR` (optional, default: `./tb_data`)

You may also place these in a `.env` file if you have `python-dotenv` installed (it is included in the default dependencies).

## Usage

```bash
tb snapshot
```

Options:

- `--no-redact` — disable redaction for task content/description
- `--diff <path>` — write `DIFF.md` comparing against a prior snapshot
- `--include-project <name_or_id>` (repeatable)
- `--exclude-project <name_or_id>` (repeatable)
- `--include-label <label>` (repeatable)
- `--exclude-label <label>` (repeatable)
- `--due-window <Nd>` — include a subset `tasks_due_window.json` of tasks due within `N` days

## Outputs

Snapshots are written to:

```
./tb_data/snapshots/<YYYY-MM-DD_HHMM>/
```

Files produced:

- `meta.json`
- `tasks.json` (normalized tasks)
- `projects.json`
- `labels.json` (or `inferred_labels.json` when labels endpoint is unavailable)
- `SUMMARY.md`
- `PROJECTS.md`
- `TASKS_TOP.md`
- `local_notes.json` (starter notes per task)
- `tasks_due_window.json` (optional)
- `DIFF.md` (optional)

## Privacy & Redaction

Redaction is enabled by default and applies to task content and description only. The redactor masks emails, phone-like patterns, long numbers (8+ digits), and URLs. Project names, labels, due dates, and IDs are never redacted.

## Sample Run (using fixture data)

```text
Snapshot saved to: ./tb_data/snapshots/2024-01-01_0930
Counts - Tasks: 3, Projects: 2, Labels: 2
```

## Notes / Limitations

- Todoist REST API snapshots are active-only; completed tasks are not included.
- If the labels endpoint is unavailable, labels are inferred from tasks and a warning is written in `meta.json`.
