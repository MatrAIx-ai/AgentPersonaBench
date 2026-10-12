from playground.cli import format_transcript
from playground.types import (Persona, PlaygroundConfig, PlaygroundTurn, Questionnaire,
                            MetricScores, PlaygroundResult)


def _result():
    return PlaygroundResult(
        config=PlaygroundConfig(domain="game"),
        persona=Persona(id="p", name="Marco", summary="s", preferences=[],
                        dislikes=[], constraints=[], goal="g", communication_style="c"),
        sut_description="desc",
        transcript=[PlaygroundTurn(1, "hi", "try A", [{"key": "items", "label": "Items", "format": "item_list", "value": [{"itemId": "1", "title": "A"}]}], "satisfied", 1.0)],
        questionnaire=Questionnaire(4, "r", 4, "r", 8, "good", True, "asked"),
        metric_scores=MetricScores(num_turns=1), created_at="t")


def test_format_transcript_is_readable():
    text = format_transcript(_result())
    assert "Marco" in text and "try A" in text
    assert "Overall: 8/10" in text
    assert "num turns: 1" in text
