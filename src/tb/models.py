from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DueInfo(BaseModel):
    date: str | None = None
    datetime: str | None = None
    timezone: str | None = None
    string: str | None = None


class TaskNormalized(BaseModel):
    id: str
    content: str
    description: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    labels: list[str] = Field(default_factory=list)
    priority_api: int
    due: DueInfo | None = None
    created_at: str | None = None
    url: str | None = None


class Project(BaseModel):
    id: str
    name: str


class Label(BaseModel):
    id: str | None = None
    name: str


class SnapshotMeta(BaseModel):
    timestamp: str
    tool_version: str
    filters: dict[str, Any]
    redacted: bool
    counts: dict[str, int]
    warnings: list[str] = Field(default_factory=list)
