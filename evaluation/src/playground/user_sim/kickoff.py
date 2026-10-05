from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

_SCENARIO_DEFAULT = """You are a real user of this interactive chatbot application.

Application context: {domain}

{sut_description}

Who you are:
{persona_context}

First decide what realistic goal you want to accomplish with this application
and what constraints or preferences matter most to you. Then behave like a
genuine human user:
- Do NOT reveal everything at once: share your needs gradually, as a real person
  would, and answer the agent's follow-up questions naturally.
- React to the application's responses: if they fit your needs, say so; if not,
  push back, refine, or ask for clarification.
- Keep messages short and conversational (1-3 sentences)."""


@dataclass
class GoalContext:
    id: str
    label: str
    description: str
    template: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "template": self.template,
        }


_REGISTRY: Dict[str, GoalContext] = {
    "scenario_default": GoalContext(
        id="scenario_default",
        label="Realistic scenario",
        description="The persona settles on a realistic need and reveals it gradually.",
        template=_SCENARIO_DEFAULT,
    ),
}


def load_goal_contexts() -> List[GoalContext]:
    return list(_REGISTRY.values())


def get_goal_context(id: str) -> GoalContext:
    try:
        return _REGISTRY[id]
    except KeyError:
        raise KeyError("unknown goal context: {!r}".format(id))
