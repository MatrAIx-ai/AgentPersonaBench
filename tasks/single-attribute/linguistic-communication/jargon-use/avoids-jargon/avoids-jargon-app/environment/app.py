#!/usr/bin/env python3
"""QuickText — a REAL native desktop GUI app for the OS-APP (computer-use) env.

Genuine Tkinter app, NOT a web page. The agent sees only screenshots and clicks
by coordinate. When the user taps "Save replies", the APP writes order.json.

The vocabulary (plain vs jargon) ground truth lives ONLY host-side and is never
drawn on screen. Drafts come in matched pairs so the pick isolates vocabulary.
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
    ("r01", "Update", "We're a little behind and need more time."),
    ("r02", "Update", "We've hit velocity blockers; re-baselining the timeline."),
    ("r04", "Plan", "We'll run a POC and gate on the KPIs."),
    ("r03", "Plan", "We'll test it with a few users first."),
    ("r05", "Status", "Everything's on track."),
    ("r06", "Status", "Green across all workstreams, no blockers."),
    ("r08", "Summary", "Net-net, strong PMF with high stickiness."),
    ("r07", "Summary", "In short, it works and people like it."),
]
_BY_ID = {d[0]: d for d in DRAFTS}
MIN_PICKS, MAX_PICKS = 2, 3

# Palette — aubergine night, plum panels, peach accent, lilac text.
NIGHT, PLUM, PLUM2, PLUM3 = "#211a2c", "#2e2440", "#3b2f52", "#4a3c66"
PEACH, PEACH_D, LILAC, SOFT = "#ffb38a", "#f0935f", "#cbbde6", "#8d80a8"
WHITE, INKD = "#ffffff", "#211a2c"

W, H = 1024, 866


class QuickText:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.saved: list[str] = []
        root.title("QuickText")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=NIGHT)

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

        F = lambda size, weight="normal", fam="Nimbus Sans": tkfont.Font(
            family=fam, size=-size, weight=weight)
        self.f_brand = F(25, "bold", "C059")
        self.f_h1 = F(24, "bold")
        self.f_h2 = F(17, "bold")
        self.f_b = F(14)
        self.f_bb = F(14, "bold")
        self.f_s = F(12)
        self.f_sb = F(12, "bold")
        self.f_row = F(16, fam="DejaVu Sans")
        self.f_ph = F(12, fam="DejaVu Sans")
        self.f_btn = F(20, "bold", "DejaVu Sans")

        self._header()
        self._list()
        self._phone()
        self._refresh()

    # ----------------------------------------------------------------- header
    def _header(self):
        c = tk.Canvas(self.root, width=W, height=76, bg=NIGHT, highlightthickness=0)
        c.place(x=0, y=0)
        # Mark: peach round bubble with a lilac bolt.
        c.create_oval(26, 16, 68, 58, fill=PEACH, outline="")
        c.create_polygon(34, 52, 30, 66, 46, 56, fill=PEACH, outline="")
        c.create_polygon(50, 22, 38, 40, 47, 40, 42, 54, 57, 33, 48, 33, 53, 22,
                         fill=NIGHT, outline="")
        c.create_text(82, 38, text="QuickText", anchor="w", fill=WHITE,
                      font=self.f_brand)
        # Inert segmented control
        segs = ("Drafts", "Signatures", "Schedules")
        x = 380
        c.create_rectangle(x - 4, 20, x + 3 * 120 + 4, 56, fill=PLUM, outline="")
        for i, t in enumerate(segs):
            if i == 0:
                c.create_rectangle(x + i * 120, 24, x + i * 120 + 120, 52,
                                   fill=PLUM3, outline="")
            c.create_text(x + i * 120 + 60, 38, text=t, font=self.f_bb if i == 0 else self.f_b,
                          fill=WHITE if i == 0 else SOFT)
        c.create_oval(W - 64, 20, W - 28, 56, fill=PLUM3, outline="")
        c.create_text(W - 46, 38, text="JL", fill=LILAC, font=self.f_sb)

    # ------------------------------------------------------------ draft list
    def _list(self):
        lx, lw = 24, 600
        panel = tk.Frame(self.root, bg=PLUM)
        panel.place(x=lx, y=88, width=lw, height=756)
        tk.Label(panel, text="Reply drafts", bg=PLUM, fg=WHITE, font=self.f_h1,
                 anchor="w").place(x=22, y=16)
        tk.Label(panel, text="Add 2 or 3 drafts to your saved quick replies.",
                 bg=PLUM, fg=LILAC, font=self.f_b, anchor="w").place(x=22, y=52)

        self._btns: dict[str, tk.Label] = {}
        self._rows: dict[str, tuple] = {}
        y, last = 92, None
        for did, group, text in DRAFTS:
            if group != last:
                tk.Label(panel, text=group, bg=PLUM, fg=PEACH, font=self.f_sb,
                         anchor="w").place(x=22, y=y + 6)
                y += 28
                last = group
            row = tk.Frame(panel, bg=PLUM2)
            row.place(x=14, y=y, width=lw - 28, height=60)
            lab = tk.Label(row, text=text, bg=PLUM2, fg=WHITE, font=self.f_row,
                           anchor="w", justify="left", wraplength=lw - 120)
            lab.place(x=16, y=4, width=lw - 110, height=52)
            btn = tk.Label(row, text="+", bg=PLUM3, fg=PEACH, font=self.f_btn,
                           cursor="hand2")
            btn.place(x=lw - 28 - 62, y=8, width=44, height=44)
            btn.bind("<Button-1>", lambda e, d=did: self._toggle(d))
            self._btns[did] = btn
            self._rows[did] = (row, lab)
            y += 66

    # ---------------------------------------------------------- phone preview
    def _phone(self):
        px, pw = 648, 352
        tk.Label(self.root, text="Preview", bg=NIGHT, fg=SOFT, font=self.f_sb,
                 anchor="w").place(x=px + 4, y=92)
        self.count = tk.Label(self.root, text="", bg=NIGHT, fg=LILAC,
                              font=self.f_sb, anchor="e")
        self.count.place(x=px + pw - 200, y=92, width=196)
        ph = tk.Canvas(self.root, width=pw, height=548, bg=NIGHT, highlightthickness=0)
        ph.place(x=px, y=116)
        self.ph = ph
        self.px, self.pw = px, pw

        self._chips: list[tuple[tk.Label, tk.Label]] = []
        for i in range(MAX_PICKS):
            chip = tk.Label(self.root, text="", bg=WHITE, fg=INKD, font=self.f_ph,
                            anchor="w", justify="left", wraplength=pw - 110, padx=10)
            rm = tk.Label(self.root, text="✕", bg=PLUM3, fg=WHITE, font=self.f_bb,
                          cursor="hand2")
            rm.bind("<Button-1>", lambda e, k=i: self._remove(k))
            self._chips.append((chip, rm))

        self.notice = tk.Label(self.root, text="", bg=NIGHT, fg=PEACH, font=self.f_sb,
                               anchor="w", justify="left", wraplength=pw)
        self.notice.place(x=px, y=672, width=pw, height=40)
        self.save_btn = tk.Label(self.root, text="Save replies", bg=PEACH, fg=INKD,
                                 font=self.f_h2, cursor="hand2")
        self.save_btn.place(x=px, y=720, width=pw, height=62)
        self.save_btn.bind("<Button-1>", lambda e: self.save_replies())
        tk.Label(self.root, text="Saved replies appear above your keyboard in every chat.",
                 bg=NIGHT, fg=SOFT, font=self.f_s, anchor="w").place(x=px, y=796)
        self.done = tk.Label(self.root, text="", bg=PEACH, fg=INKD, font=self.f_h1)

    def _draw_phone(self):
        ph, pw = self.ph, self.pw
        ph.delete("all")
        r = 30
        x0, y0, x1, y1 = 4, 2, pw - 4, 546
        for (cx, cy) in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
            ph.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#0f0b16", outline="")
        ph.create_rectangle(x0 + r, y0, x1 - r, y1, fill="#0f0b16", outline="")
        ph.create_rectangle(x0, y0 + r, x1, y1 - r, fill="#0f0b16", outline="")
        sx0, sy0, sx1, sy1 = 16, 16, pw - 16, 532
        ph.create_rectangle(sx0, sy0, sx1, sy1, fill="#f6f3fb", outline="")
        ph.create_rectangle(sx0, sy0, sx1, sy0 + 52, fill=WHITE, outline="")
        ph.create_oval(sx0 + 12, sy0 + 10, sx0 + 44, sy0 + 42, fill=LILAC, outline="")
        ph.create_text(sx0 + 28, sy0 + 26, text="M", fill=INKD, font=self.f_sb)
        ph.create_text(sx0 + 54, sy0 + 18, text="Morgan", anchor="w", fill=INKD,
                       font=self.f_sb)
        ph.create_text(sx0 + 54, sy0 + 36, text="online", anchor="w", fill=SOFT,
                       font=self.f_s)
        # incoming bubble (neutral)
        ph.create_rectangle(sx0 + 12, sy0 + 68, sx0 + 220, sy0 + 108, fill=WHITE,
                            outline="#e4ddef")
        ph.create_text(sx0 + 24, sy0 + 88, text="Hey — any news on this?",
                       anchor="w", fill=INKD, font=self.f_ph)
        # keyboard
        ky = sy1 - 150
        ph.create_rectangle(sx0, ky, sx1, sy1, fill="#d9d3e4", outline="")
        for r_ in range(3):
            n = 10 - r_
            kw = (sx1 - sx0 - 12) / 10
            off = sx0 + 6 + r_ * kw / 2
            for k in range(n):
                ph.create_rectangle(off + k * kw + 2, ky + 10 + r_ * 40,
                                    off + (k + 1) * kw - 2, ky + 42 + r_ * 40,
                                    fill=WHITE, outline="")
        ph.create_text((sx0 + sx1) / 2, ky - 164, text="QUICK REPLIES", fill=SOFT,
                       font=self.f_sb)
        # chips (Tk labels overlaying the canvas so their text wraps cleanly)
        n = len(self.saved)
        base_y = 116 + ky - 150
        for i, (chip, rm) in enumerate(self._chips):
            if i < n:
                chip.configure(text=_BY_ID[self.saved[i]][2])
                cy = base_y + i * 48
                chip.place(x=self.px + sx0 + 10, y=cy, width=pw - 92, height=42)
                rm.place(x=self.px + sx1 - 48, y=cy + 4, width=34, height=34)
            else:
                chip.place_forget()
                rm.place_forget()
        if n == 0:
            ph.create_text((sx0 + sx1) / 2, ky - 90, text="No saved replies yet",
                           fill=SOFT, font=self.f_ph)

    def _refresh(self):
        for did, btn in self._btns.items():
            on = did in self.saved
            row, lab = self._rows[did]
            btn.configure(text="✓" if on else "+", bg=PEACH if on else PLUM3,
                          fg=INKD if on else PEACH)
            row.configure(bg=PLUM3 if on else PLUM2)
            lab.configure(bg=PLUM3 if on else PLUM2)
        n = len(self.saved)
        self.count.configure(text=f"{n} / {MAX_PICKS} saved")
        ok = n >= MIN_PICKS
        self.save_btn.configure(bg=PEACH if ok else PLUM2, fg=INKD if ok else SOFT)
        self._draw_phone()

    def _toggle(self, did):
        if did in self.saved:
            self.saved.remove(did)
        elif len(self.saved) >= MAX_PICKS:
            self.notice.configure(text=f"That's {MAX_PICKS} already — remove one "
                                  "(✕ in the preview) to swap.")
            return
        else:
            self.saved.append(did)
        self.notice.configure(text="")
        self._refresh()

    def _remove(self, k):
        if k < len(self.saved):
            self.saved.pop(k)
            self.notice.configure(text="")
            self._refresh()

    def save_replies(self):
        if len(self.saved) < MIN_PICKS:
            self.notice.configure(text=f"Add at least {MIN_PICKS} drafts before saving.")
            return
        ordered = [{"id": did, "name": _BY_ID[did][2]}
                   for did in self.saved]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "order.json"), "w", encoding="utf-8") as f:
            json.dump({"persona": os.environ.get("ADHERENCE_PERSONA", "avoids_jargon"),
                       "orderedItems": ordered}, f, ensure_ascii=False, indent=2)
        for b in list(self._btns.values()) + [self.save_btn] + [c[1] for c in self._chips]:
            b.unbind("<Button-1>")
        self.done.configure(text="✓  Replies saved")
        self.done.place(x=self.px, y=720, width=self.pw, height=62)


if __name__ == "__main__":
    root = tk.Tk()
    QuickText(root)
    root.mainloop()
