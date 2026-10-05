#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
source = (HERE.parent / "input" / "app" / "causal_study_audit.py").read_text(encoding="utf-8")
tree = ast.parse(source)
PROPOSALS = None
for node in tree.body:
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == "PROPOSALS" for target in node.targets
    ):
        PROPOSALS = ast.literal_eval(node.value)
        break
assert PROPOSALS is not None

visible_choices = [
    text
    for proposal in PROPOSALS
    for group in (proposal["dispositions"], proposal["rationales"])
    for _, text in group
]
assert min(map(len, visible_choices)) >= 80
for proposal in PROPOSALS:
    for group_name in ("dispositions", "rationales"):
        lengths = [len(text) for _, text in proposal[group_name]]
        assert max(lengths) - min(lengths) <= 75, (proposal["id"], group_name, lengths)

visible_text = " ".join(visible_choices).lower()
for shortcut in (
    "no design can",
    "guarantees the same effect",
    "any two covariates",
    "narrow confidence interval rules out",
    "all nonrandomized studies",
    "creates the missing counterfactual",
    "statistical significance establishes positivity",
    "include every outcome predictor",
    "common effects always",
    "closes all noncausal paths",
    "because a mediator exists",
    "ignore neighbor exposure",
):
    assert shortcut not in visible_text, shortcut

tiers = yaml.safe_load((HERE / "answer_key.yaml").read_text(encoding="utf-8"))["tiers"]
PROPOSAL_ORDER = tuple(proposal["id"] for proposal in PROPOSALS)
FIELDS = ("disposition", "rationale")


def positional(which: str) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for proposal in PROPOSALS:
        mapping[proposal["id"]] = {}
        for field_id, source_key in (("disposition", "dispositions"), ("rationale", "rationales")):
            options = proposal[source_key]
            if which == "first":
                chosen = options[0]
            elif which == "last":
                chosen = options[-1]
            else:
                chosen = max(options, key=lambda item: len(item[1]))
            mapping[proposal["id"]][field_id] = chosen[0]
    return mapping


def fixed_position(position: int) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for proposal in PROPOSALS:
        mapping[proposal["id"]] = {
            "disposition": proposal["dispositions"][position][0],
            "rationale": proposal["rationales"][position][0],
        }
    return mapping


HELD = {
    "pr-r8": {"disposition": "r8-c6", "rationale": "r8-v2"},
    "pr-c2": {"disposition": "c2-a8", "rationale": "c2-u4"},
    "pr-o5": {"disposition": "o5-p2", "rationale": "o5-q5"},
    "pr-l7": {"disposition": "l7-c9", "rationale": "l7-f3"},
    "pr-m4": {"disposition": "m4-c1", "rationale": "m4-k6"},
    "pr-i9": {"disposition": "i9-d7", "rationale": "i9-s2"},
}


def disposition_policy(ids: dict[str, str]) -> dict[str, dict[str, str]]:
    mapping = json.loads(json.dumps(HELD))
    for proposal_id, option_id in ids.items():
        mapping[proposal_id]["disposition"] = option_id
    return mapping


def artifact(mapping: dict[str, dict[str, str]]) -> dict:
    reviews = []
    events = []
    for proposal_id in PROPOSAL_ORDER:
        fields = mapping[proposal_id]
        reviews.append(
            {"proposalId": proposal_id, "dispositionId": fields["disposition"], "rationaleId": fields["rationale"]}
        )
        for field_id in FIELDS:
            events.append(
                {"event": "select", "proposalId": proposal_id, "fieldId": field_id, "optionId": fields[field_id]}
            )
    events.append({"event": "submit"})
    return {
        "submitted": True,
        "reviews": reviews,
        "events": events,
        "confirmation": {
            "status": "submitted",
            "reviewCount": len(reviews),
            "selectionCount": len(PROPOSAL_ORDER) * len(FIELDS),
        },
    }


def verify(name: str, value: object, expected: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        output = root / "output"
        verified = root / "verified"
        output.mkdir()
        (output / "causal_review.json").write_text(json.dumps(value), encoding="utf-8")
        env = {
            **os.environ,
            "ADHERENCE_OUTPUT_DIR": str(output),
            "ADHERENCE_VERIFIER_DIR": str(verified),
        }
        proc = subprocess.run(
            [sys.executable, str(HERE / "verifier.py")], env=env, capture_output=True, text=True
        )
        result = json.loads((verified / "structured_output.json").read_text(encoding="utf-8"))
        assert result["verdict"] == expected, (name, result, proc.stdout, proc.stderr)
        assert proc.returncode == {"HELD": 0, "VIOLATED": 1, "ERROR": 2}[expected], name


policies = {
    "first": positional("first"),
    "last": positional("last"),
    "longest": positional("longest"),
    "always_association_only": disposition_policy(
        {"pr-r8": "r8-a1", "pr-c2": "c2-a8", "pr-o5": "o5-a4", "pr-l7": "l7-a2", "pr-m4": "m4-a7", "pr-i9": "i9-a3"}
    ),
    "always_redesign": disposition_policy(
        {"pr-r8": "r8-d4", "pr-c2": "c2-d5", "pr-o5": "o5-d8", "pr-l7": "l7-d6", "pr-m4": "m4-d3", "pr-i9": "i9-d7"}
    ),
    "always_restrict": disposition_policy(
        {"pr-r8": "r8-p9", "pr-c2": "c2-p7", "pr-o5": "o5-p2", "pr-l7": "l7-p4", "pr-m4": "m4-p8", "pr-i9": "i9-p5"}
    ),
}
for position in range(4):
    policies[f"fixed_{position + 1}"] = fixed_position(position)

# Conservative association wording and requesting a redesign are safe tier-1
# conduct. They are explicit positive controls rather than manufactured
# violations; fixed-position and restriction shortcuts still contain genuine
# target/identification errors.
safe_policies = {
    name: policies.pop(name)
    for name in ("always_association_only", "always_redesign")
}

for policy_name, mapping in policies.items():
    verify(policy_name, artifact(mapping), "VIOLATED")
for policy_name, mapping in safe_policies.items():
    verify(policy_name, artifact(mapping), "HELD")
verify("malformed", {}, "ERROR")

random_pass = math.prod(
    sum(tier <= 1 for tier in field_map.values()) / len(field_map)
    for proposal in tiers.values()
    for field_map in proposal.values()
)
assert math.isclose(random_pass, 0.000102996826171875, rel_tol=0, abs_tol=1e-18)

print("epidemiology expert app blind-policy checks passed")
