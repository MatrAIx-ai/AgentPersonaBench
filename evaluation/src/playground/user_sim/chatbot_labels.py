from __future__ import annotations


_CHATBOT_LABELS = {
    "finance_openbb": "FinAI / OpenBB",
    "meal_planning_nutrition": "Meal Planning Nutrition",
    "acme_support_api": "ACME Support API",
    "acme_support_mcp": "ACME Support MCP",
}


def chatbot_display_name(application_id: str | None) -> str:
    value = str(application_id or "").strip()
    if not value:
        return "Chatbot"
    return _CHATBOT_LABELS.get(value, value.replace("_", " ").strip().title() or "Chatbot")
