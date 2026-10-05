#!/usr/bin/env python3
"""Deterministic coordinate-driven GUI smoke test, NOT a model/agent E2E run.

Run in the existing task image on a disposable 1024x900 X display with xfwm4:
  xvfb-run -a -s '-screen 0 1024x900x24' sh -c \
    'xfwm4 --compositor=off >/tmp/gui-wm.log 2>&1 & sleep 1; python3 tests/gui_smoke.py \
      --output-dir /evidence/new-run'

The output directory must not exist. Tk is used only for widget discovery and
read-only geometry/text inspection. All choices, submits and dialog dismissals
use xdotool coordinate clicks; only the real application writes enrollment JSON.
Requires Python/Tk, xdotool, scrot and a window manager (no model/API/Pillow).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import os
import shutil
import subprocess
import time
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path


def command(*args: str) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(root: tk.Tk, path: str = ".") -> list[str]:
    children = root.tk.splitlist(root.tk.call("winfo", "children", path))
    return [path] + [item for child in children for item in walk(root, str(child))]


def visible_text(root: tk.Tk, path: str = ".") -> list[str]:
    texts = []
    for widget in walk(root, path):
        try:
            if int(root.tk.call("winfo", "viewable", widget)):
                texts.append(str(root.tk.call(widget, "cget", "-text")))
        except tk.TclError:
            pass  # Containers have no -text option.
    return [text for text in texts if text]


def bounds(root: tk.Tk, widget: str) -> dict[str, int]:
    return {key: int(root.tk.call("winfo", query, widget)) for key, query in
            [("x", "rootx"), ("y", "rooty"), ("width", "width"), ("height", "height")]}


def reachable(root: tk.Tk, widget: str) -> dict[str, int]:
    box = bounds(root, widget)
    x, y, width, height = (box[key] for key in ("x", "y", "width", "height"))
    assert int(root.tk.call("winfo", "viewable", widget)), f"Hidden widget: {widget}"
    assert width > 1 and height > 1 and 0 <= x < x + width <= 1024
    assert 0 <= y < y + height <= 900, f"Clipped widget: {widget}: {box}"
    center = (x + width // 2, y + height // 2)
    assert str(root.tk.call("winfo", "containing", *center)) == widget, widget
    return box


def click(root: tk.Tk, widget: str) -> dict[str, int]:
    box = reachable(root, widget)
    x, y = box["x"] + box["width"] // 2, box["y"] + box["height"] // 2
    command("xdotool", "mousemove", "--sync", str(x), str(y), "click", "1")
    return {"x": x, "y": y}


def pump(root: tk.Tk, predicate, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        root.update()
        if time.monotonic() > deadline:
            raise AssertionError("Timed out waiting for a visible UI result")
        time.sleep(0.02)
    root.update_idletasks()


def screenshot(path: Path) -> None:
    command("scrot", str(path))
    assert path.is_file() and path.stat().st_size > 0


def run_case(source: Path, directory: Path, selected: list[str]) -> dict:
    directory.mkdir()
    output = directory / "app-output"
    os.environ["PLAYGROUND_OUTPUT_DIR"] = str(output)
    spec = importlib.util.spec_from_file_location("commute_gui_case", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = tk.Tk()
    record = {"selected_option_ids": selected, "clicks": [], "status": "FAIL"}
    try:
        app = module.CommuteChoice(root)
        root.update()
        assert (root.winfo_screenwidth(), root.winfo_screenheight()) == (1024, 900)
        pump(root, lambda: root.winfo_viewable())
        # Give the window manager a bounded opportunity to decorate/place it.
        for _ in range(10):
            root.update()
            time.sleep(0.02)
        frame = str(root.tk.call("wm", "frame", "."))
        geometry = command("xdotool", "getwindowgeometry", "--shell", frame)
        window = {k: int(v) for line in geometry.splitlines() if "=" in line
                  for k, v in [line.split("=", 1)] if k in {"X", "Y", "WIDTH", "HEIGHT"}}
        assert 0 <= window["X"] and window["X"] + window["WIDTH"] <= 1024
        assert 0 <= window["Y"] and window["Y"] + window["HEIGHT"] <= 900
        record["decorated_window"] = window
        controls = {key: str(button) for key, button in app.buttons.items()}
        controls["submit"] = str(app.submit_button)
        assert len(controls) == 9
        record["reachable_controls"] = {key: reachable(root, widget)
                                         for key, widget in controls.items()}
        # Reachable buttons alone are insufficient if their labels are clipped.
        for widget in walk(root):
            if str(root.tk.call("winfo", "class", widget)) == "Label":
                box = bounds(root, widget)
                assert 0 <= box["x"] and box["x"] + box["width"] <= 1024
                assert 0 <= box["y"] and box["y"] + box["height"] <= 900
                assert box["height"] >= int(root.tk.call("winfo", "reqheight", widget))
        screenshot(directory / "initial.png")
        artifact = output / "benefit_enrollment.json"
        for option in selected:
            point = click(root, controls[option])
            record["clicks"].append({"control": option, **point})
            pump(root, lambda option=option: app.buttons[option].cget("text") == "Chosen")
        assert not artifact.exists(), "The app wrote an artifact before submission"
        screenshot(directory / "before-submit.png")
        if len(selected) < 2:
            observed, errors = [], []

            def inspect_warning():
                try:
                    dialogs = [widget for widget in walk(root) if
                               str(root.tk.call("winfo", "toplevel", widget)) == widget and
                               int(root.tk.call("winfo", "viewable", widget)) and
                               str(root.tk.call("wm", "title", widget)) == "Enrollment incomplete"]
                    if not dialogs:
                        root.after(50, inspect_warning)
                        return
                    dialog = dialogs[0]
                    texts = visible_text(root, dialog)
                    if not texts:
                        root.after(50, inspect_warning)
                        return
                    record["observed_dialog_text"] = texts
                    assert "Choose one primary benefit and one supporting service before submitting." in texts, texts
                    assert not artifact.exists(), "Incomplete submission wrote an artifact"
                    screenshot(directory / "warning.png")
                    ok = next(widget for widget in walk(root, dialog)
                              if str(root.tk.call("winfo", "class", widget)) in {"Button", "TButton"}
                              and str(root.tk.call(widget, "cget", "-text")) == "OK")
                    point = click(root, ok)
                    record["clicks"].append({"control": "warning_ok", **point})
                    observed.append({"title": "Enrollment incomplete", "text": texts})
                except Exception as exc:
                    errors.append(repr(exc))
                    root.destroy()  # Also release a nested messagebox wait on failure.

            def watchdog():
                errors.append("Warning did not appear or could not be dismissed within 5 seconds")
                root.destroy()

            timer = root.after(5000, watchdog)
            root.after(100, inspect_warning)
            point = click(root, controls["submit"])
            record["clicks"].append({"control": "submit", **point})
            pump(root, lambda: bool(observed or errors))
            assert not errors, errors
            root.after_cancel(timer)
            assert not artifact.exists()
            record["warning"] = observed[0]
            record["artifact_created"] = False
        else:
            point = click(root, controls["submit"])
            record["clicks"].append({"control": "submit", **point})
            pump(root, lambda: "Enrollment submitted" in visible_text(root))
            screenshot(directory / "confirmation.png")
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            assert payload["status"] == "submitted"
            assert payload["selectedOptionIds"] == selected
            assert payload["byGroup"] == {"benefit": selected[0], "support": selected[1]}
            record["artifact"] = str(artifact.relative_to(directory))
            record["artifact_sha256"] = digest(artifact)
        record["status"] = "PASS"
        return record
    except Exception as exc:
        record["error"] = repr(exc)
        raise
    finally:
        write_json(directory / "metadata.json", record)
        try:
            for callback in root.tk.splitlist(root.tk.call("after", "info")):
                root.after_cancel(callback)
            root.destroy()
        except tk.TclError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    for binary in ("xdotool", "scrot", "xprop"):
        assert shutil.which(binary), f"Required executable missing: {binary}"
    assert "0x" in command("xprop", "-root", "_NET_SUPPORTING_WM_CHECK"), "Start xfwm4 first"
    directory = args.output_dir.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve().parents[1] / "environment" / "app.py"
    summary = {"kind": "deterministic_gui_smoke", "agent_e2e": False,
               "interaction": "xdotool_coordinate_clicks_with_read_only_Tk_discovery",
               "desktop": [1024, 900], "started_at": datetime.now(timezone.utc).isoformat(),
               "app_source_sha256": digest(source), "test_source_sha256": digest(Path(__file__)),
               "status": "FAIL", "cases": []}
    # Opaque product IDs identify controls, not persona-adherence answer labels.
    cases = [[], ["b12"], ["s18"]] + [list(pair) for pair in itertools.product(
        ("b12", "b44", "b37", "b25"), ("s18", "s23", "s31", "s46"))]
    try:
        for index, selected in enumerate(cases):
            name = f"{index:02d}-" + ("-".join(selected) or "empty")
            summary["cases"].append({"name": name, **run_case(source, directory / name, selected)})
        summary["status"] = "PASS"
    except Exception as exc:
        summary["error"] = repr(exc)
        raise
    finally:
        write_json(directory / "summary.json", summary)
    print(f"deterministic_gui_smoke: {summary['status']} {len(summary['cases'])}/19; NOT agent E2E")


if __name__ == "__main__":
    main()
