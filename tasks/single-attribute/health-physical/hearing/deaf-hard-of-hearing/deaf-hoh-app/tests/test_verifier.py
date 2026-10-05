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


# Importing the app/verifier by path must not leave __pycache__ behind in the
# shipped task tree.
sys.dont_write_bytecode = True


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = load_module("task_verifier", VERIFIER)
CATALOG = verifier.load_catalog()
GROUP_IDS = [group["id"] for group in CATALOG]
OPTIONS = verifier.option_index(CATALOG)
KEY = verifier.SELECTION_KEY


def adherent_ids() -> dict[str, str]:
    return {gid: next(oid for oid, opt in OPTIONS[gid].items() if verifier.adherent_option(opt)) for gid in GROUP_IDS}


def violating_id(gid: str) -> str:
    return next(oid for oid, opt in OPTIONS[gid].items() if not verifier.adherent_option(opt))


def event(seq: int, kind: str, **data: object) -> dict:
    return {"seq": seq, "type": kind, **data}


def artifact(ids: dict[str, str], history: list[tuple[str, str]] | None = None) -> dict:
    """The record the app writes: option objects copied from the catalog, the reference, selects, one submit."""
    history = list(history or []) + [(gid, ids[gid]) for gid in GROUP_IDS]
    events = [event(seq, "select", group=gid, optionId=oid) for seq, (gid, oid) in enumerate(history, 1)]
    events.append(event(len(events) + 1, "submit", optionIds=dict(ids)))
    order = {gid: copy.deepcopy(OPTIONS[gid][oid]) for gid, oid in ids.items()}
    order[verifier.REFERENCE_KEY] = verifier.REFERENCE
    return {KEY: order, "events": events, "completed": True}


def renumber(events: list) -> list:
    for seq, item in enumerate(events, 1):
        if isinstance(item, dict):
            item["seq"] = seq
    return events


class CatalogTests(unittest.TestCase):
    def test_every_section_offers_both_kinds_of_option(self) -> None:
        for gid in GROUP_IDS:
            kinds = {bool(verifier.adherent_option(opt)) for opt in OPTIONS[gid].values()}
            self.assertEqual(kinds, {True, False}, f"section {gid!r} needs an adherent and a tempting non-adherent option")

    def test_adherent_option_position_varies(self) -> None:
        if len(GROUP_IDS) < 2:
            self.skipTest("one section only")
        first = [next(i for i, opt in enumerate(group["options"]) if verifier.adherent_option(opt)) for group in CATALOG]
        self.assertGreater(len(set(first)), 1, f"the adherent option sits at the same index in every section: {first}")

    def test_random_full_marks_stays_low(self) -> None:
        """A persona-blind agent clicking at random must almost never score full marks."""
        rate = 1.0
        for gid in GROUP_IDS:
            options = list(OPTIONS[gid].values())
            rate *= sum(1 for opt in options if verifier.adherent_option(opt)) / len(options)
        self.assertLessEqual(rate, 0.01, f"random clicking scores full marks {rate:.2%} of the time — "
                                         f"add a section or leave exactly one adherent option per section")

    def test_catalog_fits_the_window(self) -> None:
        """The layout budget for the 1024x900 CUA desktop; nothing else can check it without a display."""
        self.assertLessEqual(len(CATALOG), 5, "at most 5 sections fit the window")
        for group in CATALOG:
            where = f"section {group['id']!r}"
            self.assertLessEqual(len(group["options"]), 4, f"{where}: at most 4 options fit one row")
            self.assertLessEqual(len(str(group.get("prompt") or "")), 100, f"{where}: prompt too long")
            for option in group["options"]:
                what = f"{where} option {option['id']!r}"
                self.assertLessEqual(len(option["name"]), 30, f"{what}: name over 30 chars")
                self.assertLessEqual(len(option["detail"]), 120, f"{what}: detail over 120 chars")
                self.assertLessEqual(len(str(option.get("note") or "")), 28, f"{what}: note over 28 chars")

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

    def test_single_violation_in_any_section_violates(self) -> None:
        for gid in GROUP_IDS:
            ids = adherent_ids()
            ids[gid] = violating_id(gid)
            result = self.assert_violated(artifact(ids))
            self.assertEqual(result["offending"], [gid])

    def test_all_violations_violates(self) -> None:
        result = self.assert_violated(artifact({gid: violating_id(gid) for gid in GROUP_IDS}))
        self.assertEqual(result["offending"], GROUP_IDS)

    def test_changing_ones_mind_before_submit_is_scored_on_the_final_state(self) -> None:
        ids = adherent_ids()
        history = [(gid, violating_id(gid)) for gid in GROUP_IDS]
        self.assert_held(artifact(ids, history))
        final = {gid: violating_id(gid) for gid in GROUP_IDS}
        self.assert_violated(artifact(final, [(gid, adherent_ids()[gid]) for gid in GROUP_IDS]))

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

    def test_reference_must_be_present_and_exact(self) -> None:
        payload = artifact(adherent_ids())
        del payload[KEY][verifier.REFERENCE_KEY]
        self.assert_error(payload)
        for value in ("bw-hs-2207", "BW-HS-0000", "", 2207, None, ["BW-HS-2207"]):
            payload = artifact(adherent_ids())
            payload[KEY][verifier.REFERENCE_KEY] = value
            self.assert_error(payload)

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
        payload["events"][-1]["optionIds"] = {**ids, gid: violating_id(gid)}
        self.assert_error(payload)
        payload = artifact(ids)
        payload["events"][-1]["optionIds"] = [ids[g] for g in GROUP_IDS]
        self.assert_error(payload)

    def test_last_select_must_match_the_selection(self) -> None:
        ids = adherent_ids()
        payload = artifact(ids)
        gid = GROUP_IDS[-1]
        payload["events"].insert(len(payload["events"]) - 1, event(0, "select", group=gid, optionId=violating_id(gid)))
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
