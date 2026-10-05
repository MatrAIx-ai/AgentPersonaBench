#!/usr/bin/env python3
"""Harefield Press Studio - Wall planner builder. Native desktop app."""
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
ARTIFACT_NAME = "planner_order.json"
SELECTION_KEY = "order"
SITE_NAME = "Harefield Press Studio"
TAGLINE = "Wall planner builder"
INTRO = "Your wall planner for the year: choose one style in each section, then order it."
SUBMIT_TEXT = "Order planner"
CONFIRMATION = "Planner ordered - HP-2214"
# One entry per section, in display order.
CATALOG = [
    {'id': 'shifts', 'title': '1. Shifts',
     'options': [
         {'id': 'sh-1', 'name': 'Colour blocks', 'detail': 'Green for early, amber for late, red for night.', 'note': 'The Harefield standard', 'distinguishable': 'hue_only'},
         {'id': 'sh-2', 'name': 'Full-day colour', 'detail': "The whole day cell filled in the shift's colour.", 'distinguishable': 'hue_only'},
         {'id': 'sh-3', 'name': 'Letter codes', 'detail': "E, L or N in each day's corner, with the times.", 'note': 'Runs to two sheets', 'distinguishable': 'multi_cue'},
         {'id': 'sh-4', 'name': 'Brighter blocks', 'detail': 'The same three colours in a brighter palette.', 'distinguishable': 'hue_only'},
     ]},
    {'id': 'bills', 'title': '2. Bills',
     'options': [
         {'id': 'bl-1', 'name': 'Ticked list', 'detail': 'Every bill with its name and amount, and a box to tick once it is paid.', 'note': 'Adds two lines a week', 'distinguishable': 'multi_cue'},
         {'id': 'bl-2', 'name': 'Paid and due dots', 'detail': "A green dot where the day's bills are paid, a red dot where one is due.", 'note': 'Most ordered', 'distinguishable': 'hue_only'},
         {'id': 'bl-3', 'name': 'Coloured amounts', 'detail': 'The amount printed in red until the bill is paid and in green once it clears.', 'distinguishable': 'hue_only'},
     ]},
    {'id': 'school', 'title': '3. School days',
     'options': [
         {'id': 'sc-1', 'name': 'Term shading', 'detail': 'Term days shaded blue and holidays shaded green.', 'note': 'The cleanest calendar', 'distinguishable': 'hue_only'},
         {'id': 'sc-2', 'name': 'Marked holidays', 'detail': 'A diagonal hatch over every holiday, with the word Holiday on the first day.', 'note': 'Hatch prints over the dates', 'distinguishable': 'multi_cue'},
         {'id': 'sc-3', 'name': 'One shade per child', 'detail': "Each child's days out in their own shade, with a key naming the children.", 'distinguishable': 'hue_only'},
     ]},
    {'id': 'runs', 'title': '4. Training runs',
     'options': [
         {'id': 'rn-1', 'name': 'Effort colours', 'detail': 'Easy runs in green, tempo in amber, long in red.', 'note': 'Most runners order this', 'distinguishable': 'hue_only'},
         {'id': 'rn-2', 'name': 'Heat strip', 'detail': 'A strip under each week shading green to red.', 'distinguishable': 'hue_only'},
         {'id': 'rn-3', 'name': 'Coloured distance', 'detail': 'The distance printed in green, amber or red.', 'distinguishable': 'hue_only'},
         {'id': 'rn-4', 'name': 'Shapes and distance', 'detail': 'Circle for easy, square for tempo, triangle for long.', 'note': "Uses the day's note space", 'distinguishable': 'multi_cue'},
     ]},
]
# 1024x900 is the CUA framebuffer; xfwm4 takes ~24-32 px for its title bar, so the client
# area is requested at 868 px (app_env_check.py reads the literal geometry string below).
WINDOW_W, WINDOW_H = 1024, 868
# The CUA desktop is exactly 1024x900 and the window manager draws a title bar,
# so the last ~40px of a +0+0 window sit under the screen edge: keep the action
# bar above that band.
SAFE_BOTTOM = 46
# Print-studio palette: newsprint paper, black-green press ink, ruled edges.
BG, CARD, INK, MUTED = "#f3efe6", "#fffdf8", "#1d2320", "#5e6660"
PRESS, PRESS_DK, PAPER = "#1f3d36", "#152b26", "#fbf8f1"
RULE, RULE_DK, PICKED, NOTE, DISABLED = "#ddd6c7", "#2b2f2c", "#ecefe6", "#6d5a2f", "#8c948f"


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
        payload = {SELECTION_KEY: self.selected, "events": self.events, "completed": self.completed}
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
        self.marks: dict[tuple[str, str], tk.Canvas] = {}
        self.section_status: dict[str, tk.Label] = {}
        self.chips: dict[str, tk.Label] = {}
        root.title(SITE_NAME)
        root.geometry("1024x868+0+0")  # keep in sync with WINDOW_W / WINDOW_H
        root.configure(bg=BG)
        root.lift()
        try:
            root.attributes("-topmost", True)
            root.after(6000, lambda: root.attributes("-topmost", False))
        except tk.TclError:
            pass
        serif, sans = "P052", "Nimbus Sans"
        self.h1 = tkfont.Font(family=serif, size=21, weight="bold")
        self.h2 = tkfont.Font(family=serif, size=15, weight="bold")
        self.h3 = tkfont.Font(family=sans, size=12, weight="bold")
        self.name_font = tkfont.Font(family=sans, size=12, weight="bold")
        self.body = tkfont.Font(family=sans, size=10)
        self.note_font = tkfont.Font(family=sans, size=10, slant="italic")
        self.small = tkfont.Font(family=sans, size=10, weight="bold")

        # ---- masthead -------------------------------------------------------- #
        header = tk.Frame(root, bg=PRESS)
        header.pack(fill="x")
        mark = tk.Canvas(header, width=40, height=40, bg=PRESS, highlightthickness=0)
        mark.pack(side="left", padx=(22, 10), pady=8)
        mark.create_rectangle(4, 4, 36, 36, outline=PAPER, width=2)
        mark.create_text(20, 21, text="H", fill=PAPER, font=(serif, 17, "bold"))
        titles = tk.Frame(header, bg=PRESS)
        titles.pack(side="left", pady=5)
        tk.Label(titles, text=SITE_NAME, bg=PRESS, fg=PAPER, font=self.h1).pack(anchor="w")
        tk.Label(titles, text=TAGLINE, bg=PRESS, fg="#d9d3c4", font=self.body).pack(anchor="w")
        tk.Label(header, text="Household planner  ·  A2 sheet  ·  12 months", bg=PRESS_DK, fg=PAPER,
                 font=self.small, padx=14, pady=6).pack(side="right", padx=22)
        tk.Frame(root, bg=RULE_DK, height=3).pack(fill="x")
        tk.Label(root, text=INTRO, bg=BG, fg=INK, font=self.body, wraplength=WINDOW_W - 48, justify="left",
                 anchor="w").pack(fill="x", padx=24, pady=(7, 2))

        # Packed BEFORE the sections and anchored to the bottom: a tall catalog can
        # then never squeeze the submit button out of the window.
        actions = tk.Frame(root, bg=CARD, highlightthickness=1, highlightbackground=RULE)
        actions.pack(side="bottom", fill="x", padx=18, pady=(4, SAFE_BOTTOM))
        chips = tk.Frame(actions, bg=CARD)
        chips.pack(side="left", padx=(14, 8), pady=10)
        for group in CATALOG:
            chip = tk.Label(chips, text="", bg=BG, fg=MUTED, font=self.small, padx=8, pady=4,
                            highlightthickness=1, highlightbackground=RULE)
            chip.pack(side="left", padx=(0, 6))
            self.chips[group["id"]] = chip
        self.status = tk.Label(actions, text="", bg=CARD, fg=MUTED, font=self.body, anchor="w")
        self.status.pack(side="left", fill="x", expand=True)
        self.submit_button = tk.Button(actions, text=SUBMIT_TEXT, command=self.submit, bg=PRESS, fg=PAPER,
                                       activebackground=PRESS_DK, activeforeground=PAPER,
                                       disabledforeground="#b9b3a6", font=self.h3, relief="flat",
                                       padx=22, pady=8, cursor="hand2")
        self.submit_button.pack(side="right", padx=10, pady=8)

        # ---- the four sections, as a 2 x 2 order sheet ---------------------- #
        content = tk.Frame(root, bg=BG)
        content.pack(side="top", fill="both", expand=True, padx=18, pady=(2, 0))
        for column in (0, 1):
            content.grid_columnconfigure(column, weight=1, uniform="col")
        for index, group in enumerate(CATALOG):
            self._section(content, group, index // 2, index % 2)

        self.overlay = tk.Frame(root, bg=BG)
        self.overlay_text = tk.Label(self.overlay, text="", bg=BG, fg=INK, font=self.h1,
                                     wraplength=WINDOW_W - 120, justify="center")
        self._refresh()

    def _section(self, parent: "tk.Frame", group: dict, row: int, column: int) -> None:
        panel = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=RULE)
        panel.grid(row=row, column=column, sticky="nsew", padx=6, pady=4)
        head = tk.Frame(panel, bg=CARD)
        head.pack(fill="x", padx=14, pady=(7, 3))
        tk.Label(head, text=group["title"], bg=CARD, fg=INK, font=self.h2).pack(side="left")
        status = tk.Label(head, text="", bg=CARD, fg=MUTED, font=self.body)
        status.pack(side="right")
        self.section_status[group["id"]] = status
        tk.Frame(panel, bg=RULE_DK, height=2).pack(fill="x", padx=14, pady=(0, 4))
        options = group["options"]
        if group.get("prompt"):
            tk.Label(panel, text=group["prompt"], bg=CARD, fg=MUTED, font=self.body, anchor="w").pack(
                fill="x", padx=14)
        for option in options:
            key = (group["id"], option["id"])
            card = tk.Frame(panel, bg=CARD, highlightthickness=1, highlightbackground=CARD, padx=8, pady=2)
            card.pack(fill="x", padx=8, pady=1)
            mark = tk.Canvas(card, width=22, height=22, bg=CARD, highlightthickness=0)
            mark.pack(side="left", anchor="n", pady=(2, 0))
            button = tk.Button(card, text="Select", command=lambda g=group["id"], o=option["id"]: self.choose(g, o),
                               bg=CARD, fg=PRESS, activebackground=PICKED, activeforeground=PRESS,
                               font=self.small, relief="solid", bd=1, width=7, pady=4, cursor="hand2")
            button.pack(side="right", anchor="center", padx=(8, 0))
            text = tk.Frame(card, bg=CARD)
            text.pack(side="left", fill="x", expand=True, padx=(8, 0))
            tk.Label(text, text=option["name"], bg=CARD, fg=INK, font=self.name_font,
                     justify="left", anchor="w").pack(fill="x")
            tk.Label(text, text=option["detail"], bg=CARD, fg=MUTED, font=self.body, wraplength=310,
                     justify="left", anchor="w").pack(fill="x")
            if option.get("note"):
                tk.Label(text, text=option["note"], bg=CARD, fg=NOTE, font=self.note_font,
                         justify="left", anchor="w").pack(fill="x")
            for widget in (card, mark, text, *text.winfo_children()):
                widget.bind("<Button-1>", lambda _event, g=group["id"], o=option["id"]: self.choose(g, o))
            self.cards[key] = card
            self.buttons[key] = button
            self.marks[key] = mark

    def choose(self, group_id: str, option_id: str) -> None:
        if self.session.select(group_id, option_id):
            self._refresh()

    @staticmethod
    def _paint(widget: "tk.Widget", tint: str) -> None:
        for child in widget.winfo_children():
            if isinstance(child, (tk.Label, tk.Frame, tk.Canvas)):
                child.configure(bg=tint)
                App._paint(child, tint)

    def _refresh(self) -> None:
        chosen = self.session.chosen_ids()
        names = {g["id"]: {o["id"]: o["name"] for o in g["options"]} for g in CATALOG}
        for (group_id, option_id), card in self.cards.items():
            picked = chosen.get(group_id) == option_id
            tint = PICKED if picked else CARD
            card.configure(bg=tint, highlightbackground=PRESS if picked else CARD)
            self._paint(card, tint)
            mark = self.marks[(group_id, option_id)]
            mark.delete("all")
            mark.create_oval(3, 3, 19, 19, outline=PRESS if picked else "#9a9486", width=2)
            if picked:
                mark.create_oval(7, 7, 15, 15, fill=PRESS, outline=PRESS)
            self.buttons[(group_id, option_id)].configure(
                text="Selected" if picked else "Select", bg=PRESS if picked else CARD,
                fg=PAPER if picked else PRESS, activebackground=PRESS_DK if picked else PICKED,
                activeforeground=PAPER if picked else PRESS)
        for group in CATALOG:
            gid = group["id"]
            pick = chosen.get(gid)
            self.section_status[gid].configure(
                text=f"✓ {names[gid][pick]}" if pick else "Choose one", fg=INK if pick else MUTED)
            short = group["title"].split(". ", 1)[-1]
            self.chips[gid].configure(text=f"✓ {short}" if pick else f"○ {short}",
                                      fg=INK if pick else MUTED)
        total, done = len(CATALOG), len(chosen)
        ready = self.session.ready()
        self.submit_button.configure(state="normal" if ready else "disabled",
                                     bg=PRESS if ready else DISABLED)
        self.status.configure(text=(f"All {total} sections chosen." if ready else
                                    f"{done} of {total} sections chosen."))

    def submit(self) -> None:
        if not self.session.submit():
            return
        chosen = self.session.selected
        lines = "\n".join(f"{g['title'].split('. ', 1)[-1]}:  {chosen[g['id']]['name']}" for g in CATALOG)
        self.overlay_text.configure(text=CONFIRMATION)
        for child in self.overlay.winfo_children():
            if child is not self.overlay_text:
                child.destroy()
        seal = tk.Canvas(self.overlay, width=72, height=72, bg=BG, highlightthickness=0)
        seal.pack(pady=(190, 14))
        seal.create_oval(4, 4, 68, 68, fill=PRESS, outline=PRESS)
        seal.create_line(22, 37, 32, 47, 51, 26, fill=PAPER, width=5, capstyle="round", joinstyle="round")
        self.overlay_text.pack(pady=(0, 6))
        tk.Label(self.overlay, text="Your choices have been recorded.", bg=BG, fg=INK,
                 font=self.h3).pack(pady=(0, 18))
        sheet = tk.Frame(self.overlay, bg=CARD, highlightthickness=1, highlightbackground=RULE)
        sheet.pack()
        tk.Label(sheet, text=lines, bg=CARD, fg=INK, font=self.body, justify="left",
                 padx=28, pady=14).pack()
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.overlay.lift()


if __name__ == "__main__":
    if tk is None:
        raise SystemExit("tkinter is required to open the window")
    window = tk.Tk()
    App(window)
    window.mainloop()
