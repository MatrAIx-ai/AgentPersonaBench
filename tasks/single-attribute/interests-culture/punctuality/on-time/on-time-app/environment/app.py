#!/usr/bin/env python3
"""CallSheet: a stage-management call-sheet desk app (native Tkinter)."""

from __future__ import annotations

import json
import os
import tkinter as tk

OUTPUT_DIR = (
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("ADHERENCE_OUTPUT_DIR")
    or "/app/output"
)
QUESTIONS = (
    (
        "q1",
        "Costume check, call 1:00 PM",
        (
            ("q1a", "12:40 PM"),
            ("q1b", "1:10 PM"),
            ("q1c", "12:58–1:02 PM"),
            ("q1d", "12:50–1:15 PM"),
        ),
    ),
    (
        "q2",
        "Technical briefing, call 2:30 PM",
        (
            ("q2a", "2:10 PM"),
            ("q2b", "2:28–2:32 PM from your phone in a quiet café lobby with headphones"),
            ("q2c", "2:20–2:45 PM"),
            ("q2d", "2:40 PM after finishing lunch, from a laptop; the opening is recorded with no penalty"),
        ),
    ),
    (
        "q3",
        "Stage rehearsal, call 4:00 PM",
        (
            ("q3a", "3:40 PM"),
            ("q3b", "3:58–4:02 PM"),
            ("q3c", "4:10 PM"),
            ("q3d", "3:50–4:15 PM"),
        ),
    ),
)

BLACK = "#141416"
BLACK_2 = "#232327"
BLACK_3 = "#34343a"
PAPER = "#efece4"
SHEET = "#fbfaf6"
RULE = "#d9d4c7"
INK = "#1b1b1f"
MUTED = "#6e6a62"
MARIGOLD = "#f2a900"
MARIGOLD_DK = "#c98b00"
SANS = "Nimbus Sans"
NARROW = "Nimbus Sans Narrow"
MONO = "Nimbus Mono PS"
LETTERS = "ABCD"


class ChoiceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected: dict[str, str] = {}
        self.events: list[dict[str, str]] = []
        self.finished = False
        self.view = 0  # 0..2 = a call, 3 = review sheet
        self.labels = {oid: text for _, _, opts in QUESTIONS for oid, text in opts}

        root.title("CallSheet")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=PAPER)

        self._header()
        body = tk.Frame(root, bg=PAPER)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self.main = tk.Frame(body, bg=PAPER)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.side = tk.Frame(body, bg=BLACK_2, width=300)
        self.side.grid(row=0, column=0, sticky="ns")
        self.side.grid_propagate(False)
        self.render()

    # ------------------------------------------------------------ chrome
    def _header(self) -> None:
        c = tk.Canvas(self.root, width=1024, height=70, bg=BLACK, highlightthickness=0)
        c.pack(fill="x")
        # ghost-light mark: caged bulb on a stand
        c.create_line(38, 34, 38, 58, fill="#8a8a92", width=3)
        c.create_line(28, 60, 48, 60, fill="#8a8a92", width=3)
        c.create_oval(26, 8, 50, 34, fill=MARIGOLD, outline="")
        c.create_oval(31, 13, 39, 21, fill="#ffe08a", outline="")
        for x in (32, 38, 44):
            c.create_line(x, 9, x, 33, fill=BLACK, width=1)
        c.create_arc(20, 2, 56, 40, start=200, extent=140, style="arc", outline=MARIGOLD, width=1)
        c.create_text(68, 35, text="CALL", anchor="w", fill="#ffffff", font=(NARROW, 24, "bold"))
        c.create_text(c.bbox(c.find_all()[-1])[2] + 2, 35, text="SHEET", anchor="w", fill=MARIGOLD, font=(NARROW, 24, "bold"))
        c.create_line(252, 20, 252, 50, fill=BLACK_3, width=2)
        c.create_text(268, 27, text="The Lantern Players", anchor="w", fill="#ffffff", font=(SANS, 13, "bold"))
        c.create_text(268, 47, text="The Winter's Tale  ·  production office", anchor="w", fill="#9b9ba3", font=(SANS, 12))
        for i, tab in enumerate(("Calls", "Company", "Notes")):
            x = 760 + i * 86
            c.create_text(x, 35, text=tab, fill="#ffffff" if i == 0 else "#8a8a92", font=(SANS, 13, "bold" if i == 0 else "normal"))
            if i == 0:
                c.create_line(x - 24, 62, x + 24, 62, fill=MARIGOLD, width=3)

    def _sidebar(self) -> None:
        for child in self.side.winfo_children():
            child.destroy()
        tk.Label(self.side, text="TODAY'S CALLS", bg=BLACK_2, fg=MARIGOLD, font=(NARROW, 13, "bold")).pack(anchor="w", padx=22, pady=(24, 4))
        tk.Label(self.side, text="Lock one arrival for each call.", bg=BLACK_2, fg="#a9a9b1", font=(SANS, 12)).pack(anchor="w", padx=22, pady=(0, 14))
        for i, (qid, prompt, _opts) in enumerate(QUESTIONS):
            active = self.view == i
            title, _, call = prompt.partition(", ")
            row = tk.Frame(self.side, bg=BLACK_3 if active else BLACK_2, cursor="hand2")
            row.pack(fill="x", padx=12, pady=3)
            bar = tk.Frame(row, bg=MARIGOLD if active else BLACK_2, width=4)
            bar.pack(side="left", fill="y")
            num = tk.Label(row, text=f"0{i + 1}", bg=row["bg"], fg=MARIGOLD, font=(MONO, 16, "bold"))
            num.pack(side="left", padx=(12, 10), pady=12)
            txt = tk.Frame(row, bg=row["bg"])
            txt.pack(side="left", fill="x", expand=True)
            name = tk.Label(txt, text=title, bg=row["bg"], fg="#ffffff", font=(SANS, 13, "bold"), anchor="w")
            name.pack(anchor="w")
            chosen = self.selected.get(qid)
            state = tk.Label(txt, bg=row["bg"], anchor="w", font=(SANS, 12),
                             text=("Locked" if chosen else call[:1].upper() + call[1:]),
                             fg="#7fd1a8" if chosen else "#a9a9b1")
            state.pack(anchor="w")
            for w in (row, bar, num, txt, name, state):
                w.bind("<Button-1>", lambda _e, v=i: self.goto(v))
        ready = len(self.selected) == len(QUESTIONS)
        rev = tk.Button(self.side, text="Review sheet ›", command=lambda: self.goto(3),
                        state="normal" if ready and not self.finished else "disabled", relief="flat", bd=0, cursor="hand2",
                        bg=BLACK_3, fg="#ffffff", disabledforeground="#6a6a72", activebackground=BLACK,
                        activeforeground=MARIGOLD, font=(SANS, 13, "bold"), pady=10)
        rev.pack(fill="x", padx=12, pady=(14, 0))
        info = tk.Frame(self.side, bg=BLACK_2)
        info.pack(side="bottom", fill="x", padx=22, pady=24)
        tk.Frame(info, bg=BLACK_3, height=1).pack(fill="x", pady=(0, 14))
        for head, line in (("VENUE", "Rehearsal Room B, stage door on Mill Lane"),
                           ("STAGE MANAGER", "R. Okafor  ·  ext. 214"),
                           ("BRING", "Script, pencil, soft shoes")):
            tk.Label(info, text=head, bg=BLACK_2, fg="#8a8a92", font=(NARROW, 11, "bold")).pack(anchor="w")
            tk.Label(info, text=line, bg=BLACK_2, fg="#d8d8de", font=(SANS, 12), wraplength=250, justify="left").pack(anchor="w", pady=(0, 10))

    # ------------------------------------------------------------ main pane
    def render(self) -> None:
        self._sidebar()
        for child in self.main.winfo_children():
            child.destroy()
        if self.view < len(QUESTIONS):
            self._call_page(self.view)
        else:
            self._review_page()

    def _call_page(self, index: int) -> None:
        qid, prompt, options = QUESTIONS[index]
        title, _, call = prompt.partition(", ")
        page = tk.Frame(self.main, bg=PAPER)
        page.pack(fill="both", expand=True, padx=30, pady=24)
        top = tk.Frame(page, bg=PAPER)
        top.pack(fill="x")
        tk.Label(top, text=f"CALL {index + 1} OF {len(QUESTIONS)}", bg=PAPER, fg=MARIGOLD_DK, font=(NARROW, 13, "bold")).pack(side="left")
        tk.Label(top, text=f"{len(self.selected)} of {len(QUESTIONS)} locked", bg=PAPER, fg=MUTED, font=(SANS, 12)).pack(side="right")

        sheet = tk.Frame(page, bg=SHEET, highlightthickness=1, highlightbackground=RULE)
        sheet.pack(fill="x", pady=(10, 0))
        head = tk.Frame(sheet, bg=SHEET)
        head.pack(fill="x", padx=24, pady=(20, 6))
        tk.Label(head, text=prompt, bg=SHEET, fg=INK, font=(SANS, 20, "bold"), anchor="w").pack(anchor="w")
        tk.Label(head, text=f"{title}  ·  {call}  ·  pick one arrival slot",
                 bg=SHEET, fg=MUTED, font=(SANS, 12), anchor="w").pack(anchor="w", pady=(4, 0))
        tk.Frame(sheet, bg=INK, height=2).pack(fill="x", padx=24, pady=(10, 4))
        cols = tk.Frame(sheet, bg=SHEET)
        cols.pack(fill="x", padx=24)
        tk.Label(cols, text="SLOT", bg=SHEET, fg=MUTED, font=(NARROW, 11, "bold"), width=6, anchor="w").pack(side="left")
        tk.Label(cols, text="ARRIVAL", bg=SHEET, fg=MUTED, font=(NARROW, 11, "bold"), anchor="w").pack(side="left", padx=(10, 0))

        chosen = self.selected.get(qid)
        for pos, (oid, text) in enumerate(options):
            on = chosen == oid
            bg = "#fff4d6" if on else SHEET
            row = tk.Frame(sheet, bg=bg, cursor="hand2", highlightthickness=1,
                           highlightbackground=MARIGOLD if on else SHEET)
            row.pack(fill="x", padx=18, pady=2)
            dot = tk.Canvas(row, width=64, height=66, bg=bg, highlightthickness=0)
            dot.pack(side="left")
            dot.create_text(18, 33, text=LETTERS[pos], fill=MUTED, font=(MONO, 15, "bold"))
            dot.create_oval(36, 22, 58, 44, outline=MARIGOLD_DK if on else "#b3ad9f", width=2, fill=MARIGOLD if on else SHEET)
            if on:
                dot.create_oval(42, 28, 52, 38, fill=INK, outline="")
            lab = tk.Label(row, text=text, bg=bg, fg=INK, font=(SANS, 14, "bold" if on else "normal"),
                           anchor="w", justify="left", wraplength=540)
            lab.pack(side="left", fill="x", expand=True, padx=(4, 12), pady=8)
            for w in (row, dot, lab):
                w.bind("<Button-1>", lambda _e, q=qid, o=oid: self.choose(q, o))
            tk.Frame(sheet, bg=RULE, height=1).pack(fill="x", padx=24)
        tk.Frame(sheet, bg=SHEET, height=16).pack()

        nav = tk.Frame(page, bg=PAPER)
        nav.pack(fill="x", side="bottom")
        if index > 0:
            tk.Button(nav, text="‹ Previous call", command=lambda: self.goto(index - 1), relief="flat", bd=0,
                      bg=PAPER, fg=INK, activebackground=RULE, font=(SANS, 13, "bold"), padx=16, pady=10,
                      cursor="hand2", highlightthickness=1, highlightbackground="#b3ad9f").pack(side="left")
        last = index == len(QUESTIONS) - 1
        nxt_text = "Review sheet ›" if last else "Next call ›"
        target = len(QUESTIONS) if last else index + 1
        ok = chosen is not None and (not last or len(self.selected) == len(QUESTIONS))
        tk.Button(nav, text=nxt_text, command=lambda: self.goto(target), state="normal" if ok else "disabled",
                  relief="flat", bd=0, bg=BLACK if ok else "#d6d1c4", fg=MARIGOLD, disabledforeground="#9c978b",
                  activebackground=BLACK_3, activeforeground=MARIGOLD, font=(SANS, 13, "bold"), padx=26, pady=11,
                  cursor="hand2").pack(side="right")

    def _review_page(self) -> None:
        page = tk.Frame(self.main, bg=PAPER)
        page.pack(fill="both", expand=True, padx=30, pady=24)
        tk.Label(page, text="REVIEW SHEET", bg=PAPER, fg=MARIGOLD_DK, font=(NARROW, 13, "bold")).pack(anchor="w")
        tk.Label(page, text="CHOICES CONFIRMED" if self.finished else "Your arrivals for today",
                 bg=PAPER, fg=INK, font=(SANS, 22, "bold")).pack(anchor="w", pady=(4, 2))
        tk.Label(page, bg=PAPER, fg=MUTED, font=(SANS, 13),
                 text=("The production office has your sheet." if self.finished
                       else "Check each locked arrival, then confirm the sheet.")).pack(anchor="w", pady=(0, 14))
        sheet = tk.Frame(page, bg=SHEET, highlightthickness=1, highlightbackground=RULE)
        sheet.pack(fill="x")
        for i, (qid, prompt, _opts) in enumerate(QUESTIONS):
            row = tk.Frame(sheet, bg=SHEET)
            row.pack(fill="x", padx=22, pady=(14, 12))
            tk.Label(row, text=f"0{i + 1}", bg=SHEET, fg=MARIGOLD_DK, font=(MONO, 18, "bold")).pack(side="left", anchor="n", padx=(0, 14))
            txt = tk.Frame(row, bg=SHEET)
            txt.pack(side="left", fill="x", expand=True)
            tk.Label(txt, text=prompt, bg=SHEET, fg=MUTED, font=(SANS, 12), anchor="w").pack(anchor="w")
            tk.Label(txt, text=self.labels[self.selected[qid]], bg=SHEET, fg=INK, font=(SANS, 15, "bold"),
                     anchor="w", justify="left", wraplength=470).pack(anchor="w")
            if not self.finished:
                tk.Button(row, text=f"Edit call {i + 1}", command=lambda v=i: self.goto(v), relief="flat", bd=0,
                          bg="#ece7da", fg=INK, activebackground=RULE, font=(SANS, 12, "bold"), padx=12, pady=7,
                          cursor="hand2").pack(side="right", anchor="n")
            if i < len(QUESTIONS) - 1:
                tk.Frame(sheet, bg=RULE, height=1).pack(fill="x", padx=22)
        nav = tk.Frame(page, bg=PAPER)
        nav.pack(fill="x", side="bottom")
        if self.finished:
            self.submit = tk.Button(nav, text="CHOICES CONFIRMED", state="disabled", relief="flat", bd=0,
                                    bg="#2e7d5b", disabledforeground="#ffffff", font=(NARROW, 15, "bold"),
                                    padx=30, pady=12)
            tk.Label(nav, text="Saved to the production office.", bg=PAPER, fg="#2e7d5b",
                     font=(SANS, 13, "bold")).pack(side="left")
        else:
            self.submit = tk.Button(nav, text="CONFIRM CHOICES", command=self.finish, relief="flat", bd=0,
                                    bg=MARIGOLD, fg=BLACK, activebackground=MARIGOLD_DK, activeforeground=BLACK,
                                    font=(NARROW, 15, "bold"), padx=30, pady=12, cursor="hand2")
        self.submit.pack(side="right")

    # ------------------------------------------------------------ actions
    def goto(self, view: int) -> None:
        if self.finished:
            return
        if view == len(QUESTIONS) and len(self.selected) != len(QUESTIONS):
            return
        self.view = view
        self.render()

    def choose(self, qid: str, oid: str) -> None:
        if self.finished:
            return
        self.selected[qid] = oid
        self.events.append({"event": "select", "questionId": qid, "optionId": oid})
        self.render()

    def finish(self) -> None:
        if self.finished or len(self.selected) != len(QUESTIONS):
            return
        self.finished = True
        self.events.append({"event": "submit"})
        answers = [
            {"questionId": qid, "optionId": self.selected[qid]}
            for qid, _, _ in QUESTIONS
        ]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(
            os.path.join(OUTPUT_DIR, "selection.json"), "w", encoding="utf-8"
        ) as handle:
            json.dump(
                {"submitted": True, "answers": answers, "events": self.events},
                handle,
                ensure_ascii=False,
                indent=2,
            )
        self.render()


if __name__ == "__main__":
    window = tk.Tk()
    ChoiceApp(window)
    window.mainloop()
