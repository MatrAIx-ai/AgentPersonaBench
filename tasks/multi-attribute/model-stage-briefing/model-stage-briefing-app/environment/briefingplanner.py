#!/usr/bin/env python3
"""BriefingPlanner — a native Tkinter community-budget work planner.

A genuine desktop application (native windows, buttons, panels). Every package uses the
same reviewed dataset, policy constraints, accessibility support and decision date.
Read the eight work packages on the planning board, tap "+ Reserve" on two, and tap
"Reserve packages" — the app then writes the result to briefing_plan.json in the
output directory.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 briefingplanner.py
"""
from __future__ import annotations

import hashlib
import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# (id, category, name, description, note)
MENU = [
    ("bp06", "Library hours", "Library evidence matrix — written memo", "remote moderated session with pre-approved criteria; the facilitator maintains the criteria and captures rationale and dissent in an audit-ready record; asynchronous memo with 48 hours to revise", "same reviewed evidence, policy review and decision date"),
    ("bp01", "Library hours", "Library allocation model — live forum", "three hours at the on-site model bench to reconcile source rows and derive the model, followed by personal ownership of its assumptions and two sensitivity checks through six monthly updates; 6:30 p.m. rehearsal plus public questions", "same reviewed evidence, policy review and decision date"),
    ("bp07", "Street trees", "Tree-service optimization — recorded brief", "three hours at the on-site model bench to reconcile source rows and derive the model, followed by personal ownership of its assumptions and two sensitivity checks through six monthly updates; recorded narration with no live questions", "same reviewed evidence, policy review and decision date"),
    ("bp03", "Street trees", "Tree evidence matrix — live forum", "remote moderated review with pre-approved criteria; the facilitator maintains the criteria and captures rationale and dissent in an audit-ready record; present live and handle audience questions", "same reviewed evidence, policy review and decision date"),
    ("bp08", "Bus shelters", "Bus evidence matrix — recorded brief", "remote moderated review with pre-approved criteria; the facilitator maintains the criteria and captures rationale and dissent in an audit-ready record; recorded narration with no live questions", "same reviewed evidence, policy review and decision date"),
    ("bp04", "Bus shelters", "Bus-shelter allocation model — live forum", "three hours at the on-site model bench to reconcile source rows and derive the model, followed by personal ownership of its assumptions and two sensitivity checks through six monthly updates; present live with questions", "same reviewed evidence, policy review and decision date"),
    ("bp02", "Youth grants", "Youth-grant evidence matrix — live forum", "remote moderated session with pre-approved criteria; the facilitator maintains the criteria and captures rationale and dissent in an audit-ready record; 6:30 p.m. rehearsal plus public questions", "same reviewed evidence, policy review and decision date"),
    ("bp05", "Youth grants", "Youth-grant allocation model — written memo", "three hours at the on-site model bench to reconcile source rows and derive the model, followed by personal ownership of its assumptions and two sensitivity checks through six monthly updates; asynchronous memo with 48 hours to revise", "same reviewed evidence, policy review and decision date"),
]
_BY_ID = {m[0]: m for m in MENU}
PICKS = 2

# Municipal slate + bronze: slate chrome, cool-grey desk, white work cards.
SLATE, SLATE_2, BRONZE, BRONZE_DK = "#26303b", "#34404d", "#c1803c", "#9c6427"
DESK, CARD, INK, MUTED, EDGE, SOFT = "#e9ecef", "#ffffff", "#1c232b", "#5b6773", "#cdd3d9", "#f6f1ea"


def _split(name: str) -> tuple[str, str]:
    head, _sep, tail = name.partition(" — ")
    return head, tail


class BriefingPlanner:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cart: list[str] = []
        self.add_btns: dict[str, tk.Button] = {}
        self.cards: dict[str, tk.Frame] = {}
        root.title("BriefingPlanner")
        root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
        root.configure(bg=DESK)
        try:
            root.attributes("-zoomed", True)   # maximize on X11
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        F = tkfont.Font
        self.f_logo = F(family="Liberation Sans Narrow", size=-26, weight="bold")
        self.f_sub = F(family="Liberation Sans", size=-12)
        self.f_chip = F(family="Liberation Sans Narrow", size=-13, weight="bold")
        self.f_title = F(family="Liberation Sans Narrow", size=-18, weight="bold")
        self.f_fmt = F(family="Liberation Sans", size=-12, weight="bold")
        self.f_body = F(family="Liberation Sans", size=-13)
        self.f_note = F(family="Liberation Sans", size=-12, slant="italic")
        self.f_mono = F(family="Liberation Mono", size=-12)
        self.f_btn = F(family="Liberation Sans", size=-13, weight="bold")
        self.f_h = F(family="Liberation Sans Narrow", size=-17, weight="bold")
        self.f_big = F(family="Liberation Sans Narrow", size=-42, weight="bold")

        self._header()
        body = tk.Frame(root, bg=DESK)
        body.pack(fill="both", expand=True)
        self.side = tk.Frame(body, bg=SLATE, width=246)
        self.side.pack(side="right", fill="y")
        self.side.pack_propagate(False)
        board = tk.Frame(body, bg=DESK)
        board.pack(side="left", fill="both", expand=True, padx=12, pady=(8, 10))
        tk.Label(board, text="Planning board · 8 work packages · reserve the two you would lead",
                 bg=DESK, fg=MUTED, font=self.f_sub, anchor="w").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 4))
        board.columnconfigure(0, weight=1, uniform="c")
        board.columnconfigure(1, weight=1, uniform="c")
        for i, m in enumerate(MENU):
            self._card(board, 1 + i // 2, i % 2, m)
            board.rowconfigure(1 + i // 2, weight=1)
        self._sidebar()
        self.done = tk.Frame(root, bg=DESK)
        self._refresh()

    # ── chrome ────────────────────────────────────────────────────────────
    def _header(self):
        h = tk.Canvas(self.root, height=62, bg=SLATE, highlightthickness=0)
        h.pack(fill="x")
        # clipboard-calendar mark
        h.create_rectangle(16, 12, 50, 52, fill=BRONZE, outline="")
        h.create_rectangle(25, 8, 41, 16, fill=SOFT, outline="")
        for r in range(3):
            for c in range(3):
                x, y = 21 + c * 9, 22 + r * 9
                h.create_rectangle(x, y, x + 6, y + 6, fill=SLATE if (r, c) != (1, 1) else SOFT,
                                   outline="")
        h.create_text(62, 24, text="BriefingPlanner", anchor="w", fill="#ffffff", font=self.f_logo)
        h.create_text(63, 47, text="Neighborhood budget forum · analysis & briefing rota",
                      anchor="w", fill="#aab5c1", font=self.f_sub)
        # step tracker
        x = 1008
        for i, step in reversed(list(enumerate(("Read packages", "Reserve two", "Confirm"), 1))):
            w = self.f_sub.measure(step) + 40
            h.create_oval(x - w, 22, x - w + 20, 42, fill=BRONZE if i == 1 else SLATE_2,
                          outline="")
            h.create_text(x - w + 10, 32, text=str(i), fill="#ffffff", font=self.f_chip)
            h.create_text(x - w + 26, 32, text=step, anchor="w", fill="#dfe5ea", font=self.f_sub)
            x -= w + 6
        h.create_rectangle(0, 59, 2000, 62, fill=BRONZE, outline="")

    def _card(self, board, r, col, m):
        mid, group, name, desc, note = m
        title, fmt = _split(name)
        c = tk.Frame(board, bg=CARD, highlightthickness=2, highlightbackground=EDGE)
        c.grid(row=r, column=col, sticky="nsew", padx=4, pady=4)
        self.cards[mid] = c
        inner = tk.Frame(c, bg=CARD)
        inner.pack(fill="both", expand=True, padx=12, pady=8)
        top = tk.Frame(inner, bg=CARD)
        top.pack(fill="x")
        tk.Label(top, text=group.upper(), bg=SOFT, fg=BRONZE_DK, font=self.f_chip,
                 padx=6).pack(side="left")
        tk.Label(top, text=f"FORMAT  ·  {fmt}", bg=CARD, fg=SLATE_2, font=self.f_fmt,
                 anchor="e").pack(side="right")
        tl = tk.Label(inner, text=title, bg=CARD, fg=INK, font=self.f_title, anchor="w",
                      justify="left")
        tl.pack(fill="x", pady=(3, 0))
        dl = tk.Label(inner, text=desc, bg=CARD, fg="#39434d", font=self.f_body, anchor="nw",
                      justify="left", wraplength=330)
        dl.pack(fill="x", pady=(3, 0))
        dl.bind("<Configure>", lambda e: dl.configure(wraplength=max(160, e.width - 2)))
        foot = tk.Frame(inner, bg=CARD)
        foot.pack(side="bottom", fill="x")
        tk.Label(foot, text=note, bg=CARD, fg=MUTED, font=self.f_note, anchor="w",
                 justify="left", wraplength=200).pack(side="left")
        b = tk.Button(foot, text="+ Reserve", font=self.f_btn, relief="flat", bd=0,
                      highlightthickness=0, padx=12, pady=5, cursor="hand2",
                      command=lambda: self._toggle(mid))
        b.pack(side="right")
        self.add_btns[mid] = b

    def _sidebar(self):
        s = self.side
        tk.Label(s, text="YOUR ROTA", bg=SLATE, fg=BRONZE, font=self.f_h,
                 anchor="w").pack(fill="x", padx=16, pady=(18, 0))
        self.count_lbl = tk.Label(s, text="", bg=SLATE, fg="#dfe5ea", font=self.f_sub, anchor="w")
        self.count_lbl.pack(fill="x", padx=16, pady=(0, 10))
        self.slots = []
        for i in range(PICKS):
            fr = tk.Frame(s, bg=SLATE_2)
            fr.pack(fill="x", padx=14, pady=5)
            tk.Frame(fr, bg=BRONZE, width=4).pack(side="left", fill="y")
            box = tk.Frame(fr, bg=SLATE_2)
            box.pack(side="left", fill="both", expand=True, padx=10, pady=8)
            head = tk.Frame(box, bg=SLATE_2)
            head.pack(fill="x")
            tk.Label(head, text=f"PACKAGE {i + 1}", bg=SLATE_2, fg="#aab5c1",
                     font=self.f_chip).pack(side="left")
            rm = tk.Button(head, text="Remove", font=self.f_note, relief="flat", bd=0,
                           highlightthickness=0, bg=SLATE_2, fg="#f0c38e",
                           activebackground=SLATE_2, activeforeground="#ffffff",
                           cursor="hand2", command=lambda i=i: self._remove_slot(i))
            name = tk.Label(box, text="", bg=SLATE_2, fg="#ffffff", font=self.f_btn,
                            anchor="w", justify="left", wraplength=180)
            name.pack(fill="x", pady=(2, 0))
            self.slots.append((name, rm))
        self.notice = tk.Label(s, text="", bg=SLATE, fg="#f0c38e", font=self.f_note,
                               anchor="w", justify="left", wraplength=210)
        self.notice.pack(fill="x", padx=16, pady=(6, 2))
        self.place_btn = tk.Button(s, text="Reserve packages", font=self.f_h, relief="flat",
                                   bd=0, highlightthickness=0, bg=BRONZE, fg="#ffffff",
                                   activebackground=BRONZE_DK, activeforeground="#ffffff",
                                   pady=9, cursor="hand2", command=self.place_order)
        self.place_btn.pack(fill="x", padx=14, pady=(4, 16))
        tk.Frame(s, bg=SLATE_2, height=1).pack(fill="x", padx=14)
        tk.Label(s, text="FORUM DESK", bg=SLATE, fg="#aab5c1", font=self.f_chip,
                 anchor="w").pack(fill="x", padx=16, pady=(12, 2))
        for line in ("Each package covers one budget topic,",
                     "from analysis through the briefing.",
                     "Reservations are shared with the",
                     "forum coordinator once confirmed."):
            tk.Label(s, text=line, bg=SLATE, fg="#dfe5ea", font=self.f_sub,
                     anchor="w").pack(fill="x", padx=16)
        tk.Label(s, text="Questions? forum desk · ext. 214", bg=SLATE, fg="#8795a3",
                 font=self.f_note, anchor="w").pack(side="bottom", fill="x", padx=16, pady=14)

    # ── state ─────────────────────────────────────────────────────────────
    def _refresh(self):
        n = len(self.cart)
        self.count_lbl.configure(text=f"{n} of {PICKS} packages reserved")
        for i, (name, rm) in enumerate(self.slots):
            if i < n:
                name.configure(text=_BY_ID[self.cart[i]][2], fg="#ffffff")
                rm.pack(side="right")
            else:
                name.configure(text="Open slot", fg="#8795a3")
                rm.pack_forget()
        for mid, b in self.add_btns.items():
            if mid in self.cart:
                b.configure(text="✓ Reserved", bg=BRONZE, fg="#ffffff", activebackground=BRONZE_DK,
                            activeforeground="#ffffff")
                self.cards[mid].configure(highlightbackground=BRONZE)
            else:
                b.configure(text="+ Reserve", bg=SLATE, fg="#ffffff", activebackground=SLATE_2,
                            activeforeground="#ffffff")
                self.cards[mid].configure(highlightbackground=EDGE)

    def _toggle(self, mid):
        # Tapping again removes the item — a misclick is correctable.
        if mid in self.cart:
            self.cart.remove(mid)
        elif len(self.cart) >= PICKS:
            self.notice.configure(text="Your rota holds two packages — remove one before "
                                       "adding another.")
            return
        else:
            self.cart.append(mid)
        self.notice.configure(text="")
        self._refresh()

    def _remove_slot(self, i):
        if i < len(self.cart):
            self.cart.pop(i)
            self.notice.configure(text="")
            self._refresh()

    def place_order(self):
        if len(self.cart) != PICKS:
            self.notice.configure(text=f"Choose exactly two packages ({len(self.cart)} "
                                       f"reserved so far).")
            return
        chosen = [{"id": mid, "name": _BY_ID[mid][2]} for mid in self.cart]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "briefing_plan.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "hf-4887322357"),
                       "reservedBriefings": chosen}, f, ensure_ascii=False, indent=2)
        self._confirm()

    def _confirm(self):
        d = self.done
        d.place(relx=0, rely=0, relwidth=1, relheight=1)
        d.lift()
        tk.Frame(d, bg=SLATE, height=62).pack(fill="x")
        tk.Frame(d, bg=BRONZE, height=3).pack(fill="x")
        card = tk.Frame(d, bg=CARD, highlightthickness=1, highlightbackground=EDGE)
        card.pack(pady=80, ipadx=30, ipady=16)
        c = tk.Canvas(card, width=64, height=64, bg=CARD, highlightthickness=0)
        c.pack(pady=(14, 0))
        c.create_rectangle(6, 6, 58, 58, fill=BRONZE, outline="")
        c.create_line(18, 33, 28, 43, 46, 22, fill="#ffffff", width=5, capstyle="round")
        tk.Label(card, text="Packages reserved", bg=CARD, fg=INK, font=self.f_big).pack(pady=(8, 0))
        ref = "BP-" + hashlib.md5("".join(self.cart).encode()).hexdigest()[:6].upper()
        tk.Label(card, text=f"Rota reference {ref} · shared with the forum coordinator",
                 bg=CARD, fg=MUTED, font=self.f_sub).pack(pady=(2, 16))
        for i, mid in enumerate(self.cart, 1):
            m = _BY_ID[mid]
            row = tk.Frame(card, bg=SOFT)
            row.pack(fill="x", padx=24, pady=4)
            tk.Label(row, text=f"PACKAGE {i} · {m[1].upper()}", bg=SOFT, fg=BRONZE_DK,
                     font=self.f_chip, anchor="w").pack(fill="x", padx=12, pady=(8, 0))
            tk.Label(row, text=m[2], bg=SOFT, fg=INK, font=self.f_title,
                     anchor="w").pack(fill="x", padx=12, pady=(0, 8))


if __name__ == "__main__":
    root = tk.Tk()
    BriefingPlanner(root)
    root.mainloop()
