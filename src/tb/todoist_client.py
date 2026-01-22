from __future__ import annotations

import time
from typing import Any, Iterable

import httpx


class TodoistClient:
    def __init__(self, token: str, base_url: str = "https://api.todoist.com/rest/v2") -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.client = httpx.Client(timeout=30.0, headers=self.headers)

    def close(self) -> None:
        self.client.close()

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        url = f"{self.base_url}{path}"
        backoff = 1.0
        for attempt in range(5):
            response = self.client.request(method, url, params=params)
            if response.status_code != 429:
                return response
            retry_after = response.headers.get("Retry-After")
            wait = float(retry_after) if retry_after else backoff
            time.sleep(wait)
            backoff *= 2
        return response

    def _get_paginated(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        collected: list[dict[str, Any]] = []
        cursor: str | None = None
        params = params.copy() if params else {}
        while True:
            if cursor:
                params["cursor"] = cursor
            response = self._request("GET", path, params=params)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                collected.extend(payload)
                break
            if not isinstance(payload, dict):
                break
            items = payload.get("items") or payload.get("results") or payload.get("data")
            if isinstance(items, list):
                collected.extend(items)
            next_cursor = payload.get("next_cursor") or payload.get("cursor")
            if not next_cursor:
                break
            cursor = next_cursor
        return collected

    def get_tasks(self) -> list[dict[str, Any]]:
        return self._get_paginated("/tasks")

    def get_projects(self) -> list[dict[str, Any]]:
        return self._get_paginated("/projects")

    def get_labels(self) -> list[dict[str, Any]]:
        return self._get_paginated("/labels")
