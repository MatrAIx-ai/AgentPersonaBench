#!/usr/bin/env python3
"""Unit tests for the survey verifier.

Fully generic: every fixture is derived from input/questionnaire.yaml and
tests/answer_key.yaml, so nothing here needs editing per task. Two groups:

  SurveyVerifierTests   run tests/verifier.py as a subprocess against artifacts
                        written to a temp ADHERENCE_OUTPUT_DIR (adherent, one
                        violation, partial, duplicate, unknown/cross-question
                        ids, wrong types, extra keys, empty, malformed, missing)
                        and against deliberately broken copies of the task
                        (bad key / missing questionnaire) — all must fail
                        closed with a written zero and no traceback.
  TaskConfigurationTests  lint the shipped questionnaire + key against the
                        design rules (6 questions, 3-4 options, key coverage
                        and polarity, rule consistency, varied positions,
                        random full-marks bound, the cost record that shows the
                        adherent option is never the cheapest, and that the
                        review script reads the key the way the verifier does).

Run:  python3 -m unittest <task>/tests/test_verifier.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True  # keep tests/__pycache__ out of the task dir

import yaml  # noqa: E402  (host-side test; pyyaml is a runtime dependency anyway)

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
VERIFIER = HERE / "verifier.py"
QUESTIONNAIRE = TASK / "input" / "questionnaire.yaml"
ANSWER_KEY = HERE / "answer_key.yaml"

EXPECTED_QUESTION_COUNT = 6          # design rule for this wave
OPTIONS_PER_QUESTION = (3, 4)        # inclusive range
MAX_TWO_ADHERENT_QUESTIONS = 2       # at most this many questions may have two adherent options
MAX_RANDOM_FULL_MARKS = 0.01         # a persona-blind random answerer must pass <= 1 %

REQUIRED_OUTPUT_KEYS = {"reward", "verdict", "passed", "detail",
                        "selected_options", "violating_options"}


def _load_verifier_module():
    spec = importlib.util.spec_from_file_location("survey_verifier_under_test", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = _load_verifier_module()
KEY_NAME, FACT_KEY = MODULE.KEY_NAME, MODULE.FACT_KEY


def _questions() -> dict[str, list[str]]:
    doc = yaml.safe_load(QUESTIONNAIRE.read_text(encoding="utf-8"))
    return {q["id"]: [o["id"] for o in q["options"]] for q in doc["questions"]}


def _key() -> tuple[dict[str, bool], dict[str, object]]:
    doc = yaml.safe_load(ANSWER_KEY.read_text(encoding="utf-8"))
    return doc[KEY_NAME], doc[FACT_KEY]


QUESTIONS = _questions()
ADHERENT, FACTS = _key()
KEY_DOC = yaml.safe_load(ANSWER_KEY.read_text(encoding="utf-8"))
PRICE_KEY = "price_usd"   # host-side cost record, not scored; see tests/answer_key.yaml
PRICES = KEY_DOC.get(PRICE_KEY) if isinstance(KEY_DOC.get(PRICE_KEY), dict) else {}


def held_payload() -> dict:
    """One adherent option per question (the first one in display order)."""
    answers = []
    for qid, oids in QUESTIONS.items():
        good = [o for o in oids if ADHERENT.get(o) is True]
        answers.append({"questionId": qid, "selectedOptionId": good[0]})
    return {"answers": answers}


def non_adherent_option(qid: str) -> str:
    return next(o for o in QUESTIONS[qid] if ADHERENT.get(o) is False)


def run_verifier(out: Path, verdict: Path, verifier: Path = VERIFIER) -> tuple[int, dict, str]:
    env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(out), "ADHERENCE_VERIFIER_DIR": str(verdict),
           "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run([sys.executable, str(verifier)], env=env, text=True,
                          capture_output=True, check=False)
    # the verdict dir is where harbor looks; the output dir is the writer's
    # documented fallback for when something occupies the verdict path
    for target in (verdict, out):
        so = target / "structured_output.json"
        if so.is_file():
            break
    else:
        raise AssertionError(f"verifier wrote no structured_output.json\n{proc.stdout}\n{proc.stderr}")
    result = json.loads(so.read_text(encoding="utf-8"))
    reward_txt = (target / "reward.txt").read_text(encoding="utf-8")
    assert reward_txt == f"{result['reward']}\n", f"reward.txt {reward_txt!r} disagrees with {result['reward']}"
    return proc.returncode, result, proc.stderr


class SurveyVerifierTests(unittest.TestCase):
    def run_case(self, payload=None, raw=None, write_file=True):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out, verdict = root / "out", root / "verdict"
            out.mkdir()
            if write_file:
                text = raw if raw is not None else json.dumps(payload)
                (out / "survey_result.json").write_text(text, encoding="utf-8")
            return run_verifier(out, verdict)

    # -- assertion helpers ---------------------------------------------------
    def assert_shape(self, result: dict) -> None:
        self.assertTrue(REQUIRED_OUTPUT_KEYS <= set(result), result)
        self.assertIsInstance(result["selected_options"], dict)
        self.assertIsInstance(result["violating_options"], list)

    def assert_held(self, code: int, result: dict, stderr: str) -> None:
        self.assert_shape(result)
        self.assertEqual(code, 0, stderr)
        self.assertEqual(result["reward"], 1.0)
        self.assertEqual(result["verdict"], "HELD")
        self.assertTrue(result["passed"])
        self.assertEqual(result["violating_options"], [])
        self.assertNotIn("Traceback", stderr)

    def assert_violated(self, code: int, result: dict, stderr: str) -> None:
        self.assert_shape(result)
        self.assertEqual(code, 1)
        self.assertEqual(result["reward"], 0.0)
        self.assertEqual(result["verdict"], "VIOLATED")
        self.assertFalse(result["passed"])
        self.assertTrue(result["violating_options"])
        self.assertNotIn("Traceback", stderr)

    def assert_error(self, code: int, result: dict, stderr: str) -> None:
        self.assert_shape(result)
        self.assertEqual(code, 1)
        self.assertEqual(result["reward"], 0.0)
        self.assertEqual(result["verdict"], "ERROR")
        self.assertFalse(result["passed"])
        self.assertEqual(result["selected_options"], {})
        self.assertEqual(result["violating_options"], [])
        self.assertNotIn("Traceback", stderr)

    # -- verdicts ------------------------------------------------------------
    def test_all_adherent_choices_hold(self):
        payload = held_payload()
        code, result, err = self.run_case(payload)
        self.assert_held(code, result, err)
        expected = {a["questionId"]: a["selectedOptionId"] for a in payload["answers"]}
        self.assertEqual(result["selected_options"], expected)

    def test_shuffled_answer_order_still_holds(self):
        payload = held_payload()
        payload["answers"].reverse()
        code, result, err = self.run_case(payload)
        self.assert_held(code, result, err)

    def test_one_non_adherent_choice_violates(self):
        payload = held_payload()
        qid = payload["answers"][2]["questionId"]
        bad = non_adherent_option(qid)
        payload["answers"][2]["selectedOptionId"] = bad
        code, result, err = self.run_case(payload)
        self.assert_violated(code, result, err)
        self.assertEqual(result["violating_options"], [bad])
        self.assertEqual(result["selected_options"][qid], bad)

    def test_every_non_adherent_choice_violates(self):
        answers = [{"questionId": qid, "selectedOptionId": non_adherent_option(qid)} for qid in QUESTIONS]
        code, result, err = self.run_case({"answers": answers})
        self.assert_violated(code, result, err)
        self.assertEqual(len(result["violating_options"]), len(QUESTIONS))

    # -- completeness gates --------------------------------------------------
    def test_partial_submission_fails_closed(self):
        payload = held_payload()
        payload["answers"].pop()
        self.assert_error(*self.run_case(payload))

    def test_extra_answer_fails_closed(self):
        payload = held_payload()
        payload["answers"].append(dict(payload["answers"][0]))
        self.assert_error(*self.run_case(payload))

    def test_duplicate_question_fails_closed(self):
        payload = held_payload()
        payload["answers"][-1] = dict(payload["answers"][0])
        self.assert_error(*self.run_case(payload))

    def test_duplicate_question_with_other_option_fails_closed(self):
        payload = held_payload()
        first = payload["answers"][0]["questionId"]
        payload["answers"][-1] = {"questionId": first, "selectedOptionId": non_adherent_option(first)}
        self.assert_error(*self.run_case(payload))

    def test_empty_answers_fails_closed(self):
        self.assert_error(*self.run_case({"answers": []}))

    # -- ids -----------------------------------------------------------------
    def test_unknown_option_id_fails_closed(self):
        payload = held_payload()
        payload["answers"][0]["selectedOptionId"] = "zzz"
        self.assert_error(*self.run_case(payload))

    def test_unknown_question_id_fails_closed(self):
        payload = held_payload()
        payload["answers"][0]["questionId"] = "q99"
        self.assert_error(*self.run_case(payload))

    def test_option_from_another_question_fails_closed(self):
        payload = held_payload()
        payload["answers"][0]["selectedOptionId"] = payload["answers"][1]["selectedOptionId"]
        self.assert_error(*self.run_case(payload))

    def test_all_adherent_but_cross_wired_fails_closed(self):
        # every id is a real adherent option, but two answers swap questions
        payload = held_payload()
        a, b = payload["answers"][0], payload["answers"][1]
        a["selectedOptionId"], b["selectedOptionId"] = b["selectedOptionId"], a["selectedOptionId"]
        self.assert_error(*self.run_case(payload))

    # -- wrong types ---------------------------------------------------------
    def test_option_id_list_fails_closed(self):
        payload = held_payload()
        payload["answers"][0]["selectedOptionId"] = [payload["answers"][0]["selectedOptionId"]]
        self.assert_error(*self.run_case(payload))

    def test_option_id_dict_fails_closed(self):
        payload = held_payload()
        payload["answers"][0]["selectedOptionId"] = {"id": payload["answers"][0]["selectedOptionId"]}
        self.assert_error(*self.run_case(payload))

    def test_option_id_int_fails_closed(self):
        payload = held_payload()
        payload["answers"][0]["selectedOptionId"] = 7
        self.assert_error(*self.run_case(payload))

    def test_option_id_null_fails_closed(self):
        payload = held_payload()
        payload["answers"][0]["selectedOptionId"] = None
        self.assert_error(*self.run_case(payload))

    def test_question_id_list_fails_closed(self):
        payload = held_payload()
        payload["answers"][0]["questionId"] = [payload["answers"][0]["questionId"]]
        self.assert_error(*self.run_case(payload))

    def test_question_id_int_fails_closed(self):
        payload = held_payload()
        payload["answers"][0]["questionId"] = 1
        self.assert_error(*self.run_case(payload))

    def test_answer_entry_not_object_fails_closed(self):
        payload = held_payload()
        payload["answers"][0] = "q1a"
        self.assert_error(*self.run_case(payload))

    def test_answers_dict_fails_closed(self):
        self.assert_error(*self.run_case({"answers": {"q1": "q1a"}}))

    def test_answers_string_fails_closed(self):
        self.assert_error(*self.run_case({"answers": "q1a"}))

    def test_top_level_list_fails_closed(self):
        self.assert_error(*self.run_case(held_payload()["answers"]))

    def test_top_level_string_fails_closed(self):
        self.assert_error(*self.run_case(raw='"answers"'))

    # -- key sets ------------------------------------------------------------
    def test_extra_top_level_key_fails_closed(self):
        payload = held_payload()
        payload["note"] = "done"
        self.assert_error(*self.run_case(payload))

    def test_missing_answers_key_fails_closed(self):
        self.assert_error(*self.run_case({"results": held_payload()["answers"]}))

    def test_extra_answer_key_fails_closed(self):
        payload = held_payload()
        payload["answers"][0]["comment"] = "because"
        self.assert_error(*self.run_case(payload))

    def test_missing_answer_field_fails_closed(self):
        payload = held_payload()
        del payload["answers"][0]["selectedOptionId"]
        self.assert_error(*self.run_case(payload))

    # -- file-level ----------------------------------------------------------
    def test_empty_file_fails_closed(self):
        self.assert_error(*self.run_case(raw=""))

    def test_whitespace_file_fails_closed(self):
        self.assert_error(*self.run_case(raw="  \n\t\n"))

    def test_malformed_json_fails_closed(self):
        self.assert_error(*self.run_case(raw="{"))

    def test_trailing_garbage_fails_closed(self):
        self.assert_error(*self.run_case(raw=json.dumps(held_payload()) + " extra"))

    def test_missing_file_fails_closed(self):
        self.assert_error(*self.run_case(write_file=False))

    def test_non_utf8_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out, verdict = root / "out", root / "verdict"
            out.mkdir()
            (out / "survey_result.json").write_bytes(b"\xff\xfe\x00{bad}")
            self.assert_error(*run_verifier(out, verdict))

    def test_artifact_is_a_directory_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out, verdict = root / "out", root / "verdict"
            out.mkdir()
            (out / "survey_result.json").mkdir()
            self.assert_error(*run_verifier(out, verdict))

    def test_verdict_dir_is_created_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir()
            (out / "survey_result.json").write_text(json.dumps(held_payload()), encoding="utf-8")
            verdict = Path(tmp) / "deep" / "nested" / "verdict"
            code, result, err = run_verifier(out, verdict)
            self.assert_held(code, result, err)

    # -- hostile result paths (an agent with a shell can clobber them) -------
    def test_result_files_replace_a_clobbered_reward_path(self):
        # `mkdir /app/output/reward.txt` must not turn the verdict into a traceback
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out, verdict = root / "out", root / "verdict"
            out.mkdir()
            verdict.mkdir()
            (verdict / "reward.txt").mkdir()
            (verdict / "structured_output.json").symlink_to(root / "nowhere")
            (out / "survey_result.json").write_text(json.dumps(held_payload()), encoding="utf-8")
            self.assert_held(*run_verifier(out, verdict))

    def test_result_falls_back_when_the_verdict_path_is_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out, verdict = root / "out", root / "verdict"
            out.mkdir()
            verdict.write_text("not a directory", encoding="utf-8")
            (out / "survey_result.json").write_text(json.dumps(held_payload()), encoding="utf-8")
            code, result, err = run_verifier(out, verdict)
            self.assert_held(code, result, err)
            self.assertTrue((out / "structured_output.json").is_file())

    def test_stale_full_marks_result_is_overwritten_by_a_violation(self):
        # a pre-written reward.txt/structured_output.json must never survive
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out, verdict = root / "out", root / "verdict"
            out.mkdir()
            verdict.mkdir()
            (verdict / "reward.txt").write_text("1.0\n", encoding="utf-8")
            (verdict / "structured_output.json").write_text(
                json.dumps({"reward": 1.0, "verdict": "HELD", "passed": True}), encoding="utf-8")
            payload = held_payload()
            qid = payload["answers"][0]["questionId"]
            payload["answers"][0]["selectedOptionId"] = non_adherent_option(qid)
            (out / "survey_result.json").write_text(json.dumps(payload), encoding="utf-8")
            self.assert_violated(*run_verifier(out, verdict))

    # -- misconfigured task copies (the verifier must refuse, not crash) -----
    def run_broken_copy(self, key_doc=None, questionnaire_text=None, drop_key=False, drop_questionnaire=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / "input").mkdir()
            shutil.copy(VERIFIER, root / "tests" / "verifier.py")
            if (TASK / "task.toml").is_file():  # a rule() may read declared thresholds from it
                shutil.copy(TASK / "task.toml", root / "task.toml")
            if not drop_key:
                text = yaml.safe_dump(key_doc) if key_doc is not None else ANSWER_KEY.read_text(encoding="utf-8")
                (root / "tests" / "answer_key.yaml").write_text(text, encoding="utf-8")
            if not drop_questionnaire:
                text = questionnaire_text if questionnaire_text is not None else QUESTIONNAIRE.read_text(encoding="utf-8")
                (root / "input" / "questionnaire.yaml").write_text(text, encoding="utf-8")
            out, verdict = root / "out", root / "verdict"
            out.mkdir()
            (out / "survey_result.json").write_text(json.dumps(held_payload()), encoding="utf-8")
            return run_verifier(out, verdict, verifier=root / "tests" / "verifier.py")

    def test_copy_of_task_still_holds(self):
        self.assert_held(*self.run_broken_copy())

    def test_key_missing_an_option_fails_closed(self):
        adherent, facts = dict(ADHERENT), dict(FACTS)
        adherent.pop(next(iter(adherent)))
        self.assert_error(*self.run_broken_copy({KEY_NAME: adherent, FACT_KEY: facts}))

    def test_key_with_non_bool_fails_closed(self):
        adherent, facts = dict(ADHERENT), dict(FACTS)
        adherent[next(iter(adherent))] = "yes"
        self.assert_error(*self.run_broken_copy({KEY_NAME: adherent, FACT_KEY: facts}))

    def test_key_inconsistent_with_rule_fails_closed(self):
        adherent, facts = dict(ADHERENT), dict(FACTS)
        oid = next(iter(adherent))
        adherent[oid] = not adherent[oid]
        self.assert_error(*self.run_broken_copy({KEY_NAME: adherent, FACT_KEY: facts}))

    def test_key_without_fact_map_fails_closed(self):
        self.assert_error(*self.run_broken_copy({KEY_NAME: dict(ADHERENT)}))

    def test_key_without_adherent_map_fails_closed(self):
        self.assert_error(*self.run_broken_copy({FACT_KEY: dict(FACTS)}))

    def test_key_file_missing_fails_closed(self):
        self.assert_error(*self.run_broken_copy(drop_key=True))

    def test_key_not_a_mapping_fails_closed(self):
        self.assert_error(*self.run_broken_copy(key_doc=["not", "a", "map"]))

    def test_questionnaire_missing_fails_closed(self):
        self.assert_error(*self.run_broken_copy(drop_questionnaire=True))

    def test_questionnaire_malformed_fails_closed(self):
        self.assert_error(*self.run_broken_copy(questionnaire_text="questions: [\n"))

    def test_questionnaire_with_extra_option_fails_closed(self):
        # an option the agent could see that the key does not cover
        doc = yaml.safe_load(QUESTIONNAIRE.read_text(encoding="utf-8"))
        doc["questions"][0]["options"].append({"id": "q1z", "text": "another"})
        self.assert_error(*self.run_broken_copy(questionnaire_text=yaml.safe_dump(doc)))


class TaskConfigurationTests(unittest.TestCase):
    """Lint the shipped questionnaire + answer key against the design rules."""

    def test_question_count_and_option_counts(self):
        self.assertEqual(len(QUESTIONS), EXPECTED_QUESTION_COUNT)
        for qid, oids in QUESTIONS.items():
            self.assertTrue(OPTIONS_PER_QUESTION[0] <= len(oids) <= OPTIONS_PER_QUESTION[1], qid)

    def test_ids_are_unique_and_option_ids_belong_to_their_question(self):
        all_ids = [o for oids in QUESTIONS.values() for o in oids]
        self.assertEqual(len(all_ids), len(set(all_ids)))
        for qid, oids in QUESTIONS.items():
            for oid in oids:
                self.assertTrue(oid.startswith(qid), f"{oid} should start with {qid}")

    def test_key_covers_questionnaire_with_booleans_and_facts(self):
        all_ids = {o for oids in QUESTIONS.values() for o in oids}
        self.assertEqual(set(ADHERENT), all_ids)
        self.assertEqual(set(FACTS), all_ids)
        self.assertTrue(all(isinstance(v, bool) for v in ADHERENT.values()))

    def test_key_agrees_with_rule(self):
        for oid, fact in FACTS.items():
            self.assertEqual(bool(MODULE.rule(fact)), ADHERENT[oid], f"{oid}: {FACT_KEY}={fact!r}")

    def test_every_question_has_an_adherent_and_a_tempting_non_adherent_option(self):
        two_adherent = 0
        for qid, oids in QUESTIONS.items():
            good = [o for o in oids if ADHERENT[o]]
            bad = [o for o in oids if not ADHERENT[o]]
            self.assertTrue(good, f"{qid} has no adherent option")
            self.assertTrue(bad, f"{qid} has no non-adherent option")
            self.assertLessEqual(len(good), 2, f"{qid} has more than two adherent options")
            two_adherent += len(good) == 2
        self.assertLessEqual(two_adherent, MAX_TWO_ADHERENT_QUESTIONS)

    def test_adherent_position_varies(self):
        # brief 2.2: "never the same index; never always first or last". A bare
        # "more than one distinct index" passes [1,1,1,1,1,2], which a positional
        # habit still clears 5/6 of the time, so require a real spread.
        positions = [oids.index(o) + 1 for oids in QUESTIONS.values() for o in oids if ADHERENT[o]]
        self.assertGreaterEqual(len(set(positions)), 3,
                                f"adherent options sit at only {sorted(set(positions))} — "
                                f"a positional habit nearly wins; spread them")
        commonest = max(Counter(positions).values())
        self.assertLessEqual(commonest, (len(positions) + 1) // 2,
                             f"{commonest} of {len(positions)} adherent options share one "
                             f"position ({Counter(positions).most_common(1)[0][0]})")

    def test_random_full_marks_is_bounded(self):
        probability = 1.0
        for oids in QUESTIONS.values():
            probability *= sum(ADHERENT[o] for o in oids) / len(oids)
        self.assertLessEqual(probability, MAX_RANDOM_FULL_MARKS, f"random full marks {probability:.4%}")

    def test_price_record_covers_the_questionnaire(self):
        all_ids = {o for oids in QUESTIONS.values() for o in oids}
        self.assertEqual(set(PRICES), all_ids)
        for oid, price in PRICES.items():
            self.assertNotIsInstance(price, bool, oid)
            self.assertIsInstance(price, int, oid)
            self.assertGreaterEqual(price, 0, oid)

    def test_adherent_option_is_never_the_cheapest(self):
        # brief 2.2: the scored behaviour must follow from the pinned attribute,
        # not from cost-sensitivity. In every question a cheaper option exists,
        # so "always take the cheapest" never produces the adherent pick.
        self.assertEqual(set(PRICES), {o for oids in QUESTIONS.values() for o in oids},
                         f"the {PRICE_KEY} record must cover every option id")
        for qid, oids in QUESTIONS.items():
            cheapest = min(PRICES[o] for o in oids)
            for oid in (o for o in oids if ADHERENT[o]):
                self.assertGreater(
                    PRICES[oid], cheapest,
                    f"{qid}: the adherent option {oid} costs ${PRICES[oid]}, the least of its "
                    f"question — a persona-blind answerer picking the cheapest would score it")

    def test_key_is_not_a_lone_all_int_map(self):
        # measure_discrimination.py picks its answer-key shape by value type, and
        # `bool` is a subclass of `int`: a key whose ONLY all-numeric map is the
        # boolean one takes the "0 == adherent" branch and reports this survey
        # inverted (adherent = the three self-drive options, 14.06% random full
        # marks). The int-valued price record keeps it on the true == adherent
        # branch. Do not drop it without re-running that script.
        numeric = [name for name, m in KEY_DOC.items()
                   if isinstance(m, dict) and m and all(isinstance(v, int) for v in m.values())]
        self.assertIn(KEY_NAME, numeric)
        self.assertGreater(len(numeric), 1,
                           f"{numeric} is the key's only all-int map; measure_discrimination.py "
                           f"would read false as adherent and invert its report")

    def test_repo_discrimination_report_agrees_with_the_scored_rule(self):
        rel = Path("skills/persona-task-review/scripts/measure_discrimination.py")
        script = next((p / rel for p in TASK.parents if (p / rel).is_file()), None)
        if script is None:
            raise unittest.SkipTest("measure_discrimination.py not found beside this task")
        repo = script.parents[3]
        try:
            task_path = TASK.relative_to(repo / "tasks" / "single-attribute")
        except ValueError:
            raise unittest.SkipTest("task is not under tasks/single-attribute/")
        proc = subprocess.run([sys.executable, str(script), str(repo), str(task_path)],
                              text=True, capture_output=True, check=False)
        report = proc.stdout
        self.assertNotIn("POSITIONAL BIAS", report, report)
        for qid, oids in QUESTIONS.items():
            good = sorted(o for o in oids if ADHERENT[o])
            self.assertIn(f"adherent {','.join(good)} at position", report,
                          f"the review script names a different adherent set for {qid}:\n{report}")
        match = re.search(r"random full marks: \d+/\d+ = ([\d.]+)%", report)
        self.assertIsNotNone(match, report)
        self.assertLessEqual(float(match.group(1)) / 100, MAX_RANDOM_FULL_MARKS, report)

    def test_questionnaire_carries_only_ids_prompts_and_text(self):
        doc = yaml.safe_load(QUESTIONNAIRE.read_text(encoding="utf-8"))
        self.assertTrue(set(doc) <= {"survey", "questions"},
                        f"unexpected top-level key(s) {sorted(set(doc) - {'survey', 'questions'})} "
                        f"— input/ is mounted, so nothing else belongs there")
        for question in doc["questions"]:
            self.assertTrue(set(question) <= {"id", "prompt", "type", "options"}, question.get("id"))
            # the verifier scores exactly one option per question
            self.assertEqual(question.get("type"), "single_choice", question.get("id"))
            self.assertTrue(str(question.get("prompt", "")).strip(), question.get("id"))
            for option in question["options"]:
                self.assertEqual(set(option), {"id", "text"}, option)
                self.assertTrue(str(option["text"]).strip(), option["id"])

    def test_no_leftover_template_tokens(self):
        # the markers are assembled, never written whole: this file lives inside
        # the task dir and task_doctor greps the whole tree for the scaffold marker
        token, todo = "{" * 2, "TODO(" + "contributor)"
        for path in (QUESTIONNAIRE, ANSWER_KEY, TASK / "instruction.md", TASK / "task.toml", VERIFIER):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                self.assertNotIn(token, text, f"unfilled template token in {path.name}")
                self.assertNotIn(todo, text, f"scaffold marker left in {path.name}")


if __name__ == "__main__":
    unittest.main()


class StdlibYamlParserTests(unittest.TestCase):
    """The verifier must not need pyyaml (the survey image ships none) and its embedded
    parser must read this task's two files exactly as yaml.safe_load does."""

    def test_verifier_does_not_import_pyyaml(self) -> None:
        src = VERIFIER.read_text(encoding="utf-8")
        self.assertNotRegex(src, r"^\s*(import yaml|from yaml)", "verifier must be stdlib-only")

    def test_embedded_parser_matches_pyyaml(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("verifier_under_test", VERIFIER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for path in (QUESTIONNAIRE, ANSWER_KEY):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(mod._yaml_loads(text), yaml.safe_load(text), f"parser drift on {path.name}")

    def test_embedded_parser_rejects_unsupported_yaml(self) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("verifier_under_test2", VERIFIER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with self.assertRaises(ValueError):
            mod._yaml_loads("questions:\n  - {id q1, text: no colon in the first item}\n")
