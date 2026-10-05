"""Host-side LLM proxy — lets containerized solvers reach the provider layer.

Docker-based solvers (web / app environments) run inside a sandbox that has no
provider SDK and no API key — by design, a task contributor should never touch
LLM plumbing. This proxy runs on the HOST (started by run_task.py), holds the
one `llm_client` provider layer, and exposes a tiny HTTP surface the container
calls via `agent_client`:

    POST /chat   {"system": "...", "user": "...", "max_tokens": N,
                  "images": ["<base64 png/jpeg>", ...]}   (images optional)
              -> {"text": "...", "usage": {...}}
    GET  /calls  -> {"calls": [...], "summary": {...}}   (per-run token log)

The container never learns which provider served the request. Provider choice,
auth, retries all live in llm_client on the host. Bind to loopback; the proxy is
per-run and short-lived (run_task starts it before solve, stops it after).
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from llm_client import chat, reset_call_log, get_call_log, call_log_summary

# Model/provider come from the arm config via env (run_task exports LLM_MODEL);
# the proxy just forwards to chat(), which resolves provider from LLM_PROVIDER.
import os

_MODEL = os.environ.get("LLM_MODEL", "claude-opus-4-8")


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence default stderr access log
        pass

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/calls":
            self._send(200, {"calls": get_call_log(), "summary": call_log_summary()})
        elif self.path == "/health":
            self._send(200, {"ok": True, "model": _MODEL})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/chat":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length) or b"{}")
            messages = req.get("messages")
            if not messages:
                # convenience {system,user} shape for the container client
                messages = []
                if req.get("system"):
                    messages.append({"role": "system", "content": req["system"]})
                user = req.get("user", "")
                images = req.get("images") or []
                if images:  # screenshots ride along with the user turn
                    media = req.get("image_media_type", "image/png")
                    user = [{"type": "text", "text": user}] + [
                        {"type": "image_url", "image_url": {"url": f"data:{media};base64,{b64}"}}
                        for b64 in images]
                messages.append({"role": "user", "content": user})
            text = chat(
                messages,
                model=req.get("model", _MODEL),
                max_tokens=int(req.get("max_tokens", 1024)),
                temperature=float(req.get("temperature", 0.0)),
            )
            # last recorded call is this one — surface its usage to the caller
            log = get_call_log()
            self._send(200, {"text": text, "usage": (log[-1] if log else {})})
        except Exception as e:  # noqa: BLE001 — report as JSON, don't crash the proxy
            self._send(500, {"error": str(e)})


class LLMProxy:
    """A loopback HTTP proxy in a background thread. `url` is what the container
    calls (via --network=host). Resets the call log on start so each run's token
    accounting is clean; `summary()` returns the aggregate after solve."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        reset_call_log()
        self._server = ThreadingHTTPServer((host, port), _Handler)
        self.host, self.port = self._server.server_address
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> "LLMProxy":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def summary(self) -> dict:
        return call_log_summary()

    def calls(self) -> list:
        return get_call_log()
