"""In-sandbox LLM client for containerized solvers (web / app environments).

This is the ONLY LLM surface a Docker-based task solver needs. It has zero
dependencies (pure stdlib), needs no API key, and knows nothing about which
provider serves the request — it just POSTs to the host-side proxy
(`llm_proxy`) whose URL run_task.py passes in via LLM_PROXY_URL.

Contributor usage inside a web/app solver — that's all there is to it:

    from agent_client import chat
    reply = chat(system="You are ...", user="Menu:\n...\nReturn JSON ...")

Provider selection, API keys, retries, and token accounting all live on the
host. A new web/app task never touches any of that.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

_PROXY = os.environ.get("LLM_PROXY_URL", "http://127.0.0.1:8991").rstrip("/")


def chat(system: str = "", user: str = "", *, max_tokens: int = 1024,
         temperature: float = 0.0, timeout: int = 180,
         images: list[str] | None = None, image_media_type: str = "image/png") -> str:
    """One chat turn via the host proxy. Returns assistant text.

    Provider/model/auth are resolved on the host — this call carries none of it.
    `images` are base64-encoded screenshots attached to the user turn.
    """
    payload = {"system": system, "user": user,
               "max_tokens": max_tokens, "temperature": temperature}
    if images:
        payload["images"] = list(images)
        payload["image_media_type"] = image_media_type
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_PROXY}/chat", data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # The proxy reports backend failures as JSON {"error": ...} even on 5xx —
        # surface that message instead of a bare "HTTP 500".
        try:
            data = json.loads(e.read().decode("utf-8"))
        except Exception:
            raise RuntimeError(f"LLM proxy HTTP {e.code}") from e
    if "error" in data:
        raise RuntimeError(f"LLM proxy error: {data['error']}")
    return data.get("text", "")
