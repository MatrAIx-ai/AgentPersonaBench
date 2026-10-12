"""Backward-compatible entry point for the host Codex task runner."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from evaluation.run_task_codex import main

if __name__ == "__main__":
    raise SystemExit(main())
