#!/usr/bin/env python3
"""GuidePicker — a native Tkinter team-docs app for client onboarding lessons.

A genuine desktop application. Every guide covers the same workflow with equal factual coverage, accuracy and owner workload.
Browse the lesson table, add two lessons with their + buttons, and tap "Save lessons"
— the app then writes the result to lessons.json in the output directory.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 guidepicker.py
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# (id, category, name, description, note)
MENU = [
    ("gp01", "Workspace setup", "Workspace untouched until next week's studio + one optional reader note", "leave the reviewed outline idle for seven days; then hold delivery 48 hours for one trusted-reader note and reserve a 20-minute owner reconciliation pass, even if no note arrives", "same workflow, factual coverage and accuracy; review logistics differ"),
    ("gp02", "Workspace setup", "Workspace untouched until next week's studio + consolidated committee rewrite", "leave the reviewed outline idle for seven days; then the review coordinator returns one same-day integrated revision with no owner reconciliation pass", "same workflow, factual coverage and accuracy; review logistics differ"),
    ("gp03", "Review cycle", "Reviews opening captured today + consolidated committee rewrite", "use 25 free minutes while client context is fresh, then finish next week; the review coordinator returns one same-day integrated revision with no owner reconciliation pass", "same workflow, factual coverage and accuracy; review logistics differ"),
    ("gp04", "Review cycle", "Reviews opening captured today + one optional reader note", "use 25 free minutes while client context is fresh, then finish next week; hold delivery 48 hours for one trusted-reader note and reserve a 20-minute owner reconciliation pass, even if no note arrives", "same workflow, factual coverage and accuracy; review logistics differ"),
    ("gp05", "Handoff flow", "Handoff opening captured today + consolidated committee rewrite", "use 25 free minutes while client context is fresh, then finish next week; the review coordinator returns one same-day integrated revision with no owner reconciliation pass", "same workflow, factual coverage and accuracy; review logistics differ"),
    ("gp06", "Handoff flow", "Handoff opening captured today + one optional reader note", "use 25 free minutes while client context is fresh, then finish next week; hold delivery 48 hours for one trusted-reader note and reserve a 20-minute owner reconciliation pass, even if no note arrives", "same workflow, factual coverage and accuracy; review logistics differ"),
    ("gp07", "Launch check", "Launch untouched until next week's studio + consolidated committee rewrite", "leave the reviewed outline idle for seven days; then the review coordinator returns one same-day integrated revision with no owner reconciliation pass", "same workflow, factual coverage and accuracy; review logistics differ"),
    ("gp08", "Launch check", "Launch untouched until next week's studio + one optional reader note", "leave the reviewed outline idle for seven days; then hold delivery 48 hours for one trusted-reader note and reserve a 20-minute owner reconciliation pass, even if no note arrives", "same workflow, factual coverage and accuracy; review logistics differ"),
]
_BY_ID = {m[0]: m for m in MENU}
CAP = 2

# Palette: warm-white doc page, graphite text, indigo accent.
SIDE, SIDE_HOVER, PAGE, INK, MUT, FAINT = "#f4f3ef", "#e9e7e0", "#ffffff", "#27272a", "#71717a", "#e7e5e0"
ACC, ACC_DK, ACC_BG, GROUP_BG = "#4338ca", "#3730a3", "#eef0ff", "#faf9f6"


def _font(families, size, weight="normal", slant="roman"):
    have = set(tkfont.families())
    fam = next((f for f in families if f in have), "DejaVu Sans")
    return tkfont.Font(family=fam, size=size, weight=weight, slant=slant)


class GuidePicker:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cart: list[str] = []
        self.hit: dict[str, tk.Widget] = {}
        self.rows: dict[str, tuple] = {}
        root.title("GuidePicker")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=PAGE)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))
        sans = ("DejaVu Sans", "Liberation Sans")
        serif = ("Liberation Serif", "Nimbus Roman", "DejaVu Serif")
        self.f_title = _font(serif, 24, "bold")
        self.f_side = _font(sans, 11)
        self.f_side_b = _font(sans, 11, "bold")
        self.f_name = _font(sans, 10, "bold")
        self.f_desc = _font(sans, 9)
        self.f_head = _font(sans, 9, "bold")
        self.f_ui = _font(sans, 11, "bold")
        self.f_small = _font(sans, 10)
        self.f_plus = _font(sans, 15, "bold")

        self._sidebar()
        self._page()
        self.done = tk.Frame(root, bg=PAGE)
        self._refresh()

    # --------------------------------------------------------------- sidebar
    def _sidebar(self):
        s = tk.Frame(self.root, bg=SIDE)
        s.place(x=0, y=0, width=196, height=866)
        tk.Frame(s, bg=FAINT, width=1).place(x=195, y=0, height=866)
        logo = tk.Canvas(s, width=28, height=28, bg=SIDE, highlightthickness=0)
        logo.place(x=16, y=18)
        logo.create_rectangle(2, 2, 26, 26, fill=ACC, outline="")
        logo.create_text(14, 14, text="G", fill="white", font=self.f_ui)
        tk.Label(s, text="GuidePicker", bg=SIDE, fg=INK, font=self.f_side_b).place(x=52, y=21)
        tk.Label(s, text="Studio workspace", bg=SIDE, fg=MUT, font=self.f_small).place(x=18, y=60)
        items = [("Home", False), ("Inbox", False), ("Client onboarding", True),
                 ("Style guide", False), ("Templates", False)]
        for i, (label, active) in enumerate(items):
            bg = SIDE_HOVER if active else SIDE
            f = tk.Frame(s, bg=bg)
            f.place(x=8, y=96 + i * 34, width=180, height=30)
            tk.Label(f, text=("▸  " if active else "    ") + label, bg=bg,
                     fg=INK if active else MUT,
                     font=self.f_side_b if active else self.f_side).place(x=6, y=5)
        tk.Label(s, text="ONBOARDING PLAN", bg=SIDE, fg=MUT, font=self.f_head).place(x=18, y=292)
        self.side_slots = []
        for n in range(CAP):
            lbl = tk.Label(s, text="", bg=SIDE, fg=MUT, font=self.f_small, justify="left",
                           wraplength=164, anchor="nw")
            lbl.place(x=18, y=316 + n * 92, width=170)
            self.side_slots.append(lbl)
        tk.Label(s, text="Edited just now", bg=SIDE, fg=MUT, font=self.f_small).place(x=18, y=826)

    # ------------------------------------------------------------------ page
    def _page(self):
        p = tk.Frame(self.root, bg=PAGE)
        p.place(x=196, y=0, width=828, height=866)
        tk.Label(p, text="Client onboarding  /  Lessons", bg=PAGE, fg=MUT,
                 font=self.f_small).place(x=28, y=14)
        tk.Label(p, text="Choose two client lessons", bg=PAGE, fg=INK,
                 font=self.f_title).place(x=26, y=36)
        call = tk.Frame(p, bg=GROUP_BG, highlightthickness=1, highlightbackground=FAINT)
        call.place(x=28, y=80, width=772, height=28)
        tk.Label(call, text="ℹ  Every lesson: same workflow, factual coverage and accuracy; "
                            "review logistics differ.", bg=GROUP_BG, fg=MUT,
                 font=self.f_small).place(x=10, y=4)
        # table header
        cols = tk.Frame(p, bg=PAGE)
        cols.place(x=28, y=112, width=772, height=24)
        tk.Label(cols, text="LESSON", bg=PAGE, fg=MUT, font=self.f_head).place(x=8, y=4)
        tk.Label(cols, text="WHAT HAPPENS", bg=PAGE, fg=MUT, font=self.f_head).place(x=298, y=4)
        tk.Label(cols, text="ADD", bg=PAGE, fg=MUT, font=self.f_head).place(x=744, y=4, anchor="n")
        tk.Frame(p, bg=FAINT, height=1).place(x=28, y=136, width=772)
        groups: list[str] = []
        for m in MENU:
            if m[1] not in groups:
                groups.append(m[1])
        y = 139
        for group in groups:
            gh = tk.Frame(p, bg=GROUP_BG)
            gh.place(x=28, y=y, width=772, height=24)
            tk.Label(gh, text=f"▾  {group}", bg=GROUP_BG, fg=INK, font=self.f_head).place(x=8, y=4)
            tk.Label(gh, text="2", bg=GROUP_BG, fg=MUT, font=self.f_head).place(x=764, y=4, anchor="ne")
            y += 26
            for m in [m for m in MENU if m[1] == group]:
                self._row(p, m, y)
                y += 68
        # bottom action bar
        bar = tk.Frame(p, bg=PAGE)
        bar.place(x=0, y=790, width=828, height=76)
        tk.Frame(bar, bg=FAINT, height=1).place(x=0, y=0, relwidth=1)
        self.cart_lbl = tk.Label(bar, text="Selected · 0 of 2", bg=PAGE, fg=INK, font=self.f_ui)
        self.cart_lbl.place(x=28, y=14)
        self.msg = tk.Label(bar, text="Tap + on two lessons, then save.", bg=PAGE, fg=MUT,
                            font=self.f_small)
        self.msg.place(x=28, y=40)
        self.place_btn = tk.Button(bar, text="Save lessons", font=self.f_ui, bg=ACC, fg="white",
                                   activebackground=ACC_DK, activeforeground="white",
                                   disabledforeground="#c7c9e8", relief="flat", bd=0,
                                   cursor="hand2", command=self.place_order)
        self.place_btn.place(x=800, y=38, anchor="e", width=170, height=46)
        self.hit["save"] = self.place_btn

    def _row(self, parent, m, y):
        mid, name, desc = m[0], m[2], m[3]
        r = tk.Frame(parent, bg=PAGE)
        r.place(x=28, y=y, width=772, height=67)
        name_lbl = tk.Label(r, text=name, bg=PAGE, fg=INK, font=self.f_name, justify="left",
                            wraplength=276, anchor="nw")
        name_lbl.place(x=8, y=4, width=284)
        desc_lbl = tk.Label(r, text=desc, bg=PAGE, fg=MUT, font=self.f_desc, justify="left",
                            wraplength=410, anchor="nw")
        desc_lbl.place(x=298, y=4, width=418)
        btn = tk.Button(r, text="+", font=self.f_plus, bg=PAGE, fg=ACC, activebackground=ACC_BG,
                        activeforeground=ACC_DK, relief="flat", bd=0, highlightthickness=1,
                        highlightbackground="#c7c9e8", cursor="hand2",
                        command=lambda: self._toggle(mid))
        btn.place(x=744, y=33, anchor="center", width=38, height=38)
        tk.Frame(r, bg=FAINT, height=1).place(x=0, y=66, relwidth=1)
        self.hit[mid] = btn
        self.rows[mid] = (r, name_lbl, desc_lbl, btn)

    # ----------------------------------------------------------------- state
    def _refresh(self):
        for mid, (r, name_lbl, desc_lbl, btn) in self.rows.items():
            on = mid in self.cart
            bg = ACC_BG if on else PAGE
            for w in (r, name_lbl, desc_lbl):
                w.configure(bg=bg)
            btn.configure(text="✓" if on else "+", bg=ACC if on else PAGE,
                          fg="white" if on else ACC, activebackground=ACC_DK if on else ACC_BG,
                          activeforeground="white" if on else ACC_DK)
        for n, lbl in enumerate(self.side_slots):
            if n < len(self.cart):
                lbl.configure(text=f"{n + 1}.  {_BY_ID[self.cart[n]][2]}", fg=INK)
            else:
                lbl.configure(text=f"{n + 1}.  Empty slot", fg=MUT)
        n = len(self.cart)
        self.cart_lbl.configure(text=f"Selected · {n} of 2")
        self.place_btn.configure(state="normal" if n == CAP else "disabled",
                                 bg=ACC if n == CAP else "#a5a8d8")

    def _toggle(self, mid, btn=None):
        # Tapping again removes the item — a misclick is correctable.
        if mid in self.cart:
            self.cart.remove(mid)
            self.msg.configure(text="Removed. Tap + to add a lesson.", fg=MUT)
        else:
            if len(self.cart) >= CAP:
                self.msg.configure(text="The plan holds two lessons — tap ✓ on one to remove it first.",
                                   fg="#b91c1c")
                return
            self.cart.append(mid)
            self.msg.configure(text="Tap ✓ again to remove a lesson.", fg=MUT)
        self._refresh()

    def place_order(self):
        if len(self.cart) != 2:
            self.cart_lbl.configure(text="Select exactly 2 options before saving")
            return
        chosen = [{"id": mid, "name": _BY_ID[mid][2]} for mid in self.cart]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "lessons.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "hf-1557002195"),
                       "savedLessons": chosen}, f, ensure_ascii=False, indent=2)
        self._show_done(chosen)

    def _show_done(self, chosen):
        d = self.done
        d.place(x=196, y=0, width=828, height=866)
        tk.Label(d, text="Client onboarding  /  Lessons", bg=PAGE, fg=MUT,
                 font=self.f_small).place(x=28, y=14)
        badge = tk.Frame(d, bg=ACC_BG)
        badge.place(x=28, y=60, width=772, height=64)
        tk.Label(badge, text="✓  Lessons saved", bg=ACC_BG, fg=ACC_DK,
                 font=self.f_title).place(x=16, y=12)
        tk.Label(d, text="ONBOARDING PLAN", bg=PAGE, fg=MUT, font=self.f_head).place(x=28, y=150)
        for i, row in enumerate(chosen):
            y = 176 + i * 90
            tk.Label(d, text=f"{i + 1}", bg=ACC, fg="white", font=self.f_ui, width=2).place(x=28, y=y)
            tk.Label(d, text=row["name"], bg=PAGE, fg=INK, font=self.f_ui, wraplength=700,
                     justify="left").place(x=64, y=y)
            tk.Label(d, text=_BY_ID[row["id"]][3], bg=PAGE, fg=MUT, font=self.f_desc,
                     wraplength=700, justify="left").place(x=64, y=y + 26)


if __name__ == "__main__":
    root = tk.Tk()
    GuidePicker(root)
    root.mainloop()
