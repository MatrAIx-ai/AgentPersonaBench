"""Application Harbor tasks must use host-aware verifier paths."""

from __future__ import annotations

from pathlib import Path

from backend.service.example_task_catalog import repo_root

_FORBIDDEN_SNIPPETS = (
    "echo 1 > /logs/verifier/reward.txt",
    "echo 0 > /logs/verifier/reward.txt",
    "python3 /tests/test_state.py",
    "pytest --ctrf /logs/verifier/ctrf.json /tests/test_state.py",
)


def _application_task_verifier_scripts(root: Path) -> list[Path]:
    return sorted((root / "application/tasks").glob("*/tests/test.sh"))


def _combined_verifier_script(root: Path, test_sh: Path) -> str:
    tests_dir = test_sh.parent
    parts = [test_sh.read_text(encoding="utf-8")]
    env_sh = tests_dir / "verifier_env.sh"
    if env_sh.is_file():
        parts.append(env_sh.read_text(encoding="utf-8"))
    return "\n".join(parts)


def test_application_task_verifier_scripts_use_harbor_dirs():
    root = repo_root()
    scripts = _application_task_verifier_scripts(root)
    assert scripts, "expected application/tasks/*/tests/test.sh files"

    for path in scripts:
        relative = path.relative_to(root).as_posix()
        content = _combined_verifier_script(root, path)
        assert "verifier_env.sh" in path.read_text(encoding="utf-8"), relative
        assert (path.parent / "verifier_env.sh").is_file(), relative
        assert "HARBOR_VERIFIER_DIR" in content, relative
        for snippet in _FORBIDDEN_SNIPPETS:
            assert snippet not in content, f"{relative} still contains {snippet!r}"
        if "test_state.py" in content:
            assert "HARBOR_TESTS_DIR" in content, relative
            assert "${TESTS_DIR}/test_state.py" in content, relative
