"""No-provider audit of the process-only App persona-omission control."""
from __future__ import annotations
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import pytest

TASK = Path(__file__).resolve().parents[1]
REPO = next(parent for parent in TASK.parents if (parent / "evaluation/src").is_dir())
sys.path.insert(0, str(REPO / "evaluation/src"))
spec = importlib.util.spec_from_file_location("hobby_blind_adapter", Path(__file__).with_name("blind_adapter.py"))
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def test_exact_extra_suffix_only(tmp_path):
    original = tmp_path / "native"
    original.write_bytes(b"# Your profile\nPRIVATE PERSONA\n\n" + adapter.UI_CONSTRAINT.encode() + b"\n")
    blind = tmp_path / "blind-extra-instruction.txt"
    metadata = adapter.prepare_extra(original, blind, TASK / "persona.yaml")
    assert blind.read_bytes() == b"\n" + adapter.UI_CONSTRAINT.encode() + b"\n"
    assert metadata["active_persona"] is None
    assert metadata["source_persona_injected"] is False
    assert metadata["ui_suffix_preserved_byte_for_byte"] is True
    assert b"PRIVATE" not in blind.read_bytes()
    with pytest.raises(FileExistsError):
        adapter.prepare_extra(original, blind, TASK / "persona.yaml")


@pytest.mark.parametrize("text", ["profile only", adapter.UI_CONSTRAINT + "\n",
                                    "profile\n\n" + adapter.UI_CONSTRAINT + "\nchanged"])
def test_changed_native_prompt_contract_is_rejected(tmp_path, text):
    source = tmp_path / "native"
    source.write_text(text)
    with pytest.raises(ValueError):
        adapter.prepare_extra(source, tmp_path / "blind", TASK / "persona.yaml")
    assert not (tmp_path / "blind").exists()


def test_actual_run_has_empty_delegate_identity_and_no_persona_upload(tmp_path, monkeypatch):
    from matraix.agents.persona import computer_1 as native
    from harbor.agents.computer_1.providers import anthropic as provider
    logs = tmp_path / "trial/agent"
    logs.mkdir(parents=True)
    instance = native.PersonaComputer1(
        logs_dir=logs, model_name="claude-opus-4-8",
        persona_path=str(TASK / "persona.yaml"), provider="anthropic", cua_backend="docker")
    original_run = native.PersonaComputer1.run
    original_source_hash = hashlib.sha256((TASK / "persona.yaml").read_bytes()).hexdigest()
    uploads, received = [], []
    async def upload(*args):
        uploads.append(args)
    environment = SimpleNamespace(upload_file=upload)
    delegate = SimpleNamespace()
    async def delegate_run(instruction, env, context):
        received.append((instruction, delegate._identity_prompt, env, context))
    delegate.run = delegate_run
    def get_delegate(env):
        instance._delegate_kind = "docker_computer1"
        return delegate
    monkeypatch.setattr(instance, "_get_delegate", get_delegate)
    async def final_answer(*args, **kwargs):
        pass
    monkeypatch.setattr(native, "materialize_final_answer_file", final_answer)
    evidence = tmp_path / "control"
    restore = adapter.install_runtime_patches(evidence)
    try:
        task_instruction = "Unchanged hobby task.\n\n" + adapter.UI_CONSTRAINT
        context = object()
        asyncio.run(instance.run(task_instruction, environment, context))
        assert native.PersonaComputer1.run is original_run
        assert uploads == []
        assert received == [(task_instruction, "", environment, context)]
        actual_provider = provider.AnthropicProvider.__new__(provider.AnthropicProvider)
        actual_provider._identity_prompt = delegate._identity_prompt
        assert actual_provider._system_prompt() == "\n\n" + provider._CAPABILITY_AFTER_IDENTITY
        assert actual_provider._system_prompt() != provider.SYSTEM_PROMPT
        actual_provider._identity_prompt = "UNEXPECTED PROFILE"
        with pytest.raises(RuntimeError, match="unexpectedly"):
            actual_provider._system_prompt()
        meta = json.loads((logs.parent / "persona_meta.json").read_text())
        assert meta["source"] == "persona-blind-control" and meta["persona_id"] is None
        assert meta["persona_upload_omitted"] is True
        assert meta["source_persona_sha256"] == original_source_hash
        assert hashlib.sha256((TASK / "persona.yaml").read_bytes()).hexdigest() == original_source_hash
        audit = [json.loads(line) for line in (evidence / "blind-sdk-system-audit.jsonl").read_text().splitlines()]
        assert len(audit) == 2 and all(row["identity_empty"] for row in audit)
    finally:
        restore()


def test_non_docker_backend_rejected_without_upload(tmp_path):
    from matraix.agents.persona import computer_1 as native
    logs = tmp_path / "trial/agent"
    logs.mkdir(parents=True)
    instance = native.PersonaComputer1(
        logs_dir=logs, model_name="claude-opus-4-8", persona_path=str(TASK / "persona.yaml"),
        provider="anthropic", cua_backend="ios")
    restore = adapter.install_runtime_patches(tmp_path / "evidence")
    try:
        with pytest.raises(RuntimeError, match="only the native Docker"):
            asyncio.run(instance._prepare_persona_trial(SimpleNamespace()))
    finally:
        restore()


def test_invocation_rejects_old_extra_file(tmp_path):
    extra = tmp_path / "blind-extra-instruction.txt"
    extra.write_bytes(b"\n" + adapter.UI_CONSTRAINT.encode() + b"\n")
    argv = ["run", "-a", "persona-computer-1", "-m", "unchanged-model", "-e", "docker",
            "--ak", "provider=anthropic", "--ak", "persona_path=" + str(TASK / "persona.yaml"),
            "--ak", "max_steps=30", "--extra-instruction-path", str(extra)]
    adapter.validate_invocation(argv, tmp_path)
    saved = json.loads((tmp_path / "blind-harbor-invocation.json").read_text())
    assert saved["argv"] == argv
    invalid = [*argv[:-1], str(tmp_path / "native-persona.txt")]
    with pytest.raises(ValueError, match="only the prepared"):
        adapter.validate_invocation(invalid, tmp_path)
    with pytest.raises(ValueError, match="only the prepared"):
        adapter.validate_invocation([*argv, "--extra-instruction-path", "old"], tmp_path)


def test_helper_prepare_only_is_real_native_configuration_no_run(tmp_path):
    output = tmp_path / "output"
    env = {"PATH": str(Path(sys.executable).parent) + os.pathsep + os.defpath,
           "PYTHONDONTWRITEBYTECODE": "1", "RUNTIME_PYTHON": sys.executable,
           "ADHERENCE_OUTPUT_DIR": str(output), "ADHERENCE_RUN_BLIND": "1",
           "BLIND_APP_PREPARE_ONLY": "1", "LLM_MODEL": "claude-opus-4-8",
           "LLM_PROVIDER": "anthropic", "ADHERENCE_ARM": "opus-4-8"}
    process = subprocess.run(["bash", str(TASK / "tests/run_blind.sh")],
                             env=env, text=True, capture_output=True, timeout=30)
    assert process.returncode == 0, process.stdout + process.stderr
    assert "no Docker, provider, or agent run" in process.stdout
    meta = json.loads((output / "blind-prompt-metadata.json").read_text())
    assert meta["removed_extra_bytes"] > 10000
    assert meta["ui_suffix_preserved_byte_for_byte"] is True
    assert not (output / "hobby_reservation.json").exists()
    assert not (output / "blind-harbor-invocation.json").exists()
