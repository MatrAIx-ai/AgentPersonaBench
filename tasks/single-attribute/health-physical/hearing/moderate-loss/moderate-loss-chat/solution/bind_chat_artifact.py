#!/usr/bin/env python3
"""Bind the shared chat artifact to this task persona and refresh its trace."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import zipfile


PERSONA_ID_RE = re.compile(rb"(?m)^persona_id:\s*['\"]?([^'\"\r\n]+)")
REQUIRED_TRACE_MEMBERS = {"transcript.json", "user_turns.json"}


def bind_chat_artifact(persona_path: Path, output_dir: Path) -> dict[str, object]:
    """Normalize ``user_turns.json`` and atomically refresh ``trace.zip``.

    The shared chat harness writes ``{persona, turns}`` and immediately archives
    it.  This task adds immutable persona provenance, so the archive must be
    refreshed after normalization.  Existing trace members are preserved byte
    for byte; only ``user_turns.json`` is replaced with the normalized bytes.
    """
    persona_path = Path(persona_path)
    output_dir = Path(output_dir)
    artifact_path = output_dir / "user_turns.json"
    trace_path = output_dir / "trace.zip"

    persona_bytes = persona_path.read_bytes()
    match = PERSONA_ID_RE.search(persona_bytes)
    if match is None:
        raise ValueError("persona.yaml has no parseable persona_id")
    persona_id = match.group(1).decode("utf-8").strip()

    value = json.loads(artifact_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {"persona", "turns"}:
        raise ValueError("shared chat artifact has an invalid shape")
    if value["persona"] != persona_id:
        raise ValueError("shared chat artifact persona does not match persona.yaml")
    turns = value["turns"]
    if not isinstance(turns, list) or not turns:
        raise ValueError("shared chat artifact turns must be a non-empty list")
    if not all(isinstance(turn, str) and turn.strip() for turn in turns):
        raise ValueError("shared chat artifact turns must be non-empty strings")

    bound: dict[str, object] = {
        "schemaVersion": 2,
        "personaId": persona_id,
        "personaHash": hashlib.sha256(persona_bytes).hexdigest(),
        "turns": turns,
    }
    bound_bytes = json.dumps(bound, ensure_ascii=False, indent=2).encode("utf-8")

    with zipfile.ZipFile(trace_path, "r") as source:
        names = source.namelist()
        if len(names) != len(set(names)):
            raise ValueError("trace.zip contains duplicate member names")
        missing = REQUIRED_TRACE_MEMBERS.difference(names)
        if missing:
            raise ValueError(
                "trace.zip is missing required members: " + ", ".join(sorted(missing))
            )
        members = [
            (name, bound_bytes if name == "user_turns.json" else source.read(name))
            for name in names
        ]
        comment = source.comment

    artifact_tmp = output_dir / ".user_turns.json.tmp"
    trace_tmp = output_dir / ".trace.zip.tmp"
    try:
        artifact_tmp.write_bytes(bound_bytes)
        with zipfile.ZipFile(
            trace_tmp, "w", compression=zipfile.ZIP_DEFLATED
        ) as destination:
            destination.comment = comment
            for name, data in members:
                destination.writestr(name, data)
        os.replace(artifact_tmp, artifact_path)
        os.replace(trace_tmp, trace_path)
    finally:
        artifact_tmp.unlink(missing_ok=True)
        trace_tmp.unlink(missing_ok=True)

    return bound


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: bind_chat_artifact.py PERSONA_YAML OUTPUT_DIR")
    bind_chat_artifact(Path(sys.argv[1]), Path(sys.argv[2]))


if __name__ == "__main__":
    main()
