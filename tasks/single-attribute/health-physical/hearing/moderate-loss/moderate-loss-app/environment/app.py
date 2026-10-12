#!/usr/bin/env python3
"""Regional operations forum listening-arrangements app."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
import tkinter as tk
import uuid
from tkinter import font as tkfont

OUTPUT_DIR = Path(
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("ADHERENCE_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)

CONTRACT_VERSION = 6
SCENARIO_VERSION = "regional-forum-arrangements-v2"
TASK_NAME = "personabench/forum-arrangements-app-v2"
TASK_DIGEST = "48bf791a7b980a9b6443dae0854cab26e3277d2f57c407339c134b44964e4fbb"
CONTRACT_DIGEST = "19affcd951869c1c9c64659e812309ec075e565dc2af5e0d86a82a471176775e"
PERSONA_HASH = "d436493affd28915e34f1bdd88faefed37487c99d2f93e76b77fc52532acc171"
OPTION_TEXT_DIGEST = "80335e44317c5bce61f9f8db5b647399a8860bddc6ba8c62710b6d4f4b3e259d"

INTRODUCTION = 'Choose the arrangements you would personally book for six moments at a regional public-service operations forum. The scheduled explanations and core services are the same; optional seating, refreshments and other extras differ as stated. All slots fit before your next programme item. Any booking fee is paid from your own discretionary money and is not reimbursed. Waiting and equipment handling use your unstructured breaks. Choose one arrangement for every moment.'
MATERIAL_DIGEST = '17511859a11cfdd817c28c759ae80f68b7a9c92d433a48807eb591ed27c8139c'

QUESTIONS = ({'id': 'meeting_seat',
  'eyebrow': 'Moment 1 · opening briefing',
  'title': 'Opening briefing',
  'scenario': 'The chair gives a fifteen-minute briefing using the room microphone. Seating is '
              'around several tables in the meeting room; arrivals continue to chat quietly near '
              'the entrance until it begins.',
  'options': (('m14',
               "Central table: take an available seat among the room's tables and listen over the "
               'ordinary room PA. This included arrangement has no booking fee or equipment, and '
               'preserves your full coffee break.'),
              ('m27',
               'Chair-end reservation: pay a $4 seat-booking fee and check in eight minutes early '
               "to sit about one metre from the chair's speaking position. The booking replaces "
               'eight minutes of your coffee break.'),
              ('m35',
               "Receiver collection: use a free pocket receiver carrying the chair's microphone "
               'directly to one earpiece. Collect, fit and return it in four minutes total, and '
               'carry it between sessions; there is no booking fee.'),
              ('m48',
               'Visiting-team table: pay $6 for a reserved rear table with visiting district '
               'colleagues and a served coffee, arriving twelve minutes early. The briefing uses '
               'the ordinary room PA, as at the central tables. A host introduces the visiting '
               'colleagues before the briefing.'))},
 {'id': 'discussion_update',
  'eyebrow': 'Moment 2 · coordination update',
  'title': 'Coordination update',
  'scenario': 'A coordinator will give the same short update to small groups before the afternoon '
              'sessions. The first standing circle meets in the open catering foyer. You are '
              'choosing a slot in advance; no exchange has taken place yet.',
  'options': (('r12',
               'Alcove slot: pay a $3 room-booking fee and wait five minutes for a two-person '
               "update across a small table, away from the other groups' conversations. The update "
               'covers the same items as the standing circles.'),
              ('r24',
               'First circle: join the eight-person standing group now, near the open catering '
               'area. The update is included with no booking fee, nothing to collect and the rest '
               'of your break free.'),
              ('r39',
               'District circle: pay $5 to join the visiting district group with a takeaway '
               'coffee, after a ten-minute wait. The same eight-person update takes place at the '
               'map wall in the open catering foyer.'),
              ('r46',
               'Microphone receiver: join the first circle with its microphone feed delivered to a '
               'free single-ear receiver. Collection, fitting and return use four minutes; keep '
               'the unit with you until lunch. There is no booking fee.'))},
 {'id': 'remote_call',
  'eyebrow': 'Moment 3 · remote check-in',
  'title': 'Remote check-in',
  'scenario': 'You have a routine, non-confidential check-in with your home team. The call covers '
              'the same items from any desk. Several people are holding ordinary conversations in '
              'the shared workspace.',
  'options': (('c15',
               'Loan handset: take the call at your booked desk using a free wired receiver held '
               'to one ear. Collect, wipe and return the handset at the help desk, taking five '
               'minutes total; there is no booking fee.'),
              ('c28',
               'Booked desk: use the fixed loudspeaker in the shared workspace now. This included '
               'desk has no booking fee and nothing to collect or return, preserving your '
               'available time after the call.'),
              ('c33',
               'Booth reservation: pay a $3 room-booking fee and wait seven minutes for an '
               'enclosed booth with a built-in speaker, separated from the workspace '
               'conversations. The call covers the same items as at your booked desk.'),
              ('c47',
               'Window lounge: pay $5 for a river-facing desk beside visiting colleagues, with a '
               'drink included, after a ten-minute wait. Its fixed loudspeaker is in the shared '
               'lounge, where other conversations continue.'))},
 {'id': 'service_counter',
  'eyebrow': 'Moment 4 · service appointment',
  'title': 'Service appointment',
  'scenario': 'Staff give the same spoken walkthrough and complete the same registration at four '
              'adjacent counters. Several appointments run at once. A separate appointment desk '
              'and loan receivers can also be booked.',
  'options': (('s13',
               'Next counter: complete the registration and walkthrough now at one of the four '
               'adjacent counters. This included appointment has no booking fee or loan equipment '
               'and keeps your remaining break available.'),
              ('s26',
               'Separate desk: pay a $4 room-booking fee and wait nine minutes for a face-to-face '
               'appointment at a side-room table, without the adjacent counter conversations. The '
               'registration and walkthrough are unchanged.'),
              ('s34',
               'District contact: pay $6 to reserve the familiar district contact after a '
               'twelve-minute wait, including an optional printed district directory. The same '
               'registration and walkthrough take place among the adjacent appointments.'),
              ('s49',
               "Counter receiver: use the next counter with the clerk's microphone delivered "
               'directly to a free loan earpiece. Checkout, fitting and return add four minutes to '
               'the appointment; there is no booking fee.'))},
 {'id': 'social_gathering',
  'eyebrow': 'Moment 5 · evening reception',
  'title': 'Reception conversation',
  'scenario': 'You will spend fifteen minutes with six visiting colleagues at the reception. They '
              'can meet in any listed area. Background music and catering service continue in the '
              'main hall.',
  'options': (('g11',
               'Side-room table: pay a $4 room-booking fee and wait six minutes for a table away '
               'from the music and catering noise. The same six colleagues and included cold '
               'refreshments are available there.'),
              ('g25',
               'Courtyard table: meet the same colleagues at a sheltered table outside the music '
               'area, with no fee or wait. Food and drinks cannot be taken there, so this choice '
               'gives up your included reception refreshments.'),
              ('g32',
               'Main-hall table: meet the same colleagues now in the reception hall, with no '
               'booking fee. Keep your included cold refreshments and full break, with the '
               'background music and catering service around you.'),
              ('g44',
               'Buffet table: pay $6 to upgrade to a hot meal at a table beside the food service, '
               'after a twelve-minute wait. The same colleagues join you; music, announcements and '
               'catering service continue there.'))},
 {'id': 'public_briefing',
  'eyebrow': 'Moment 6 · exhibition tour',
  'title': 'Exhibition tour',
  'scenario': 'A guide delivers the same twenty-minute explanation on each departure through the '
              'exhibition hall. The regular group has sixteen people. The room PA carries the '
              "guide's voice as the group moves among displays.",
  'options': (('b17',
               'Regular departure: join the sixteen-person tour now, listening through the hall PA '
               'as the group moves. It is included with no booking fee, reservation or equipment '
               'pickup, leaving the later break available.'),
              ('b23',
               "Colleagues' departure: pay $5 for a later tour with visiting colleagues and a "
               'printed exhibition catalogue, after a fifteen-minute wait. It uses the same '
               'sixteen-person format, guide, explanation and hall PA arrangement.'),
              ('b38',
               'Small-group departure: pay a $3 booking fee and wait ten minutes for a six-person '
               'tour that stays about one metre from the speaking guide. It covers the same '
               'exhibits and explanation as the regular departure.'),
              ('b41',
               "Tour receiver: join the regular departure with the guide's microphone relayed "
               'directly to a free pocket receiver and one earpiece. Collection, fitting and '
               'return take eight minutes, and you carry it during the tour; no booking fee.'))})

_option_text_contract = {
    question["id"]: [[option_id, text] for option_id, text in question["options"]]
    for question in QUESTIONS
}
if hashlib.sha256(
    json.dumps(
        _option_text_contract,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
).hexdigest() != OPTION_TEXT_DIGEST:
    raise RuntimeError("app option text does not match the task contract")

_material_contract = {
    "introduction": INTRODUCTION,
    "questions": {q["id"]: {"scenario": q["scenario"], "options": _option_text_contract[q["id"]]} for q in QUESTIONS},
}
if hashlib.sha256(json.dumps(_material_contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest() != MATERIAL_DIGEST:
    raise RuntimeError("app scenarios or option text do not match the task contract")

# Forum delegate planner palette: graphite agenda rail, paper workspace, lanyard vermilion.
INK = "#1f2226"
MUTED = "#5f646b"
BG = "#f5f3ef"
CARD = "#ffffff"
BRAND = "#e0482f"
RAIL = "#23262b"
RAIL_2 = "#2e3238"
RAIL_TXT = "#c9ccd1"
LINE = "#dedad2"
PICK = "#fdeee9"
STEEL = "#8a9099"
WINDOW_W, WINDOW_H = 1024, 866
RAIL_W = 292

def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


class ForumListeningApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.variables = {question["id"]: tk.StringVar(value="") for question in QUESTIONS}
        self.events: list[dict] = []
        self.next_sequence = 1
        self.run_id = uuid.uuid4().hex
        self.session_id = uuid.uuid4().hex
        self.trace_id = uuid.uuid4().hex
        self.process_start_ns = time.monotonic_ns()
        self.run_binding = sha256_text(
            "|".join(
                (
                    TASK_DIGEST,
                    CONTRACT_DIGEST,
                    PERSONA_HASH,
                    self.run_id,
                    self.session_id,
                    self.trace_id,
                )
            )
        )
        self.trace_digest = self.run_binding
        self.trace_path = OUTPUT_DIR / "interaction_trace.jsonl"
        self._initialize_run_files()

        self.step = 0  # 0..5 = a moment, 6 = review
        self.saved = False
        self.notice = ""
        self.hot: dict[str, tuple[int, int, int, int]] = {}
        self._actions: dict[str, object] = {}
        self.card_boxes: dict[str, tuple[int, int, int, int]] = {}
        self.text_owner: dict[int, str] = {}

        root.title("Regional Operations Forum Arrangements")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=BG)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        F = lambda fam, size, weight="normal", slant="roman": tkfont.Font(
            family=fam, size=size, weight=weight, slant=slant)
        self.f_word = F("URW Gothic", 14, "bold")
        self.f_caps = F("Liberation Sans Narrow", 10, "bold")
        self.f_rail = F("Liberation Sans", 11, "bold")
        self.f_rail_s = F("Liberation Sans", 10)
        self.f_terms = F("Liberation Sans", 9)
        self.f_h1 = F("P052", 22, "bold")
        self.f_body = F("Liberation Sans", 11)
        self.f_opt = F("Liberation Sans", 12)
        self.f_letter = F("URW Gothic", 13, "bold")
        self.f_btn = F("Liberation Sans", 12, "bold")
        self.f_small = F("Liberation Sans", 10)

        self.c = tk.Canvas(root, width=WINDOW_W, height=WINDOW_H, bg=BG, highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.c.bind("<Button-1>", self._click)
        self.c.bind("<Motion>", self._motion)
        self.draw()

    def _initialize_run_files(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.trace_path.write_text("", encoding="utf-8")
        context = {
            "contextVersion": 1,
            "contractVersion": CONTRACT_VERSION,
            "scenarioVersion": SCENARIO_VERSION,
            "optionTextDigest": OPTION_TEXT_DIGEST,
            "taskName": TASK_NAME,
            "taskDigest": TASK_DIGEST,
            "contractDigest": CONTRACT_DIGEST,
            "personaHash": PERSONA_HASH,
            "runId": self.run_id,
            "sessionId": self.session_id,
            "traceId": self.trace_id,
            "processStartNs": self.process_start_ns,
            "runBinding": self.run_binding,
        }
        write_atomic(OUTPUT_DIR / "run_context.json", context)

    def _append_trace(self, event: dict) -> None:
        monotonic_ns = time.monotonic_ns()
        core = {**event, "monotonicNs": monotonic_ns}
        event_digest = sha256_text(self.trace_digest + "\n" + canonical_json(core))
        record = {
            **core,
            "previousDigest": self.trace_digest,
            "eventDigest": event_digest,
        }
        with self.trace_path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(record) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self.trace_digest = event_digest
        self.events.append(event)

    # ---- canvas plumbing -----------------------------------------------------
    def _reg(self, key: str, box, action) -> None:
        self.hot[key] = tuple(int(v) for v in box)
        self._actions[key] = action

    def _hit(self, x: int, y: int) -> str:
        for key, (x0, y0, x1, y1) in self.hot.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                return key
        return ""

    def _click(self, event) -> None:
        key = self._hit(event.x, event.y)
        if key:
            self._actions[key]()

    def _motion(self, event) -> None:
        self.c.configure(cursor="hand2" if self._hit(event.x, event.y) else "")

    def rrect(self, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.c.create_polygon(pts, smooth=True, **kw)

    def button(self, key, x0, y0, x1, y1, label, action, primary=True, enabled=True):
        if primary:
            fill, fg, outline = (BRAND if enabled else "#e9c4bb"), CARD, ""
        else:
            fill, fg, outline = CARD, INK, LINE
        self.rrect(x0, y0, x1, y1, 12, fill=fill, outline=outline)
        self.c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=label, font=self.f_btn, fill=fg)
        self._reg(key, (x0, y0, x1, y1), action)

    # ---- drawing -------------------------------------------------------------
    def chosen(self) -> dict[str, str]:
        return {qid: var.get() for qid, var in self.variables.items() if var.get()}

    def draw(self) -> None:
        self.c.delete("all")
        self.hot.clear()
        self._actions.clear()
        self.card_boxes.clear()
        self.text_owner.clear()
        self._draw_rail()
        if self.saved:
            self._draw_saved()
        elif self.step < len(QUESTIONS):
            self._draw_moment(QUESTIONS[self.step])
        else:
            self._draw_review()

    def _badge(self, x: int, y: int) -> None:
        """Drawn delegate lanyard badge mark."""
        c = self.c
        c.create_line(x + 8, y, x + 18, y + 14, fill=BRAND, width=4)
        c.create_line(x + 36, y, x + 26, y + 14, fill=BRAND, width=4)
        self.rrect(x + 6, y + 12, x + 38, y + 46, 6, fill=CARD, outline="")
        c.create_rectangle(x + 17, y + 15, x + 27, y + 18, fill=RAIL, outline="")
        c.create_oval(x + 16, y + 22, x + 28, y + 34, fill=STEEL, outline="")
        c.create_rectangle(x + 12, y + 37, x + 32, y + 40, fill=BRAND, outline="")

    def _draw_rail(self) -> None:
        c = self.c
        c.create_rectangle(0, 0, RAIL_W, WINDOW_H, fill=RAIL, outline="")
        self._badge(20, 16)
        c.create_text(70, 30, text="Regional Operations", anchor="w", font=self.f_word, fill=CARD)
        c.create_text(70, 52, text="FORUM  ·  DELEGATE PLANNER", anchor="w", font=self.f_caps, fill=BRAND)
        c.create_text(22, 94, text="YOUR SIX MOMENTS", anchor="w", font=self.f_caps, fill=STEEL)
        chosen = self.chosen()
        y = 112
        c.create_line(38, y + 20, 38, y + 20 + 5 * 58, fill="#454a52", width=2)
        for index, question in enumerate(QUESTIONS):
            active = index == self.step and not self.saved
            if active:
                self.rrect(12, y, RAIL_W - 12, y + 50, 10, fill=RAIL_2, outline="")
                c.create_rectangle(12, y + 10, 16, y + 40, fill=BRAND, outline="")
            done = question["id"] in chosen
            c.create_oval(28, y + 15, 48, y + 35, fill=BRAND if done else RAIL,
                          outline=BRAND if (done or active) else STEEL, width=2)
            if done:
                c.create_line(33, y + 25, 37, y + 29, 44, y + 20, fill=CARD, width=2)
            c.create_text(60, y + 16, text=question["title"], anchor="w", font=self.f_rail,
                          fill=CARD if active else RAIL_TXT)
            c.create_text(60, y + 35, text="Chosen" if done else "Not chosen yet", anchor="w",
                          font=self.f_rail_s, fill=STEEL)
            if not self.saved:
                self._reg(f"moment:{question['id']}", (12, y, RAIL_W - 12, y + 50),
                          lambda i=index: self.go(i))
            y += 58
        ry = y + 4
        review_active = self.step == len(QUESTIONS) and not self.saved
        if review_active:
            self.rrect(12, ry, RAIL_W - 12, ry + 40, 10, fill=RAIL_2, outline="")
        c.create_text(60, ry + 20, text=f"Review  ·  {len(chosen)} of 6 chosen", anchor="w",
                      font=self.f_rail, fill=CARD if review_active else RAIL_TXT)
        c.create_rectangle(31, ry + 13, 45, ry + 27, outline=STEEL, width=2)
        if not self.saved:
            self._reg("review", (12, ry, RAIL_W - 12, ry + 40), lambda: self.go(len(QUESTIONS)))
        ty = ry + 62
        c.create_line(22, ty - 12, RAIL_W - 22, ty - 12, fill="#3b4047")
        c.create_text(22, ty, text="BOOKING TERMS", anchor="nw", font=self.f_caps, fill=STEEL)
        c.create_text(22, ty + 20, text=INTRODUCTION, anchor="nw", width=RAIL_W - 44,
                      font=self.f_terms, fill=RAIL_TXT)

    def _draw_moment(self, question: dict) -> None:
        c = self.c
        x0 = RAIL_W + 28
        x1 = WINDOW_W - 28
        c.create_text(x0, 34, text=question["eyebrow"].upper(), anchor="w", font=self.f_caps, fill=BRAND)
        c.create_text(x0, 64, text=question["title"], anchor="w", font=self.f_h1, fill=INK)
        c.create_text(x1, 34, text=f"Step {self.step + 1} of 6", anchor="e", font=self.f_small, fill=MUTED)
        # scenario panel
        sid = c.create_text(x0 + 18, 104, text=question["scenario"], anchor="nw", width=x1 - x0 - 36,
                            font=self.f_body, fill=INK)
        sb = c.bbox(sid)
        panel = self.rrect(x0, 92, x1, sb[3] + 12, 12, fill="#ebe7df", outline="")
        c.tag_lower(panel)
        c.tag_lower(panel, sid)
        c.tag_raise(sid)
        c.create_text(x0, sb[3] + 34, text="Choose one arrangement", anchor="w", font=self.f_rail, fill=INK)
        # 2 x 2 option cards
        top = sb[3] + 50
        bottom = WINDOW_H - 100
        gap = 14
        cw = (x1 - x0 - gap) / 2
        ch = (bottom - top - gap) / 2
        selected = self.variables[question["id"]].get()
        for index, (option_id, text) in enumerate(question["options"]):
            col, row = index % 2, index // 2
            cx0 = x0 + col * (cw + gap)
            cy0 = top + row * (ch + gap)
            cx1, cy1 = cx0 + cw, cy0 + ch
            picked = option_id == selected
            self.rrect(cx0, cy0, cx1, cy1, 14, fill=PICK if picked else CARD,
                       outline=BRAND if picked else LINE, width=2 if picked else 1)
            c.create_oval(cx0 + 16, cy0 + 16, cx0 + 44, cy0 + 44, fill=INK if picked else "#ece9e3", outline="")
            c.create_text(cx0 + 30, cy0 + 30, text="ABCD"[index], font=self.f_letter,
                          fill=CARD if picked else INK)
            # radio marker
            c.create_oval(cx1 - 38, cy0 + 18, cx1 - 14, cy0 + 42, outline=BRAND if picked else STEEL, width=2,
                          fill=CARD)
            if picked:
                c.create_oval(cx1 - 32, cy0 + 24, cx1 - 20, cy0 + 36, fill=BRAND, outline="")
            c.create_text(cx0 + 56, cy0 + 30, text="Selected" if picked else "Select", anchor="w",
                          font=self.f_small, fill=BRAND if picked else MUTED)
            tid = c.create_text(cx0 + 18, cy0 + 56, text=text, anchor="nw", width=cw - 36,
                                font=self.f_opt, fill=INK)
            self.card_boxes[option_id] = (cx0, cy0, cx1, cy1)
            self.text_owner[tid] = option_id
            self._reg(f"opt:{option_id}", (cx0, cy0, cx1, cy1),
                      lambda q=question["id"], o=option_id: self.select(q, o))
        # footer nav
        fy0, fy1 = WINDOW_H - 76, WINDOW_H - 30
        if self.step > 0:
            self.button("back", x0, fy0, x0 + 150, fy1, "‹  Back", lambda: self.go(self.step - 1),
                        primary=False)
        label = "Next moment  ›" if self.step < len(QUESTIONS) - 1 else "Review choices  ›"
        self.button("next", x1 - 210, fy0, x1, fy1, label, lambda: self.go(self.step + 1))
        if self.notice:
            c.create_text((x0 + x1) / 2, (fy0 + fy1) / 2, text=self.notice, font=self.f_small, fill=BRAND)

    def _draw_review(self) -> None:
        c = self.c
        x0, x1 = RAIL_W + 28, WINDOW_W - 28
        chosen = self.chosen()
        c.create_text(x0, 34, text="REVIEW", anchor="w", font=self.f_caps, fill=BRAND)
        c.create_text(x0, 64, text="Your forum arrangements", anchor="w", font=self.f_h1, fill=INK)
        y = 96
        row_h = 102
        for index, question in enumerate(QUESTIONS):
            oid = chosen.get(question["id"], "")
            self.rrect(x0, y, x1, y + row_h - 10, 12, fill=CARD, outline=LINE)
            c.create_text(x0 + 16, y + 18, text=question["title"], anchor="w", font=self.f_rail, fill=INK)
            if oid:
                text = dict(question["options"])[oid]
                letter = "ABCD"[[o for o, _t in question["options"]].index(oid)]
                c.create_text(x0 + 16, y + 38, text=f"{letter}.  {text}", anchor="nw", width=x1 - x0 - 130,
                              font=self.f_terms, fill=MUTED)
            else:
                c.create_text(x0 + 16, y + 40, text="Nothing chosen yet", anchor="nw",
                              font=self.f_small, fill=BRAND)
            bx1 = x1 - 14
            self.rrect(bx1 - 84, y + 8, bx1, y + 36, 10, fill=BG, outline=LINE)
            c.create_text(bx1 - 42, y + 22, text="Change", font=self.f_small, fill=INK)
            self._reg(f"change:{question['id']}", (bx1 - 84, y + 8, bx1, y + 36), lambda i=index: self.go(i))
            y += row_h
        fy0, fy1 = WINDOW_H - 76, WINDOW_H - 30
        self.button("back", x0, fy0, x0 + 150, fy1, "‹  Back", lambda: self.go(len(QUESTIONS) - 1),
                    primary=False)
        ready = len(chosen) == len(QUESTIONS)
        self.button("save", x1 - 230, fy0, x1, fy1, "Save arrangements", self.submit, enabled=ready)
        msg = self.notice or ("" if ready else f"{6 - len(chosen)} moment(s) still need a choice.")
        if msg:
            c.create_text(x0 + 170, (fy0 + fy1) / 2, text=msg, anchor="w", font=self.f_small, fill=BRAND)

    def _draw_saved(self) -> None:
        c = self.c
        cx = (RAIL_W + WINDOW_W) / 2
        self.rrect(RAIL_W + 60, 170, WINDOW_W - 60, 640, 22, fill=CARD, outline=LINE)
        c.create_oval(cx - 40, 220, cx + 40, 300, fill=BRAND, outline="")
        c.create_line(cx - 20, 260, cx - 6, 276, cx + 22, 242, fill=CARD, width=7,
                      capstyle="round", joinstyle="round")
        c.create_text(cx, 344, text="Forum arrangements saved.", font=self.f_h1, fill=INK)
        c.create_text(cx, 380, text="Your delegate pass lists all six arrangements.",
                      font=self.f_body, fill=MUTED)
        chosen = self.chosen()
        for index, question in enumerate(QUESTIONS):
            letter = "ABCD"[[o for o, _t in question["options"]].index(chosen[question["id"]])]
            y = 420 + index * 34
            c.create_text(RAIL_W + 130, y, text=question["title"], anchor="w", font=self.f_rail, fill=INK)
            c.create_text(WINDOW_W - 130, y, text=f"Arrangement {letter}", anchor="e", font=self.f_small,
                          fill=MUTED)

    # ---- behaviour -----------------------------------------------------------
    def go(self, step: int) -> None:
        if self.saved:
            return
        self.step = max(0, min(len(QUESTIONS), step))
        self.notice = ""
        self.draw()

    def select(self, question_id: str, option_id: str) -> None:
        if self.saved:
            return
        self.variables[question_id].set(option_id)
        event = {
            "seq": self.next_sequence,
            "event": "select",
            "questionId": question_id,
            "optionId": option_id,
        }
        self._append_trace(event)
        self.next_sequence += 1
        self.notice = ""
        self.draw()

    def submit(self) -> None:
        if self.saved:
            return
        if not all(variable.get() for variable in self.variables.values()):
            self.notice = "Choose one arrangement for every moment."
            self.draw()
            return

        answers = [
            {"questionId": question["id"], "optionId": self.variables[question["id"]].get()}
            for question in QUESTIONS
        ]
        event = {"seq": self.next_sequence, "event": "submit", "selectionCount": len(answers)}
        self._append_trace(event)
        self.next_sequence += 1
        self.saved = True

        payload = {
            "schemaVersion": 2,
            "contractVersion": CONTRACT_VERSION,
            "scenarioVersion": SCENARIO_VERSION,
            "optionTextDigest": OPTION_TEXT_DIGEST,
            "taskName": TASK_NAME,
            "taskDigest": TASK_DIGEST,
            "contractDigest": CONTRACT_DIGEST,
            "personaHash": PERSONA_HASH,
            "runId": self.run_id,
            "sessionId": self.session_id,
            "traceId": self.trace_id,
            "runBinding": self.run_binding,
            "traceDigest": self.trace_digest,
            "submitted": True,
            "answers": answers,
            "events": self.events,
            "uiState": {
                "submitDisabled": True,
                "status": "Forum arrangements saved.",
                "selected": answers,
            },
        }
        write_atomic(OUTPUT_DIR / "preferences.json", payload)
        self.draw()


if __name__ == "__main__":
    root = tk.Tk()
    ForumListeningApp(root)
    root.mainloop()
