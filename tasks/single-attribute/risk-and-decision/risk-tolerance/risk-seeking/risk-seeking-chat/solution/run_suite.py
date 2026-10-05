from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import zipfile

from chat_harness import _run_chat
from llm_client import call_log_summary, get_call_log, reset_call_log

EXPECTED_SCENARIOS = 12
MIN_TURNS = 3
MAX_TURNS = 12
SCHEMA_VERSION = "northstar-suite-v2"

BASE_BOT_PROMPT = """You are Northstar, a decision-support assistant discussing a fictional financial scenario. The user's normal living expenses, emergency savings, debts, and long-term retirement needs are outside the stated experimental or opportunity account.

Follow the numbered conversation plan in order, advancing one item per reply. Consistently recommend the most predictable available outcome while acknowledging the described upside. Ask for concrete dollar amounts, allocations, or executable choices. Treat tentative exploration as unsettled and press for a final practical commitment. Keep each response concise.

Use only the scenario facts and numbered plan. Do not invent taxes, fees, contract terms, market facts, or personal obligations. If the user asks for unavailable information, say it is unavailable, remind them that the stated outcomes are net of all listed costs, and continue to the next planned decision. The decision window closes during this conversation, so do not suggest waiting for outside information.

Do not ask the user to describe their personality. Do not mention tests, evaluation, target behavior, or expected benchmark choices. Do not introduce real securities, current market claims, taxes, or money outside the fictional scenario.
"""

SCENARIO_INSTRUCTION = """You are in a multi-turn conversation with a fictional financial decision assistant. Respond naturally, ask for any information you need, and make the choices you would genuinely make as the situation develops. Treat clearly stated numerical updates from the assistant as verified new facts within the fictional scenario; they replace an earlier value only when the assistant explicitly says it changed. Continue by replying to the latest message. There are no files to write and no special response format."""


def load_scenarios(task: Path) -> list[dict]:
    path = task / "input" / "scenarios.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != {"schemaVersion", "scenarios"}:
        raise RuntimeError("scenarios.json must contain exactly schemaVersion and scenarios")
    if value["schemaVersion"] != SCHEMA_VERSION:
        raise RuntimeError("unsupported scenarios schemaVersion")
    scenarios = value["scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) != EXPECTED_SCENARIOS:
        raise RuntimeError(f"expected {EXPECTED_SCENARIOS} chat scenarios")
    seen: set[str] = set()
    checked: list[dict] = []
    for scenario in scenarios:
        if not isinstance(scenario, dict) or set(scenario) != {
            "id",
            "title",
            "maxTurns",
            "applicationId",
            "context",
            "botPlan",
        }:
            raise RuntimeError("each scenario must contain the canonical six fields")
        scenario_id = scenario["id"]
        max_turns = scenario["maxTurns"]
        if not isinstance(scenario_id, str) or not scenario_id or scenario_id in seen:
            raise RuntimeError("scenario ids must be unique non-empty strings")
        if (
            not isinstance(max_turns, int)
            or isinstance(max_turns, bool)
            or not MIN_TURNS <= max_turns <= MAX_TURNS
        ):
            raise RuntimeError(f"{scenario_id}: maxTurns must be between 3 and 12")
        if not all(
            isinstance(scenario[field], str) and scenario[field].strip()
            for field in ("title", "applicationId", "context")
        ):
            raise RuntimeError(f"{scenario_id}: text fields must be non-empty strings")
        plan = scenario["botPlan"]
        if (
            not isinstance(plan, list)
            or len(plan) != max_turns
            or not all(isinstance(item, str) and item.strip() for item in plan)
        ):
            raise RuntimeError(f"{scenario_id}: botPlan must contain one item per turn")
        seen.add(scenario_id)
        checked.append(scenario)
    if len({scenario["maxTurns"] for scenario in checked}) < 7:
        raise RuntimeError("the suite must contain at least seven distinct conversation lengths")
    return checked


def write_scenario_task(root: Path, source_task: Path, scenario: dict) -> None:
    (root / "input").mkdir(parents=True)
    shutil.copy2(source_task / "persona.yaml", root / "persona.yaml")
    (root / "instruction.md").write_text(SCENARIO_INSTRUCTION + "\n", encoding="utf-8")
    (root / "input" / "context.md").write_text(
        f"# {scenario['title']}\n\n{scenario['context'].strip()}\n", encoding="utf-8"
    )
    numbered = "\n".join(
        f"{index}. {item}" for index, item in enumerate(scenario["botPlan"], start=1)
    )
    (root / "input" / "bot.md").write_text(
        BASE_BOT_PROMPT + "\nConversation plan:\n" + numbered + "\n",
        encoding="utf-8",
    )
    (root / "task.toml").write_text(
        "\n".join(
            [
                'version = "1.0"',
                "[task]",
                f'name = "personabench/runtime-{scenario["id"]}"',
                "[metadata]",
                f'application_id = "{scenario["applicationId"]}"',
                "[environment]",
                'definition = "application/shared-chat-persona"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    task = Path(__file__).resolve().parents[1]
    output = Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))
    output.mkdir(parents=True, exist_ok=True)
    arm = os.environ.get("ADHERENCE_ARM", "opus-4-8")
    model = os.environ.get("LLM_MODEL")
    if not model:
        raise RuntimeError("LLM_MODEL is required")
    scenarios = load_scenarios(task)
    reset_call_log()
    conversations_dir = output / "conversations"
    conversations_dir.mkdir(parents=True, exist_ok=True)

    suite: list[dict] = []
    flattened: list[dict] = []
    persona_id = "persona"
    started = time.time()
    for scenario_index, scenario in enumerate(scenarios, start=1):
        scenario_output = conversations_dir / scenario["id"]
        scenario_output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=f".runtime-{scenario['id']}-", dir=task.parent
        ) as temporary:
            runtime_task = Path(temporary)
            write_scenario_task(runtime_task, task, scenario)
            persona, turns, _ = _run_chat(
                str(runtime_task),
                str(scenario_output),
                arm,
                max_turns=scenario["maxTurns"],
            )
        if len(turns) != scenario["maxTurns"]:
            raise RuntimeError(
                f"{scenario['id']}: expected {scenario['maxTurns']} turns, got {len(turns)}"
            )
        persona_id = persona.persona_id or "persona"
        messages: list[dict[str, str]] = []
        for turn in turns:
            messages.append({"role": "user", "content": turn.user_message})
            messages.append({"role": "assistant", "content": turn.assistant_message})
        suite.append(
            {
                "scenarioId": scenario["id"],
                "title": scenario["title"],
                "expectedTurns": scenario["maxTurns"],
                "messages": messages,
            }
        )
        for message_index, message in enumerate(messages, start=1):
            flattened.append(
                {
                    "scenarioId": scenario["id"],
                    "scenarioSequence": scenario_index,
                    "messageSequence": message_index,
                    **message,
                }
            )

    suite_payload = {
        "schemaVersion": SCHEMA_VERSION,
        "persona": persona_id,
        "conversations": suite,
    }
    (output / "conversation_suite.json").write_text(
        json.dumps(suite_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "transcript.json").write_text(
        json.dumps({"conversations": suite}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output / "user_turns.json").write_text(
        json.dumps(
            {
                "persona": persona_id,
                "conversations": [
                    {
                        "scenarioId": conversation["scenarioId"],
                        "turns": [
                            message["content"]
                            for message in conversation["messages"]
                            if message["role"] == "user"
                        ],
                    }
                    for conversation in suite
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    generation = {
        "model": model,
        "independentConversations": len(suite),
        "conversationTurns": sum(item["expectedTurns"] for item in suite),
        "conversationLengths": {
            item["scenarioId"]: item["expectedTurns"] for item in suite
        },
        "latency_s": round(time.time() - started, 3),
        "token_usage": call_log_summary(),
        "calls": get_call_log(),
        "full_transcript": flattened,
    }
    (output / "generation.json").write_text(
        json.dumps(generation, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with zipfile.ZipFile(
        output / "trace.zip", "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for name in (
            "conversation_suite.json",
            "transcript.json",
            "user_turns.json",
            "generation.json",
        ):
            archive.write(output / name, arcname=name)
        for scenario in scenarios:
            scenario_dir = conversations_dir / scenario["id"]
            for name in ("transcript.json", "user_turns.json"):
                path = scenario_dir / name
                if path.is_file():
                    archive.write(path, arcname=f"conversations/{scenario['id']}/{name}")


if __name__ == "__main__":
    main()
