"""Authored artifact fixtures: verifier tests, never claimed as agent output."""
from __future__ import annotations
import copy
import itertools
import json
from pathlib import Path

KEY = json.loads(Path(__file__).with_name("answer_key.json").read_text())
FIELDS = ("pack", "workspace", "case", "pickup")


def configurations():
    return [dict(zip(FIELDS, row)) for row in itertools.product(
        ("b29", "b73", "b46", "b85"), ("w14", "w62"), ("c83", "c25"), ("r45", "r82"))]


def fixture(selections=None):
    selected = selections or dict(zip(FIELDS, ("b73", "w14", "c83", "r45")))
    materials = [{"item": item, "quantity": 1} for item in KEY["packs"][selected["pack"]]["materials"]]
    panel = {"w14": ("Full fold-out workspace panel", 1), "w62": ("Smaller linked workspace panel", 2)}[selected["workspace"]]
    materials += [{"item": panel[0], "quantity": panel[1]}, {"item": KEY["options"]["case"][selected["case"]], "quantity": 1}]
    snapshot = {"revision": 4, "selections": selected.copy(), "packingList": materials,
                "pickupInstructions": KEY["pickupInstructions"][selected["pickup"]]}
    events = [{"seq": index, "event": "select", "revision": index, "field": field, "optionId": selected[field]}
              for index, field in enumerate(FIELDS, 1)]
    events += [{"seq": 5, "event": "review", **copy.deepcopy(snapshot)},
               {"seq": 6, "event": "confirm", **copy.deepcopy(snapshot)}]
    return {"schemaVersion": 1, "status": "confirmed", "sessionId": "a" * 32,
            **copy.deepcopy(snapshot), "review": copy.deepcopy(snapshot), "events": events}


def invalid_cases():
    cases = {}
    def changed(name, change):
        value = fixture()
        change(value)
        cases[name] = json.dumps(value).encode()
    for key in fixture():
        changed("missing-" + key, lambda x, k=key: x.pop(k))
    for name, value in (("bool-version", True), ("string-version", "1"), ("old-version", 0)):
        changed(name, lambda x, v=value: x.update(schemaVersion=v))
    changed("unconfirmed", lambda x: x.update(status="reviewed"))
    changed("forged-target-claim", lambda x: x.update(targetValue="Avid", reward=1))
    changed("invalid-session", lambda x: x.update(sessionId="not-a-session"))
    changed("bool-revision", lambda x: x.update(revision=True))
    for field in FIELDS:
        changed("unknown-" + field, lambda x, f=field: x["selections"].update({f: "unknown"}))
        changed("list-" + field, lambda x, f=field: x["selections"].update({f: []}))
    changed("partial-selection", lambda x: x["selections"].pop("case"))
    changed("extra-selection", lambda x: x["selections"].update(extra="b73"))
    changed("quantity-bool", lambda x: x["packingList"][0].update(quantity=True))
    changed("quantity-wrong", lambda x: x["packingList"][0].update(quantity=99))
    changed("material-forged", lambda x: x["packingList"][0].update(item="Valuable rare coins"))
    changed("pickup-forged", lambda x: x.update(pickupInstructions="Already shipped"))
    changed("no-history", lambda x: x.update(events=[]))
    changed("reversed-history", lambda x: x.update(events=list(reversed(x["events"]))))
    changed("bool-sequence", lambda x: x["events"][0].update(seq=True))
    changed("wrong-sequence", lambda x: x["events"][0].update(seq=2))
    changed("unknown-event", lambda x: x["events"][0].update(event="submit"))
    changed("wrong-event-field", lambda x: x["events"][0].update(field="reward"))
    changed("unknown-event-option", lambda x: x["events"][0].update(optionId="b00"))
    changed("bool-event-revision", lambda x: x["events"][0].update(revision=True))
    changed("repeated-confirmation", lambda x: x["events"].append({**x["events"][-1], "seq": 7}))
    changed("missing-review", lambda x: x["events"][4].update(event="confirm"))
    changed("select-after-review", lambda x: x["events"].insert(5, {"seq": 6, "event": "select", "revision": 5, "field": "pack", "optionId": "b73"}))
    changed("stale-review", lambda x: x["review"].update(revision=3))
    changed("review-claim-forged", lambda x: x["review"]["selections"].update(pack="b29"))
    changed("changed-workspace-no-new-list", lambda x: x["selections"].update(workspace="w62"))
    cases.update({
        "empty": b"", "malformed": b"{", "null": b"null", "list": b"[]", "object": b"{}",
        "duplicate-key": b'{"schemaVersion":1,"schemaVersion":1}',
        "duplicate-nested-key": json.dumps(fixture()).replace('"pack": "b73"', '"pack": "b73", "pack": "b73"', 1).encode(),
        "nan": b'{"schemaVersion": NaN}', "oversized-integer": b'{"schemaVersion":' + b'9' * 100 + b'}',
        "surrogate": b'{"value":"\\ud800"}', "invalid-utf8": b'\xff',
        "oversized": b' ' * 262145, "deep": b'[' * 1100 + b'0' + b']' * 1100,
    })
    return cases
