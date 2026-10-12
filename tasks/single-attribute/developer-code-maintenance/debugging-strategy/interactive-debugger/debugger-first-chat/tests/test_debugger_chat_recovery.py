"""Recovery retains source evidence and rejects partial or inconsistent turns."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("chat_recovery", Path(__file__).with_name("recover_diagnostic.py"))
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)


class Recovery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.task = self.root / "task"
        (self.task / "tests").mkdir(parents=True)
        (self.task / "persona.yaml").write_text("persona_id: original-native\n", encoding="utf-8")
        for name in ("rubric.md", "verifier.py"):
            (self.task / "tests" / name).write_text("frozen source", encoding="utf-8")
        self.trial = self.root / "trial"
        self.trial.mkdir()
        self.metadata = {
            "status": "error", "error_type": "AttributeError",
            "persona_block_matches_treatment": True, "native_persona_unchanged": True,
            "model": "actual-model", "provider": "anthropic", "condition": "full",
            "partial_actor_usage": {"calls": [{"total_tokens": 20}], "summary": {"total_tokens": 20}},
            "source_sha256": {name: hashlib.sha256((self.task / name).read_bytes()).hexdigest()
                              for name in ("tests/rubric.md", "tests/verifier.py", "persona.yaml")},
        }
        self.events = []
        for i in range(1, 13):
            turn = {"turnIndex": i, "userMessage": f"Actual user {i}", "assistantMessage": f"Actual bot {i}"}
            self.events.extend([{"type": "assistant_message", **turn}, {"type": "turn", "turn": turn}])

    def run_recovery(self):
        recovery.write(self.trial / "diagnostic-metadata.json", self.metadata)
        recovery.write(self.trial / "harness-events.json", self.events)
        with patch.object(recovery, "TASK", self.task):
            return recovery.recover(self.trial)

    def test_preserves_verbatim_and_does_not_relabel_original_status(self):
        out = self.run_recovery()
        turns = json.loads((out / "user_turns.json").read_text())["turns"]
        self.assertEqual(turns, [f"Actual user {i}" for i in range(1, 13)])
        self.assertEqual(json.loads((self.trial / "diagnostic-metadata.json").read_text())["status"], "error")
        record = json.loads((out / "recovery.json").read_text())
        self.assertEqual(record["model_calls_repeated"], 0)
        self.assertEqual(record["harness_events_sha256"],
                         hashlib.sha256((self.trial / "harness-events.json").read_bytes()).hexdigest())
        self.assertFalse((out / "envelope.json").exists())

    def test_partial_events_fail_closed(self):
        self.events.pop()
        with self.assertRaises(ValueError):
            self.run_recovery()

    def test_changed_scoring_source_fails_closed(self):
        self.metadata["source_sha256"]["tests/rubric.md"] = "wrong"
        with self.assertRaises(ValueError):
            self.run_recovery()


if __name__ == "__main__":
    unittest.main()
