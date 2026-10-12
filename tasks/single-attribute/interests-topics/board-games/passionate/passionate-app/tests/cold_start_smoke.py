"""Provider-free cold-start ordering check inside a fresh task container.

Run this process with Docker --init. It calls the real healthcheck BEFORE starting
Xvfb/XFWM, verifies background launch afterward, and records a screenshot.
This is infrastructure smoke evidence, not an acting-agent or behavior result.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time


def command(*argv: str, timeout: float = 5) -> str:
    return subprocess.check_output(argv, text=True, stderr=subprocess.STDOUT,
                                   timeout=timeout).strip()


def wait_for(predicate, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise RuntimeError("Cold-start condition did not arrive before timeout")
        time.sleep(0.1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    launcher = Path("/opt/lend-return/start-app.sh")
    app = launcher.with_name("app.py")
    state = Path("/tmp/lend-return-bootstrap")
    socket = Path("/tmp/.X11-unix/X1")
    assert not socket.exists(), "Use a fresh container: display :1 already exists"
    assert not (state / "keeper.pid").exists(), "Use a fresh container: keeper already exists"
    for binary in ("Xvfb", "xfwm4", "xdpyinfo", "xdotool", "xprop", "scrot"):
        assert shutil.which(binary), f"Missing {binary}"
    summary = {"kind": "native_launcher_cold_start", "agent_e2e": False,
               "status": "FAIL", "app_source_sha256": hashlib.sha256(app.read_bytes()).hexdigest(),
               "launcher_sha256": hashlib.sha256(launcher.read_bytes()).hexdigest()}
    children, handles = [], []
    environment = {**os.environ, "DISPLAY": ":1"}
    # Discovery and screenshots must inspect the same display we start below,
    # not a DISPLAY inherited from the base image.
    os.environ["DISPLAY"] = ":1"
    try:
        started = time.monotonic()
        summary["healthcheck_output"] = command(str(launcher), timeout=5)
        summary["pre_display_healthcheck_seconds"] = time.monotonic() - started
        assert not socket.exists(), "Healthcheck must not itself create the display"
        summary["pre_display_keeper_status"] = (state / "status").read_text().strip()
        assert summary["pre_display_keeper_status"] == "waiting-display"
        keeper_pid = (state / "keeper.pid").read_text().strip()
        os.kill(int(keeper_pid), 0)
        for name, argv in (
            ("xvfb", ["Xvfb", ":1", "-screen", "0", "1024x900x24", "-nolisten", "tcp"]),
            ("wm", ["xfwm4", "--compositor=off"]),
        ):
            if name == "wm":
                wait_for(socket.exists)
                wait_for(lambda: subprocess.run(["xdpyinfo"], env=environment,
                                                capture_output=True, timeout=3).returncode == 0)
            log = (output / (name + ".log")).open("w")
            handles.append(log)
            children.append(subprocess.Popen(argv, env=environment, stdout=log,
                                              stderr=subprocess.STDOUT, start_new_session=True))
        wait_for(lambda: (state / "status").read_text().strip() == "window-visible")
        ids = command("xdotool", "search", "--onlyvisible", "--name", "^Lend & Return$").splitlines()
        assert len(ids) == 1, ids
        window = ids[0]
        geometry = command("xdotool", "getwindowgeometry", "--shell", window)
        bounds = {key: int(value) for line in geometry.splitlines() if "=" in line
                  for key, value in [line.split("=", 1)] if key in {"X", "Y", "WIDTH", "HEIGHT"}}
        extents = command("xprop", "-id", window, "_NET_FRAME_EXTENTS").split("=", 1)[1]
        left, right, top, bottom = [int(value.strip()) for value in extents.split(",")]
        decorated = {"x": bounds["X"] - left, "y": bounds["Y"] - top,
                     "width": bounds["WIDTH"] + left + right,
                     "height": bounds["HEIGHT"] + top + bottom}
        assert 0 <= decorated["x"] and decorated["x"] + decorated["width"] <= 1024
        assert 0 <= decorated["y"] and decorated["y"] + decorated["height"] <= 900
        summary["decorated_window"] = decorated
        summary["window_id"] = window
        summary["repeat_healthcheck_output"] = command(str(launcher), timeout=5)
        assert (state / "keeper.pid").read_text().strip() == keeper_pid
        summary["singleton_keeper"] = True
        command("scrot", str(output / "cold-start.png"))
        assert (output / "cold-start.png").stat().st_size > 0
        summary["status"] = "PASS"
    except Exception as exc:
        summary["error"] = repr(exc)
        raise
    finally:
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=3)
        for handle in handles:
            handle.close()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
