#!/usr/bin/env python3
"""Lend & Return — native personal leisure-library borrowing plan.

A card-catalogue style desktop app: the library's kits are shown as index
cards in two side-by-side drawers (your first choice and a standing
fallback), and a borrowing slip at the foot of the window collects both
choices before the plan is saved. The application atomically records the
user's submitted selections. Opaque option ids are stable product identifiers.
"""
from __future__ import annotations

import json
import os
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from tkinter import messagebox

OUTPUT_DIR = Path(
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("ADHERENCE_OUTPUT_DIR")
    or "/app/output"
)

# group, opaque id, label, description, badge
CHOICES = [
    ("primary", "p18", "Pattern Pieces", "Landscape jigsaws with a sorting mat and changeable images. Setup: 2 min; activity: 30–60 min; pause on the mat.", ""),
    ("primary", "p47", "Harbor Routes", "Route-building board game with varied route cards. Quick start and setup: 5 min; play: 30–45 min; save between turns.", ""),
    ("primary", "p29", "Number Trails", "Reusable number-grid puzzles with a wipe-clean marker. Setup: 1 min; activity: 20–40 min; pause after any clue.", ""),
    ("primary", "p63", "Word Finder", "Printed word-search sheets with several themes and a reusable marker. Setup: 1 min; activity: 20–40 min; pause after any word.", ""),
    ("fallback", "f36", "Garden Commons", "Garden tile-placement board game with varied layouts. Quick start and setup: 5 min; play: 30–45 min; save between turns.", ""),
    ("fallback", "f52", "City Windows", "Streetscape jigsaws with a sorting mat and changeable pictures. Setup: 2 min; activity: 30–60 min; pause on the mat.", ""),
    ("fallback", "f81", "Logic Paths", "Reusable logic-grid puzzle cards with a wipe-clean marker. Setup: 1 min; activity: 20–40 min; pause after any clue.", ""),
    ("fallback", "f24", "Letter Paths", "Word-search sheets with many varied word lists and a reusable marker. Setup: 1 min; activity: 20–40 min; pause after any word.", ""),
]

GROUPS = [
    ("primary", "1. Choose the kit you most want to borrow"),
    ("fallback", "2. Choose a standing fallback if the first box becomes unavailable"),
]

DRAWER_TITLES = {"primary": "Drawer 1", "fallback": "Drawer 2"}

# Palette: manila catalogue drawers, oxblood ink, brass pulls, oat desk.
DESK = "#ece6da"
MANILA = "#f1e4c4"
MANILA_D = "#d9c697"
CARD = "#fffdf7"
OXBLOOD = "#7a2332"
OXBLOOD_D = "#5c1824"
INK = "#2a2320"
MUTED = "#6f655b"
RULE = "#e2d8c6"
BRASS = "#b58a3c"
BLUE_RULE = "#c9d6e3"


class LendReturn:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        # Freeze the same public catalog for rendering, confirmation and receipt.
        self.choices = tuple(CHOICES)
        self.selected: dict[str, str] = {}
        self.events: list[dict[str, object]] = []
        self.buttons: dict[str, tk.Button] = {}
        self.cards: dict[str, tk.Frame] = {}

        root.title("Lend & Return")
        root.geometry("1010x828+6+4")
        root.resizable(False, False)
        root.configure(bg=DESK)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_word = tkfont.Font(family="P052", size=23, weight="bold")
        self.f_amp = tkfont.Font(family="P052", size=23, weight="bold", slant="italic")
        self.f_tag = tkfont.Font(family="Nimbus Sans", size=12)
        self.f_nav = tkfont.Font(family="Nimbus Sans", size=12, weight="bold")
        self.h2 = tkfont.Font(family="P052", size=13, weight="bold")
        self.option_font = tkfont.Font(family="Nimbus Sans", size=14, weight="bold")
        self.body_font = tkfont.Font(family="Nimbus Sans", size=12)
        self.small_font = tkfont.Font(family="Nimbus Sans", size=12)
        self.mono = tkfont.Font(family="Nimbus Mono PS", size=12, weight="bold")
        self.btn_font = tkfont.Font(family="Nimbus Sans", size=12, weight="bold")
        self.h1 = tkfont.Font(family="P052", size=26, weight="bold")

        self._build_header()
        self._build_footer()
        body = tk.Frame(root, bg=DESK)
        body.pack(fill="both", expand=True, padx=14, pady=(8, 8))
        body.columnconfigure(0, weight=1, uniform="drawer")
        body.columnconfigure(1, weight=1, uniform="drawer")
        for column, (group, title) in enumerate(GROUPS):
            self._build_group(body, column, group, title)

    # ------------------------------------------------------------ header
    def _build_header(self) -> None:
        bar = tk.Canvas(self.root, bg=MANILA, height=76, highlightthickness=0)
        bar.pack(fill="x")
        # mark: an oxblood catalogue drawer front with brass label holder + pull
        bar.create_rectangle(18, 14, 70, 62, fill=OXBLOOD, outline="")
        bar.create_rectangle(30, 22, 58, 34, fill=CARD, outline=BRASS, width=2)
        bar.create_line(34, 28, 54, 28, fill=MUTED)
        bar.create_arc(32, 40, 56, 60, start=180, extent=180, style="arc",
                       outline=BRASS, width=3)
        bar.create_line(18, 62, 70, 62, fill=OXBLOOD_D, width=3)
        t = bar.create_text(86, 30, text="Lend", anchor="w", font=self.f_word, fill=OXBLOOD)
        x = bar.bbox(t)[2] + 7
        t = bar.create_text(x, 30, text="&", anchor="w", font=self.f_amp, fill=BRASS)
        x = bar.bbox(t)[2] + 7
        bar.create_text(x, 30, text="Return", anchor="w", font=self.f_word, fill=OXBLOOD)
        bar.create_text(88, 58, text="Leisure library  ·  Two-week personal borrowing plan",
                        anchor="w", font=self.f_tag, fill=MUTED)
        x = 990
        for label in ("Help", "My loans", "Borrowing plan"):
            tid = bar.create_text(x, 38, text=label, anchor="e", font=self.f_nav,
                                  fill=INK if label == "Borrowing plan" else MUTED)
            x0, _y0, x1, _y1 = bar.bbox(tid)
            if label == "Borrowing plan":
                bar.create_line(x0, 51, x1, 51, fill=OXBLOOD, width=3)
            x = x0 - 24
        tk.Frame(self.root, bg=MANILA_D, height=2).pack(fill="x")

        terms = tk.Frame(self.root, bg=DESK)
        terms.pack(fill="x", padx=18, pady=(10, 0))
        tk.Label(
            terms,
            text=("All kits are free, in stock and "
                  "adult-friendly, with equal pickup and two-week loan terms. Use alone or with "
                  "one other person. Quick-start cards are included; captioned game videos are "
                  "optional. All activities can be paused and resumed."),
            bg=DESK, fg=INK, font=self.small_font, anchor="w", justify="left",
            wraplength=970,
        ).pack(fill="x")
        tk.Label(
            terms,
            text="Choose a kit for yourself, then an acceptable substitute. "
                 "Use it whenever you like during the loan.",
            bg=DESK, fg=MUTED, font=self.small_font, anchor="w", justify="left",
        ).pack(fill="x", pady=(3, 0))

    # ------------------------------------------------------------ drawers
    def _build_group(self, parent: tk.Widget, column: int, group: str, title: str) -> None:
        drawer = tk.Frame(parent, bg=MANILA, highlightbackground=MANILA_D,
                          highlightthickness=1)
        drawer.grid(row=0, column=column, sticky="nsew", padx=5)
        head = tk.Frame(drawer, bg=MANILA)
        head.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(head, text=DRAWER_TITLES[group].upper(), bg=OXBLOOD, fg=CARD,
                 font=self.mono, padx=8).pack(side="left")
        tk.Label(drawer, text=title, bg=MANILA, fg=INK, font=self.h2, anchor="w",
                 justify="left", wraplength=470).pack(fill="x", padx=12, pady=(0, 6))

        for _, option_id, label, detail, badge in [
            choice for choice in self.choices if choice[0] == group
        ]:
            self._build_card(drawer, group, option_id, label, detail, badge)

    def _build_card(self, drawer, group, option_id, label, detail, badge) -> None:
        card = tk.Frame(drawer, bg=CARD, highlightbackground=RULE, highlightthickness=1)
        card.pack(fill="x", padx=12, pady=(0, 6))
        self.cards[option_id] = card
        spine = tk.Canvas(card, bg=CARD, width=44, height=10, highlightthickness=0)
        spine.pack(side="left", fill="y")
        spine.create_line(43, 0, 43, 400, fill="#e8b9b9")
        spine.create_oval(15, 36, 29, 50, fill=DESK, outline=MANILA_D)
        spine.create_text(22, 18, text=option_id[1:], font=self.mono, fill=MUTED)
        text_area = tk.Frame(card, bg=CARD)
        text_area.pack(side="left", fill="both", expand=True, padx=(10, 8), pady=(6, 6))
        title_line = tk.Frame(text_area, bg=CARD)
        title_line.pack(fill="x")
        tk.Label(title_line, text=label, bg=CARD, fg=INK, font=self.option_font,
                 anchor="w").pack(side="left")
        if badge:
            tk.Label(title_line, text=f"  {badge}  ", bg=MANILA, fg=OXBLOOD,
                     font=self.small_font).pack(side="left", padx=(8, 0))
        button = tk.Button(
            title_line,
            text="Choose",
            font=self.btn_font,
            relief="solid",
            bd=1,
            padx=14,
            pady=3,
            cursor="hand2",
            command=lambda g=group, oid=option_id: self.choose(g, oid),
        )
        button.pack(side="right")
        self.buttons[option_id] = button
        self._paint(option_id, False)
        tk.Label(text_area, text=detail, bg=CARD, fg=MUTED, font=self.small_font,
                 anchor="w", justify="left", wraplength=372).pack(fill="x", pady=(2, 0))

    def _paint(self, option_id: str, on: bool) -> None:
        self.buttons[option_id].configure(
            text="Chosen" if on else "Choose",
            bg=OXBLOOD if on else CARD, fg=CARD if on else OXBLOOD,
            activebackground=OXBLOOD_D if on else MANILA,
            activeforeground=CARD if on else OXBLOOD_D,
            highlightbackground=OXBLOOD)
        self.cards[option_id].configure(highlightbackground=OXBLOOD if on else RULE,
                                        highlightthickness=2 if on else 1)

    # ------------------------------------------------------------ slip
    def _build_footer(self) -> None:
        footer = tk.Frame(self.root, bg=CARD, highlightbackground=MANILA_D,
                          highlightthickness=1)
        footer.pack(fill="x", side="bottom", padx=19, pady=(0, 12))
        tk.Frame(footer, bg=OXBLOOD, height=4).pack(fill="x")
        inner = tk.Frame(footer, bg=CARD)
        inner.pack(fill="x", padx=14, pady=10)
        tk.Label(inner, text="BORROWING SLIP", bg=CARD, fg=OXBLOOD,
                 font=self.mono).grid(row=0, column=0, sticky="w")
        self.slip = {}
        for row, (group, caption) in enumerate((("primary", "First choice"),
                                                 ("fallback", "Standing fallback")), start=1):
            tk.Label(inner, text=caption, bg=CARD, fg=MUTED, font=self.small_font,
                     anchor="w", width=16).grid(row=row, column=0, sticky="w", pady=(4, 0))
            value = tk.Label(inner, text="—  not chosen yet", bg=CARD, fg=MUTED,
                             font=self.btn_font, anchor="w",
                             width=24)
            value.grid(row=row, column=1, sticky="w", pady=(4, 0))
            self.slip[group] = value
        self.status = tk.Label(inner, text="Choose a primary loan and a fallback",
                               bg=CARD, fg=MUTED, font=self.body_font, anchor="w")
        self.status.grid(row=0, column=1, sticky="w")
        inner.columnconfigure(2, weight=1)
        self.submit_button = tk.Button(
            inner,
            text="SAVE BORROWING PLAN",
            bg=OXBLOOD,
            fg="white",
            activebackground=OXBLOOD_D,
            activeforeground="white",
            font=self.h2,
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.submit,
        )
        self.submit_button.grid(row=0, column=3, rowspan=3, sticky="e")

    def choose(self, group: str, option_id: str) -> None:
        for _, candidate_id, *_ in [choice for choice in self.choices if choice[0] == group]:
            self._paint(candidate_id, False)
        self.selected[group] = option_id
        self.events.append({"event": "select", "group": group, "optionId": option_id})
        self._paint(option_id, True)
        labels = {option: label for _, option, label, _, _ in self.choices}
        self.slip[group].configure(text=labels[option_id], fg=INK)
        complete = len(self.selected) == len(GROUPS)
        self.status.configure(
            text="Ready to submit" if complete else "One more section needs a choice",
            fg=OXBLOOD if complete else MUTED,
        )

    def submit(self) -> None:
        missing = [group for group, _ in GROUPS if group not in self.selected]
        if missing:
            messagebox.showwarning(
                "Plan incomplete",
                "Choose one primary loan and one fallback before saving your plan.",
            )
            return

        by_group = {group: self.selected[group] for group, _ in GROUPS}
        selections = [
            {
                "group": group,
                "optionId": by_group[group],
            }
            for group, _title in GROUPS
        ]
        submitted_events = [*self.events, {"event": "submit", "selections": by_group.copy()}]
        payload = {
            "schemaVersion": 2,
            "status": "submitted",
            "catalog": [
                {"group": group, "optionId": option_id, "label": label,
                 "description": description, "badge": badge}
                for group, option_id, label, description, badge in self.choices
            ],
            "selectedOptionIds": [by_group["primary"], by_group["fallback"]],
            "byGroup": by_group,
            "selections": selections,
            "events": submitted_events,
        }
        temporary = None
        try:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            destination = OUTPUT_DIR / "loan_plan.json"
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                             dir=OUTPUT_DIR, prefix=".loan-plan-",
                                             suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        except OSError:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
            messagebox.showerror("Plan could not be saved",
                                 "The plan could not be written. Your choices are still here; please try again.")
            return
        self.events = submitted_events
        self._show_confirmation()

    def _show_confirmation(self) -> None:
        labels = {option: label for _, option, label, _, _ in self.choices}
        receipt = (f"Primary loan: {labels[self.selected['primary']]}\n"
                   f"Standing fallback: {labels[self.selected['fallback']]}")
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.configure(bg=DESK)
        slip = tk.Frame(self.root, bg=CARD, highlightbackground=MANILA_D,
                        highlightthickness=1)
        slip.place(relx=0.5, rely=0.45, anchor="center", width=520)
        tk.Frame(slip, bg=OXBLOOD, height=8).pack(fill="x")
        tk.Label(slip, text="LEND & RETURN  ·  DATE-DUE SLIP", bg=CARD, fg=OXBLOOD,
                 font=self.mono).pack(pady=(18, 6))
        tk.Label(
            slip,
            text="Borrowing plan saved",
            bg=CARD,
            fg=INK,
            font=self.h1,
        ).pack(pady=(0, 10))
        tk.Frame(slip, bg=BLUE_RULE, height=1).pack(fill="x", padx=30)
        tk.Label(
            slip,
            text=receipt + "\n\nYour fallback is used only if the first box becomes unavailable.",
            bg=CARD,
            fg=MUTED,
            font=self.body_font,
            wraplength=440,
            justify="center",
        ).pack(padx=30, pady=(14, 22))


def main() -> None:
    root = tk.Tk()
    LendReturn(root)
    root.mainloop()


if __name__ == "__main__":
    main()
