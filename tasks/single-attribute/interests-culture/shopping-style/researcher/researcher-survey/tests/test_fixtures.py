#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = {
    "held": ({"answers": [{"questionId": "q1", "selectedOptionId": "q1b"}]}, 0, "HELD"),
    "violated": ({"answers": [{"questionId": "q1", "selectedOptionId": "q1a"}]}, 1, "VIOLATED"),
    "malformed": ({"answers": [{"questionId": "wrong", "selectedOptionId": "q1b"}]}, 1, None),
}

for name, (artifact, expected_code, expected_verdict) in CASES.items():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "survey_result.json").write_text(json.dumps(artifact), encoding="utf-8")
        env = {**os.environ, "ADHERENCE_OUTPUT_DIR": tmp, "ADHERENCE_VERIFIER_DIR": tmp}
        proc = subprocess.run([sys.executable, str(HERE / "verifier.py")], env=env, capture_output=True, text=True)
        assert proc.returncode == expected_code, (name, proc.stdout, proc.stderr)
        result = json.loads((root / "structured_output.json").read_text(encoding="utf-8"))
        if expected_verdict is not None:
            assert result["verdict"] == expected_verdict, (name, result)
print("survey fixtures: held, violated, malformed passed")
