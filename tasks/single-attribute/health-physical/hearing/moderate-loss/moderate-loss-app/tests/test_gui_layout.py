"""Real Tk text-fit regression; run on Linux with an X display (e.g. xvfb-run)."""
from __future__ import annotations

import ast
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(
    sys.platform.startswith("linux") and os.environ.get("DISPLAY"),
    "requires Linux Tk and an X display; run with xvfb-run",
)
class GuiLayoutTests(unittest.TestCase):
    def test_stale_intro_or_scenario_cannot_start_with_unchanged_options(self) -> None:
        source = Path(__file__).resolve().parents[1] / "environment/app.py"
        for name in ("INTRODUCTION", "QUESTIONS"):
            tree = ast.parse(source.read_text(encoding="utf-8"))
            node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
            value = ast.literal_eval(node.value)
            if name == "INTRODUCTION":
                value = value.replace("not reimbursed", "reimbursed")
            else:
                value[0]["scenario"] += " Everyone has already missed a sentence."
            node.value = ast.parse(repr(value), mode="eval").body
            ast.fix_missing_locations(tree)
            with self.subTest(changed=name), tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"ADHERENCE_OUTPUT_DIR": tmp}):
                with self.assertRaisesRegex(RuntimeError, "scenarios or option text"):
                    exec(compile(tree, str(source), "exec"), {"__name__": "material_guard_probe"})
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_every_step_fits_the_window_and_option_text_stays_in_its_card(self) -> None:
        import tkinter as tk

        source = Path(__file__).resolve().parents[1] / "environment" / "app.py"
        spec = importlib.util.spec_from_file_location("hearing_layout_app", source)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)

        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"ADHERENCE_OUTPUT_DIR": tmp}
        ):
            spec.loader.exec_module(module)
            root = tk.Tk()
            errors = []
            root.report_callback_exception = lambda typ, value, trace: errors.append(
                f"{typ.__name__}: {value}"
            )
            try:
                app = module.ForumListeningApp(root)
                root.update()
                canvas = app.c
                seen_options = set()
                for step in range(len(module.QUESTIONS) + 1):
                    with self.subTest(step=step):
                        app.go(step)
                        root.update()
                        # every piece of text and every clickable control sits inside the
                        # window, clear of the bottom band a window-manager title bar pushes off-screen
                        boxes = [canvas.bbox(i) for i in canvas.find_all() if canvas.type(i) == "text"]
                        boxes += list(app.hot.values())
                        for x0, y0, x1, y1 in boxes:
                            self.assertGreaterEqual(x0, -2)
                            self.assertLessEqual(x1, module.WINDOW_W + 2)
                            self.assertGreaterEqual(y0, -2)
                            self.assertLessEqual(y1, module.WINDOW_H - 24)
                        for text_id, option_id in app.text_owner.items():
                            cx0, cy0, cx1, cy1 = app.card_boxes[option_id]
                            x0, y0, x1, y1 = canvas.bbox(text_id)
                            self.assertTrue(cx0 <= x0 and x1 <= cx1 and cy0 <= y0 and y1 <= cy1 - 4,
                                            f"option {option_id} text overflows its card")
                            seen_options.add(option_id)
                        self.assertFalse(errors, errors)
                self.assertEqual(len(seen_options), 24)
            finally:
                root.destroy()


if __name__ == "__main__":
    unittest.main()
