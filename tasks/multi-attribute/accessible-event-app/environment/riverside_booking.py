#!/usr/bin/env python3
"""Riverside Booking - the Riverside Hall visitor booking desktop app.

A three-step booking wizard (arrival, admission, seating) followed by a review
ticket. Submitting writes the arrangement to booking.json in the output dir.
"""
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

CATALOG = {
    "arrival": [
        {"id": "ar1", "name": "Front courtyard", "detail": "35 m from taxi point; 18 stone steps with handrail, then a level corridor.", "route": "18 steps"},
        {"id": "ar2", "name": "Riverside side entrance", "detail": "Level curb drop-off, automatic doors, and lift access all the way to the hall; about 70 m indoors.", "route": "level drop-off, automatic doors, lift"},
        {"id": "ar3", "name": "Garden path", "detail": "120 m gently sloped path, two shallow steps, then a narrow manual door.", "route": "two steps and manual door"},
    ],
    "ticket": [
        {"id": "tk2", "name": "Welcome-desk assistance", "detail": "Give your name; a staff member retrieves and scans the ticket for you.", "handling": "staff retrieves and scans by name"},
        {"id": "tk1", "name": "Mobile changing QR", "detail": "Unlock phone, open the event app, find the booking, adjust brightness, and position the changing code under the scanner.", "handling": "multi-step phone and scanner"},
        {"id": "tk3", "name": "Self-service kiosk", "detail": "Enter an eight-character code on a small touchscreen and tear off the printed stub.", "handling": "small touchscreen and tear-off stub"},
    ],
    "seating": [
        {"id": "st1", "name": "General rear benches", "detail": "Unreserved; stand in a queue for about 25 minutes, then choose a remaining bench place.", "arrangement": "25-minute standing queue; unreserved bench"},
        {"id": "st2", "name": "Standing gallery", "detail": "Stand at the rail for the program; a few backless stools may become available.", "arrangement": "standing; uncertain backless stool"},
        {"id": "st3", "name": "Reserved supported aisle seat", "detail": "Padded chair with back and arm support, direct entry without a standing queue, and adjacent equipment space.", "arrangement": "padded back and arms; direct entry; no standing queue"},
    ],
}

GROUPS = ("arrival", "ticket", "seating")
STEP_TITLES = {"arrival": "Arrival route", "ticket": "Admission handling", "seating": "Seating"}
STEP_PROMPTS = {
    "arrival": "How will you arrive at Riverside Hall?",
    "ticket": "How will you handle admission at the door?",
    "seating": "Where will you watch the program?",
}

# Riverside Hall palette: bottle green, brass, warm ivory paper.
GREEN = "#1f3d33"
GREEN_2 = "#2c5446"
BRASS = "#b8893a"
BRASS_PALE = "#f3e6c9"
IVORY = "#f7f2e7"
PAPER = "#fffdf8"
INK = "#1d2420"
MUTED = "#5d655f"
LINE = "#d9cfbb"
SEL = "#eef4ef"


class RiversideBooking:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected: dict[str, dict | None] = {g: None for g in GROUPS}
        self.events: list[dict] = []
        self.step = 0  # 0..2 = option steps, 3 = review, 4 = done
        self.submitted = False

        root.title("Riverside Booking")
        root.geometry("1024x866+0+0")
        root.minsize(1000, 820)
        root.configure(bg=IVORY)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_brand = tkfont.Font(family="C059", size=-24, weight="bold")
        self.f_display = tkfont.Font(family="C059", size=-30, weight="bold")
        self.f_h2 = tkfont.Font(family="C059", size=-21, weight="bold")
        self.f_title = tkfont.Font(family="DejaVu Sans", size=-17, weight="bold")
        self.f_body = tkfont.Font(family="DejaVu Sans", size=-14)
        self.f_small = tkfont.Font(family="DejaVu Sans", size=-13)
        self.f_bold = tkfont.Font(family="DejaVu Sans", size=-14, weight="bold")
        self.f_caps = tkfont.Font(family="DejaVu Sans", size=-12, weight="bold")

        self._build_chrome()
        self.render()

    # ---------------------------------------------------------------- chrome
    def _build_chrome(self) -> None:
        top = tk.Frame(self.root, bg=GREEN, height=64)
        top.pack(fill="x")
        top.pack_propagate(False)
        mark = tk.Canvas(top, width=40, height=40, bg=GREEN, highlightthickness=0)
        mark.pack(side="left", padx=(22, 10), pady=12)
        mark.create_oval(2, 2, 38, 38, outline=BRASS, width=2)
        for i, y in enumerate((16, 22, 28)):
            mark.create_line(9, y, 15, y - 3, 21, y, 27, y - 3, 33, y, fill=BRASS, width=2, smooth=True)
        tk.Label(top, text="Riverside Hall", bg=GREEN, fg="#fbf6ea", font=self.f_brand).pack(side="left")
        tk.Label(top, text="  Visitor Booking", bg=GREEN, fg="#c9d6cf", font=self.f_body).pack(side="left", pady=(6, 0))
        for label in ("Help", "Venue guide", "What's on"):
            tk.Label(top, text=label, bg=GREEN, fg="#dfe8e2", font=self.f_small).pack(side="right", padx=14)

        hero = tk.Frame(self.root, bg=GREEN_2)
        hero.pack(fill="x")
        left = tk.Frame(hero, bg=GREEN_2)
        left.pack(side="left", padx=26, pady=14)
        tk.Label(left, text="TONIGHT IN THE GREAT HALL", bg=GREEN_2, fg=BRASS, font=self.f_caps).pack(anchor="w")
        tk.Label(left, text="Riverside History Evening", bg=GREEN_2, fg="white", font=self.f_display).pack(anchor="w")
        tk.Label(left, text="19:00  ·  95-minute program  ·  all arrangements cost the same",
                 bg=GREEN_2, fg="#d7e2dc", font=self.f_body).pack(anchor="w", pady=(2, 0))
        stub = tk.Frame(hero, bg=BRASS_PALE, padx=16, pady=8)
        stub.pack(side="right", padx=26)
        tk.Label(stub, text="ADMIT ONE", bg=BRASS_PALE, fg=GREEN, font=self.f_caps).pack()
        tk.Label(stub, text="19:00", bg=BRASS_PALE, fg=INK, font=self.f_h2).pack()

        self.body = tk.Frame(self.root, bg=IVORY)
        self.body.pack(fill="both", expand=True)

        rail = tk.Frame(self.body, bg=PAPER, width=250, highlightthickness=1, highlightbackground=LINE)
        rail.pack(side="left", fill="y", padx=(22, 0), pady=20)
        rail.pack_propagate(False)
        tk.Label(rail, text="YOUR BOOKING", bg=PAPER, fg=MUTED, font=self.f_caps).pack(anchor="w", padx=18, pady=(18, 10))
        self.rail_rows: list[tuple[tk.Frame, tk.Label, tk.Label, tk.Label]] = []
        for i, name in enumerate([STEP_TITLES[g] for g in GROUPS] + ["Review & submit"]):
            row = tk.Frame(rail, bg=PAPER, cursor="hand2")
            row.pack(fill="x", padx=10, pady=3)
            num = tk.Label(row, text=str(i + 1), width=3, bg=LINE, fg=INK, font=self.f_bold)
            num.pack(side="left", padx=(6, 10), pady=8)
            col = tk.Frame(row, bg=PAPER)
            col.pack(side="left", fill="x", expand=True)
            title = tk.Label(col, text=name, bg=PAPER, fg=INK, font=self.f_bold, anchor="w")
            title.pack(anchor="w")
            sub = tk.Label(col, text="", bg=PAPER, fg=MUTED, font=self.f_small, anchor="w",
                           wraplength=160, justify="left")
            sub.pack(anchor="w")
            for w in (row, num, col, title, sub):
                w.bind("<Button-1>", lambda _e, s=i: self.goto(s))
            self.rail_rows.append((row, num, title, sub))
        info = tk.Frame(rail, bg=PAPER)
        info.pack(side="bottom", fill="x", padx=18, pady=18)
        tk.Frame(info, bg=LINE, height=1).pack(fill="x", pady=(0, 10))
        tk.Label(info, text="Riverside Hall", bg=PAPER, fg=INK, font=self.f_bold).pack(anchor="w")
        tk.Label(info, text="Doors open 18:30\nBox office 0161 555 0142\nCloakroom free of charge",
                 bg=PAPER, fg=MUTED, font=self.f_small, justify="left").pack(anchor="w")

        self.main = tk.Frame(self.body, bg=IVORY)
        self.main.pack(side="left", fill="both", expand=True, padx=22, pady=20)

    # ---------------------------------------------------------------- flow
    def goto(self, step: int) -> None:
        if self.submitted:
            return
        # only allow jumping to steps that are reachable
        reachable = 0
        while reachable < 3 and self.selected[GROUPS[reachable]] is not None:
            reachable += 1
        if step <= reachable:
            self.step = step
            self.render()

    def choose(self, group: str, item: dict) -> None:
        if self.submitted:
            return
        self.selected[group] = dict(item)
        self.events.append({"event": "select", "group": group, "optionId": item["id"]})
        self.render()

    def next_step(self) -> None:
        if self.step < 3 and self.selected[GROUPS[self.step]] is not None:
            self.step += 1
            self.render()

    def prev_step(self) -> None:
        if self.step > 0:
            self.step -= 1
            self.render()

    def _update_rail(self) -> None:
        for i, (row, num, title, sub) in enumerate(self.rail_rows):
            active = i == self.step
            done = (i < 3 and self.selected[GROUPS[i]] is not None) or (i == 3 and self.submitted)
            bg = SEL if active else PAPER
            for w in (row, title, sub, title.master):
                w.configure(bg=bg)
            num.configure(bg=GREEN if active else (BRASS if done else LINE),
                          fg="white" if (active or done) else INK,
                          text="✓" if done and not active else str(i + 1))
            if i < 3:
                chosen = self.selected[GROUPS[i]]
                sub.configure(text=chosen["name"] if chosen else "Not chosen yet", bg=bg)
            else:
                sub.configure(text="Submitted" if self.submitted else "Check and send", bg=bg)

    def render(self) -> None:
        for child in self.main.winfo_children():
            child.destroy()
        self._update_rail()
        if self.step < 3:
            self._render_step(GROUPS[self.step])
        elif self.submitted:
            self._render_done()
        else:
            self._render_review()

    def _button(self, parent, text, command, primary=True, enabled=True):
        bg = GREEN if primary else PAPER
        fg = "white" if primary else GREEN
        if not enabled:
            bg, fg = "#c9c6bb", "#f6f4ee"
        b = tk.Button(parent, text=text, command=command if enabled else None, bg=bg, fg=fg,
                      activebackground=GREEN_2 if primary else SEL,
                      activeforeground="white" if primary else GREEN,
                      font=self.f_bold, relief="flat", bd=0, padx=22, pady=10,
                      highlightthickness=1 if not primary else 0, highlightbackground=GREEN,
                      cursor="hand2" if enabled else "arrow",
                      state="normal" if enabled else "disabled", disabledforeground=fg)
        return b

    def _render_step(self, group: str) -> None:
        idx = GROUPS.index(group)
        tk.Label(self.main, text=f"STEP {idx + 1} OF 3  ·  {STEP_TITLES[group].upper()}",
                 bg=IVORY, fg=BRASS, font=self.f_caps).pack(anchor="w")
        tk.Label(self.main, text=STEP_PROMPTS[group], bg=IVORY, fg=INK, font=self.f_h2).pack(anchor="w", pady=(4, 2))
        tk.Label(self.main, text="Choose one option. You can come back and change it before submitting.",
                 bg=IVORY, fg=MUTED, font=self.f_body).pack(anchor="w", pady=(0, 12))

        chosen = self.selected[group]
        for pos, item in enumerate(CATALOG[group]):
            is_sel = chosen is not None and chosen["id"] == item["id"]
            card = tk.Frame(self.main, bg=SEL if is_sel else PAPER, cursor="hand2",
                            highlightthickness=2, highlightbackground=GREEN if is_sel else LINE)
            card.pack(fill="x", pady=6)
            bg = SEL if is_sel else PAPER
            badge = tk.Canvas(card, width=46, height=46, bg=bg, highlightthickness=0)
            badge.pack(side="left", padx=(16, 14), pady=16, anchor="n")
            badge.create_oval(3, 3, 43, 43, fill=GREEN if is_sel else IVORY, outline=GREEN, width=2)
            badge.create_text(23, 23, text="✓" if is_sel else "ABC"[pos],
                              fill="white" if is_sel else GREEN, font=self.f_title)
            pick = tk.Label(card, text="Selected" if is_sel else "Select", width=8, bg=GREEN if is_sel else PAPER,
                            fg="white" if is_sel else GREEN, font=self.f_bold, padx=14, pady=6,
                            highlightthickness=1, highlightbackground=GREEN)
            pick.pack(side="right", padx=16)
            text = tk.Frame(card, bg=bg)
            text.pack(side="left", fill="x", expand=True, pady=14, padx=(0, 18))
            name = tk.Label(text, text=item["name"], bg=bg, fg=INK, font=self.f_title, anchor="w")
            name.pack(anchor="w")
            detail = tk.Label(text, text=item["detail"], bg=bg, fg=MUTED, font=self.f_body,
                              anchor="w", justify="left", wraplength=430)
            detail.pack(anchor="w", pady=(4, 0))
            for w in (card, badge, text, name, detail, pick):
                w.bind("<Button-1>", lambda _e, g=group, it=item: self.choose(g, it))

        nav = tk.Frame(self.main, bg=IVORY)
        nav.pack(fill="x", side="bottom", pady=(8, 0))
        if idx > 0:
            self._button(nav, "‹ Back", self.prev_step, primary=False).pack(side="left")
        nxt = "Continue to review ›" if idx == 2 else f"Continue to {STEP_TITLES[GROUPS[idx + 1]].lower()} ›"
        self._button(nav, nxt, self.next_step, enabled=chosen is not None).pack(side="right")
        if chosen is None:
            tk.Label(nav, text="Select an option to continue.", bg=IVORY, fg=MUTED,
                     font=self.f_small).pack(side="right", padx=14)

    def _render_review(self) -> None:
        tk.Label(self.main, text="STEP 4  ·  REVIEW & SUBMIT", bg=IVORY, fg=BRASS, font=self.f_caps).pack(anchor="w")
        tk.Label(self.main, text="Check your arrangement", bg=IVORY, fg=INK, font=self.f_h2).pack(anchor="w", pady=(4, 12))
        ticket = tk.Frame(self.main, bg=PAPER, highlightthickness=1, highlightbackground=LINE)
        ticket.pack(fill="x")
        head = tk.Frame(ticket, bg=GREEN)
        head.pack(fill="x")
        tk.Label(head, text="Riverside History Evening  ·  19:00  ·  95 min", bg=GREEN, fg="white",
                 font=self.f_bold).pack(side="left", padx=18, pady=10)
        tk.Label(head, text="Great Hall", bg=GREEN, fg=BRASS_PALE, font=self.f_small).pack(side="right", padx=18)
        for group in GROUPS:
            item = self.selected[group]
            row = tk.Frame(ticket, bg=PAPER)
            row.pack(fill="x", padx=18, pady=(12, 0))
            tk.Label(row, text=STEP_TITLES[group].upper(), bg=PAPER, fg=BRASS, font=self.f_caps,
                     width=20, anchor="w").pack(side="left", anchor="n", pady=2)
            tk.Button(row, text=f"Change {STEP_TITLES[group].lower()}", bg=PAPER, fg=GREEN, relief="flat",
                      bd=0, font=self.f_small, activebackground=SEL, cursor="hand2", padx=8, pady=6,
                      highlightthickness=1, highlightbackground=LINE,
                      command=lambda s=GROUPS.index(group): self.goto(s)).pack(side="right", anchor="n")
            col = tk.Frame(row, bg=PAPER)
            col.pack(side="left", fill="x", expand=True)
            tk.Label(col, text=item["name"], bg=PAPER, fg=INK, font=self.f_title, anchor="w").pack(anchor="w")
            tk.Label(col, text=item["detail"], bg=PAPER, fg=MUTED, font=self.f_small, anchor="w",
                     justify="left", wraplength=300).pack(anchor="w")
        tk.Frame(ticket, bg=LINE, height=1).pack(fill="x", padx=18, pady=(14, 0))
        tk.Label(ticket, text="Price: same for every arrangement  ·  Pay at the venue",
                 bg=PAPER, fg=MUTED, font=self.f_small).pack(anchor="w", padx=18, pady=12)

        nav = tk.Frame(self.main, bg=IVORY)
        nav.pack(fill="x", side="bottom", pady=(8, 0))
        self._button(nav, "‹ Back", self.prev_step, primary=False).pack(side="left")
        self._button(nav, "Submit booking", self.submit_booking).pack(side="right")

    def _render_done(self) -> None:
        box = tk.Frame(self.main, bg=PAPER, highlightthickness=1, highlightbackground=LINE)
        box.pack(fill="both", expand=True)
        c = tk.Canvas(box, width=90, height=90, bg=PAPER, highlightthickness=0)
        c.pack(pady=(70, 10))
        c.create_oval(5, 5, 85, 85, fill=GREEN, outline="")
        c.create_line(28, 46, 41, 59, 63, 33, fill="white", width=6, capstyle="round", joinstyle="round")
        tk.Label(box, text="Booking submitted", bg=PAPER, fg=INK, font=self.f_display).pack()
        tk.Label(box, text="Your arrangement for the Riverside History Evening is confirmed.",
                 bg=PAPER, fg=MUTED, font=self.f_body).pack(pady=(6, 18))
        for group in GROUPS:
            tk.Label(box, text=f"{STEP_TITLES[group]}:  {self.selected[group]['name']}", bg=PAPER,
                     fg=INK, font=self.f_bold).pack(pady=2)

    def submit_booking(self) -> None:
        if self.submitted or not all(self.selected.values()):
            return
        option_ids = {group: item["id"] for group, item in self.selected.items() if item is not None}
        self.events.append({"event": "submit", "optionIds": option_ids})
        payload = {"selected": self.selected, "events": self.events, "submitted": True}
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "booking.json"), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        self.submitted = True
        self.render()


if __name__ == "__main__":
    app_root = tk.Tk()
    RiversideBooking(app_root)
    app_root.mainloop()
