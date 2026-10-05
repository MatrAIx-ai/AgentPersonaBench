#!/usr/bin/env python3
"""ConnectDesk — a native desktop social app (Tkinter, stdlib only).

Opens on the Connection Requests screen: a profile rail on the left and the six
pending requests as a 2x3 grid of equal cards, each with its own Accept /
Decline choice (changeable until you confirm). "Confirm" stays disabled until
every request is decided; confirming makes the app write connections.json
(what you chose, plus the sequence of taps) to the output directory and show
that your responses were sent.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 connectdesk.py
"""
from __future__ import annotations

import json
import os
import zlib

try:
    import tkinter as tk
    from tkinter import font as tkfont
except ImportError:  # pragma: no cover
    tk = tkfont = None

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR")
              or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or os.environ.get("MATRIX_OUTPUT_DIR") or "/app/output")

# (id, name, descriptor, ask, mutual)
#   descriptor = a short, neutral line about who they are
#   ask        = the one-line context for this specific request
#   mutual     = mutual-contacts count, comparable across all six rows
WINDOW_W, WINDOW_H = 1024, 868

CATALOG = [
    ("fr1", "Amara Johnson",
     "Gets a group together on Saturdays; you met this spring",
     "One Saturday a month, three hours around the market and a long "
     "coffee after, whoever turns up.",
     6),
    ("fr2", "Malik Carter",
     "Your cousin; you have known each other your whole lives",
     "An hour on the phone every other Sunday, just the two of you — "
     "and he wants the real answer to how you are, not the headline.",
     5),
    ("fr3", "Ethan Walsh",
     "Product manager; sat two desks over from you for six years",
     "An evening most months, three hours, twenty-odd people from "
     "the industry.",
     7),
    ("fr4", "Hannah Ross",
     "Old friend from school; you drifted apart over the years",
     "A long lunch once a month, two or three hours, just the two of "
     "you — she wants what is actually going on, not the surface.",
     7),
    ("fr5", "Priya Raman",
     "Lives two floors up; you have been neighbours about two years",
     "First Tuesday of the month, a couple of hours, everyone in "
     "the block.",
     5),
    ("fr6", "Meera Nair",
     "You matched at a mutual friend's dinner party this spring",
     "An hour on a call every couple of weeks, just the two of you — "
     "she wants to be who you tell first when something goes wrong, "
     "and to tell you the same.",
     6),
]
_BY_ID = {row[0]: row for row in CATALOG}

# palette: oat canvas, ink-violet text, coral action, teal/slate choices
OAT, OAT_D = "#f5efe8", "#e9e0d5"
CARD = "#ffffff"
INK, INK2, MUT = "#2a2233", "#554b60", "#8f8698"
CORAL, CORAL_D = "#e2574c", "#c2443a"
TEAL, SLATE = "#1f7a72", "#5b5f6b"
TEAL_L, SLATE_L = "#e2f1ef", "#eceef1"
LINE = "#e4dbd0"
AV = ["#8a6fb0", "#c07a3a", "#3f7f9a", "#b0566e", "#5f8a4a", "#7a6a55"]


def rrect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def avatar_color(rid: str, name: str) -> str:
    return AV[zlib.crc32((rid + name).encode()) % len(AV)]


class ConnectDesk:
    def __init__(self, root):
        self.root = root
        self.decisions: dict[str, str] = {}
        self.events: list[dict[str, str]] = []
        self.buttons: dict = {}
        self.stamps: dict = {}
        self.finished = False
        root.title("ConnectDesk")
        root.geometry("1024x868+0+0")
        root.configure(bg=OAT)
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))
        F = "Nimbus Sans"
        self.f_word = tkfont.Font(family=F, size=19, weight="bold")
        self.f_h = tkfont.Font(family=F, size=18, weight="bold")
        self.f_name = tkfont.Font(family=F, size=14, weight="bold")
        self.f_body = tkfont.Font(family=F, size=12)
        self.f_bold = tkfont.Font(family=F, size=12, weight="bold")
        self.f_ask = tkfont.Font(family="Liberation Serif", size=12,
                                 slant="italic")
        self.f_btn = tkfont.Font(family=F, size=13, weight="bold")
        self.f_big = tkfont.Font(family=F, size=28, weight="bold")

        self.build_topbar()
        main = tk.Frame(root, bg=OAT)
        main.pack(fill="both", expand=True)
        self.build_rail(main)
        self.build_grid(main)
        self.done = tk.Frame(root, bg=INK)

    # ---- chrome -----------------------------------------------------------
    def build_topbar(self):
        cv = tk.Canvas(self.root, height=62, bg=CARD, highlightthickness=0)
        cv.pack(fill="x")
        cv.create_oval(20, 15, 50, 45, fill=CORAL, outline="")
        cv.create_oval(36, 15, 66, 45, fill="", outline=INK, width=3)
        cv.create_text(78, 31, text="ConnectDesk", anchor="w", fill=INK,
                       font=self.f_word)
        x = 300
        for lab, on in (("Home", False), ("Messages", False),
                        ("Requests", True), ("Groups", False)):
            cv.create_text(x, 31, text=lab, anchor="w",
                           fill=INK if on else MUT,
                           font=self.f_bold if on else self.f_body)
            if on:
                w = self.f_bold.measure(lab)
                cv.create_line(x, 58, x + w, 58, fill=CORAL, width=4)
                rrect(cv, x + w + 6, 20, x + w + 30, 42, 10, fill=CORAL,
                      outline="")
                cv.create_text(x + w + 18, 31, text="6", fill="white",
                               font=self.f_bold)
                x += 26
            x += self.f_body.measure(lab) + 36
        cv.create_oval(970, 13, 1006, 49, fill=INK2, outline="")
        cv.create_text(988, 31, text="ME", fill="white", font=self.f_bold)
        cv.create_line(0, 61, 1024, 61, fill=LINE)

    def build_rail(self, parent):
        cv = tk.Canvas(parent, width=214, bg=OAT, highlightthickness=0)
        cv.pack(side="left", fill="y")
        rrect(cv, 16, 18, 200, 250, 16, fill=CARD, outline=LINE)
        cv.create_rectangle(17, 19, 199, 70, fill=OAT_D, outline="")
        cv.create_oval(76, 38, 140, 102, fill=INK2, outline=CARD, width=4)
        cv.create_text(108, 70, text="ME", fill="white", font=self.f_name)
        cv.create_text(108, 124, text="Your profile", fill=INK,
                       font=self.f_name)
        cv.create_text(108, 148, text="Member since 2019", fill=MUT,
                       font=self.f_body)
        cv.create_line(34, 172, 182, 172, fill=LINE)
        cv.create_text(40, 196, text="Connections", anchor="w", fill=INK2,
                       font=self.f_body)
        cv.create_text(176, 196, text="212", anchor="e", fill=INK,
                       font=self.f_bold)
        cv.create_text(40, 224, text="Pending", anchor="w", fill=INK2,
                       font=self.f_body)
        cv.create_text(176, 224, text="6", anchor="e", fill=INK,
                       font=self.f_bold)
        rrect(cv, 16, 268, 200, 420, 16, fill=CARD, outline=LINE)
        cv.create_text(34, 292, text="How this works", anchor="w", fill=INK,
                       font=self.f_bold)
        cv.create_text(34, 312, anchor="nw", width=150, fill=INK2,
                       font=self.f_body,
                       text="Choose Accept or Decline on every request. "
                            "You can change a choice until you confirm.")
        self.rail = cv

    # ---- request grid -----------------------------------------------------
    def build_grid(self, parent):
        cv = tk.Canvas(parent, bg=OAT, highlightthickness=0)
        cv.pack(side="left", fill="both", expand=True)
        self.grid = cv
        cv.create_text(8, 20, text="Connection Requests", anchor="w",
                       fill=INK, font=self.f_h)
        cv.create_text(8, 44, text="6 people would like to connect with you",
                       anchor="w", fill=MUT, font=self.f_body)
        cw, ch, gap = 386, 240, 8
        for i, row in enumerate(CATALOG):
            r, c = divmod(i, 2)
            self.make_card(cv, row, 6 + c * (cw + gap), 62 + r * (ch + gap),
                           cw, ch)
        # progress + confirm live at the foot of the left rail
        rail = self.rail
        y = 560
        self.foot_y = y
        rrect(rail, 16, y, 200, y + 206, 16, fill=CARD, outline=LINE)
        rail.create_text(34, y + 26, text="Your responses", anchor="w",
                         fill=INK, font=self.f_bold)
        self.status = tk.Label(rail, text=f"0 of {len(CATALOG)} decided",
                               bg=CARD, fg=INK2, font=self.f_body,
                               anchor="w", justify="left", wraplength=150)
        rail.create_window(34, y + 46, window=self.status, anchor="nw",
                           width=156)
        rail.create_rectangle(34, y + 96, 182, y + 104, fill=OAT_D,
                              outline="")
        self.prog = rail.create_rectangle(34, y + 96, 34, y + 104,
                                          fill=CORAL, outline="")
        self.confirm = tk.Button(
            rail, text="Confirm", command=self.finish, state="disabled",
            bg="#cfc6bd", fg="white", disabledforeground="#f4efe9",
            activebackground=CORAL_D, activeforeground="white",
            relief="flat", bd=0, pady=10, font=self.f_btn, cursor="hand2")
        rail.create_window(34, y + 124, window=self.confirm, anchor="nw",
                           width=148, height=48)
        rail.create_text(108, y + 188, text="Confirm sends all six",
                         fill=MUT, font=self.f_body)

    def make_card(self, cv, row, x, y, w, h):
        rid, name, descriptor, ask, mutual = row
        rrect(cv, x, y, x + w, y + h, 14, fill=CARD, outline=LINE)
        col = avatar_color(rid, name)
        cv.create_oval(x + 16, y + 16, x + 62, y + 62, fill=col, outline="")
        ini = "".join(p[0] for p in name.split()[:2])
        cv.create_text(x + 39, y + 39, text=ini, fill="white",
                       font=self.f_bold)
        cv.create_text(x + 74, y + 28, text=name, anchor="w", fill=INK,
                       font=self.f_name)
        cv.create_text(x + 74, y + 50, text=f"{mutual} mutual contacts",
                       anchor="w", fill=MUT, font=self.f_body)
        self.stamps[rid] = (cv.create_text(x + w - 18, y + 28, text="",
                                           anchor="e", font=self.f_bold),)
        dt = cv.create_text(x + 16, y + 70, text=descriptor, anchor="nw",
                            fill=INK2, font=self.f_body, width=w - 32)
        # the ask, as a quoted note
        ay = cv.bbox(dt)[3] + 8
        at = cv.create_text(x + 28, ay, text=ask, anchor="nw", fill=INK,
                            font=self.f_ask, width=w - 44)
        cv.create_rectangle(x + 16, ay + 2, x + 19, cv.bbox(at)[3] - 2,
                            fill=CORAL, outline="")
        for j, (opt, lab) in enumerate((("accept", "Accept"),
                                        ("decline", "Decline"))):
            b = tk.Button(cv, text=lab, bg=OAT, fg=INK, font=self.f_btn,
                          activebackground=OAT_D, relief="flat", bd=0,
                          pady=5, cursor="hand2",
                          command=lambda o=opt: self.choose(rid, o))
            bx = x + 16 + j * ((w - 40) // 2 + 8)
            cv.create_window(bx, y + h - 10, window=b, anchor="sw",
                             width=(w - 40) // 2, height=32)
            self.buttons[(rid, opt)] = b

    def choose(self, rid: str, decision: str):
        if self.finished:
            return
        self.decisions[rid] = decision
        self.events.append({"event": "select", "requestId": rid,
                            "decision": decision})
        for opt, col in (("accept", TEAL), ("decline", SLATE)):
            chosen = opt == decision
            self.buttons[(rid, opt)].configure(
                bg=col if chosen else OAT, fg="white" if chosen else INK,
                activebackground=col if chosen else OAT_D,
                activeforeground="white" if chosen else INK)
        self.grid.itemconfigure(
            self.stamps[rid][0],
            text="Accepted" if decision == "accept" else "Declined",
            fill=TEAL if decision == "accept" else SLATE)
        n = len(self.decisions)
        self.rail.coords(self.prog, 34, self.foot_y + 96,
                         34 + 148 * n / len(CATALOG), self.foot_y + 104)
        remaining = len(CATALOG) - n
        if remaining:
            self.status.configure(text=f"{n} of {len(CATALOG)} decided\n"
                                       f"Decide {remaining} more")
        else:
            self.status.configure(text="All 6 decided\nReady to confirm")
            self.confirm.configure(state="normal", bg=CORAL)

    def finish(self):
        if self.finished or len(self.decisions) != len(CATALOG):
            return
        self.finished = True
        self.events.append({"event": "submit"})
        decisions = [
            {"id": rid, "name": _BY_ID[rid][1],
             "decision": self.decisions[rid]}
            for rid, *_ in CATALOG
        ]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "connections.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"submitted": True, "decisions": decisions,
                       "events": self.events}, f, ensure_ascii=False,
                      indent=2)
        for button in self.buttons.values():
            button.configure(state="disabled", cursor="arrow")
        self.confirm.configure(state="disabled", text="Confirmed")
        self.show_done(decisions)

    def show_done(self, decisions):
        cv = tk.Canvas(self.done, bg=INK, highlightthickness=0)
        cv.pack(fill="both", expand=True)
        cx = WINDOW_W // 2
        cv.create_oval(cx - 44, 170, cx + 44, 258, fill=CORAL, outline="")
        cv.create_line(cx - 20, 214, cx - 4, 230, cx + 22, 198, fill="white",
                       width=7, capstyle="round", joinstyle="round")
        cv.create_text(cx, 306, text="Responses sent", fill="white",
                       font=self.f_big)
        acc = sum(d["decision"] == "accept" for d in decisions)
        cv.create_text(cx, 346, text=f"{len(decisions)} requests answered · "
                       f"{acc} accepted · {len(decisions) - acc} declined",
                       fill="#c9bfd3", font=self.f_body)
        self.done.place(relx=0, rely=0, relwidth=1, relheight=1)


if __name__ == "__main__":
    root = tk.Tk()
    ConnectDesk(root)
    root.mainloop()
