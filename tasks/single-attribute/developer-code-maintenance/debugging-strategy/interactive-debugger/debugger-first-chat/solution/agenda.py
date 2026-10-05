"""Task-local ChatSessionPort with guaranteed report and handoff opportunities."""
from __future__ import annotations

import json
from pathlib import Path

REVISION = 3


def load_agenda(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if set(data) != {"revision", "fixed_replies", "generated_replies"} or data["revision"] != REVISION:
        raise ValueError("unknown task agenda")
    fixed, generated = data["fixed_replies"], data["generated_replies"]
    if not isinstance(fixed, dict) or not isinstance(generated, dict):
        raise ValueError("invalid agenda mapping")
    if set(fixed) != {"1", "4", "7", "9", "10", "11", "12"} or set(generated) != {"2", "3", "5", "6", "8"}:
        raise ValueError("agenda must cover exactly the twelve scheduled replies")
    if any(not isinstance(text, str) or not text.strip() for text in fixed.values()):
        raise ValueError("empty fixed agenda reply")
    for context in generated.values():
        if not isinstance(context, dict) or set(context) != {"incident", "purpose"}:
            raise ValueError("invalid generated reply context")
        if any(not isinstance(value, str) or not value.strip() for value in context.values()):
            raise ValueError("empty generated reply context")
    return data


class AgendaColleague:
    """Use the unchanged shared provider client for five natural colleague replies."""

    def __init__(self, system_prompt, model, agenda_path, *, chat=None, temperature=0.6):
        if chat is None:
            from llm_client import chat
        self._chat = chat
        self._system = system_prompt
        self._model = model
        self._temperature = temperature
        self.agenda = load_agenda(Path(agenda_path))
        self.history = []
        self.events = []
        self.session_id = "batch-desk-agenda-v3"

    def run_turn_sync(self, message):
        if not isinstance(message, str) or not message.strip():
            raise ValueError("colleague expects a nonempty persona message")
        index = len(self.events) + 1
        if index > 12:
            raise ValueError("the task agenda has exactly twelve replies")
        current = [*self.history, {"role": "user", "content": message}]
        fixed = self.agenda["fixed_replies"].get(str(index))
        context = None
        if fixed is not None:
            reply = fixed
        else:
            context = self.agenda["generated_replies"][str(index)]
            system = (self._system + "\n\nCurrent report: " + context["incident"] +
                      "\nThis reply's purpose: " + context["purpose"])
            from playground.openai_client import openai_model_is_reasoning_family
            # Keep room for hidden reasoning without changing colleague content
            # or setting a reasoning effort in the task.
            budget = 16000 if openai_model_is_reasoning_family(self._model) else 1024
            reply = self._chat([{"role": "system", "content": system}, *current],
                               model=self._model, max_tokens=budget,
                               temperature=self._temperature)
        if not isinstance(reply, str) or not reply.strip():
            raise ValueError("colleague reply is empty or nontext")
        self.history = [*current, {"role": "assistant", "content": reply}]
        self.events.append({"reply": index, "kind": "fixed" if fixed is not None else "generated",
                            "context": context, "assistantMessage": reply})
        return {"assistantMessage": reply, "items": []}
