"""A verifier that could not score a trial must not be read as a model failure.

Chat verifiers that catch a judge exception, an unparseable judge reply or a
configuration problem write reward 0 with `verdict: "ERROR"` (or a
`judge_error` / `configuration_error` status, or an `error_stage`) and no
top-level `error` key. run_task used to treat that as a scored 0, so a dead
judge or a truncated judge reply lowered the arm's adherence.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_task = load_module("run_task", REPO / "evaluation" / "run_task.py")
report_suite = load_module("report_suite", REPO / "evaluation" / "report_suite.py")


class VerifierReportedErrorTest(unittest.TestCase):
    def test_scored_results_are_not_errors(self) -> None:
        for findings in (
            {"reward": 0.0, "verdict": "VIOLATED", "passed": False},
            {"reward": 1.0, "verdict": "HELD", "passed": True},
            {"reward": 1, "points": 1, "max_points": 3,
             "checks": [{"verdict": "HELD"}, {"verdict": "VIOLATED"}, {"verdict": "NOT_ADDRESSED"}]},
        ):
            self.assertIsNone(run_task._verifier_reported_error(findings), findings)

    def test_error_shapes_verifiers_write_are_errors(self) -> None:
        for findings in (
            {"reward": 0.0, "verdict": "ERROR", "passed": False, "detail": "judge failed"},
            {"reward": 0.0, "status": "judge_error", "verdict": "ERROR"},
            {"reward": 0.0, "status": "configuration_error"},
            {"reward": 0.0, "verdict": "ERROR", "error_stage": "judge_call"},
            {"reward": 1, "points": 1, "max_points": 2,
             "checks": [{"dimension_id": "a", "verdict": "HELD"},
                        {"dimension_id": "b", "verdict": "ERROR"}]},
            {"stage": "verify", "error": "verifier wrote no structured_output.json"},
        ):
            self.assertIsNotNone(run_task._verifier_reported_error(findings), findings)


class ReportMaxPointsTest(unittest.TestCase):
    def test_missing_envelope_takes_denominator_from_score(self) -> None:
        """Without the envelope the report used to divide a 3-point reward by 1."""
        with tempfile.TemporaryDirectory() as tmp:
            suite = Path(tmp)
            (suite / "plan.json").write_text(json.dumps({"tasks": []}))
            event = {"event": "completed", "run_key": "k", "task": "t", "surface": "chat",
                     "model": "m", "seed": 0, "status": "pass", "score": "3/3", "reward": 3.0,
                     "envelope": "does/not/exist/envelope.json"}
            (suite / "events.jsonl").write_text(json.dumps(event) + "\n")
            _, rows = report_suite.build_rows(suite)
        self.assertEqual(rows[0]["max_points"], 3.0)
        self.assertEqual(rows[0]["normalized_reward"], 1.0)

    def test_parse_score(self) -> None:
        self.assertEqual(report_suite.parse_score("2/3"), (2.0, 3.0))
        self.assertIsNone(report_suite.parse_score("0/0"))
        self.assertIsNone(report_suite.parse_score(None))


if __name__ == "__main__":
    unittest.main()
