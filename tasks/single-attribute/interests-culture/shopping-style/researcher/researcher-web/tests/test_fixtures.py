#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMPAT = {"name": "ArborLink ProDock 12", "monitors": "Dual external monitors supported", "pd": "100W max passthrough", "notes": "Validated for this laptop profile with dual monitors"}
CASES = {
    "held": ({"decision": "buy", "selectedProductId": "d02", "selectedCompatibility": COMPAT, "events": [{"event": "view_compatibility", "productId": "d02"}, {"event": "purchase", "productId": "d02"}]}, 0, "HELD"),
    "violated": ({"decision": "buy", "selectedProductId": "d01", "selectedCompatibility": {"name": "NorthPort MiniDock 8"}, "events": [{"event": "view_compatibility", "productId": "d01"}, {"event": "purchase", "productId": "d01"}]}, 1, "VIOLATED"),
    "malformed": ({"decision": "buy", "selectedProductId": "bogus", "events": []}, 1, None),
}
for name, (artifact, expected_code, expected_verdict) in CASES.items():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); (root / "anchor").mkdir()
        (root / "anchor" / "purchase.json").write_text(json.dumps(artifact), encoding="utf-8")
        env = {**os.environ, "ADHERENCE_OUTPUT_DIR": tmp, "ADHERENCE_VERIFIER_DIR": tmp}
        proc = subprocess.run([sys.executable, str(HERE / "verifier.py")], env=env, capture_output=True, text=True)
        assert proc.returncode == expected_code, (name, proc.stdout, proc.stderr)
        result = json.loads((root / "structured_output.json").read_text(encoding="utf-8"))
        if expected_verdict is not None: assert result["verdict"] == expected_verdict, (name, result)
print("web fixtures: held, violated, malformed passed")
