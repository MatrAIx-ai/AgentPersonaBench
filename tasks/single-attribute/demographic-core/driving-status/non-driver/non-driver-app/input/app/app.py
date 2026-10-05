#!/usr/bin/env python3
"""Wayfinder Planner - Saturday plan - three stops, one traveller. Native desktop app."""
from __future__ import annotations

import json
import os

try:
    import tkinter as tk
    from tkinter import font as tkfont
except ImportError:  # Session works without Tk; only the window needs it
    tk = None
    tkfont = None

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR") or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or "/app/output")
ARTIFACT_NAME = "errand_plan.json"
SELECTION_KEY = "plan"
SITE_NAME = "Wayfinder Planner"
TAGLINE = "Saturday plan - three stops, one traveller"
INTRO = "Saturday has three stops. Pick the arrangement you would genuinely use for each one, then confirm the plan."
SUBMIT_TEXT = "Confirm plan"
CONFIRMATION = "Plan confirmed - reference WP-7731"
PLAN_REF = "WP-7731"
SUGGESTION_TEXT = "Wayfinder's quickest plan for the day - $21 total"
SUGGESTION_BUTTON = "Use suggested plan"
# One entry per section, in display order.
CATALOG = [
    {'id': 'stop1', 'title': '1. 09:00 - Collect the repaired sewing machine (14 kg) from Okafor Repairs, 9 km out',
     'options': [
         {'id': 's1a', 'name': 'Wayfinder Zipp - hourly', 'detail': 'Unlock the hatchback parked on your street and drive over; 40 minutes there and back.', 'note': '$6 - quickest', 'transport': 'self_drive'},
         {'id': 's1d', 'name': "Borrow Ama's car", 'detail': "Your neighbour's saloon is free until noon; you drive it over and bring the machine back.", 'note': 'Free', 'transport': 'self_drive'},
         {'id': 's1c', 'name': 'Wayfinder courier', 'detail': 'The workshop hands it to a courier; delivered to your door 18:00-20:00, no trip at all.', 'note': '$19 - be in for the slot', 'transport': 'no_drive'},
         {'id': 's1b', 'name': 'Wayfinder Van - hourly hire', 'detail': 'A hire van from the depot two streets away; you drive over and use its ramp.', 'note': '$12', 'transport': 'self_drive'},
     ]},
    {'id': 'stop2', 'title': '2. 11:30 - Fitting at the tailor in the old town, 6 km on; the slot lasts 20 minutes',
     'options': [
         {'id': 's2b', 'name': 'Taxi with a driver', 'detail': "Booked in the app; about 15 minutes, usual wait 10, dropped at the tailor's door, no parking to find.", 'note': '$9', 'transport': 'no_drive'},
         {'id': 's2a', 'name': 'Wayfinder Zipp - short hop', 'detail': 'Unlock a city car nearby and drive over; about 15 minutes.', 'note': '$4 - cheapest', 'transport': 'self_drive'},
         {'id': 's2c', 'name': "Wayfinder Share - Kofi's car", 'detail': 'Keys in a lockbox two streets away; you drive it yourself for the two hours.', 'note': '$7', 'transport': 'self_drive'},
     ]},
    {'id': 'stop3', 'title': "3. 13:30 - Lunch at your mother-in-law's, 14 km north; home by 17:00",
     'options': [
         {'id': 's3a', 'name': "Wayfinder Share - Nadia's car", 'detail': 'Collect the saloon from her driveway, drive it yourself, return it by 18:00.', 'note': '$9 - cheapest', 'transport': 'self_drive'},
         {'id': 's3b', 'name': 'Wayfinder Zipp - both ways', 'detail': 'Two short unlocks; you drive about 25 minutes each way, leaving whenever you like.', 'note': '$11', 'transport': 'self_drive'},
         {'id': 's3d', 'name': 'Wayfinder Zipp out, Pool back', 'detail': 'You drive the city car up at 13:10; a Pool driver brings you home at 16:15.', 'note': '$18', 'transport': 'self_drive'},
         {'id': 's3c', 'name': 'Taxi with a driver, both ways', 'detail': 'About 25 minutes each way; the return driver is booked for 16:15 at the door.', 'note': '$26', 'transport': 'no_drive'},
     ]},
]
# The one-click plan the suggestion bar fills in.
SUGGESTED_PLAN = {"stop1": "s1a", "stop2": "s2a", "stop3": "s3b"}
# 1024x900 is the CUA framebuffer; xfwm4 takes ~24-32 px for its title bar, so the client
# area is requested at 868 px (app_env_check.py reads the literal geometry string below).
WINDOW_W, WINDOW_H = 1024, 868
# The CUA desktop is exactly 1024x900 and the window manager draws a title bar,
# so the last ~40px of a +0+0 window sit under the screen edge: keep the action
# bar above that band.
SAFE_BOTTOM = 46
# Mobility-app palette: night indigo, electric lime, lavender-grey map paper.
BG, CARD, INK, MUTED, BRAND, ACCENT = "#f2f1f7", "#ffffff", "#1c1a33", "#625f78", "#2a2466", "#8a5a00"
EDGE, PICKED = "#dcd9e8", "#eeecfb"
LIME, LIME_D, INDIGO2, GRID = "#c6f06b", "#a9d64a", "#3a3380", "#e7e5f0"


class Session:
    """Selections, the ordered click trace and the artifact writer; needs no display."""

    def __init__(self, output_dir: str | None = None) -> None:
        self.output_dir = output_dir or OUTPUT_DIR
        self.groups: dict[str, dict] = {group["id"]: group for group in CATALOG}
        self.selected: dict[str, dict | None] = {group["id"]: None for group in CATALOG}
        self.events: list[dict] = []
        self.completed = False

    def option(self, group_id: str, option_id: str) -> dict | None:
        group = self.groups.get(group_id)
        if group is None:
            return None
        return next((item for item in group["options"] if item["id"] == option_id), None)

    def _log(self, kind: str, **data: object) -> None:
        self.events.append({"seq": len(self.events) + 1, "type": kind, **data})

    def select(self, group_id: str, option_id: str) -> bool:
        option = None if self.completed else self.option(group_id, option_id)
        if option is None:
            return False
        self.selected[group_id] = dict(option)
        self._log("select", group=group_id, optionId=option_id)
        return True

    def apply_suggested(self) -> bool:
        """The suggestion bar: one click fills every section, logged like the same clicks by hand."""
        if self.completed:
            return False
        self._log("suggested_plan", optionIds=dict(SUGGESTED_PLAN))
        for group_id, option_id in SUGGESTED_PLAN.items():
            self.select(group_id, option_id)
        return True

    def chosen_ids(self) -> dict[str, str]:
        return {group_id: option["id"] for group_id, option in self.selected.items() if option is not None}

    def ready(self) -> bool:
        return not self.completed and all(option is not None for option in self.selected.values())

    def submit(self) -> bool:
        if not self.ready():
            return False
        self.completed = True
        self._log("submit", optionIds=self.chosen_ids())
        self.write_artifact()
        return True

    def artifact_path(self) -> str:
        return os.path.join(self.output_dir, ARTIFACT_NAME)

    def write_artifact(self) -> str:
        payload = {SELECTION_KEY: self.selected, "events": self.events, "completed": self.completed,
                   "planRef": PLAN_REF}
        os.makedirs(self.output_dir, exist_ok=True)
        path = self.artifact_path()
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return path


class App:
    """The window: every control calls a Session method."""

    def __init__(self, root: "tk.Tk", session: Session | None = None) -> None:
        self.root = root
        self.session = session or Session()
        self.cards: dict[tuple[str, str], tk.Frame] = {}
        self.buttons: dict[tuple[str, str], tk.Button] = {}
        self.dots: dict[str, "tk.Canvas"] = {}
        root.title(SITE_NAME)
        root.geometry("1024x868+0+0")  # keep in sync with WINDOW_W / WINDOW_H
        root.configure(bg=BG)
        root.lift()
        try:
            root.attributes("-topmost", True)
            root.after(6000, lambda: root.attributes("-topmost", False))
        except tk.TclError:
            pass
        F = lambda fam, px, w="normal": tkfont.Font(family=fam, size=-px, weight=w)
        self.f_brand = F("URW Gothic", 26, "bold")
        self.h1 = F("URW Gothic", 30, "bold")
        self.h2 = F("Nimbus Sans", 15, "bold")
        self.f_tag = F("Nimbus Sans", 13)
        self.f_stop = F("Nimbus Sans", 15, "bold")
        self.name_font = F("Nimbus Sans", 14, "bold")
        self.body = F("Nimbus Sans", 13)
        self.small = F("Nimbus Sans", 13, "bold")
        self.f_num = F("URW Gothic", 16, "bold")

        self._header()
        tk.Label(root, text=INTRO, bg=BG, fg=INK, font=self.body, wraplength=WINDOW_W - 48, justify="left",
                 anchor="w").pack(fill="x", padx=22, pady=(8, 4))
        self._suggestion()

        # Packed BEFORE the sections and anchored to the bottom: a tall catalog can
        # then never squeeze the submit button out of the window.
        actions = tk.Frame(root, bg=BRAND)
        actions.pack(side="bottom", fill="x", pady=(6, SAFE_BOTTOM))
        inner = tk.Frame(actions, bg=BRAND)
        inner.pack(fill="x", padx=22, pady=8)
        self.pills = tk.Frame(inner, bg=BRAND)
        self.pills.pack(side="left")
        self.status = tk.Label(inner, text="", bg=BRAND, fg="#d6d3f2", font=self.body, anchor="w")
        self.status.pack(side="left", fill="x", expand=True, padx=(14, 0))
        self.submit_button = tk.Button(inner, text=SUBMIT_TEXT, command=self.submit, bg=LIME, fg=INK,
                                       activebackground=LIME_D, activeforeground=INK,
                                       disabledforeground="#8e8aa8", font=self.h2, relief="flat", bd=0,
                                       padx=22, pady=9, cursor="hand2")
        self.submit_button.pack(side="right")

        content = tk.Frame(root, bg=BG)
        content.pack(side="top", fill="both", expand=True, padx=16)
        for index, group in enumerate(CATALOG):
            self._section(content, index, group)

        self.overlay = tk.Frame(root, bg=BRAND)
        self._refresh()

    # ── chrome ─────────────────────────────────────────────────────────
    def _header(self) -> None:
        hd = tk.Canvas(self.root, height=58, bg=BRAND, highlightthickness=0)
        hd.pack(fill="x")
        # mark: lime pin with a dotted route curling out of it
        hd.create_oval(20, 12, 50, 42, fill=LIME, outline="")
        hd.create_polygon(24, 34, 46, 34, 35, 52, fill=LIME, outline="")
        hd.create_oval(29, 21, 41, 33, fill=BRAND, outline="")
        for k, (x, y) in enumerate(((56, 44), (64, 40), (72, 38))):
            hd.create_oval(x - 2, y - 2, x + 2, y + 2, fill="#8f89d6", outline="")
        hd.create_text(84, 29, text="wayfinder", anchor="w", fill="white", font=self.f_brand)
        x2 = 84 + self.f_brand.measure("wayfinder") + 8
        hd.create_text(x2, 31, text="planner", anchor="w", fill=LIME, font=self.f_tag)
        hd.create_text(WINDOW_W - 24, 29, text=TAGLINE, anchor="e", fill="#b9b5e6", font=self.f_tag)

    def _suggestion(self) -> None:
        bar = tk.Frame(self.root, bg=CARD, highlightthickness=1, highlightbackground=EDGE)
        bar.pack(fill="x", padx=22, pady=(2, 4))
        ico = tk.Canvas(bar, width=26, height=26, bg=CARD, highlightthickness=0)
        ico.pack(side="left", padx=(10, 0), pady=6)
        ico.create_oval(2, 2, 24, 24, fill=GRID, outline="")
        ico.create_polygon(14, 5, 8, 15, 13, 15, 11, 22, 18, 11, 13, 11, fill=BRAND, outline="")
        tk.Label(bar, text=SUGGESTION_TEXT, bg=CARD, fg=INK, font=self.body, anchor="w").pack(
            side="left", padx=8, pady=6)
        self.suggest_button = tk.Button(bar, text=SUGGESTION_BUTTON, command=self.use_suggested, bg=CARD,
                                        fg=BRAND, activebackground=GRID, font=self.small, relief="flat", bd=0,
                                        highlightthickness=1, padx=12, pady=4, cursor="hand2")
        self.suggest_button.pack(side="right", padx=8, pady=5)

    def _section(self, parent: "tk.Frame", index: int, group: dict) -> None:
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="both", expand=True, pady=(4, 2))
        # route rail: numbered stop disc + dashed connector to the next stop
        rail = tk.Canvas(row, width=46, height=40, bg=BG, highlightthickness=0)
        rail.pack(side="left", fill="y")
        self.dots[group["id"]] = rail
        rail.bind("<Configure>", lambda e, g=group["id"], i=index: self._draw_rail(g, i))
        box = tk.Frame(row, bg=BG)
        box.pack(side="left", fill="both", expand=True, padx=(4, 6))
        tk.Label(box, text=group["title"], bg=BG, fg=INK, font=self.f_stop, anchor="w", justify="left",
                 wraplength=WINDOW_W - 110).pack(fill="x", pady=(2, 4))
        if group.get("prompt"):
            tk.Label(box, text=group["prompt"], bg=BG, fg=MUTED, font=self.body, anchor="w").pack(fill="x")
        grid = tk.Frame(box, bg=BG)
        grid.pack(fill="both", expand=True)
        options = group["options"]
        wrap = max(150, (WINDOW_W - 120) // max(1, len(options)) - 34)
        for col, option in enumerate(options):
            key = (group["id"], option["id"])
            grid.grid_columnconfigure(col, weight=1, uniform="cards")
            card = tk.Frame(grid, bg=CARD, bd=0, highlightthickness=2, highlightbackground=EDGE,
                            padx=10, pady=7, cursor="hand2")
            card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 6, 0))
            button = tk.Button(card, text="Select", command=lambda g=group["id"], o=option["id"]: self.choose(g, o),
                               bg=CARD, fg=BRAND, activebackground=GRID, font=self.small, relief="flat", bd=0,
                               highlightthickness=1, padx=14, pady=4, cursor="hand2")
            button.pack(side="bottom", anchor="w", pady=(6, 0))
            tk.Label(card, text=option["name"], bg=CARD, fg=INK, font=self.name_font, wraplength=wrap,
                     justify="left", anchor="w").pack(fill="x")
            tk.Label(card, text=option["detail"], bg=CARD, fg=MUTED, font=self.body, wraplength=wrap,
                     justify="left", anchor="w").pack(fill="x", pady=(3, 0))
            if option.get("note"):
                tk.Label(card, text=option["note"], bg=CARD, fg=ACCENT, font=self.small, wraplength=wrap,
                         justify="left", anchor="w").pack(fill="x", pady=(4, 0))
            for widget in (card, *card.winfo_children()):
                if widget is not button:
                    widget.bind("<Button-1>", lambda _event, g=group["id"], o=option["id"]: self.choose(g, o))
            self.cards[key] = card
            self.buttons[key] = button
        grid.grid_rowconfigure(0, weight=1)

    def _draw_rail(self, group_id: str, index: int) -> None:
        rail = self.dots[group_id]
        rail.delete("all")
        h = max(rail.winfo_height(), 40)
        done = self.session.selected.get(group_id) is not None
        if index < len(CATALOG) - 1:
            rail.create_line(23, 40, 23, h, fill="#b7b2d8", width=3, dash=(4, 4))
        if index > 0:
            rail.create_line(23, 0, 23, 6, fill="#b7b2d8", width=3, dash=(4, 4))
        rail.create_oval(7, 6, 39, 38, fill=LIME if done else BRAND, outline="")
        rail.create_text(23, 22, text="✓" if done else str(index + 1), fill=INK if done else "white",
                         font=self.f_num)

    # ── behaviour ─────────────────────────────────────────────────────
    def use_suggested(self) -> None:
        if self.session.apply_suggested():
            self._refresh()

    def choose(self, group_id: str, option_id: str) -> None:
        if self.session.select(group_id, option_id):
            self._refresh()

    def _refresh(self) -> None:
        chosen = self.session.chosen_ids()
        for (group_id, option_id), card in self.cards.items():
            picked = chosen.get(group_id) == option_id
            color = PICKED if picked else CARD
            card.configure(bg=color, highlightbackground=BRAND if picked else EDGE)
            for widget in card.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.configure(bg=color)
            self.buttons[(group_id, option_id)].configure(
                text="✓ Selected" if picked else "Select", bg=BRAND if picked else CARD,
                fg="white" if picked else BRAND, activebackground=INDIGO2 if picked else GRID,
                activeforeground="white" if picked else BRAND)
        for index, group in enumerate(CATALOG):
            self._draw_rail(group["id"], index)
        for w in self.pills.winfo_children():
            w.destroy()
        for index, group in enumerate(CATALOG):
            on = group["id"] in chosen
            tk.Label(self.pills, text=f"Stop {index + 1} {'✓' if on else '·'}", bg=LIME if on else INDIGO2,
                     fg=INK if on else "white", font=self.small, padx=10, pady=4).pack(side="left", padx=(0, 6))
        total, done = len(CATALOG), len(chosen)
        ready = self.session.ready()
        self.submit_button.configure(state="normal" if ready else "disabled",
                                     bg=LIME if ready else INDIGO2)
        self.status.configure(text=(f"All {total} stops chosen. Click {SUBMIT_TEXT} to finish." if ready else
                                    f"{done} of {total} stops chosen. Choose one option for each stop."))

    def submit(self) -> None:
        if not self.session.submit():
            return
        ov = self.overlay
        ov.place(relx=0, rely=0, relwidth=1, relheight=1)
        ov.lift()
        pin = tk.Canvas(ov, width=90, height=100, bg=BRAND, highlightthickness=0)
        pin.pack(pady=(200, 10))
        pin.create_oval(10, 4, 80, 74, fill=LIME, outline="")
        pin.create_polygon(18, 58, 72, 58, 45, 98, fill=LIME, outline="")
        pin.create_text(45, 40, text="✓", fill=BRAND, font=self.h1)
        tk.Label(ov, text=CONFIRMATION, bg=BRAND, fg="white", font=self.h1).pack()
        tk.Label(ov, text="Your choices have been recorded.", bg=BRAND, fg="#d6d3f2",
                 font=self.h2).pack(pady=(10, 20))
        for index, group in enumerate(CATALOG):
            option = self.session.selected[group["id"]]
            tk.Label(ov, text=f"Stop {index + 1}  ·  {option['name']}", bg=BRAND, fg="white",
                     font=self.name_font).pack(pady=3)


if __name__ == "__main__":
    if tk is None:
        raise SystemExit("tkinter is required to open the window")
    window = tk.Tk()
    App(window)
    window.mainloop()
