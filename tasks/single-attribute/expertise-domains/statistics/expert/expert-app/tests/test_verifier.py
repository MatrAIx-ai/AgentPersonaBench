#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent
CASES = ("email", "catalog", "recommender")
BEST = {
    "email": ("act_launch", "em_declared"),
    "catalog": ("act_continue", "ca_interval"),
    "recommender": ("act_investigate", "rc_multiplicity"),
}


def artifact(
    selected: dict[str, tuple[object, object]] | None = None,
    *,
    submitted: bool = True,
) -> dict:
    choices = BEST if selected is None else selected
    reviews = [
        {"caseId": case_id, "actionId": choices[case_id][0], "reasonId": choices[case_id][1]}
        for case_id in choices
    ]
    events: list[dict] = []
    for case_id in CASES:
        events.append({"event": "open_case", "caseId": case_id})
        if case_id in choices:
            events.append(
                {"event": "select_action", "caseId": case_id, "actionId": choices[case_id][0]}
            )
            events.append(
                {"event": "select_reason", "caseId": case_id, "reasonId": choices[case_id][1]}
            )
    if submitted:
        events.append({"event": "submit"})
    return {
        "appVersion": "stat-review-desk-v1",
        "contentDigest": "364d202e49a31dfae60c56e5a74ca6c596abecb314550dca25c8a09eb2b601d8",
        "submitted": submitted,
        "reviews": reviews,
        "events": events,
    }


class AppVerifierTests(unittest.TestCase):
    def run_case(
        self,
        value: object | None,
        *,
        write_file: bool = True,
        raw: str | None = None,
    ) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            if write_file:
                (root / "decision.json").write_text(
                    raw if raw is not None else json.dumps(value), encoding="utf-8"
                )
            verified = root / "verified"
            env = {
                **os.environ,
                "ADHERENCE_OUTPUT_DIR": str(root),
                "ADHERENCE_VERIFIER_DIR": str(verified),
            }
            proc = subprocess.run(
                [sys.executable, str(HERE / "verifier.py")],
                env=env,
                capture_output=True,
                text=True,
            )
            result = json.loads((verified / "structured_output.json").read_text(encoding="utf-8"))
            self.assertEqual(
                float((verified / "reward.txt").read_text(encoding="utf-8")), result["reward"]
            )
            return proc.returncode, result

    def assert_case(self, value: object, code: int, verdict: str) -> None:
        actual_code, result = self.run_case(value)
        self.assertEqual(actual_code, code, result)
        self.assertEqual(result["verdict"], verdict, result)

    def test_held_exact_and_tier_one(self) -> None:
        self.assert_case(artifact(), 0, "HELD")
        defensible = {
            "email": ("act_continue", "em_more"),
            "catalog": ("act_investigate", "ca_interval"),
            "recommender": ("act_reject", "rc_multiplicity"),
        }
        self.assert_case(artifact(defensible), 0, "HELD")

    def test_material_errors_and_blind_policies_violate(self) -> None:
        self.assert_case(
            artifact({**BEST, "recommender": ("act_launch", "rc_onep")}),
            1,
            "VIOLATED",
        )
        for action_id in ("act_launch", "act_continue", "act_investigate", "act_reject"):
            policy = {
                case_id: (action_id, BEST[case_id][1]) for case_id in CASES
            }
            self.assert_case(artifact(policy), 1, "VIOLATED")
        reason_positions = (
            {"email": "em_pvalue", "catalog": "ca_point", "recommender": "rc_users"},
            {"email": "em_vp", "catalog": "ca_interval", "recommender": "rc_onep"},
            {"email": "em_declared", "catalog": "ca_deadline", "recommender": "rc_multiplicity"},
            {"email": "em_more", "catalog": "ca_zero", "recommender": "rc_morepeek"},
        )
        for reasons in reason_positions:
            policy = {
                case_id: (BEST[case_id][0], reasons[case_id]) for case_id in CASES
            }
            self.assert_case(artifact(policy), 1, "VIOLATED")

    def test_only_coherent_low_tier_action_reason_pairs_are_held(self) -> None:
        key = yaml.safe_load((HERE / "answer_key.yaml").read_text(encoding="utf-8"))
        for case_id in CASES:
            acceptable = {tuple(pair) for pair in key["acceptable_pairs"][case_id]}
            for action_id in key["action_tiers"][case_id]:
                for reason_id in key["reason_tiers"][case_id]:
                    policy = {**BEST, case_id: (action_id, reason_id)}
                    expected = (
                        (0, "HELD")
                        if (action_id, reason_id) in acceptable
                        else (1, "VIOLATED")
                    )
                    self.assert_case(artifact(policy), *expected)

        self.assert_case(
            artifact({**BEST, "email": ("act_launch", "em_more")}),
            1,
            "VIOLATED",
        )

    def test_dynamic_first_last_and_longest_policies_violate(self) -> None:
        source_path = TASK_DIR / "input" / "app" / "app.py"
        spec = importlib.util.spec_from_file_location("statistics_review_app_blind", source_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        actions = list(module.ACTIONS)
        cases = {case["id"]: case for case in module.CASES}
        policies: list[dict[str, tuple[str, str]]] = []
        for action_index, reason_selector in (
            (0, lambda reasons: reasons[0]),
            (-1, lambda reasons: reasons[-1]),
        ):
            policies.append(
                {
                    case_id: (actions[action_index][0], reason_selector(cases[case_id]["reasons"])[0])
                    for case_id in CASES
                }
            )
        longest_action = max(actions, key=lambda action: len(action[1] + " " + action[2]))[0]
        policies.append(
            {
                case_id: (
                    longest_action,
                    max(cases[case_id]["reasons"], key=lambda reason: len(reason[1]))[0],
                )
                for case_id in CASES
            }
        )
        for policy in policies:
            self.assert_case(artifact(policy), 1, "VIOLATED")

    def test_visible_copy_avoids_caricature_shortcuts(self) -> None:
        source = (TASK_DIR / "input" / "app" / "app.py").read_text(encoding="utf-8").lower()
        for phrase in (
            "by itself is enough",
            "vp supports",
            "every positive experiment",
            "immediate decision necessary",
            "can never be useful",
            "any positive engagement direction",
            "one result below 0.05 establishes",
            "repeatedly inspect all 20",
            "instead of the registered",
            "although the protocol did not",
        ):
            self.assertNotIn(phrase, source)

    def test_uniform_random_action_reason_probability_is_low(self) -> None:
        key = yaml.safe_load((HERE / "answer_key.yaml").read_text(encoding="utf-8"))
        probability = 1.0
        for case_id in CASES:
            probability *= len(key["acceptable_pairs"][case_id]) / 16
        self.assertAlmostEqual(probability, 0.0029296875)

    def test_material_reasons_claim_confirmatory_validity_after_same_data_redefinition(self) -> None:
        source_path = TASK_DIR / "input" / "app" / "app.py"
        spec = importlib.util.spec_from_file_location("statistics_review_app_semantics", source_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cases = {case["id"]: case for case in module.CASES}
        self.assertIn("binding rollout population", cases["email"]["evidence"])
        self.assertIn("no alternative loss or utility rule", cases["catalog"]["evidence"])
        self.assertIn("untouched remaining 60%", cases["recommender"]["evidence"])
        self.assertIn("Pooling stages was not registered", cases["recommender"]["evidence"])
        email = dict(cases["email"]["reasons"])
        catalog = dict(cases["catalog"]["reasons"])
        recommender = dict(cases["recommender"]["reasons"])
        self.assertIn("same run", email["em_vp"].lower())
        self.assertIn("confirmatory target", email["em_vp"].lower())
        self.assertIn("after seeing", catalog["ca_point"].lower())
        self.assertIn("confirmatory success", catalog["ca_point"].lower())
        self.assertIn("this interim read", catalog["ca_deadline"].lower())
        self.assertIn("protocol-valid evidence", catalog["ca_deadline"].lower())
        self.assertIn("one effective test", recommender["rc_users"].lower())
        self.assertIn("untouched-stage confirmation", recommender["rc_users"].lower())
        self.assertIn("honor the registered split", recommender["rc_multiplicity"].lower())

    def test_changed_selection_valid_and_tampered_event_fails(self) -> None:
        changed = artifact()
        submit = changed["events"].pop()
        changed["events"].append(
            {"event": "select_action", "caseId": "email", "actionId": "act_reject"}
        )
        changed["events"].append(
            {"event": "select_action", "caseId": "email", "actionId": "act_launch"}
        )
        changed["events"].append(submit)
        self.assert_case(changed, 0, "HELD")

        tampered = artifact()
        for event in reversed(tampered["events"]):
            if event.get("event") == "select_reason" and event.get("caseId") == "catalog":
                event["reasonId"] = "ca_point"
                break
        self.assert_case(tampered, 2, "ERROR")

    def test_missing_open_case_and_tampered_digest_are_errors(self) -> None:
        missing_open = artifact()
        missing_open["events"].remove({"event": "open_case", "caseId": "catalog"})
        self.assert_case(missing_open, 2, "ERROR")
        bad_digest = artifact()
        bad_digest["contentDigest"] = "0" * 64
        self.assert_case(bad_digest, 2, "ERROR")

    def test_missing_malformed_empty_partial_duplicate_cross_unknown_are_errors(self) -> None:
        code, result = self.run_case(None, write_file=False)
        self.assertEqual((code, result["verdict"]), (2, "ERROR"))
        code, result = self.run_case(None, raw="{bad")
        self.assertEqual((code, result["verdict"]), (2, "ERROR"))
        empty = artifact({})
        self.assert_case(empty, 2, "ERROR")
        partial = artifact({"email": BEST["email"], "catalog": BEST["catalog"]})
        self.assert_case(partial, 2, "ERROR")
        duplicate = artifact()
        duplicate["reviews"][1]["caseId"] = "email"
        self.assert_case(duplicate, 2, "ERROR")
        cross = artifact()
        cross["reviews"][0]["reasonId"] = "ca_interval"
        self.assert_case(cross, 2, "ERROR")
        unknown = artifact()
        unknown["reviews"][0]["actionId"] = "act_guess"
        self.assert_case(unknown, 2, "ERROR")

    def test_not_submitted_extra_wrong_type_and_overflow_are_errors(self) -> None:
        self.assert_case(artifact(submitted=False), 2, "ERROR")
        extra = artifact()
        extra["answerKey"] = "injected"
        self.assert_case(extra, 2, "ERROR")
        wrong = artifact()
        wrong["reviews"][0]["actionId"] = 1
        self.assert_case(wrong, 2, "ERROR")
        overflow = artifact()
        overflow["events"] = overflow["events"][:-1] + [
            {"event": "open_case", "caseId": "email"}
        ] * 250 + [{"event": "submit"}]
        self.assert_case(overflow, 2, "ERROR")


class AppSourceTests(unittest.TestCase):
    def test_input_and_environment_sources_are_byte_identical(self) -> None:
        input_source = TASK_DIR / "input" / "app" / "app.py"
        environment_source = TASK_DIR / "environment" / "app.py"
        self.assertEqual(input_source.read_bytes(), environment_source.read_bytes())

    def test_visible_content_digest_and_no_embedded_answer_key(self) -> None:
        source_path = TASK_DIR / "input" / "app" / "app.py"
        spec = importlib.util.spec_from_file_location("statistics_review_app", source_path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(
            module.content_digest(),
            "364d202e49a31dfae60c56e5a74ca6c596abecb314550dca25c8a09eb2b601d8",
        )
        source = source_path.read_text(encoding="utf-8")
        for hidden_token in ("action_tiers", "reason_tiers", "acceptable_pairs", "worst_tier"):
            self.assertNotIn(hidden_token, source)


if __name__ == "__main__":
    unittest.main()
