"""Saved-dialogue rejudging preserves input and refuses evidence replacement."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

TESTS = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(__name__ + "_verifier", TESTS / "verifier.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
spec = importlib.util.spec_from_file_location(__name__ + "_rejudge", TESTS / "rejudge.py")
rejudge = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"verifier": verifier}):
    spec.loader.exec_module(rejudge)


class SavedDialogue(unittest.TestCase):
    def setUp(self):
        import yaml
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "original"
        self.source.mkdir()
        self.output = self.root / "new-judgment"
        persona = yaml.safe_load((TESTS.parent / "persona.yaml").read_text(encoding="utf-8"))
        turns = [f"Saved persona turn {i}." for i in range(12)]
        transcript = [message for turn in turns for message in
                      ({"role": "user", "content": turn},
                       {"role": "assistant", "content": "Saved colleague reply."})]
        for name, value in {
            "user_turns.json": {"persona": persona["persona_id"], "turns": turns},
            "transcript.json": transcript,
            "diagnostic-metadata.json": {"status": "verifier_error", "condition": "blind",
                "source_sha256": {"tests/rubric.md":
                    hashlib.sha256((TESTS / "rubric.md").read_bytes()).hexdigest()}},
        }.items():
            (self.source / name).write_text(json.dumps(value), encoding="utf-8")
        self.resolved = SimpleNamespace(model="test-judge", provider="openai",
            _asdict=lambda: {"model": "test-judge", "provider": "openai"})
        self.fake_modules = {
            "judge": SimpleNamespace(infer_provider=lambda _: "openai", resolve=lambda: self.resolved),
            "judge_protocol": SimpleNamespace(REVISION="6.0"),
            "usage": SimpleNamespace(CALL_LOG=[], reset=lambda: None, summary=lambda: {"calls": 0}),
        }

    def run_cli(self, source, flag="--input"):
        arguments = ["rejudge.py", "--execute", flag, str(source),
                     "--output", str(self.output), "--model-id", "test-judge",
                     "--target", "Interactive debugger"]
        with patch.object(sys, "argv", arguments), patch.dict(sys.modules, self.fake_modules), \
             patch.object(rejudge.verifier, "assess", return_value={
                 "verdict": "HELD", "reward": 1.0, "complete": True, "target_count": 3}):
            return rejudge.main()

    def test_saved_input_and_legacy_recovered_alias(self):
        original = {p.name: p.read_bytes() for p in self.source.iterdir()}
        self.assertEqual(self.run_cli(self.source), 0)
        result = json.loads((self.output / "structured_output.json").read_text())
        detail = result["criteria"][0]["raw"]
        self.assertEqual(detail["rubric_revision"], verifier.RUBRIC_REVISION)
        self.assertFalse(detail["input_is_recovered"])
        self.assertEqual(detail["actor_calls_repeated"], 0)
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.source.iterdir()})

        recovered = self.source / "recovered-diagnostic"
        recovered.mkdir()
        for name in ("transcript.json", "user_turns.json"):
            (recovered / name).write_bytes(original[name])
        (recovered / "recovery.json").write_text("{}")
        self.output = self.root / "recovered-judgment"
        self.assertEqual(self.run_cli(recovered, "--recovered"), 0)
        detail = json.loads((self.output / "structured_output.json").read_text())["criteria"][0]["raw"]
        self.assertTrue(detail["input_is_recovered"])

    def test_refuses_overwrite_and_unlabeled_input(self):
        self.output.mkdir()
        marker = self.output / "preserve.txt"
        marker.write_text("earlier evidence")
        with self.assertRaises(SystemExit):
            self.run_cli(self.source)
        self.assertEqual(marker.read_text(), "earlier evidence")
        self.output = self.root / "other-judgment"
        (self.source / "diagnostic-metadata.json").unlink()
        with self.assertRaises(SystemExit):
            self.run_cli(self.source)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
