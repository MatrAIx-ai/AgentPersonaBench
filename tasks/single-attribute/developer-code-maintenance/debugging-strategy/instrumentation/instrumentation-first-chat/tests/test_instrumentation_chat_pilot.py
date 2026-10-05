"""Observer regression: never enable shared result serialization callbacks."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

SPEC = importlib.util.spec_from_file_location("chat_pilot", Path(__file__).with_name("pilot.py"))
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)


class Observer(unittest.TestCase):
    def test_prompt_and_reply_observation_without_final_callback(self):
        for condition in ("full", "blind"):
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as temp:
                out = Path(temp)
                metadata = {}
                prompt = SimpleNamespace(render_persona_block=lambda *a, **kw: "Full native block")
                original_render = prompt.render_persona_block
                usage = SimpleNamespace(CALL_LOG=[], summary=lambda: {})
                class PersonaWithoutToDict:
                    pass
                class Session:
                    def __init__(self, persona):
                        self.system_prompt = prompt.render_persona_block(persona) + "\n\nUnchanged material"
                class Bot:
                    def run_turn_sync(self, message):
                        return {"assistantMessage": "Real colleague reply", "items": []}
                original_init, original_reply = Session.__init__, Bot.run_turn_sync
                def unchanged_runner(*, on_event=None):
                    person = PersonaWithoutToDict()
                    Session(person)
                    reply = Bot().run_turn_sync("Real user message")
                    if on_event is not None:
                        person.to_dict()  # The dormant shared mismatch must stay dormant.
                    return reply
                with pilot.diagnostic_observers(
                    session_type=Session, bot_type=Bot, prompt_module=prompt, usage=usage,
                    output=out, metadata=metadata, full_block="Full native block", condition=condition,
                ):
                    result = unchanged_runner()
                self.assertEqual(result["assistantMessage"], "Real colleague reply")
                self.assertIs(Session.__init__, original_init)
                self.assertIs(Bot.run_turn_sync, original_reply)
                self.assertIs(prompt.render_persona_block, original_render)
                events = json.loads((out / "harness-events.json").read_text())
                self.assertEqual(events[0]["turn"]["userMessage"], "Real user message")
                self.assertTrue(metadata["persona_block_matches_treatment"])

    def test_functions_restore_on_failure(self):
        prompt = SimpleNamespace(render_persona_block=lambda *a, **kw: "native")
        original = prompt.render_persona_block
        class Session:
            def __init__(self):
                raise RuntimeError("simulated failure")
        class Bot:
            def run_turn_sync(self, message):
                return {}
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(RuntimeError):
                with pilot.diagnostic_observers(
                    session_type=Session, bot_type=Bot, prompt_module=prompt,
                    usage=SimpleNamespace(CALL_LOG=[], summary=lambda: {}),
                    output=Path(temp), metadata={}, full_block="native", condition="blind",
                ):
                    Session()
        self.assertIs(prompt.render_persona_block, original)

    def test_luna_full_and_blind_diagnostics_select_the_named_provider_and_arm(self):
        import os
        from unittest.mock import patch
        for condition in ("full", "blind"):
            with self.subTest(condition=condition), tempfile.TemporaryDirectory() as temp:
                out = Path(temp) / condition
                prompt = SimpleNamespace(render_persona_block=lambda *a, **kw: "Full native block")
                class Session:
                    def __init__(self, *args, **kwargs):
                        self.system_prompt = prompt.render_persona_block(None) + chr(10) * 2 + "Unchanged task material"
                class Bot:
                    def run_turn_sync(self, message):
                        return {"assistantMessage": "Fixed colleague reply"}
                calls = []
                def run(task, output, arm):
                    calls.append({"arm": arm, "environment": dict(os.environ)})
                    Session()
                    Bot().run_turn_sync("Actual persona turn")
                actor = SimpleNamespace(run=run, AgendaColleague=Bot)
                verifier = SimpleNamespace(main=lambda: 0)
                def spec(name, path):
                    module = actor if str(path).endswith("run_chat.py") else verifier
                    return SimpleNamespace(module=module, loader=SimpleNamespace(exec_module=lambda module: None))
                modules = {"usage": SimpleNamespace(CALL_LOG=[], summary=lambda: {}),
                           "playground.user_sim": SimpleNamespace(prompt=prompt),
                           "playground.user_sim.session": SimpleNamespace(UserSimSession=Session),
                           "matraix.agents.persona.loader": SimpleNamespace(load_persona=lambda path: SimpleNamespace(persona_id="native"))}
                argv = ["pilot.py", "--execute", "--model-id", "gpt-5.6-luna",
                        "--condition", condition, "--output", str(out)]
                with patch.dict("sys.modules", modules), patch.dict(os.environ, {}, clear=False), patch(
                    "sys.argv", argv
                ), patch.object(pilot.importlib.util, "spec_from_file_location", side_effect=spec), patch.object(
                    pilot.importlib.util, "module_from_spec", side_effect=lambda spec: spec.module
                ):
                    self.assertEqual(pilot.main(), 0)
                env = calls[0]["environment"]
                for key in ("LLM_PROVIDER", "ADHERENCE_JUDGE_PROVIDER"):
                    self.assertEqual(env[key], "openai")
                for key in ("LLM_MODEL", "ADHERENCE_JUDGE_MODEL"):
                    self.assertEqual(env[key], "gpt-5.6-luna")
                self.assertEqual(calls[0]["arm"], "gpt-5-6-luna")
                metadata = json.loads((out / "diagnostic-metadata.json").read_text())
                self.assertEqual(metadata["provider"], "openai")
                self.assertEqual(metadata["arm_label"], "gpt-5-6-luna")
                self.assertEqual(metadata["condition"], condition)
                self.assertTrue(metadata["persona_block_matches_treatment"])
                self.assertTrue(metadata["native_persona_unchanged"])
                rendered = json.loads((out / "rendered-prompts.json").read_text())
                self.assertEqual(rendered["personaPrompt"], "Full native block" if condition == "full" else pilot.NEUTRAL_ROLE)



if __name__ == "__main__":
    unittest.main()
