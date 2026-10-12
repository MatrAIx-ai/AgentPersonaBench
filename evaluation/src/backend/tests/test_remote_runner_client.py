"""Tests for the general remote runner HTTP client."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import pytest

from playground.remote_runner.client import (
    RemoteRunError,
    RemoteRunnerClient,
)


class _Handler(BaseHTTPRequestHandler):
    runs: dict[str, dict] = {}

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return None

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(200, {"status": "ok"})
            return
        if self.path.startswith("/v1/runs/") and "/artifacts/" not in self.path:
            run_id = self.path.split("/")[-1]
            payload = self.runs.get(run_id)
            if payload is None:
                self._json(404, {"detail": "missing"})
                return
            self._json(200, payload)
            return
        self._json(404, {"detail": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/runs":
            self._json(404, {"detail": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        run_id = "run_test"
        self.runs[run_id] = {
            "id": run_id,
            "status": "succeeded",
            "taskType": body.get("taskType"),
        }
        self._json(200, self.runs[run_id])

    def _json(self, code: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture()
def remote_server():
    _Handler.runs = {}
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:{}".format(server.server_address[1])
    finally:
        server.shutdown()


def test_remote_runner_client_create_and_wait(remote_server: str) -> None:
    client = RemoteRunnerClient(base_url=remote_server, poll_interval=0.01)
    run = client.create_run(task_type="harbor_job", payload={"jobName": "demo"})
    assert run.id == "run_test"
    completed = client.wait_for_run(run.id)
    assert completed.status == "succeeded"


def test_remote_runner_client_requires_base_url() -> None:
    client = RemoteRunnerClient(base_url="")
    with pytest.raises(RemoteRunError):
        client.create_run(task_type="harbor_job", payload={})
