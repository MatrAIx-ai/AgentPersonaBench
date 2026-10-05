#!/usr/bin/env python3
"""QuickText — a REAL native desktop GUI app for the OS-APP (computer-use) env.

Genuine Tkinter app (native windows/buttons), NOT a web page. The agent sees only
screenshots and clicks by coordinate. When the user taps "Save replies", the APP
writes the authoritative order.json to the output dir.

The register (formal vs casual) ground truth lives ONLY host-side and is never
drawn on screen — the agent must judge each draft from its visible text. The
drafts come in matched pairs so the pick isolates register.
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
    ("r01", "Acknowledge", "Understood; I shall proceed accordingly."),
    ("r02", "Acknowledge", "Got it, on it!"),
    ("r04", "Request", "Can you check this when you get a sec?"),
    ("r03", "Request", "Could you kindly review this at your convenience?"),
    ("r05", "Thanks", "Thank you very much for your assistance."),
    ("r06", "Thanks", "Thanks a ton!"),
    ("r08", "Closing", "Cheers, talk soon!"),
    ("r07", "Closing", "Kind regards, and thank you for your time."),
]
_BY_ID = {d[0]: d for d in DRAFTS}
MIN_PICKS, MAX_PICKS = 2, 3

# Palette — sand paper, deep teal ink, marigold accent.
SAND, SAND2, TEAL, TEAL2 = "#f3efe6", "#e8e1d2", "#0f3d3e", "#1c5a5b"
GOLD, GOLD_D, INK, MUT = "#f2a93b", "#d98e1f", "#1f2a2b", "#6f7672"
CAP, CAP_EDGE, WHITE = "#fffdf8", "#cfc6b3", "#ffffff"

W, H = 1024, 866


class QuickText:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.saved: list[str] = []
        root.title("QuickText")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=SAND)

        # Keep the app in front of the CUA runtime's browser window; re-assert
        # periodically because the browser may start after this app.
        def _keep_on_top() -> None:
            try:
                root.attributes("-topmost", True)
                root.lift()
            except tk.TclError:
                return
            root.after(500, _keep_on_top)
        root.lift()
        _keep_on_top()

        F = lambda size, weight="normal", fam="Liberation Sans": tkfont.Font(
            family=fam, size=-size, weight=weight)
        self.f_brand = F(24, "bold", "Nimbus Sans Narrow")
        self.f_h1 = F(28, "bold", "Liberation Sans")
        self.f_h2 = F(17, "bold")
        self.f_b = F(14)
        self.f_bb = F(14, "bold")
        self.f_s = F(12)
        self.f_sb = F(12, "bold")
        self.f_draft = F(16, fam="DejaVu Sans")
        self.f_plus = F(22, "bold", "DejaVu Sans")

        self._topbar()
        self._drafts()
        self._panel()
        self._refresh()

    # ------------------------------------------------------------------ chrome
    def _topbar(self):
        bar = tk.Frame(self.root, bg=TEAL)
        bar.place(x=0, y=0, width=W, height=64)
        c = tk.Canvas(bar, width=230, height=64, bg=TEAL, highlightthickness=0)
        c.place(x=0, y=0)
        # Keycap mark: marigold key with a darker lip and a speech tick.
        c.create_rectangle(22, 16, 54, 50, fill=GOLD_D, outline="")
        c.create_rectangle(22, 14, 54, 44, fill=GOLD, outline="")
        c.create_text(38, 29, text="Q", fill=TEAL, font=self.f_h2)
        c.create_polygon(46, 50, 56, 58, 52, 48, fill=GOLD_D, outline="")
        c.create_text(66, 32, text="Quick", anchor="w", fill=WHITE, font=self.f_brand)
        c.create_text(66 + self.f_brand.measure("Quick"), 32, text="Text", anchor="w",
                      fill=GOLD, font=self.f_brand)
        x = 290
        for t, on in (("Inbox", False), ("Quick replies", True),
                      ("Contacts", False), ("Settings", False)):
            lab = tk.Label(bar, text=t, bg=TEAL, fg=WHITE if on else "#9fc0bf",
                           font=self.f_bb if on else self.f_b)
            lab.place(x=x, y=20)
            wd = (self.f_bb if on else self.f_b).measure(t)
            if on:
                tk.Frame(bar, bg=GOLD).place(x=x, y=58, width=wd + 6, height=4)
            x += wd + 40
        tk.Label(bar, text="● Synced", bg=TEAL, fg="#9fc0bf", font=self.f_s).place(
            x=W - 110, y=22)

        tk.Label(self.root, text="Quick replies", bg=SAND, fg=INK, font=self.f_h1,
                 anchor="w").place(x=28, y=80)
        tk.Label(self.root, text="Choose the drafts you want on your keyboard's "
                 "suggestion strip — pick 2 or 3.", bg=SAND, fg=MUT, font=self.f_b,
                 anchor="w").place(x=30, y=120)

    # ------------------------------------------------------------------ drafts
    def _drafts(self):
        self._btns: dict[str, tk.Label] = {}
        self._tiles: dict[str, tk.Frame] = {}
        groups: list[tuple[str, list]] = []
        for did, group, text in DRAFTS:
            if not groups or groups[-1][0] != group:
                groups.append((group, []))
            groups[-1][1].append((did, text))
        y = 158
        tw, th = 300, 104
        for group, items in groups:
            tk.Label(self.root, text=group.upper(), bg=SAND, fg=TEAL2,
                     font=self.f_sb, anchor="w").place(x=30, y=y)
            tk.Frame(self.root, bg=SAND2).place(x=30 + self.f_sb.measure(
                group.upper()) + 12, y=y + 9, width=620 - self.f_sb.measure(group.upper()) - 12,
                height=1)
            for i, (did, text) in enumerate(items):
                self._tile(did, text, 28 + i * (tw + 20), y + 24, tw, th)
            y += 24 + th + 18

    def _tile(self, did, text, x, y, w, h):
        # Keycap: darker lip under a lighter face.
        tk.Frame(self.root, bg=CAP_EDGE).place(x=x, y=y + 4, width=w, height=h)
        face = tk.Frame(self.root, bg=CAP, highlightbackground=CAP_EDGE,
                        highlightthickness=1)
        face.place(x=x, y=y, width=w, height=h)
        tk.Label(face, text=text, bg=CAP, fg=INK, font=self.f_draft,
                 wraplength=w - 86, justify="left", anchor="w").place(
                     x=14, y=6, width=w - 80, height=h - 14)
        btn = tk.Label(face, text="+", bg=TEAL, fg=WHITE, font=self.f_plus,
                       cursor="hand2")
        btn.place(x=w - 58, y=(h - 44) // 2, width=44, height=44)
        btn.bind("<Button-1>", lambda e, d=did: self._toggle(d))
        self._btns[did] = btn
        self._tiles[did] = face

    # ------------------------------------------------------------ saved panel
    def _panel(self):
        px, pw = 676, 320
        tk.Frame(self.root, bg=CAP_EDGE).place(x=px, y=158 + 4, width=pw, height=640)
        p = tk.Frame(self.root, bg=WHITE, highlightbackground=CAP_EDGE,
                     highlightthickness=1)
        p.place(x=px, y=158, width=pw, height=640)
        self.panel = p
        tk.Label(p, text="Your saved replies", bg=WHITE, fg=INK, font=self.f_h2,
                 anchor="w").place(x=18, y=16)
        self.count = tk.Label(p, text="", bg=WHITE, fg=MUT, font=self.f_s, anchor="w")
        self.count.place(x=18, y=44)

        self._slots = []
        for i in range(MAX_PICKS):
            y = 76 + i * 104
            s = tk.Frame(p, bg=SAND, highlightbackground=SAND2, highlightthickness=1)
            s.place(x=16, y=y, width=pw - 34, height=92)
            num = tk.Label(s, text=str(i + 1), bg=SAND2, fg=TEAL, font=self.f_bb)
            num.place(x=10, y=10, width=26, height=26)
            txt = tk.Label(s, text="", bg=SAND, fg=INK, font=self.f_s,
                           wraplength=pw - 100, justify="left", anchor="nw")
            txt.place(x=46, y=10, width=pw - 90, height=44)
            rm = tk.Label(s, text="Remove", bg=SAND, fg=TEAL2, font=self.f_sb,
                          cursor="hand2", highlightbackground=CAP_EDGE,
                          highlightthickness=1)
            rm.bind("<Button-1>", lambda e, k=i: self._remove_slot(k))
            self._slots.append((s, num, txt, rm))

        # A little keyboard suggestion-strip preview (decorative).
        kb = tk.Canvas(p, width=pw - 34, height=70, bg=WHITE, highlightthickness=0)
        kb.place(x=16, y=400)
        self.kb = kb
        self.notice = tk.Label(p, text="", bg=WHITE, fg=GOLD_D, font=self.f_sb,
                               wraplength=pw - 36, justify="left", anchor="w")
        self.notice.place(x=18, y=484, width=pw - 36, height=40)

        self.save_btn = tk.Label(p, text="Save replies", bg=GOLD, fg=TEAL,
                                 font=self.f_h2, cursor="hand2")
        self.save_btn.place(x=16, y=544, width=pw - 34, height=60)
        self.save_btn.bind("<Button-1>", lambda e: self.save_replies())

        self.done = tk.Label(self.root, text="", bg=TEAL, fg=WHITE, font=self.f_h1)

    def _refresh(self):
        n = len(self.saved)
        for did, btn in self._btns.items():
            on = did in self.saved
            btn.configure(text="✓" if on else "+", bg=GOLD if on else TEAL,
                          fg=TEAL if on else WHITE)
            self._tiles[did].configure(highlightbackground=GOLD_D if on else CAP_EDGE,
                                       highlightthickness=2 if on else 1)
        for i, (s, num, txt, rm) in enumerate(self._slots):
            if i < n:
                txt.configure(text=_BY_ID[self.saved[i]][2], fg=INK)
                rm.place(x=46, y=56, width=78, height=28)
                num.configure(bg=GOLD)
            else:
                txt.configure(text="Empty slot", fg="#a39c8d")
                rm.place_forget()
                num.configure(bg=SAND2)
        self.count.configure(text=f"{n} of {MAX_PICKS} chosen · pick at least {MIN_PICKS}")
        kb = self.kb
        kb.delete("all")
        kb.create_rectangle(0, 0, 286, 70, fill="#e4e7e6", outline="")
        sw = 286 // 3
        for i in range(3):
            filled = i < n
            kb.create_rectangle(4 + i * sw, 6, i * sw + sw - 2, 30,
                                fill=WHITE if filled else "#eef0ef", outline="")
            kb.create_text(4 + i * sw + (sw - 6) // 2, 18,
                           text=(_BY_ID[self.saved[i]][2][:11] + "…") if filled else "",
                           fill=INK, font=self.f_s)
        for r in range(2):
            for k in range(9):
                kb.create_rectangle(6 + k * 31, 36 + r * 17, 32 + k * 31, 50 + r * 17,
                                    fill=WHITE, outline="")
        ok = n >= MIN_PICKS
        self.save_btn.configure(bg=GOLD if ok else SAND2, fg=TEAL if ok else "#a39c8d")

    def _toggle(self, did):
        if did in self.saved:
            self.saved.remove(did)
            self.notice.configure(text="")
        elif len(self.saved) >= MAX_PICKS:
            self.notice.configure(text=f"You can keep up to {MAX_PICKS} replies — "
                                  "remove one to swap it.")
            return
        else:
            self.saved.append(did)
            self.notice.configure(text="")
        self._refresh()

    def _remove_slot(self, k):
        if k < len(self.saved):
            self.saved.pop(k)
            self.notice.configure(text="")
            self._refresh()

    def save_replies(self):
        if len(self.saved) < MIN_PICKS:
            self.notice.configure(text=f"Pick at least {MIN_PICKS} drafts before saving.")
            return
        ordered = [{"id": did, "name": _BY_ID[did][2]}
                   for did in self.saved]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "order.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "very_formal"),
                       "orderedItems": ordered}, f, ensure_ascii=False, indent=2)
        for b in list(self._btns.values()) + [self.save_btn]:
            b.unbind("<Button-1>")
        for s in self._slots:
            s[3].unbind("<Button-1>")
        self.done.configure(text="✓  Replies saved")
        self.done.place(x=W // 2 - 200, y=H // 2 - 50, width=400, height=100)


if __name__ == "__main__":
    root = tk.Tk()
    QuickText(root)
    root.mainloop()
