#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOOD = {"id": "w01", "name": "Aster HomeWash 4.2", "specs": {"width_in": 26.8, "depth_in": 31.7, "height_in": 38.2, "doorway_min_in": 28.5, "voltage": 120}}
BAD = {"id": "w02", "name": "Granite TurboWash 5.0", "specs": {"width_in": 27.9, "depth_in": 33.5, "height_in": 39.0, "doorway_min_in": 30.0, "voltage": 240}}
CASES = {
    "held": ({"action": "purchase", "selectedModelId": "w01", "selectedModel": GOOD, "events": [{"event": "view_spec", "modelId": "w01"}, {"event": "purchase", "modelId": "w01"}]}, 0, "HELD"),
    "violated": ({"action": "purchase", "selectedModelId": "w02", "selectedModel": BAD, "events": [{"event": "view_spec", "modelId": "w02"}, {"event": "purchase", "modelId": "w02"}]}, 1, "VIOLATED"),
    "malformed": ({"action": "purchase", "selectedModelId": "w01", "events": []}, 1, None),
}
for name, (artifact, expected_code, expected_verdict) in CASES.items():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); (root / "order.json").write_text(json.dumps(artifact), encoding="utf-8")
        env = {**os.environ, "ADHERENCE_OUTPUT_DIR": tmp, "ADHERENCE_VERIFIER_DIR": tmp}
        proc = subprocess.run([sys.executable, str(HERE / "verifier.py")], env=env, capture_output=True, text=True)
        assert proc.returncode == expected_code, (name, proc.stdout, proc.stderr)
        result = json.loads((root / "structured_output.json").read_text(encoding="utf-8"))
        if expected_verdict is not None: assert result["verdict"] == expected_verdict, (name, result)
print("app fixtures: held, violated, malformed passed")
