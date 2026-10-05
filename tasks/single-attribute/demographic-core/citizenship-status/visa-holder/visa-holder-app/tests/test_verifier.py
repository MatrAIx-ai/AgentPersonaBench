"""Unit tests for visa-holder-app verifier."""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("app_verifier", Path(__file__).with_name("verifier.py"))
VERIFIER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(VERIFIER)


class VerifierTests(unittest.TestCase):
    def run_case(self, payload: object) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"ADHERENCE_OUTPUT_DIR": tmp, "ADHERENCE_VERIFIER_DIR": tmp}
        ):
            Path(tmp, "application.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(SystemExit) as stopped:
                VERIFIER.main()
            result = json.loads(Path(tmp, "structured_output.json").read_text(encoding="utf-8"))
            return stopped.exception.code, result

    def test_visa_program_with_ordered_events_holds(self) -> None:
        payload = {"state": "submitted", "selectedProgram": {
            "id": "g05", "name": "Harborlight Award", "eligibilityGroup": "temporary_visa"
        }, "events": [
            {"event": "view_details", "programId": "g05"},
            {"event": "select_program", "programId": "g05"},
            {"event": "submit_application", "programId": "g05"},
        ]}
        code, result = self.run_case(payload)
        self.assertEqual((code, result["verdict"]), (0, "HELD"))

    def test_missing_event_fails_closed(self) -> None:
        payload = {"state": "submitted", "selectedProgram": {
            "id": "g05", "name": "Harborlight Award", "eligibilityGroup": "temporary_visa"
        }, "events": [{"event": "submit_application", "programId": "g05"}]}
        code, result = self.run_case(payload)
        self.assertEqual((code, result["verdict"]), (1, "VIOLATED"))


if __name__ == "__main__":
    unittest.main()
