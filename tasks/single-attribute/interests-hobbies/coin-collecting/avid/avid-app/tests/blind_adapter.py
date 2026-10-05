"""Opt-in process-only full-Harbor persona-omission control.

Production runtime files, persona data, native task, delegate, provider and scorer
are unchanged. No model is called by prepare_extra or the unit tests.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys

UI_CONSTRAINT = ("Environment constraint: interact only with the visible application UI using "
                 "screenshots, clicks, scrolling, and normal text entry. Do not use view-source, "
                 "developer tools, DOM inspection, shell commands, or filesystem inspection.")
TASK = Path(__file__).resolve().parents[1]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def prepare_extra(original: Path, destination: Path, persona: Path) -> dict:
    raw = original.read_bytes()
    suffix = b"\n" + UI_CONSTRAINT.encode() + b"\n"
    if not raw.endswith(suffix) or raw.count(UI_CONSTRAINT.encode()) != 1:
        raise ValueError("Original native extra instruction lacks the exact unique UI suffix")
    if len(raw) <= len(suffix):
        raise ValueError("Original extra instruction has no persona block to omit")
    if any(marker in suffix for marker in (b"# Your profile", b"hob_coin_collecting", b"Avid")):
        raise ValueError("Blind suffix contains persona data")
    with destination.open("xb") as handle:
        handle.write(suffix)
    metadata = {
        "kind": "persona-blind-control", "active_persona": None,
        "source_persona_sha256": sha(persona.read_bytes()), "source_persona_injected": False,
        "original_extra_sha256": sha(raw), "blind_extra_sha256": sha(suffix),
        "blind_extra_text": suffix.decode(), "removed_extra_bytes": len(raw) - len(suffix),
        "ui_suffix_preserved_byte_for_byte": True,
    }
    write_new(destination.parent / "blind-prompt-metadata.json", metadata)
    return metadata


def install_runtime_patches(evidence: Path):
    from matraix.agents.persona import computer_1 as persona_module
    from harbor.agents.computer_1.providers import anthropic as provider_module

    cls = persona_module.PersonaComputer1
    provider_cls = provider_module.AnthropicProvider
    original_prepare = cls._prepare_persona_trial
    original_render = cls._render_persona_system
    original_system = provider_cls._system_prompt

    # Derive, don't rewrite, the native post-identity capability text. A bare
    # empty identity would instead choose a different generic SYSTEM_PROMPT.
    marker = "PERSONA_CONTROL_BOUNDARY_SENTINEL"
    probe = type("PromptProbe", (), {"_identity_prompt": marker})()
    native = original_system(probe)
    if not native.startswith(marker + "\n\n"):
        raise RuntimeError("Native identity/system contract changed")
    suffix = native[len(marker):]
    if suffix != "\n\n" + provider_module._CAPABILITY_AFTER_IDENTITY:
        raise RuntimeError("Native capability suffix changed")
    evidence.mkdir(parents=True, exist_ok=True)
    contract = {
        "kind": "persona-blind-control", "active_persona": None,
        "native_capability_suffix": suffix, "native_capability_suffix_sha256": sha(suffix.encode()),
        "generic_fallback_not_used": True,
        "original_prepare_source_sha256": sha(inspect.getsource(original_prepare).encode()),
        "original_identity_source_sha256": sha(inspect.getsource(original_render).encode()),
        "original_provider_system_source_sha256": sha(inspect.getsource(original_system).encode()),
        "production_run_method_unchanged": True,
    }
    write_new(evidence / "blind-runtime-contract.json", contract)

    async def prepare(self, environment):
        kind = persona_module.resolve_cua_backend_kind(
            environment, override=self._cua_backend_override)
        if kind != "docker_computer1":
            raise RuntimeError("Blind control supports only the native Docker computer-1 backend")
        if self._delegate_kwargs.get("provider") != "anthropic":
            raise RuntimeError("This audited control supports only the native Anthropic provider")
        identity = original_render(self)
        if not identity:
            raise RuntimeError("Native persona identity was unexpectedly empty")
        self._blind_native_identity_sha256 = sha(identity.encode())
        metadata = {
            "source": "persona-blind-control", "persona_id": None, "active_persona": None,
            "agent": self.name(), "source_persona_injected": False, "persona_upload_omitted": True,
            "source_persona_sha256": sha(self._persona.persona_path.read_bytes()),
            "omitted_identity_sha256": self._blind_native_identity_sha256,
            "backend": kind, "provider": "anthropic",
        }
        # The source YAML remains unmodified on the host and is NOT uploaded.
        write_new(self.logs_dir.parent / "persona_meta.json", metadata)
        write_new(evidence / "blind-persona-omission.json", metadata)

    def render(self):
        if not getattr(self, "_blind_native_identity_sha256", None):
            raise RuntimeError("Persona omission preparation did not run")
        return ""

    def system(self):
        if self._identity_prompt:
            raise RuntimeError("Blind provider unexpectedly received persona identity")
        record = {"at": datetime.now(timezone.utc).isoformat(), "identity_empty": True,
                  "system_prompt_sha256": sha(suffix.encode()),
                  "native_capability_suffix_preserved": True}
        with (evidence / "blind-sdk-system-audit.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        return suffix

    cls._prepare_persona_trial = prepare
    cls._render_persona_system = render
    provider_cls._system_prompt = system

    def restore():
        cls._prepare_persona_trial = original_prepare
        cls._render_persona_system = original_render
        provider_cls._system_prompt = original_system
    return restore


def validate_invocation(argv: list[str], evidence: Path) -> None:
    if not argv or argv[0] != "run":
        raise ValueError("Control wrapper accepts only Harbor run")
    pairs = list(zip(argv, argv[1:]))
    if ("-a", "persona-computer-1") not in pairs or ("-e", "docker") not in pairs:
        raise ValueError("Control must retain native persona-computer-1 and Docker")
    if ("--ak", "provider=anthropic") not in pairs:
        raise ValueError("Only the audited native Anthropic route is allowed")
    extras = [value for flag, value in pairs if flag == "--extra-instruction-path"]
    expected = evidence / "blind-extra-instruction.txt"
    if len(extras) != 1 or Path(extras[0]).resolve() != expected.resolve():
        raise ValueError("Blind invocation must use only the prepared UI constraint")
    if expected.read_bytes() != b"\n" + UI_CONSTRAINT.encode() + b"\n":
        raise ValueError("Blind extra instruction was modified after preparation")
    persona_args = [value for flag, value in pairs if flag == "--ak" and value.startswith("persona_path=")]
    if persona_args != ["persona_path=" + str(TASK / "persona.yaml")]:
        raise ValueError("Native source persona path changed")
    # The required native loader still reads the unchanged file. The audited
    # process patches prevent both its upload and its identity injection.
    write_new(evidence / "blind-harbor-invocation.json",
              {"kind": "persona-blind-control", "argv": argv,
               "source_persona_loaded_but_not_injected": True})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-extra", nargs=3, metavar=("ORIGINAL", "BLIND", "PERSONA"))
    parser.add_argument("--harbor", action="store_true")
    args, remaining = parser.parse_known_args()
    if args.prepare_extra:
        if remaining or args.harbor:
            parser.error("Unexpected arguments for prompt preparation")
        prepare_extra(*(Path(value) for value in args.prepare_extra))
        return
    if not args.harbor or os.environ.get("ADHERENCE_RUN_BLIND") != "1":
        parser.error("Full control requires --harbor and ADHERENCE_RUN_BLIND=1")
    evidence = Path(os.environ["BLIND_APP_EVIDENCE_DIR"]).resolve()
    validate_invocation(remaining, evidence)
    install_runtime_patches(evidence)
    from harbor.cli.main import app
    sys.argv = ["harbor", *remaining]
    app()


if __name__ == "__main__":
    main()
