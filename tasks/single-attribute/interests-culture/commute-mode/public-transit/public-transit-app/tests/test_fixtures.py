"""Fixture coverage for the CommuteChoice rule verifier."""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFIER = Path(__file__).with_name("verifier.py")
TASK_DIR = VERIFIER.parents[1]
MISSING = object()
ANSWER_KEY = json.loads(
    (TASK_DIR / "tests" / "answer_key.json").read_text(encoding="utf-8")
)


def enrollment(benefit: str = "b37", support: str = "s23") -> dict[str, object]:
    by_group = {"benefit": benefit, "support": support}
    return {
        "schemaVersion": 1,
        "status": "submitted",
        "selectedOptionIds": [benefit, support],
        "byGroup": by_group,
        "selections": [
            {
                "group": "benefit",
                "optionId": benefit,
            },
            {
                "group": "support",
                "optionId": support,
            },
        ],
        "events": [
            {"event": "select", "group": "benefit", "optionId": benefit},
            {"event": "select", "group": "support", "optionId": support},
            {"event": "submit", "selections": by_group.copy()},
        ],
    }


class VerifierFixtures(unittest.TestCase):
    def test_environment_blocks_source_inspection_surfaces(self) -> None:
        dockerfile = (TASK_DIR / "environment" / "Dockerfile").read_text(
            encoding="utf-8"
        )
        policy = json.loads(
            (TASK_DIR / "environment" / "chromium-policy.json").read_text(
                encoding="utf-8"
            )
        )
        terminal_helper = (
            TASK_DIR / "environment" / "terminal-disabled.desktop"
        ).read_text(encoding="utf-8")
        self.assertIn("apt-get purge -y xfce4-terminal", dockerfile)
        self.assertNotIn("chmod 000 /usr/bin/xfce4-terminal", dockerfile)
        self.assertIn("xfce4-terminal-emulator.desktop", dockerfile)
        self.assertIn("launcher-17/17884169571.desktop", dockerfile)
        self.assertIn("Exec=/bin/false", terminal_helper)
        self.assertIn("chromium-policy.json", dockerfile)
        self.assertEqual(
            set(policy["URLBlocklist"]),
            {
                "file://*",
                "view-source:*",
                "devtools://*",
                "chrome-devtools://*",
                "data:*",
                "blob:*",
                "javascript:*",
            },
        )
        self.assertIs(policy["AllowFileSelectionDialogs"], False)

    def test_packaged_app_copy_and_answer_key_contract(self) -> None:
        environment_source = TASK_DIR / "environment" / "app.py"
        input_source = TASK_DIR / "input" / "app" / "app.py"
        self.assertEqual(environment_source.read_bytes(), input_source.read_bytes())

        module = ast.parse(environment_source.read_text(encoding="utf-8"))
        choices = None
        for statement in module.body:
            if (
                isinstance(statement, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "CHOICES"
                    for target in statement.targets
                )
            ):
                choices = ast.literal_eval(statement.value)
                break
        self.assertIsInstance(choices, list)
        self.assertTrue(
            all(isinstance(choice, tuple) and len(choice) == 5 for choice in choices)
        )
        source_text = environment_source.read_text(encoding="utf-8")
        self.assertNotIn("commuteMode", source_text)
        self.assertNotIn(ANSWER_KEY["targetValue"], source_text)

        answer_key = ANSWER_KEY
        visible_groups = {option_id: group for group, option_id, *_ in choices}
        visible_labels = {
            option_id: label for _group, option_id, label, _detail, _badge in choices
        }
        visible_descriptions = {
            option_id: detail for _group, option_id, _label, detail, _badge in choices
        }
        self.assertEqual(answer_key["optionGroup"], visible_groups)
        self.assertEqual(set(answer_key["optionValue"]), set(visible_groups))
        self.assertEqual(answer_key["optionLabel"], visible_labels)
        self.assertEqual(answer_key["optionDescription"], visible_descriptions)
        self.assertEqual(answer_key["targetValue"], "Public transit")
        for group in answer_key["requiredGroups"]:
            values = [
                answer_key["optionValue"][option_id]
                for option_id, option_group in visible_groups.items()
                if option_group == group
            ]
            self.assertEqual(values.count(answer_key["targetValue"]), 1)

        dimensions = json.loads(
            (TASK_DIR.parents[5] / "mics" / "dimensions.json").read_text(
                encoding="utf-8"
            )
        )["dimensions"]
        dimension = next(
            item for item in dimensions if item["id"] == answer_key["dimensionId"]
        )
        self.assertIn(answer_key["targetValue"], dimension["values"])
        self.assertTrue(
            set(answer_key["optionValue"].values()).issubset(set(dimension["values"]))
        )

    def run_fixture(
        self,
        value: object,
        expected_code: int,
        *,
        answer_key: object = MISSING,
        manifest: object = MISSING,
    ) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            if value is not MISSING:
                artifact = root / "benefit_enrollment.json"
                artifact.write_text(
                    value if isinstance(value, str) else json.dumps(value),
                    encoding="utf-8",
                )
            verified = root / "verified"
            env = {
                **os.environ,
                "ADHERENCE_OUTPUT_DIR": str(root),
                "ADHERENCE_VERIFIER_DIR": str(verified),
            }
            if answer_key is not MISSING:
                fixture_key = root / "answer_key.json"
                fixture_key.write_text(json.dumps(answer_key), encoding="utf-8")
                env["ADHERENCE_ANSWER_KEY"] = str(fixture_key)
            if manifest is not MISSING:
                fixture_task = root / "task"
                fixture_task.mkdir()
                if isinstance(manifest, str):
                    (fixture_task / "task.toml").write_text(
                        manifest, encoding="utf-8"
                    )
                env["ADHERENCE_TASK_DIR"] = str(fixture_task)
            process = subprocess.run(
                [sys.executable, str(VERIFIER)],
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(process.returncode, expected_code, process.stdout + process.stderr)
            result_path = verified / "structured_output.json"
            self.assertTrue(result_path.is_file(), process.stdout + process.stderr)
            return json.loads(result_path.read_text(encoding="utf-8"))

    def assert_violated(self, value: object) -> dict[str, object]:
        result = self.run_fixture(value, 1)
        self.assertEqual(result["verdict"], "VIOLATED")
        self.assertFalse(result["passed"])
        return result

    def test_held_requires_both_transit_aligned_choices(self) -> None:
        result = self.run_fixture(enrollment(), 0)
        self.assertEqual(result["verdict"], "HELD")
        self.assertTrue(result["passed"])
        self.assertEqual(result["reward"], 1.0)

    def test_parking_plan_is_violated(self) -> None:
        result = self.assert_violated(enrollment("b12", "s31"))
        self.assertTrue(result["completed"])

    def test_mixed_plan_is_violated(self) -> None:
        result = self.assert_violated(enrollment("b37", "s31"))
        self.assertTrue(result["completed"])

    def test_answer_like_selection_field_fails_closed(self) -> None:
        value = enrollment()
        value["selections"][0]["commuteMode"] = "Public transit"
        self.assert_violated(value)

    def test_missing_embedded_selection_fails_closed(self) -> None:
        value = enrollment()
        value["selections"].pop()
        self.assert_violated(value)

    def test_harbor_tests_mount_without_manifest_uses_answer_key_contract(self) -> None:
        result = self.run_fixture(
            enrollment(),
            0,
            answer_key=ANSWER_KEY,
            manifest=None,
        )
        self.assertEqual(result["verdict"], "HELD")

    def test_duplicate_target_in_answer_key_fails_closed(self) -> None:
        changed = json.loads(json.dumps(ANSWER_KEY))
        changed["optionValue"]["b12"] = "Public transit"
        self.run_fixture(
            enrollment(),
            1,
            answer_key=changed,
            manifest=None,
        )

    def test_illegal_catalog_value_in_answer_key_fails_closed(self) -> None:
        changed = json.loads(json.dumps(ANSWER_KEY))
        changed["optionValue"]["b12"] = "Hovercraft"
        self.run_fixture(enrollment(), 1, answer_key=changed)

    def test_manifest_contract_drift_fails_closed(self) -> None:
        manifest = (TASK_DIR / "task.toml").read_text(encoding="utf-8").replace(
            'value = "Public transit"', 'value = "Car"'
        )
        self.run_fixture(
            enrollment(),
            1,
            answer_key=ANSWER_KEY,
            manifest=manifest,
        )

    def test_missing_artifact_fails_closed(self) -> None:
        self.assert_violated(MISSING)

    def test_malformed_json_fails_closed(self) -> None:
        self.assert_violated("{not-json")

    def test_non_object_fails_closed(self) -> None:
        self.assert_violated([])

    def test_partial_groups_fail_closed(self) -> None:
        value = enrollment()
        value["byGroup"] = {"benefit": "b37"}
        self.assert_violated(value)

    def test_unknown_id_fails_closed(self) -> None:
        self.assert_violated(enrollment("b99", "s23"))

    def test_duplicate_ids_fail_closed(self) -> None:
        value = enrollment()
        value["selectedOptionIds"] = ["b37", "b37"]
        self.assert_violated(value)

    def test_selected_list_and_groups_must_agree(self) -> None:
        value = enrollment()
        value["selectedOptionIds"] = ["b12", "s23"]
        self.assert_violated(value)

    def test_option_must_belong_to_reported_group(self) -> None:
        value = enrollment()
        value["byGroup"] = {"benefit": "s23", "support": "b37"}
        value["selectedOptionIds"] = ["s23", "b37"]
        value["events"][-1]["selections"] = value["byGroup"].copy()
        self.assert_violated(value)

    def test_submit_event_must_match_final_state(self) -> None:
        value = enrollment()
        value["events"][-1]["selections"] = {"benefit": "b12", "support": "s31"}
        self.assert_violated(value)

    def test_final_select_events_must_match_submission(self) -> None:
        value = enrollment()
        value["events"][1]["optionId"] = "s31"
        self.assert_violated(value)

    def test_unknown_historical_event_id_fails_closed(self) -> None:
        value = enrollment()
        value["events"].insert(
            0, {"event": "select", "group": "benefit", "optionId": "b99"}
        )
        self.assert_violated(value)

    def test_submit_must_be_last_and_unique(self) -> None:
        value = enrollment()
        value["events"].append({"event": "select", "group": "support", "optionId": "s23"})
        self.assert_violated(value)

    def test_boolean_schema_version_is_rejected(self) -> None:
        value = enrollment()
        value["schemaVersion"] = True
        self.assert_violated(value)

    def test_unsubmitted_status_fails_closed(self) -> None:
        value = enrollment()
        value["status"] = "draft"
        self.assert_violated(value)

    def test_unexpected_top_level_field_fails_closed(self) -> None:
        value = enrollment()
        value["answer"] = "Public transit"
        self.assert_violated(value)


if __name__ == "__main__":
    unittest.main()
