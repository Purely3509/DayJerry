from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def snapshot_dir(base_dir: Path, timestamp: str) -> Path:
    return base_dir / "snapshots" / timestamp
