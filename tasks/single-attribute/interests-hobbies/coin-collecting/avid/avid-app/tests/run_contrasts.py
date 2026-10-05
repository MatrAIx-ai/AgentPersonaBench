#!/usr/bin/env python3
"""Persist authored verifier contrasts; no GUI or model/agent execution."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    task = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("coin_fixtures", Path(__file__).with_name("fixtures.py"))
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    cases = [("valid-" + "-".join(selected.values()), json.dumps(fixtures.fixture(selected)).encode(), selected["pack"] == "b73", True)
             for selected in fixtures.configurations()]
    cases += [("invalid-" + name, raw, False, False) for name, raw in fixtures.invalid_cases().items()]
    cases += [("missing", None, False, False)]
    summary = {"kind": "constructed_verifier_contrasts", "agent_e2e": False,
               "verifier_sha256": hashlib.sha256((task / "tests/verifier.py").read_bytes()).hexdigest(),
               "valid_configuration_count": 32, "expected_valid_held": 8, "expected_valid_violated": 24,
               "uniform_pack_chance": 0.25, "cases": [], "status": "FAIL"}
    try:
        for name, raw, held, completed in cases:
            folder = output / name
            folder.mkdir()
            if raw is not None: (folder / "hobby_reservation.json").write_bytes(raw)
            env = {"PATH": os.defpath, "ADHERENCE_OUTPUT_DIR": str(folder), "ADHERENCE_VERIFIER_DIR": str(folder / "verified")}
            process = subprocess.run([sys.executable, "-B", str(task / "tests/verifier.py")], env=env, capture_output=True, text=True, timeout=15)
            (folder / "stdout.txt").write_text(process.stdout)
            (folder / "stderr.txt").write_text(process.stderr)
            result = json.loads((folder / "verified/structured_output.json").read_text())
            assert process.returncode == (0 if held else 1) and not process.stderr, name
            assert result["reward"] == float(held) and result["completed"] == completed, name
            summary["cases"].append({"name": name, "held": held, "completed": completed, "status": "PASS"})
        summary["status"] = "PASS"
    finally:
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"PASS {len(cases)} authored contrasts; 32 valid configurations = 8 HELD + 24 VIOLATED. NOT agent E2E.")


if __name__ == "__main__":
    main()
