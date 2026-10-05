"""Run the unchanged simulator with the task's explicit handoff colleague."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tomllib
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agenda import AgendaColleague


def run(task: Path, out: Path, arm: str) -> None:
    from matraix.agents.persona.loader import load_persona
    from playground.types import PlaygroundConfig
    from playground.user_sim.runner import run_playground
    import usage

    raw_limit = os.environ.get("MATRAIX_PERSONA_PROFILE_MAX_CHARS", "").strip().lower()
    if raw_limit not in ("", "0", "-1", "none", "unlimited"):
        raise ValueError("Chat requires the full native profile; remove profile truncation.")
    usage.reset()
    model = os.environ.get("LLM_MODEL")
    if not model:
        raise ValueError("LLM_MODEL is required; the task has no paid-model fallback")
    task = task.resolve()
    repo = task
    while repo != repo.parent and not (repo / "tasks").is_dir():
        repo = repo.parent
    native = load_persona(str(task / "persona.yaml"))
    meta = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))
    colleague = AgendaColleague((task / "input/bot.md").read_text(encoding="utf-8"),
                                model, task / "input/agenda.json")
    config = PlaygroundConfig(persona_model=model, max_turns=12, force_full_turns=True,
                              application_id=meta["metadata"]["application_id"])
    result = run_playground(
        colleague, native, (task / "input/context.md").read_text(encoding="utf-8"), config,
        created_at="1970-01-01T00:00:00Z", persona_yaml_path=str(task / "persona.yaml"),
        task_path=str(task.relative_to(repo)), repo_root=repo,
    )
    transcript = []
    turns = list(result.transcript or [])
    for turn in turns:
        transcript.extend([{"role": "user", "content": turn.user_message},
                           {"role": "assistant", "content": turn.assistant_message}])
    out.mkdir(parents=True, exist_ok=True)
    def write(name, obj):
        (out / name).write_bytes((json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    write("transcript.json", transcript)
    write("user_turns.json", {"persona": native.persona_id, "turns": [t.user_message for t in turns]})
    write("chat_usage.json", usage.summary())
    write("colleague_agenda.json", {"revision": 3, "events": colleague.events})
    generation = {
        "model": os.environ.get("LLM_MODEL"),
        "provider": os.environ.get("LLM_PROVIDER"),
        "arm": arm,
        "seed_label": os.environ.get("ADHERENCE_SEED"),
        "seed_controls_sampling": False,
        "full_transcript": transcript,
        "token_usage": usage.summary(),
        "calls": list(usage.CALL_LOG),
        "persona_sha256": hashlib.sha256((task / "persona.yaml").read_bytes()).hexdigest(),
        "task_source_sha256": {
            name: hashlib.sha256((task / name).read_bytes()).hexdigest()
            for name in ("instruction.md", "input/context.md", "input/bot.md", "input/agenda.json", "task.toml")
        },
        "construct": "explicit final incident handoff; declared workflow; no code execution",
        "construct_version": 3,
        "harness_entrypoint": "playground.user_sim.runner.run_playground",
        "colleague_adapter": "task-local AgendaColleague, revision 3",
    }
    write("generation.json", generation)
    with zipfile.ZipFile(out / "trace.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in ("transcript.json", "user_turns.json", "generation.json", "chat_usage.json", "colleague_agenda.json"):
            if (out / name).is_file():
                bundle.write(out / name, name)


if __name__ == "__main__":
    run(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3])
