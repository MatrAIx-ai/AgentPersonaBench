"""Verifier tests for the Minimalism = Enthusiast suite (no network, no Docker).

Each rule-based verifier is run as a subprocess against synthetic agent output,
both directions plus every completeness guard, and the survey/web surfaces are
checked for containment: nothing the agent can see may carry a scoring label.

    python3 evaluation/tests/test_minimalism_verifiers.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SUITE = Path(__file__).resolve().parents[2] / "tasks" / "single-attribute" / \
    "worldview-beliefs" / "attitude-minimalism" / "enthusiast"
SURVEY, WEB, APP, CHAT = (SUITE / f"minimalist-{e}" for e in ("survey", "web", "app", "chat"))

_results = []


def check(name, cond, note=""):
    _results.append((name, bool(cond), note))
    print(f"{'ok  ' if cond else 'FAIL'} {name}{('  ' + note) if note and not cond else ''}")


def run_verifier(task, files):
    """Write the synthetic artifacts, run tests/verifier.py, return (rc, structured)."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out"
        for rel, obj in files.items():
            p = out / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(obj), encoding="utf-8")
        out.mkdir(parents=True, exist_ok=True)
        vd = Path(td) / "verifier"
        env = dict(os.environ, ADHERENCE_OUTPUT_DIR=str(out), ADHERENCE_VERIFIER_DIR=str(vd))
        rc = subprocess.run([sys.executable, str(task / "tests" / "verifier.py")],
                            env=env, capture_output=True, text=True)
        so = vd / "structured_output.json"
        return rc.returncode, (json.loads(so.read_text(encoding="utf-8")) if so.is_file() else {})


# --------------------------------------------------------------------------
# survey
# --------------------------------------------------------------------------
import yaml  # noqa: E402  (pyyaml is a verifier dependency too)

Q = yaml.safe_load((SURVEY / "input" / "questionnaire.yaml").read_text(encoding="utf-8"))
KEY = yaml.safe_load((SURVEY / "tests" / "answer_key.yaml").read_text(encoding="utf-8"))["clutter"]
QIDS = [q["id"] for q in Q["questions"]]
OPTS = {q["id"]: [o["id"] for o in q["options"]] for q in Q["questions"]}


def clean_option(qid):
    return next(o for o in OPTS[qid] if not KEY[o])


def clutter_option(qid):
    return next(o for o in OPTS[qid] if KEY[o])


def answers(mapping):
    return {"answers": [{"questionId": q, "selectedOptionId": o} for q, o in mapping.items()]}


full_clean = {q: clean_option(q) for q in QIDS}

rc, so = run_verifier(SURVEY, {"survey_result.json": answers(full_clean)})
check("survey HELD on an all-essentials sheet", rc == 0 and so.get("verdict") == "HELD", str(so))

one_clutter = dict(full_clean, **{QIDS[0]: clutter_option(QIDS[0])})
rc, so = run_verifier(SURVEY, {"survey_result.json": answers(one_clutter)})
check("survey VIOLATED on one clutter pick",
      rc == 1 and so.get("verdict") == "VIOLATED" and so.get("clutter_picks"), str(so))

rc, so = run_verifier(SURVEY, {"survey_result.json": answers({QIDS[0]: clean_option(QIDS[0])})})
check("survey VIOLATED on a partial sheet (1 of 6 answered)",
      rc == 1 and "unanswered" in str(so.get("incomplete", "")), str(so))

rc, so = run_verifier(SURVEY, {"survey_result.json": {"answers": [
    {"questionId": q, "selectedOptionId": o} for q, o in full_clean.items()] + [
    {"questionId": QIDS[0], "selectedOptionId": clean_option(QIDS[0])}]}})
check("survey VIOLATED when a question is answered twice",
      rc == 1 and "more than once" in str(so.get("incomplete", "")), str(so))

rc, so = run_verifier(SURVEY, {"survey_result.json": answers(
    dict(full_clean, **{QIDS[0]: "q9z"}))})
check("survey VIOLATED on a hallucinated option id",
      rc == 1 and "does not belong" in str(so.get("incomplete", "")), str(so))

rc, so = run_verifier(SURVEY, {"survey_result.json": answers(
    dict(full_clean, **{QIDS[0]: clean_option(QIDS[1])}))})
check("survey VIOLATED on a cross-question option id",
      rc == 1 and "does not belong" in str(so.get("incomplete", "")), str(so))

rc, so = run_verifier(SURVEY, {"survey_result.json": answers(dict(full_clean, zz="q1a"))})
check("survey VIOLATED on an unknown questionId",
      rc == 1 and "unknown questionId" in str(so.get("incomplete", "")), str(so))

# Containment: only input/ is mounted into the agent container, so the mounted
# questionnaire must carry no scoring label, structurally or in its comments, and
# the host-only key must cover every option the agent can choose.
mounted_raw = (SURVEY / "input" / "questionnaire.yaml").read_text(encoding="utf-8").lower()
check("survey input/ mentions no scoring vocabulary",
      not any(w in mounted_raw for w in ("clutter", "flag", "answer_key", "ground truth",
                                         "ground-truth", "label")),
      "a scoring hint leaked into the agent-mounted questionnaire")
extra_keys = ([k for q in Q["questions"] for k in q if k not in ("id", "prompt", "type", "options")]
              + [k for ids in Q["questions"] for o in ids["options"] for k in o
                 if k not in ("id", "text")])
check("survey input/ carries no field beyond id/prompt/type/options and id/text",
      not extra_keys, f"unexpected keys: {extra_keys}")
all_opts = [o for ids in OPTS.values() for o in ids]
check("survey answer key covers every option id",
      set(all_opts) == set(KEY) and len(all_opts) == len(set(all_opts)),
      f"{len(all_opts)} options vs {len(KEY)} labels")

# --------------------------------------------------------------------------
# web
# --------------------------------------------------------------------------
import re  # noqa: E402

html = (WEB / "input" / "site" / "index.html").read_text(encoding="utf-8")
PAGE = {m.group(1): m.group(2).strip().lower() == "true"
        for m in re.finditer(r'class="item"\s+data-id="([^"]+)"\s+data-clutter="([^"]+)"', html)}
clean_ids = [i for i, c in PAGE.items() if not c]
clutter_ids = [i for i, c in PAGE.items() if c]
check("web page parses into a ground-truth map",
      len(PAGE) == 12 and clean_ids and clutter_ids, f"{len(PAGE)} items")

rc, so = run_verifier(WEB, {"anchor/order.json": {"orderedItemIds": clean_ids[:3]}})
check("web HELD on a 3-item essentials cart", rc == 0 and so.get("verdict") == "HELD", str(so))

rc, so = run_verifier(WEB, {"anchor/order.json": {
    "orderedItemIds": clean_ids[:2] + clutter_ids[:1]}})
check("web VIOLATED on one clutter item in the cart",
      rc == 1 and so.get("clutter_in_cart") == clutter_ids[:1], str(so))

rc, so = run_verifier(WEB, {"anchor/order.json": {"orderedItemIds": clean_ids[:1]}})
check("web VIOLATED on a short cart (1 of 3)",
      rc == 1 and "asks for 3" in str(so.get("incomplete", "")), str(so))

rc, so = run_verifier(WEB, {"anchor/order.json": {"orderedItemIds": clean_ids[:4]}})
check("web VIOLATED on a padded cart (4 of 3)",
      rc == 1 and "asks for 3" in str(so.get("incomplete", "")), str(so))

rc, so = run_verifier(WEB, {"anchor/order.json": {
    "orderedItemIds": [clean_ids[0], clean_ids[0], clean_ids[1]]}})
check("web VIOLATED on a duplicated cart",
      rc == 1 and "duplicate" in str(so.get("incomplete", "")), str(so))

rc, so = run_verifier(WEB, {"anchor/order.json": {
    "orderedItemIds": clean_ids[:2] + ["p99"]}})
check("web VIOLATED on an item that is not on the page",
      rc == 1 and "not on the shop page" in str(so.get("incomplete", "")), str(so))

# --------------------------------------------------------------------------
# app
# --------------------------------------------------------------------------
app_src = (APP / "input" / "app" / "cartpop.py").read_text(encoding="utf-8")
MENU = re.findall(r'\(\s*"(i\d+)",\s*"[^"]*",\s*"([^"]*)",[^)]*?(True|False)\)', app_src)
app_clean = [(i, n) for i, n, c in MENU if c == "False"]
app_clutter = [(i, n) for i, n, c in MENU if c == "True"]
check("app menu parses into a ground-truth map",
      len(MENU) == 10 and app_clean and app_clutter, f"{len(MENU)} items")


def order(items):
    return {"orderedItems": [{"id": i, "name": n, "clutter": c} for i, n, c in items]}


rc, so = run_verifier(APP, {"order.json": order(
    [(i, n, False) for i, n in app_clean[:2]])})
check("app HELD on a 2-item essentials order", rc == 0 and so.get("verdict") == "HELD", str(so))

rc, so = run_verifier(APP, {"order.json": order(
    [(app_clean[0][0], app_clean[0][1], False), (app_clutter[0][0], app_clutter[0][1], True)])})
check("app VIOLATED on a clutter item",
      rc == 1 and so.get("clutter_hits") and so["clutter_hits"][0][1] == "catalog", str(so))

# A free-text CUA submission names items without stamping a label. The verdict
# comes from the catalog, so a clutter item cannot be laundered by dropping the
# label, and a clean-looking pair still resolves to HELD.
rc, so = run_verifier(APP, {"order.json": {"orderedItems": [
    {"name": app_clean[0][1]}, {"name": app_clutter[0][1]}]}})
check("app VIOLATED by name alone when no label is stamped",
      rc == 1 and so.get("clutter_hits") and so["clutter_hits"][0][1] == "catalog", str(so))

rc, so = run_verifier(APP, {"order.json": {"orderedItems": [
    {"name": app_clean[0][1]}, {"name": app_clean[1][1].upper()}]}})
check("app HELD on essentials named without a label, case-insensitively",
      rc == 0 and so.get("verdict") == "HELD", str(so))

# The agent's own label is not trusted over the catalog: stamping clutter=False
# on a clutter item must not buy adherence.
rc, so = run_verifier(APP, {"order.json": order(
    [(app_clean[0][0], app_clean[0][1], False), (app_clutter[0][0], app_clutter[0][1], False)])})
check("app ignores a self-reported label that contradicts the catalog",
      rc == 1 and so.get("verdict") == "VIOLATED", str(so))

rc, so = run_verifier(APP, {"order.json": {"orderedItems": [
    {"name": app_clean[0][1]}, {"name": "Something Not On The Menu"}]}})
check("app errors, not VIOLATED, when an item cannot be resolved",
      rc == 2 and so.get("verdict") is None and "unresolved" in str(so.get("error", "")), str(so))

# A fully forged order: two invented items, each self-stamped clutter=false. The
# CUA desktop ships a terminal that can write exactly this file, so a stamped
# label on a name the catalog does not know must not buy adherence.
rc, so = run_verifier(APP, {"order.json": {"orderedItems": [
    {"name": "Imaginary Thing A", "clutter": False},
    {"name": "Imaginary Thing B", "clutter": False}]}})
check("app errors on a forged order even when every item is stamped clutter=false",
      rc == 2 and so.get("verdict") is None and "unresolved" in str(so.get("error", "")), str(so))

rc, so = run_verifier(APP, {"order.json": order([(app_clean[0][0], app_clean[0][1], False)])})
check("app VIOLATED on a one-item order",
      rc == 1 and "asks for 2-3" in str(so.get("incomplete", "")), str(so))

rc, so = run_verifier(APP, {"order.json": order(
    [(i, n, False) for i, n in app_clean[:4]])})
check("app VIOLATED on an oversized order (4 of 2-3)",
      rc == 1 and "asks for 2-3" in str(so.get("incomplete", "")), str(so))

rc, so = run_verifier(APP, {"order.json": order(
    [(app_clean[0][0], app_clean[0][1], False), (app_clean[0][0], app_clean[0][1], False)])})
check("app VIOLATED on a duplicated order",
      rc == 1 and "duplicate" in str(so.get("incomplete", "")), str(so))

rc, so = run_verifier(APP, {"order.json": order(
    [(app_clean[0][0], app_clean[0][1], False), ("i99", "Phantom Item", False)])})
check("app VIOLATED on an id that is not in the catalog",
      rc == 1 and "not in the CartPop catalog" in str(so.get("incomplete", "")), str(so))

check("app refuses to write an order outside 2-3 items",
      "MIN_ITEMS <= len(self.cart) <= MAX_ITEMS" in app_src,
      "the GUI would finalize a partial cart")
check("app input/ and environment/ copies are identical",
      app_src == (APP / "environment" / "cartpop.py").read_text(encoding="utf-8"),
      "the Docker image would ship a different app than the one documented")

# --------------------------------------------------------------------------
# chat: judge-parsing regression, no network needed
# --------------------------------------------------------------------------
# The chat verifier is loaded with a stub llm_client so no network is needed.
# Both mutations below are GLOBAL — sys.path and sys.modules outlive this module
# — so what they replace is saved here and restored at the end of the file.
# `setdefault` does not protect the real module: when llm_client is already
# imported it keeps that object and the assignments below overwrite its `chat`,
# leaving every later test in the session calling a stub that returns "HELD".
_saved_sys_path = list(sys.path)
_saved_llm_client = sys.modules.get("llm_client")
sys.path.insert(0, str(CHAT / "tests"))
sys.modules["llm_client"] = type(sys)("llm_client")
sys.modules["llm_client"].chat = lambda *a, **k: "HELD"
for _n in ("reset_call_log", "get_call_log", "call_log_summary"):
    setattr(sys.modules["llm_client"], _n, lambda *a, **k: {})
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("chatverif", CHAT / "tests" / "verifier.py")
_chat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_chat)

check("chat judge parses a bare HELD", _chat._parse_verdict("HELD") == "HELD")
check("chat judge parses a bare VIOLATED", _chat._parse_verdict(" violated.\n") == "VIOLATED")
check("chat judge does not read 'Not HELD; the verdict is VIOLATED' as adherence",
      _chat._parse_verdict("Not HELD; the verdict is VIOLATED") is None,
      "an ambiguous judge scored as HELD")
check("chat judge treats an unparseable reply as an error",
      _chat._parse_verdict("I think the user was fine") is None)


def run_chat_main(replies):
    """Drive the chat verifier end to end with a scripted judge. Returns (rc, structured)."""
    calls = []

    def stub(*a, **k):
        calls.append(1)
        return replies[min(len(calls) - 1, len(replies) - 1)]

    with tempfile.TemporaryDirectory() as td:
        out, vd = Path(td) / "out", Path(td) / "verifier"
        out.mkdir(parents=True)
        (out / "user_turns.json").write_text(json.dumps(
            {"persona": "minimalism_enthusiast", "turns": ["No thanks, just the lamp."]}),
            encoding="utf-8")
        old = dict(os.environ)
        os.environ.update(ADHERENCE_OUTPUT_DIR=str(out), ADHERENCE_VERIFIER_DIR=str(vd))
        _chat.chat = stub
        try:
            try:
                _chat.main()
                rc = 0
            except SystemExit as e:
                rc = e.code
        finally:
            os.environ.clear(); os.environ.update(old)
        so = vd / "structured_output.json"
        return rc, (json.loads(so.read_text(encoding="utf-8")) if so.is_file() else {}), len(calls)


rc, so, n = run_chat_main(["HELD"])
check("chat HELD when the judge answers cleanly",
      rc == 0 and so.get("verdict") == "HELD" and n == 1, f"{rc} {so.get('verdict')} calls={n}")

rc, so, n = run_chat_main(["VIOLATED"])
check("chat VIOLATED when the judge says so",
      rc == 1 and so.get("verdict") == "VIOLATED" and so.get("reward") == 0.0, str(so.get("verdict")))

# An unparseable judge must not be recorded as a persona violation: the run was
# not measured, so the verdict stays null and the exit code is 2, not 1.
rc, so, n = run_chat_main(["let me think about it"])
check("chat errors after two unparseable judge replies, and does not call it VIOLATED",
      rc == 2 and so.get("verdict") is None and so.get("error") and n == 2,
      f"rc={rc} verdict={so.get('verdict')} calls={n}")

rc, so, n = run_chat_main(["Verdict: HELD", "HELD"])
check("chat retries once and accepts a clean second reply",
      rc == 0 and so.get("verdict") == "HELD" and n == 2, f"rc={rc} calls={n}")

# Containment: input/ is the only thing the chat scenario renders into the user
# simulator's prompt, so it must not name the attribute, its level, or the
# scoring rule. The design note lives in the suite README instead.
chat_input = "\n".join(
    p.read_text(encoding="utf-8").lower()
    for p in sorted((CHAT / "input").rglob("*")) if p.is_file())
leaks = [w for w in ("att_minimalism", "enthusiast", "adherence", "verdict", "held",
                     "violated", "latent", "clutter", "ground truth", "ground-truth",
                     "verifier", "judge", "score") if w in chat_input]
check("chat input/ names neither the attribute nor the scoring rule",
      not leaks, f"leaked: {leaks}")

# A second, subtler leak the lexical check above cannot catch on its own: the
# scenario must not plant the adherent stance in the persona's mouth, nor point
# the simulator at shopping style as the live axis. The judge scores the user's
# turns, so an opener that already reads as minimalist pre-scores the transcript.
# Scoped to context.md, which is the only file rendered into the user simulator's
# frame (chat_harness.py: sut_desc). bot.md is the pushy assistant's own prompt
# and legitimately talks about essentials and add-ons, so it is out of scope.
# This is a regression fence against the two phrasings a reviewer caught, not a
# claim to have solved stance-planting in general.
context_md = (CHAT / "input" / "context.md").read_text(encoding="utf-8").lower()
stance = [w for w in ("actually use", "actually need", "keep it simple",
                      "keep it minimal", "only what", "only buy", "declutter",
                      "how this person likes to shop", "likes to shop",
                      "how they shop", "the essentials") if w in context_md]
check("chat context.md plants no adherent stance and names no shopping-style axis",
      not stance, f"stance phrasing leaked: {stance}")

# --------------------------------------------------------------------------
# Undo the global mutations from the chat section, so the rest of the session
# sees the real llm_client and an unshadowed sys.path.
sys.path[:] = _saved_sys_path
if _saved_llm_client is not None:
    sys.modules["llm_client"] = _saved_llm_client
else:
    sys.modules.pop("llm_client", None)

failed = [n for n, ok, _ in _results if not ok]
print(f"\n{len(_results) - len(failed)}/{len(_results)} passed")


def test_minimalism_verifiers():
    assert not failed, "failed checks: " + ", ".join(failed)


if __name__ == "__main__":
    sys.exit(1 if failed else 0)
