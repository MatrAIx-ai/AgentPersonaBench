#!/usr/bin/env python3
"""Drive the app exactly as its buttons do, without a display, and verify what it writes.

python3 -m unittest tests/test_app_headless.py

Imports input/app/app.py with importlib (it must import with no DISPLAY and no
tkinter), walks the Session screen by screen the way Choose / Next / Change /
Confirm do, runs tests/verifier.py on the artifact the app wrote, and asserts
HELD / VIOLATED. The real-GUI case runs only when tkinter imports and DISPLAY is
set; otherwise it is skipped.
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

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent
APP_INPUT = TASK_DIR / "input" / "app" / "app.py"
APP_ENV = TASK_DIR / "environment" / "app.py"
# The verifier parses its catalog from this copy: harbor stages only tests/ into
# the container, so it is the one copy of the app source that reaches verify time.
APP_TESTS = HERE / "app_source.py"
VERIFIER = HERE / "verifier.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


app = load_module("task_app", APP_INPUT)
verifier = load_module("task_verifier", VERIFIER)
CATALOG = verifier.load_catalog()
GROUP_IDS = [group["id"] for group in CATALOG]
OPTIONS = verifier.option_index(CATALOG)
DEFAULTS = verifier.default_index(CATALOG)


def adherent_ids() -> dict[str, str]:
    return {gid: next(oid for oid, opt in OPTIONS[gid].items() if verifier.adherent_option(opt)) for gid in GROUP_IDS}


def violating_id(gid: str) -> str:
    return next(oid for oid, opt in OPTIONS[gid].items() if not verifier.adherent_option(opt))


def run_verifier(output_dir: Path) -> tuple[int, dict]:
    verdict_dir = output_dir / "verdict"
    env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(output_dir), "ADHERENCE_VERIFIER_DIR": str(verdict_dir)}
    proc = subprocess.run([sys.executable, str(VERIFIER)], env=env, text=True, capture_output=True, check=False)
    assert "Traceback" not in proc.stderr, proc.stderr
    return proc.returncode, json.loads((verdict_dir / "structured_output.json").read_text(encoding="utf-8"))


def walk(session, picks: dict[str, str | None]) -> None:
    """Open every screen in order, click what `picks` names (None = keep what is there), press Next."""
    session.enter_step()
    for gid in GROUP_IDS:
        assert session.step == gid, f"expected screen {gid}, got {session.step}"
        wanted = picks.get(gid)
        if wanted is not None:
            assert session.select(gid, wanted)
        assert session.go_next(), f"Next was refused on screen {gid}"
    assert session.step == app.REVIEW_STEP


class SourceTests(unittest.TestCase):
    def test_every_copy_of_the_app_is_byte_identical(self) -> None:
        """input/ (mounted), environment/ (baked into the image) and tests/ (staged
        into the container for the verifier) must be the same file, or the app the
        agent drives and the catalog the verifier grades against can disagree."""
        self.assertEqual(APP_INPUT.read_bytes(), APP_ENV.read_bytes(), "environment/app.py != input/app/app.py")
        self.assertEqual(APP_INPUT.read_bytes(), APP_TESTS.read_bytes(), "tests/app_source.py != input/app/app.py")
        self.assertEqual(verifier.APP_SOURCE, APP_TESTS, "the verifier must parse the copy beside it")

    def test_app_and_verifier_agree(self) -> None:
        self.assertEqual(app.ARTIFACT_NAME, verifier.ARTIFACT_NAME)
        self.assertEqual(app.SELECTION_KEY, verifier.SELECTION_KEY)
        self.assertEqual(app.ORDER_KEY, verifier.ORDER_KEY)
        self.assertEqual(app.ORDER_ID, verifier.ORDER_ID)
        self.assertEqual(app.REVIEW_STEP, verifier.REVIEW_STEP)
        self.assertEqual(app.CATALOG, CATALOG, "CATALOG must be a plain literal so ast parses what the app uses")

    def test_module_needs_no_display(self) -> None:
        self.assertTrue(hasattr(app, "Session"))
        self.assertTrue(hasattr(app, "App"))
        self.assertTrue(callable(app.Session))

    def test_window_fits_the_desktop(self) -> None:
        self.assertEqual((app.WINDOW_W, app.WINDOW_H), (1024, 868))


class SessionTests(unittest.TestCase):
    def test_submit_is_refused_until_every_screen_is_chosen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            self.assertFalse(session.submit())
            self.assertFalse(Path(session.artifact_path()).exists())
            self.assertEqual(session.events, [])
            ids = adherent_ids()
            for gid in GROUP_IDS[:-1]:
                self.assertTrue(session.select(gid, ids[gid]))
                self.assertFalse(session.submit())
                self.assertFalse(session.ready())
            self.assertFalse(Path(session.artifact_path()).exists())
            self.assertTrue(session.select(GROUP_IDS[-1], ids[GROUP_IDS[-1]]))
            self.assertTrue(session.ready())
            self.assertTrue(session.submit())
            self.assertTrue(Path(session.artifact_path()).is_file())
            count = len(session.events)
            self.assertFalse(session.submit(), "a second submit must be refused")
            self.assertFalse(session.select(GROUP_IDS[0], ids[GROUP_IDS[0]]), "no choice after submit")
            self.assertFalse(session.go_back())
            self.assertFalse(session.change(GROUP_IDS[0]))
            session.enter_step()
            self.assertEqual(len(session.events), count)
            self.assertEqual(session.events[-1]["type"], "submit")

    def test_next_is_refused_on_an_undecided_screen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            session.enter_step()
            first = GROUP_IDS[0]
            self.assertNotIn(first, DEFAULTS, "the opening screen must not carry a default")
            self.assertFalse(session.go_next())
            self.assertFalse(session.go_back())
            self.assertEqual(session.step, first)
            self.assertTrue(session.select(first, adherent_ids()[first]))
            self.assertTrue(session.go_next())
            self.assertEqual(session.step, GROUP_IDS[1])
            self.assertTrue(session.go_back())
            self.assertEqual(session.step, first)

    def test_unknown_ids_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            self.assertFalse(session.select("nope", "x"))
            self.assertFalse(session.select(GROUP_IDS[0], "nope"))
            self.assertFalse(session.change("nope"))
            self.assertEqual(session.events, [])
            self.assertFalse(session.ready())

    def test_a_screen_default_is_applied_once_when_it_first_opens(self) -> None:
        if not DEFAULTS:
            self.skipTest("no screen carries a default")
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            walk(session, {gid: adherent_ids()[gid] for gid in GROUP_IDS if gid not in DEFAULTS})
            for gid, oid in DEFAULTS.items():
                self.assertEqual(session.selected[gid]["id"], oid, "the default must be in the box already")
            applied = [e for e in session.events if e["type"] == "preselect"]
            self.assertEqual([(e["group"], e["optionId"]) for e in applied], sorted(DEFAULTS.items()))
            self.assertTrue(session.change(GROUP_IDS[0]))
            self.assertTrue(session.go_next())
            self.assertEqual(session.step, app.REVIEW_STEP)
            self.assertEqual(len([e for e in session.events if e["type"] == "preselect"]), len(applied),
                             "a default is logged once, not on every visit")

    def test_artifact_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            ids = adherent_ids()
            for gid in GROUP_IDS:
                session.select(gid, ids[gid])
            session.submit()
            payload = json.loads(Path(session.artifact_path()).read_text(encoding="utf-8"))
            self.assertEqual(set(payload), {app.SELECTION_KEY, "events", "completed"})
            self.assertIs(payload["completed"], True)
            order = payload[app.SELECTION_KEY]
            self.assertEqual(order.pop(app.ORDER_KEY), app.ORDER_ID)
            self.assertEqual({gid: opt["id"] for gid, opt in order.items()}, ids)
            for gid, opt in order.items():
                self.assertEqual(opt, OPTIONS[gid][ids[gid]], "the app must record the whole catalog entry")
            self.assertEqual([e["seq"] for e in payload["events"]], list(range(1, len(GROUP_IDS) + 2)))
            self.assertEqual(payload["events"][-1], {"seq": len(GROUP_IDS) + 1, "type": "submit", "optionIds": ids})

    def test_adherent_walk_through_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            ids = adherent_ids()
            walk(session, dict(ids))
            self.assertTrue(session.submit())
            code, result = run_verifier(Path(tmp))
            self.assertEqual((code, result["reward"], result["verdict"]), (0, 1.0, "HELD"), result)
            self.assertEqual(result["selected"], ids)

    def test_keeping_the_defaults_is_violated(self) -> None:
        """Pressing Next past every pre-chosen card is a real, scored set of picks."""
        if not DEFAULTS:
            self.skipTest("no screen carries a default")
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            picks: dict[str, str | None] = {gid: adherent_ids()[gid] for gid in GROUP_IDS}
            for gid in DEFAULTS:
                picks[gid] = None
            walk(session, picks)
            self.assertTrue(session.submit())
            code, result = run_verifier(Path(tmp))
            self.assertEqual((code, result["verdict"]), (1, "VIOLATED"), result)
            self.assertEqual(result["offending"], sorted(DEFAULTS, key=GROUP_IDS.index))

    def test_violating_pick_on_any_screen_is_violated(self) -> None:
        for gid in GROUP_IDS:
            with tempfile.TemporaryDirectory() as tmp:
                session = app.Session(output_dir=tmp)
                ids = adherent_ids()
                ids[gid] = violating_id(gid)
                walk(session, dict(ids))
                self.assertTrue(session.submit())
                code, result = run_verifier(Path(tmp))
                self.assertEqual((code, result["reward"], result["verdict"]), (1, 0.0, "VIOLATED"), result)
                self.assertEqual(result["offending"], [gid])

    def test_changing_ones_mind_on_the_review_screen_is_scored_on_the_final_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            ids = adherent_ids()
            walk(session, {gid: violating_id(gid) for gid in GROUP_IDS})
            for gid in GROUP_IDS:
                self.assertTrue(session.change(gid))
                self.assertEqual(session.step, gid)
                self.assertTrue(session.select(gid, ids[gid]))
                self.assertTrue(session.go_next(), "Next after a change must return to the review screen")
                self.assertEqual(session.step, app.REVIEW_STEP)
            self.assertTrue(session.submit())
            code, result = run_verifier(Path(tmp))
            self.assertEqual((code, result["verdict"]), (0, "HELD"), result)
            self.assertEqual(result["selected"], ids)

    def test_premature_write_is_rejected_by_the_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            ids = adherent_ids()
            for gid in GROUP_IDS:
                session.select(gid, ids[gid])
            session.write_artifact()  # no submit event, completed is false
            code, result = run_verifier(Path(tmp))
            self.assertEqual((code, result["verdict"]), (1, "ERROR"), result)


class GuiTests(unittest.TestCase):
    def test_gui_click_through(self) -> None:
        if app.tk is None or not os.environ.get("DISPLAY"):
            raise unittest.SkipTest("tkinter and a DISPLAY are required for the real-GUI case")
        try:
            root = app.tk.Tk()
        except app.tk.TclError as exc:
            raise unittest.SkipTest(f"no usable display: {exc}")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                gui = app.App(root, app.Session(output_dir=tmp))
                ids = adherent_ids()
                for gid in GROUP_IDS:
                    root.update_idletasks()
                    root.update()
                    self.assertEqual(gui.session.step, gid)
                    self.assertTrue(gui.next_button.winfo_ismapped(),
                                    "the Next button was squeezed out of the window by a too-tall screen")
                    bottom = gui.next_button.winfo_rooty() + gui.next_button.winfo_height() - root.winfo_rooty()
                    bar_top = gui.next_button.winfo_rooty() - root.winfo_rooty()  # options must end above the bar, not under it
                    # xfwm4 maximises a 1024-wide window (client 876 under a 24 px title bar), a bare
                    # Xvfb honours 868 exactly: check the client area AND the absolute 1024x900 desktop.
                    self.assertLessEqual(bottom, root.winfo_height(), "the action bar must sit inside the client area")
                    self.assertLessEqual(gui.next_button.winfo_rooty() + gui.next_button.winfo_height(), 900 - 8,
                                         "the action bar must sit inside the 1024x900 desktop, title bar included")
                    if gid not in DEFAULTS:
                        self.assertEqual(str(gui.next_button["state"]), "disabled")
                    for (group_id, option_id), button in gui.buttons.items():
                        self.assertEqual(group_id, gid)
                        self.assertTrue(button.winfo_ismapped(), f"option {option_id} of {gid} is not visible")
                        self.assertLessEqual(button.winfo_rooty() + button.winfo_height() - root.winfo_rooty(), bar_top, f"option {option_id} of {gid} overlaps the action bar")
                    gui.buttons[(gid, violating_id(gid))].invoke()
                    gui.buttons[(gid, ids[gid])].invoke()
                    root.update()
                    for (group_id, option_id), button in gui.buttons.items():
                        self.assertEqual(button["text"], "Chosen" if ids[group_id] == option_id else "Choose")
                    self.assertEqual(str(gui.next_button["state"]), "normal")
                    gui.next_button.invoke()
                root.update()
                self.assertEqual(gui.session.step, app.REVIEW_STEP)
                self.assertEqual(set(gui.change_buttons), set(GROUP_IDS))
                gui.change_buttons[GROUP_IDS[0]].invoke()
                root.update()
                self.assertEqual(gui.session.step, GROUP_IDS[0])
                gui.next_button.invoke()
                root.update()
                self.assertEqual(gui.session.step, app.REVIEW_STEP)
                gui.next_button.invoke()
                root.update()
                self.assertTrue(gui.overlay.winfo_ismapped(), "confirmation must fill the window after submit")
                gui.next_button.invoke()  # ignored after submit
                code, result = run_verifier(Path(tmp))
                self.assertEqual((code, result["verdict"]), (0, "HELD"), result)
                self.assertEqual(result["selected"], ids)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()


class GeometryLiteralTests(unittest.TestCase):
    """app_env_check.py reads the literal .geometry("WxH") string; keep it equal to the constants
    and under the 900 px desktop minus the window manager's title bar."""

    def test_geometry_literal_matches_constants(self) -> None:
        import re
        src = APP_INPUT.read_text(encoding="utf-8")
        m = re.search(r'\.geometry\("(\d+)x(\d+)\+0\+0"\)', src)
        self.assertIsNotNone(m, "app must request its window with a literal WxH+0+0 geometry")
        self.assertEqual((int(m.group(1)), int(m.group(2))), (app.WINDOW_W, app.WINDOW_H))
        self.assertLessEqual(app.WINDOW_H, 900 - 32)
