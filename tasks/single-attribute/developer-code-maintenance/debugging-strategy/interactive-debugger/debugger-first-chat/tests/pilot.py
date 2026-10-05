"""Explicit diagnostic run through the shared harness, never a runner envelope."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

TASK = Path(__file__).resolve().parents[1]
REPO = TASK
while REPO != REPO.parent and not (REPO / "evaluation" / "src").is_dir():
    REPO = REPO.parent
sys.path.insert(0, str(REPO / "evaluation" / "src"))
NEUTRAL_ROLE = (
    "You are role-playing a user. Make your choices and use language naturally, "
    "the way a real person would behave. Do not announce that you are role-playing."
)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@contextmanager
def diagnostic_observers(*, session_type, bot_type, prompt_module, usage,
                         output, metadata, full_block, condition):
    """Observe actual prompts/replies without enabling runner's final callback."""
    expected = full_block if condition == "full" else NEUTRAL_ROLE
    original_init = session_type.__init__
    original_reply = bot_type.run_turn_sync
    events = []

    def observe_init(session, *args, **kwargs):
        original_init(session, *args, **kwargs)
        system = session.system_prompt
        metadata["persona_block_matches_treatment"] = system.startswith(expected + "\n\n")
        if not metadata["persona_block_matches_treatment"]:
            raise RuntimeError("Delivered persona block differs from the locked condition.")
        prompts = {"personaPrompt": expected, "harborPrompt": system}
        metadata["actual_prompt_hashes"] = {k: digest(v) for k, v in prompts.items()}
        write(output / "rendered-prompts.json", prompts)
        write(output / "diagnostic-metadata.json", metadata)

    def observe_reply(bot, message):
        result = original_reply(bot, message)
        turn = {"turnIndex": len(events) + 1, "userMessage": message,
                "assistantMessage": result["assistantMessage"]}
        events.append({"type": "turn", "turn": turn})
        write(output / "harness-events.json", events)
        write(output / "partial-usage.json", {"calls": list(usage.CALL_LOG), "summary": usage.summary()})
        return result

    with ExitStack() as stack:
        stack.enter_context(patch.object(session_type, "__init__", observe_init))
        stack.enter_context(patch.object(bot_type, "run_turn_sync", observe_reply))
        if condition == "blind":
            stack.enter_context(patch.object(prompt_module, "render_persona_block",
                                            lambda *a, **kw: NEUTRAL_ROLE))
        yield


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Required: this invokes paid models.")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--arm", help="Recorded arm label; defaults to the model id with dots replaced by hyphens.")
    parser.add_argument("--condition", choices=("full", "blind"), default="full")
    parser.add_argument("--seed", type=int, default=0, help="Recorded run label; the shared simulator exposes no sampling-seed control.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required; this uses the named model for persona, bot, and judge")
    if args.output.exists():
        parser.error("output already exists; use a new diagnostic trial directory")
    args.output.mkdir(parents=True)
    # Explicit model selection is required; no accidental benchmark-judge spend.
    from judge import infer_provider
    provider = infer_provider(args.model_id)
    arm = args.arm or args.model_id.replace(".", "-")
    os.environ.update({"LLM_MODEL": args.model_id, "LLM_PROVIDER": provider,
                       "ADHERENCE_JUDGE_MODEL": args.model_id,
                       "ADHERENCE_JUDGE_PROVIDER": provider,
                       "ADHERENCE_OUTPUT_DIR": str(args.output.resolve()),
                       "ADHERENCE_VERIFIER_DIR": str(args.output.resolve()),
                       "ADHERENCE_SEED": str(args.seed),
                       "LLM_CALL_ROLE": "arm"})
    import usage
    from playground.user_sim import prompt
    from playground.user_sim.session import UserSimSession
    from matraix.agents.persona.loader import load_persona
    native = load_persona(str(TASK / "persona.yaml"))
    full_block = prompt.render_persona_block(native, persona_yaml_path=str(TASK / "persona.yaml"))
    native_hash = hashlib.sha256((TASK / "persona.yaml").read_bytes()).hexdigest()
    metadata = {
        "status": "started", "diagnostic_only": True, "condition": args.condition,
        "driver_revision": 4, "construct_version": 3,
        "seed_label": args.seed, "seed_controls_sampling": False,
        "model": args.model_id, "provider": provider, "arm_label": arm,
        "persona_file_sha256": native_hash,
        "native_profile_delivered": args.condition == "full",
        "full_render_sha256": digest(full_block),
        "delivered_persona_block_sha256": digest(full_block if args.condition == "full" else NEUTRAL_ROLE),
        "max_persona_turns": 12,
        "blind_adapter": "process-local render_persona_block replacement" if args.condition == "blind" else None,
        "source_sha256": {
            str(path.relative_to(TASK)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(TASK.rglob("*"))
            if path.is_file() and path.suffix in (".py", ".sh", ".md", ".toml", ".yaml", ".json")
        },
        "shared_source_sha256": {
            name: hashlib.sha256((REPO / "evaluation" / "src" / name).read_bytes()).hexdigest()
            for name in ("chat_harness.py", "persona.py", "judge.py", "llm_client.py",
                         "playground/user_sim/prompt.py", "playground/user_sim/runner.py",
                         "playground/user_sim/tool_client.py", "playground/user_sim/sim_guidelines.md")
        },
    }
    write(args.output / "diagnostic-metadata.json", metadata)
    try:
        spec = importlib.util.spec_from_file_location("batch_chat_run", TASK / "solution" / "run_chat.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with diagnostic_observers(session_type=UserSimSession, bot_type=module.AgendaColleague,
                                  prompt_module=prompt, usage=usage, output=args.output,
                                  metadata=metadata, full_block=full_block,
                                  condition=args.condition):
            module.run(TASK, args.output, arm)
        metadata["actor_usage"] = {"calls": list(usage.CALL_LOG), "summary": usage.summary()}
        write(args.output / "diagnostic-metadata.json", metadata)
        spec = importlib.util.spec_from_file_location("batch_chat_verify", TASK / "tests" / "verifier.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        code = module.main()
        metadata["status"] = "completed" if code == 0 else "verifier_error"
        return code
    except Exception as exc:
        metadata["status"] = "error"
        metadata["error_type"] = type(exc).__name__
        metadata["partial_actor_usage"] = {"calls": list(usage.CALL_LOG), "summary": usage.summary()}
        return 3
    finally:
        metadata["native_persona_unchanged"] = (
            hashlib.sha256((TASK / "persona.yaml").read_bytes()).hexdigest() == native_hash
        )
        write(args.output / "diagnostic-metadata.json", metadata)


if __name__ == "__main__":
    raise SystemExit(main())
