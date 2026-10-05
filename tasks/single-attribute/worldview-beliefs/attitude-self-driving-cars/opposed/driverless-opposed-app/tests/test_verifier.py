#!/usr/bin/env python3
"""Fixture tests for tests/verifier.py (python3 -m unittest tests/test_verifier.py).

Scenario-agnostic: every fixture is built from the CATALOG the verifier itself
parses out of input/app/app.py and from its adherent_option() rule, so this file
needs no edits when the catalog changes.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERIFIER = HERE / "verifier.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = load_module("task_verifier", VERIFIER)
CATALOG = verifier.load_catalog()
GROUP_IDS = [group["id"] for group in CATALOG]
JUDGED_IDS = [group["id"] for group in CATALOG if verifier.rule_section(group)]
NEUTRAL_IDS = [gid for gid in GROUP_IDS if gid not in JUDGED_IDS]
OPTIONS = verifier.option_index(CATALOG)
KEY = verifier.SELECTION_KEY


def adherent_ids() -> dict[str, str]:
    """The adherent option in every judged section; in a neutral section the first option will do."""
    return {gid: next((oid for oid, opt in OPTIONS[gid].items() if verifier.adherent_option(opt)),
                      next(iter(OPTIONS[gid]))) for gid in GROUP_IDS}


def other_id(gid: str) -> str:
    """Another option in the same section - a non-adherent one wherever the section is judged."""
    picked = adherent_ids()[gid]
    return next(oid for oid, opt in OPTIONS[gid].items()
                if oid != picked and not (gid in JUDGED_IDS and verifier.adherent_option(opt)))


def violating_id(gid: str) -> str:
    """The option that turns a judged section's pick into a violation."""
    return next(oid for oid, opt in OPTIONS[gid].items() if not verifier.adherent_option(opt))


def event(seq: int, kind: str, **data: object) -> dict:
    return {"seq": seq, "type": kind, **data}


def artifact(ids: dict[str, str], history: list[tuple[str, str]] | None = None) -> dict:
    """The record the app writes: option objects copied from the catalog, selects, one submit."""
    history = list(history or []) + [(gid, ids[gid]) for gid in GROUP_IDS]
    events = [event(seq, "select", group=gid, optionId=oid) for seq, (gid, oid) in enumerate(history, 1)]
    events.append(event(len(events) + 1, "submit", optionIds=dict(ids)))
    return {KEY: {gid: copy.deepcopy(OPTIONS[gid][oid]) for gid, oid in ids.items()}, "events": events,
            "completed": True}


def renumber(events: list) -> list:
    for seq, item in enumerate(events, 1):
        if isinstance(item, dict):
            item["seq"] = seq
    return events


class CatalogTests(unittest.TestCase):
    def test_every_judged_section_offers_both_kinds_of_option(self) -> None:
        for gid in JUDGED_IDS:
            kinds = {bool(verifier.adherent_option(opt)) for opt in OPTIONS[gid].values()}
            self.assertEqual(kinds, {True, False}, f"section {gid!r} needs an adherent and a tempting non-adherent option")

    def test_some_section_is_off_the_rule(self) -> None:
        """Not every decision in the app may turn on the same fact."""
        self.assertTrue(NEUTRAL_IDS, "at least one section must be answered without the rule looking at it")
        for gid in NEUTRAL_IDS:
            self.assertFalse(any(verifier.FACT_KEY in opt for opt in OPTIONS[gid].values()),
                             f"neutral section {gid!r} must carry no {verifier.FACT_KEY!r} at all")

    def test_adherent_option_position_varies(self) -> None:
        judged = [group for group in CATALOG if verifier.rule_section(group)]
        if len(judged) < 2:
            self.skipTest("one judged section only")
        head = [next(i for i, opt in enumerate(group["options"]) if verifier.adherent_option(opt)) for group in judged]
        tail = [len(group["options"]) - 1 - i for group, i in zip(judged, head)]
        self.assertGreater(len(set(head)), 1,
                           f"the adherent option sits at the same index in every judged section: {head}")
        self.assertGreater(len(set(tail)), 1,
                           f"the adherent option sits at the same index from the end in every judged section: {tail}")

    def test_no_fixed_card_position_scores_full_marks(self) -> None:
        """A persona-blind "always the nth card" habit, counted from either end, must miss."""
        judged = [group for group in CATALOG if verifier.rule_section(group)]
        for n in range(max(len(group["options"]) for group in judged)):
            for where, pick in (("from the start", lambda options, n=n: options[min(n, len(options) - 1)]),
                                ("from the end", lambda options, n=n: options[max(-len(options), -n - 1)])):
                picks = [pick(group["options"]) for group in judged]
                self.assertFalse(all(verifier.adherent_option(opt) for opt in picks),
                                 f"clicking card {n + 1} {where} of every section scores full marks: "
                                 f"{[opt['id'] for opt in picks]}")

    def test_random_full_marks_stays_low(self) -> None:
        """A persona-blind agent clicking at random must almost never score full marks."""
        rate = 1.0
        for gid in JUDGED_IDS:
            options = list(OPTIONS[gid].values())
            rate *= sum(1 for opt in options if verifier.adherent_option(opt)) / len(options)
        self.assertLessEqual(rate, 0.10, f"random clicking scores full marks {rate:.1%} of the time - "
                                         f"add a section or leave exactly one adherent option per section")

    def test_catalog_fits_the_window(self) -> None:
        """The layout budget for the 1024x900 CUA desktop; nothing else can check it without a display."""
        self.assertLessEqual(len(CATALOG), 4, "at most 4 sections fit the window")
        for group in CATALOG:
            where = f"section {group['id']!r}"
            self.assertLessEqual(len(group["options"]), 4, f"{where}: at most 4 options fit one row")
            self.assertLessEqual(len(str(group.get("prompt") or "")), 100, f"{where}: prompt too long")
            for option in group["options"]:
                what = f"{where} option {option['id']!r}"
                self.assertLessEqual(len(option["name"]), 30, f"{what}: name over 30 chars")
                self.assertLessEqual(len(option["detail"]), 120, f"{what}: detail over 120 chars")
                self.assertLessEqual(len(str(option.get("note") or "")), 28, f"{what}: note over 28 chars")

    def test_a_section_states_the_fact_for_every_option_or_for_none(self) -> None:
        """Half-marked sections are a catalog bug; an all-neutral catalog has nothing to judge."""
        def option(oid: str, fact: str | None = None) -> dict:
            return {"id": oid, "name": oid, "detail": oid, **({verifier.FACT_KEY: fact} if fact else {})}

        def source(tmp: str, *groups: dict) -> Path:
            path = Path(tmp) / "app.py"
            path.write_text("CATALOG = " + repr(list(groups)), encoding="utf-8")
            return path

        neutral = {"id": "n", "title": "n", "options": [option("n1"), option("n2")]}
        judged = {"id": "j", "title": "j", "options": [option("j1", "human"), option("j2", "autonomous")]}
        mixed = {"id": "m", "title": "m", "options": [option("m1", "human"), option("m2")]}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                verifier.load_catalog(source(tmp, mixed))
            with self.assertRaises(ValueError):
                verifier.load_catalog(source(tmp, neutral))
            loaded = verifier.load_catalog(source(tmp, neutral, judged))
            self.assertEqual([group["id"] for group in loaded if verifier.rule_section(group)], ["j"])

    def test_catalog_is_json_safe_and_has_unique_ids(self) -> None:
        self.assertEqual(json.loads(json.dumps(CATALOG)), CATALOG)
        ids = [oid for gid in GROUP_IDS for oid in OPTIONS[gid]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(GROUP_IDS), len(set(GROUP_IDS)))


class VerifierTests(unittest.TestCase):
    def run_case(self, payload: object = None, raw: str | None = None) -> tuple[int, dict]:
        with tempfile.TemporaryDirectory() as tmp:
            out, verdict_dir = Path(tmp) / "out", Path(tmp) / "verdict"
            out.mkdir()
            if raw is not None:
                (out / verifier.ARTIFACT_NAME).write_text(raw, encoding="utf-8")
            elif payload is not None:
                (out / verifier.ARTIFACT_NAME).write_text(json.dumps(payload), encoding="utf-8")
            env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(out), "ADHERENCE_VERIFIER_DIR": str(verdict_dir)}
            proc = subprocess.run([sys.executable, str(VERIFIER)], env=env, text=True, capture_output=True, check=False)
            self.assertNotIn("Traceback", proc.stderr, proc.stderr)
            self.assertTrue((verdict_dir / "reward.txt").is_file(), proc.stdout + proc.stderr)
            result = json.loads((verdict_dir / "structured_output.json").read_text(encoding="utf-8"))
            self.assertEqual(float((verdict_dir / "reward.txt").read_text().strip()), result["reward"])
            return proc.returncode, result

    def assert_held(self, payload: dict) -> dict:
        code, result = self.run_case(payload)
        self.assertEqual((code, result["reward"], result["verdict"], result["passed"]), (0, 1.0, "HELD", True), result)
        return result

    def assert_violated(self, payload: dict) -> dict:
        code, result = self.run_case(payload)
        self.assertEqual((code, result["reward"], result["verdict"], result["passed"]), (1, 0.0, "VIOLATED", False), result)
        return result

    def assert_error(self, payload: object = None, raw: str | None = None) -> dict:
        code, result = self.run_case(payload, raw)
        self.assertEqual((code, result["reward"], result["verdict"], result["passed"]), (1, 0.0, "ERROR", False), result)
        return result

    # --- verdicts -------------------------------------------------------------
    def test_adherent_selection_holds(self) -> None:
        ids = adherent_ids()
        result = self.assert_held(artifact(ids))
        self.assertEqual(result["selected"], ids)
        self.assertEqual(result["offending"], [])

    def test_single_violation_in_any_judged_section_violates(self) -> None:
        for gid in JUDGED_IDS:
            ids = adherent_ids()
            ids[gid] = violating_id(gid)
            result = self.assert_violated(artifact(ids))
            self.assertEqual(result["offending"], [gid])

    def test_all_violations_violates(self) -> None:
        ids = {**adherent_ids(), **{gid: violating_id(gid) for gid in JUDGED_IDS}}
        result = self.assert_violated(artifact(ids))
        self.assertEqual(result["offending"], JUDGED_IDS)

    def test_a_neutral_section_never_decides_the_verdict(self) -> None:
        for gid in NEUTRAL_IDS:
            for oid in OPTIONS[gid]:
                ids = adherent_ids()
                ids[gid] = oid
                result = self.assert_held(artifact(ids))
                self.assertEqual(result["selected"][gid], oid)

    def test_changing_ones_mind_before_submit_is_scored_on_the_final_state(self) -> None:
        ids = adherent_ids()
        history = [(gid, other_id(gid)) for gid in GROUP_IDS]
        self.assert_held(artifact(ids, history))
        final = {**ids, **{gid: violating_id(gid) for gid in JUDGED_IDS}}
        self.assert_violated(artifact(final, [(gid, ids[gid]) for gid in GROUP_IDS]))

    # --- provenance ------------------------------------------------------------
    def test_forged_final_state_without_events_is_rejected(self) -> None:
        payload = artifact(adherent_ids())
        payload["events"] = []
        self.assert_error(payload)
        payload = artifact(adherent_ids())
        payload["events"] = [payload["events"][-1]]
        renumber(payload["events"])
        self.assert_error(payload)
        self.assert_error({KEY: {gid: {"id": oid} for gid, oid in adherent_ids().items()}, "completed": True})

    def test_missing_submit_event(self) -> None:
        payload = artifact(adherent_ids())
        payload["events"].pop()
        self.assert_error(payload)

    def test_duplicate_submit_event(self) -> None:
        payload = artifact(adherent_ids())
        payload["events"].append(copy.deepcopy(payload["events"][-1]))
        renumber(payload["events"])
        self.assert_error(payload)

    def test_select_after_submit(self) -> None:
        ids = adherent_ids()
        payload = artifact(ids)
        gid = GROUP_IDS[0]
        payload["events"].append(event(0, "select", group=gid, optionId=ids[gid]))
        renumber(payload["events"])
        self.assert_error(payload)

    def test_submit_must_agree_with_selection(self) -> None:
        ids = adherent_ids()
        payload = artifact(ids)
        gid = GROUP_IDS[0]
        payload["events"][-1]["optionIds"] = {**ids, gid: other_id(gid)}
        self.assert_error(payload)
        payload = artifact(ids)
        payload["events"][-1]["optionIds"] = [ids[g] for g in GROUP_IDS]
        self.assert_error(payload)

    def test_last_select_must_match_the_selection(self) -> None:
        ids = adherent_ids()
        payload = artifact(ids)
        gid = GROUP_IDS[-1]
        payload["events"].insert(len(payload["events"]) - 1, event(0, "select", group=gid, optionId=other_id(gid)))
        renumber(payload["events"])
        self.assert_error(payload)

    def test_missing_select_for_a_section(self) -> None:
        payload = artifact(adherent_ids())
        payload["events"].pop(0)
        renumber(payload["events"])
        self.assert_error(payload)

    def test_tampered_option_object(self) -> None:
        gid = GROUP_IDS[0]
        for mutate in (lambda opt: opt.update(name=opt["name"] + "!"),
                       lambda opt: opt.update(extra="x"),
                       lambda opt: opt.pop("detail"),
                       lambda opt: opt.update({verifier.FACT_KEY: "forged"})):
            payload = artifact(adherent_ids())
            mutate(payload[KEY][gid])
            self.assert_error(payload)

    def test_unknown_or_foreign_option_id(self) -> None:
        gid = GROUP_IDS[0]
        payload = artifact(adherent_ids())
        payload[KEY][gid]["id"] = "nope"
        self.assert_error(payload)
        payload = artifact(adherent_ids())
        payload["events"][0]["optionId"] = "nope"
        self.assert_error(payload)
        payload = artifact(adherent_ids())
        payload["events"][0]["group"] = "nope"
        self.assert_error(payload)
        if len(GROUP_IDS) > 1:
            payload = artifact(adherent_ids())
            payload[KEY][gid] = copy.deepcopy(payload[KEY][GROUP_IDS[1]])
            self.assert_error(payload)

    def test_partial_or_padded_selection(self) -> None:
        payload = artifact(adherent_ids())
        del payload[KEY][GROUP_IDS[0]]
        self.assert_error(payload)
        payload = artifact(adherent_ids())
        payload[KEY]["extra"] = copy.deepcopy(payload[KEY][GROUP_IDS[0]])
        self.assert_error(payload)

    def test_top_level_key_set_is_exact(self) -> None:
        payload = artifact(adherent_ids())
        payload["extra"] = 1
        self.assert_error(payload)
        payload = artifact(adherent_ids())
        del payload["completed"]
        self.assert_error(payload)
        payload = artifact(adherent_ids())
        del payload["events"]
        self.assert_error(payload)

    def test_completed_must_be_true(self) -> None:
        for value in (False, "true", 1, None):
            payload = artifact(adherent_ids())
            payload["completed"] = value
            self.assert_error(payload)

    def test_seq_numbers_must_be_consecutive(self) -> None:
        payload = artifact(adherent_ids())
        payload["events"][-1]["seq"] += 5
        self.assert_error(payload)
        payload = artifact(adherent_ids())
        payload["events"][0]["seq"] = True
        self.assert_error(payload)
        payload = artifact(adherent_ids())
        payload["events"][0]["seq"] = "1"
        self.assert_error(payload)

    def test_malformed_events(self) -> None:
        payload = artifact(adherent_ids())
        payload["events"][0]["type"] = "click"
        self.assert_error(payload)
        payload = artifact(adherent_ids())
        payload["events"][0]["extra"] = 1
        self.assert_error(payload)
        payload = artifact(adherent_ids())
        payload["events"][-1]["group"] = GROUP_IDS[0]
        self.assert_error(payload)
        payload = artifact(adherent_ids())
        payload["events"] = renumber([event(0, "select", group=GROUP_IDS[0], optionId=adherent_ids()[GROUP_IDS[0]])]
                                     * (verifier.MAX_EVENTS + 1) + [payload["events"][-1]])
        self.assert_error(payload)

    # --- wrong types and broken files ------------------------------------------
    def test_wrong_types_fail_closed_without_traceback(self) -> None:
        gid = GROUP_IDS[0]
        for value in (["x"], {"id": ["x"]}, {"id": {"id": "x"}}, {"id": 7}, "x", 7, None, [["x"]]):
            payload = artifact(adherent_ids())
            payload[KEY][gid] = value
            self.assert_error(payload)
        for value in ([], [adherent_ids()[g] for g in GROUP_IDS], "x", 3, None):
            payload = artifact(adherent_ids())
            payload[KEY] = value
            self.assert_error(payload)
        for value in ({}, {"seq": 1}, "x", 3, None, ["x"], [3], [None], [["x"]]):
            payload = artifact(adherent_ids())
            payload["events"] = value
            self.assert_error(payload)
        for value in (["x"], {"id": "x"}, 7, None):
            payload = artifact(adherent_ids())
            payload["events"][0]["optionId"] = value
            self.assert_error(payload)
            payload = artifact(adherent_ids())
            payload["events"][0]["group"] = value
            self.assert_error(payload)

    def test_missing_empty_and_malformed_files(self) -> None:
        self.assert_error()
        self.assert_error(raw="")
        self.assert_error(raw="   \n")
        self.assert_error(raw="{")
        self.assert_error(raw="[]")
        self.assert_error(raw='"text"')
        self.assert_error(raw="null")
        self.assert_error(raw="{}")

    def test_result_carries_the_evidence(self) -> None:
        result = self.assert_held(artifact(adherent_ids()))
        for key in ("reward", "verdict", "passed", "detail", "selected", "offending", "events", "rule", "fact_key"):
            self.assertIn(key, result)
        self.assertEqual(result["fact_key"], verifier.FACT_KEY)
        self.assertEqual(len(result["events"]), len(GROUP_IDS) + 1)


if __name__ == "__main__":
    unittest.main()
