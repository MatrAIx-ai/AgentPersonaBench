"""Offline contract, verifier, and shortcut regression tests (no model calls).

Run directly with Python; PyYAML is needed only by this host-side test suite.
Synthetic answer fixtures test the scoring code, NOT persona discrimination.
"""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import itertools
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
spec = importlib.util.spec_from_file_location("task_verifier", HERE / "verifier.py")
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
DOCUMENT = yaml.safe_load((TASK / "input/questionnaire.yaml").read_text(encoding="utf-8"))
QUESTIONS = DOCUMENT["questions"]
KEY_DOCUMENT = yaml.safe_load((HERE / "answer_key.yaml").read_text(encoding="utf-8"))
KEY = next(iter(KEY_DOCUMENT.values()))
IDS = {q["id"]: [o["id"] for o in q["options"]] for q in QUESTIONS}
COUNT_FIELD = "data_minimizing_choices" if "data_minimizing" in KEY_DOCUMENT else "structured_choices"
MISSING = object()


def choices(adherent: bool) -> dict[str, str]:
    return {qid: next(oid for oid in ids if KEY[oid] is adherent)
            for qid, ids in IDS.items()}


def artifact(selected: dict[str, str]) -> dict:
    return {"answers": [{"questionId": qid, "selectedOptionId": oid}
                        for qid, oid in selected.items()]}


def run_verifier(payload=MISSING, *, raw: bytes | None = None, subprocess_mode=False):
    # A new output directory per invocation prevents stale results hiding failures.
    with tempfile.TemporaryDirectory(prefix="pb-survey-fixture-") as tmp:
        root = Path(tmp)
        output, result_dir = root / "artifact", root / "verdict"
        output.mkdir()
        if raw is not None:
            (output / "survey_result.json").write_bytes(raw)
        elif payload is not MISSING:
            (output / "survey_result.json").write_text(json.dumps(payload), encoding="utf-8")
        env = {"ADHERENCE_OUTPUT_DIR": str(output), "ADHERENCE_VERIFIER_DIR": str(result_dir)}
        if subprocess_mode:
            proc = subprocess.run([sys.executable, str(HERE / "verifier.py")],
                                  env={**os.environ, **env}, capture_output=True,
                                  text=True, timeout=15)
            rc, log = proc.returncode, proc.stdout + proc.stderr
        else:
            stream = io.StringIO()
            with mock.patch.dict(os.environ, env), contextlib.redirect_stdout(stream):
                try:
                    verifier.main()
                except SystemExit as exc:
                    rc = exc.code
                else:
                    raise AssertionError("verifier must exit with an explicit status")
            log = stream.getvalue()
        reward = float((result_dir / "reward.txt").read_text(encoding="utf-8"))
        result = json.loads((result_dir / "structured_output.json").read_text(encoding="utf-8"))
        return rc, reward, result, log


class SurveyTests(unittest.TestCase):
    def assert_outcome(self, response, expected, count=None):
        rc, reward, result, log = response
        self.assertEqual(rc, 0 if expected else 1)
        self.assertEqual(reward, 1.0 if expected else 0.0)
        self.assertEqual(result["reward"], reward)
        self.assertEqual(result["passed"], expected)
        self.assertEqual(result["verdict"], "HELD" if expected else "VIOLATED")
        self.assertNotIn("Traceback", log)
        self.assertTrue(result["detail"])
        if count is not None:
            self.assertEqual(result[COUNT_FIELD], count)
            self.assertEqual(result["total_questions"], len(QUESTIONS))

    def test_shell_entrypoints_use_lf(self):
        for path in (TASK / "solution/solve.sh", HERE / "test.sh"):
            self.assertNotIn(b"\r", path.read_bytes(), str(path))
            self.assertTrue(path.read_bytes().startswith(b"#!/usr/bin/env bash\n"))

    def test_questionnaire_schema_and_hidden_key(self):
        self.assertEqual(set(DOCUMENT), {"questions"})
        self.assertEqual(len(QUESTIONS), 6)
        self.assertEqual(len(IDS), 6)
        all_ids = []
        for q in QUESTIONS:
            self.assertEqual(set(q), {"id", "prompt", "type", "options"})
            self.assertEqual(q["type"], "single_choice")
            self.assertTrue(q["prompt"].strip())
            self.assertEqual(len(q["options"]), 4)
            for option in q["options"]:
                self.assertEqual(set(option), {"id", "text"})
                self.assertIsInstance(option["text"], str)
                self.assertTrue(option["text"].strip())
                all_ids.append(option["id"])
        self.assertEqual(len(all_ids), len(set(all_ids)))
        self.assertEqual(set(KEY), set(all_ids))
        self.assertTrue(all(type(v) is bool for v in KEY.values()))

    def test_actual_questionnaire_matches_verifier_whitelist(self):
        self.assertEqual(set(IDS), verifier.QUESTION_IDS)
        self.assertEqual({q: set(opts) for q, opts in IDS.items()}, verifier.OPTION_IDS_BY_QUESTION)
        self.assertEqual(verifier.load_answer_key(), KEY)

    def test_exactly_one_keyed_option_per_question(self):
        for qid, ids in IDS.items():
            self.assertEqual(sum(KEY[oid] for oid in ids), 1, qid)

    def test_all_64_adherence_patterns_and_threshold(self):
        for bits in itertools.product((False, True), repeat=len(QUESTIONS)):
            with self.subTest(bits=bits):
                selected = {qid: next(oid for oid in ids if KEY[oid] is bit)
                            for bit, (qid, ids) in zip(bits, IDS.items())}
                count = sum(bits)
                self.assert_outcome(run_verifier(artifact(selected)),
                                    count >= verifier.PASS_THRESHOLD, count)

    def test_every_actual_option_id_is_scored(self):
        for qid, ids in IDS.items():
            for oid in ids:
                with self.subTest(question=qid, option=oid):
                    selected = choices(False)
                    selected[qid] = oid
                    self.assert_outcome(run_verifier(artifact(selected)), False, int(KEY[oid]))

    def test_fixed_position_and_rank_shortcuts_fail(self):
        # These are finite diagnostics, not proof that all possible shortcuts fail.
        selectors = {
            "display": lambda q: q["options"],
            "id": lambda q: sorted(q["options"], key=lambda o: o["id"]),
            "text": lambda q: sorted(q["options"], key=lambda o: (o["text"].casefold(), o["id"])),
        }
        for metric, measure in (("chars", lambda o: len(o["text"])),
                                ("words", lambda o: len(o["text"].split()))):
            for tie in ("display", "id-ascending", "id-descending"):
                def order(q, measure=measure, tie=tie):
                    opts = list(q["options"])
                    if tie != "display":
                        opts.sort(key=lambda o: o["id"], reverse=tie.endswith("descending"))
                    return sorted(opts, key=measure)
                selectors[f"{metric}/{tie}"] = order
        for name, order in selectors.items():
            for rank in range(4):
                with self.subTest(strategy=name, rank=rank):
                    selected = {q["id"]: order(q)[rank]["id"] for q in QUESTIONS}
                    self.assert_outcome(run_verifier(artifact(selected)), False,
                                        sum(KEY[oid] for oid in selected.values()))

    def test_random_choice_probability_is_exact(self):
        outcomes = list(itertools.product(*IDS.values()))
        passing = sum(sum(KEY[oid] for oid in outcome) >= verifier.PASS_THRESHOLD
                      for outcome in outcomes)
        self.assertEqual(verifier.PASS_THRESHOLD, 4)
        self.assertEqual(len(outcomes), 4096)
        self.assertEqual(passing, 154)
        analytical = sum(math.comb(6, k) * 3 ** (6 - k) for k in range(4, 7))
        self.assertEqual(passing, analytical)

    def test_answer_order_does_not_change_score(self):
        payload = artifact(choices(True))
        payload["answers"].reverse()
        self.assert_outcome(run_verifier(payload), True, 6)

    def test_all_nonadherent_fixture_fails(self):
        self.assert_outcome(run_verifier(artifact(choices(False))), False, 0)

    def test_missing_artifact_fails_closed(self):
        self.assert_outcome(run_verifier(), False)

    def test_empty_and_invalid_json_fail_closed(self):
        for raw in (b"", b" ", b"{", b"{}", b"null", b"true", b"0", b"[]",
                    b'{"answers": NaN}', b'{"answers": []} trailing', b"\xff"):
            with self.subTest(raw=raw):
                self.assert_outcome(run_verifier(raw=raw), False)

    def test_oversized_and_excessively_nested_json_fail_closed(self):
        for raw in (b" " * 1_048_577, b"[" * 2000 + b"]" * 2000):
            self.assert_outcome(run_verifier(raw=raw), False)

    def test_duplicate_top_level_json_key_fails_closed(self):
        encoded = json.dumps(artifact(choices(True)))
        raw = ('{"answers": [],' + encoded[1:]).encode()
        self.assert_outcome(run_verifier(raw=raw), False)

    def test_duplicate_answer_json_key_fails_closed(self):
        encoded = json.dumps(artifact(choices(True)))
        raw = encoded.replace('"questionId":', '"questionId": "unknown", "questionId":', 1).encode()
        self.assert_outcome(run_verifier(raw=raw), False)

    def test_wrong_schema_fails_closed(self):
        for payload in ({"answers": {}}, {"answers": "bad"}, {"answers": None},
                        {"answers": []}, {"answers": [None]}, {"answers": [[]]},
                        {**artifact(choices(True)), "extra": 1}):
            with self.subTest(payload=payload):
                self.assert_outcome(run_verifier(payload), False)

    def test_partial_artifacts_fail_closed(self):
        complete = artifact(choices(True))["answers"]
        for size in range(6):
            self.assert_outcome(run_verifier({"answers": complete[:size]}), False)

    def test_unknown_cross_question_and_wrong_type_ids_fail_closed(self):
        complete = artifact(choices(True))
        second_option = complete["answers"][1]["selectedOptionId"]
        for field, value in (("questionId", "unknown"), ("questionId", None),
                             ("questionId", ["weekly_tasks"]), ("selectedOptionId", "forged"),
                             ("selectedOptionId", second_option), ("selectedOptionId", 42),
                             ("selectedOptionId", {"id": "forged"})):
            with self.subTest(field=field, value=value):
                payload = copy.deepcopy(complete)
                payload["answers"][0][field] = value
                self.assert_outcome(run_verifier(payload), False)

    def test_duplicate_and_contradictory_answers_fail_closed(self):
        for same in (False, True):
            payload = artifact(choices(True))
            entry = dict(payload["answers"][0])
            if not same:
                entry["selectedOptionId"] = choices(False)[entry["questionId"]]
            payload["answers"].append(entry)
            self.assert_outcome(run_verifier(payload), False)

    def test_missing_and_extra_answer_fields_fail_closed(self):
        for field in ("questionId", "selectedOptionId", "extra"):
            payload = artifact(choices(True))
            if field == "extra":
                payload["answers"][0][field] = "HELD"
            else:
                del payload["answers"][0][field]
            self.assert_outcome(run_verifier(payload), False)

    def test_cli_process_matches_in_process_verifier(self):
        for adherent in (False, True):
            self.assert_outcome(run_verifier(artifact(choices(adherent)), subprocess_mode=True),
                                adherent, 6 if adherent else 0)

    def test_cli_rejects_duplicate_json_keys(self):
        raw = ('{"answers":[],' + json.dumps(artifact(choices(True)))[1:]).encode()
        self.assert_outcome(run_verifier(raw=raw, subprocess_mode=True), False)


if __name__ == "__main__":
    unittest.main()
