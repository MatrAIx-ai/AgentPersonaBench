import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


VERIFIER = Path(__file__).with_name("verifier.py")


class WebVerifierTests(unittest.TestCase):
    def run_case(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            if payload is not None:
                target = root / "anchor"
                target.mkdir()
                (target / "reviews.json").write_text(
                    payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8"
                )
            env = {**os.environ, "ADHERENCE_OUTPUT_DIR": directory, "ADHERENCE_VERIFIER_DIR": directory}
            result = subprocess.run([sys.executable, str(VERIFIER)], env=env, capture_output=True, text=True)
            record = json.loads((root / "structured_output.json").read_text(encoding="utf-8"))
            return result.returncode, record

    @staticmethod
    def reviews(proposals):
        return {"reviews": [{"ticketId": f"t{i}", "proposalId": proposal} for i, proposal in enumerate(proposals, 1)]}

    def test_held_with_three_large_workflows(self):
        code, record = self.run_case(self.reviews(["t1p2", "t2p4", "t3p1", "t4p1"]))
        self.assertEqual(code, 0)
        self.assertEqual(record["verdict"], "HELD")

    def test_violated_with_two_large_workflows(self):
        code, record = self.run_case(self.reviews(["t1p2", "t2p4", "t3p2", "t4p1"]))
        self.assertEqual(code, 1)
        self.assertEqual(record["verdict"], "VIOLATED")

    def test_forged_line_count_is_ignored(self):
        payload = self.reviews(["t1p1", "t2p2", "t3p2", "t4p1"])
        for review in payload["reviews"]:
            review["primaryLines"] = 999
        code, record = self.run_case(payload)
        self.assertEqual(code, 1)
        self.assertEqual(record["large_workflow_count"], 0)

    def test_partial_malformed_and_cross_ticket_fail_closed(self):
        code, record = self.run_case({"reviews": [{"ticketId": "t1", "proposalId": "t1p2"}]})
        self.assertEqual(code, 1)
        self.assertEqual(record["reward"], 0.0)
        code, record = self.run_case("no json")
        self.assertEqual(code, 1)
        cross = self.reviews(["t2p4", "t2p4", "t3p1", "t4p3"])
        code, record = self.run_case(cross)
        self.assertEqual(code, 1)
        self.assertEqual(record["reward"], 0.0)


if __name__ == "__main__":
    unittest.main()
