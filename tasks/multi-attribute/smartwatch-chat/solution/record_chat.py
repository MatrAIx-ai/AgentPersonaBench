#!/usr/bin/env python3
"""Record chat generation and ATIF-lite trajectory after the shared harness."""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: record_chat.py OUTPUT_DIR ARM")
    output = Path(sys.argv[1])
    arm = sys.argv[2]
    transcript = json.loads((output / "transcript.json").read_text(encoding="utf-8"))
    user_record = json.loads((output / "user_turns.json").read_text(encoding="utf-8"))
    steps = [
        {
            "step_id": index,
            "source": message.get("role", "agent"),
            "message": message.get("content", ""),
            "raw": message,
        }
        for index, message in enumerate(transcript, start=1)
    ]
    generation = {
        "persona": user_record.get("persona", "persona"),
        "model": arm,
        "n_turns": len(user_record.get("turns", [])),
        "full_transcript": transcript,
        "user_turns": user_record.get("turns", []),
    }
    trajectory = {"schema_version": "ATIF-lite-v1", "steps": steps}
    (output / "generation.json").write_text(
        json.dumps(generation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "trajectory.json").write_text(
        json.dumps(trajectory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    trace_path = output / "trace.zip"
    if trace_path.is_file():
        with zipfile.ZipFile(trace_path, "a", compression=zipfile.ZIP_DEFLATED) as archive:
            existing = set(archive.namelist())
            for name in ("generation.json", "trajectory.json"):
                if name not in existing:
                    archive.write(output / name, arcname=name)


if __name__ == "__main__":
    main()
