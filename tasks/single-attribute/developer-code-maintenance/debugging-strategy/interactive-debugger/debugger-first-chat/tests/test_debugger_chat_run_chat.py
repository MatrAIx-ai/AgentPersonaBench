"""Check real conversation/history retention through the unchanged simulator port."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

TASK = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("chat_task_run", TASK / "solution/run_chat.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class HarnessArtifacts(unittest.TestCase):
    def test_preserves_real_runner_messages_calls_and_agenda(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            calls = []
            native = SimpleNamespace(persona_id="native-without-to-dict")
            actual_colleague = module.AgendaColleague
            def chat(messages, **kwargs):
                calls.append({"model": kwargs["model"], "prompt_tokens": 7, "completion_tokens": 3})
                return "A natural follow-up question."
            def colleague(*args, **kwargs):
                return actual_colleague(*args, **kwargs, chat=chat)
            def runner(session, persona, context, config, **kwargs):
                self.assertIs(persona, native)
                self.assertEqual(config.max_turns, 12)
                self.assertTrue(config.force_full_turns)
                self.assertEqual(config.persona_model, "recorded-model")
                self.assertEqual(kwargs["persona_yaml_path"], str(TASK / "persona.yaml"))
                self.assertNotIn("on_event", kwargs)
                self.assertEqual(context, (TASK / "input/context.md").read_text(encoding="utf-8"))
                turns = []
                for i in range(12):
                    user = f"Real persona message {i + 1}."
                    reply = session.run_turn_sync(user)["assistantMessage"]
                    turns.append(SimpleNamespace(user_message=user, assistant_message=reply))
                return SimpleNamespace(transcript=turns)
            fake_usage = SimpleNamespace(reset=calls.clear, CALL_LOG=calls,
                                         summary=lambda: {"calls": len(calls), "total_tokens": len(calls) * 10})
            modules = {"matraix.agents.persona.loader": SimpleNamespace(load_persona=lambda path: native),
                       "playground.types": SimpleNamespace(PlaygroundConfig=lambda **kw: SimpleNamespace(**kw)),
                       "playground.user_sim.runner": SimpleNamespace(run_playground=runner),
                       "usage": fake_usage}
            with patch.dict(sys.modules, modules), patch.object(module, "AgendaColleague", colleague), patch.dict(
                "os.environ", {"MATRAIX_PERSONA_PROFILE_MAX_CHARS": "", "LLM_MODEL": "recorded-model"}):
                module.run(TASK, out, "configured-arm")
            result = json.loads((out / "generation.json").read_text())
            self.assertEqual(result["construct_version"], 3)
            self.assertEqual(len(result["full_transcript"]), 24)
            self.assertEqual(result["calls"], calls)
            self.assertEqual(len(calls), 5)
            turns = json.loads((out / "user_turns.json").read_text())
            self.assertEqual(turns["turns"], [f"Real persona message {i}." for i in range(1, 13)])
            events = json.loads((out / "colleague_agenda.json").read_text())["events"]
            self.assertEqual(len(events), 12)
            with zipfile.ZipFile(out / "trace.zip") as bundle:
                for name in bundle.namelist():
                    self.assertEqual(bundle.read(name), (out / name).read_bytes())

    def test_truncated_profile_rejected_before_runner(self):
        modules = {"matraix.agents.persona.loader": SimpleNamespace(load_persona=lambda *a: self.fail("loaded persona")),
                   "playground.types": SimpleNamespace(PlaygroundConfig=SimpleNamespace),
                   "playground.user_sim.runner": SimpleNamespace(run_playground=lambda *a: self.fail("runner called")),
                   "usage": SimpleNamespace()}
        with patch.dict(sys.modules, modules), patch.dict("os.environ", {"MATRAIX_PERSONA_PROFILE_MAX_CHARS": "2000"}):
            with self.assertRaises(ValueError):
                module.run(TASK, Path("unused"), "test")


if __name__ == "__main__":
    unittest.main()
