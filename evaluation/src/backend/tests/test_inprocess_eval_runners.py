import json
import urllib.request

from playground.inprocess.chatbot_eval import DirectApplicationSession
from playground.types import PlaygroundConfig


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_direct_finance_session_uses_http_sidecar(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(
            {
                "url": request.full_url,
                "timeout": timeout,
                "body": json.loads(request.data.decode("utf-8")),
            }
        )
        return FakeHTTPResponse(
            {
                "sessionId": "fin_ses_1",
                "reply": "I can compare ETFs and risk constraints.",
                "turn": {
                    "turnId": "fin_turn_1",
                    "conversationId": "fin_ses_1",
                    "backend": "finance_openbb",
                    "assistantMessage": "I can compare ETFs and risk constraints.",
                    "recommendedItems": [
                        {
                            "itemId": "finance:openbb:etf_search:0",
                            "title": "ETF data",
                        }
                    ],
                },
            }
        )

    monkeypatch.setenv("CHATBOT_UPSTREAM_FINANCE", "http://finance.local")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    session = DirectApplicationSession(
        PlaygroundConfig(
            application_id="finance_openbb",
            application_context="financial_research",
        )
    )
    turn = session.run_turn_sync("Can you compare low-cost broad market ETFs?")

    assert calls[0]["url"] == "http://finance.local/v1/messages"
    assert calls[0]["body"]["applicationId"] == "finance_openbb"
    assert calls[0]["body"]["applicationContext"] == "financial_research"
    assert calls[0]["body"]["message"] == "Can you compare low-cost broad market ETFs?"
    assert turn["assistantMessage"] == "I can compare ETFs and risk constraints."
    assert isinstance(turn.get("structuredExposure"), list)


def test_direct_meal_planning_session_uses_http_sidecar(monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append(json.loads(request.data.decode("utf-8")))
        return FakeHTTPResponse(
            {
                "sessionId": "med_ses_1",
                "reply": "I can help plan meals around your nutrition goals.",
                "turn": {
                    "turnId": "med_turn_1",
                    "conversationId": "med_ses_1",
                    "backend": "meal_planning_nutrition",
                    "assistantMessage": "I can help plan meals around your nutrition goals.",
                    "recommendedItems": [],
                },
            }
        )

    monkeypatch.setenv("CHATBOT_API_URL", "http://meal.local")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    session = DirectApplicationSession(
        PlaygroundConfig(
            application_id="meal_planning_nutrition",
            application_context="meal_planning",
        )
    )
    turn = session.run_turn_sync("Can you suggest a high-protein dinner?")

    assert calls[0]["applicationId"] == "meal_planning_nutrition"
    assert calls[0]["applicationContext"] == "meal_planning"
    assert turn["assistantMessage"].startswith("I can help plan meals")
