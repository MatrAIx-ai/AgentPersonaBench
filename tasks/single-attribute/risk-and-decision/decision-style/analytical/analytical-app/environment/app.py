#!/usr/bin/env python3
"""Northstar Experiment Desk native app (stdlib + Tk)."""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("ADHERENCE_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)

QUESTIONS = (
    {
        "id": "activation",
        "eyebrow": "Experiment A · onboarding",
        "title": "Early activation readout",
        "scenario": (
            "A new flow shows 4.1% higher activation. The slide omits denominators, "
            "uncertainty intervals, and segment results."
        ),
        "options": (
            ("a17", "Launch now because a four-point gain is large enough to act on."),
            ("a42", "Ask the product leads to vote and follow the majority view."),
            (
                "a68",
                "Retrieve group sizes and uncertainty intervals, then check key segments before deciding.",
            ),
            ("a91", "Choose whichever flow feels more coherent with the product vision."),
        ),
    },
    {
        "id": "pricing",
        "eyebrow": "Experiment B · pricing",
        "title": "Conflicting business outcomes",
        "scenario": (
            "Variant B raises revenue per visitor but lowers conversion. "
            "No decision rule combines those outcomes yet."
        ),
        "options": (
            ("p09", "Choose Variant B because revenue per visitor is the strongest headline."),
            (
                "p31",
                "Specify the trade-off, calculate expected contribution, and compare sensitivity cases.",
            ),
            ("p57", "Keep the familiar price because changing it feels unnecessarily disruptive."),
            ("p84", "Let the most senior commercial leader make the call."),
        ),
    },
    {
        "id": "reminders",
        "eyebrow": "Experiment C · reminders",
        "title": "Early-stopped pilot",
        "scenario": (
            "A reminder-email pilot stopped after a strong first week. "
            "The team wants to ship before the seasonal campaign."
        ),
        "options": (
            ("r14", "Ship immediately while the observed lift is strong."),
            ("r36", "Use support-team impressions to decide whether the emails seemed helpful."),
            (
                "r63",
                "Re-estimate with the stopping rule accounted for, or continue to the planned sample.",
            ),
            ("r88", "Ask the campaign owner to choose based on the deadline."),
        ),
    },
)

# Parchment + deep teal + saffron palette.
PAPER = "#f5f0e6"
PANEL = "#fffdf8"
INK = "#1d2b2f"
MUTED = "#5f6b6d"
TEAL = "#0f4c52"
TEAL_DK = "#0a3a3f"
TEAL_SOFT = "#dcebe9"
SAFFRON = "#e3a52b"
SAFFRON_SOFT = "#fbefd4"
LINE = "#e2d9c7"
LETTERS = "ABCD"
# Decorative queue metadata, seeded by card position only.
META = (("Queue #0412", "Opened 3 days ago"), ("Queue #0415", "Opened 2 days ago"),
        ("Queue #0419", "Opened yesterday"))


def pick_font(root: tk.Tk, families: tuple[str, ...], size: int, weight: str = "normal",
              slant: str = "roman") -> tkfont.Font:
    available = set(tkfont.families(root))
    family = next((f for f in families if f in available), "DejaVu Sans")
    return tkfont.Font(root=root, family=family, size=-size, weight=weight, slant=slant)


class NorthstarApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.selected: dict[str, str] = {q["id"]: "" for q in QUESTIONS}
        self.events: list[dict] = []
        self.submitted = False
        self.page = 0  # 0..2 experiments, 3 = review

        root.title("Northstar Experiment Desk")
        root.geometry("1024x866+0+0")
        root.minsize(900, 760)
        root.configure(bg=PAPER)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        sans = ("Nimbus Sans", "Liberation Sans", "DejaVu Sans")
        serif = ("P052", "C059", "Liberation Serif", "DejaVu Serif")
        mono = ("Nimbus Mono PS", "Liberation Mono", "DejaVu Sans Mono")
        self.f_brand = pick_font(root, sans, 22, "bold")
        self.f_brand_sub = pick_font(root, ("Nimbus Sans Narrow",) + sans, 16)
        self.f_nav = pick_font(root, sans, 14)
        self.f_h1 = pick_font(root, serif, 28, "bold")
        self.f_h2 = pick_font(root, serif, 20, "bold")
        self.f_eyebrow = pick_font(root, mono, 13, "bold")
        self.f_body = pick_font(root, sans, 16)
        self.f_small = pick_font(root, sans, 13)
        self.f_rail_t = pick_font(root, sans, 15, "bold")
        self.f_letter = pick_font(root, sans, 16, "bold")
        self.f_btn = pick_font(root, sans, 15, "bold")

        self._build_header()
        body = tk.Frame(root, bg=PAPER)
        body.pack(fill="both", expand=True)
        self._build_rail(body)
        self.main = tk.Frame(body, bg=PAPER)
        self.main.pack(side="left", fill="both", expand=True, padx=(22, 24), pady=18)
        self.show(0)

    # ---------- chrome ----------
    def _build_header(self) -> None:
        bar = tk.Frame(self.root, bg=TEAL, height=68)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)
        mark = tk.Canvas(bar, width=46, height=46, bg=TEAL, highlightthickness=0)
        mark.pack(side="left", padx=(22, 10))
        cx, cy, r, k = 23, 23, 20, 5
        mark.create_oval(3, 3, 43, 43, outline="#2f6d72", width=2)
        mark.create_polygon(cx, cy - r, cx + k, cy - k, cx + r, cy, cx + k, cy + k,
                            cx, cy + r, cx - k, cy + k, cx - r, cy, cx - k, cy - k,
                            fill=SAFFRON, outline="")
        mark.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill=TEAL, outline="")
        tk.Label(bar, text="NORTHSTAR", bg=TEAL, fg="white", font=self.f_brand).pack(side="left")
        tk.Label(bar, text="  Experiment Desk", bg=TEAL, fg="#bcd9d6",
                 font=self.f_brand_sub).pack(side="left", pady=(4, 0))
        avatar = tk.Canvas(bar, width=36, height=36, bg=TEAL, highlightthickness=0)
        avatar.pack(side="right", padx=(8, 22))
        avatar.create_oval(2, 2, 34, 34, fill=SAFFRON_SOFT, outline="")
        avatar.create_text(18, 18, text="PM", fill=TEAL_DK, font=self.f_small)
        for label in ("Help", "Archive", "Review queue"):
            tk.Label(bar, text=label, bg=TEAL, fg="#d7ebe9" if label != "Review queue" else "white",
                     font=self.f_nav).pack(side="right", padx=12)

    def _build_rail(self, parent: tk.Widget) -> None:
        rail = tk.Frame(parent, bg=PANEL, width=268, highlightthickness=1,
                        highlightbackground=LINE)
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)
        tk.Label(rail, text="OPEN EXPERIMENTS", bg=PANEL, fg=MUTED,
                 font=self.f_eyebrow).pack(anchor="w", padx=20, pady=(22, 10))
        self.rail_rows: list[dict] = []
        for index, question in enumerate(QUESTIONS):
            self.rail_rows.append(self._rail_row(rail, index, question["eyebrow"].split(" · ")[0],
                                                 question["title"]))
        tk.Frame(rail, bg=LINE, height=1).pack(fill="x", padx=20, pady=14)
        self.rail_rows.append(self._rail_row(rail, 3, "Final step", "Review & submit"))

        note = tk.Frame(rail, bg=SAFFRON_SOFT)
        note.pack(side="bottom", fill="x", padx=16, pady=18)
        tk.Label(note, text="Desk note", bg=SAFFRON_SOFT, fg=TEAL_DK,
                 font=self.f_rail_t).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(note, text=("There is no mandated company answer. Record the "
                             "process you would actually use."),
                 bg=SAFFRON_SOFT, fg=INK, font=self.f_small, justify="left",
                 wraplength=210).pack(anchor="w", padx=12, pady=(0, 12))

    def _rail_row(self, rail: tk.Widget, index: int, eyebrow: str, title: str) -> dict:
        row = tk.Frame(rail, bg=PANEL, cursor="hand2")
        row.pack(fill="x", padx=12, pady=3)
        accent = tk.Frame(row, bg=PANEL, width=4)
        accent.pack(side="left", fill="y")
        dot = tk.Canvas(row, width=26, height=26, bg=PANEL, highlightthickness=0)
        dot.pack(side="left", padx=(10, 8), pady=12)
        text = tk.Frame(row, bg=PANEL)
        text.pack(side="left", fill="x", expand=True, pady=8)
        e = tk.Label(text, text=eyebrow, bg=PANEL, fg=MUTED, font=self.f_small, anchor="w")
        e.pack(anchor="w")
        t = tk.Label(text, text=title, bg=PANEL, fg=INK, font=self.f_rail_t, anchor="w",
                     justify="left", wraplength=180)
        t.pack(anchor="w")
        s = tk.Label(text, text="", bg=PANEL, fg=MUTED, font=self.f_small, anchor="w")
        s.pack(anchor="w")
        widgets = (row, accent, dot, text, e, t, s)
        for w in widgets:
            w.bind("<Button-1>", lambda _e, i=index: self.show(i))
        return {"row": row, "accent": accent, "dot": dot, "status": s,
                "bgs": (row, dot, text, e, t, s)}

    def _refresh_rail(self) -> None:
        for index, info in enumerate(self.rail_rows):
            active = index == self.page
            bg = TEAL_SOFT if active else PANEL
            for w in info["bgs"]:
                w.configure(bg=bg)
            info["accent"].configure(bg=TEAL if active else bg)
            dot = info["dot"]
            dot.delete("all")
            if index < 3:
                done = bool(self.selected[QUESTIONS[index]["id"]])
                if done:
                    dot.create_oval(3, 3, 23, 23, fill=TEAL, outline="")
                    dot.create_line(8, 13, 12, 17, 18, 9, fill="white", width=2)
                else:
                    dot.create_oval(3, 3, 23, 23, outline=MUTED, width=2)
                    dot.create_text(13, 13, text=LETTERS[index], fill=MUTED, font=self.f_small)
                info["status"].configure(text="Next step chosen" if done else "Awaiting next step")
            else:
                count = sum(bool(v) for v in self.selected.values())
                dot.create_rectangle(4, 4, 22, 22, outline=SAFFRON, width=2)
                if self.submitted:
                    dot.create_line(8, 13, 12, 17, 18, 9, fill=SAFFRON, width=2)
                info["status"].configure(
                    text="Submitted" if self.submitted else f"{count} of 3 steps chosen")

    # ---------- pages ----------
    def show(self, page: int) -> None:
        self.page = page
        for child in self.main.winfo_children():
            child.destroy()
        if page < 3:
            self._experiment_page(page)
        else:
            self._review_page()
        self._refresh_rail()

    def _experiment_page(self, index: int) -> None:
        question = QUESTIONS[index]
        top = tk.Frame(self.main, bg=PAPER)
        top.pack(fill="x")
        tk.Label(top, text=question["eyebrow"].upper(), bg=PAPER, fg=TEAL,
                 font=self.f_eyebrow).pack(side="left")
        tk.Label(top, text=f"{META[index][0]}  ·  {META[index][1]}", bg=PAPER, fg=MUTED,
                 font=self.f_small).pack(side="right")
        tk.Label(self.main, text=question["title"], bg=PAPER, fg=INK,
                 font=self.f_h1).pack(anchor="w", pady=(6, 12))

        brief = tk.Frame(self.main, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
        brief.pack(fill="x")
        tk.Frame(brief, bg=SAFFRON, width=6).pack(side="left", fill="y")
        inner = tk.Frame(brief, bg=PANEL)
        inner.pack(side="left", fill="x", expand=True, padx=16, pady=12)
        tk.Label(inner, text="Situation", bg=PANEL, fg=MUTED, font=self.f_small).pack(anchor="w")
        tk.Label(inner, text=question["scenario"], bg=PANEL, fg=INK, font=self.f_body,
                 justify="left", wraplength=640).pack(anchor="w", pady=(2, 0))

        tk.Label(self.main, text="What is your next step?", bg=PAPER, fg=INK,
                 font=self.f_h2).pack(anchor="w", pady=(20, 4))
        tk.Label(self.main, text="Select one option. You can change it until the review is submitted.",
                 bg=PAPER, fg=MUTED, font=self.f_small).pack(anchor="w", pady=(0, 10))

        for pos, (option_id, text) in enumerate(question["options"]):
            self._option_tile(question["id"], pos, option_id, text)

        nav = tk.Frame(self.main, bg=PAPER)
        nav.pack(fill="x", side="bottom", pady=(8, 0))
        if index > 0:
            self._button(nav, "‹  Previous experiment", lambda: self.show(index - 1),
                         primary=False).pack(side="left")
        nxt = "Next experiment  ›" if index < 2 else "Go to review  ›"
        self._button(nav, nxt, lambda: self.show(index + 1), primary=True).pack(side="right")

    def _option_tile(self, qid: str, pos: int, option_id: str, text: str) -> None:
        chosen = self.selected[qid] == option_id
        bg = TEAL_SOFT if chosen else PANEL
        border = TEAL if chosen else LINE
        tile = tk.Frame(self.main, bg=bg, highlightthickness=2 if chosen else 1,
                        highlightbackground=border, cursor="hand2")
        tile.pack(fill="x", pady=5)
        badge = tk.Canvas(tile, width=40, height=40, bg=bg, highlightthickness=0)
        badge.pack(side="left", padx=(14, 12), pady=14)
        badge.create_oval(2, 2, 38, 38, fill=TEAL if chosen else PAPER,
                          outline=TEAL if chosen else LINE, width=2)
        badge.create_text(20, 20, text=LETTERS[pos], fill="white" if chosen else TEAL,
                          font=self.f_letter)
        label = tk.Label(tile, text=text, bg=bg, fg=INK, font=self.f_body, justify="left",
                         anchor="w", wraplength=520)
        label.pack(side="left", fill="x", expand=True, pady=14)
        radio = tk.Canvas(tile, width=30, height=30, bg=bg, highlightthickness=0)
        radio.pack(side="right", padx=16)
        radio.create_oval(4, 4, 26, 26, outline=TEAL if chosen else MUTED, width=2)
        if chosen:
            radio.create_oval(10, 10, 20, 20, fill=TEAL, outline="")
        if not self.submitted:
            for w in (tile, badge, label, radio):
                w.bind("<Button-1>", lambda _e, q=qid, o=option_id: self.select(q, o))

    def _review_page(self) -> None:
        tk.Label(self.main, text="FINAL STEP", bg=PAPER, fg=TEAL,
                 font=self.f_eyebrow).pack(anchor="w")
        tk.Label(self.main, text="Review your next steps", bg=PAPER, fg=INK,
                 font=self.f_h1).pack(anchor="w", pady=(6, 14))
        for index, question in enumerate(QUESTIONS):
            chosen = self.selected[question["id"]]
            text = dict(question["options"]).get(chosen, "")
            card = tk.Frame(self.main, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            card.pack(fill="x", pady=6)
            head = tk.Frame(card, bg=PANEL)
            head.pack(fill="x", padx=16, pady=(12, 0))
            tk.Label(head, text=question["eyebrow"], bg=PANEL, fg=MUTED,
                     font=self.f_small).pack(side="left")
            if not self.submitted:
                self._button(head, f"Change step {LETTERS[index]}", lambda i=index: self.show(i),
                             primary=False, small=True).pack(side="right")
            tk.Label(card, text=question["title"], bg=PANEL, fg=INK,
                     font=self.f_rail_t).pack(anchor="w", padx=16, pady=(2, 4))
            if chosen:
                letter = LETTERS[[o for o, _ in question["options"]].index(chosen)]
                tk.Label(card, text=f"{letter}.  {text}", bg=PANEL, fg=TEAL_DK, font=self.f_body,
                         justify="left", wraplength=640).pack(anchor="w", padx=16, pady=(0, 14))
            else:
                tk.Label(card, text="No next step chosen yet.", bg=PANEL, fg="#a4521f",
                         font=self.f_body).pack(anchor="w", padx=16, pady=(0, 14))

        foot = tk.Frame(self.main, bg=PAPER)
        foot.pack(fill="x", side="bottom", pady=(8, 0))
        self.status = tk.Label(foot, text="", bg=PAPER, fg=MUTED, font=self.f_body)
        self.status.pack(side="left")
        if self.submitted:
            self.status.configure(text="Review submitted. Thank you.", fg=TEAL)
        else:
            count = sum(bool(v) for v in self.selected.values())
            self.status.configure(text=f"{count} of 3 steps chosen.")
            self._button(foot, "Submit review", self.submit, primary=True,
                         accent=True).pack(side="right")

    def _button(self, parent, text, command, primary=True, small=False, accent=False):
        bg = SAFFRON if accent else (TEAL if primary else PANEL)
        fg = INK if accent else ("white" if primary else TEAL)
        btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                        activebackground=TEAL_DK if primary and not accent else SAFFRON_SOFT,
                        activeforeground="white" if primary and not accent else INK,
                        font=self.f_small if small else self.f_btn, relief="flat",
                        bd=0, highlightthickness=1, highlightbackground=TEAL if not primary else bg,
                        padx=12 if small else 20, pady=5 if small else 10, cursor="hand2")
        return btn

    # ---------- actions ----------
    def select(self, question_id: str, option_id: str) -> None:
        if self.submitted:
            return
        self.events.append({"event": "select", "questionId": question_id, "optionId": option_id})
        self.selected[question_id] = option_id
        self.root.after_idle(lambda: self.show(self.page))

    def submit(self) -> None:
        if self.submitted:
            return
        if not all(self.selected.values()):
            missing = [LETTERS[i] for i, q in enumerate(QUESTIONS) if not self.selected[q["id"]]]
            self.status.configure(text=f"Choose a next step for experiment {', '.join(missing)}.",
                                  fg="#a4521f")
            return
        answers = [{"questionId": q["id"], "optionId": self.selected[q["id"]]} for q in QUESTIONS]
        self.events.append({"event": "submit"})
        payload = {"submitted": True, "answers": answers, "events": self.events}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        temporary = os.path.join(OUTPUT_DIR, "review.json.tmp")
        destination = os.path.join(OUTPUT_DIR, "review.json")
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, destination)
        self.submitted = True
        self.show(3)


if __name__ == "__main__":
    root = tk.Tk()
    NorthstarApp(root)
    root.mainloop()
