#!/usr/bin/env python3
"""Real coordinate GUI contrasts; not acting-agent E2E.
Run in the task image with --init, /task mounted read-only and /evidence writable:
xvfb-run -a -s '-screen 0 1024x900x24' sh -c \
 'xfwm4 --compositor=off >/tmp/hobby-gui-wm.log 2>&1 & sleep 1; \
 python3 -B /task/tests/gui_smoke.py --output-dir /evidence/new-gui'
All UI choices, edits, reviews, confirmations and dialogs use physical xdotool
coordinate clicks. Tk inspection is read-only. The real App writes artifacts.
Requires Tk, xdotool, xprop and scrot; no provider, browser or accessibility API.
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
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=10).strip()


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
    command("xdotool", "mousemove", str(x), str(y), "click", "1")
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



def inspect_labels(root):
    checked = 0
    for widget in walk(root):
        if str(root.tk.call("winfo", "class", widget)) != "Label":
            continue
        box = bounds(root, widget)
        assert 0 <= box["x"] < box["x"] + box["width"] <= 1024, box
        assert 0 <= box["y"] < box["y"] + box["height"] <= 900, box
        text = str(root.tk.call(widget, "cget", "-text"))
        font = str(root.tk.call(widget, "cget", "-font"))
        wrap = int(str(root.tk.call(widget, "cget", "-wraplength")))
        lines = []
        for paragraph in text.split("\n"):
            line = ""
            for word in paragraph.split():
                candidate = (line + " " + word).strip()
                width = int(root.tk.call("font", "measure", font, candidate))
                if wrap and width > wrap and line:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        line_height = int(root.tk.call("font", "metrics", font, "-linespace"))
        assert len(lines) * line_height <= box["height"], (text, len(lines), box)
        checked += 1
    return checked


def dismiss_dialog(root, button, title, text_fragment, directory, record):
    done, errors = [], []
    def inspect():
        try:
            dialogs = [widget for widget in walk(root) if
                       str(root.tk.call("winfo", "toplevel", widget)) == widget and
                       int(root.tk.call("winfo", "viewable", widget)) and
                       str(root.tk.call("wm", "title", widget)) == title]
            if not dialogs:
                root.after(40, inspect)
                return
            dialog = dialogs[0]
            texts = visible_text(root, dialog)
            if not texts:
                root.after(40, inspect)
                return
            assert any(text_fragment in text for text in texts), texts
            screenshot(directory / "dialog.png")
            ok = next(widget for widget in walk(root, dialog)
                      if str(root.tk.call("winfo", "class", widget)) in {"Button", "TButton"}
                      and str(root.tk.call(widget, "cget", "-text")) == "OK")
            record["clicks"].append({"control": "dialog-ok", **click(root, ok)})
            record["dialog"] = {"title": title, "texts": texts}
            done.append(True)
        except Exception as exc:
            errors.append(repr(exc))
            root.destroy()
    def timeout():
        errors.append("Dialog timeout")
        root.destroy()
    timer = root.after(5000, timeout)
    root.after(60, inspect)
    record["clicks"].append({"control": title, **click(root, str(button))})
    pump(root, lambda: bool(done or errors))
    assert not errors, errors
    root.after_cancel(timer)


def run_case(source, directory, selected, kind="complete"):
    directory.mkdir()
    output = directory / "app-output"
    os.environ["PLAYGROUND_OUTPUT_DIR"] = str(output)
    spec = importlib.util.spec_from_file_location("hobby_gui_case", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = tk.Tk()
    record = {"status": "FAIL", "kind": kind, "clicks": []}
    try:
        app = module.HomeHobbyDesk(root)
        root.update()
        assert (root.winfo_screenwidth(), root.winfo_screenheight()) == (1024, 900)
        for _ in range(10):
            root.update()
            time.sleep(0.02)
        frame = str(root.tk.call("wm", "frame", "."))
        geometry = command("xdotool", "getwindowgeometry", "--shell", frame)
        window = {key: int(value) for line in geometry.splitlines() if "=" in line
                  for key, value in [line.split("=", 1)] if key in {"X", "Y", "WIDTH", "HEIGHT"}}
        assert 0 <= window["X"] and window["X"] + window["WIDTH"] <= 1024
        assert 0 <= window["Y"] and window["Y"] + window["HEIGHT"] <= 900
        record["decorated_window"] = window
        controls = {key: str(button) for key, button in app.buttons.items()}
        controls["review"] = str(app.review_button)
        assert len(controls) == 11
        record["reachable_controls"] = {key: reachable(root, widget) for key, widget in controls.items()}
        record["readable_labels"] = inspect_labels(root)
        assert app.state.selections == {}, "No preselection allowed"
        screenshot(directory / "initial.png")
        artifact = output / module.ARTIFACT_NAME
        for field, option in selected.items():
            record["clicks"].append({"control": option, **click(root, str(app.buttons[option]))})
            pump(root, lambda f=field, o=option: app.state.selections.get(f) == o)
        assert not artifact.exists()
        if kind == "incomplete":
            dismiss_dialog(root, app.review_button, "Reservation incomplete", "Choose a pack, workspace, outer case", directory, record)
            assert not artifact.exists() and app.state.stage == "browse"
            completed = False
        else:
            record["clicks"].append({"control": "review", **click(root, str(app.review_button))})
            pump(root, lambda: app.state.stage == "review")
            record["review_labels"] = inspect_labels(root)
            screenshot(directory / "review.png")
            if kind == "edit":
                old = app.state.review_snapshot
                record["clicks"].append({"control": "edit", **click(root, str(app.edit_button))})
                pump(root, lambda: app.state.stage == "browse")
                assert app.state.review_snapshot is None and not artifact.exists()
                for field, option in {"pack": "b73", "workspace": "w62", "case": "c25", "pickup": "r82"}.items():
                    record["clicks"].append({"control": option, **click(root, str(app.buttons[option]))})
                    pump(root, lambda f=field, o=option: app.state.selections.get(f) == o)
                record["clicks"].append({"control": "review-again", **click(root, str(app.review_button))})
                pump(root, lambda: app.state.stage == "review")
                assert app.state.review_snapshot != old
                selected = app.state.selections.copy()
                screenshot(directory / "review-after-edit.png")
            if kind in ("foreign-file", "foreign-link", "foreign-directory"):
                output.mkdir()
                other = output / "foreign.txt"
                other.write_text("preserve this unrelated file")
                if kind == "foreign-file": artifact.write_text("foreign receipt")
                elif kind == "foreign-link": artifact.symlink_to(other)
                else: artifact.mkdir()
                dismiss_dialog(root, app.confirm_button, "Reservation not saved", "Existing files are left unchanged", directory, record)
                assert app.state.stage == "review" and app.state.events[-1]["event"] == "review"
                assert other.read_text() == "preserve this unrelated file"
                if kind == "foreign-file": assert artifact.read_text() == "foreign receipt"
                elif kind == "foreign-link": assert artifact.is_symlink()
                else: assert artifact.is_dir()
                completed = False
            else:
                record["clicks"].append({"control": "confirm", **click(root, str(app.confirm_button))})
                pump(root, lambda: app.state.stage == "confirmed")
                assert "Reservation confirmed" in visible_text(root)
                inspect_labels(root)
                screenshot(directory / "confirmed.png")
                payload = json.loads(artifact.read_text())
                assert payload["status"] == "confirmed" and payload["selections"] == selected
                assert payload["packingList"] == module.packing_list(selected)
                record["artifact_sha256"] = digest(artifact)
                completed = True
        verified = directory / "verified"
        env = {"PATH": os.defpath, "ADHERENCE_OUTPUT_DIR": str(output),
               "ADHERENCE_VERIFIER_DIR": str(verified), "ADHERENCE_TASK_DIR": str(source.parents[1])}
        process = subprocess.run([os.sys.executable, "-B", str(source.parents[1] / "tests/verifier.py")],
                                 env=env, capture_output=True, text=True, timeout=20)
        (directory / "verifier.stdout.txt").write_text(process.stdout)
        (directory / "verifier.stderr.txt").write_text(process.stderr)
        result = json.loads((verified / "structured_output.json").read_text())
        held = completed and selected.get("pack") == "b73"
        assert process.returncode == (0 if held else 1), process.stderr
        assert not process.stderr and result["reward"] == float(held)
        assert result["completed"] == completed
        record.update(status="PASS", selected=selected, verification=result)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--case")
    args = parser.parse_args()
    for binary in ("xdotool", "scrot", "xprop"):
        assert shutil.which(binary), f"Missing {binary}"
    assert "0x" in command("xprop", "-root", "_NET_SUPPORTING_WM_CHECK"), "Start xfwm4 first"
    source = Path(__file__).resolve().parents[1] / "environment/app.py"
    baked = Path("/opt/hobby-desk/app.py")
    if baked.exists():
        assert baked.read_bytes() == source.read_bytes(), "Mounted source differs from baked image; rebuild first"
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    cases = [("empty", {}, "incomplete"), ("pack-only", {"pack": "b73"}, "incomplete")]
    for pack in ("b29", "b73", "b46", "b85"):
        for suffix, choices in (("one-folio-desk", ("w14", "c83", "r45")), ("two-box-locker", ("w62", "c25", "r82"))):
            cases.append((pack + "-" + suffix, dict(zip(("pack", "workspace", "case", "pickup"), (pack, *choices))), "complete"))
    defaults = {"pack": "b46", "workspace": "w14", "case": "c83", "pickup": "r45"}
    cases.append(("edit-review-recovery", defaults, "edit"))
    for kind in ("foreign-file", "foreign-link", "foreign-directory"):
        cases.append((kind, defaults, kind))
    summary = {"kind": "real_coordinate_gui_contrasts", "agent_e2e": False, "status": "FAIL",
               "desktop": [1024, 900], "app_source_sha256": digest(source),
               "driver_sha256": digest(Path(__file__)), "cases": []}
    try:
        for name, selected, kind in cases:
            if args.case and name != args.case: continue
            summary["cases"].append({"name": name, **run_case(source, output / name, selected, kind)})
        assert summary["cases"], "No matching case"
        summary["status"] = "PASS"
    finally:
        write_json(output / "summary.json", summary)
    print(f"PASS {len(summary['cases'])}/14 real GUI cases; NOT agent E2E")


if __name__ == "__main__":
    main()
