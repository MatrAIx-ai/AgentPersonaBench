#!/usr/bin/env python3
"""ReplyDesk: a response-queue console for contacts who are waiting on you."""

from __future__ import annotations

import json
import os
import tkinter as tk

OUTPUT_DIR = (
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("ADHERENCE_OUTPUT_DIR")
    or "/app/output"
)
QUESTIONS = (
    (
        "q1",
        "Routine appointment confirmation",
        (
            ("q1a", "Make a two-minute call and confirm the address immediately"),
            ("q1b", "Complete a six-field secure text form for confirmation tomorrow"),
            ("q1c", "Start a video call"),
            ("q1d", "Record a voice reply"),
        ),
    ),
    (
        "q2",
        "Repair appointment voicemail",
        (
            ("q2a", "Call back"),
            ("q2b", "Start a video call"),
            ("q2c", "Use the appointment message thread"),
            ("q2d", "Record a voice reply"),
        ),
    ),
    (
        "q3",
        "Project update voicemail",
        (
            ("q3a", "Post a written project update"),
            ("q3b", "Call back"),
            ("q3c", "Start a video call"),
            ("q3d", "Record a voice reply"),
        ),
    ),
)

# Palette: harbour navy chrome, cool fog page, citron accent.
NAVY = "#1b2a3a"
NAVY_2 = "#26384b"
FOG = "#eef1f4"
PAPER = "#ffffff"
LINE = "#d5dbe2"
INK = "#15202b"
MUTED = "#617080"
CITRON = "#c8dc4f"
CITRON_DARK = "#5d6b12"
CITRON_PALE = "#f4f8dc"
SKY = "#9fb4c8"
FONT = "Nimbus Sans"
AVATAR_TONES = ("#7f93a8", "#8a8f9e", "#7d9a97")  # seeded by queue position only


class ChoiceApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected: dict[str, str] = {}
        self.events: list[dict[str, str]] = []
        self.finished = False
        self.current = 0
        self.tiles: dict[str, tuple[tk.Frame, list[tk.Widget], tk.Canvas]] = {}
        self.queue_rows: list[tuple[tk.Frame, tk.Label, tk.Label, tk.Canvas]] = []
        root.title("ReplyDesk")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=FOG)
        self._header()
        body = tk.Frame(root, bg=FOG)
        body.pack(fill="both", expand=True, padx=22, pady=(18, 18))
        self._queue(body)
        self.detail = tk.Frame(body, bg=FOG)
        self.detail.pack(side="left", fill="both", expand=True, padx=(18, 0))
        self._detail_shell()
        self.show(0)

    # ------------------------------------------------------------------ chrome
    def _header(self) -> None:
        bar = tk.Frame(self.root, bg=NAVY, height=64)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        mark = tk.Canvas(bar, width=44, height=44, bg=NAVY, highlightthickness=0)
        mark.pack(side="left", padx=(22, 10), pady=10)
        # Drawn mark: an in-tray with a returning arrow.
        mark.create_rectangle(4, 18, 40, 40, fill=NAVY_2, outline=CITRON, width=2)
        mark.create_line(4, 28, 14, 28, 17, 33, 27, 33, 30, 28, 40, 28, fill=CITRON, width=2)
        mark.create_line(28, 12, 14, 12, fill="white", width=3)
        mark.create_polygon(14, 5, 5, 12, 14, 19, fill="white", outline="")
        words = tk.Frame(bar, bg=NAVY)
        words.pack(side="left")
        tk.Label(words, text="Reply", bg=NAVY, fg="white", font=(FONT, 20, "bold")).pack(side="left")
        tk.Label(words, text="Desk", bg=NAVY, fg=CITRON, font=(FONT, 20)).pack(side="left")
        for name in ("Help", "Settings", "Queue"):
            tk.Label(bar, text=name, bg=NAVY, fg=SKY if name != "Queue" else "white",
                     font=(FONT, 12, "bold" if name == "Queue" else "normal")).pack(side="right", padx=14)
        chip = tk.Label(bar, text="  Shift: today  ", bg=NAVY_2, fg="#dfe7ef", font=(FONT, 12))
        chip.pack(side="right", padx=(0, 18), ipady=4)

    def _queue(self, body: tk.Frame) -> None:
        panel = tk.Frame(body, bg=PAPER, width=292, highlightthickness=1, highlightbackground=LINE)
        panel.pack(side="left", fill="y")
        panel.pack_propagate(False)
        tk.Label(panel, text="WAITING FOR YOU", bg=PAPER, fg=MUTED,
                 font=(FONT, 12, "bold")).pack(anchor="w", padx=18, pady=(18, 2))
        tk.Label(panel, text=f"{len(QUESTIONS)} contacts in your queue", bg=PAPER, fg=INK,
                 font=(FONT, 15, "bold")).pack(anchor="w", padx=18, pady=(0, 12))
        for index, (_qid, prompt, _opts) in enumerate(QUESTIONS):
            row = tk.Frame(panel, bg=PAPER, height=78, cursor="hand2")
            row.pack(fill="x", padx=10, pady=3)
            row.pack_propagate(False)
            avatar = tk.Canvas(row, width=40, height=40, bg=PAPER, highlightthickness=0, cursor="hand2")
            avatar.place(x=10, y=19)
            avatar.create_oval(2, 2, 38, 38, fill=AVATAR_TONES[index], outline="")
            avatar.create_text(20, 20, text=str(index + 1), fill="white", font=(FONT, 14, "bold"))
            title = tk.Label(row, text=prompt, bg=PAPER, fg=INK, font=(FONT, 13, "bold"),
                             anchor="w", justify="left", wraplength=196, cursor="hand2")
            title.place(x=60, y=12)
            state = tk.Label(row, text="Waiting · no reply chosen", bg=PAPER, fg=MUTED,
                             font=(FONT, 12), anchor="w", cursor="hand2")
            state.place(x=60, y=50)
            for widget in (row, avatar, title, state):
                widget.bind("<Button-1>", lambda _e, i=index: self.show(i))
            self.queue_rows.append((row, title, state, avatar))
        tk.Frame(panel, bg=LINE, height=1).pack(fill="x", padx=18, pady=(16, 12))
        tk.Label(panel, text="Every reply option reaches the same person immediately.",
                 bg=PAPER, fg=MUTED, font=(FONT, 12), justify="left", wraplength=250,
                 anchor="w").pack(anchor="w", fill="x", padx=18)
        foot = tk.Frame(panel, bg=PAPER)
        foot.pack(side="bottom", fill="x", padx=18, pady=18)
        self.status = tk.Label(foot, text=f"Choose {len(QUESTIONS)} more", bg=PAPER, fg=MUTED,
                               font=(FONT, 12, "bold"))
        self.status.pack(anchor="w", pady=(0, 8))
        self.submit = tk.Button(
            foot, text="CONFIRM CHOICES", command=self.finish, state="disabled",
            bg="#c9ced4", fg=NAVY, disabledforeground="#8993a0", activebackground=CITRON,
            activeforeground=NAVY, relief="flat", bd=0, pady=12, font=(FONT, 13, "bold"),
            cursor="hand2",
        )
        self.submit.pack(fill="x")

    def _detail_shell(self) -> None:
        top = tk.Frame(self.detail, bg=FOG)
        top.pack(fill="x")
        self.crumb = tk.Label(top, text="", bg=FOG, fg=MUTED, font=(FONT, 12, "bold"))
        self.crumb.pack(anchor="w")
        self.heading = tk.Label(top, text="", bg=FOG, fg=INK, font=(FONT, 22, "bold"),
                                anchor="w", justify="left", wraplength=640)
        self.heading.pack(anchor="w", pady=(4, 2))
        tk.Label(top, text="Choose how you will respond. Pick one reply method below.",
                 bg=FOG, fg=MUTED, font=(FONT, 13)).pack(anchor="w", pady=(0, 14))
        # Message bubble placeholder describing the waiting item (neutral copy).
        self.bubble = tk.Canvas(self.detail, height=86, bg=FOG, highlightthickness=0)
        self.bubble.pack(fill="x", pady=(0, 16))
        self.grid = tk.Frame(self.detail, bg=FOG)
        self.grid.pack(fill="x")
        nav = tk.Frame(self.detail, bg=FOG)
        nav.pack(fill="x", pady=(20, 0))
        self.prev_btn = tk.Button(nav, text="‹ Previous contact", command=lambda: self.show(self.current - 1),
                                  bg=FOG, fg=INK, activebackground=LINE, relief="flat", bd=0,
                                  font=(FONT, 13), padx=12, pady=9, cursor="hand2",
                                  highlightthickness=1, highlightbackground=LINE)
        self.prev_btn.pack(side="left")
        self.next_btn = tk.Button(nav, text="Next contact ›", command=lambda: self.show(self.current + 1),
                                  bg=NAVY, fg="white", activebackground=NAVY_2, activeforeground="white",
                                  relief="flat", bd=0, font=(FONT, 13, "bold"), padx=18, pady=9,
                                  cursor="hand2")
        self.next_btn.pack(side="right")
        tip = tk.Frame(self.detail, bg="#e3e8ee")
        tip.pack(fill="x", side="bottom")
        tk.Label(tip, text="Tip: click a reply card to choose it. You can change any choice until you confirm the queue.",
                 bg="#e3e8ee", fg=MUTED, font=(FONT, 12), wraplength=620, justify="left").pack(anchor="w", padx=16, pady=12)

    # ------------------------------------------------------------------ views
    def show(self, index: int) -> None:
        if not 0 <= index < len(QUESTIONS):
            return
        self.current = index
        qid, prompt, options = QUESTIONS[index]
        self.crumb.configure(text=f"QUEUE  ›  CONTACT {index + 1} OF {len(QUESTIONS)}")
        self.heading.configure(text=prompt)
        self.bubble.delete("all")
        self.bubble.update_idletasks()
        width = max(self.bubble.winfo_width(), 660)
        self.bubble.create_oval(0, 20, 44, 64, fill=AVATAR_TONES[index], outline="")
        self.bubble.create_text(22, 42, text=str(index + 1), fill="white", font=(FONT, 15, "bold"))
        self.bubble.create_rectangle(60, 6, width - 4, 80, fill=PAPER, outline=LINE)
        self.bubble.create_polygon(60, 34, 50, 42, 60, 50, fill=PAPER, outline=LINE)
        self.bubble.create_line(60, 35, 60, 49, fill=PAPER, width=2)
        self.bubble.create_text(78, 28, anchor="w", text=prompt, fill=INK, font=(FONT, 14, "bold"))
        self.bubble.create_text(78, 56, anchor="w", fill=MUTED, font=(FONT, 12),
                                text="This contact is waiting for your response.")
        for child in self.grid.winfo_children():
            child.destroy()
        self.tiles = {}
        for position, (oid, label) in enumerate(options):
            tile = tk.Frame(self.grid, bg=PAPER, height=136, cursor="hand2",
                            highlightthickness=2, highlightbackground=LINE)
            tile.grid(row=position // 2, column=position % 2, sticky="nsew",
                      padx=(0 if position % 2 == 0 else 8, 0 if position % 2 else 8), pady=8)
            tile.grid_propagate(False)
            tile.pack_propagate(False)
            badge = tk.Canvas(tile, width=36, height=36, bg=PAPER, highlightthickness=0, cursor="hand2")
            badge.place(x=16, y=16)
            ring = tk.Canvas(tile, width=26, height=26, bg=PAPER, highlightthickness=0, cursor="hand2")
            ring.place(relx=1.0, x=-40, y=20)
            text = tk.Label(tile, text=label, bg=PAPER, fg=INK, font=(FONT, 13), anchor="nw",
                            justify="left", wraplength=200, cursor="hand2")
            text.place(x=64, y=20)
            hint = tk.Label(tile, text="Select this reply", bg=PAPER, fg=MUTED, font=(FONT, 12),
                            cursor="hand2")
            hint.place(x=64, rely=1.0, y=-32)
            parts: list[tk.Widget] = [tile, badge, ring, text, hint]
            for widget in parts:
                widget.bind("<Button-1>", lambda _e, q=qid, o=oid: self.choose(q, o))
            badge.create_oval(1, 1, 35, 35, fill=FOG, outline=LINE)
            badge.create_text(18, 18, text="ABCD"[position], fill=NAVY, font=(FONT, 13, "bold"))
            self.tiles[oid] = (tile, parts, ring)
            self.grid.grid_columnconfigure(position % 2, weight=1, uniform="tiles")
        self.prev_btn.configure(state="normal" if index > 0 else "disabled")
        self.next_btn.configure(state="normal" if index < len(QUESTIONS) - 1 else "disabled",
                                bg=NAVY if index < len(QUESTIONS) - 1 else "#c9ced4")
        self._paint()

    def _paint(self) -> None:
        qid = QUESTIONS[self.current][0]
        chosen = self.selected.get(qid)
        for oid, (tile, parts, ring) in self.tiles.items():
            on = oid == chosen
            bg = CITRON_PALE if on else PAPER
            tile.configure(bg=bg, highlightbackground=CITRON_DARK if on else LINE)
            for widget in parts[1:]:
                widget.configure(bg=bg)
            parts[4].configure(text="Chosen reply" if on else "Select this reply",
                               fg=CITRON_DARK if on else MUTED)
            ring.delete("all")
            ring.create_oval(2, 2, 24, 24, outline=CITRON_DARK if on else "#a7b1bc", width=2,
                             fill=CITRON if on else bg)
            if on:
                ring.create_line(7, 13, 11, 18, 19, 8, fill=NAVY, width=2)
        for index, (row, title, state, avatar) in enumerate(self.queue_rows):
            active = index == self.current
            bg = "#e7edf3" if active else PAPER
            for widget in (row, title, state, avatar):
                widget.configure(bg=bg)
            done = QUESTIONS[index][0] in self.selected
            state.configure(text="Reply chosen" if done else "Waiting · no reply chosen",
                            fg=CITRON_DARK if done else MUTED)

    # ------------------------------------------------------------------ actions
    def choose(self, qid: str, oid: str) -> None:
        if self.finished:
            return
        self.selected[qid] = oid
        self.events.append({"event": "select", "questionId": qid, "optionId": oid})
        self._paint()
        remaining = len(QUESTIONS) - len(self.selected)
        if remaining:
            self.status.configure(text=f"Choose {remaining} more", fg=MUTED)
        else:
            self.status.configure(text="Ready to confirm", fg=CITRON_DARK)
            self.submit.configure(state="normal", bg=CITRON)

    def finish(self) -> None:
        if self.finished or len(self.selected) != len(QUESTIONS):
            return
        self.finished = True
        self.events.append({"event": "submit"})
        answers = [
            {"questionId": qid, "optionId": self.selected[qid]}
            for qid, _, _ in QUESTIONS
        ]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(
            os.path.join(OUTPUT_DIR, "selection.json"), "w", encoding="utf-8"
        ) as handle:
            json.dump(
                {"submitted": True, "answers": answers, "events": self.events},
                handle,
                ensure_ascii=False,
                indent=2,
            )
        for _tile, parts, _ring in self.tiles.values():
            for widget in parts:
                widget.configure(cursor="arrow")
        self.submit.configure(state="disabled", text="CHOICES CONFIRMED", bg=CITRON,
                              disabledforeground=NAVY)
        self.status.configure(text="Saved", fg=CITRON_DARK)


if __name__ == "__main__":
    window = tk.Tk()
    ChoiceApp(window)
    window.mainloop()
