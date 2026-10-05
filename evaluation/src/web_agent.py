"""Shared multi-step web agent for the `web` surface.

Runs INSIDE the shared-web-playwright container. The persona operates the page
itself, one action per step. By default (APB_WEB_OBS=hybrid) every step it sees
a screenshot of the part of the page on screen with each usable control boxed and
numbered (Set-of-Marks, as in VisualWebArena / WebVoyager), plus the whole
rendered page as text with the same numbers, and it acts by number. With
APB_WEB_OBS=text it gets the text alone (WebArena / Mind2Web style). Nothing is pre-extracted for it
and no script clicks on its behalf; the loop only executes what it chose, and
the persona decides when it is finished.

What the model sees is what a user sees: visible text, control labels, and
visible control state (selected / checked / disabled / typed value). It never
sees element ids, classes, HTML comments or `data-*` attributes, which is where
tasks keep their ground truth.

After the loop ends, the task's final page state is read out as its
`solution/web.json` declares, into the same file the verifier has always read:

    {"role": "a diner choosing meals",
     "outputs": [
       {"path": "anchor/order.json", "kind": "dom",
        "selector": "#cart-items li", "attr": "data-id", "key": "orderedItemIds"},
       {"path": "anchor/selection.json", "kind": "js",
        "expr": "() => window.__artifact"}]}

Optional "notes" are sentences about the person's situation that the page does
not state (a window's width, which slots are final); they are appended to the
goal. A task whose page keeps its state on a small server of its own adds
    "server": {"cmd": ["python3", "server.py", "--port", "0", "--output", "/app/output"]}
and the loop starts it from /app/site and browses to it instead of the file.

`dom` writes {key: [attr of every element matching selector]}; `js` writes
whatever the expression returns as JSON; `text` writes the string the expression
returns as-is (a code file, a message).

Usage (inside the container):
    python3 /app/web_agent.py --goal-file /app/goal.md --spec /app/web.json

Env: PERSONA_SYS (rendered persona system prompt), LLM_MODEL, ADHERENCE_PERSONA,
LLM_PROXY_URL (read by agent_client), WEB_MAX_STEPS (default 40),
APB_WEB_OBS (hybrid | text, default hybrid).
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import time

OUTPUT_DIR = "/app/output"
SITE_URL = "file:///app/site/index.html"
DEFAULT_MAX_STEPS = 40
OBS_MODES = ("hybrid", "text")
VIEWPORT = {"width": 1280, "height": 900}
SCROLL_PX = 700


def obs_mode() -> str:
    mode = (os.environ.get("APB_WEB_OBS") or "hybrid").strip().lower()
    if mode not in OBS_MODES:
        raise ValueError(f"APB_WEB_OBS must be one of {OBS_MODES}, not {mode!r}")
    return mode

# Serialize the rendered page for the model. Interactive controls get a
# numbered ref (stored in a data attribute the model never sees); everything
# else contributes its visible text. Hidden elements are skipped.
OBSERVE_JS = r"""
() => {
  const INTERACTIVE = 'button, a[href], input, select, textarea, summary, [role=button], [role=checkbox], [role=radio], [role=option], [role=tab], [role=link], [onclick], [contenteditable=""], [contenteditable=true]';
  const BLOCK = /^(DIV|P|H[1-6]|LI|UL|OL|SECTION|ARTICLE|HEADER|FOOTER|NAV|MAIN|FORM|TABLE|TR|FIELDSET|LEGEND|LABEL|BR|HR|DL|DT|DD|FIGURE|FIGCAPTION|ASIDE|DETAILS|BLOCKQUOTE|PRE)$/;
  const visible = el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false;
    if (el.hidden || el.getAttribute('aria-hidden') === 'true') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 || r.height > 0 || el.tagName === 'OPTION' || s.display === 'contents';
  };
  document.querySelectorAll('[data-apb-ref]').forEach(el => el.removeAttribute('data-apb-ref'));
  const lines = []; let cur = ''; let n = 0;
  const flush = () => { const t = cur.replace(/\s+/g, ' ').trim(); if (t) lines.push(t); cur = ''; };
  const clean = t => (t || '').replace(/\s+/g, ' ').trim();
  // A field with no label of its own is named by what a reader sees next to
  // it: aria-labelledby, its fieldset legend, the text just before it, or the
  // heading of the block it sits in.
  const nearby = el => {
    const ids = (el.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean);
    const byIds = ids.map(i => document.getElementById(i)).filter(Boolean).map(n => n.innerText).join(' ');
    if (clean(byIds)) return clean(byIds);
    const fs = el.closest('fieldset'); const lg = fs && fs.querySelector('legend');
    if (lg && clean(lg.innerText)) return clean(lg.innerText);
    let prev = el.previousElementSibling;
    while (prev && !clean(prev.innerText)) prev = prev.previousElementSibling;
    if (prev && clean(prev.innerText).length <= 80) return clean(prev.innerText);
    const box = el.closest('section, form, article, div');
    const h = box && box.querySelector('h1, h2, h3, h4, h5, h6, label, legend');
    return h ? clean(h.innerText).slice(0, 80) : '';
  };
  const label = el => {
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable) {
      const byFor = el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      const wrap = el.closest('label');
      return clean(el.getAttribute('aria-label') || (byFor && byFor.innerText)
                   || (wrap && wrap.innerText) || el.placeholder || el.title || nearby(el));
    }
    return clean(el.getAttribute('aria-label') || el.innerText || el.value || el.title || '');
  };
  const state = el => {
    const st = [];
    if (el.disabled || el.getAttribute('aria-disabled') === 'true') st.push('disabled');
    if (el.getAttribute('aria-pressed') === 'true' || el.getAttribute('aria-selected') === 'true'
        || el.getAttribute('aria-checked') === 'true' || el.checked
        || el.classList.contains('selected') || el.classList.contains('active')
        || el.classList.contains('chosen') || el.classList.contains('picked')) st.push('selected');
    if ((el.tagName === 'INPUT' && !['checkbox', 'radio', 'button', 'submit', 'reset'].includes(el.type))
        || el.tagName === 'TEXTAREA' || el.isContentEditable) {
      const v = el.isContentEditable ? el.innerText : el.value;
      st.push(`value="${clean(v).slice(0, 200)}"`);
    }
    if (el.tagName === 'SELECT') {
      const o = el.options[el.selectedIndex];
      st.push(`value="${o ? clean(o.text) : ''}"`);
    }
    return st.length ? ' (' + st.join(', ') + ')' : '';
  };
  const kind = el => {
    if (el.tagName === 'INPUT') {
      if (el.type === 'checkbox' || el.type === 'radio') return el.type;
      if (['button', 'submit', 'reset'].includes(el.type)) return 'button';
      return 'textbox';
    }
    if (el.tagName === 'TEXTAREA' || el.isContentEditable) return 'textbox';
    if (el.tagName === 'SELECT') return 'dropdown';
    if (el.tagName === 'A') return 'link';
    return el.getAttribute('role') || 'button';
  };
  // Repeated generic labels ("Add", "Select", "+") are ambiguous on their own:
  // give each such control the text of the item it belongs to.
  const counts = {};
  document.querySelectorAll(INTERACTIVE).forEach(el => {
    if (visible(el)) { const l = label(el).toLowerCase(); counts[l] = (counts[l] || 0) + 1; }
  });
  const context = el => {
    const l = label(el);
    if ((counts[l.toLowerCase()] || 0) < 2 || l.length > 40) return '';
    const box = el.parentElement && el.parentElement.closest('[data-id], li, tr, article, .item, .card, .product, .option, .choice, fieldset, section');
    if (!box) return '';
    const t = clean(box.innerText).replace(l, '').trim();
    return t ? ` for "${t.slice(0, 100)}"` : '';
  };
  const walk = node => {
    if (node.nodeType === Node.TEXT_NODE) { cur += ' ' + node.textContent; return; }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    const el = node;
    if (/^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE|HEAD|META|LINK)$/.test(el.tagName) || !visible(el)) return;
    if (el.matches(INTERACTIVE)) {
      flush(); n += 1; el.setAttribute('data-apb-ref', String(n));
      let line = `[${n}] ${kind(el)} "${label(el)}"${context(el)}${state(el)}`;
      if (el.tagName === 'SELECT')
        line += ' options: ' + Array.from(el.options).map(o => JSON.stringify(clean(o.text))).join(', ');
      lines.push(line); return;
    }
    const block = BLOCK.test(el.tagName);
    if (block) flush();
    if (/^H[1-6]$/.test(el.tagName)) cur += '#'.repeat(+el.tagName[1]) + ' ';
    if (el.tagName === 'LI') cur += '- ';
    if (el.tagName === 'IMG' && el.alt) cur += ` [image: ${el.alt}] `;
    el.childNodes.forEach(walk);
    if (block) flush();
  };
  walk(document.body); flush();
  return {text: lines.join('\n'), refs: n, title: document.title};
}
"""

# Draw a numbered box over every control observe() numbered that is on screen
# (Set-of-Marks). The overlay ignores the pointer and is removed right after
# the screenshot, so it never changes what the page does.
MARK_JS = r"""
() => {
  const layer = document.createElement('div');
  layer.id = '__apb_marks';
  layer.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:2147483647';
  const W = window.innerWidth, H = window.innerHeight, shown = [];
  document.querySelectorAll('[data-apb-ref]').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1 || r.bottom < 0 || r.right < 0 || r.top > H || r.left > W) return;
    const n = el.getAttribute('data-apb-ref'); shown.push(+n);
    const box = document.createElement('div');
    box.style.cssText = `position:fixed;left:${r.left}px;top:${r.top}px;width:${r.width}px;height:${r.height}px;` +
      'outline:2px solid #e5186e;outline-offset:-1px;box-sizing:border-box';
    const tag = document.createElement('div');
    tag.textContent = n;
    tag.style.cssText = `position:fixed;left:${Math.max(0, r.left - 1)}px;top:${Math.max(0, r.top - 16)}px;` +
      'background:#e5186e;color:#fff;font:bold 12px/15px monospace;padding:0 3px;border-radius:2px';
    layer.appendChild(box); layer.appendChild(tag);
  });
  document.documentElement.appendChild(layer);
  return shown;
}
"""
UNMARK_JS = "() => { const l = document.getElementById('__apb_marks'); if (l) l.remove(); }"

_ACTIONS_TEXT = """Reply with exactly one action as JSON and nothing else:
  {"action": "click", "ref": n}
  {"action": "type", "ref": n, "text": "..."}
  {"action": "select", "ref": n, "option": "<visible option text>"}
  {"action": "done"}"""
_ACTIONS_HYBRID = _ACTIONS_TEXT.replace(
    '\n  {"action": "done"}',
    '\n  {"action": "scroll", "direction": "down" | "up"}\n  {"action": "done"}')
_FINISH = """Take one action at a time and look at the page again before the next one. \
When the task on the page is complete, including any final button the page \
asks you to press, reply {"action": "done"}."""

RULES_TEXT = """You are using a web browser yourself. Each turn you are shown the \
page as text; controls you can use are marked [n], with their current state in \
parentheses. """ + _ACTIONS_TEXT + "\n" + _FINISH

RULES_HYBRID = """You are using a web browser yourself. Each turn you see a \
screenshot of the part of the page currently on screen, where every control you \
can use is outlined and labelled with its number n, and the whole page as text \
with the same numbers [n] and each control's current state in parentheses. \
Controls further down the page can be used by number without scrolling; scroll \
when you want to see them. """ + _ACTIONS_HYBRID + "\n" + _FINISH

RULES = RULES_TEXT  # back-compat name


def rules(mode: str) -> str:
    return RULES_HYBRID if mode == "hybrid" else RULES_TEXT

_MAX_INVALID = 3
_HISTORY = 15  # most recent actions shown back to the model
_ACTIONS = {"click", "type", "select", "scroll", "done"}


def goal_from_instruction(text: str) -> str:
    """The task instruction minus its container-file section, which describes
    what the harness records, not what the person is doing."""
    text = re.split(r"^##\s*Files\b", text, flags=re.M | re.I)[0]
    return text.strip()


def parse_action(raw: str) -> dict | None:
    """The first well-formed action object in a reply. Models sometimes chain
    their plan ({"click"}{"done"}); only one action runs per step, and it is the
    first, so a trailing "done" never ends the task before the click happens."""
    decoder = json.JSONDecoder()
    found = None
    for i, ch in enumerate(raw or ""):
        if ch != "{":
            continue
        try:
            value, _ = decoder.raw_decode(raw[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("action") in _ACTIONS:
            found = value
            break
    if found is not None and isinstance(found.get("ref"), str) and found["ref"].strip().isdigit():
        found["ref"] = int(found["ref"].strip())
    return found


def observe(page) -> dict:
    return page.evaluate(OBSERVE_JS)


def screenshot(page) -> tuple[str, list[int]]:
    """Viewport screenshot with Set-of-Marks boxes over the controls the last
    observe() numbered; returns (base64 JPEG, refs on screen)."""
    shown = page.evaluate(MARK_JS)
    try:
        img = page.screenshot(type="jpeg", quality=75)
    finally:
        page.evaluate(UNMARK_JS)
    return base64.b64encode(img).decode("ascii"), shown


def observe_visual(page) -> dict:
    obs = observe(page)
    obs["image"], obs["on_screen"] = screenshot(page)
    obs["scroll"] = page.evaluate(
        "() => ({y: Math.round(scrollY), h: document.documentElement.scrollHeight, vh: innerHeight})")
    return obs


def act(page, action: dict, n_refs: int) -> str:
    """Execute one action; return a short result line for the history."""
    kind = action["action"]
    if kind == "scroll":
        direction = str(action.get("direction", "down")).lower()
        if direction not in ("down", "up"):
            return f"invalid: scroll direction {direction!r}"
        page.mouse.wheel(0, SCROLL_PX if direction == "down" else -SCROLL_PX)
        page.wait_for_timeout(150)
        return "ok"
    ref = action.get("ref")
    if not isinstance(ref, int) or not 1 <= ref <= n_refs:
        return f"invalid: control [{ref}] is not on the page"
    loc = page.locator(f'[data-apb-ref="{ref}"]')
    try:
        if kind == "click":
            loc.click(timeout=3000)
        elif kind == "type":
            loc.fill(str(action.get("text", "")), timeout=3000)
        elif kind == "select":
            loc.select_option(label=str(action.get("option", "")), timeout=3000)
    except Exception as exc:  # disabled control, bad option, detached node ...
        return f"failed: {type(exc).__name__}: {str(exc).splitlines()[0][:120]}"
    try:
        page.wait_for_load_state("domcontentloaded", timeout=2000)
    except Exception:  # noqa: BLE001 - a same-page update has nothing to wait for
        pass
    page.wait_for_timeout(120)
    return "ok"


def target_of(obs_text: str, ref) -> str:
    m = re.search(rf"^\[{ref}\] (.*)$", obs_text, re.M) if isinstance(ref, int) else None
    return m.group(1)[:100] if m else ""


def run(page, decide, max_steps: int, mode: str = "text") -> tuple[list, str]:
    """Drive the page until *decide* says done. decide(obs, history) -> (action|None, raw).
    In hybrid mode each obs also carries the marked screenshot (obs["image"])."""
    trajectory, history = [], []
    invalid, stop = 0, "max_steps"
    for step in range(1, max_steps + 1):
        obs = observe_visual(page) if mode == "hybrid" else observe(page)
        action, raw = decide(obs, history)
        if action is None:
            invalid += 1
            history.append(f"{step}. (reply was not a valid action)")
            trajectory.append({"step": "model_action", "index": step, "action": None,
                               "raw": (raw or "")[:500]})
            if invalid >= _MAX_INVALID:
                stop = "invalid_actions"
                break
            continue
        invalid = 0
        if action["action"] == "done":
            trajectory.append({"step": "model_action", "index": step, "action": action,
                               "raw": (raw or "")[:500]})
            stop = "done"
            break
        before = obs["text"]
        target = target_of(before, action.get("ref"))
        result = act(page, action, obs["refs"])
        if result == "ok" and action["action"] != "scroll" and observe(page)["text"] == before:
            result = "ok (no visible change)"
        desc = {k: v for k, v in action.items() if k != "action"}
        history.append(f"{step}. {action['action']} {json.dumps(desc, ensure_ascii=False)} "
                       f"on {target or '?'} -> {result}")
        trajectory.append({"step": "model_action", "index": step, "action": action,
                           "target": target, "result": result, "raw": (raw or "")[:500],
                           **({"on_screen": obs["on_screen"]} if "on_screen" in obs else {})})
    return trajectory, stop


def llm_decider(system: str, goal: str, calls: list):
    from agent_client import chat  # host-proxied LLM; imported lazily for tests
    try:
        from agent_client import last_usage  # per-call usage, when the proxy reports it
    except ImportError:  # the host proxy accounts for spend either way
        def last_usage():
            return {}

    def decide(obs, history):
        past = "\n".join(history[-_HISTORY:]) or "(none yet)"
        screen = ""
        if "image" in obs:
            sc = obs["scroll"]
            on = obs["on_screen"]
            screen = (f"SCREENSHOT: attached. On screen: controls "
                      f"{', '.join(map(str, on)) if on else 'none'}; scrolled to "
                      f"{sc['y']}px of {sc['h']}px (window {sc['vh']}px tall).\n\n")
        user = (f"TASK:\n{goal}\n\nYOUR PREVIOUS ACTIONS:\n{past}\n\n{screen}"
                f"CURRENT PAGE ({obs['title']}):\n{obs['text']}\n\n"
                "Your next action (JSON only):")
        t0 = time.time()
        if "image" in obs:
            raw = chat(system=system, user=user, max_tokens=2000,
                       images=[obs["image"]], image_media_type="image/jpeg")
        else:
            raw = chat(system=system, user=user, max_tokens=2000)
        u = last_usage() or {}
        calls.append({"model": u.get("model", os.environ.get("LLM_MODEL", "")),
                      "latency_s": round(time.time() - t0, 3),
                      **{k: u[k] for k in ("prompt_tokens", "completion_tokens",
                                           "total_tokens") if k in u}})
        return parse_action(raw), raw
    return decide


def extract(page, out: dict):
    kind = out.get("kind")
    if kind == "dom":
        attr = out.get("attr", "data-id")
        vals = [el.get_attribute(attr) for el in page.locator(out["selector"]).all()]
        return {out["key"]: [v for v in vals if v is not None]}
    if kind in ("js", "text"):
        return page.evaluate(out["expr"])
    raise ValueError(f"unknown output kind {kind!r}")


def write_outputs(page, spec: dict, root: str = OUTPUT_DIR) -> dict:
    written = {}
    for out in spec["outputs"]:
        state = extract(page, out)
        if out["kind"] == "text" and state is None:
            # nothing was written on the page (e.g. a reply never sent): no
            # file, so the verifier records a missing artifact, not the text "null"
            written[out["path"]] = None
            continue
        dest = os.path.join(root, out["path"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            if out["kind"] == "text":  # a code file or a message, written as-is
                text = "" if state is None else str(state)
                fh.write(text if text.endswith("\n") or not text else text + "\n")
            else:
                json.dump(state, fh, ensure_ascii=False, indent=2)
        written[out["path"]] = state
    return written


def start_server(cfg: dict | None):
    """Start a task's own page server (a site whose state lives server-side).

    cfg = {"cmd": ["python3", "server.py", "--port", "0", "--output", "/app/output"]},
    run from /app/site; the server prints {"port": N} as its first line.
    Returns (process, url) or None when the task is a static page.
    """
    if not cfg:
        return None
    import subprocess
    proc = subprocess.Popen(cfg["cmd"], cwd="/app/site", stdout=subprocess.PIPE, text=True)
    first = proc.stdout.readline()
    port = json.loads(first)["port"]
    return proc, f"http://127.0.0.1:{port}/{cfg.get('path', '')}"


def main() -> None:
    from playwright.sync_api import sync_playwright

    ap = argparse.ArgumentParser()
    ap.add_argument("--goal-file", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--max-steps", type=int,
                    default=int(os.environ.get("WEB_MAX_STEPS", str(DEFAULT_MAX_STEPS))))
    args = ap.parse_args()

    spec = json.load(open(args.spec, encoding="utf-8"))
    mode = obs_mode()
    system = os.environ["PERSONA_SYS"] + "\n\n" + rules(mode)
    goal = goal_from_instruction(open(args.goal_file, encoding="utf-8").read())
    if spec.get("notes"):
        # Facts about the situation that the page itself does not state (the
        # person's own circumstances); part of the task as the person knows it.
        goal += "\n\n" + "\n".join(spec["notes"])
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    calls: list = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VIEWPORT)
        ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = ctx.new_page()
        server = start_server(spec.get("server"))
        page.goto(server[1] if server else SITE_URL, wait_until="domcontentloaded")
        trajectory, stop = run(page, llm_decider(system, goal, calls), args.max_steps, mode)
        written = write_outputs(page, spec)
        trajectory.append({"step": "read_final_state", "state": written})
        ctx.tracing.stop(path=os.path.join(OUTPUT_DIR, "trace.zip"))
        browser.close()
        if server:
            server[0].terminate()
    with open(os.path.join(OUTPUT_DIR, "generation.json"), "w", encoding="utf-8") as fh:
        json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", ""),
                   "model": os.environ.get("LLM_MODEL", ""),
                   "agent": "web_agent", "obs_mode": mode, "stop_reason": stop,
                   "n_steps": sum(1 for t in trajectory if t["step"] == "model_action"),
                   "trajectory": trajectory, "calls": calls},
                  fh, ensure_ascii=False, indent=2)
    print(f"[web_agent] mode={mode} stop={stop} llm_calls={len(calls)} outputs={list(written)}")


if __name__ == "__main__":
    main()
