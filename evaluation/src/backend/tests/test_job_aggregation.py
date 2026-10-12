from __future__ import annotations

import json
from pathlib import Path

from backend.service.job_aggregation import (
    SUMMARY_LLM_BUCKET_CHUNK,
    _execute_summary_llm,
    build_job_aggregation,
    job_aggregation_artifact_is_fresh,
    read_job_aggregation_artifact,
    write_job_aggregation,
)


def _write_trial(job_dir: Path, trial_name: str, payload: dict) -> None:
    trial_dir = job_dir / trial_name
    (trial_dir / "verifier").mkdir(parents=True, exist_ok=True)
    (trial_dir / "result.json").write_text("{}", encoding="utf-8")
    (trial_dir / "verifier" / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class _FakeChatClient:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system: str, user: str) -> dict:
        self.calls.append((system, user))
        assert self._responses, "unexpected extra LLM call"
        return self._responses.pop(0)


def test_build_job_aggregation_groups_text_by_categorical_directive(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    payload_yes = {
        "presenceCheck": {"passed": True},
        "contexts": [
            {
                "key": "question.q1",
                "label": "Question 1",
                "contextType": "question_response",
                "summaryAnalyses": [
                    {
                        "id": "q1.reason_by_response",
                        "title": "Reason by response",
                        "targetFacetKey": "reason",
                        "groupByFacetKey": "response",
                        "groupByMode": "categorical",
                        "summaryKind": "llm_bucket_summary",
                    }
                ],
                "facets": [
                    {"key": "response", "label": "Response", "role": "primary", "kind": "categorical", "value": "yes"},
                    {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "value": "Easy to use."},
                ],
            }
        ],
    }
    payload_no = {
        "presenceCheck": {"passed": True},
        "contexts": [
            {
                "key": "question.q1",
                "label": "Question 1",
                "contextType": "question_response",
                "summaryAnalyses": [
                    {
                        "id": "q1.reason_by_response",
                        "title": "Reason by response",
                        "targetFacetKey": "reason",
                        "groupByFacetKey": "response",
                        "groupByMode": "categorical",
                        "summaryKind": "llm_bucket_summary",
                    }
                ],
                "facets": [
                    {"key": "response", "label": "Response", "role": "primary", "kind": "categorical", "value": "no"},
                    {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "value": "Too expensive."},
                ],
            }
        ],
    }
    _write_trial(job_dir, "trial-1", payload_yes)
    _write_trial(job_dir, "trial-2", payload_no)

    aggregation = build_job_aggregation(job_dir)

    assert aggregation is not None
    contexts = aggregation["contexts"]
    assert len(contexts) == 1
    summaries = contexts[0]["summaries"]
    assert summaries[0]["id"] == "q1.reason_by_response"
    buckets = {bucket["bucket"]: bucket for bucket in summaries[0]["buckets"]}
    assert buckets["yes"]["count"] == 1
    assert buckets["no"]["count"] == 1
    assert buckets["yes"]["summary"]


def test_build_job_aggregation_groups_text_by_numeric_band_directive(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    for name, score, text in [
        ("trial-low", 2, "Low confidence reason."),
        ("trial-high", 9, "High confidence reason."),
    ]:
        _write_trial(
            job_dir,
            name,
            {
                "presenceCheck": {"passed": True},
                "contexts": [
                    {
                        "key": "decision.review",
                        "label": "Decision review",
                        "contextType": "decision",
                        "summaryAnalyses": [
                            {
                                "id": "decision.reason_by_confidence",
                                "title": "Reason by confidence",
                                "targetFacetKey": "reason",
                                "groupByFacetKey": "confidence",
                                "groupByMode": "numeric_band",
                                "bands": [
                                    {"label": "low", "min": 0, "max": 3},
                                    {"label": "high", "min": 8, "max": 10},
                                ],
                                "summaryKind": "llm_bucket_summary",
                            }
                        ],
                        "facets": [
                            {"key": "confidence", "label": "Confidence", "role": "score", "kind": "numerical", "value": score},
                            {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "value": text},
                        ],
                    }
                ],
            },
        )

    aggregation = build_job_aggregation(job_dir)

    assert aggregation is not None
    summaries = aggregation["contexts"][0]["summaries"]
    buckets = {bucket["bucket"]: bucket for bucket in summaries[0]["buckets"]}
    assert buckets["low"]["count"] == 1
    assert buckets["high"]["count"] == 1


def test_build_job_aggregation_reads_task_reporting_config(tmp_path: Path) -> None:
    repo_root = tmp_path
    task_dir = repo_root / "application" / "tasks" / "example-task"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "reporting.json").write_text(
        json.dumps(
            {
                "contextRules": [
                    {
                        "match": {"key": "decision.review"},
                        "summaryAnalyses": [
                            {
                                "id": "decision.reason_by_choice",
                                "title": "Reason by choice",
                                "targetFacetKey": "reason",
                                "groupByFacetKey": "choice",
                                "groupByMode": "categorical",
                                "summaryKind": "llm_bucket_summary",
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    job_dir = repo_root / "jobs" / "job"
    trial_dir = job_dir / "trial-1"
    (trial_dir / "verifier").mkdir(parents=True, exist_ok=True)
    (trial_dir / "result.json").write_text("{}", encoding="utf-8")
    (trial_dir / "config.json").write_text(
        json.dumps({"task": {"path": "application/tasks/example-task"}}),
        encoding="utf-8",
    )
    (trial_dir / "verifier" / "structured_output.json").write_text(
        json.dumps(
            {
                "presenceCheck": {"passed": True},
                "contexts": [
                    {
                        "key": "decision.review",
                        "label": "Decision review",
                        "contextType": "decision",
                        "facets": [
                            {
                                "key": "choice",
                                "label": "Choice",
                                "role": "primary",
                                "kind": "categorical",
                                "value": "yes",
                            },
                            {
                                "key": "reason",
                                "label": "Reason",
                                "role": "explanation",
                                "kind": "textual",
                                "value": "It was straightforward.",
                            },
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    aggregation = build_job_aggregation(job_dir, repo_root=repo_root)

    assert aggregation is not None
    summaries = aggregation["contexts"][0]["summaries"]
    assert summaries[0]["id"] == "decision.reason_by_choice"
    assert summaries[0]["buckets"][0]["bucket"] == "yes"


def test_build_job_aggregation_synthesizes_user_feedback_context(tmp_path: Path) -> None:
    repo_root = tmp_path
    task_dir = repo_root / "application" / "tasks" / "example-web-playwright_quote-choice"
    input_dir = task_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "reporting.json").write_text(
        json.dumps(
            {
                "contextRules": [
                    {
                        "match": {"contextType": "user_feedback"},
                        "summaryAnalyses": [
                            {
                                "id": "user_feedback.reason_by_need_satisfaction",
                                "title": "Feedback reason by need satisfaction",
                                "targetFacetKey": "feedback_reason",
                                "groupByFacetKey": "need_constraint_satisfaction",
                                "groupByMode": "categorical",
                                "summaryKind": "llm_bucket_summary",
                            }
                        ],
                        "signalScans": [
                            {
                                "id": "user_feedback.reason_signal_scan",
                                "title": "Feedback signal scan",
                                "targetFacetKey": "feedback_reason",
                                "groupByFacetKey": "personal_preference_satisfaction",
                                "groupByMode": "categorical",
                                "judgeKind": "llm_signal_judge",
                                "prompt": "Read the persona's feedback and classify signals.",
                                "rubric": "Only mark present when explicit.",
                                "signals": [
                                    {
                                        "key": "trust_signal",
                                        "label": "Trust or confidence",
                                        "valueType": "boolean",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (input_dir / "self_report_schema.yaml").write_text(
        "\n".join(
            [
                "artifactName: user_feedback.json",
                "fields:",
                "  - key: needConstraintSatisfaction",
                "    prompt: How well did the choice satisfy your need?",
                "    kind: enum",
                "  - key: personalPreferenceSatisfaction",
                "    prompt: How well did it match your preferences?",
                "    kind: enum",
                "  - key: overallExperienceRating",
                "    prompt: Overall rating",
                "    kind: integer",
                "  - key: reason",
                "    prompt: Why?",
                "  - key: trustLevel",
                "    prompt: Trust level",
                "    kind: integer",
                "  - key: clarityOfNextStep",
                "    prompt: Was the next step clear?",
                "    kind: boolean",
                "",
            ]
        ),
        encoding="utf-8",
    )
    job_dir = repo_root / "jobs" / "job"
    trial_dir = job_dir / "trial-1"
    output_dir = trial_dir / "artifacts" / "app" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "verifier").mkdir(parents=True, exist_ok=True)
    (trial_dir / "result.json").write_text("{}", encoding="utf-8")
    (trial_dir / "config.json").write_text(
        json.dumps({"task": {"path": "application/tasks/example-web-playwright_quote-choice"}}),
        encoding="utf-8",
    )
    (output_dir / "user_feedback.json").write_text(
        json.dumps(
            {
                "needConstraintSatisfaction": "yes",
                "personalPreferenceSatisfaction": "partially",
                "overallExperienceRating": 8,
                "reason": "The site felt trustworthy and I knew what to do next.",
                "trustLevel": 9,
                "clarityOfNextStep": True,
            }
        ),
        encoding="utf-8",
    )
    (trial_dir / "verifier" / "structured_output.json").write_text(
        json.dumps(
            {
                "presenceCheck": {"passed": True},
                "contexts": [
                    {
                        "key": "decision.primary",
                        "label": "Primary decision",
                        "contextType": "decision",
                        "facets": [
                            {
                                "key": "decision_outcome",
                                "label": "Decision outcome",
                                "role": "primary",
                                "kind": "categorical",
                                "value": "selected",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    aggregation = build_job_aggregation(job_dir, repo_root=repo_root)

    assert aggregation is not None
    feedback_context = next(
        context
        for context in aggregation["contexts"]
        if context["contextType"] == "user_feedback"
    )
    facets = {facet["facetKey"]: facet for facet in feedback_context["facets"]}
    assert facets["feedback_reason"]["textual"]["count"] == 1
    assert facets["need_constraint_satisfaction"]["categorical"]["counts"][0]["value"] == "yes"
    assert facets["trust_level"]["numerical"]["avg"] == 9.0
    assert facets["clarity_of_next_step"]["categorical"]["counts"][0]["value"] == "true"
    assert feedback_context["summaries"][0]["id"] == "user_feedback.reason_by_need_satisfaction"
    assert feedback_context["judges"][0]["id"] == "user_feedback.reason_signal_scan"
    assert aggregation["reporting"]["status"] == "ready"
    assert aggregation["reporting"]["totalUnits"] == 2


def test_yaml_yes_no_choices_not_boolified(tmp_path: Path) -> None:
    """Bare YAML ``yes``/``no`` must stay enum choice tokens, not booleans."""
    repo_root = tmp_path
    task = "chat_openbb-corporate-action-honesty"
    _write_feedback_task(
        repo_root,
        task=task,
        schema_lines=[
            "artifactName: user_feedback.json",
            "fields:",
            "  - key: hcpDelistingHandled",
            "    prompt: Did HCP meet expectations?",
            "    kind: enum",
            "    choices: [yes, partially, no]",
            "  - key: needConstraintSatisfaction",
            "    prompt: Overall, did the assistant meet what you needed?",
            "    kind: enum",
            "    choices: [yes, partially, no]",
        ],
    )
    job_dir = repo_root / "jobs" / "job"
    _write_feedback_trial(
        job_dir,
        task=task,
        trial="trial-1",
        feedback={
            "hcpDelistingHandled": "True",
            "needConstraintSatisfaction": "partially",
        },
    )

    aggregation = build_job_aggregation(job_dir, repo_root=repo_root)
    assert aggregation is not None
    feedback = next(
        context
        for context in aggregation["contexts"]
        if context["contextType"] == "user_feedback"
    )
    facets = {facet["facetKey"]: facet for facet in feedback["facets"]}
    assert facets["hcp_delisting_handled"]["categories"] == ["yes", "partially", "no"]
    # Authored enum value is kept as-is (lowercased only).
    assert facets["hcp_delisting_handled"]["categorical"]["counts"] == [
        {"value": "true", "count": 1}
    ]
    assert facets["need_constraint_satisfaction"]["label"] == (
        "Overall, did the assistant meet what you needed?"
    )


def _write_feedback_task(
    repo_root: Path, *, task: str, schema_lines: list[str]
) -> None:
    input_dir = repo_root / "application" / "tasks" / task / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "self_report_schema.yaml").write_text(
        "\n".join(schema_lines) + "\n", encoding="utf-8"
    )


def _write_feedback_trial(
    job_dir: Path, *, task: str, trial: str, feedback: dict
) -> None:
    trial_dir = job_dir / trial
    output_dir = trial_dir / "artifacts" / "app" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "verifier").mkdir(parents=True, exist_ok=True)
    (trial_dir / "result.json").write_text("{}", encoding="utf-8")
    (trial_dir / "config.json").write_text(
        json.dumps({"task": {"path": "application/tasks/" + task}}),
        encoding="utf-8",
    )
    (trial_dir / "verifier" / "structured_output.json").write_text(
        json.dumps({"presenceCheck": {"passed": True}, "contexts": []}),
        encoding="utf-8",
    )
    (output_dir / "user_feedback.json").write_text(
        json.dumps(feedback), encoding="utf-8"
    )


_NESTED_REASON_SCHEMA = [
    "artifactName: user_feedback.json",
    "fields:",
    "  - key: needConstraintSatisfaction",
    "    prompt: How well did the choice satisfy your need?",
    "    kind: enum",
    "  - key: overallExperienceRating",
    "    prompt: Overall rating",
    "    kind: integer",
    "    minimum: 1",
    "    maximum: 10",
    "    explanation:",
    "      key: reason",
    "      prompt: Briefly explain the rating.",
]


def test_build_job_aggregation_schema_explanation_drives_numeric_group_axis(
    tmp_path: Path,
) -> None:
    """Nested schema ``explanation`` binds reason to the rating (auto-binned)."""
    repo_root = tmp_path
    task = "example-web-schema-bound"
    _write_feedback_task(repo_root, task=task, schema_lines=_NESTED_REASON_SCHEMA)
    job_dir = repo_root / "jobs" / "job"
    for index, (rating, reason) in enumerate(
        [
            (2, "Confusing flow and I gave up early."),
            (6, "Mostly fine but a few rough edges."),
            (9, "Smooth and trustworthy end to end."),
        ]
    ):
        _write_feedback_trial(
            job_dir,
            task=task,
            trial=f"trial-{index}",
            feedback={
                "needConstraintSatisfaction": "yes",
                "overallExperienceRating": rating,
                "reason": reason,
            },
        )

    aggregation = build_job_aggregation(job_dir, repo_root=repo_root, enable_llm=False)
    assert aggregation is not None
    feedback = next(
        context
        for context in aggregation["contexts"]
        if context.get("contextType") == "user_feedback"
    )
    views = feedback.get("crossFacetViews") or []
    reason_view = next(
        view
        for view in views
        if str(view.get("textFacetKey") or "").endswith("feedback_reason")
    )
    assert str(reason_view.get("primaryFacetKey") or "").endswith(
        "overall_experience_rating"
    )
    assert len(reason_view.get("buckets") or []) >= 2
    summaries = feedback.get("summaries") or []
    reason_summary = next(
        summary
        for summary in summaries
        if str(summary.get("targetFacetKey") or "").endswith("feedback_reason")
    )
    assert reason_summary.get("groupByMode") == "numeric_band"
    assert str(reason_summary.get("groupByFacetKey") or "").endswith(
        "overall_experience_rating"
    )


def test_build_job_aggregation_no_binding_no_reason_group(tmp_path: Path) -> None:
    """A reason with no declared target gets no auto group-by (no heuristic guess)."""
    repo_root = tmp_path
    task = "example-web-unbound"
    _write_feedback_task(
        repo_root,
        task=task,
        schema_lines=[
            "artifactName: user_feedback.json",
            "fields:",
            "  - key: needConstraintSatisfaction",
            "    prompt: How well did the choice satisfy your need?",
            "    kind: enum",
            "  - key: overallExperienceRating",
            "    prompt: Overall rating",
            "    kind: integer",
            "    minimum: 1",
            "    maximum: 10",
            "  - key: reason",
            "    prompt: Briefly explain the rating.",
        ],
    )
    job_dir = repo_root / "jobs" / "job"
    for index, (need, rating, reason) in enumerate(
        [
            ("yes", 2, "Confusing flow and I gave up early."),
            ("partially", 6, "Mostly fine but a few rough edges."),
            ("no", 9, "Smooth and trustworthy end to end."),
        ]
    ):
        _write_feedback_trial(
            job_dir,
            task=task,
            trial=f"trial-{index}",
            feedback={
                "needConstraintSatisfaction": need,
                "overallExperienceRating": rating,
                "reason": reason,
            },
        )

    aggregation = build_job_aggregation(job_dir, repo_root=repo_root, enable_llm=False)
    assert aggregation is not None
    feedback = next(
        context
        for context in aggregation["contexts"]
        if context.get("contextType") == "user_feedback"
    )
    views = feedback.get("crossFacetViews") or []
    assert not any(
        str(view.get("textFacetKey") or "").endswith("feedback_reason") for view in views
    )
    summaries = feedback.get("summaries") or []
    assert not any(
        str(summary.get("targetFacetKey") or "").endswith("feedback_reason")
        for summary in summaries
    )


def test_build_job_aggregation_emits_judge_units(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    _write_trial(
        job_dir,
        "trial-1",
        {
            "presenceCheck": {"passed": True},
            "contexts": [
                {
                    "key": "question.q1",
                    "label": "Question 1",
                    "contextType": "question_response",
                    "facets": [
                        {"key": "response", "label": "Response", "role": "primary", "kind": "categorical", "value": "yes"},
                        {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "value": "It is affordable."},
                    ],
                    "signalScans": [
                        {
                            "id": "question.reason_signal_scan",
                            "title": "Reason signal scan",
                            "targetFacetKey": "reason",
                            "groupByFacetKey": "response",
                            "groupByMode": "categorical",
                            "judgeKind": "llm_signal_judge",
                            "prompt": "Read the reason and classify signals.",
                            "rubric": "Set true only when the signal is explicit.",
                            "signals": [
                                {
                                    "key": "price_sensitivity",
                                    "label": "Price sensitivity",
                                    "valueType": "boolean",
                                }
                            ],
                        }
                    ],
                }
            ],
        },
    )

    aggregation = build_job_aggregation(job_dir)

    assert aggregation is not None
    judges = aggregation["contexts"][0]["judges"]
    assert judges[0]["id"] == "question.reason_signal_scan"
    assert judges[0]["signals"][0]["key"] == "price_sensitivity"
    assert judges[0]["rubric"] == "Set true only when the signal is explicit."
    assert judges[0]["status"] == "ready_for_llm"
    assert judges[0]["buckets"][0]["bucket"] == "yes"
    assert aggregation["reporting"]["status"] == "ready"
    assert aggregation["reporting"]["totalUnits"] == 1


def test_build_job_aggregation_executes_and_caches_llm_reporting(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    _write_trial(
        job_dir,
        "trial-1",
        {
            "presenceCheck": {"passed": True},
            "contexts": [
                {
                    "key": "question.q1",
                    "label": "Question 1",
                    "contextType": "question_response",
                    "summaryAnalyses": [
                        {
                            "id": "question.reason_summary",
                            "title": "Reason summary",
                            "targetFacetKey": "reason",
                            "groupByFacetKey": "response",
                            "groupByMode": "categorical",
                            "summaryKind": "llm_bucket_summary",
                        }
                    ],
                    "signalScans": [
                        {
                            "id": "question.reason_judge",
                            "title": "Reason judge",
                            "targetFacetKey": "reason",
                            "groupByFacetKey": "response",
                            "groupByMode": "categorical",
                            "judgeKind": "llm_signal_judge",
                            "prompt": "Spot pricing signals.",
                            "rubric": "Only mark present when explicit.",
                            "signals": [
                                {
                                    "key": "price_sensitivity",
                                    "label": "Price sensitivity",
                                    "valueType": "boolean",
                                }
                            ],
                        }
                    ],
                    "facets": [
                        {"key": "response", "label": "Response", "role": "primary", "kind": "categorical", "value": "yes"},
                        {"key": "reason", "label": "Reason", "role": "explanation", "kind": "textual", "value": "It is affordable and easy to use."},
                    ],
                }
            ],
        },
    )
    client = _FakeChatClient(
        [
            {
                "overallSummary": "Participants liked the affordability rationale.",
                "bucketSummaries": [
                    {
                        "bucket": "yes",
                        "summary": "Affordable pricing was the main reason for positive responses.",
                    }
                ],
            },
            {
                "overallAssessment": "Pricing language is explicit in the positive bucket.",
                "samples": [
                    {"id": 0, "present": ["price_sensitivity"]},
                ],
            },
        ]
    )

    aggregation = build_job_aggregation(job_dir, llm_client=client, enable_llm=True)

    assert aggregation is not None
    summary = aggregation["contexts"][0]["summaries"][0]
    judge = aggregation["contexts"][0]["judges"][0]
    assert summary["status"] == "llm_completed"
    assert summary["overall"]["summary"] == "Participants liked the affordability rationale."
    assert summary["buckets"][0]["summaryType"] == "llm"
    assert judge["status"] == "llm_completed"
    assert judge["overallAssessment"] == "Pricing language is explicit in the positive bucket."
    assert judge["total"] == 1
    assert judge["signalStats"][0]["key"] == "price_sensitivity"
    assert judge["signalStats"][0]["present"] == 1
    assert judge["signalStats"][0]["total"] == 1
    assert judge["buckets"][0]["signalStats"][0]["present"] == 1
    assert aggregation["reporting"]["status"] == "completed"
    assert aggregation["reporting"]["completedUnits"] == 2
    assert len(client.calls) == 2

    cached_only = build_job_aggregation(job_dir, enable_llm=False)

    assert cached_only is not None
    cached_summary = cached_only["contexts"][0]["summaries"][0]
    cached_judge = cached_only["contexts"][0]["judges"][0]
    assert cached_summary["status"] == "llm_completed"
    assert cached_summary["buckets"][0]["summary"] == "Affordable pricing was the main reason for positive responses."
    assert cached_judge["status"] == "llm_completed"
    assert cached_judge["signalStats"][0]["present"] == 1
    assert cached_only["reporting"]["status"] == "completed"


def test_build_job_aggregation_promotes_choice_id_textual_to_categorical(tmp_path: Path) -> None:
    """Survey verifiers historically tagged choice ids as textual — recover full mix."""
    job_dir = tmp_path / "job"
    for index, value in enumerate(
        [
            "q0_pay_when_roi_clear",
            "q0_pay_when_roi_clear",
            "q0_wait_and_see",
            "q0_pay_when_roi_clear",
        ]
    ):
        _write_trial(
            job_dir,
            f"trial-{index}",
            {
                "presenceCheck": {"passed": True},
                "contexts": [
                    {
                        "key": "question.q0",
                        "label": "q0",
                        "contextType": "question_response",
                        "facets": [
                            {
                                "key": "response",
                                "label": "Selected response",
                                "role": "primary",
                                "kind": "textual",
                                "value": value,
                            }
                        ],
                    }
                ],
            },
        )

    aggregation = build_job_aggregation(job_dir, enable_llm=False)
    assert aggregation is not None
    facet = aggregation["contexts"][0]["facets"][0]
    assert facet["kind"] == "categorical"
    assert facet["presentCount"] == 4
    counts = {row["value"]: row["count"] for row in facet["categorical"]["counts"]}
    assert counts == {"q0_pay_when_roi_clear": 3, "q0_wait_and_see": 1}


def test_build_job_aggregation_promotes_subject_label_textual_to_categorical(
    tmp_path: Path,
) -> None:
    """Discrete choice titles must exact-count, even when tagged textual/evidence."""
    job_dir = tmp_path / "job-subject-labels"
    labels = [
        "Data Analysis for Social Scientists",
        "Design of Electromechanical Robotic Systems",
        "Kitchen Chemistry",
        "Data Analysis for Social Scientists",
        "Kitchen Chemistry",
        "Introduction to Computer Science and Programming in Python",
    ]
    for index, label in enumerate(labels):
        _write_trial(
            job_dir,
            f"trial-{index}",
            {
                "presenceCheck": {"passed": True},
                "contexts": [
                    {
                        "key": "decision.primary",
                        "label": "Decision",
                        "contextType": "decision",
                        "facets": [
                            {
                                "key": "decision_subject_label",
                                "label": "Decision subject label",
                                "role": "evidence",
                                "kind": "textual",
                                "value": label,
                            }
                        ],
                    }
                ],
            },
        )

    aggregation = build_job_aggregation(job_dir, enable_llm=False)
    assert aggregation is not None
    facet = aggregation["contexts"][0]["facets"][0]
    assert facet["kind"] == "categorical"
    assert facet["presentCount"] == 6
    counts = {row["value"]: row["count"] for row in facet["categorical"]["counts"]}
    assert counts == {
        "Data Analysis for Social Scientists": 2,
        "Kitchen Chemistry": 2,
        "Design of Electromechanical Robotic Systems": 1,
        "Introduction to Computer Science and Programming in Python": 1,
    }
    assert "textual" not in facet or facet.get("textual") is None


def test_build_job_aggregation_groups_reason_by_declared_numeric_target(
    tmp_path: Path,
) -> None:
    """A reason bound (explainsFacetKey) to a numeric rating groups by auto bands."""
    job_dir = tmp_path / "job-feedback-common"
    for index, (need, reason) in enumerate(
        [
            ("yes", "Clear and useful guidance."),
            ("partially", "Helpful but incomplete."),
            ("no", "Did not address my constraint."),
        ]
    ):
        _write_trial(
            job_dir,
            f"trial-{index}",
            {
                "presenceCheck": {"passed": True},
                "contexts": [
                    {
                        "key": "user_feedback.primary",
                        "label": "User feedback",
                        "contextType": "user_feedback",
                        "facets": [
                            {
                                "key": "overall_experience_rating",
                                "label": "Overall experience rating",
                                "role": "score",
                                "kind": "numerical",
                                "value": 5 + index,
                            },
                            {
                                "key": "feedback_reason",
                                "label": "Feedback reason",
                                "role": "explanation",
                                "kind": "textual",
                                # Explicit binding: reason explains the rating.
                                "explainsFacetKey": "overall_experience_rating",
                                "value": reason,
                            },
                            {
                                "key": "need_constraint_satisfaction",
                                "label": "Need or constraint satisfaction",
                                "role": "evidence",
                                "kind": "categorical",
                                "value": need,
                            },
                            {
                                "key": "clarification_questions_useful",
                                "label": "Clarification questions useful",
                                "role": "primary",
                                "kind": "categorical",
                                "value": "true" if index == 0 else "false",
                            },
                        ],
                    }
                ],
            },
        )

    aggregation = build_job_aggregation(job_dir, enable_llm=False)
    assert aggregation is not None
    feedback = next(
        context
        for context in aggregation["contexts"]
        if context.get("contextType") == "user_feedback"
    )
    views = feedback.get("crossFacetViews") or []
    assert len(views) >= 1
    view = next(
        view
        for view in views
        if str(view.get("textFacetKey") or "").endswith("feedback_reason")
    )
    # Grouped by the declared rating target (auto-binned), not by needs met.
    assert str(view.get("primaryFacetKey") or "").endswith("overall_experience_rating")
    assert len(view.get("buckets") or []) == 3
    # No reason should be grouped by need_constraint_satisfaction anymore.
    assert not any(
        str(view.get("primaryFacetKey") or "").endswith("need_constraint_satisfaction")
        for view in views
    )


def test_build_job_aggregation_skips_constant_task_goal_cross_facet(tmp_path: Path) -> None:
    job_dir = tmp_path / "job-skip-goal"
    for index, status in enumerate(["resolved", "partially_resolved", "not_resolved"]):
        _write_trial(
            job_dir,
            f"trial-{index}",
            {
                "presenceCheck": {"passed": True},
                "contexts": [
                    {
                        "key": "task_outcome.primary",
                        "label": "Task outcome",
                        "contextType": "task_outcome",
                        "facets": [
                            {
                                "key": "outcome_status",
                                "label": "Outcome status",
                                "role": "primary",
                                "kind": "categorical",
                                "value": status,
                            },
                            {
                                "key": "outcome_reason",
                                "label": "Outcome reason",
                                "role": "explanation",
                                "kind": "textual",
                                "explainsFacetKey": "outcome_status",
                                "value": f"Reason for {status}",
                            },
                            {
                                "key": "task_goal_label",
                                "label": "Task goal",
                                "role": "evidence",
                                "kind": "textual",
                                "value": "Get useful medical guidance",
                            },
                        ],
                    }
                ],
            },
        )

    aggregation = build_job_aggregation(job_dir, enable_llm=False)
    assert aggregation is not None
    outcome = aggregation["contexts"][0]
    views = outcome.get("crossFacetViews") or []
    text_keys = [str(view.get("textFacetKey") or "") for view in views]
    assert any(key.endswith("outcome_reason") for key in text_keys)
    assert not any(key.endswith("task_goal_label") for key in text_keys)


def test_verifier_binding_forces_explanation_role(tmp_path: Path) -> None:
    """A textual facet that declares explainsFacetKey is treated as an explanation
    regardless of the role the verifier tagged, and groups by its declared target."""
    job_dir = tmp_path / "job-role-binding"
    for index, status in enumerate(["selected", "rejected", "deferred"]):
        _write_trial(
            job_dir,
            f"trial-{index}",
            {
                "presenceCheck": {"passed": True},
                "contexts": [
                    {
                        "key": "decision.primary",
                        "label": "Primary decision",
                        "contextType": "decision",
                        "facets": [
                            {
                                "key": "decision_outcome",
                                "label": "Decision outcome",
                                "role": "primary",
                                "kind": "categorical",
                                "value": status,
                            },
                            {
                                "key": "reason",
                                "label": "Reason",
                                # Deliberately mis-tagged: the binding must win.
                                "role": "evidence",
                                "kind": "textual",
                                "explainsFacetKey": "decision_outcome",
                                "value": f"Chose to {status} because option {index}.",
                            },
                        ],
                    }
                ],
            },
        )

    aggregation = build_job_aggregation(job_dir, enable_llm=False)
    assert aggregation is not None
    decision = aggregation["contexts"][0]
    reason_facet = next(
        facet for facet in decision["facets"] if facet["facetKey"] == "reason"
    )
    # The declared binding overrides the (wrong) verifier role.
    assert reason_facet["role"] == "explanation"
    views = decision.get("crossFacetViews") or []
    view = next(
        view for view in views if str(view.get("textFacetKey") or "").endswith("reason")
    )
    assert str(view.get("primaryFacetKey") or "").endswith("decision_outcome")


def _write_persona_trial(
    job_dir: Path,
    repo_root: Path,
    *,
    task: str,
    trial: str,
    persona_id: str,
    dimensions: dict,
    contexts: list,
) -> None:
    trial_dir = job_dir / trial
    (trial_dir / "verifier").mkdir(parents=True, exist_ok=True)
    (trial_dir / "result.json").write_text("{}", encoding="utf-8")
    persona_rel = f"application/tasks/{task}/personas/persona_{persona_id}.yaml"
    persona_abs = repo_root / persona_rel
    persona_abs.parent.mkdir(parents=True, exist_ok=True)
    dim_lines = "\n".join(f"  {key}: {value}" for key, value in dimensions.items())
    persona_abs.write_text(f"dimensions:\n{dim_lines}\n", encoding="utf-8")
    (trial_dir / "config.json").write_text(
        json.dumps(
            {
                "task": {"path": f"application/tasks/{task}"},
                "agent": {"kwargs": {"persona_path": persona_rel}},
            }
        ),
        encoding="utf-8",
    )
    (trial_dir / "verifier" / "structured_output.json").write_text(
        json.dumps({"presenceCheck": {"passed": True}, "contexts": contexts}),
        encoding="utf-8",
    )


def _persona_feedback_contexts(rating, need, preference, reason):
    return [
        {
            "key": "user_feedback.primary",
            "label": "User feedback",
            "contextType": "user_feedback",
            "facets": [
                {
                    "key": "overall_experience_rating",
                    "label": "Overall experience rating",
                    "role": "score",
                    "kind": "numerical",
                    "value": rating,
                },
                {
                    "key": "need_constraint_satisfaction",
                    "label": "Need or constraint satisfaction",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": need,
                },
                {
                    "key": "personal_preference_satisfaction",
                    "label": "Personal preference satisfaction",
                    "role": "evidence",
                    "kind": "categorical",
                    "value": preference,
                },
                {
                    "key": "feedback_reason",
                    "label": "Feedback reason",
                    "role": "explanation",
                    "kind": "textual",
                    "explainsFacetKey": "overall_experience_rating",
                    "value": reason,
                },
            ],
        }
    ]


def test_persona_distributions_are_config_driven(tmp_path: Path) -> None:
    """Default persona lens is driven by reporting.json (contextRules → distributions):
    only declared facets become default cards, the explorer options enumerate every
    eligible facet × dimension, and free-text reasons are NOT auto-summarized. A
    persona-grouped summary in the same rule renders in Custom analysis (task lens)."""
    repo_root = tmp_path
    task = "example-persona-auto"
    task_dir = repo_root / "application" / "tasks" / task
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "persona_strategy.json").write_text(
        json.dumps(
            {
                "sampling": {
                    "mode": "stratified",
                    "fields": ["life_stage"],
                    "allocation": "perCell",
                    "perCell": 1,
                }
            }
        ),
        encoding="utf-8",
    )
    (task_dir / "reporting.json").write_text(
        json.dumps(
            {
                "contextRules": [
                    {
                        "match": {"contextType": "user_feedback"},
                        "distributions": [
                            {"facetKey": "overall_experience_rating"},
                            {"facetKey": "need_constraint_satisfaction"},
                        ],
                        "summaryAnalyses": [
                            {
                                "id": "user_feedback.reason_by_life_stage",
                                "title": "What each life stage wanted",
                                "targetFacetKey": "feedback_reason",
                                "groupByPersonaDimension": "life_stage",
                                "summaryKind": "llm_bucket_summary",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    job_dir = repo_root / "jobs" / "job"
    rows = [
        ("p1", "new_parent", 6, "yes", "partially", "Needed reassurance."),
        ("p2", "new_parent", 7, "partially", "yes", "Wanted clear next steps."),
        ("p3", "retiree", 9, "yes", "yes", "Cost was transparent."),
        ("p4", "retiree", 8, "no", "no", "Felt understood."),
    ]
    for persona_id, life_stage, rating, need, preference, reason in rows:
        _write_persona_trial(
            job_dir,
            repo_root,
            task=task,
            trial=f"trial-{persona_id}",
            persona_id=persona_id,
            dimensions={"life_stage": life_stage},
            contexts=_persona_feedback_contexts(rating, need, preference, reason),
        )

    aggregation = build_job_aggregation(job_dir, repo_root=repo_root, enable_llm=False)
    assert aggregation is not None
    feedback = next(
        context
        for context in aggregation["contexts"]
        if context.get("contextType") == "user_feedback"
    )
    # Default cards: only the two declared facets, no more.
    distributions = feedback.get("personaDistributions") or []
    by_facet = {dist["facetKey"]: dist for dist in distributions}
    assert set(by_facet) == {"overall_experience_rating", "need_constraint_satisfaction"}
    rating_dist = by_facet["overall_experience_rating"]
    assert rating_dist["kind"] == "numerical"
    assert rating_dist["groupByPersonaDimension"] == "life_stage"
    assert rating_dist["lens"] == "persona"
    assert len(rating_dist["buckets"]) == 2
    assert all(bucket["numerical"]["avg"] is not None for bucket in rating_dist["buckets"])
    need_dist = by_facet["need_constraint_satisfaction"]
    assert need_dist["kind"] == "categorical"
    assert need_dist.get("categories")
    assert all("categorical" in bucket for bucket in need_dist["buckets"])
    # Explorer options enumerate every eligible facet — including the undeclared one.
    option_facets = {
        opt["facetKey"] for opt in feedback.get("personaDistributionOptions") or []
    }
    assert "personal_preference_satisfaction" in option_facets
    assert "overall_experience_rating" in option_facets
    # ...but the undeclared facet is not a default card.
    assert "personal_preference_satisfaction" not in by_facet
    # Routing is by directive type, not rule list: no summary lands in the persona
    # tab; every LLM summary lives in Custom analysis (task lens).
    summaries = feedback.get("summaries") or []
    assert all(summary.get("lens") != "persona" for summary in summaries)
    # The declared persona-grouped summary is present, tagged task lens, and the
    # persona-attribute grouping was inferred from groupByPersonaDimension.
    life_stage_summary = next(
        summary
        for summary in summaries
        if summary.get("groupByPersonaDimension") == "life_stage"
    )
    assert life_stage_summary["lens"] == "task"
    assert life_stage_summary["groupByMode"] == "persona_attribute"


def test_persona_standalone_facets_from_empty_groupby(tmp_path: Path) -> None:
    """Explicit empty groupByPersonaDimensions → cohort cards, not heatmaps."""
    repo_root = tmp_path
    task = "example-persona-standalone"
    task_dir = repo_root / "application" / "tasks" / task
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "persona_strategy.json").write_text(
        json.dumps(
            {
                "sampling": {
                    "mode": "stratified",
                    "fields": ["life_stage"],
                    "allocation": "perCell",
                    "perCell": 1,
                }
            }
        ),
        encoding="utf-8",
    )
    (task_dir / "reporting.json").write_text(
        json.dumps(
            {
                "contextRules": [
                    {
                        "match": {"contextType": "user_feedback"},
                        "distributions": [
                            {
                                "facetKey": "overall_experience_rating",
                                "title": "Overall satisfaction",
                                "groupByPersonaDimensions": [],
                            },
                            {
                                "facetKey": "need_constraint_satisfaction",
                                "title": "Needs met?",
                                "standalone": True,
                            },
                            {
                                "facetKey": "overall_experience_rating",
                                "title": "Satisfaction by life stage",
                                "groupByPersonaDimensions": ["life_stage"],
                            },
                            {
                                "facetKey": "personal_preference_satisfaction",
                                "title": "Third standalone should be dropped",
                                "groupByPersonaDimensions": [],
                            },
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    job_dir = repo_root / "jobs" / "job"
    for persona_id, life_stage, rating, need, preference, reason in [
        ("p1", "new_parent", 6, "yes", "partially", "a"),
        ("p2", "retiree", 9, "no", "yes", "b"),
    ]:
        _write_persona_trial(
            job_dir,
            repo_root,
            task=task,
            trial=f"trial-{persona_id}",
            persona_id=persona_id,
            dimensions={"life_stage": life_stage},
            contexts=_persona_feedback_contexts(rating, need, preference, reason),
        )

    aggregation = build_job_aggregation(job_dir, repo_root=repo_root, enable_llm=False)
    assert aggregation is not None
    feedback = next(
        context
        for context in aggregation["contexts"]
        if context.get("contextType") == "user_feedback"
    )
    standalones = feedback.get("personaStandaloneFacets") or []
    assert len(standalones) == 2
    assert [row["facetKey"] for row in standalones] == [
        "overall_experience_rating",
        "need_constraint_satisfaction",
    ]
    assert standalones[0]["label"] == "Overall satisfaction"
    crosses = feedback.get("personaDistributions") or []
    assert len(crosses) == 1
    assert crosses[0]["groupByPersonaDimension"] == "life_stage"


def test_persona_distribution_dimensions_fall_back_to_filters(tmp_path: Path) -> None:
    """When persona_strategy has no sampling.fields, distribution directives without
    explicit axes default to the dimensionFilters keys."""
    repo_root = tmp_path
    task = "example-persona-filters"
    task_dir = repo_root / "application" / "tasks" / task
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "persona_strategy.json").write_text(
        json.dumps(
            {
                "dimensionFilters": {
                    "life_stage": ["new_parent", "retiree"],
                }
            }
        ),
        encoding="utf-8",
    )
    (task_dir / "reporting.json").write_text(
        json.dumps(
            {
                "contextRules": [
                    {
                        "match": {"contextType": "user_feedback"},
                        "distributions": [{"facetKey": "overall_experience_rating"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    job_dir = repo_root / "jobs" / "job"
    rows = [
        ("p1", "new_parent", 6, "yes", "partially", "a"),
        ("p2", "new_parent", 7, "partially", "yes", "b"),
        ("p3", "retiree", 9, "yes", "yes", "c"),
        ("p4", "retiree", 8, "no", "no", "d"),
    ]
    for persona_id, life_stage, rating, need, preference, reason in rows:
        _write_persona_trial(
            job_dir,
            repo_root,
            task=task,
            trial=f"trial-{persona_id}",
            persona_id=persona_id,
            dimensions={"life_stage": life_stage},
            contexts=_persona_feedback_contexts(rating, need, preference, reason),
        )

    aggregation = build_job_aggregation(job_dir, repo_root=repo_root, enable_llm=False)
    assert aggregation is not None
    feedback = next(
        context
        for context in aggregation["contexts"]
        if context.get("contextType") == "user_feedback"
    )
    distributions = feedback.get("personaDistributions") or []
    rating_dist = next(
        dist for dist in distributions if dist["facetKey"] == "overall_experience_rating"
    )
    # No sampling.fields → fell back to the dimensionFilters key.
    assert rating_dist["groupByPersonaDimension"] == "life_stage"


def test_aggregate_textual_clusters_near_duplicate_free_text(tmp_path: Path) -> None:
    job_dir = tmp_path / "job-free-text"
    answers = [
        "Adding unit tests for existing functions",
        "Adding unit tests for an existing function",
        "Adding unit tests for existing functions",
        "refactoring a single function to improve readability without changing behavior",
        "Refactoring a single function to improve readability without changing behavior.",
        "something completely different",
    ]
    for index, value in enumerate(answers):
        _write_trial(
            job_dir,
            f"trial-{index}",
            {
                "presenceCheck": {"passed": True},
                "contexts": [
                    {
                        "key": "question.safe_first_task",
                        "label": "safe_first_task",
                        "contextType": "question_response",
                        "questionType": "free_text",
                        "facets": [
                            {
                                "key": "response",
                                "label": "Response",
                                "role": "primary",
                                "kind": "textual",
                                "value": value,
                            }
                        ],
                    }
                ],
            },
        )

    aggregation = build_job_aggregation(job_dir, enable_llm=False)
    assert aggregation is not None
    facet = aggregation["contexts"][0]["facets"][0]
    assert facet["kind"] == "textual"
    textual = facet["textual"]
    assert textual["count"] == 6
    assert 2 <= textual["uniqueCount"] <= 4
    assert sum(row["count"] for row in textual["counts"]) == 6
    # Near-duplicate unit-test answers should land in one theme.
    unit_theme = next(row for row in textual["counts"] if "unit test" in row["value"].lower())
    assert unit_theme["count"] >= 3
    assert "samples" in unit_theme and len(unit_theme["samples"]) >= 1
    refactor_theme = next(row for row in textual["counts"] if "refactor" in row["value"].lower())
    assert refactor_theme["count"] >= 2
    other = next(row for row in textual["counts"] if "completely different" in row["value"].lower())
    assert other["count"] == 1
    assert "theme" in textual["summary"].lower()


def test_execute_summary_llm_chunks_high_cardinality_buckets() -> None:
    bucket_count = SUMMARY_LLM_BUCKET_CHUNK + 5
    summary = {
        "id": "decision.primary.auto_summary.reason",
        "title": "Reason",
        "instruction": "Summarize each bucket.",
        "overall": {"summary": "", "summaryType": "heuristic"},
        "buckets": [
            {
                "bucket": "Course {}".format(index),
                "count": index + 1,
                "samples": ["Reason for course {}.".format(index)],
                "summary": "heuristic {}".format(index),
                "summaryType": "heuristic",
            }
            for index in range(bucket_count)
        ],
        "status": "ready_for_llm",
    }

    class _ChunkAwareClient:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def complete_json(self, system: str, user: str) -> dict:
            payload = json.loads(user)
            self.calls.append(payload)
            if "partialSummaries" in payload:
                return {"overallSummary": "Merged cohort themes across course groups."}
            buckets = payload.get("buckets") or []
            return {
                "overallSummary": "Chunk with {} buckets.".format(len(buckets)),
                "bucketSummaries": [
                    {
                        "bucket": bucket["bucket"],
                        "summary": "LLM summary for {}.".format(bucket["bucket"]),
                    }
                    for bucket in buckets
                ],
            }

    client = _ChunkAwareClient()
    _execute_summary_llm(summary, client=client)

    assert summary["status"] == "llm_completed"
    assert summary["overall"]["summaryType"] == "llm"
    assert "Merged cohort themes" in summary["overall"]["summary"]
    assert all(bucket.get("summaryType") == "llm" for bucket in summary["buckets"])
    # 2 bucket chunks + 1 overall merge
    expected_chunks = (bucket_count + SUMMARY_LLM_BUCKET_CHUNK - 1) // SUMMARY_LLM_BUCKET_CHUNK
    assert len(client.calls) == expected_chunks + 1
    assert all(len(call.get("buckets") or []) <= SUMMARY_LLM_BUCKET_CHUNK for call in client.calls if "buckets" in call)


def test_execute_summary_llm_single_shot_for_small_bucket_sets() -> None:
    summary = {
        "id": "small.summary",
        "title": "Reason",
        "buckets": [
            {"bucket": "yes", "count": 2, "samples": ["Affordable."], "summaryType": "heuristic"},
            {"bucket": "no", "count": 1, "samples": ["Too costly."], "summaryType": "heuristic"},
        ],
        "overall": {"summary": "", "summaryType": "heuristic"},
        "status": "ready_for_llm",
    }
    client = _FakeChatClient(
        [
            {
                "overallSummary": "Price dominated the rationale.",
                "bucketSummaries": [
                    {"bucket": "yes", "summary": "Liked the price."},
                    {"bucket": "no", "summary": "Rejected on price."},
                ],
            }
        ]
    )
    _execute_summary_llm(summary, client=client)
    assert summary["status"] == "llm_completed"
    assert len(client.calls) == 1
    assert summary["buckets"][0]["summary"] == "Liked the price."


def test_failed_llm_summary_is_not_reused_from_cache(tmp_path: Path) -> None:
    job_dir = tmp_path / "job-retry-failed"
    _write_trial(
        job_dir,
        "trial-1",
        {
            "presenceCheck": {"passed": True},
            "contexts": [
                {
                    "key": "question.q1",
                    "label": "Question 1",
                    "contextType": "question_response",
                    "summaryAnalyses": [
                        {
                            "id": "question.reason_summary",
                            "title": "Reason summary",
                            "targetFacetKey": "reason",
                            "groupByFacetKey": "response",
                            "groupByMode": "categorical",
                            "summaryKind": "llm_bucket_summary",
                        }
                    ],
                    "facets": [
                        {
                            "key": "response",
                            "label": "Response",
                            "role": "primary",
                            "kind": "categorical",
                            "value": "yes",
                        },
                        {
                            "key": "reason",
                            "label": "Reason",
                            "role": "explanation",
                            "kind": "textual",
                            "value": "Affordable and simple.",
                        },
                    ],
                }
            ],
        },
    )
    _write_trial(
        job_dir,
        "trial-2",
        {
            "presenceCheck": {"passed": True},
            "contexts": [
                {
                    "key": "question.q1",
                    "label": "Question 1",
                    "contextType": "question_response",
                    "summaryAnalyses": [
                        {
                            "id": "question.reason_summary",
                            "title": "Reason summary",
                            "targetFacetKey": "reason",
                            "groupByFacetKey": "response",
                            "groupByMode": "categorical",
                            "summaryKind": "llm_bucket_summary",
                        }
                    ],
                    "facets": [
                        {
                            "key": "response",
                            "label": "Response",
                            "role": "primary",
                            "kind": "categorical",
                            "value": "no",
                        },
                        {
                            "key": "reason",
                            "label": "Reason",
                            "role": "explanation",
                            "kind": "textual",
                            "value": "Too expensive for me.",
                        },
                    ],
                }
            ],
        },
    )

    class _FlakyClient:
        def __init__(self) -> None:
            self.calls = 0

        def complete_json(self, system: str, user: str) -> dict:
            self.calls += 1
            if self.calls == 1:
                raise ValueError("boom")
            payload = json.loads(user)
            return {
                "overallSummary": "Recovered summary.",
                "bucketSummaries": [
                    {"bucket": bucket["bucket"], "summary": "ok {}".format(bucket["bucket"])}
                    for bucket in payload.get("buckets") or []
                ],
            }

    client = _FlakyClient()
    first = build_job_aggregation(job_dir, llm_client=client, enable_llm=True)
    assert first is not None
    assert first["contexts"][0]["summaries"][0]["status"] == "llm_failed"
    assert client.calls == 1

    second = build_job_aggregation(job_dir, llm_client=client, enable_llm=True)
    assert second is not None
    assert second["contexts"][0]["summaries"][0]["status"] == "llm_completed"
    assert second["contexts"][0]["summaries"][0]["overall"]["summary"] == "Recovered summary."
    assert client.calls == 2


def test_job_aggregation_artifact_is_fresh_matches_disk_coverage(tmp_path: Path) -> None:
    job_dir = tmp_path / "fresh-job"
    payload = {
        "presenceCheck": {"passed": True},
        "contexts": [
            {
                "key": "question.q1",
                "label": "Question 1",
                "contextType": "question_response",
                "facets": [
                    {
                        "key": "response",
                        "label": "Response",
                        "role": "primary",
                        "kind": "categorical",
                        "value": "yes",
                    }
                ],
            }
        ],
    }
    _write_trial(job_dir, "trial-1", payload)
    _write_trial(job_dir, "trial-2", payload)

    aggregation = build_job_aggregation(job_dir, enable_llm=False)
    assert aggregation is not None
    assert job_aggregation_artifact_is_fresh(job_dir, aggregation)

    # Pending trial makes coverage stale.
    pending = job_dir / "trial-3"
    pending.mkdir(parents=True)
    assert not job_aggregation_artifact_is_fresh(job_dir, aggregation)

    # Completing the pending trial without rebuilding stays stale until coverage updates.
    (pending / "result.json").write_text("{}", encoding="utf-8")
    assert not job_aggregation_artifact_is_fresh(job_dir, aggregation)

    rebuilt = build_job_aggregation(job_dir, enable_llm=False)
    assert rebuilt is not None
    assert rebuilt["coverage"]["trialCount"] == 3
    assert job_aggregation_artifact_is_fresh(job_dir, rebuilt)
    assert job_aggregation_artifact_is_fresh(job_dir, read_job_aggregation_artifact(job_dir))


def test_job_aggregation_artifact_is_fresh_rejects_bad_payload(tmp_path: Path) -> None:
    job_dir = tmp_path / "empty-job"
    job_dir.mkdir()
    assert not job_aggregation_artifact_is_fresh(job_dir, None)
    assert not job_aggregation_artifact_is_fresh(job_dir, {"coverage": {}})
    write_job_aggregation(
        job_dir,
        {
            "coverage": {
                "trialCount": 1,
                "completedTrials": 1,
                "pendingTrials": 0,
            }
        },
    )
    # No trial dirs on disk → not fresh.
    assert not job_aggregation_artifact_is_fresh(
        job_dir, read_job_aggregation_artifact(job_dir)
    )
