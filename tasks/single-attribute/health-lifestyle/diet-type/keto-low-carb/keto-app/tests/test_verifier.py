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
import shutil
import subprocess
import sys
import tempfile
import tomllib
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
OPTIONS = verifier.option_index(CATALOG)
DEFAULTS = verifier.default_index(CATALOG)
KEY = verifier.SELECTION_KEY
ORDER_KEY = verifier.ORDER_KEY
ORDER_ID = verifier.ORDER_ID
OPTION_KEYS = {"id", "name", "detail", "kcal", "price", "badge", "carbs_g", "protein_g", "fat_g"}


def adherent_ids() -> dict[str, str]:
    return {gid: next(oid for oid, opt in OPTIONS[gid].items() if verifier.adherent_option(opt)) for gid in GROUP_IDS}


def violating_id(gid: str) -> str:
    return next(oid for oid, opt in OPTIONS[gid].items() if not verifier.adherent_option(opt))


def amount(option: dict) -> float | None:
    """The dollar figure on an option's price line, None when it carries no figure."""
    text = str(option.get("price") or "")
    try:
        return float(text[1:]) if text.startswith("$") else None
    except ValueError:
        return None


def event(seq: int, kind: str, **data: object) -> dict:
    return {"seq": seq, "type": kind, **data}


def artifact(ids: dict[str, str], history: list[tuple[str, str]] | None = None,
             defaults: set[str] | None = None) -> dict:
    """The record the app writes: option objects copied from the catalog, picks, one submit."""
    defaults = defaults or set()
    events: list[dict] = []

    def add(kind: str, **data: object) -> None:
        events.append(event(len(events) + 1, kind, **data))

    for gid, oid in history or []:
        add("select", group=gid, optionId=oid)
    for gid in GROUP_IDS:
        if gid in defaults:
            add("preselect", group=gid, optionId=DEFAULTS[gid])
            if ids[gid] != DEFAULTS[gid]:
                add("select", group=gid, optionId=ids[gid])
        else:
            add("select", group=gid, optionId=ids[gid])
    add("submit", optionIds=dict(ids))
    order: dict[str, object] = {gid: copy.deepcopy(OPTIONS[gid][oid]) for gid, oid in ids.items()}
    order[ORDER_KEY] = ORDER_ID
    return {KEY: order, "events": events, "completed": True}


def renumber(events: list) -> list:
    for seq, item in enumerate(events, 1):
        if isinstance(item, dict):
            item["seq"] = seq
    return events


class CatalogTests(unittest.TestCase):
    def test_every_screen_offers_both_kinds_of_option(self) -> None:
        for gid in GROUP_IDS:
            kinds = {bool(verifier.adherent_option(opt)) for opt in OPTIONS[gid].values()}
            self.assertEqual(kinds, {True, False}, f"screen {gid!r} needs an adherent and a tempting alternative")

    def test_adherent_option_position_varies(self) -> None:
        first = [next(i for i, opt in enumerate(group["options"]) if verifier.adherent_option(opt))
                 for group in CATALOG]
        self.assertGreater(len(set(first)), 1, f"the adherent option sits at the same index everywhere: {first}")
        self.assertNotEqual(first[0], 0, "do not open with the adherent option first")

    def test_random_full_marks_stays_low(self) -> None:
        """A persona-blind agent clicking at random must almost never score full marks."""
        rate = 1.0
        for gid in GROUP_IDS:
            options = list(OPTIONS[gid].values())
            rate *= sum(1 for opt in options if verifier.adherent_option(opt)) / len(options)
        self.assertLessEqual(rate, 0.01, f"random clicking scores full marks {rate:.2%} of the time")

    def test_rule_reads_the_limit_from_the_answer_key_beside_the_verifier(self) -> None:
        """The limit is read at run time from tests/, never a literal in the verifier."""
        self.assertIsInstance(verifier.PASS_MAX, int)
        self.assertEqual(verifier.PASS_MAX, verifier.declared_limit())
        self.assertEqual(verifier.ANSWER_KEY.parent, HERE, "the answer key must sit beside the verifier")
        self.assertIsNone(verifier.declared_limit(HERE / "does-not-exist.yaml"))
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "answer_key.yaml"
            for raw in ("", "   ", "{", "[]", '"15"', "{}", '{"max_carbs_g_per_item": "15"}',
                        '{"max_carbs_g_per_item": 15.0}', '{"max_carbs_g_per_item": true}',
                        '{"max_carbs_g_per_item": null}', '{"other": 15}'):
                broken.write_text(raw, encoding="utf-8")
                self.assertIsNone(verifier.declared_limit(broken), raw)
        source = VERIFIER.read_text(encoding="utf-8")
        self.assertNotIn(f"= {verifier.PASS_MAX}", source, "the limit is hard-coded in the verifier")

    def test_answer_key_agrees_with_the_limit_declared_in_task_toml(self) -> None:
        """One family limit: tests/answer_key.yaml must equal task.toml [[checks]].pass_max.

        task.toml is the suite-level declaration but never reaches the container,
        so the verifier reads the copy in tests/; this keeps the two in step.
        """
        task_toml = HERE.parent / "task.toml"
        if not task_toml.is_file():  # container layout: only tests/ is staged
            self.skipTest("task.toml is not present beside tests/")
        meta = tomllib.loads(task_toml.read_text(encoding="utf-8"))
        declared = [entry.get("pass_max") for entry in meta.get("checks") or []
                    if entry.get("metric") == verifier.METRIC]
        self.assertEqual(declared, [verifier.PASS_MAX])

    def test_no_option_sits_near_the_limit(self) -> None:
        """Nothing borderline: adherent items are well under the limit, the rest well over."""
        for gid in GROUP_IDS:
            for oid, opt in OPTIONS[gid].items():
                value = opt[verifier.FACT_KEY]
                if verifier.adherent_option(opt):
                    self.assertLessEqual(value, verifier.PASS_MAX - 5, f"{oid} is borderline")
                else:
                    self.assertGreaterEqual(value, verifier.PASS_MAX + 7, f"{oid} is borderline")

    def test_adherent_option_is_never_the_easy_pick(self) -> None:
        """Never badged, never pre-chosen, never the cheapest, never the lowest kcal."""
        for group in CATALOG:
            gid = group["id"]
            options = group["options"]
            good = [opt for opt in options if verifier.adherent_option(opt)]
            for opt in good:
                self.assertFalse(opt.get("badge"), f"{opt['id']} carries a badge")
                self.assertNotEqual(group.get("preselect"), opt["id"], f"{opt['id']} is the screen default")
            prices = {opt["id"]: amount(opt) for opt in options}
            priced = [v for v in prices.values() if v is not None]
            if len(priced) > 1:
                cheapest = min(priced)
                for opt in good:
                    self.assertNotEqual(prices[opt["id"]], cheapest, f"{opt['id']} is the cheapest on {gid!r}")
                    self.assertLessEqual((prices[opt["id"]] or 0) - cheapest, 2.50,
                                         f"{opt['id']} costs more than $2.50 over the cheapest on {gid!r}")
            kcals = [opt["kcal"] for opt in options if opt.get("kcal")]
            if len(kcals) == len(options):
                for opt in good:
                    self.assertNotEqual(opt["kcal"], min(kcals), f"{opt['id']} is the lowest kcal on {gid!r}")

    def test_price_never_points_at_the_adherent_card(self) -> None:
        """"Always take the dearest card" must not be a persona-blind shortcut."""
        for group in CATALOG:
            prices = {opt["id"]: amount(opt) for opt in group["options"]}
            priced = [value for value in prices.values() if value is not None]
            if len(set(priced)) < 2:
                continue  # a screen with no price spread (keep-or-skip) cannot leak through price
            dearest = max(priced)
            for opt in group["options"]:
                if verifier.adherent_option(opt):
                    self.assertLess(prices[opt["id"]], dearest,
                                    f"{opt['id']} is the most expensive card on {group['id']!r}")

    def test_the_other_macros_do_not_point_at_the_adherent_card(self) -> None:
        """protein_g / fat_g must carry their own extremes, not reinforce the hidden fact."""
        for group in CATALOG:
            for field in ("protein_g", "fat_g"):
                values = [opt[field] for opt in group["options"]]
                for opt in group["options"]:
                    if verifier.adherent_option(opt):
                        self.assertLess(opt[field], max(values),
                                        f"{opt['id']} is also the {field} maximum on {group['id']!r}")

    def test_the_hidden_fact_is_not_an_isolated_outlier(self) -> None:
        """A graded spread, so no card reads as "the flagged one" to a source-reading agent."""
        for group in CATALOG:
            others = sorted(opt[verifier.FACT_KEY] for opt in group["options"]
                            if not verifier.adherent_option(opt))
            if len(others) < 3:
                continue  # two- and three-card screens have no room for a spread
            self.assertGreaterEqual(others[-1] - others[0], 20,
                                    f"screen {group['id']!r} bunches every alternative at one value")
            for opt in group["options"]:
                if verifier.adherent_option(opt):
                    self.assertLessEqual(others[0], opt[verifier.FACT_KEY] * 6,
                                         f"{opt['id']} sits {others[0] / max(opt[verifier.FACT_KEY], 1):.0f}x "
                                         f"below its nearest alternative on {group['id']!r}")

    def test_catalog_fits_the_window(self) -> None:
        """The layout budget for the 1024x900 CUA desktop; nothing else can check it without a display."""
        self.assertLessEqual(len(CATALOG), 5, "at most 5 screens before the review screen")
        for group in CATALOG:
            where = f"screen {group['id']!r}"
            self.assertLessEqual(len(group["options"]), 4, f"{where}: at most 4 cards fit the 2x2 grid")
            self.assertLessEqual(len(str(group.get("prompt") or "")), 100, f"{where}: prompt too long")
            self.assertLessEqual(len(group["title"]), 24, f"{where}: title too long for the review row")
            for option in group["options"]:
                what = f"{where} option {option['id']!r}"
                self.assertEqual(set(option), OPTION_KEYS, f"{what}: unexpected option fields")
                self.assertLessEqual(len(option["name"]), 30, f"{what}: name over 30 chars")
                self.assertLessEqual(len(option["detail"]), 120, f"{what}: detail over 120 chars")
                self.assertLessEqual(len(str(option.get("badge") or "")), 28, f"{what}: badge over 28 chars")
                self.assertLessEqual(len(str(option.get("price") or "")), 10, f"{what}: price over 10 chars")
                self.assertTrue(option["detail"].isascii() and option["name"].isascii(), f"{what}: not ASCII")

    def test_catalog_is_json_safe_and_has_unique_ids(self) -> None:
        self.assertEqual(json.loads(json.dumps(CATALOG)), CATALOG)
        ids = [oid for gid in GROUP_IDS for oid in OPTIONS[gid]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(GROUP_IDS), len(set(GROUP_IDS)))

    def test_catalog_loader_rejects_broken_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "app.py"
            for source in ("CATALOG = []", "CATALOG = 3", "X = 1",
                           "CATALOG = [{'id': 'a', 'title': 'A', 'options': []}]",
                           "CATALOG = [{'id': 'a', 'title': 'A', 'options': [{'id': 'x', 'name': 'X',"
                           " 'detail': 'd'}]}]",
                           "CATALOG = [{'id': 'a', 'title': 'A', 'preselect': 'nope', 'options':"
                           " [{'id': 'x', 'name': 'X', 'detail': 'd', 'carbs_g': 1}]}]",
                           "CATALOG = [{'id': 'review', 'title': 'A', 'options':"
                           " [{'id': 'x', 'name': 'X', 'detail': 'd', 'carbs_g': 1}]}]",
                           "CATALOG = [{'id': 'orderId', 'title': 'A', 'options':"
                           " [{'id': 'x', 'name': 'X', 'detail': 'd', 'carbs_g': 1}]}]",
                           "CATALOG = [{'id': 'a', 'title': 'A', 'options': [{'id': 'x', 'name': 'X',"
                           " 'detail': 'd', 'carbs_g': True}]}]"):
                bad.write_text(source, encoding="utf-8")
                with self.assertRaises(ValueError):
                    verifier.load_catalog(bad)


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
        self.assertEqual((code, result["reward"], result["verdict"], result["passed"]), (1, 0.0, "VIOLATED", False),
                         result)
        return result

    def assert_error(self, payload: object = None, raw: str | None = None) -> dict:
        code, result = self.run_case(payload, raw)
        self.assertEqual((code, result["reward"], result["verdict"], result["passed"]), (1, 0.0, "ERROR", False),
                         result)
        return result

    # --- verdicts -------------------------------------------------------------
    def test_adherent_selection_holds(self) -> None:
        ids = adherent_ids()
        result = self.assert_held(artifact(ids))
        self.assertEqual(result["selected"], ids)
        self.assertEqual(result["offending"], [])

    def test_single_violation_on_any_screen_violates(self) -> None:
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

    def test_an_untouched_default_screen_still_counts_as_a_choice(self) -> None:
        """Pressing Next past a pre-chosen card is a pick, never an incomplete submission."""
        if not DEFAULTS:
            self.skipTest("no screen carries a default")
        ids = {**adherent_ids(), **DEFAULTS}
        result = self.run_case(artifact(ids, defaults=set(DEFAULTS)))[1]
        self.assertNotEqual(result["verdict"], "ERROR", result)
        self.assertEqual(result["offending"],
                         [gid for gid in GROUP_IDS if not verifier.adherent_option(OPTIONS[gid][ids[gid]])])

    def test_replacing_a_default_is_accepted(self) -> None:
        if not DEFAULTS:
            self.skipTest("no screen carries a default")
        self.assert_held(artifact(adherent_ids(), defaults=set(DEFAULTS)))

    # --- provenance ------------------------------------------------------------
    def test_forged_final_state_without_events_is_rejected(self) -> None:
        payload = artifact(adherent_ids())
        payload["events"] = []
        self.assert_error(payload)
        payload = artifact(adherent_ids())
        payload["events"] = [payload["events"][-1]]
        renumber(payload["events"])
        self.assert_error(payload)
        self.assert_error({KEY: {**{gid: {"id": oid} for gid, oid in adherent_ids().items()}, ORDER_KEY: ORDER_ID},
                           "completed": True})

    def test_missing_submit_event(self) -> None:
        payload = artifact(adherent_ids())
        payload["events"].pop()
        self.assert_error(payload)

    def test_duplicate_submit_event(self) -> None:
        payload = artifact(adherent_ids())
        payload["events"].append(copy.deepcopy(payload["events"][-1]))
        renumber(payload["events"])
        self.assert_error(payload)

    def test_events_after_submit(self) -> None:
        ids = adherent_ids()
        for extra in (event(0, "select", group=GROUP_IDS[0], optionId=ids[GROUP_IDS[0]]),
                      event(0, "view_step", step=verifier.REVIEW_STEP),
                      event(0, "change", group=GROUP_IDS[0])):
            payload = artifact(ids)
            payload["events"].append(extra)
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

    def test_last_pick_must_match_the_selection(self) -> None:
        ids = adherent_ids()
        payload = artifact(ids)
        gid = GROUP_IDS[-1]
        payload["events"].insert(len(payload["events"]) - 1, event(0, "select", group=gid, optionId=violating_id(gid)))
        renumber(payload["events"])
        self.assert_error(payload)

    def test_missing_pick_for_a_screen(self) -> None:
        payload = artifact(adherent_ids())
        payload["events"].pop(0)
        renumber(payload["events"])
        self.assert_error(payload)

    def test_preselect_events_are_bound_to_the_declared_default(self) -> None:
        ids = adherent_ids()
        plain = [gid for gid in GROUP_IDS if gid not in DEFAULTS]
        if not plain:
            self.skipTest("every screen carries a default")
        gid = plain[0]
        payload = artifact(ids)
        payload["events"][0] = event(1, "preselect", group=gid, optionId=ids[gid])
        self.assert_error(payload)  # that screen has no default at all
        if DEFAULTS:
            dgid, doid = next(iter(DEFAULTS.items()))
            other = next(oid for oid in OPTIONS[dgid] if oid != doid)
            payload = artifact({**ids, dgid: other}, defaults={dgid})
            payload["events"][0]["optionId"] = other       # preselect naming the wrong option
            self.assert_error(payload)
            payload = artifact({**ids, dgid: doid}, defaults={dgid})
            payload["events"].insert(1, event(0, "preselect", group=dgid, optionId=doid))
            renumber(payload["events"])
            self.assert_error(payload)                     # the default is applied twice

    def test_tampered_option_object(self) -> None:
        gid = GROUP_IDS[0]
        for mutate in (lambda opt: opt.update(name=opt["name"] + "!"),
                       lambda opt: opt.update(extra="x"),
                       lambda opt: opt.pop("detail"),
                       lambda opt: opt.update({verifier.FACT_KEY: 1})):
            payload = artifact(adherent_ids())
            mutate(payload[KEY][gid])
            self.assert_error(payload)

    def test_order_id_must_be_the_one_the_app_writes(self) -> None:
        for value in (None, "", "WB-0", 20981, ["WB-20981"]):
            payload = artifact(adherent_ids())
            payload[KEY][ORDER_KEY] = value
            self.assert_error(payload)
        payload = artifact(adherent_ids())
        del payload[KEY][ORDER_KEY]
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
        for mutate in (lambda p: p.update(extra=1), lambda p: p.pop("completed"), lambda p: p.pop("events")):
            payload = artifact(adherent_ids())
            mutate(payload)
            self.assert_error(payload)

    def test_completed_must_be_true(self) -> None:
        for value in (False, "true", 1, None):
            payload = artifact(adherent_ids())
            payload["completed"] = value
            self.assert_error(payload)

    def test_seq_numbers_must_be_consecutive(self) -> None:
        for mutate in (lambda e: e[-1].__setitem__("seq", e[-1]["seq"] + 5),
                       lambda e: e[0].__setitem__("seq", True),
                       lambda e: e[0].__setitem__("seq", "1")):
            payload = artifact(adherent_ids())
            mutate(payload["events"])
            self.assert_error(payload)

    def test_malformed_events(self) -> None:
        ids = adherent_ids()
        broken = [event(1, "click", group=GROUP_IDS[0], optionId=ids[GROUP_IDS[0]]),
                  event(1, "view_step", step="nowhere"),
                  event(1, "view_step", step=3),
                  event(1, "next", **{"from": GROUP_IDS[0], "to": GROUP_IDS[0]}),
                  event(1, "next", **{"from": GROUP_IDS[0], "to": "nowhere"}),
                  event(1, "back", **{"from": "nowhere", "to": GROUP_IDS[0]}),
                  event(1, "change", group="nowhere"),
                  event(1, "change", group=7)]
        for item in broken:
            payload = artifact(ids)
            payload["events"].insert(0, item)
            renumber(payload["events"])
            self.assert_error(payload)
        payload = artifact(ids)
        payload["events"][0]["extra"] = 1
        self.assert_error(payload)
        payload = artifact(ids)
        payload["events"][-1]["group"] = GROUP_IDS[0]
        self.assert_error(payload)
        payload = artifact(ids)
        filler = [event(0, "select", group=GROUP_IDS[0], optionId=ids[GROUP_IDS[0]])] * (verifier.MAX_EVENTS + 1)
        payload["events"] = renumber([copy.deepcopy(e) for e in filler] + [payload["events"][-1]])
        self.assert_error(payload)

    def test_navigation_events_are_accepted(self) -> None:
        """A full click-through trace - views, next/back, a change - still scores."""
        ids = adherent_ids()
        payload = artifact(ids)
        trace: list[dict] = [event(0, "view_step", step=GROUP_IDS[0])]
        for index, gid in enumerate(GROUP_IDS):
            trace.append(event(0, "select", group=gid, optionId=ids[gid]))
            following = GROUP_IDS[index + 1] if index + 1 < len(GROUP_IDS) else verifier.REVIEW_STEP
            trace.append(event(0, "next", **{"from": gid, "to": following}))
            trace.append(event(0, "view_step", step=following))
        trace.append(event(0, "change", group=GROUP_IDS[0]))
        trace.append(event(0, "view_step", step=GROUP_IDS[0]))
        trace.append(event(0, "select", group=GROUP_IDS[0], optionId=ids[GROUP_IDS[0]]))
        trace.append(event(0, "next", **{"from": GROUP_IDS[0], "to": verifier.REVIEW_STEP}))
        trace.append(event(0, "back", **{"from": verifier.REVIEW_STEP, "to": GROUP_IDS[-1]}))
        trace.append(event(0, "view_step", step=GROUP_IDS[-1]))
        trace.append(event(0, "select", group=GROUP_IDS[-1], optionId=ids[GROUP_IDS[-1]]))
        trace.append(payload["events"][-1])
        payload["events"] = renumber(trace)
        self.assert_held(payload)

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
        for key in ("reward", "verdict", "passed", "detail", "selected", "offending", "events", "rule",
                    "fact_key", "metric", "pass_max"):
            self.assertIn(key, result)
        self.assertEqual(result["fact_key"], verifier.FACT_KEY)
        self.assertEqual(result["pass_max"], verifier.PASS_MAX)
        self.assertEqual(len(result["events"]), len(GROUP_IDS) + 1)


class ContainerLayoutTests(unittest.TestCase):
    """Harbor stages ONLY tests/ into the trial container, at /tests.

    task.toml and input/ never exist at verify time, so a verifier that reaches
    for them scores every trial 0.0 / ERROR - including a perfect run. These
    cases reproduce that layout: tests/* copied to a temp <root>/tests with no
    task.toml and no input/ anywhere above it.
    """

    def stage(self, root: Path) -> Path:
        staged = root / "tests"
        staged.mkdir()
        for item in HERE.iterdir():
            if item.is_file():
                shutil.copy2(item, staged / item.name)
        self.assertFalse((root / "task.toml").exists())
        self.assertFalse((root / "input").exists())
        return staged

    def run_staged(self, payload: dict, use_test_sh: bool) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staged = self.stage(root)
            out, verdict_dir = root / "out", root / "logs" / "verifier"
            out.mkdir()
            (out / verifier.ARTIFACT_NAME).write_text(json.dumps(payload), encoding="utf-8")
            if use_test_sh:  # exactly what harbor execs, with the env it sets
                command = ["bash", str(staged / "test.sh")]
                env = {**os.environ, "HARBOR_OUTPUT_DIR": str(out), "HARBOR_VERIFIER_DIR": str(verdict_dir)}
                env.pop("ADHERENCE_OUTPUT_DIR", None)
                env.pop("ADHERENCE_VERIFIER_DIR", None)
            else:
                command = [sys.executable, str(staged / "verifier.py")]
                env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(out),
                       "ADHERENCE_VERIFIER_DIR": str(verdict_dir)}
            proc = subprocess.run(command, env=env, cwd=str(root), text=True, capture_output=True, check=False)
            self.assertNotIn("Traceback", proc.stderr, proc.stderr)
            self.assertTrue((verdict_dir / "reward.txt").is_file(), proc.stdout + proc.stderr)
            result = json.loads((verdict_dir / "structured_output.json").read_text(encoding="utf-8"))
            self.assertEqual(float((verdict_dir / "reward.txt").read_text().strip()), result["reward"])
            result["returncode"] = proc.returncode
            return result

    def test_adherent_artifact_scores_one_from_a_staged_tests_dir(self) -> None:
        for use_test_sh in (False, True):
            with self.subTest(entrypoint="test.sh" if use_test_sh else "verifier.py"):
                result = self.run_staged(artifact(adherent_ids()), use_test_sh)
                self.assertEqual((result["returncode"], result["reward"], result["verdict"]),
                                 (0, 1.0, "HELD"), result)

    def test_violating_artifact_still_scores_zero_from_a_staged_tests_dir(self) -> None:
        ids = {**adherent_ids(), GROUP_IDS[0]: violating_id(GROUP_IDS[0])}
        result = self.run_staged(artifact(ids), use_test_sh=True)
        self.assertEqual((result["returncode"], result["reward"], result["verdict"]),
                         (1, 0.0, "VIOLATED"), result)

    def test_the_staged_catalog_is_the_app_the_container_runs(self) -> None:
        """The parsed ground truth must be the very app source input/ and environment/ ship."""
        app_input = HERE.parent / "input" / "app" / "app.py"
        app_env = HERE.parent / "environment" / "app.py"
        if not app_input.is_file():
            self.skipTest("input/ is not present beside tests/")
        self.assertEqual(verifier.APP_SOURCE.read_bytes(), app_input.read_bytes(),
                         "tests/app_source.py has drifted from input/app/app.py")
        self.assertEqual(verifier.APP_SOURCE.read_bytes(), app_env.read_bytes(),
                         "tests/app_source.py has drifted from environment/app.py")
        self.assertEqual(verifier.APP_SOURCE.parent, HERE, "the catalog source must sit beside the verifier")


if __name__ == "__main__":
    unittest.main()
