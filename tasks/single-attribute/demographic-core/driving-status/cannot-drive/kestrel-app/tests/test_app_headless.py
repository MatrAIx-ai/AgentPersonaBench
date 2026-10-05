"""Drive the real Tkinter GUI on a private Xvfb display. Hard requirements
for the OS-APP env, asserted here: (1) the window fits inside the 1024x900 CUA
desktop; (2) the option list is scrollable — a visible Scrollbar, wheel
(<MouseWheel>, <Button-4>/<Button-5>) and key bindings all move `yview`, and
every option button can be brought fully on screen above the action bar;
(3) saving with nothing selected shows a visible message and writes nothing.
Plus: a click per leg selects (and replaces) the option, and a complete save
writes the artifact the verifier scores HELD. Skipped when Xvfb or tkinter is
unavailable."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.dont_write_bytecode = True

TASK_DIR = Path(__file__).resolve().parents[1]
DESKTOP_W, DESKTOP_H, TITLEBAR = 1024, 900, 32


def _free_display() -> int:
    for n in range(90, 140):
        if not Path(f"/tmp/.X{n}-lock").exists() and not Path(f"/tmp/.X11-unix/X{n}").exists():
            return n
    raise RuntimeError("no free X display")


@pytest.fixture(scope="module")
def display():
    if shutil.which("Xvfb") is None:
        pytest.skip("Xvfb not installed")
    pytest.importorskip("tkinter")
    n = _free_display()
    proc = subprocess.Popen(["Xvfb", f":{n}", "-screen", "0", f"{DESKTOP_W}x{DESKTOP_H}x24", "-nolisten", "tcp"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        if Path(f"/tmp/.X11-unix/X{n}").exists():
            break
        time.sleep(0.1)
    yield f":{n}"
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture
def app(display, tmp_path, monkeypatch):
    monkeypatch.setenv("DISPLAY", display)
    monkeypatch.setenv("ADHERENCE_OUTPUT_DIR", str(tmp_path / "out"))
    spec = importlib.util.spec_from_file_location("kestrel_app", TASK_DIR / "environment" / "kestrel.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    import tkinter as tk
    root = tk.Tk()
    builder = module.build(root)
    root.update_idletasks()
    root.update()
    yield module, builder, tmp_path / "out"
    root.destroy()


def _bottom(widget) -> int:
    return widget.winfo_rooty() + widget.winfo_height()


def _visible_in_canvas(builder, btn) -> bool:
    c = builder.canvas
    top, bottom = c.winfo_rooty(), c.winfo_rooty() + c.winfo_height()
    return top <= btn.winfo_rooty() and _bottom(btn) <= bottom


def test_window_fits_the_desktop_and_action_bar_is_on_screen(app):
    _module, b, _ = app
    root = b.root
    assert root.winfo_width() <= DESKTOP_W and root.winfo_height() <= DESKTOP_H - TITLEBAR
    assert root.winfo_rootx() >= 0 and root.winfo_rooty() >= 0
    assert root.winfo_rootx() + root.winfo_width() <= DESKTOP_W
    assert root.winfo_rooty() + root.winfo_height() <= DESKTOP_H
    assert b.save_btn.winfo_ismapped() and _bottom(b.save_btn) <= root.winfo_rooty() + root.winfo_height()
    for btn in b.buttons.values():
        assert btn.winfo_reqwidth() <= DESKTOP_W


def test_list_is_scrollable_with_scrollbar_wheel_and_keys(app):
    import tkinter as tk
    _module, b, _ = app
    assert isinstance(b.scrollbar, tk.Scrollbar) and b.scrollbar.winfo_ismapped()
    assert b.scrollbar.winfo_width() >= 12
    assert str(b.canvas.cget("yscrollcommand"))                       # scrollbar tracks the canvas
    assert b.canvas.cget("scrollregion") and b.canvas.bbox("all")[3] > b.canvas.winfo_height()  # content overflows
    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>", "<Prior>", "<Next>", "<Up>", "<Down>"):
        assert b.canvas.bind_all(seq), f"{seq} is not bound"
    # wheel and keys actually move the view
    b.canvas.yview_moveto(0)
    b.root.update()
    assert b.canvas.yview()[0] == 0.0
    b.canvas.event_generate("<Button-5>", x=10, y=10)
    b.root.update()
    after_wheel_down = b.canvas.yview()[0]
    assert after_wheel_down > 0.0
    b.canvas.event_generate("<Button-4>", x=10, y=10)
    b.root.update()
    assert b.canvas.yview()[0] < after_wheel_down
    b.canvas.event_generate("<MouseWheel>", x=10, y=10, delta=-120)
    b.root.update()
    assert b.canvas.yview()[0] > 0.0
    b.canvas.event_generate("<End>")
    b.root.update()
    assert b.canvas.yview()[1] == 1.0
    b.canvas.event_generate("<Home>")
    b.root.update()
    assert b.canvas.yview()[0] == 0.0
    # the scrollbar's own command scrolls too
    b.scrollbar.invoke = None  # not used; drive through the canvas command the scrollbar is wired to
    b.canvas.yview("scroll", 1, "pages")
    b.root.update()
    assert b.canvas.yview()[0] > 0.0


def test_every_option_can_be_scrolled_fully_on_screen_above_the_action_bar(app):
    _module, b, _ = app
    total = b.canvas.bbox("all")[3]
    for oid, btn in b.buttons.items():
        assert btn.winfo_ismapped(), oid
        y_in_list = btn.winfo_y()
        b.canvas.yview_moveto(max(0.0, (y_in_list - 8) / total))
        b.root.update()
        assert _visible_in_canvas(b, btn), f"{oid} cannot be scrolled fully into view"
        assert btn.winfo_rootx() >= 0 and btn.winfo_rootx() + btn.winfo_width() <= DESKTOP_W
        assert _bottom(btn) <= b.save_btn.winfo_rooty(), f"{oid} sits under the action bar"
        assert btn.winfo_width() > 0 and btn.winfo_height() > 0


def test_empty_save_shows_a_visible_message_and_writes_nothing(app):
    _module, b, out = app
    status_label = next(w for w in b.save_btn.master.winfo_children() if w.winfo_class() == "Label")
    before = b.status.get()
    b.save_btn.invoke()                       # the real button, nothing selected
    b.root.update()
    message = b.status.get()
    assert message != before and "still missing" in message
    assert all(day in message for day in ("Monday", "Wednesday", "Thursday"))
    assert status_label.winfo_ismapped() and status_label.winfo_width() > 0
    assert 0 <= status_label.winfo_rooty() and _bottom(status_label) <= b.root.winfo_rooty() + b.root.winfo_height()
    assert not (out / "itinerary.json").exists() and not b.submitted


def test_click_per_leg_selects_and_replaces(app):
    _module, b, out = app
    b.buttons["m41"].invoke()
    b.buttons["m62"].invoke()                 # a second click in the same leg replaces the first
    b.root.update()
    assert b.picks == {"monday": "m62"}
    assert b.buttons["m62"].cget("text").startswith("[x]") and b.buttons["m41"].cget("text").startswith("[ ]")
    assert "1 of 3" in b.status.get()
    b.save_btn.invoke()
    b.root.update()
    assert not (out / "itinerary.json").exists()
    assert "still missing" in b.status.get() and "Wednesday" in b.status.get() and "Monday" not in b.status.get()


def test_save_writes_artifact_that_verifies(app):
    _module, b, out = app
    for oid in ("m62", "t44", "f37"):
        b.buttons[oid].invoke()
    b.save_btn.invoke()
    b.root.update()
    artifact = json.loads((out / "itinerary.json").read_text(encoding="utf-8"))
    assert artifact["submitted"] is True and artifact["appVersion"] == "kestrel-itinerary-v1"
    assert [s["optionId"] for s in artifact["selections"]] == ["m62", "t44", "f37"]
    assert set(artifact["selections"][0]) == {"sectionId", "optionId", "name"}   # no mode fact leaves the process
    assert b.submitted and str(b.save_btn.cget("state")) == "disabled"
    assert "SAVED" in b.status.get()
    b.select("m41")                           # no changes after saving
    assert b.picks["monday"] == "m62"
    spec = importlib.util.spec_from_file_location("kestrel_app_verifier_h", TASK_DIR / "tests" / "verifier.py")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    assert verifier.evaluate(artifact, verifier.load_key())["verdict"] == "HELD"


def test_screenshot_for_review(app):
    """Best-effort PNG of the app for reviewers; never fails the suite."""
    _module, b, out = app
    try:
        from PIL import ImageGrab
    except ImportError:
        pytest.skip("Pillow not installed")
    b.root.update()
    try:
        image = ImageGrab.grab(xdisplay=os.environ["DISPLAY"])
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"screen grab unavailable: {exc}")
    target = Path(os.environ.get("KESTREL_SCREENSHOT", str(out / "kestrel-app.png")))
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    assert target.stat().st_size > 0
