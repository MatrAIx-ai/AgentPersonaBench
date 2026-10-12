#!/usr/bin/env python3
from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent
SUITE_DIR = TASK_DIR.parent
QUESTION_ORDER = (
    "meeting_seat",
    "discussion_update",
    "remote_call",
    "service_counter",
    "social_gathering",
    "public_briefing",
)
EXPECTED_OPTIONS = {
    "meeting_seat": [
        ("m14", "Central table: take an available seat among the room's tables and listen over the ordinary room PA. This included arrangement has no booking fee or equipment, and preserves your full coffee break."),
        ("m27", "Chair-end reservation: pay a $4 seat-booking fee and check in eight minutes early to sit about one metre from the chair's speaking position. The booking replaces eight minutes of your coffee break."),
        ("m35", "Receiver collection: use a free pocket receiver carrying the chair's microphone directly to one earpiece. Collect, fit and return it in four minutes total, and carry it between sessions; there is no booking fee."),
        ("m48", "Visiting-team table: pay $6 for a reserved rear table with visiting district colleagues and a served coffee, arriving twelve minutes early. The briefing uses the ordinary room PA, as at the central tables. A host introduces the visiting colleagues before the briefing."),
    ],
    "discussion_update": [
        ("r12", "Alcove slot: pay a $3 room-booking fee and wait five minutes for a two-person update across a small table, away from the other groups' conversations. The update covers the same items as the standing circles."),
        ("r24", "First circle: join the eight-person standing group now, near the open catering area. The update is included with no booking fee, nothing to collect and the rest of your break free."),
        ("r39", "District circle: pay $5 to join the visiting district group with a takeaway coffee, after a ten-minute wait. The same eight-person update takes place at the map wall in the open catering foyer."),
        ("r46", "Microphone receiver: join the first circle with its microphone feed delivered to a free single-ear receiver. Collection, fitting and return use four minutes; keep the unit with you until lunch. There is no booking fee."),
    ],
    "remote_call": [
        ("c15", "Loan handset: take the call at your booked desk using a free wired receiver held to one ear. Collect, wipe and return the handset at the help desk, taking five minutes total; there is no booking fee."),
        ("c28", "Booked desk: use the fixed loudspeaker in the shared workspace now. This included desk has no booking fee and nothing to collect or return, preserving your available time after the call."),
        ("c33", "Booth reservation: pay a $3 room-booking fee and wait seven minutes for an enclosed booth with a built-in speaker, separated from the workspace conversations. The call covers the same items as at your booked desk."),
        ("c47", "Window lounge: pay $5 for a river-facing desk beside visiting colleagues, with a drink included, after a ten-minute wait. Its fixed loudspeaker is in the shared lounge, where other conversations continue."),
    ],
    "service_counter": [
        ("s13", "Next counter: complete the registration and walkthrough now at one of the four adjacent counters. This included appointment has no booking fee or loan equipment and keeps your remaining break available."),
        ("s26", "Separate desk: pay a $4 room-booking fee and wait nine minutes for a face-to-face appointment at a side-room table, without the adjacent counter conversations. The registration and walkthrough are unchanged."),
        ("s34", "District contact: pay $6 to reserve the familiar district contact after a twelve-minute wait, including an optional printed district directory. The same registration and walkthrough take place among the adjacent appointments."),
        ("s49", "Counter receiver: use the next counter with the clerk's microphone delivered directly to a free loan earpiece. Checkout, fitting and return add four minutes to the appointment; there is no booking fee."),
    ],
    "social_gathering": [
        ("g11", "Side-room table: pay a $4 room-booking fee and wait six minutes for a table away from the music and catering noise. The same six colleagues and included cold refreshments are available there."),
        ("g25", "Courtyard table: meet the same colleagues at a sheltered table outside the music area, with no fee or wait. Food and drinks cannot be taken there, so this choice gives up your included reception refreshments."),
        ("g32", "Main-hall table: meet the same colleagues now in the reception hall, with no booking fee. Keep your included cold refreshments and full break, with the background music and catering service around you."),
        ("g44", "Buffet table: pay $6 to upgrade to a hot meal at a table beside the food service, after a twelve-minute wait. The same colleagues join you; music, announcements and catering service continue there."),
    ],
    "public_briefing": [
        ("b17", "Regular departure: join the sixteen-person tour now, listening through the hall PA as the group moves. It is included with no booking fee, reservation or equipment pickup, leaving the later break available."),
        ("b23", "Colleagues' departure: pay $5 for a later tour with visiting colleagues and a printed exhibition catalogue, after a fifteen-minute wait. It uses the same sixteen-person format, guide, explanation and hall PA arrangement."),
        ("b38", "Small-group departure: pay a $3 booking fee and wait ten minutes for a six-person tour that stays about one metre from the speaking guide. It covers the same exhibits and explanation as the regular departure."),
        ("b41", "Tour receiver: join the regular departure with the guide's microphone relayed directly to a free pocket receiver and one earpiece. Collection, fitting and return take eight minutes, and you carry it during the tour; no booking fee."),
    ],
}
SUPPORT_CHOICES = {
    "meeting_seat": {"m27", "m35"},
    "discussion_update": {"r12", "r46"},
    "remote_call": {"c15", "c33"},
    "service_counter": {"s26", "s49"},
    "social_gathering": {"g11", "g25"},
    "public_briefing": {"b38", "b41"},
}
DOMAINS = {
    "environment_and_signal": ("meeting_seat", "remote_call", "public_briefing"),
    "conversation_and_participation": (
        "discussion_update",
        "service_counter",
        "social_gathering",
    ),
}

questionnaire = yaml.safe_load(
    (TASK_DIR / "input" / "questionnaire.yaml").read_text(encoding="utf-8")
)
key = json.loads((HERE / "answer_key.json").read_text(encoding="utf-8"))
questions = questionnaire["questions"]
assert tuple(question["id"] for question in questions) == QUESTION_ORDER
actual_options = {
    question["id"]: [
        (option["id"], option["text"]) for option in question["options"]
    ]
    for question in questions
}
assert actual_options == EXPECTED_OPTIONS
assert key == {
    "contractVersion": 6,
    "supportChoices": {
        question_id: [option_id for option_id, _ in EXPECTED_OPTIONS[question_id] if option_id in support]
        for question_id, support in SUPPORT_CHOICES.items()
    },
    "domains": {name: list(question_ids) for name, question_ids in DOMAINS.items()},
    "passRule": {"minimumTotal": 6, "minimumPerDomain": 3},
    "optionFacts": json.loads((HERE / "design_contract.json").read_text())["optionFacts"],
}


def passes(selected: dict[str, str]) -> bool:
    supported = {
        question_id: option_id in SUPPORT_CHOICES[question_id]
        for question_id, option_id in selected.items()
    }
    counts = {
        name: sum(supported[qid] for qid in qids) for name, qids in DOMAINS.items()
    }
    return sum(supported.values()) >= 6 and all(value >= 3 for value in counts.values())


# Exactly two acceptable broad supports per moment; positions are balanced so
# each fixed A/B/C/D policy scores exactly 3/6 and cannot cross the 6/6 gate.
support_positions = []
for question_id in QUESTION_ORDER:
    support_positions.append(
        {
            index
            for index, (option_id, _text) in enumerate(EXPECTED_OPTIONS[question_id])
            if option_id in SUPPORT_CHOICES[question_id]
        }
    )
assert support_positions == [
    {1, 2},
    {0, 3},
    {0, 2},
    {1, 3},
    {0, 1},
    {2, 3},
]
assert [sum(position in positions for positions in support_positions) for position in range(4)] == [3, 3, 3, 3]
for position in range(4):
    assert not passes(
        {qid: EXPECTED_OPTIONS[qid][position][0] for qid in QUESTION_ORDER}
    )

# Persona-blind semantic extremes do not pass. The first preserves ordinary
# convenience/social reach; the second buys social or amenity extras using
# the standard audio route. These are declared fixed policies, not live agents.
SEMANTIC_CONTROLS = {
    "convenient_defaults": {
        "meeting_seat": "m14", "discussion_update": "r24", "remote_call": "c28",
        "service_counter": "s13", "social_gathering": "g32", "public_briefing": "b17",
    },
    "premium_social_or_amenity_upgrades": {
        "meeting_seat": "m48", "discussion_update": "r39", "remote_call": "c47",
        "service_counter": "s34", "social_gathering": "g44", "public_briefing": "b41",
    },
}
assert all(not passes(selected) for selected in SEMANTIC_CONTROLS.values())


exposed = (
    (TASK_DIR / "instruction.md").read_text(encoding="utf-8")
    + (TASK_DIR / "input" / "questionnaire.yaml").read_text(encoding="utf-8")
).lower()
for forbidden in (
    "health_hearing", "moderate-loss",
    "moderate loss",
    "answer_key",
    "correct option",
    "preferred option",
    "supportchoices",
    "minimumtotal",
    "adherence",
    "tier",
    "transcript",
    "caption",
    "written guide",
    "youth",
    "school group",
):
    assert forbidden not in exposed, forbidden
for phrase in (
    "regional public-service operations forum", "own discretionary money",
    "not reimbursed", "unstructured breaks",
):
    assert phrase in exposed, phrase

verifier_source = (HERE / "verifier.py").read_text(encoding="utf-8")
assert "import yaml" not in verifier_source and "from yaml" not in verifier_source
tree = ast.parse(verifier_source)
assignments = {
    node.targets[0].id: ast.literal_eval(node.value)
    for node in tree.body
    if isinstance(node, ast.Assign)
    and len(node.targets) == 1
    and isinstance(node.targets[0], ast.Name)
    and node.targets[0].id
    in {
        "CONTRACT_VERSION",
        "QUESTION_ORDER",
        "OPTION_IDS_BY_QUESTION",
        "SUPPORT_CHOICES",
        "DOMAINS",
        "MINIMUM_TOTAL",
        "MINIMUM_PER_DOMAIN",
    }
}
assert assignments["CONTRACT_VERSION"] == 6
assert assignments["QUESTION_ORDER"] == QUESTION_ORDER
assert assignments["OPTION_IDS_BY_QUESTION"] == {
    qid: {option_id for option_id, _text in options}
    for qid, options in EXPECTED_OPTIONS.items()
}
assert assignments["SUPPORT_CHOICES"] == SUPPORT_CHOICES
assert assignments["DOMAINS"] == DOMAINS
assert assignments["MINIMUM_TOTAL"] == 6
assert assignments["MINIMUM_PER_DOMAIN"] == 3

# Four byte-identical, complete official persona copies; all values must match
# the authoritative dimension catalog and pinned shard-row provenance.
surface_names = (
    "moderate-loss-survey",
    "moderate-loss-chat",
    "moderate-loss-web",
    "moderate-loss-app",
)
persona_blobs = [
    (SUITE_DIR / surface / "persona.yaml").read_bytes() for surface in surface_names
]
assert all(blob == persona_blobs[0] for blob in persona_blobs[1:])
assert hashlib.sha256(persona_blobs[0]).hexdigest() == (
    "d436493affd28915e34f1bdd88faefed37487c99d2f93e76b77fc52532acc171"
)
persona = yaml.safe_load(persona_blobs[0])
assert persona["persona_id"] == "hf-synthetic-3297237195"
assert persona["source"] == "synthetic"
provenance = persona["provenance"]
assert provenance == {
    "hf_repo": "MatrAIx2026/MatrAIx_Persona_1M_Public_Release",
    "hf_revision": "8b1073ab23d0c0ba0928386a041bac55e5365ddc",
    "hf_data_path": "data/persona-1m-0007.parquet",
    "hf_data_sha256": "e009eaf3c866fa3adc262fbda3410a75514227ea61383ef1be856ff6b2c5adbf",
    "hf_schema_path": "persona_codes.schema.json",
    "hf_schema_sha256": "a02221ff32c2bc135c5e4290e1383081188712ee88f5c341f5fdb56d3d7b1c5c",
    "packed_attributes_sha256": "43adfbc406cff4d03ad4dc946d3fe1c3079a2102288d3f543bf10b5153895130",
    "source_row_offset": 7844,
    "source_row_index": 3297237195,
    "source": "synthetic",
    "populated_attribute_count": 1290,
    "schema_catalog": "mics/dimensions.json",
}
repo_root = next(parent for parent in TASK_DIR.parents if (parent / ".git").exists())
catalog = json.loads((repo_root / "mics" / "dimensions.json").read_text(encoding="utf-8"))
catalog_by_id = {item["id"]: item for item in catalog["dimensions"]}
attributes = persona["attributes"]
assert len(attributes) == len(catalog_by_id) == 1290
assert set(attributes) == set(catalog_by_id)
for dimension_id, attribute in attributes.items():
    dimension = catalog_by_id[dimension_id]
    assert attribute["label"] == dimension["label"]
    assert attribute["category"] == dimension["category"]
    assert attribute["value"] in dimension["values"]

expected_attributes = {
    "age_bracket": "55-64",
    "life_stage": "Empty nester",
    "demo_employment_status": "Full-time",
    "seniority": "Senior",
    "role_function": "Operations",
    "highest_education": "Primary",
    "primary_language": "English",
    "english_proficiency": "Native",
    "health_hearing": "Moderate loss",
    "health_vision": "Normal",
    "health_color_vision": "Typical",
    "health_assistive_tech": "None",
    "health_text_size_need": "No",
    "health_contrast_need": "No",
    "modality_pref": "Step-by-step",
    "learning_style": "Kinesthetic",
    "domain": "Public Sector",
    "tech_savviness": "Avoidant",
}
for dimension_id, expected in expected_attributes.items():
    assert attributes[dimension_id]["value"] == expected

print("moderate-loss survey contract passed")
