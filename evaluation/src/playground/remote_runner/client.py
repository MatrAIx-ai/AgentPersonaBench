"""HTTP client for a general remote runner service.

Contract (vendor-neutral):

* ``POST /v1/runs`` with ``{"taskType": ..., "payload": ...}``
* ``GET /v1/runs/{id}``
* ``GET /v1/runs/{id}/artifacts/{name}``
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class RemoteRunError(RuntimeError):
    """Raised when a remote run cannot be created or completed."""


@dataclass(frozen=True)
class RemoteRun:
    """Minimal view of a remote run."""

    id: str
    status: str
    task_type: str | None = None
    detail: dict[str, Any] | None = None


class RemoteRunnerClient:
    """HTTP client for a remote runner API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
        poll_interval: float = 2.0,
        max_wait_seconds: float = 1800.0,
    ) -> None:
        self.base_url = (
            base_url or os.environ.get("REMOTE_RUNNER_API_URL", "").strip()
        ).rstrip("/")
        self.api_key = (
            api_key
            if api_key is not None
            else os.environ.get("REMOTE_RUNNER_API_KEY")
        )
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_wait_seconds = max_wait_seconds

    def create_run(self, *, task_type: str, payload: dict[str, Any]) -> RemoteRun:
        if not self.base_url:
            raise RemoteRunError(
                "REMOTE_RUNNER_API_URL is not configured for remote execution"
            )
        body = self._request(
            "POST",
            "/v1/runs",
            body={"taskType": task_type, "payload": payload},
        )
        if not isinstance(body, dict) or not body.get("id"):
            raise RemoteRunError("remote runner returned an invalid create response")
        return RemoteRun(
            id=str(body["id"]),
            status=str(body.get("status") or "queued"),
            task_type=task_type,
            detail=body,
        )

    def get_run(self, run_id: str) -> RemoteRun:
        body = self._request("GET", "/v1/runs/{}".format(run_id))
        if not isinstance(body, dict) or not body.get("id"):
            raise RemoteRunError("remote runner returned an invalid run response")
        return RemoteRun(
            id=str(body["id"]),
            status=str(body.get("status") or "unknown"),
            task_type=str(body.get("taskType") or "") or None,
            detail=body,
        )

    def wait_for_run(self, run_id: str) -> RemoteRun:
        deadline = time.monotonic() + self.max_wait_seconds
        while True:
            run = self.get_run(run_id)
            if run.status in {"succeeded", "failed"}:
                if run.status == "failed":
                    error = ""
                    if isinstance(run.detail, dict):
                        error = str(run.detail.get("error") or "")
                    raise RemoteRunError(
                        error or "remote run {} failed".format(run_id)
                    )
                return run
            if time.monotonic() >= deadline:
                raise RemoteRunError(
                    "timed out waiting for remote run {} after {}s".format(
                        run_id,
                        self.max_wait_seconds,
                    )
                )
            time.sleep(self.poll_interval)

    def get_artifact(self, run_id: str, name: str) -> Any:
        return self._request("GET", "/v1/runs/{}/artifacts/{}".format(run_id, name))

    def health(self) -> dict[str, Any]:
        if not self.base_url:
            raise RemoteRunError("REMOTE_RUNNER_API_URL is not configured")
        body = self._request("GET", "/health")
        if not isinstance(body, dict):
            raise RemoteRunError("remote runner health returned invalid JSON")
        return body

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> Any:
        url = "{}{}".format(self.base_url, path)
        data = None
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer {}".format(self.api_key)
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RemoteRunError(
                "remote runner {} {} failed ({}): {}".format(
                    method,
                    path,
                    exc.code,
                    detail[:1000],
                )
            ) from exc
        except urllib.error.URLError as exc:
            raise RemoteRunError(
                "remote runner {} {} failed: {}".format(method, path, exc.reason)
            ) from exc
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RemoteRunError(
                "remote runner {} {} returned non-JSON body".format(method, path)
            ) from exc
