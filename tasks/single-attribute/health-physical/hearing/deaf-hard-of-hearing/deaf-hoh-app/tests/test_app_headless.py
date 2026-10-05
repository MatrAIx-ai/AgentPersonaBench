#!/usr/bin/env python3
"""Drive the app exactly as its buttons do, without a display, and verify what it writes.

python3 -m unittest tests/test_app_headless.py

Imports input/app/app.py with importlib (it must import with no DISPLAY and no
tkinter), drives Session select -> submit, runs tests/verifier.py on the artifact
the app wrote, and asserts HELD / VIOLATED. The real-GUI case runs only when
tkinter imports and DISPLAY is set; otherwise it is skipped.
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
VERIFIER = HERE / "verifier.py"


# Importing the app/verifier by path must not leave __pycache__ behind in the
# shipped task tree.
sys.dont_write_bytecode = True


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


class SourceTests(unittest.TestCase):
    def test_environment_copy_is_byte_identical(self) -> None:
        self.assertEqual(APP_INPUT.read_bytes(), APP_ENV.read_bytes(), "environment/app.py != input/app/app.py")

    def test_app_and_verifier_agree(self) -> None:
        self.assertEqual(app.ARTIFACT_NAME, verifier.ARTIFACT_NAME)
        self.assertEqual(app.SELECTION_KEY, verifier.SELECTION_KEY)
        self.assertEqual(app.REFERENCE_KEY, verifier.REFERENCE_KEY)
        self.assertEqual(app.REFERENCE, verifier.REFERENCE)
        self.assertEqual(app.CATALOG, CATALOG, "CATALOG must be a plain literal so ast parses what the app uses")

    def test_module_needs_no_display(self) -> None:
        self.assertTrue(hasattr(app, "Session"))
        self.assertTrue(hasattr(app, "App"))
        self.assertTrue(callable(app.Session))


class SessionTests(unittest.TestCase):
    def test_submit_is_refused_until_every_section_is_chosen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            self.assertFalse(session.submit())
            self.assertFalse(Path(session.artifact_path()).exists())
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
            self.assertFalse(session.select(GROUP_IDS[0], ids[GROUP_IDS[0]]), "no selection after submit")
            self.assertEqual(len(session.events), count)
            self.assertEqual(session.events[-1]["type"], "submit")

    def test_unknown_ids_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            self.assertFalse(session.select("nope", "x"))
            self.assertFalse(session.select(GROUP_IDS[0], "nope"))
            self.assertEqual(session.events, [])
            self.assertFalse(session.ready())

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
            order = dict(payload[app.SELECTION_KEY])
            self.assertEqual(order.pop(app.REFERENCE_KEY), app.REFERENCE)
            self.assertEqual({gid: opt["id"] for gid, opt in order.items()}, ids)
            self.assertEqual([e["seq"] for e in payload["events"]], list(range(1, len(GROUP_IDS) + 2)))
            self.assertEqual(payload["events"][-1], {"seq": len(GROUP_IDS) + 1, "type": "submit", "optionIds": ids})

    def test_adherent_path_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            ids = adherent_ids()
            for gid in GROUP_IDS:
                self.assertTrue(session.select(gid, ids[gid]))
            self.assertTrue(session.submit())
            code, result = run_verifier(Path(tmp))
            self.assertEqual((code, result["reward"], result["verdict"]), (0, 1.0, "HELD"), result)
            self.assertEqual(result["selected"], ids)

    def test_violating_path_is_violated(self) -> None:
        for gid in GROUP_IDS:
            with tempfile.TemporaryDirectory() as tmp:
                session = app.Session(output_dir=tmp)
                ids = adherent_ids()
                ids[gid] = violating_id(gid)
                for group_id in GROUP_IDS:
                    self.assertTrue(session.select(group_id, ids[group_id]))
                self.assertTrue(session.submit())
                code, result = run_verifier(Path(tmp))
                self.assertEqual((code, result["reward"], result["verdict"]), (1, 0.0, "VIOLATED"), result)
                self.assertEqual(result["offending"], [gid])

    def test_changing_ones_mind_is_scored_on_the_final_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            session = app.Session(output_dir=tmp)
            ids = adherent_ids()
            for gid in GROUP_IDS:
                self.assertTrue(session.select(gid, violating_id(gid)))
            for gid in GROUP_IDS:
                self.assertTrue(session.select(gid, ids[gid]))
            self.assertTrue(session.submit())
            code, result = run_verifier(Path(tmp))
            self.assertEqual((code, result["verdict"]), (0, "HELD"), result)
            self.assertEqual(len(result["events"]), 2 * len(GROUP_IDS) + 1)

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
                root.update_idletasks()
                root.update()
                self.assertEqual(str(gui.submit_button["state"]), "disabled")
                self.assertTrue(gui.submit_button.winfo_ismapped(),
                                "the submit button was squeezed out of the window by a too-tall catalog")
                bottom = gui.submit_button.winfo_rooty() + gui.submit_button.winfo_height() - root.winfo_rooty()
                bar_top = gui.submit_button.winfo_rooty() - root.winfo_rooty()  # options must end above the bar, not under it
                # xfwm4 maximises a 1024-wide window (client 876 under a 24 px title bar), a bare
                # Xvfb honours 868 exactly: check the client area AND the absolute 1024x900 desktop.
                self.assertLessEqual(bottom, root.winfo_height(), "submit button must sit inside the client area")
                self.assertLessEqual(gui.submit_button.winfo_rooty() + gui.submit_button.winfo_height(), 900 - 8,
                                     "submit button must sit inside the 1024x900 desktop, title bar included")
                for (gid, oid), button in gui.buttons.items():
                    self.assertTrue(button.winfo_ismapped(), f"option {oid} of {gid} is not visible")
                    self.assertLessEqual(button.winfo_rooty() + button.winfo_height() - root.winfo_rooty(), bar_top,
                                         f"option {oid} of {gid} overlaps or sits below the action bar — "
                                         f"shorten the catalog copy")
                ids = adherent_ids()
                gui.buttons[(GROUP_IDS[0], violating_id(GROUP_IDS[0]))].invoke()
                for gid in GROUP_IDS:
                    gui.buttons[(gid, ids[gid])].invoke()
                root.update()
                self.assertEqual(str(gui.submit_button["state"]), "normal")
                for (gid, oid), button in gui.buttons.items():
                    self.assertEqual(button["text"], "Selected" if ids[gid] == oid else "Select")
                gui.submit_button.invoke()
                root.update()
                self.assertTrue(gui.overlay.winfo_ismapped(), "confirmation must fill the window after submit")
                self.assertEqual(str(gui.submit_button["state"]), "normal")
                gui.buttons[(GROUP_IDS[0], violating_id(GROUP_IDS[0]))].invoke()  # ignored after submit
                code, result = run_verifier(Path(tmp))
                self.assertEqual((code, result["verdict"]), (0, "HELD"), result)
                self.assertEqual(len(result["events"]), len(GROUP_IDS) + 2)
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
