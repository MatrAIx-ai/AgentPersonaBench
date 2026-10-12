#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
QUESTIONNAIRE = HERE.parent / "input" / "questionnaire.yaml"
QUESTION_ORDER = ("checkout", "search", "signup", "composer", "notifications")
BEST = {
    "checkout": "cx_m17",
    "search": "sr_t61",
    "signup": "su_d47",
    "composer": "mc_e87",
    "notifications": "nt_u83",
}


def artifact(mapping: dict[str, object] | None = None) -> dict:
    selected = BEST if mapping is None else mapping
    return {
        "answers": [
            {"questionId": question_id, "selectedOptionId": selected[question_id]}
            for question_id in selected
        ]
    }


class SurveyVerifierTests(unittest.TestCase):
    def run_case(
        self,
        value: object = None,
        *,
        write_file: bool = True,
        raw: str | None = None,
        without_pyyaml: bool = False,
    ) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if write_file:
                (root / "survey_result.json").write_text(
                    raw if raw is not None else json.dumps(value), encoding="utf-8"
                )
            verified = root / "verified"
            env = {
                **os.environ,
                "ADHERENCE_OUTPUT_DIR": str(root),
                "ADHERENCE_VERIFIER_DIR": str(verified),
            }
            command = [sys.executable]
            if without_pyyaml:
                command.append("-S")
            command.append(str(HERE / "verifier.py"))
            proc = subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
            )
            result = json.loads((verified / "structured_output.json").read_text(encoding="utf-8"))
            reward = (verified / "reward.txt").read_text(encoding="utf-8").strip()
            self.assertEqual(float(reward), result["reward"])
            return proc.returncode, result

    def assert_case(self, value: object, code: int, verdict: str) -> None:
        actual_code, result = self.run_case(value)
        self.assertEqual(actual_code, code, result)
        self.assertEqual(result["verdict"], verdict, result)

    def test_held_exact_and_defensible(self) -> None:
        self.assert_case(artifact(), 0, "HELD")
        defensible = {**BEST, "checkout": "cx_q42", "signup": "su_r86"}
        self.assert_case(artifact(defensible), 0, "HELD")

    def test_without_pyyaml_scores_valid_work_and_fails_closed(self) -> None:
        code, result = self.run_case(artifact(), without_pyyaml=True)
        self.assertEqual((code, result["verdict"], result["reward"]), (0, "HELD", 1.0))
        code, result = self.run_case({"answers": []}, without_pyyaml=True)
        self.assertEqual((code, result["verdict"], result["reward"]), (2, "ERROR", 0.0))

    def test_material_and_serious_errors_violate(self) -> None:
        material = {**BEST, "signup": "su_k13"}
        serious = {**BEST, "composer": "mc_l39"}
        self.assert_case(artifact(material), 1, "VIOLATED")
        self.assert_case(artifact(serious), 1, "VIOLATED")

    def test_dynamic_blind_action_and_position_policies_fail(self) -> None:
        questions = yaml.safe_load(QUESTIONNAIRE.read_text(encoding="utf-8"))["questions"]
        self.assertEqual(tuple(question["id"] for question in questions), QUESTION_ORDER)
        policies: list[dict[str, str]] = []
        policies.append({question["id"]: question["options"][0]["id"] for question in questions})
        policies.append({question["id"]: question["options"][-1]["id"] for question in questions})
        policies.append(
            {
                question["id"]: max(question["options"], key=lambda option: len(option["text"]))["id"]
                for question in questions
            }
        )
        for action in ("launch", "continue", "investigate", "reject"):
            fixed_action: dict[str, str] = {}
            for question in questions:
                matches = [
                    option for option in question["options"]
                    if option["text"].lower().startswith(action)
                ]
                self.assertEqual(len(matches), 1, (question["id"], action))
                fixed_action[question["id"]] = matches[0]["id"]
            policies.append(fixed_action)
        for policy in policies:
            self.assert_case(artifact(policy), 1, "VIOLATED")

    def test_visible_options_avoid_caricature_shortcuts(self) -> None:
        questions = yaml.safe_load(QUESTIONNAIRE.read_text(encoding="utf-8"))["questions"]
        visible = "\n".join(
            option["text"].lower()
            for question in questions
            for option in question["options"]
        )
        for phrase in (
            "by itself is enough",
            "vp supports",
            "every positive experiment",
            "can never be useful",
            "p-value still smaller",
            "one conventional p-value",
            "abandon the variant permanently",
            "repeatedly checking the same",
            "post-hoc",
            "even though no",
            "despite the registered",
        ):
            self.assertNotIn(phrase, visible)

    def test_uniform_random_held_probability_is_low(self) -> None:
        questions = yaml.safe_load(QUESTIONNAIRE.read_text(encoding="utf-8"))["questions"]
        tiers = yaml.safe_load((HERE / "answer_key.yaml").read_text(encoding="utf-8"))["tiers"]
        probability = 1.0
        for question in questions:
            acceptable = sum(tiers[option["id"]] < 2 for option in question["options"])
            self.assertEqual(acceptable, 2)
            probability *= acceptable / len(question["options"])
        self.assertAlmostEqual(probability, 0.03125)

    def test_material_options_misuse_same_data_not_legitimate_new_business_rules(self) -> None:
        questions = yaml.safe_load(QUESTIONNAIRE.read_text(encoding="utf-8"))["questions"]
        by_id = {question["id"]: question for question in questions}
        checkout = by_id["checkout"]
        self.assertIn("binding rollout population", checkout["prompt"])
        self.assertIn("already includes capacity", checkout["prompt"])
        checkout_options = {option["id"]: option["text"] for option in checkout["options"]}
        self.assertIn("after seeing the result", checkout_options["cx_v68"].lower())
        self.assertIn("same run", checkout_options["cx_b91"].lower())
        self.assertIn("confirmatory target", checkout_options["cx_b91"].lower())
        composer = by_id["composer"]
        self.assertIn("binding target population", composer["prompt"])
        composer_options = {option["id"]: option["text"] for option in composer["options"]}
        self.assertIn("same run", composer_options["mc_f22"].lower())
        self.assertIn("confirmatory rollout rule", composer_options["mc_f22"].lower())

    def test_missing_empty_overflow_and_partial_are_errors(self) -> None:
        code, result = self.run_case(write_file=False)
        self.assertEqual((code, result["verdict"]), (2, "ERROR"))
        self.assert_case({"answers": []}, 2, "ERROR")
        self.assert_case(artifact({key: BEST[key] for key in QUESTION_ORDER[:-1]}), 2, "ERROR")
        overflow = artifact() | {"comment": "extra"}
        self.assert_case(overflow, 2, "ERROR")

    def test_duplicate_cross_question_unknown_and_wrong_types_are_errors(self) -> None:
        duplicate = artifact()
        duplicate["answers"][1] = {
            "questionId": "checkout",
            "selectedOptionId": "cx_q42",
        }
        self.assert_case(duplicate, 2, "ERROR")
        cross = artifact()
        cross["answers"][0]["selectedOptionId"] = "sr_t61"
        self.assert_case(cross, 2, "ERROR")
        unknown = artifact()
        unknown["answers"][0]["selectedOptionId"] = "not-an-option"
        self.assert_case(unknown, 2, "ERROR")
        wrong_type = artifact()
        wrong_type["answers"][0]["selectedOptionId"] = 17
        self.assert_case(wrong_type, 2, "ERROR")

    def test_malformed_json_and_answer_shape_are_errors(self) -> None:
        code, result = self.run_case(raw="{not json")
        self.assertEqual((code, result["verdict"]), (2, "ERROR"))
        malformed = artifact()
        malformed["answers"][0]["explanation"] = "because"
        self.assert_case(malformed, 2, "ERROR")


if __name__ == "__main__":
    unittest.main()
