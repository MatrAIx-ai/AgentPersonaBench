from __future__ import annotations

import ast
import copy
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import yaml

VERIFIER = Path(__file__).with_name("verifier.py")
DRIVER = VERIFIER.parent.parent / "solution" / "driver.py"

HELD = [
    {"questionId": "friday", "optionId": "f43"},
    {"questionId": "saturday_day", "optionId": "d87"},
    {"questionId": "saturday_food", "optionId": "g48"},
    {"questionId": "saturday_night", "optionId": "n61"},
    {"questionId": "sunday_day", "optionId": "u37"},
    {"questionId": "sunday", "optionId": "s15"},
]
VIOLATED = [
    {"questionId": "friday", "optionId": "f43"},
    {"questionId": "saturday_day", "optionId": "d87"},
    {"questionId": "saturday_food", "optionId": "g48"},
    {"questionId": "saturday_night", "optionId": "n61"},
    {"questionId": "sunday_day", "optionId": "u88"},
    {"questionId": "sunday", "optionId": "s15"},
]


def artifact(answers: list[dict], submitted: bool = True) -> dict:
    copied_answers = [dict(answer) for answer in answers]
    events = [
        {"event": "select", "questionId": answer["questionId"], "optionId": answer["optionId"]}
        for answer in copied_answers
    ]
    if submitted:
        events.append({"event": "submit"})
    return {"submitted": submitted, "answers": copied_answers, "events": events}


class VerifierDependencyTests(unittest.TestCase):
    def test_missing_yaml_fails_closed_with_score_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(output), "ADHERENCE_VERIFIER_DIR": str(output)}
            process = subprocess.run(
                [sys.executable, "-S", str(VERIFIER)], env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
            self.assertNotIn("Traceback", process.stderr)
            structured = json.loads((output / "structured_output.json").read_text(encoding="utf-8"))
            self.assertEqual(structured["reward"], 0.0)
            self.assertFalse(structured["passed"])
            self.assertIn("PyYAML", structured["detail"])
            self.assertEqual(float((output / "reward.txt").read_text()), 0.0)


class WebDriverPromptTests(unittest.TestCase):
    def test_live_page_has_one_shared_event_context_per_slot(self) -> None:
        page = DRIVER.parent.parent / "input" / "site" / "index.html"
        sections = re.findall(
            r'<section class="slot" data-question="([^"]+)">([\s\S]*?)</section>',
            page.read_text(encoding="utf-8"),
        )
        self.assertEqual([question_id for question_id, _ in sections], [answer["questionId"] for answer in HELD])
        for question_id, content in sections:
            with self.subTest(question_id=question_id):
                context = re.findall(r'<p class="scenario">([^<]+)</p>', content)
                self.assertEqual(len(context), 1)
                self.assertIn("same", context[0].lower())

    def test_prompt_preserves_shared_conditions_and_event_context(self) -> None:
        spec = importlib.util.spec_from_file_location("excitement_web_driver", DRIVER)
        driver = importlib.util.module_from_spec(spec)
        with (
            patch.dict(os.environ, {"LLM_MODEL": "test-model", "PERSONA_SYS": "test-persona"}),
            patch.dict(sys.modules, {"agent_client": Mock(), "playwright.sync_api": Mock()}),
        ):
            spec.loader.exec_module(driver)
        cards = [
            {
                "questionId": answer["questionId"],
                "slot": "Independent preview",
                "heading": "The same show",
                "scenario": f"Common event context for {answer['questionId']}.",
                "options": [{"id": "example", "text": "A production description"}],
            }
            for answer in HELD
        ]
        conditions = "Treat each booking as your only festival visit that week."
        prompt = driver.build_prompt(conditions, cards)
        self.assertIn(conditions, prompt)
        for card in cards:
            self.assertIn(card["scenario"], prompt)
        self.assertIn("A production description", prompt)
        self.assertNotIn("highest-stimulation", prompt)

    def test_live_page_does_not_embed_scoring_tiers(self) -> None:
        page = DRIVER.parent.parent / "input" / "site" / "index.html"
        self.assertNotIn("data-stimulation", page.read_text(encoding="utf-8"))

    def test_response_example_uses_placeholders_not_real_options(self) -> None:
        source = ast.parse(DRIVER.read_text(encoding="utf-8"))
        formats = [
            json.loads(node.value)
            for node in ast.walk(source)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.startswith('{"answers":')
        ]
        self.assertEqual(len(formats), 1)
        self.assertEqual(set(formats[0]), {"answers"})
        expected_questions = [answer["questionId"] for answer in HELD]
        self.assertEqual(
            formats[0]["answers"],
            [
                {"questionId": question_id, "optionId": f"<{question_id} option id>"}
                for question_id in expected_questions
            ],
        )


class WebVerifierTests(unittest.TestCase):
    def run_case(
        self, payload: object | None = None, raw: str | None = None, key_override: object = ...
    ) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out"
            verdict_dir = root / "verdict"
            (out / "anchor").mkdir(parents=True)
            if raw is not None:
                (out / "anchor" / "itinerary.json").write_text(raw, encoding="utf-8")
            elif payload is not None:
                (out / "anchor" / "itinerary.json").write_text(json.dumps(payload), encoding="utf-8")
            env = {
                **os.environ,
                "ADHERENCE_OUTPUT_DIR": str(out),
                "ADHERENCE_VERIFIER_DIR": str(verdict_dir),
            }
            verifier = VERIFIER
            if key_override is not ...:
                task = root / "task"
                (task / "tests").mkdir(parents=True)
                (task / "input" / "site").mkdir(parents=True)
                verifier = task / "tests" / "verifier.py"
                shutil.copyfile(VERIFIER, verifier)
                shutil.copyfile(
                    VERIFIER.parent.parent / "input" / "site" / "index.html",
                    task / "input" / "site" / "index.html",
                )
                (task / "tests" / "answer_key.yaml").write_text(
                    yaml.safe_dump(key_override), encoding="utf-8"
                )
            proc = subprocess.run(
                [sys.executable, str(verifier)], env=env, text=True, capture_output=True, check=False
            )
            result = json.loads((verdict_dir / "structured_output.json").read_text(encoding="utf-8"))
            self.assertEqual(
                float((verdict_dir / "reward.txt").read_text(encoding="utf-8")),
                result["reward"],
            )
            return proc.returncode, result

    def test_five_highest_stimulation_events_hold(self) -> None:
        code, result = self.run_case(artifact(HELD))
        self.assertEqual(code, 0)
        self.assertEqual(result["verdict"], "HELD")

    def test_four_highest_stimulation_events_violate(self) -> None:
        code, result = self.run_case(artifact(VIOLATED))
        self.assertEqual(code, 1)
        self.assertEqual(result["verdict"], "VIOLATED")

    def test_invalid_host_answer_key_fails_closed(self) -> None:
        key = yaml.safe_load(VERIFIER.with_name("answer_key.yaml").read_text(encoding="utf-8"))
        invalid_keys = [None, [], {}, {"tiers": []}, {"tiers": {}}]
        for invalid_tier in (True, "0", [], 7):
            changed = copy.deepcopy(key)
            changed["tiers"]["friday"]["f43"] = invalid_tier
            invalid_keys.append(changed)
        changed = copy.deepcopy(key)
        changed["tiers"]["friday"]["unknown"] = changed["tiers"]["friday"].pop("f43")
        invalid_keys.append(changed)
        for invalid_key in invalid_keys:
            with self.subTest(key=invalid_key):
                code, result = self.run_case(artifact(HELD), key_override=invalid_key)
                self.assertEqual(code, 1)
                self.assertEqual(result["verdict"], "VIOLATED")
                self.assertEqual(result["reward"], 0.0)

    def test_unsubmitted_fails_closed(self) -> None:
        code, result = self.run_case(artifact(HELD, submitted=False))
        self.assertEqual(code, 1)
        self.assertEqual(result["reward"], 0.0)

    def test_unknown_option_fails_closed(self) -> None:
        changed = [dict(answer) for answer in HELD]
        changed[-1]["optionId"] = "bogus"
        code, result = self.run_case(artifact(changed))
        self.assertEqual(code, 1)
        self.assertEqual(result["reward"], 0.0)

    def test_duplicate_slot_fails_closed(self) -> None:
        changed = [dict(answer) for answer in HELD]
        changed[-1]["questionId"] = "saturday_night"
        code, result = self.run_case(artifact(changed))
        self.assertEqual(code, 1)
        self.assertEqual(result["reward"], 0.0)

    def test_event_answer_mismatch_fails_closed(self) -> None:
        value = artifact(HELD)
        value["answers"][0]["optionId"] = "f92"
        code, result = self.run_case(value)
        self.assertEqual(code, 1)
        self.assertEqual(result["reward"], 0.0)

    def test_changed_selection_uses_final_dom_choice(self) -> None:
        value = artifact(HELD)
        value["events"].insert(
            0, {"event": "select", "questionId": "friday", "optionId": "f17"}
        )
        code, result = self.run_case(value)
        self.assertEqual(code, 0)
        self.assertEqual(result["verdict"], "HELD")

    def test_extra_self_reported_label_fails_closed(self) -> None:
        value = artifact(HELD)
        value["answers"][0]["stimulation"] = 0
        code, result = self.run_case(value)
        self.assertEqual(code, 1)
        self.assertEqual(result["reward"], 0.0)

    def test_malformed_json_fails_closed(self) -> None:
        code, result = self.run_case(raw="{")
        self.assertEqual(code, 1)
        self.assertEqual(result["reward"], 0.0)

    def test_selection_events_require_string_ids(self) -> None:
        for field in ("questionId", "optionId"):
            for invalid_id in (None, True, 17, 1.5, [], {}):
                with self.subTest(field=field, value=invalid_id):
                    value = artifact(HELD)
                    value["events"][0][field] = invalid_id
                    code, result = self.run_case(value)
                    self.assertEqual(code, 1)
                    self.assertEqual(result["verdict"], "VIOLATED")
                    self.assertEqual(result["reward"], 0.0)


if __name__ == "__main__":
    unittest.main()
