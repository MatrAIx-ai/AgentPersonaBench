#!/usr/bin/env python3
"""CommuteChoice — native annual commuter-benefits enrollment.

The application presents two enrollment sections and atomically records the
user's submitted selections. Opaque option ids are stable product identifiers.
Layout: a plum brand header, a left "Your enrollment" rail that tracks both
sections and holds the submit action, and two sections of option cards.
"""
from __future__ import annotations

import json
import os
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
    (
        "benefit",
        "b12",
        "Parking account",
        "$120/month for entry at participating office-area garages.",
        "",
    ),
    (
        "benefit",
        "b44",
        "Bike program",
        "$120/month for secure lockers and eligible maintenance costs.",
        "",
    ),
    (
        "benefit",
        "b37",
        "Bus and rail pass",
        "$120/month for local bus, subway, and commuter-rail fares.",
        "",
    ),
    (
        "benefit",
        "b25",
        "Shared-ride wallet",
        "$120/month for eligible carpools and shared rides to the office.",
        "",
    ),
    (
        "support",
        "s18",
        "Pickup coordination",
        "Priority shared-ride matching plus a backup pickup after a cancellation.",
        "",
    ),
    (
        "support",
        "s23",
        "Service alerts and guaranteed ride home",
        "Disruption alerts plus an emergency ride home when scheduled service stops.",
        "",
    ),
    (
        "support",
        "s31",
        "Parking availability alerts",
        "Space forecasts plus access to a backup garage when the first is full.",
        "",
    ),
    (
        "support",
        "s46",
        "Locker status and repair network",
        "Secure bike-locker access plus on-call puncture and repair assistance.",
        "",
    ),
]

GROUPS = [
    ("benefit", "1. Choose your primary commuter benefit"),
    ("support", "2. Choose one included supporting service (no cost)"),
]
RAIL_NAMES = {"benefit": "Primary benefit", "support": "Supporting service"}

# Palette: aubergine plum + peach on warm linen.
PLUM = "#3b2448"
PLUM_2 = "#523463"
PLUM_SOFT = "#efe6f2"
PEACH = "#f2a97e"
PEACH_SOFT = "#fbe9dd"
LINEN = "#f7f3ee"
PAPER = "#ffffff"
LINE = "#e3dad2"
INK = "#241b2b"
MUTED = "#6e6475"
FAINT = "#a79fae"

WIN_W, WIN_H = 1000, 820
RAIL_W = 292


class CommuteChoice:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected: dict[str, str] = {}
        self.events: list[dict[str, object]] = []
        self.buttons: dict[str, tk.Button] = {}
        self.cards: dict[str, tk.Frame] = {}
        self.rail_values: dict[str, tk.Label] = {}
        self.rail_dots: dict[str, tk.Canvas] = {}

        root.title("CommuteChoice Benefits")
        root.geometry(f"{WIN_W}x{WIN_H}+6+6")
        root.resizable(False, False)
        root.configure(bg=LINEN)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_word = tkfont.Font(family="Liberation Serif", size=-30, weight="bold")
        self.f_word_i = tkfont.Font(family="Liberation Serif", size=-30, weight="bold",
                                    slant="italic")
        self.h1 = tkfont.Font(family="Liberation Sans", size=-26, weight="bold")
        self.h2 = tkfont.Font(family="Liberation Sans", size=-17, weight="bold")
        self.option_font = tkfont.Font(family="Liberation Sans", size=-16, weight="bold")
        self.body_font = tkfont.Font(family="Liberation Sans", size=-14)
        self.small_font = tkfont.Font(family="Liberation Sans", size=-13)
        self.caps_font = tkfont.Font(family="Liberation Sans Narrow", size=-14, weight="bold")
        self.btn_font = tkfont.Font(family="Liberation Sans", size=-15, weight="bold")

        self._build_header()
        main = tk.Frame(root, bg=LINEN)
        main.pack(fill="both", expand=True)
        self._build_rail(main)
        body = tk.Frame(main, bg=LINEN)
        body.pack(side="left", fill="both", expand=True, padx=(18, 18), pady=(12, 10))
        for index, (group, title) in enumerate(GROUPS):
            self._build_group(body, group, title, index)

    # ------------------------------------------------------------------ header
    def _build_header(self) -> None:
        header = tk.Canvas(self.root, width=WIN_W, height=92, bg=PLUM, highlightthickness=0)
        header.pack(fill="x")
        # soft diagonal bands
        for i in range(6):
            x = 560 + i * 80
            header.create_polygon(x, 0, x + 46, 0, x - 34, 92, x - 80, 92, fill=PLUM_2, outline="")
        # mark: two paths forking from one point into a ring
        cx, cy = 50, 46
        header.create_oval(cx - 28, cy - 28, cx + 28, cy + 28, fill=PEACH, outline="")
        header.create_line(cx - 14, cy + 14, cx - 2, cy + 2, width=5, fill=PLUM, capstyle="round")
        header.create_line(cx - 2, cy + 2, cx - 2, cy - 14, width=5, fill=PLUM, capstyle="round")
        header.create_line(cx - 2, cy + 2, cx + 13, cy - 9, width=5, fill=PLUM, capstyle="round")
        header.create_oval(cx - 7, cy - 21, cx + 3, cy - 11, fill=PLUM, outline="")
        header.create_oval(cx + 9, cy - 16, cx + 19, cy - 6, fill=PAPER, outline="")
        header.create_text(92, 38, text="Commute", anchor="w", font=self.f_word, fill=PAPER)
        wx = 92 + self.f_word.measure("Commute")
        header.create_text(wx, 38, text="Choice", anchor="w", font=self.f_word_i, fill=PEACH)
        header.create_text(94, 68, text="Annual commuter-benefits enrollment  ·  Upcoming plan year",
                           anchor="w", font=self.small_font, fill="#d9c9e0")
        # right-side inert chips
        for i, label in enumerate(("Help", "Benefits home")):
            w = self.small_font.measure(label) + 28
            x1 = WIN_W - 22 - i * 150
            header.create_rectangle(x1 - w, 30, x1, 60, outline="#8c6f9c", width=1)
            header.create_text(x1 - w / 2, 45, text=label, font=self.small_font, fill="#eadff0")

    # -------------------------------------------------------------------- rail
    def _build_rail(self, parent: tk.Widget) -> None:
        rail = tk.Frame(parent, bg=PAPER, width=RAIL_W, highlightbackground=LINE,
                        highlightthickness=1)
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)
        tk.Label(rail, text="YOUR ENROLLMENT", bg=PAPER, fg=PLUM, font=self.caps_font,
                 anchor="w").pack(fill="x", padx=22, pady=(20, 2))
        tk.Label(rail, text="Upcoming plan year", bg=PAPER, fg=MUTED, font=self.small_font,
                 anchor="w").pack(fill="x", padx=22)

        steps = tk.Frame(rail, bg=PAPER)
        steps.pack(fill="x", padx=22, pady=(16, 0))
        for index, (group, _title) in enumerate(GROUPS):
            row = tk.Frame(steps, bg=PAPER)
            row.pack(fill="x", pady=(0, 14))
            dot = tk.Canvas(row, width=30, height=30, bg=PAPER, highlightthickness=0)
            dot.pack(side="left", anchor="n")
            self.rail_dots[group] = dot
            text = tk.Frame(row, bg=PAPER)
            text.pack(side="left", fill="x", expand=True, padx=(10, 0))
            tk.Label(text, text=RAIL_NAMES[group], bg=PAPER, fg=INK, font=self.option_font,
                     anchor="w").pack(fill="x")
            value = tk.Label(text, text="Not chosen yet", bg=PAPER, fg=FAINT,
                             font=self.small_font, anchor="w", justify="left", wraplength=210)
            value.pack(fill="x")
            self.rail_values[group] = value
            self._draw_dot(group, index)

        info = tk.Frame(rail, bg=PLUM_SOFT)
        info.pack(fill="x", padx=18, pady=(6, 0))
        tk.Label(info, text="EVERY PROGRAM", bg=PLUM_SOFT, fg=PLUM, font=self.caps_font,
                 anchor="w").pack(fill="x", padx=14, pady=(12, 4))
        for line in ("Same $120 monthly employer contribution",
                     "Fully covers your regular office commute",
                     "No payroll deduction or out-of-pocket cost",
                     "Supporting services included at no cost"):
            tk.Label(info, text="•  " + line, bg=PLUM_SOFT, fg=INK, font=self.small_font,
                     anchor="w", justify="left", wraplength=218).pack(fill="x", padx=14, pady=1)
        tk.Frame(info, bg=PLUM_SOFT, height=10).pack(fill="x")

        help_box = tk.Frame(rail, bg=PAPER)
        help_box.pack(fill="x", padx=22, pady=(18, 0))
        tk.Label(help_box, text="QUESTIONS?", bg=PAPER, fg=PLUM, font=self.caps_font,
                 anchor="w").pack(fill="x")
        tk.Label(help_box, text="Benefits desk · ext. 4410\nChanges allowed at the next open "
                 "enrollment or after a qualifying life event.", bg=PAPER, fg=MUTED,
                 font=self.small_font, anchor="w", justify="left",
                 wraplength=240).pack(fill="x", pady=(2, 0))

        bottom = tk.Frame(rail, bg=PAPER)
        bottom.pack(side="bottom", fill="x", padx=18, pady=(0, 20))
        self.status = tk.Label(bottom, text="Complete both sections before submitting",
                               bg=PAPER, fg=MUTED, font=self.small_font, anchor="w",
                               justify="left", wraplength=250)
        self.status.pack(fill="x", pady=(0, 10))
        self.submit_button = tk.Button(
            bottom,
            text="Review and submit",
            bg=PLUM,
            fg=PAPER,
            activebackground=PLUM_2,
            activeforeground=PAPER,
            font=self.btn_font,
            relief="flat",
            bd=0,
            highlightthickness=0,
            pady=12,
            cursor="hand2",
            command=self.submit,
        )
        self.submit_button.pack(fill="x")

    def _draw_dot(self, group: str, index: int) -> None:
        dot = self.rail_dots[group]
        dot.delete("all")
        if group in self.selected:
            dot.create_oval(2, 2, 28, 28, fill=PEACH, outline="")
            dot.create_line(9, 15, 13, 20, 21, 10, width=3, fill=PLUM, capstyle="round",
                            joinstyle="round")
        else:
            dot.create_oval(2, 2, 28, 28, fill=PAPER, outline=FAINT, width=2)
            dot.create_text(15, 15, text=str(index + 1), font=self.caps_font, fill=MUTED)

    # ------------------------------------------------------------------ groups
    def _build_group(self, parent: tk.Widget, group: str, title: str, index: int) -> None:
        box = tk.Frame(parent, bg=LINEN)
        box.pack(fill="x", pady=(0 if index == 0 else 10, 0))
        head = tk.Frame(box, bg=LINEN)
        head.pack(fill="x", pady=(0, 8))
        tk.Label(head, text=title, bg=LINEN, fg=INK, font=self.h2, anchor="w").pack(side="left")
        tk.Label(head, text="choose one", bg=LINEN, fg=MUTED, font=self.small_font).pack(
            side="right")
        grid = tk.Frame(box, bg=LINEN)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1, uniform="c")
        grid.columnconfigure(1, weight=1, uniform="c")
        options = [choice for choice in CHOICES if choice[0] == group]
        for position, (_, option_id, label, detail, _badge) in enumerate(options):
            card = tk.Frame(grid, bg=PAPER, highlightbackground=LINE, highlightthickness=2,
                            height=140)
            card.grid(row=position // 2, column=position % 2, sticky="nsew",
                      padx=(0 if position % 2 == 0 else 7, 7 if position % 2 == 0 else 0),
                      pady=(0, 12))
            card.grid_propagate(False)
            card.pack_propagate(False)
            self.cards[option_id] = card
            tk.Label(card, text=label, bg=PAPER, fg=INK, font=self.option_font, anchor="w",
                     justify="left", wraplength=280).pack(fill="x", padx=16, pady=(12, 0))
            tk.Label(card, text=detail, bg=PAPER, fg=MUTED, font=self.small_font, anchor="w",
                     justify="left", wraplength=280).pack(fill="x", padx=16, pady=(3, 0))
            chip = tk.Label(card, text="Option " + "ABCD"[position], bg=PEACH_SOFT, fg=PLUM,
                            font=self.caps_font, padx=8, pady=2)
            chip.place(x=16, rely=1.0, y=-17, anchor="sw")
            button = tk.Button(
                card,
                text="Choose",
                bg=PAPER,
                fg=PLUM,
                activebackground=PLUM_SOFT,
                activeforeground=PLUM,
                font=self.btn_font,
                relief="solid",
                bd=1,
                highlightthickness=0,
                padx=18,
                pady=4,
                cursor="hand2",
                command=lambda g=group, oid=option_id: self.choose(g, oid),
            )
            button.place(relx=1.0, rely=1.0, x=-14, y=-12, anchor="se")
            self.buttons[option_id] = button

    # ----------------------------------------------------------------- actions
    def choose(self, group: str, option_id: str) -> None:
        for _, candidate_id, *_ in [choice for choice in CHOICES if choice[0] == group]:
            self.buttons[candidate_id].configure(text="Choose", bg=PAPER, fg=PLUM,
                                                 activebackground=PLUM_SOFT,
                                                 activeforeground=PLUM)
            self.cards[candidate_id].configure(highlightbackground=LINE)
        self.selected[group] = option_id
        self.events.append({"event": "select", "group": group, "optionId": option_id})
        self.buttons[option_id].configure(text="Chosen", bg=PLUM, fg=PAPER,
                                          activebackground=PLUM_2, activeforeground=PAPER)
        self.cards[option_id].configure(highlightbackground=PLUM)
        label = next(choice[2] for choice in CHOICES if choice[1] == option_id)
        self.rail_values[group].configure(text=label, fg=PLUM)
        self._draw_dot(group, [g for g, _ in GROUPS].index(group))
        complete = len(self.selected) == len(GROUPS)
        self.status.configure(
            text="Ready to submit" if complete else "One more section needs a choice",
            fg=PLUM if complete else MUTED,
        )

    def submit(self) -> None:
        missing = [group for group, _ in GROUPS if group not in self.selected]
        if missing:
            messagebox.showwarning(
                "Enrollment incomplete",
                "Choose one primary benefit and one supporting service before submitting.",
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
        self.events.append({"event": "submit", "selections": by_group.copy()})
        payload = {
            "schemaVersion": 1,
            "status": "submitted",
            "selectedOptionIds": [by_group["benefit"], by_group["support"]],
            "byGroup": by_group,
            "selections": selections,
            "events": self.events,
        }
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        destination = OUTPUT_DIR / "benefit_enrollment.json"
        temporary = OUTPUT_DIR / ".benefit_enrollment.json.tmp"
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, destination)
        self._show_confirmation(by_group)

    def _show_confirmation(self, by_group: dict[str, str]) -> None:
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.configure(bg=PLUM)
        panel = tk.Frame(self.root, bg=PAPER, padx=40, pady=32)
        panel.place(relx=0.5, rely=0.45, anchor="center")
        mark = tk.Canvas(panel, width=64, height=64, bg=PAPER, highlightthickness=0)
        mark.pack()
        mark.create_oval(2, 2, 62, 62, fill=PEACH, outline="")
        mark.create_line(18, 33, 28, 44, 46, 22, width=5, fill=PLUM, capstyle="round",
                         joinstyle="round")
        tk.Label(panel, text="Enrollment submitted", bg=PAPER, fg=INK,
                 font=self.h1).pack(pady=(12, 6))
        tk.Label(
            panel,
            text="Your commuter-benefits selections have been saved for the upcoming plan year.",
            bg=PAPER,
            fg=MUTED,
            font=self.body_font,
            wraplength=480,
            justify="center",
        ).pack(pady=(0, 14))
        for group, _title in GROUPS:
            label = next(choice[2] for choice in CHOICES if choice[1] == by_group[group])
            row = tk.Frame(panel, bg=PLUM_SOFT)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=RAIL_NAMES[group].upper(), bg=PLUM_SOFT, fg=PLUM,
                     font=self.caps_font, width=22, anchor="w").pack(side="left", padx=12,
                                                                     pady=8)
            tk.Label(row, text=label, bg=PLUM_SOFT, fg=INK, font=self.option_font,
                     anchor="w").pack(side="left", padx=(0, 12))


def main() -> None:
    root = tk.Tk()
    CommuteChoice(root)
    root.mainloop()


if __name__ == "__main__":
    main()
