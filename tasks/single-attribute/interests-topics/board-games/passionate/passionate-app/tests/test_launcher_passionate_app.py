"""No-Docker launcher lifecycle regression with mocked desktop commands.

The real shell launcher and OS file locks run. Mock commands replace X/Tk and
window-manager behavior; this is bootstrap sequencing evidence, not GUI evidence.
"""
from __future__ import annotations
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import pytest

LAUNCHER = Path(__file__).resolve().parents[1] / "environment/start-app.sh"


def wait_for(predicate, timeout=4):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError("Mock lifecycle state did not arrive")
        time.sleep(0.025)


@pytest.fixture
def environment():
    with tempfile.TemporaryDirectory(prefix="lend-bootstrap-") as folder:
        root = Path(folder)
        scripts, commands, state, sockets = [root / name for name in ("app", "bin", "state", "x")]
        for path in (scripts, commands, state, sockets):
            path.mkdir()
        launcher = scripts / "start-app.sh"
        source = LAUNCHER.read_text()
        assert '[ -S "$SOCKET_DIR/X1" ]' in source
        assert '[ -S "$socket" ]' in source
        # Replace only the filesystem socket predicate in the isolated copy.
        # Sandboxed hosts need no permission to bind a real UNIX socket.
        launcher.write_text(source.replace('[ -S "$SOCKET_DIR/X1" ]', '[ -e "$SOCKET_DIR/X1" ]')
                            .replace('[ -S "$socket" ]', '[ -e "$socket" ]'))
        (scripts / "app.py").write_text("# Mocked Tk application\n")
        header = "#!" + sys.executable + "\n"
        mock_sources = {
            "setsid": """import os, sys
try:
    os.setsid()
except PermissionError:
    pass
os.execvp(sys.argv[1], sys.argv[1:])
""",
            "flock": """import fcntl, os, subprocess, sys
args = sys.argv[1:]
target = args[1]
handle = None
if target.isdigit():
    fd = int(target)
else:
    handle = open(target, "a")
    fd = handle.fileno()
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit(1)
if len(args) > 2:
    sys.exit(subprocess.call(args[2:]))
""",
            "timeout": """import os, sys
os.execvp(sys.argv[2], sys.argv[2:])
""",
            "python3": """import json, os, pathlib, sys, time
root = pathlib.Path(os.environ["MOCK_ROOT"])
if len(sys.argv) > 1 and sys.argv[1] == "-c":
    sys.exit(int(os.environ.get("MOCK_TK_FAIL", "0")))
(root / "app.pid").write_text(str(os.getpid()))
(root / "app-start.json").write_text(json.dumps({"argv": sys.argv[1:], "display": os.environ.get("DISPLAY")}))
while True:
    time.sleep(1)
""",
            "pgrep": """import os, pathlib, sys
root = pathlib.Path(os.environ["MOCK_ROOT"])
(root / "pgrep-args").write_text(repr(sys.argv[1:]))
sys.exit(0 if (root / "app.pid").exists() else 1)
""",
            "xdpyinfo": """import os, pathlib
root = pathlib.Path(os.environ["MOCK_ROOT"])
(root / "display-probed").write_text(os.environ.get("DISPLAY", ""))
""",
            "wmctrl": """import os, pathlib, sys
root = pathlib.Path(os.environ["MOCK_ROOT"])
if sys.argv[1:] == ["-m"]:
    sys.exit(0 if (root / "wm-ready").exists() else 1)
if sys.argv[1:2] == ["-a"]:
    if (root / "app.pid").exists():
        (root / "window-focused").write_text(sys.argv[2])
        sys.exit(0)
sys.exit(1)
""",
        }
        for name, body in mock_sources.items():
            path = commands / name
            path.write_text(header + body)
            path.chmod(0o755)
        env = {"PATH": str(commands) + os.pathsep + os.defpath,
               "MOCK_ROOT": str(root), "ADHERENCE_OUTPUT_DIR": str(root / "output"),
               "LEND_RETURN_STATE_DIR": str(state), "LEND_RETURN_X11_DIR": str(sockets),
               "LEND_RETURN_POLL_SECONDS": "0.05"}
        resources = []
        try:
            yield root, launcher, env, resources
        finally:
            for path in (state / "keeper.pid", root / "app.pid"):
                if path.is_file():
                    pid = int(path.read_text())
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            time.sleep(0.2)
            for resource in resources:
                resource.close()


def launch(path, env):
    started = time.monotonic()
    result = subprocess.run(["bash", str(path)], env=env, capture_output=True,
                            text=True, timeout=3)
    assert result.returncode == 0, result.stdout + result.stderr
    assert time.monotonic() - started < 3
    return result


def test_healthcheck_bootstraps_without_waiting_for_x(environment):
    root, launcher, env, _ = environment
    launch(launcher, env)
    assert not list((root / "x").iterdir())
    wait_for(lambda: (root / "state/status").read_text().strip() == "waiting-display")
    assert not (root / "display-probed").exists()
    assert not (root / "app.pid").exists()
    assert (root / "state/keeper.pid").is_file()


def test_late_x_and_window_manager_launch_once_then_focus(environment):
    import json
    root, launcher, env, resources = environment
    launch(launcher, env)
    first_worker = (root / "state/keeper.pid").read_text()
    (root / "x/X1").touch()
    wait_for(lambda: (root / "state/status").read_text().strip() == "waiting-window-manager")
    assert not (root / "app.pid").exists()
    (root / "wm-ready").touch()
    wait_for(lambda: (root / "window-focused").is_file())
    started = json.loads((root / "app-start.json").read_text())
    assert started["display"] == ":1"
    assert started["argv"] == [str(launcher.with_name("app.py"))]
    app_pid = (root / "app.pid").read_text()
    launch(launcher, env)
    time.sleep(0.15)
    assert (root / "state/keeper.pid").read_text() == first_worker
    assert (root / "app.pid").read_text() == app_pid
    assert (root / "window-focused").read_text() == "Lend & Return"
    assert "-fx" in (root / "pgrep-args").read_text()


def test_repeated_cold_healthchecks_keep_single_waiter(environment):
    root, launcher, env, _ = environment
    launch(launcher, env)
    worker = (root / "state/keeper.pid").read_text()
    launch(launcher, env)
    assert (root / "state/keeper.pid").read_text() == worker
    assert not (root / "app.pid").exists()


def test_preflight_dependency_failure_is_not_reported_healthy(environment):
    root, launcher, env, _ = environment
    env["MOCK_TK_FAIL"] = "1"
    result = subprocess.run(["bash", str(launcher)], env=env, capture_output=True,
                            text=True, timeout=3)
    assert result.returncode != 0
    assert not (root / "state/keeper.pid").exists()
