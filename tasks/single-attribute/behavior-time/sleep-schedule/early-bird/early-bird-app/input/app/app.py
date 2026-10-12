#!/usr/bin/env python3
"""TimeChoice — native weekly routine planner for computer use."""
from __future__ import annotations

import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont

OUTPUT_DIR = os.environ.get("TIMECHOICE_OUTPUT_DIR") or "/app/output"

# Palette: electric violet chrome, lemon highlight, warm off-white paper.
VIOLET = "#4b2fd6"
VIOLET_DEEP = "#2e1a8f"
VIOLET_SOFT = "#ece8fd"
LEMON = "#ffe45c"
INK = "#16131f"
MUTED = "#6b6778"
BG = "#faf9f5"
CARD = "#ffffff"
LINE = "#e3e0ea"
GREEN = "#1d7a4c"
SANS = "Nimbus Sans"
MONO = "Nimbus Mono PS"


def _schedule_path() -> Path:
    adjacent = Path(__file__).with_name("schedule.json")
    if adjacent.is_file():
        return adjacent
    repository_copy = Path(__file__).resolve().parents[2] / "environment" / "schedule.json"
    if repository_copy.is_file():
        return repository_copy
    raise FileNotFoundError("TimeChoice schedule.json was not found")


def _load_activities() -> list[dict]:
    path = _schedule_path()
    raw = json.loads(path.read_text(encoding="utf-8"))
    activities = raw.get("activities") if isinstance(raw, dict) else None
    if not isinstance(activities, list) or not activities:
        raise ValueError(f"{path} needs a non-empty activities list")
    activity_ids = set()
    for activity in activities:
        if not isinstance(activity, dict):
            raise ValueError(f"{path} contains a malformed activity")
        activity_id = activity.get("id")
        slots = activity.get("slots")
        if not isinstance(activity_id, str) or activity_id in activity_ids:
            raise ValueError(f"{path} needs unique string activity ids")
        if not isinstance(slots, list) or not slots:
            raise ValueError(f"{path}: {activity_id!r} needs choices")
        activity_ids.add(activity_id)
        slot_ids = set()
        for slot in slots:
            slot_id = slot.get("id") if isinstance(slot, dict) else None
            if (
                not isinstance(slot_id, str)
                or slot_id in slot_ids
            ):
                raise ValueError(f"{path}: invalid slot data for {activity_id!r}")
            slot_ids.add(slot_id)
    return activities


ACTIVITIES = _load_activities()
ACTIVITY_BY_ID = {activity["id"]: activity for activity in ACTIVITIES}


class TimeChoice:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.selected: dict[str, str] = {}
        self.buttons: dict[tuple[str, str], tk.Widget] = {}
        self.tiles: dict[tuple[str, str], tuple[tk.Frame, list[tk.Widget]]] = {}
        self.summary_rows: dict[str, tk.Label] = {}
        self.row_marks: dict[str, tk.Canvas] = {}

        root.title("TimeChoice")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=BG)
        root.lift()
        # Desktop startup may open Chromium after this window. Keep TimeChoice
        # visible until its first interaction, then restore normal stacking.
        root.attributes("-topmost", True)

        startup_pending = True

        def restore_startup_focus() -> None:
            if startup_pending:
                root.focus_force()

        def startup_focus_out(event: tk.Event) -> None:
            root.after_idle(restore_startup_focus)

        def finish_startup(event: tk.Event) -> None:
            nonlocal startup_pending
            startup_pending = False
            root.attributes("-topmost", False)
            root.unbind("<ButtonPress>", pointer_binding)
            root.unbind("<KeyPress>", keyboard_binding)
            root.unbind("<FocusOut>", focus_binding)

        pointer_binding = root.bind("<ButtonPress>", finish_startup, add="+")
        keyboard_binding = root.bind("<KeyPress>", finish_startup, add="+")
        focus_binding = root.bind("<FocusOut>", startup_focus_out, add="+")
        root.after_idle(restore_startup_focus)

        self.brand = tkfont.Font(family=SANS, size=19, weight="bold")
        self.h1 = tkfont.Font(family=SANS, size=24, weight="bold")
        self.h2 = tkfont.Font(family=SANS, size=15, weight="bold")
        self.num = tkfont.Font(family=SANS, size=34, weight="bold")
        self.time_font = tkfont.Font(family=MONO, size=17, weight="bold")
        self.body_font = tkfont.Font(family=SANS, size=13)
        self.small = tkfont.Font(family=SANS, size=12)
        self.cap = tkfont.Font(family=SANS, size=12, weight="bold")

        self._header()
        footer = tk.Frame(root, bg=VIOLET_DEEP)
        footer.pack(fill="x", side="bottom")
        self._footer(footer)

        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=(18, 10))
        tk.Label(body, text="Set up your weekly routine", bg=BG, fg=INK,
                 font=self.h1).pack(anchor="w")
        tk.Label(
            body,
            text="Choose one recurring time for each activity. Within each activity, "
                 "the provider, duration, format, and price stay the same.",
            bg=BG, fg=MUTED, font=self.body_font, wraplength=968, justify="left",
        ).pack(anchor="w", pady=(4, 12))
        for index, activity in enumerate(ACTIVITIES):
            self._add_activity(body, activity, index)

    # ------------------------------------------------------------------ chrome
    def _header(self) -> None:
        bar = tk.Frame(self.root, bg=VIOLET, height=66)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        mark = tk.Canvas(bar, width=44, height=44, bg=VIOLET, highlightthickness=0)
        mark.pack(side="left", padx=(28, 10))
        # Drawn mark: a lemon tile holding a repeating loop arrow around a dot.
        mark.create_rectangle(2, 2, 42, 42, fill=LEMON, outline="")
        mark.create_arc(10, 10, 34, 34, start=110, extent=290, style="arc",
                        outline=VIOLET_DEEP, width=4)
        mark.create_polygon(12, 8, 20, 14, 11, 18, fill=VIOLET_DEEP, outline="")
        mark.create_oval(19, 19, 25, 25, fill=VIOLET_DEEP, outline="")
        tk.Label(bar, text="TimeChoice", bg=VIOLET, fg="white", font=self.brand).pack(side="left")
        tk.Label(bar, text="  ROUTINE  ", bg=VIOLET_DEEP, fg=LEMON, font=self.cap).pack(
            side="left", padx=14, ipady=2)
        for name in ("Account", "Reminders", "My week"):
            tk.Label(bar, text=name, bg=VIOLET, fg="white" if name == "My week" else "#c9c0fb",
                     font=self.cap if name == "My week" else self.small).pack(side="right", padx=14)

    def _footer(self, footer: tk.Frame) -> None:
        inner = tk.Frame(footer, bg=VIOLET_DEEP)
        inner.pack(fill="x", padx=28, pady=14)
        left = tk.Frame(inner, bg=VIOLET_DEEP)
        left.pack(side="left", fill="x", expand=True)
        self.selection_label = tk.Label(
            left, text=f"0 of {len(ACTIVITIES)} activities selected", bg=VIOLET_DEEP,
            fg=LEMON, font=self.cap,
        )
        self.selection_label.pack(anchor="w", pady=(0, 4))
        for index, activity in enumerate(ACTIVITIES):
            label = tk.Label(left, text="", bg=VIOLET_DEEP, fg="white", font=self.small, anchor="w")
            label.pack(anchor="w")
            self.summary_rows[activity["id"]] = label
            self._refresh_summary(activity["id"], index)
        self.confirm_button = tk.Button(
            inner, text="Confirm weekly schedule", bg=LEMON, fg=INK,
            disabledforeground="#8e87b8", activebackground="#fff08f", activeforeground=INK,
            font=self.h2, relief="flat", bd=0, padx=26, pady=14, state="disabled",
            cursor="hand2", command=self.confirm,
        )
        self.confirm_button.configure(bg="#4a3a9c")
        self.confirm_button.pack(side="right")

    def _refresh_summary(self, activity_id: str, index: int | None = None) -> None:
        if index is None:
            index = next(i for i, a in enumerate(ACTIVITIES) if a["id"] == activity_id)
        activity = ACTIVITY_BY_ID[activity_id]
        slot_id = self.selected.get(activity_id)
        time = next((s["time"] for s in activity["slots"] if s["id"] == slot_id), None)
        self.summary_rows[activity_id].configure(
            text=f"{index + 1:02d}  {activity['title']}  —  {time or 'not chosen yet'}",
            fg="white" if time else "#a99ff0",
        )

    # ------------------------------------------------------------------ rows
    def _add_activity(self, parent: tk.Widget, activity: dict, index: int) -> None:
        activity_id = activity["id"]
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        card.pack(fill="x", pady=7)
        num = tk.Label(card, text=f"{index + 1:02d}", bg=CARD, fg=VIOLET, font=self.num, width=3)
        num.pack(side="left", anchor="n", padx=(14, 4), pady=(14, 0))
        main = tk.Frame(card, bg=CARD)
        main.pack(side="left", fill="both", expand=True, padx=(4, 18), pady=(16, 16))
        head = tk.Frame(main, bg=CARD)
        head.pack(fill="x")
        tk.Label(head, text=activity["title"], bg=CARD, fg=INK, font=self.h2).pack(side="left")
        state = tk.Canvas(head, width=24, height=24, bg=CARD, highlightthickness=0)
        state.pack(side="right")
        self.row_marks[activity_id] = state
        self._paint_mark(activity_id)
        tk.Label(main, text=activity["detail"], bg=CARD, fg=MUTED, font=self.small).pack(
            anchor="w", pady=(2, 10))
        choices = tk.Frame(main, bg=CARD)
        choices.pack(fill="x")
        for column, slot in enumerate(activity["slots"]):
            choices.grid_columnconfigure(column, weight=1, uniform="slots")
            tile = tk.Frame(choices, bg=VIOLET_SOFT, height=64, cursor="hand2",
                            highlightthickness=2, highlightbackground=VIOLET_SOFT)
            tile.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0))
            tile.pack_propagate(False)
            time_lbl = tk.Label(tile, text=slot["time"], bg=VIOLET_SOFT, fg=VIOLET_DEEP,
                                font=self.time_font, cursor="hand2")
            time_lbl.pack(expand=True)
            parts = [tile, time_lbl]
            for widget in parts:
                widget.bind("<Button-1>",
                            lambda _e, aid=activity_id, sid=slot["id"]: self.select(aid, sid))
            self.buttons[(activity_id, slot["id"])] = tile
            self.tiles[(activity_id, slot["id"])] = (tile, parts)

    def _paint_mark(self, activity_id: str) -> None:
        mark = self.row_marks[activity_id]
        mark.delete("all")
        if activity_id in self.selected:
            mark.create_oval(1, 1, 23, 23, fill=GREEN, outline="")
            mark.create_line(7, 12, 11, 16, 17, 8, fill="white", width=2)
        else:
            mark.create_oval(2, 2, 22, 22, outline=LINE, width=2)

    def select(self, activity_id: str, slot_id: str) -> None:
        self.selected[activity_id] = slot_id
        for (candidate_activity, candidate_slot), (tile, parts) in self.tiles.items():
            if candidate_activity != activity_id:
                continue
            on = candidate_slot == slot_id
            tile.configure(bg=VIOLET if on else VIOLET_SOFT,
                           highlightbackground=LEMON if on else VIOLET_SOFT)
            parts[1].configure(bg=VIOLET if on else VIOLET_SOFT, fg="white" if on else VIOLET_DEEP)
        self._paint_mark(activity_id)
        self._refresh_summary(activity_id)
        count = len(self.selected)
        self.selection_label.configure(text=f"{count} of {len(ACTIVITIES)} activities selected")
        ready = count == len(ACTIVITIES)
        self.confirm_button.configure(state="normal" if ready else "disabled",
                                      bg=LEMON if ready else "#4a3a9c")

    def confirm(self) -> None:
        if len(self.selected) != len(ACTIVITIES):
            return
        selections = []
        for activity in ACTIVITIES:
            activity_id = activity["id"]
            slot_id = self.selected[activity_id]
            slot = next(item for item in activity["slots"] if item["id"] == slot_id)
            selections.append(
                {
                    "activityId": activity_id,
                    "activity": activity["title"],
                    "slotId": slot_id,
                    "time": slot["time"],
                }
            )
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        path = Path(OUTPUT_DIR) / "schedule.json"
        path.write_text(
            json.dumps({"selections": selections}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        overlay = tk.Frame(self.root, bg=VIOLET)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        badge = tk.Canvas(overlay, width=96, height=96, bg=VIOLET, highlightthickness=0)
        badge.place(relx=0.5, rely=0.24, anchor="center")
        badge.create_oval(4, 4, 92, 92, fill=LEMON, outline="")
        badge.create_line(28, 50, 42, 64, 70, 34, fill=VIOLET_DEEP, width=7)
        tk.Label(
            overlay, text="Weekly schedule confirmed", bg=VIOLET, fg="white", font=self.h1
        ).place(relx=0.5, rely=0.36, anchor="center")
        lines = [f'{choice["activity"]}: {choice["time"]}' for choice in selections]
        tk.Label(
            overlay, text="\n".join(lines), bg=VIOLET, fg=LEMON, font=self.h2, justify="left",
        ).place(relx=0.5, rely=0.48, anchor="center")


if __name__ == "__main__":
    window = tk.Tk()
    TimeChoice(window)
    window.mainloop()
