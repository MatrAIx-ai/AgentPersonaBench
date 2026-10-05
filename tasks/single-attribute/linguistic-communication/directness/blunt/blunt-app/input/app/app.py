#!/usr/bin/env python3
"""QuickText — a REAL native desktop GUI app for the OS-APP (computer-use) env.

Genuine Tkinter app, NOT a web page. The agent sees only screenshots and clicks
by coordinate. When the user taps "Save replies", the APP writes order.json.

The ground truth lives ONLY host-side (tests/answer_key.yaml) and is never
drawn on screen. Drafts come in matched pairs per situation so the pick isolates
wording. Layout: a draft library (four situation panels of chat bubbles, each
with a + button) on the left and a live phone preview of the saved quick-reply
tray on the right, with the Save replies button under it.
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# (id, group, text) — this app carries NO adherence label; the id -> label
# map lives host-side in tests/answer_key.yaml.
DRAFTS = [
    ("r01", "Feedback", "This doesn't work. Change it."),
    ("r02", "Feedback", "I wonder if maybe this could possibly be reconsidered?"),
    ("r04", "Decline", "I'd love to but I'm not totally sure I can, sorry..."),
    ("r03", "Decline", "No, I can't take this on."),
    ("r05", "Disagree", "I disagree. This is the wrong call."),
    ("r06", "Disagree", "I could be off base, but I have a small concern, perhaps?"),
    ("r08", "Decision", "I'm leaning against it, but I'm really not sure."),
    ("r07", "Decision", "No. We're not doing that."),
]
_BY_ID = {d[0]: d for d in DRAFTS}
MIN_PICKS, MAX_PICKS = 2, 3

# Blueberry + sunflower palette on a cool paper background.
BG = "#f3f4fa"
PANEL = "#ffffff"
BERRY = "#2b2e73"
BERRY_2 = "#4a4fb0"
SUN = "#ffc93c"
SUN_DK = "#e8ad12"
INK = "#1d1f3a"
MUTED = "#6b6f8e"
BUBBLE = "#eceefb"
LINE = "#dcdfef"
PHONE = "#15163a"
SCREEN = "#fbfbfe"


class QuickText:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.saved: list[str] = []
        self.add_btns: dict[str, tk.Button] = {}
        root.title("QuickText")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=BG)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        self.f_word = tkfont.Font(family="Nimbus Sans", size=-26, weight="bold")
        self.f_nav = tkfont.Font(family="DejaVu Sans", size=-13)
        self.f_navb = tkfont.Font(family="DejaVu Sans", size=-13, weight="bold")
        self.f_h1 = tkfont.Font(family="Nimbus Sans", size=-24, weight="bold")
        self.f_h3 = tkfont.Font(family="Nimbus Sans", size=-17, weight="bold")
        self.f_body = tkfont.Font(family="DejaVu Sans", size=-14)
        self.f_small = tkfont.Font(family="DejaVu Sans", size=-12)
        self.f_caps = tkfont.Font(family="DejaVu Sans", size=-11, weight="bold")
        self.f_btn = tkfont.Font(family="DejaVu Sans", size=-18, weight="bold")
        self.f_cta = tkfont.Font(family="DejaVu Sans", size=-15, weight="bold")
        self.f_big = tkfont.Font(family="Nimbus Sans", size=-40, weight="bold")

        self._topbar()
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(14, 18))
        self.left = tk.Frame(body, bg=BG)
        self.left.pack(side="left", fill="both", expand=True)
        self.right = tk.Frame(body, bg=BG, width=300)
        self.right.pack(side="right", fill="y", padx=(20, 0))
        self.right.pack_propagate(False)
        self._library()
        self._preview()
        self.done = tk.Frame(root, bg=BERRY)
        self._refresh()

    # --------------------------------------------------------------- chrome
    def _topbar(self) -> None:
        bar = tk.Frame(self.root, bg=BERRY, height=66)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        logo = tk.Canvas(bar, width=44, height=40, bg=BERRY, highlightthickness=0)
        logo.pack(side="left", padx=(24, 10))
        # Speech bubble carrying a lightning bolt.
        logo.create_polygon(4, 4, 40, 4, 40, 28, 18, 28, 8, 37, 10, 28, 4, 28,
                            fill=SUN, outline="")
        logo.create_polygon(24, 8, 15, 18, 21, 18, 17, 26, 28, 14, 22, 14, 26, 8,
                            fill=BERRY, outline="")
        tk.Label(bar, text="Quick", font=self.f_word, bg=BERRY, fg="white").pack(side="left")
        tk.Label(bar, text="Text", font=self.f_word, bg=BERRY, fg=SUN).pack(side="left")
        nav = tk.Frame(bar, bg=BERRY)
        nav.pack(side="right", padx=24)
        for i, t in enumerate(("Chats", "Quick replies", "Contacts", "Settings")):
            cell = tk.Frame(nav, bg=BERRY)
            cell.pack(side="left", padx=10)
            tk.Label(cell, text=t, font=self.f_navb if i == 1 else self.f_nav, bg=BERRY,
                     fg="white" if i == 1 else "#b9bce6").pack(pady=(6, 3))
            tk.Frame(cell, bg=SUN if i == 1 else BERRY, height=3).pack(fill="x")

    # -------------------------------------------------------------- library
    def _library(self) -> None:
        tk.Label(self.left, text="Draft library", font=self.f_h1, bg=BG, fg=INK).pack(anchor="w")
        tk.Label(self.left, text=f"Tap + on the {MIN_PICKS}–{MAX_PICKS} drafts you'd really "
                 "send. Saved drafts appear in your keyboard's quick-reply tray.",
                 font=self.f_small, bg=BG, fg=MUTED, anchor="w").pack(fill="x", pady=(2, 12))
        grid = tk.Frame(self.left, bg=BG)
        grid.pack(fill="x")
        for c in range(2):
            grid.columnconfigure(c, weight=1, uniform="c")
        for r in range(2):
            grid.rowconfigure(r, weight=1, uniform="r")
        how = tk.Frame(self.left, bg="#e6e8f7")
        how.pack(fill="x", pady=(16, 0), ipady=8)
        tk.Label(how, text="HOW QUICK REPLIES WORK", font=self.f_caps, bg="#e6e8f7",
                 fg=BERRY_2).pack(anchor="w", padx=18, pady=(16, 8))
        for n, t in enumerate(("Swipe up on the message bar in any chat.",
                               "Tap a saved reply to drop it into the message box.",
                               "Edit it if you like, then send as usual."), 1):
            row = tk.Frame(how, bg="#e6e8f7")
            row.pack(fill="x", padx=18, pady=3)
            dot = tk.Canvas(row, width=24, height=24, bg="#e6e8f7", highlightthickness=0)
            dot.pack(side="left")
            dot.create_oval(1, 1, 23, 23, fill=BERRY, outline="")
            dot.create_text(12, 12, text=str(n), fill="white", font=self.f_caps)
            tk.Label(row, text=t, font=self.f_body, bg="#e6e8f7", fg=INK).pack(
                side="left", padx=10)
        groups: list[str] = []
        for _, g, _ in DRAFTS:
            if g not in groups:
                groups.append(g)
        for gi, g in enumerate(groups):
            panel = tk.Frame(grid, bg=PANEL, highlightthickness=1, highlightbackground=LINE)
            panel.grid(row=gi // 2, column=gi % 2, sticky="nsew",
                       padx=(0 if gi % 2 == 0 else 8, 8 if gi % 2 == 0 else 0),
                       pady=(0 if gi < 2 else 8, 8 if gi < 2 else 0))
            head = tk.Frame(panel, bg=PANEL)
            head.pack(fill="x", padx=16, pady=(14, 6))
            tk.Label(head, text=g, font=self.f_h3, bg=PANEL, fg=INK).pack(side="left")
            tk.Label(head, text="2 drafts", font=self.f_small, bg=PANEL,
                     fg=MUTED).pack(side="right")
            for did, dg, text in DRAFTS:
                if dg == g:
                    self._bubble(panel, did, text)

    def _bubble(self, parent, did, text) -> None:
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=14, pady=(4, 10))
        btn = tk.Button(row, text="+", font=self.f_btn, width=2, bg=BERRY, fg="white",
                        activebackground=BERRY_2, activeforeground="white", relief="flat",
                        bd=0, highlightthickness=0, pady=4, cursor="hand2",
                        command=lambda: self._toggle(did))
        btn.pack(side="right", anchor="n", padx=(10, 0), pady=6)
        self.add_btns[did] = btn
        bub = tk.Frame(row, bg=BUBBLE)
        bub.pack(side="left", fill="x", expand=True)
        tk.Label(bub, text=text, font=self.f_body, bg=BUBBLE, fg=INK, justify="left",
                 anchor="w", wraplength=205).pack(fill="x", padx=14, pady=14)

    # -------------------------------------------------------------- preview
    def _preview(self) -> None:
        r = self.right
        tk.Label(r, text="Keyboard preview", font=self.f_h3, bg=BG, fg=INK).pack(anchor="w")
        tk.Label(r, text="What your quick-reply tray will show", font=self.f_small,
                 bg=BG, fg=MUTED).pack(anchor="w", pady=(2, 10))
        self.phone = tk.Canvas(r, width=300, height=520, bg=BG, highlightthickness=0)
        self.phone.pack()
        foot = tk.Frame(r, bg=BG)
        foot.pack(fill="x", pady=(10, 0))
        self.saved_lbl = tk.Label(foot, text="", font=self.f_navb, bg=BG, fg=INK)
        self.saved_lbl.pack(anchor="w")
        self.hint = tk.Label(foot, text="", font=self.f_small, bg=BG, fg=MUTED,
                             wraplength=290, justify="left")
        self.hint.pack(anchor="w", pady=(2, 8))
        self.confirm_btn = tk.Button(foot, text="Save replies", font=self.f_cta, bg=SUN, fg=INK,
                                  activebackground=SUN_DK, activeforeground=INK,
                                  relief="flat", bd=0, highlightthickness=0, pady=12,
                                  cursor="hand2", command=self.confirm)
        self.confirm_btn.pack(fill="x")

    def _rrect(self, c, x0, y0, x1, y1, r, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return c.create_polygon(pts, smooth=True, **kw)

    def _draw_phone(self) -> None:
        c = self.phone
        c.delete("all")
        self._rrect(c, 20, 0, 280, 520, 34, fill=PHONE, outline="")
        self._rrect(c, 30, 12, 270, 508, 26, fill=SCREEN, outline="")
        c.create_rectangle(120, 18, 180, 26, fill=PHONE, outline="")
        c.create_text(48, 46, text="Alex", anchor="w", font=self.f_navb, fill=INK)
        c.create_text(252, 46, text="now", anchor="e", font=self.f_small, fill=MUTED)
        c.create_line(30, 64, 270, 64, fill=LINE)
        self._rrect(c, 44, 78, 222, 132, 14, fill=BUBBLE, outline="")
        c.create_text(56, 105, text="Got a minute to look at\nthe plan before Friday?",
                      anchor="w", font=self.f_small, fill=INK)
        # Quick-reply tray
        tray_top = 236
        c.create_rectangle(30, tray_top, 270, 508, fill="#eef0f8", outline="")
        c.create_text(46, tray_top + 18, text="QUICK REPLIES", anchor="w",
                      font=self.f_caps, fill=MUTED)
        c.create_text(254, tray_top + 18, text=f"{len(self.saved)}/{MAX_PICKS}",
                      anchor="e", font=self.f_caps, fill=MUTED)
        y = tray_top + 36
        if not self.saved:
            c.create_text(150, y + 60, text="Tap + on a draft\nto add it here.",
                          font=self.f_small, fill=MUTED, justify="center")
        for did in self.saved:
            t = c.create_text(58, y + 10, text=_BY_ID[did][2], anchor="nw",
                              font=self.f_small, fill=INK, width=190)
            x0, y0, x1, y1 = c.bbox(t)
            self._rrect(c, 44, y, 256, y1 + 10, 12, fill=SUN, outline="")
            c.tag_raise(t)
            y = y1 + 20

    def _refresh(self) -> None:
        full = len(self.saved) >= MAX_PICKS
        for did, btn in self.add_btns.items():
            if did in self.saved:
                btn.configure(text="✓", bg=SUN, fg=INK, activebackground=SUN_DK,
                              activeforeground=INK, state="normal", cursor="hand2")
            elif full:
                btn.configure(text="+", bg="#c9cbe0", fg="white", state="disabled",
                              disabledforeground="white", cursor="arrow")
            else:
                btn.configure(text="+", bg=BERRY, fg="white", activebackground=BERRY_2,
                              activeforeground="white", state="normal", cursor="hand2")
        n = len(self.saved)
        self.saved_lbl.configure(text=f"Saved · {n} repl{'y' if n == 1 else 'ies'}")
        if n < MIN_PICKS:
            msg = f"Pick {MIN_PICKS}–{MAX_PICKS} drafts. Tap ✓ to take one back out."
        elif full:
            msg = f"Tray full ({MAX_PICKS} max). Tap ✓ on a draft to swap it out."
        else:
            msg = "Ready to save — or add one more."
        self.hint.configure(text=msg, fg=MUTED)
        self._draw_phone()

    def _toggle(self, did: str) -> None:
        if did in self.saved:
            self.saved.remove(did)
        elif len(self.saved) < MAX_PICKS:
            self.saved.append(did)
        self._refresh()

    def confirm(self) -> None:
        if len(self.saved) < MIN_PICKS:
            self.hint.configure(text=f"Save at least {MIN_PICKS} drafts first.", fg="#c0392b")
            return
        ordered = [{"id": did, "name": _BY_ID[did][2]} for did in self.saved]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "order.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", ""),
                       "orderedItems": ordered}, f, ensure_ascii=False, indent=2)
        d = self.done
        d.place(relx=0, rely=0, relwidth=1, relheight=1)
        inner = tk.Frame(d, bg=BERRY)
        inner.place(relx=0.5, rely=0.42, anchor="center")
        c = tk.Canvas(inner, width=90, height=80, bg=BERRY, highlightthickness=0)
        c.pack()
        c.create_polygon(6, 6, 84, 6, 84, 58, 40, 58, 20, 76, 24, 58, 6, 58,
                         fill=SUN, outline="")
        c.create_line(28, 32, 40, 44, 62, 20, fill=BERRY, width=6, capstyle="round",
                      joinstyle="round")
        tk.Label(inner, text="Replies saved", font=self.f_big, bg=BERRY,
                 fg="white").pack(pady=(16, 6))
        tk.Label(inner, text=f"{len(self.saved)} quick replies are now in your keyboard tray.",
                 font=self.f_body, bg=BERRY, fg="#c9ccf0").pack()


if __name__ == "__main__":
    root = tk.Tk()
    QuickText(root)
    root.mainloop()
