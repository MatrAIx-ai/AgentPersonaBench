import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("verifier.py")
SPEC = importlib.util.spec_from_file_location("volunteer_app_verifier", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CHECKS = [{"dimension_id": dim, "value": value} for dim, value in (
    ("skill_cooking", "Advanced"), ("skill_baking", "None"),
    ("skill_photography", "Beginner"))]
IDS = ["f1", "f2", "f3", "f4", "b1", "b2", "b3", "b4", "p1", "p2", "p3", "p4"]


def artifact(food="f4", baking="b4", media="p2"):
    selected = [{"room": "food", "id": food}, {"room": "baking", "id": baking},
                {"room": "media", "id": media}]
    events = [{"type": "view_role", "id": oid} for oid in IDS]
    events += [{"type": "select_role", "room": item["room"], "id": item["id"]}
               for item in selected]
    events.append({"type": "submit_assignments"})
    return {"submitted": True, "viewed": IDS, "selected": selected, "events": events}


class VerifierTests(unittest.TestCase):
    def test_all_held(self):
        self.assertTrue(all(item["passed"] for item in MODULE.evaluate(artifact(), CHECKS)))

    def test_checks_are_independent(self):
        results = MODULE.evaluate(artifact(food="f2"), CHECKS)
        self.assertEqual([item["passed"] for item in results], [False, True, True])

    def test_forged_readiness_and_unknown_id_fail(self):
        forged = artifact()
        forged["selected"][0]["readiness"] = "Advanced"
        with self.assertRaises(ValueError):
            MODULE.evaluate(forged, CHECKS)
        with self.assertRaises(ValueError):
            MODULE.evaluate(artifact(baking="zz"), CHECKS)

    def test_wrong_types_fail(self):
        for bad in (None, [], "text", 3):
            with self.assertRaises(ValueError):
                MODULE.evaluate(bad, CHECKS)
        bad = artifact()
        bad["viewed"][0] = {}
        with self.assertRaises(ValueError):
            MODULE.evaluate(bad, CHECKS)

    def test_event_order_and_final_state_are_required(self):
        bad = artifact()
        bad["events"][-3]["id"] = "b1"
        with self.assertRaises(ValueError):
            MODULE.evaluate(bad, CHECKS)
        bad = artifact()
        bad["events"][-1], bad["events"][-2] = bad["events"][-2], bad["events"][-1]
        with self.assertRaises(ValueError):
            MODULE.evaluate(bad, CHECKS)

    def test_malformed_file_writes_structured_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            out = root / "out"
            result = root / "result"
            out.mkdir(parents=True)
            (out / "volunteer_assignments.json").write_text("null", encoding="utf-8")
            env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(out),
                   "ADHERENCE_VERIFIER_DIR": str(result)}
            proc = subprocess.run(["python3", str(PATH)], env=env, capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0)
            payload = json.loads((result / "structured_output.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["reward"], 0.0)


if __name__ == "__main__":
    unittest.main()
