"""Tests for :class:`backend.service.trace_view.TraceView`.

Covers building a ``TurnView`` from both a ``RecBotTurnResult``-like object and
a raw dict; structured vs. free-text tool-plan parsing; recommended-item
resolution against the catalog (including unknown ids and scores); native raw
stringification; and tolerance of empty / malformed input.
"""

from __future__ import annotations

from backend.service.trace_view import TraceView, item_list_from_exposure
from backend.tests.conftest import (
    ChatMessage,
    NativeAction,
    RecBotTrace,
    RecBotTurnResult,
)


def _items(view):
    return item_list_from_exposure(view.get("structuredExposure"))


def _make_result() -> RecBotTurnResult:
    return RecBotTurnResult(
        backend="interecagent",
        conversation_id="conv-1",
        turn_id="turn-1",
        user_message=ChatMessage("user", "recommend sci-fi noir"),
        assistant_message=ChatMessage("assistant", "Try these."),
        native_action=NativeAction(
            raw={"thought": "filter then rank", "tool": "HardFilter"},
            raw_tool_plan=[
                {"tool": "HardFilter", "detail": "genre=Sci-Fi"},
                {"tool": "Rank", "detail": "match"},
            ],
        ),
        trace=RecBotTrace(
            raw_tool_plan=[
                {"tool": "HardFilter", "detail": "genre=Sci-Fi"},
                {"tool": "Rank", "detail": "match"},
            ],
            raw_tool_outputs={"candidates": 5},
            recommended_item_ids=["cmu:1", "cmu:unknown"],
        ),
    )


def test_from_result_object_with_to_dict(catalog):
    view = TraceView.from_result(_make_result(), catalog, duration_seconds=2.5)
    assert view["turnId"] == "turn-1"
    assert view["conversationId"] == "conv-1"
    assert view["backend"] == "interecagent"
    assert view["userMessage"] == "recommend sci-fi noir"
    assert view["assistantMessage"] == "Try these."
    assert view["durationSeconds"] == 2.5
    assert view["rawToolOutputs"] == {"candidates": 5}


def test_structured_plan_is_parsed(catalog):
    view = TraceView.from_result(_make_result(), catalog)
    tools = [step["tool"] for step in view["plan"]]
    assert tools == ["HardFilter", "Rank"]
    assert view["plan"][0]["detail"] == "genre=Sci-Fi"
    assert view["plan"][0]["status"] == "ok"


def test_structured_items_resolved_against_catalog(catalog):
    view = TraceView.from_result(_make_result(), catalog)
    items = _items(view)
    assert len(items) == 2

    first = items[0]
    assert first["itemId"] == "cmu:1"
    assert first["rank"] == 1
    assert first["title"] == "Blade Runner"
    # meta is "<year> · <up to 3 categories>"
    assert first["meta"] == "1982 · Sci-Fi, Film-noir, Thriller"

    # Unknown ids are still listed, just without a resolved title/meta.
    second = items[1]
    assert second["itemId"] == "cmu:unknown"
    assert second["rank"] == 2
    assert second["title"] is None
    assert second["meta"] is None


def test_native_raw_dict_is_pretty_stringified(catalog):
    view = TraceView.from_result(_make_result(), catalog)
    # native_action.raw was a dict -> pretty JSON string.
    assert isinstance(view["nativeRaw"], str)
    assert "HardFilter" in view["nativeRaw"]
    assert "\n" in view["nativeRaw"]  # indent=2 pretty print


def test_assistant_message_plain_string_passthrough(catalog):
    view = TraceView.build(
        {
            "turn_id": "t",
            "assistant_message": "a bare string",
            "trace": {"recommended_item_ids": []},
        },
        catalog,
    )
    assert view["assistantMessage"] == "a bare string"


def test_plan_falls_back_to_native_text(catalog):
    view = TraceView.build(
        {
            "native_action": {
                "raw": (
                    "First BufferStore the likes, then HardFilter year>2000, "
                    "then Rank candidates, then Map to ids."
                )
            },
            "trace": {"recommended_item_ids": []},
        },
        catalog,
    )
    tools = [step["tool"] for step in view["plan"]]
    assert tools == ["BufferStore", "HardFilter", "Rank", "Map"]


def test_scores_are_extracted(catalog):
    view = TraceView.build(
        {
            "trace": {
                "recommended_item_ids": ["cmu:1", "cmu:2"],
                "recommended_item_scores": {"cmu:1": 0.92, "cmu:2": 0.5},
            }
        },
        catalog,
    )
    by_id = {it["itemId"]: it for it in _items(view)}
    assert by_id["cmu:1"]["score"] == 0.92
    assert by_id["cmu:2"]["score"] == 0.5


def test_structured_items_title_falls_back_to_trace(catalog):
    # The id ("6574") is a recai_resources-style integer id that the
    # external-keyed CatalogIndex cannot resolve, so the catalog lookup yields
    # nothing; the trace's own recommended_items title must be used instead.
    view = TraceView.build(
        {
            "trace": {
                "recommended_item_ids": ["6574"],
                "recommended_items": [{"id": "6574", "title": "Portal 2"}],
            }
        },
        catalog,
    )
    item = _items(view)[0]
    assert item["itemId"] == "6574"
    assert item["title"] == "Portal 2"


def test_trace_title_wins_over_mismatched_catalog(catalog):
    """The agent's own trace title is authoritative; a catalog that resolves the
    id to a DIFFERENT item must not override it (nor contribute its meta).

    This guards the cross-domain collision: a beauty run's item id can also be a
    valid id in the (movie) catalog. Without this, the card would show a movie
    title + movie genres for a beauty product. The trace title ("Phloretin CF
    Serum") must win, and the mismatched catalog's meta must be dropped.
    """
    view = TraceView.build(
        {
            "trace": {
                # ``cmu:1`` resolves to "Blade Runner" (Sci-Fi…) in the fixture
                # catalog, but the agent's trace says it's a beauty product.
                "recommended_item_ids": ["cmu:1"],
                "recommended_items": [{"id": "cmu:1", "title": "Phloretin CF Serum"}],
            }
        },
        catalog,
    )
    item = _items(view)[0]
    assert item["title"] == "Phloretin CF Serum"  # authoritative trace title wins
    assert item["meta"] is None  # mismatched catalog meta (movie genres) dropped


def test_catalog_meta_used_when_it_agrees_with_trace(catalog):
    """When the catalog resolves the id to the SAME item the trace names, the
    catalog's richer meta (year · genres) is shown."""
    view = TraceView.build(
        {
            "trace": {
                "recommended_item_ids": ["cmu:1"],
                "recommended_items": [{"id": "cmu:1", "title": "Blade Runner"}],
            }
        },
        catalog,
    )
    item = _items(view)[0]
    assert item["title"] == "Blade Runner"
    assert item["meta"] == "1982 · Sci-Fi, Film-noir, Thriller"


def test_scores_from_list_of_dicts(catalog):
    view = TraceView.build(
        {
            "trace": {
                "recommended_item_ids": ["cmu:1"],
                "scores": [{"item_id": "cmu:1", "score": 7}],
            }
        },
        catalog,
    )
    assert _items(view)[0]["score"] == 7.0


def test_empty_dict_is_tolerated(catalog):
    view = TraceView.build({}, catalog)
    assert view["turnId"] is None
    assert view["userMessage"] is None
    assert view["plan"] == []
    assert view["structuredExposure"] == []
    assert view["nativeRaw"] == ""
    assert view["durationSeconds"] is None


def test_from_result_non_dict_is_tolerated(catalog):
    # A bare int has no to_dict and isn't a dict -> normalized to empty.
    view = TraceView.from_result(12345, catalog)
    assert view["turnId"] is None
    assert view["plan"] == []


def test_resolution_without_catalog_is_safe():
    view = TraceView.build(
        {"trace": {"recommended_item_ids": ["cmu:1"]}}, catalog=None
    )
    item = _items(view)[0]
    assert item["itemId"] == "cmu:1"
    assert item["title"] is None
    assert item["meta"] is None
