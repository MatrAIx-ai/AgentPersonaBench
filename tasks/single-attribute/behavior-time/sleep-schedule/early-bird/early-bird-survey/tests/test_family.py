#!/usr/bin/env python3
"""Offline regression tests for the rule-based Early Bird surfaces."""
from __future__ import annotations

import ast
import json
import itertools
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from html.parser import HTMLParser

import yaml

HERE = Path(__file__).resolve().parent
FAMILY_ROOT = HERE.parents[1]
MISSING = object()
MOCK_LLM_CLIENT = '''
import os

def chat(*args, **kwargs):
    if os.environ.get("MOCK_JUDGE_ERROR"):
        raise RuntimeError("simulated unavailable judge")
    return os.environ["MOCK_JUDGE_RESPONSE"]
'''


def _clock_minutes(text: str) -> int:
    """Parse displayed clock times instead of treating all PM choices alike."""
    match = re.fullmatch(r"(0?[1-9]|1[0-2]):([0-5]\d)\s+(AM|PM)", text.strip())
    if match is None:
        raise AssertionError(f"Invalid visible clock time: {text!r}")
    hour, minute, period = match.groups()
    return (int(hour) % 12) * 60 + int(minute) + (720 if period == "PM" else 0)


def _app_activities(source: Path) -> list[dict]:
    """Exercise the app's actual catalogue loading without importing its GUI."""
    tree = ast.parse(source.read_text(encoding="utf-8"))
    statements = [
        node for node in tree.body
        if (isinstance(node, ast.FunctionDef) and node.name in {"_schedule_path", "_load_activities"})
        or (isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in {"ACTIVITIES", "DATA"}
            for target in node.targets
        ))
    ]
    namespace = {"__file__": str(source), "Path": Path, "json": json, "os": os}
    exec(compile(ast.Module(body=statements, type_ignores=[]), str(source), "exec"), namespace)
    data = namespace.get("ACTIVITIES", namespace.get("DATA"))
    if isinstance(data, dict):
        data = data.get("activities")
    if not isinstance(data, list) or not data:
        raise AssertionError(f"No activity catalogue loaded from {source}")
    return data


def _run(
    task_name: str,
    artifact_name: str,
    artifact: object,
    *,
    judge_response: str | None = None,
    judge_error: bool = False,
) -> tuple[int, dict, str, str]:
    task = FAMILY_ROOT / task_name
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp).resolve()
        verified = output / "verified"
        artifact_path = output / artifact_name
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(artifact, bytes):
            artifact_path.write_bytes(artifact)
        elif artifact is not MISSING:
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
        env = {
            **os.environ,
            "ADHERENCE_OUTPUT_DIR": str(output),
            "ADHERENCE_VERIFIER_DIR": str(verified),
        }
        if judge_response is not None or judge_error:
            stub = output / "stub"
            stub.mkdir()
            (stub / "llm_client.py").write_text(MOCK_LLM_CLIENT, encoding="utf-8")
            (stub / "sitecustomize.py").write_text("import llm_client\n", encoding="utf-8")
            existing_pythonpath = env.get("PYTHONPATH")
            env["PYTHONPATH"] = (
                str(stub) + (os.pathsep + existing_pythonpath if existing_pythonpath else "")
            )
            env["MOCK_JUDGE_RESPONSE"] = judge_response or ""
            env["MOCK_JUDGE_ERROR"] = "1" if judge_error else ""
        proc = subprocess.run(
            [sys.executable, str(task / "tests" / "verifier.py")],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        structured = verified / "structured_output.json"
        if not structured.is_file():
            raise AssertionError(
                f"verifier wrote no structured output (exit {proc.returncode}):\n"
                f"{proc.stdout}{proc.stderr}"
            )
        result = json.loads(structured.read_text(encoding="utf-8"))
        reward = verified / "reward.txt"
        if not reward.is_file():
            raise AssertionError(
                f"verifier wrote no reward output (exit {proc.returncode}):\n"
                f"{proc.stdout}{proc.stderr}"
            )
        return (
            proc.returncode,
            result,
            proc.stdout + proc.stderr,
            reward.read_text(encoding="utf-8"),
        )


def _cases(*, contradiction: bool = False, malformed: bool = False):
    activity_id: object = [] if malformed else "language"
    schedules = [
        {"activityId": activity_id, "slotId": "lang-a" if contradiction else "lang-b"},
        {"activityId": "planning", "slotId": "plan-d"},
        {"activityId": "mobility", "slotId": "move-c"},
    ]
    answers = [
        {"questionId": [] if malformed else "q1", "selectedOptionId": "q1c" if contradiction else "q1b"},
        {"questionId": "q2", "selectedOptionId": "q2d"},
        {"questionId": "q3", "selectedOptionId": "q3c"},
        {"questionId": "q4", "selectedOptionId": "q4d"},
    ]
    return (
        ("early-bird-app", "schedule.json", {"selections": schedules}),
        ("early-bird-web", "schedule.json", {"selections": schedules}),
        ("early-bird-survey", "survey_result.json", {"answers": answers}),
    )


class EarlyBirdFamilyTests(unittest.TestCase):
    def test_visible_catalogs_and_exhaustive_discrimination(self) -> None:
        class Slots(HTMLParser):
            def __init__(self):
                super().__init__()
                self.options = {}
                self.option_ids = []
                self.current = None

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "button" and "data-slot" in attrs:
                    self.current = (attrs["data-activity"], attrs["data-slot"])
                    self.option_ids.append(self.current)

            def handle_data(self, data):
                if self.current is not None:
                    self.options[self.current] = data.strip()

            def handle_endtag(self, tag):
                if tag == "button":
                    self.current = None

        parser = Slots()
        parser.feed((FAMILY_ROOT / "early-bird-web/input/site/index.html").read_text(encoding="utf-8"))
        self.assertEqual(len(parser.option_ids), len(set(parser.option_ids)))
        schedule = json.loads(
            (FAMILY_ROOT / "early-bird-app/environment/schedule.json").read_text(encoding="utf-8")
        )
        # The shipped input app and the Docker runtime must load the same data
        # that the visible-catalogue test compares with the web page.
        for source in ("input/app/app.py", "environment/app.py"):
            self.assertEqual(
                _app_activities(FAMILY_ROOT / "early-bird-app" / source),
                schedule["activities"],
            )
        self.assertEqual(
            len(schedule["activities"]),
            len({activity["id"] for activity in schedule["activities"]}),
        )
        app_options = {
            (activity["id"], slot["id"]): slot["time"]
            for activity in schedule["activities"] for slot in activity["slots"]
        }
        self.assertEqual(len(app_options), sum(len(activity["slots"]) for activity in schedule["activities"]))
        self.assertEqual(app_options, parser.options)
        questionnaire = yaml.safe_load(
            (FAMILY_ROOT / "early-bird-survey/input/questionnaire.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(
            len(questionnaire["questions"]),
            len({question["id"] for question in questionnaire["questions"]}),
        )
        survey_options = {
            (question["id"], option["id"]): option["text"]
            for question in questionnaire["questions"] for option in question["options"]
        }
        self.assertEqual(len(survey_options), sum(len(question["options"]) for question in questionnaire["questions"]))
        for task_name, artifact_name, _ in _cases():
            with self.subTest(task=task_name):
                key = yaml.safe_load(
                    (FAMILY_ROOT / task_name / "tests/answer_key.yaml").read_text(encoding="utf-8")
                )["option_values"]
                visible = survey_options if task_name.endswith("survey") else app_options
                expected_labels = {
                    (group, option): value
                    for group, options in key.items() for option, value in options.items()
                }
                self.assertEqual(set(expected_labels), set(visible))
                for group, options in key.items():
                    times = [_clock_minutes(visible[(group, option)]) for option in options]
                    self.assertEqual(len(times), len(set(times)), f"{task_name}/{group} repeats a visible time")
                for option, label in expected_labels.items():
                    # These are authored contrast windows, not a universal
                    # chronotype boundary: morning versus 10 PM or later.
                    minute = _clock_minutes(visible[option])
                    self.assertIn(label, {"Early bird", "Night owl"})
                    if label == "Early bird":
                        self.assertLess(minute, 9 * 60, (task_name, option, visible[option]))
                    else:
                        self.assertGreaterEqual(minute, 22 * 60, (task_name, option, visible[option]))
                        self.assertLess(minute, 24 * 60, (task_name, option, visible[option]))
                keys = list(key)
                count = passed = 0
                for picks in itertools.product(*(key[group] for group in keys)):
                    if task_name.endswith("survey"):
                        artifact = {"answers": [
                            {"questionId": group, "selectedOptionId": option}
                            for group, option in zip(keys, picks)
                        ]}
                    else:
                        artifact = {"selections": [
                            {"activityId": group, "slotId": option}
                            for group, option in zip(keys, picks)
                        ]}
                    expected = all(key[group][option] == "Early bird" for group, option in zip(keys, picks))
                    code, result, output, reward = _run(task_name, artifact_name, artifact)
                    self.assertEqual(code, 0 if expected else 1, output)
                    self.assertEqual(result["verdict"], "HELD" if expected else "VIOLATED")
                    self.assertEqual(result["reward"], float(expected))
                    self.assertEqual(reward, f"{float(expected)}\n")
                    count += 1
                    passed += expected
                self.assertEqual((passed, count), (1, 64))

    def test_chat_catalogue_and_judge_describe_the_same_two_slots(self) -> None:
        task = FAMILY_ROOT / "early-bird-chat"
        verifier = ast.parse((task / "tests/verifier.py").read_text(encoding="utf-8"))
        prompt_node = next(
            node.value for node in verifier.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "JUDGE_PROMPT" for target in node.targets)
        )
        prompt = ast.literal_eval(prompt_node)
        sources = {
            "bot": (task / "input/bot.md").read_text(encoding="utf-8"),
            "context": (task / "input/context.md").read_text(encoding="utf-8"),
            "judge": prompt,
        }
        for name, source in sources.items():
            with self.subTest(source=name):
                times = re.findall(r"(?<!\d)(?:0?[1-9]|1[0-2]):[0-5]\d\s+(?:AM|PM)\b", source)
                self.assertEqual({_clock_minutes(value) for value in times}, {7 * 60 + 30, 22 * 60})
        # Inspect the fixed rubric; these checks make no model call and do not
        # assume that a model or persona will choose either offered slot.
        normalized_prompt = " ".join(prompt.split())
        self.assertRegex(normalized_prompt, r"HELD only if[^.]*7:30 AM")
        self.assertRegex(normalized_prompt, r"VIOLATED if[^.]*10:00 PM")

    def test_only_all_early_bird_choices_hold(self) -> None:
        for task_name, artifact_name, artifact in _cases():
            with self.subTest(task=task_name):
                code, result, output, _ = _run(task_name, artifact_name, artifact)
                self.assertEqual(code, 0, output)
                self.assertEqual(result["reward"], 1.0)
                self.assertTrue(all(item["observed"] == "Early bird" for item in result["criteria"]))

    def test_one_contradictory_choice_violates(self) -> None:
        for task_name, artifact_name, artifact in _cases(contradiction=True):
            with self.subTest(task=task_name):
                code, result, output, _ = _run(task_name, artifact_name, artifact)
                self.assertEqual(code, 1, output)
                self.assertEqual(result["reward"], 0.0)
                self.assertEqual(result["verdict"], "VIOLATED")

    def test_rule_surfaces_fail_closed_on_non_string_ids(self) -> None:
        for task_name, artifact_name, artifact in _cases(malformed=True):
            with self.subTest(task=task_name):
                code, result, output, _ = _run(task_name, artifact_name, artifact)
                self.assertEqual(code, 1, output)
                self.assertEqual(result["reward"], 0.0)
                self.assertIn("must be strings", result["detail"])

    def test_all_surfaces_fail_closed_on_non_object_json_roots(self) -> None:
        surfaces = (
            ("early-bird-app", "schedule.json"),
            ("early-bird-web", "schedule.json"),
            ("early-bird-survey", "survey_result.json"),
            ("early-bird-chat", "user_turns.json"),
        )
        for task_name, artifact_name in surfaces:
            for root in ([], None, "not an object", 7):
                with self.subTest(task=task_name, root=root):
                    code, result, output, reward = _run(
                        task_name,
                        artifact_name,
                        root,
                        judge_response="HELD",
                    )
                    self.assertEqual(code, 1, output)
                    self.assertEqual(result["reward"], 0.0)
                    self.assertEqual(reward, "0.0\n")

    def test_missing_empty_and_invalid_artifact_files_write_durable_zero(self) -> None:
        surfaces = [(name, artifact_name) for name, artifact_name, _ in _cases()]
        surfaces.append(("early-bird-chat", "user_turns.json"))
        for task_name, artifact_name in surfaces:
            for artifact in (MISSING, b"", b"{", b"\xff\xfe"):
                with self.subTest(task=task_name, artifact=artifact):
                    code, result, output, reward = _run(
                        task_name, artifact_name, artifact, judge_response="HELD"
                    )
                    self.assertEqual(code, 1, output)
                    self.assertEqual(result["reward"], 0.0)
                    self.assertEqual(reward, "0.0\n")

    def test_incomplete_duplicate_unknown_and_wrong_type_choices_fail_closed(self) -> None:
        for task_name, artifact_name, artifact in _cases():
            field = "answers" if task_name.endswith("survey") else "selections"
            id_field = "questionId" if field == "answers" else "activityId"
            option_field = "selectedOptionId" if field == "answers" else "slotId"
            choices = artifact[field]
            invalid = [None, {}, [], choices[:-1], choices + [choices[0]], [None] + choices[1:]]
            for value in ([], {}, 7, True, None, "unknown"):
                invalid.extend([
                    [{**choices[0], id_field: value}] + choices[1:],
                    [{**choices[0], option_field: value}] + choices[1:],
                ])
            for choices in invalid:
                with self.subTest(task=task_name, choices=choices):
                    code, result, output, reward = _run(task_name, artifact_name, {field: choices})
                    self.assertEqual(code, 1, output)
                    self.assertEqual(result["reward"], 0.0)
                    self.assertEqual(reward, "0.0\n")

    def test_chat_requires_actual_user_messages_before_judging(self) -> None:
        for turns in (None, {}, [], [""], [" \n\t"], [None], [7], ["Morning please", ""]):
            with self.subTest(turns=turns):
                code, result, output, reward = _run(
                    "early-bird-chat", "user_turns.json", {"turns": turns}, judge_response="HELD"
                )
                self.assertEqual(code, 1, output)
                self.assertEqual(result["reward"], 0.0)
                self.assertEqual(reward, "0.0\n")

    def test_chat_judge_failure_writes_durable_zero_without_a_verdict(self) -> None:
        code, result, output, reward = _run(
            "early-bird-chat", "user_turns.json", {"turns": ["Please book 7:30 AM."]},
            judge_error=True,
        )
        self.assertEqual(code, 1, output)
        self.assertEqual(result["reward"], 0.0)
        self.assertEqual(reward, "0.0\n")
        self.assertNotIn("verdict", result)
        self.assertEqual(result["detail"], "judge call failed (RuntimeError)")

    def test_chat_rejects_explanations_and_mixed_verdict_text(self) -> None:
        for response in (
            "Not HELD; the verdict is VIOLATED.",
            "HELD\n\nThe user clearly and repeatedly prefers the 7:30 AM slot.",
            "VIOLATED\n\nThe user accepts the evening slot.",
        ):
            with self.subTest(response=response):
                code, result, output, reward = _run(
                    "early-bird-chat",
                    "user_turns.json",
                    {"turns": ["Please book the 7:30 AM session."]},
                    judge_response=response,
                )
                self.assertEqual(code, 1, output)
                self.assertEqual(result["reward"], 0.0)
                self.assertEqual(reward, "0.0\n")
                self.assertNotIn("verdict", result)
                self.assertIn("did not return HELD/VIOLATED", result["detail"])

    def test_chat_accepts_only_whitespace_and_case_around_verdict(self) -> None:
        cases = ((" \nheld\t", 0, "HELD", 1.0), ("\tViOlAtEd\n", 1, "VIOLATED", 0.0))
        for response, expected_code, expected_verdict, expected_reward in cases:
            with self.subTest(response=response):
                code, result, output, reward = _run(
                    "early-bird-chat",
                    "user_turns.json",
                    {"turns": ["Please book the 7:30 AM session."]},
                    judge_response=response,
                )
                self.assertEqual(code, expected_code, output)
                self.assertEqual(result["verdict"], expected_verdict)
                self.assertEqual(result["reward"], expected_reward)
                self.assertEqual(reward, f"{expected_reward}\n")

    def test_web_solver_stages_driver_and_records_forwarded_model(self) -> None:
        solver = (
            FAMILY_ROOT / "early-bird-web" / "solution" / "solve.sh"
        ).read_text(encoding="utf-8")
        self.assertNotIn("mktemp /tmp", solver)
        self.assertIn('DRIVER="$(mktemp "$OUTPUT_DIR/', solver)
        self.assertNotIn('-v "$DRIVER:', solver)
        self.assertIn('python3 "$DRIVER_CONTAINER"', solver)
        self.assertIn("LLM_MODEL:?", solver)
        self.assertIn('-e LLM_MODEL="$LLM_MODEL"', solver)
        self.assertIn('os.environ["LLM_MODEL"]', solver)
        self.assertNotIn('os.environ.get("LLM_MODEL"', solver)

    def test_native_launcher_targets_the_agent_display_without_maximizing(self) -> None:
        task = FAMILY_ROOT / "early-bird-app"
        launcher = (task / "environment" / "start-app.sh").read_text(encoding="utf-8")
        self.assertIn('APP_DISPLAY:-:1', launcher)
        self.assertIn("xdpyinfo", launcher)
        self.assertNotIn("pgrep -f", launcher)
        self.assertNotIn("maximized_", launcher)
        environment_app = task / "environment" / "app.py"
        input_app = task / "input" / "app" / "app.py"
        self.assertEqual(environment_app.read_bytes(), input_app.read_bytes())
        self.assertNotIn('attributes("-zoomed"', environment_app.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
