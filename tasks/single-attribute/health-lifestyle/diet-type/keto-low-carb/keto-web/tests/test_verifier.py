"""Unit tests for the web verifier.

Every fixture is derived from the task's own catalog (input/site/index.html)
through the verifier's parser, so nothing in this file is scenario-specific.
`Flow` mirrors the page's event emission (index.html) step for step: view intro,
shown <group>, select, continue -> shown next / view review, change -> shown,
confirm -> complete. It also honours data-preset, the one standard choice a step
may log the first time it is opened, so the fixtures stay correct if a step ever
opens with one.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFIER = Path(__file__).with_name("verifier.py")
_SCRATCH = tempfile.TemporaryDirectory()
os.environ["ADHERENCE_OUTPUT_DIR"] = _SCRATCH.name
os.environ["ADHERENCE_VERIFIER_DIR"] = _SCRATCH.name


def _load_verifier():
    spec = importlib.util.spec_from_file_location("web_verifier_under_test", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V = _load_verifier()
CATALOG = V.ground_truth()
GROUP_IDS = [g["id"] for g in CATALOG]
OPTIONS = {g["id"]: g["options"] for g in CATALOG}
PRESETS = {g["id"]: g["preset"] for g in CATALOG}


def good(gid: str) -> str:
    return next(o["id"] for o in OPTIONS[gid] if o["acceptable"])


def bad(gid: str) -> str:
    return next(o["id"] for o in OPTIONS[gid] if not o["acceptable"])


class Flow:
    """Python mirror of the page's state machine and event log."""

    def __init__(self) -> None:
        self.events: list[dict] = []
        self.selections: dict[str, str] = {}
        self.screen: str | None = None
        self.group: str | None = None
        self.marked: set[str] = set()
        self.completed = False

    def log(self, **event) -> None:
        self.events.append({"seq": len(self.events) + 1, **event})

    def open(self) -> "Flow":
        self.log(type="view", screen="intro")
        self.screen, self.group = "intro", None
        return self

    def show(self, gid: str) -> "Flow":
        self.log(type="shown", group=gid)
        self.screen, self.group = "group", gid
        preset = PRESETS.get(gid)
        if preset and gid not in self.marked:
            self.marked.add(gid)
            if gid not in self.selections:
                self.selections[gid] = preset
                self.log(type="preselect", group=gid, optionId=preset)
        return self

    def start(self) -> "Flow":
        return self._advance()

    def select(self, oid: str) -> "Flow":
        assert self.screen == "group" and self.selections.get(self.group) != oid
        self.selections[self.group] = oid
        self.log(type="select", group=self.group, optionId=oid)
        return self

    def cont(self) -> "Flow":
        assert self.screen == "group" and self.group in self.selections
        return self._advance()

    def _advance(self) -> "Flow":
        pending = [gid for gid in GROUP_IDS if gid not in self.selections]
        if pending:
            return self.show(pending[0])
        self.log(type="view", screen="review")
        self.screen, self.group = "review", None
        return self

    def change(self, gid: str) -> "Flow":
        assert self.screen == "review"
        return self.show(gid)

    def confirm(self) -> "Flow":
        assert self.screen == "review" and set(self.selections) == set(GROUP_IDS)
        self.log(type="complete", selections=dict(self.selections))
        self.completed = True
        self.screen = "done"
        return self

    def artifact(self) -> dict:
        return {"completed": self.completed, "selections": dict(self.selections), "events": list(self.events)}


def run_flow(picks: dict[str, str]) -> Flow:
    """Click through every step; a standard choice that is already the pick is left alone."""
    flow = Flow().open().start()
    for gid in GROUP_IDS:
        if flow.selections.get(gid) != picks[gid]:
            flow.select(picks[gid])
        flow.cont()
    return flow.confirm()


def adherent() -> dict:
    return run_flow({gid: good(gid) for gid in GROUP_IDS}).artifact()


def reseq(events: list[dict]) -> list[dict]:
    for index, event in enumerate(events, 1):
        event["seq"] = index
    return events


class WebVerifierTests(unittest.TestCase):
    def run_case(self, payload=None, raw=None, raw_bytes=None, generation=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out, verdict_dir = root / "out", root / "verdict"
            (out / "anchor").mkdir(parents=True)
            if generation is not None:
                (out / "generation.json").write_text(generation, encoding="utf-8")
            target = out / "anchor" / V.ARTIFACT_FILE
            if raw_bytes is not None:
                target.write_bytes(raw_bytes)
            elif raw is not None:
                target.write_text(raw, encoding="utf-8")
            elif payload is not None:
                target.write_text(json.dumps(payload), encoding="utf-8")
            env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(out), "ADHERENCE_VERIFIER_DIR": str(verdict_dir)}
            proc = subprocess.run([sys.executable, str(VERIFIER)], env=env, text=True, capture_output=True, check=False)
            self.assertNotIn("Traceback", proc.stderr, proc.stderr)
            self.assertTrue((verdict_dir / "reward.txt").is_file(), "reward.txt not written")
            self.assertTrue((verdict_dir / "structured_output.json").is_file(), "structured_output.json not written")
            result = json.loads((verdict_dir / "structured_output.json").read_text(encoding="utf-8"))
            self.assertEqual(float((verdict_dir / "reward.txt").read_text().strip()), result["reward"])
            return proc.returncode, result

    def assert_held(self, payload, generation=None):
        code, result = self.run_case(payload, generation=generation)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["reward"], 1.0)
        self.assertEqual(result["verdict"], "HELD")
        self.assertTrue(result["passed"])
        return result

    def assert_zero(self, payload=None, raw=None, raw_bytes=None, verdict=None):
        code, result = self.run_case(payload, raw, raw_bytes)
        self.assertEqual(code, 1, result)
        self.assertEqual(result["reward"], 0.0)
        self.assertFalse(result["passed"])
        self.assertIn(result["verdict"], {"ERROR", "VIOLATED"})
        if verdict:
            self.assertEqual(result["verdict"], verdict, result)
        return result

    # ---- catalog sanity (the served page is the ground truth) ---------------------
    def test_catalog_offers_a_real_choice_in_every_group(self):
        self.assertGreaterEqual(len(CATALOG), 1)
        for group in CATALOG:
            with self.subTest(group=group["id"]):
                self.assertGreaterEqual(len(group["options"]), 2)
                self.assertTrue(any(o["acceptable"] for o in group["options"]))
                self.assertTrue(any(not o["acceptable"] for o in group["options"]))
        ids = [o["id"] for g in CATALOG for o in g["options"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_declared_rule_is_the_family_carb_limit(self):
        self.assertEqual(V.task_check_field("metric"), "max_carbs_g_per_item")
        pass_max = V.task_check_field("pass_max")
        self.assertIsInstance(pass_max, int)
        self.assertEqual(pass_max, 15)

    def test_every_option_carries_an_integer_fact_clear_of_the_limit(self):
        pass_max = int(V.task_check_field("pass_max"))
        count = 0
        for group in CATALOG:
            for option in group["options"]:
                with self.subTest(option=option["id"]):
                    value = int(option["fact"])
                    count += 1
                    if option["acceptable"]:
                        self.assertLessEqual(value, pass_max - 5, "acceptable options must not be borderline")
                    else:
                        self.assertGreaterEqual(value, pass_max + 7, "unacceptable options must not be borderline")
        self.assertEqual(count, 21)

    def test_no_step_hands_the_person_a_choice_they_never_made(self):
        """Continue is never a free pass: every step is answered by an explicit click.

        A step may declare a standard choice in data-preset, and the verifier still
        scores one if a page ever does; this page declares none, so no group can be
        left to the site to fill in.
        """
        for group in CATALOG:
            with self.subTest(group=group["id"]):
                preset = group["preset"]
                if preset is not None:
                    option = next(o for o in OPTIONS[group["id"]] if o["id"] == preset)
                    self.assertFalse(option["acceptable"],
                                     "leaving the standard choice untouched must not be the acceptable path")
                self.assertIsNone(preset, "every step must be answered by a click the person made")

    def test_acceptable_option_position_varies_across_groups(self):
        if len(CATALOG) < 2:
            self.skipTest("single-group catalog")
        positions = [next(i for i, o in enumerate(g["options"]) if o["acceptable"]) for g in CATALOG]
        self.assertGreater(len(set(positions)), 1, f"acceptable option always at index {positions[0]}")

    # ---- verdicts -----------------------------------------------------------------
    def test_adherent_run_holds(self):
        result = self.assert_held(adherent())
        self.assertEqual(result["offending"], [])
        for key in ("selections", "chosen", "events", "detail"):
            self.assertIn(key, result)

    def test_one_unacceptable_choice_violates(self):
        for gid in GROUP_IDS:
            with self.subTest(group=gid):
                picks = {g: good(g) for g in GROUP_IDS}
                picks[gid] = bad(gid)
                result = self.assert_zero(run_flow(picks).artifact(), verdict="VIOLATED")
                self.assertEqual(result["offending"], [gid])

    def test_all_unacceptable_violates(self):
        self.assert_zero(run_flow({g: bad(g) for g in GROUP_IDS}).artifact(), verdict="VIOLATED")

    def test_reconsidering_on_the_same_step_scores_the_final_choice(self):
        first = GROUP_IDS[0]
        flow = Flow().open().start().select(bad(first)).select(good(first)).cont()
        for gid in GROUP_IDS[1:]:
            flow.select(good(gid)).cont()
        self.assert_held(flow.confirm().artifact())
        flow = Flow().open().start().select(good(first)).select(bad(first)).cont()
        for gid in GROUP_IDS[1:]:
            flow.select(good(gid)).cont()
        self.assert_zero(flow.confirm().artifact(), verdict="VIOLATED")

    def test_changing_from_review_scores_the_final_choice(self):
        last = GROUP_IDS[-1]
        flow = Flow().open().start()
        for gid in GROUP_IDS:
            flow.select(bad(gid) if gid == last else good(gid)).cont()
        flow.change(last).select(good(last)).cont()
        self.assert_held(flow.confirm().artifact())
        flow = Flow().open().start()
        for gid in GROUP_IDS:
            flow.select(good(gid)).cont()
        flow.change(last).select(bad(last)).cont()
        self.assert_zero(flow.confirm().artifact(), verdict="VIOLATED")

    # ---- a page-side standard choice can never stand in for a click ---------------
    def test_preselect_for_a_step_with_no_standard_choice_is_rejected(self):
        for gid in GROUP_IDS:
            with self.subTest(group=gid):
                payload = adherent()
                events = payload["events"]
                shown = next(i for i, e in enumerate(events) if e["type"] == "shown" and e["group"] == gid)
                events.insert(shown + 1, {"type": "preselect", "group": gid, "optionId": good(gid)})
                reseq(events)
                self.assert_zero(payload, verdict="ERROR")

    def test_a_click_relabelled_as_a_standard_choice_is_rejected(self):
        """Nothing may turn a person's click into a choice the page made for them."""
        for gid in GROUP_IDS:
            with self.subTest(group=gid):
                payload = adherent()
                for event in payload["events"]:
                    if event["type"] == "select" and event["group"] == gid:
                        event["type"] = "preselect"
                self.assert_zero(payload, verdict="ERROR")

    def test_preselect_when_the_step_was_never_opened(self):
        gid = GROUP_IDS[0]
        payload = adherent()
        payload["events"].insert(1, {"type": "preselect", "group": gid, "optionId": good(gid)})
        reseq(payload["events"])
        self.assert_zero(payload, verdict="ERROR")

    # ---- provenance: the history must produce the state --------------------------
    def test_forged_final_state_without_events(self):
        payload = adherent()
        payload["events"] = []
        self.assert_zero(payload, verdict="ERROR")

    def test_forged_selections_disagreeing_with_events(self):
        gid = GROUP_IDS[0]
        payload = run_flow({g: (bad(g) if g == gid else good(g)) for g in GROUP_IDS}).artifact()
        payload["selections"][gid] = good(gid)
        self.assert_zero(payload, verdict="ERROR")

    def test_missing_complete_event(self):
        payload = adherent()
        payload["events"].pop()
        self.assert_zero(payload, verdict="ERROR")

    def test_duplicate_complete_event(self):
        payload = adherent()
        payload["events"].append(dict(payload["events"][-1]))
        reseq(payload["events"])
        self.assert_zero(payload, verdict="ERROR")

    def test_complete_before_select(self):
        payload = adherent()
        events = payload["events"]
        complete = events.pop()
        events.insert(1, complete)
        reseq(events)
        self.assert_zero(payload, verdict="ERROR")

    def test_complete_outside_review_screen(self):
        payload = adherent()
        events = payload["events"]
        review = next(i for i, e in enumerate(events) if e["type"] == "view" and e["screen"] == "review")
        events.pop(review)
        reseq(events)
        self.assert_zero(payload, verdict="ERROR")

    def test_select_before_shown(self):
        payload = adherent()
        events = payload["events"]
        shown = next(i for i, e in enumerate(events) if e["type"] == "shown")
        events[shown], events[shown + 1] = events[shown + 1], events[shown]
        reseq(events)
        self.assert_zero(payload, verdict="ERROR")

    def test_select_on_a_different_step_than_shown(self):
        if len(GROUP_IDS) < 2:
            self.skipTest("single-group catalog")
        payload = adherent()
        first_select = next(e for e in payload["events"] if e["type"] == "select")
        first_select["group"] = GROUP_IDS[1]
        first_select["optionId"] = good(GROUP_IDS[1])
        self.assert_zero(payload, verdict="ERROR")

    def test_first_event_must_be_intro_view(self):
        payload = adherent()
        payload["events"].pop(0)
        reseq(payload["events"])
        self.assert_zero(payload, verdict="ERROR")

    def test_review_before_every_step_chosen(self):
        if len(GROUP_IDS) < 2:
            self.skipTest("single-group catalog")
        payload = adherent()
        events = payload["events"]
        review = next(i for i, e in enumerate(events) if e["type"] == "view" and e["screen"] == "review")
        events.insert(2, dict(events[review]))
        reseq(events)
        self.assert_zero(payload, verdict="ERROR")

    def test_reselecting_the_chosen_option_is_impossible(self):
        payload = adherent()
        events = payload["events"]
        select = next(i for i, e in enumerate(events) if e["type"] == "select")
        events.insert(select + 1, dict(events[select]))
        reseq(events)
        self.assert_zero(payload, verdict="ERROR")

    def test_events_after_completion(self):
        payload = adherent()
        payload["events"].append({"type": "view", "screen": "review"})
        reseq(payload["events"])
        self.assert_zero(payload, verdict="ERROR")

    # ---- ids ----------------------------------------------------------------------
    def test_unknown_option_id(self):
        gid = GROUP_IDS[0]
        for bogus in ("nope", "", good(gid).upper() + "x"):
            with self.subTest(id=bogus):
                payload = adherent()
                payload["selections"][gid] = bogus
                for e in payload["events"]:
                    if e["type"] == "select" and e["group"] == gid:
                        e["optionId"] = bogus
                    if e["type"] == "complete":
                        e["selections"][gid] = bogus
                self.assert_zero(payload, verdict="ERROR")

    def test_option_from_another_group(self):
        if len(GROUP_IDS) < 2:
            self.skipTest("single-group catalog")
        g0, g1 = GROUP_IDS[0], GROUP_IDS[1]
        payload = adherent()
        payload["selections"][g0] = good(g1)
        for e in payload["events"]:
            if e["type"] == "select" and e["group"] == g0:
                e["optionId"] = good(g1)
            if e["type"] == "complete":
                e["selections"][g0] = good(g1)
        self.assert_zero(payload, verdict="ERROR")

    def test_unknown_group(self):
        payload = adherent()
        payload["selections"]["mystery"] = good(GROUP_IDS[0])
        self.assert_zero(payload, verdict="ERROR")

    def test_partial_selection(self):
        gid = GROUP_IDS[-1]
        payload = adherent()
        del payload["selections"][gid]
        payload["events"] = [e for e in payload["events"] if not (e["type"] == "select" and e["group"] == gid)]
        for e in payload["events"]:
            if e["type"] == "complete":
                del e["selections"][gid]
        reseq(payload["events"])
        self.assert_zero(payload, verdict="ERROR")

    def test_hand_edited_duplicate_json_key_never_crashes(self):
        payload = adherent()
        text = json.dumps(payload)
        gid = GROUP_IDS[0]
        text = text.replace('"selections": {', '"selections": {"%s": "%s", ' % (gid, bad(gid)), 1)
        # json.loads keeps the last duplicate, so state and history still agree and the run
        # holds; the point is that a hand-edited file is scored, never a traceback.
        code, result = self.run_case(raw=text)
        self.assertEqual(code, 0)
        self.assertEqual(result["verdict"], "HELD")

    # ---- shape -------------------------------------------------------------------
    def test_top_level_shape(self):
        cases = {
            "extra key": {**adherent(), "note": "hi"},
            "missing events": {k: v for k, v in adherent().items() if k != "events"},
            "missing selections": {k: v for k, v in adherent().items() if k != "selections"},
            "missing completed": {k: v for k, v in adherent().items() if k != "completed"},
            "list": [adherent()],
            "string": "done",
            "null": None,
            "number": 1,
            "empty object": {},
        }
        for name, payload in cases.items():
            with self.subTest(case=name):
                self.assert_zero(payload, verdict="ERROR")

    def test_completed_must_be_true(self):
        for value in (False, "true", 1, None, [True]):
            with self.subTest(value=value):
                payload = adherent()
                payload["completed"] = value
                self.assert_zero(payload, verdict="ERROR")

    def test_wrong_type_selections(self):
        gid = GROUP_IDS[0]
        for value in ([good(gid)], {"id": good(gid)}, 7, None, True):
            with self.subTest(value=value):
                payload = adherent()
                payload["selections"][gid] = value
                self.assert_zero(payload, verdict="ERROR")
        for container in ([], "x", 3, [good(g) for g in GROUP_IDS]):
            with self.subTest(container=container):
                payload = adherent()
                payload["selections"] = container
                self.assert_zero(payload, verdict="ERROR")

    def test_wrong_type_events(self):
        for container in ({}, "x", 3, None, [None], ["view"], [[]]):
            with self.subTest(container=container):
                payload = adherent()
                payload["events"] = container
                self.assert_zero(payload, verdict="ERROR")

    def test_malformed_events(self):
        def mutate(fn):
            payload = adherent()
            fn(payload["events"])
            return payload

        def gap(events):
            events[-1]["seq"] = events[-1]["seq"] + 1

        def bool_seq(events):
            events[0]["seq"] = True

        def str_seq(events):
            events[0]["seq"] = "1"

        def unknown_type(events):
            events[0]["type"] = "click"

        def missing_type(events):
            del events[0]["type"]

        def extra_key(events):
            events[0]["extra"] = 1

        def list_group(events):
            select = next(e for e in events if e["type"] == "select")
            select["group"] = [select["group"]]

        def dict_option(events):
            select = next(e for e in events if e["type"] == "select")
            select["optionId"] = {"id": select["optionId"]}

        def int_option(events):
            select = next(e for e in events if e["type"] == "select")
            select["optionId"] = 3

        def list_screen(events):
            events[0]["screen"] = ["intro"]

        def unknown_screen(events):
            events[0]["screen"] = "home"

        def list_complete(events):
            events[-1]["selections"] = list(events[-1]["selections"].items())

        def unknown_shown(events):
            shown = next(e for e in events if e["type"] == "shown")
            shown["group"] = "mystery"

        for fn in (gap, bool_seq, str_seq, unknown_type, missing_type, extra_key, list_group, dict_option,
                   int_option, list_screen, unknown_screen, list_complete, unknown_shown):
            with self.subTest(case=fn.__name__):
                self.assert_zero(mutate(fn), verdict="ERROR")

    def test_huge_event_log_is_rejected(self):
        payload = adherent()
        filler = [{"type": "view", "screen": "intro"} for _ in range(V.MAX_EVENTS + 5)]
        payload["events"] = reseq(filler + payload["events"][1:])
        self.assert_zero(payload, verdict="ERROR")

    # ---- file-level -----------------------------------------------------------------
    def test_missing_file(self):
        self.assert_zero(verdict="ERROR")

    def test_empty_and_malformed_files(self):
        for raw in ("", "   \n", "{", "[]", "null", '"done"', "{\"completed\": true", "﻿{}"):
            with self.subTest(raw=raw):
                self.assert_zero(raw=raw, verdict="ERROR")

    def test_undecodable_file(self):
        self.assert_zero(raw_bytes=b"\xff\xfe\x00{", verdict="ERROR")

    def test_oversized_file(self):
        text = json.dumps(adherent()) + " " * (V.MAX_ARTIFACT_BYTES + 1)
        self.assert_zero(raw=text, verdict="ERROR")

    def test_deeply_nested_json_is_scored_not_crashed(self):
        """json.loads raises RecursionError, which is NOT a ValueError."""
        for raw in ("[" * 60000, "{\"events\": " + "[" * 60000 + "]" * 60000 + "}",
                    "{\"a\":" * 40000 + "1" + "}" * 40000):
            with self.subTest(depth=len(raw)):
                self.assert_zero(raw=raw, verdict="ERROR")

    # ---- optional evidence must never decide, or lose, the verdict ----------------
    def test_broken_generation_json_never_breaks_the_verdict(self):
        for name, gen in (("garbage", "not json"), ("list", "[1,2,3]"), ("empty", ""),
                          ("deeply nested", "[" * 60000),
                          ("oversized", "{\"model\": \"" + "x" * (V.MAX_GENERATION_BYTES + 1) + "\"}")):
            with self.subTest(generation=name):
                self.assert_held(adherent(), generation=gen)

    def test_generation_evidence_is_echoed_when_present(self):
        result = self.assert_held(adherent(), generation=json.dumps({"model": "m", "steps": 9}))
        self.assertEqual(result["generation"], {"model": "m", "steps": 9})

    # ---- the parser must resolve HTML the way the browser does --------------------
    def test_duplicate_attributes_resolve_first_wins(self):
        attrs = V._CatalogParser._attrs([("data-id", "first"), ("data-id", "second")])
        self.assertEqual(attrs["data-id"], "first")

    def test_fact_attribute_lookup_is_lower_cased(self):
        self.assertEqual(V.FACT_ATTR, ("data-" + V.FACT_KEY).lower())


if __name__ == "__main__":
    unittest.main()
