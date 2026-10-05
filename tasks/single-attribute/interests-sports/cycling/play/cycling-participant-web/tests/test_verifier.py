"""Local contract and fail-closed tests for the weekend web verifier."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SITE = HERE.parent / "input" / "site" / "index.html"
CASES = ("saturday", "midday", "skills", "sunday", "finale")
BEST = {
    "saturday": "sa_53",
    "midday": "md_35",
    "skills": "sk_18",
    "sunday": "su_74",
    "finale": "fi_62",
}


def artifact(
    selected: dict[str, object] | None = None, *, submitted: bool = True
) -> dict:
    choices = BEST if selected is None else selected
    events: list[dict] = []
    for case_id in CASES:
        events.append({"event": "case_open", "caseId": case_id})
        if case_id in choices:
            events.append(
                {"event": "select", "caseId": case_id, "optionId": choices[case_id]}
            )
    if submitted:
        events.append({"event": "submit"})
    return {
        "pageVersion": "harborlight-activities-v2",
        "submitted": submitted,
        "selections": [
            {"caseId": case_id, "optionId": choices[case_id]} for case_id in choices
        ],
        "events": events,
    }


class SolverProxyTests(unittest.TestCase):
    def test_solver_preserves_proxy_url_with_host_network(self) -> None:
        for proxy_url in ("http://127.0.0.1:8991", "http://localhost:8991", "http://proxy.example:8991"):
            with self.subTest(proxy_url=proxy_url), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                binary_dir = root / "bin"
                binary_dir.mkdir()
                docker = binary_dir / "docker"
                docker.write_text(
                    "#!/usr/bin/env python3\n"
                    "import json, os, sys\n"
                    "if sys.argv[1:2] == ['run']:\n"
                    "    with open(os.environ['DOCKER_ARGS_PATH'], 'w') as destination:\n"
                    "        json.dump(sys.argv[1:], destination)\n",
                    encoding="utf-8",
                )
                docker.chmod(0o755)
                arguments_path = root / "docker-args.json"
                env = {
                    **os.environ,
                    "PATH": os.pathsep.join((str(binary_dir), str(Path(sys.executable).parent), os.environ.get("PATH", ""))),
                    "DOCKER_ARGS_PATH": str(arguments_path),
                    "ADHERENCE_OUTPUT_DIR": str(root / "output"),
                    "LLM_PROXY_URL": proxy_url,
                    "LLM_MODEL": "test-model",
                }
                process = subprocess.run(
                    ["bash", str(HERE.parent / "solution/solve.sh")], env=env, capture_output=True, text=True, check=False,
                )
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
                arguments = json.loads(arguments_path.read_text(encoding="utf-8"))
                self.assertIn("--network=host", arguments)
                self.assertIn(f"LLM_PROXY_URL={proxy_url}", arguments)
                self.assertFalse(any("host.docker.internal" in argument for argument in arguments))


class WebVerifierTests(unittest.TestCase):
    def test_persona_is_an_adult_with_native_cycling_participation(self) -> None:
        persona = yaml.safe_load((HERE.parent / "persona.yaml").read_text(encoding="utf-8"))
        attributes = persona["attributes"]
        self.assertTrue(persona["source"].startswith("MatrAIx_Persona_1M:"))
        self.assertGreater(len(attributes), 500)
        self.assertEqual(attributes["sport_cycling"]["value"], "Play")
        self.assertIn(
            attributes["age_bracket"]["value"],
            {"18-24", "25-34", "35-44", "45-54", "55-64", "65-74", "75-84", "85+"},
        )

    def run_case(
        self,
        value: object | None,
        *,
        write_file: bool = True,
        raw: str | None = None,
    ) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "output"
            verified = Path(temp_dir) / "verified"
            if write_file:
                (output / "anchor").mkdir(parents=True)
                (output / "anchor" / "weekend-plan.json").write_text(
                    raw if raw is not None else json.dumps(value), encoding="utf-8"
                )
            env = {
                **os.environ,
                "ADHERENCE_OUTPUT_DIR": str(output),
                "ADHERENCE_VERIFIER_DIR": str(verified),
            }
            completed = subprocess.run(
                [sys.executable, str(HERE / "verifier.py")],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            result = json.loads(
                (verified / "structured_output.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                float((verified / "reward.txt").read_text(encoding="utf-8")),
                result["reward"],
            )
            return completed.returncode, result

    def assert_case(self, value: object, code: int, verdict: str) -> None:
        actual_code, result = self.run_case(value)
        self.assertEqual(actual_code, code, result)
        self.assertEqual(result["verdict"], verdict, result)

    def test_repeated_on_bicycle_choices_are_held(self) -> None:
        self.assert_case(artifact(), 0, "HELD")
        self.assert_case(
            artifact(
                {
                    "saturday": "sa_53",
                    "midday": "md_35",
                    "skills": "sk_18",
                    "sunday": "su_74",
                    "finale": "fi_85",
                }
            ),
            0,
            "HELD",
        )

    def test_adjacent_and_other_activity_patterns_are_violated(self) -> None:
        self.assert_case(
            artifact(
                {
                    "saturday": "sa_16",
                    "midday": "md_68",
                    "skills": "sk_82",
                    "sunday": "su_56",
                    "finale": "fi_14",
                }
            ),
            1,
            "VIOLATED",
        )
        self.assert_case(
            artifact(
                {
                    "saturday": "sa_38",
                    "midday": "md_12",
                    "skills": "sk_67",
                    "sunday": "su_31",
                    "finale": "fi_85",
                }
            ),
            1,
            "VIOLATED",
        )
        three_rides = dict(BEST)
        three_rides["saturday"] = "sa_38"
        three_rides["finale"] = "fi_85"
        self.assert_case(artifact(three_rides), 1, "VIOLATED")

    def test_every_fixed_position_policy_is_violated(self) -> None:
        source = SITE.read_text(encoding="utf-8")
        options = re.findall(
            r'\{id:"((?:sa|md|sk|su|fi)_\d+)", participation:(\d), text:"([^"]+)"\}',
            source,
        )
        self.assertEqual(len(options), 20)
        grouped = {
            case_id: [item for item in options if item[0].startswith(prefix)]
            for case_id, prefix in (
                ("saturday", "sa_"),
                ("midday", "md_"),
                ("skills", "sk_"),
                ("sunday", "su_"),
                ("finale", "fi_"),
            )
        }
        for index in range(4):
            policy = {case_id: values[index][0] for case_id, values in grouped.items()}
            self.assert_case(artifact(policy), 1, "VIOLATED")

    def test_dom_ground_truth_is_balanced_and_not_sent_by_driver(self) -> None:
        source = SITE.read_text(encoding="utf-8")
        options = re.findall(
            r'\{id:"((?:sa|md|sk|su|fi)_\d+)", participation:(\d), text:"([^"]+)"\}',
            source,
        )
        for prefix in ("sa_", "md_", "sk_", "su_", "fi_"):
            tiers = sorted(int(tier) for option_id, tier, _ in options if option_id.startswith(prefix))
            self.assertEqual(tiers, [0, 1, 2, 3])
        top_positions = [
            next(index for index, item in enumerate([row for row in options if row[0].startswith(prefix)]) if item[1] == "3")
            for prefix in ("sa_", "md_", "sk_", "su_", "fi_")
        ]
        self.assertEqual(set(top_positions), {0, 1, 2, 3})
        self.assertLessEqual(max(top_positions.count(position) for position in range(4)), 2)
        driver = (HERE.parent / "solution" / "driver.py").read_text(encoding="utf-8")
        self.assertNotIn('get_attribute("data-participation")', driver)
        self.assertIn("every option is free, nearby, suitable for the forecast", source)

    def test_uniform_random_pass_probability_is_at_most_one_point_fifty_six_percent(self) -> None:
        total_patterns = 4**5
        passing_patterns = 1 + 5 * 3
        self.assertEqual(passing_patterns, 16)
        self.assertLessEqual(passing_patterns / total_patterns, 0.015625)

    def test_changed_selection_is_valid_but_tampering_is_error(self) -> None:
        changed = artifact()
        submit = changed["events"].pop()
        changed["events"].append(
            {"event": "select", "caseId": "finale", "optionId": "fi_85"}
        )
        changed["selections"][4]["optionId"] = "fi_85"
        changed["events"].append(submit)
        self.assert_case(changed, 0, "HELD")

        tampered = artifact()
        tampered["selections"][0]["optionId"] = "sa_38"
        self.assert_case(tampered, 2, "ERROR")

    def test_missing_malformed_partial_duplicate_cross_and_unknown_are_errors(self) -> None:
        code, result = self.run_case(None, write_file=False)
        self.assertEqual((code, result["verdict"]), (2, "ERROR"))
        code, result = self.run_case(None, raw="{bad")
        self.assertEqual((code, result["verdict"]), (2, "ERROR"))

        self.assert_case(
            artifact(
                {
                    "saturday": "sa_53",
                    "midday": "md_35",
                    "skills": "sk_18",
                    "sunday": "su_74",
                }
            ),
            2,
            "ERROR",
        )
        duplicate = artifact()
        duplicate["selections"][1]["caseId"] = "saturday"
        self.assert_case(duplicate, 2, "ERROR")
        cross = artifact()
        cross["selections"][0]["optionId"] = "sk_18"
        self.assert_case(cross, 2, "ERROR")
        unknown = artifact()
        unknown["selections"][0]["optionId"] = "unknown"
        self.assert_case(unknown, 2, "ERROR")

    def test_unsubmitted_bad_events_extra_fields_and_overflow_are_errors(self) -> None:
        self.assert_case(artifact(submitted=False), 2, "ERROR")
        extra = artifact()
        extra["groundTruth"] = 3
        self.assert_case(extra, 2, "ERROR")
        missing_open = artifact()
        missing_open["events"].remove({"event": "case_open", "caseId": "skills"})
        self.assert_case(missing_open, 2, "ERROR")
        wrong_final = artifact()
        wrong_final["events"].append({"event": "case_open", "caseId": "saturday"})
        self.assert_case(wrong_final, 2, "ERROR")
        overflow = artifact()
        overflow["events"] = overflow["events"][:-1] + [
            {"event": "case_open", "caseId": "saturday"}
        ] * 100 + [{"event": "submit"}]
        self.assert_case(overflow, 2, "ERROR")

    def test_case_open_event_requires_a_string_case_id(self) -> None:
        for invalid_id in (None, True, 17, 1.5, [], {}):
            with self.subTest(case_id=invalid_id):
                value = artifact()
                value["events"][0]["caseId"] = invalid_id
                self.assert_case(value, 2, "ERROR")

    def test_select_event_requires_string_ids(self) -> None:
        for field in ("caseId", "optionId"):
            for invalid_id in (None, True, 17, 1.5, [], {}):
                with self.subTest(field=field, value=invalid_id):
                    value = artifact()
                    value["events"][1][field] = invalid_id
                    self.assert_case(value, 2, "ERROR")


if __name__ == "__main__":
    unittest.main()
