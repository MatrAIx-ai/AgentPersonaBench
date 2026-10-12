"""Native startup focus regression checks (run under an X11 desktop)."""
import importlib.util
import os
from pathlib import Path
import time
import unittest

try:
    import tkinter as tk
except ImportError:
    tk = None


@unittest.skipUnless(tk is not None and os.environ.get("DISPLAY"), "requires Tk and DISPLAY")
class StartupFocusTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        path = Path(__file__).resolve().parents[1] / "environment" / "app.py"
        spec = importlib.util.spec_from_file_location("startup_timechoice", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.app = module.TimeChoice(self.root)
        self.pump()

    def tearDown(self):
        self.root.destroy()

    def pump(self):
        deadline = time.monotonic() + 0.15
        while time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.005)

    def assert_normal_switching(self):
        other = tk.Toplevel(self.root)
        other.title("Other application")
        other.geometry("220x100+790+20")
        other.lift()
        other.focus_force()
        self.pump()
        self.assertIs(self.root.focus_displayof().winfo_toplevel(), other)
        self.assertFalse(self.root.attributes("-topmost"))
        self.assertEqual((self.root.winfo_width(), self.root.winfo_height()), (1024, 866))

    def test_pointer_input_releases_startup_foreground(self):
        self.assertTrue(self.root.attributes("-topmost"))
        button = next(iter(self.app.buttons.values()))
        button.event_generate("<ButtonPress-1>", x=5, y=5)
        button.event_generate("<ButtonRelease-1>", x=5, y=5)
        self.pump()
        self.assertFalse(self.root.attributes("-topmost"))
        self.assert_normal_switching()

    def test_keyboard_input_releases_startup_foreground(self):
        self.assertTrue(self.root.attributes("-topmost"))
        self.root.focus_force()
        self.pump()
        self.root.event_generate("<KeyPress-Tab>")
        self.root.event_generate("<KeyRelease-Tab>")
        self.pump()
        self.assertFalse(self.root.attributes("-topmost"))
        self.assert_normal_switching()

    def test_initial_focus_is_reclaimed_before_first_input(self):
        other = tk.Toplevel(self.root)
        other.title("Runtime browser startup")
        other.focus_force()
        self.pump()
        self.assertIs(self.root.focus_displayof().winfo_toplevel(), self.root)
        self.assertTrue(self.root.attributes("-topmost"))


if __name__ == "__main__":
    unittest.main()
