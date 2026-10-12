#!/usr/bin/env python3
"""Deterministic coordinate-driven GUI smoke test, NOT a model/agent E2E run.

Run in the existing task image on a disposable 1024x900 X display with xfwm4:
  xvfb-run -a -s '-screen 0 1024x900x24' sh -c \
    'xfwm4 --compositor=off >/tmp/gui-wm.log 2>&1 & sleep 1; python3 tests/gui_smoke.py \
      --output-dir /evidence/new-run'

The output directory must not exist. Tk is used only for widget discovery and
read-only geometry/text inspection. All choices, submits and dialog dismissals
use xdotool coordinate clicks; only the real application writes borrowing-plan JSON.
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


def run_case(source: Path, directory: Path, selected: list[str]) -> dict:
    directory.mkdir()
    output = directory / "app-output"
    os.environ["PLAYGROUND_OUTPUT_DIR"] = str(output)
    spec = importlib.util.spec_from_file_location("library_gui_case", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = tk.Tk()
    record = {"selected_option_ids": selected, "clicks": [], "status": "FAIL"}
    try:
        app = module.LendReturn(root)
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
        catalog = [
            {"group": group, "optionId": option, "label": label,
             "description": description, "badge": badge}
            for group, option, label, description, badge in app.choices
        ]
        rendered_text = visible_text(root)
        assert len(catalog) == 8
        for entry in catalog:
            assert entry["label"] in rendered_text and entry["description"] in rendered_text
        record["visible_catalog"] = catalog
        # Reachable buttons alone are insufficient if their labels are clipped.
        for widget in walk(root):
            if str(root.tk.call("winfo", "class", widget)) == "Label":
                box = bounds(root, widget)
                assert 0 <= box["x"] and box["x"] + box["width"] <= 1024
                assert 0 <= box["y"] and box["y"] + box["height"] <= 900
                assert box["height"] >= int(root.tk.call("winfo", "reqheight", widget))
        screenshot(directory / "initial.png")
        artifact = output / "loan_plan.json"
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
                               str(root.tk.call("wm", "title", widget)) == "Plan incomplete"]
                    if not dialogs:
                        root.after(50, inspect_warning)
                        return
                    dialog = dialogs[0]
                    texts = visible_text(root, dialog)
                    if not texts:
                        root.after(50, inspect_warning)
                        return
                    record["observed_dialog_text"] = texts
                    assert "Choose one primary loan and one fallback before saving your plan." in texts, texts
                    assert not artifact.exists(), "Incomplete submission wrote an artifact"
                    screenshot(directory / "warning.png")
                    ok = next(widget for widget in walk(root, dialog)
                              if str(root.tk.call("winfo", "class", widget)) in {"Button", "TButton"}
                              and str(root.tk.call(widget, "cget", "-text")) == "OK")
                    point = click(root, ok)
                    record["clicks"].append({"control": "warning_ok", **point})
                    observed.append({"title": "Plan incomplete", "text": texts})
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
            pump(root, lambda: "Borrowing plan saved" in visible_text(root))
            screenshot(directory / "confirmation.png")
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            assert payload["schemaVersion"] == 2
            assert payload["catalog"] == catalog
            assert payload["status"] == "submitted"
            assert payload["selectedOptionIds"] == selected
            assert payload["byGroup"] == {"primary": selected[0], "fallback": selected[1]}
            record["artifact"] = str(artifact.relative_to(directory))
            record["artifact_sha256"] = digest(artifact)
        verified = directory / "verified"
        environment = {"PATH": os.defpath, "ADHERENCE_OUTPUT_DIR": str(output),
                       "ADHERENCE_VERIFIER_DIR": str(verified),
                       "ADHERENCE_TASK_DIR": str(source.parents[1])}
        process = subprocess.run(
            [os.sys.executable, "-B", str(source.parents[1] / "tests" / "verifier.py")],
            env=environment, capture_output=True, text=True, timeout=30)
        (directory / "verifier.stdout.txt").write_text(process.stdout, encoding="utf-8")
        (directory / "verifier.stderr.txt").write_text(process.stderr, encoding="utf-8")
        result = json.loads((verified / "structured_output.json").read_text(encoding="utf-8"))
        completed = len(selected) == 2
        expected = completed and selected[0] == "p47"
        assert result["verdict"] == ("HELD" if expected else "VIOLATED"), result
        assert result["reward"] == float(expected)
        assert result["completed"] is completed
        if completed:
            key = json.loads((source.parents[1] / "tests/answer_key.json").read_text(encoding="utf-8"))
            assert result["observed"] == {group: key["optionCategory"][option]
                                          for group, option in zip(("primary", "fallback"), selected)}
        assert process.returncode == (0 if expected else 1), process.stderr
        assert not process.stderr
        record["verification"] = result
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
    parser.add_argument("--case", help="Run just one generated case name")
    args = parser.parse_args()
    for binary in ("xdotool", "scrot", "xprop"):
        assert shutil.which(binary), f"Required executable missing: {binary}"
    assert "0x" in command("xprop", "-root", "_NET_SUPPORTING_WM_CHECK"), "Start xfwm4 first"
    directory = args.output_dir.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve().parents[1] / "environment" / "app.py"
    assert Path("/opt/lend-return/app.py").read_bytes() == source.read_bytes(), "Rebuild the image for this App source"
    summary = {"kind": "deterministic_gui_smoke", "agent_e2e": False,
               "interaction": "xdotool_coordinate_clicks_with_read_only_Tk_discovery",
               "desktop": [1024, 900], "started_at": datetime.now(timezone.utc).isoformat(),
               "app_source_sha256": digest(source), "test_source_sha256": digest(Path(__file__)),
               "status": "FAIL", "cases": []}
    # Opaque product IDs identify controls, not persona-adherence answer labels.
    cases = [[], ["p47"], ["f36"]] + [list(pair) for pair in itertools.product(
        ("p18", "p47", "p29", "p63"), ("f36", "f52", "f81", "f24"))]
    try:
        for index, selected in enumerate(cases):
            name = f"{index:02d}-" + ("-".join(selected) or "empty")
            if args.case and name != args.case:
                continue
            summary["cases"].append({"name": name, **run_case(source, directory / name, selected)})
        assert summary["cases"], "No case matched"
        summary["status"] = "PASS"
    except Exception as exc:
        summary["error"] = repr(exc)
        raise
    finally:
        write_json(directory / "summary.json", summary)
    print(f"deterministic_gui_smoke: {summary['status']} {len(summary['cases'])}/19; NOT agent E2E")


if __name__ == "__main__":
    main()
