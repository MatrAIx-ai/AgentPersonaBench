#!/usr/bin/env python3
"""SkillLab — new-starter equipment onboarding desk (stdlib Tk)."""

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
        "Camera gimbal setup",
        (
            ("q1a", "Fixed 45-minute lab — mount and balance a camera yourself with live prompts"),
            ("q1b", "20-minute searchable handbook now, with balance diagrams and setup examples"),
            ("q1c", "On-demand recorded demo with replayable chapters"),
            ("q1d", "Downloadable audio walkthrough for the commute"),
        ),
    ),
    (
        "q2",
        "Music synthesizer",
        (
            ("q2a", "30-minute reference lesson now with searchable diagrams and sound examples"),
            ("q2b", "On-demand video demonstration with replayable chapters"),
            ("q2c", "Fixed 45-minute interactive patch lab this afternoon — turn the controls yourself"),
            ("q2d", "Downloadable audio lecture describing the controls"),
        ),
    ),
    (
        "q3",
        "Shipping-label printer",
        (
            ("q3a", "20-minute searchable guide anytime, with setup diagrams and error tables"),
            ("q3b", "Fixed 35-minute station — load a roll, correct errors, print a label"),
            ("q3c", "Concise setup video with pause and replay"),
            ("q3d", "Downloadable spoken setup lesson for the commute"),
        ),
    ),
)

# palette: slate rail, porcelain page, apricot accent
RAIL = "#243241"
RAIL_HI = "#34475b"
PAGE = "#eef1f4"
CARD = "#ffffff"
LINE = "#d3dae2"
INK = "#1b2733"
MUTED = "#5d6b79"
ACCENT = "#e8894a"
ACCENT_DK = "#b8612a"
ACCENT_BG = "#fdf0e6"
OK = "#2e7d5b"
SANS = "Nimbus Sans"
HEAD = "URW Gothic"

ASSET_TAGS = ("EQ-0412", "EQ-0977", "EQ-1530")


class SkillLab:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.selected: dict[str, str] = {}
        self.events: list[dict[str, str]] = []
        self.finished = False
        self.step = 0  # 0..2 = tools, 3 = review
        root.title("SkillLab")
        root.geometry("1024x866+0+0")
        root.resizable(False, False)
        root.configure(bg=PAGE)

        self.rail = tk.Frame(root, bg=RAIL, width=248)
        self.rail.pack(side="left", fill="y")
        self.rail.pack_propagate(False)
        self.main = tk.Frame(root, bg=PAGE)
        self.main.pack(side="left", fill="both", expand=True)
        self._build_rail()
        self.render()

    # ------------------------------------------------------------------ rail
    def _build_rail(self) -> None:
        logo = tk.Canvas(self.rail, width=248, height=96, bg=RAIL, highlightthickness=0)
        logo.pack(fill="x")
        # mark: three interlocking hexagon cells
        import math

        def hexa(cx, cy, r, fill, outline):
            pts = []
            for k in range(6):
                a = math.radians(60 * k + 30)
                pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
            logo.create_polygon(pts, fill=fill, outline=outline, width=2)

        hexa(38, 40, 14, ACCENT, ACCENT)
        hexa(62, 40, 14, "", "#9fb3c7")
        hexa(50, 61, 14, "", "#9fb3c7")
        logo.create_text(88, 40, text="Skill", anchor="w", fill="white", font=(HEAD, 22, "bold"))
        import tkinter.font as tkfont
        skill_w = tkfont.Font(family=HEAD, size=22, weight="bold").measure("Skill")
        logo.create_text(88 + skill_w + 1, 40, text="Lab", anchor="w", fill=ACCENT, font=(HEAD, 22, "bold"))
        logo.create_text(89, 64, text="Equipment onboarding", anchor="w", fill="#9fb3c7", font=(SANS, 11))

        tk.Frame(self.rail, bg=RAIL_HI, height=1).pack(fill="x", padx=20, pady=(4, 14))
        tk.Label(self.rail, text="YOUR ONBOARDING", bg=RAIL, fg="#8da2b6",
                 font=(SANS, 10, "bold")).pack(anchor="w", padx=22)
        self.step_rows: list[tuple[tk.Frame, tk.Label, tk.Label, tk.Label]] = []
        for idx, (qid, prompt, _) in enumerate(QUESTIONS):
            row = tk.Frame(self.rail, bg=RAIL, cursor="hand2")
            row.pack(fill="x", padx=12, pady=3)
            num = tk.Label(row, text=str(idx + 1), width=2, bg=RAIL_HI, fg="white",
                           font=(SANS, 12, "bold"), pady=6)
            num.pack(side="left", padx=(8, 10), pady=8)
            box = tk.Frame(row, bg=RAIL)
            box.pack(side="left", fill="x", expand=True)
            title = tk.Label(box, text=prompt, bg=RAIL, fg="white", font=(SANS, 12, "bold"), anchor="w")
            title.pack(fill="x")
            sub = tk.Label(box, text="Not chosen yet", bg=RAIL, fg="#8da2b6", font=(SANS, 10), anchor="w")
            sub.pack(fill="x")
            for w in (row, num, box, title, sub):
                w.bind("<Button-1>", lambda _e, s=idx: self.goto(s))
            self.step_rows.append((row, num, title, sub))
        row = tk.Frame(self.rail, bg=RAIL, cursor="hand2")
        row.pack(fill="x", padx=12, pady=3)
        num = tk.Label(row, text=str(len(QUESTIONS) + 1), width=2, bg=RAIL_HI, fg="white", font=(SANS, 12, "bold"), pady=6)
        num.pack(side="left", padx=(8, 10), pady=8)
        box = tk.Frame(row, bg=RAIL)
        box.pack(side="left", fill="x", expand=True)
        title = tk.Label(box, text="Review & confirm", bg=RAIL, fg="white", font=(SANS, 12, "bold"), anchor="w")
        title.pack(fill="x")
        sub = tk.Label(box, text="Check your three paths", bg=RAIL, fg="#8da2b6", font=(SANS, 10), anchor="w")
        sub.pack(fill="x")
        for w in (row, num, box, title, sub):
            w.bind("<Button-1>", lambda _e: self.goto(3))
        self.step_rows.append((row, num, title, sub))

        foot = tk.Frame(self.rail, bg=RAIL)
        foot.pack(side="bottom", fill="x", padx=22, pady=22)
        tk.Label(foot, text="Onboarding desk", bg=RAIL, fg="white", font=(SANS, 11, "bold"),
                 anchor="w").pack(fill="x")
        tk.Label(foot, text="Level 2 · Equipment room B\nMon–Fri 08:30–17:00\nExt. 4410",
                 bg=RAIL, fg="#8da2b6", font=(SANS, 10), justify="left", anchor="w").pack(fill="x", pady=(2, 0))

    def _refresh_rail(self) -> None:
        for idx, (row, num, title, sub) in enumerate(self.step_rows):
            active = idx == self.step
            bg = RAIL_HI if active else RAIL
            for w in (row, title, sub):
                w.configure(bg=bg)
            title.master.configure(bg=bg)
            if idx < len(QUESTIONS):
                qid = QUESTIONS[idx][0]
                done = qid in self.selected
                if done:
                    letter = "ABCD"[[o for o, _ in QUESTIONS[idx][2]].index(self.selected[qid])]
                    sub.configure(text=f"Path {letter} chosen")
                else:
                    sub.configure(text="Not chosen yet")
                num.configure(bg=ACCENT if done else ("#4b6178" if active else RAIL_HI),
                              text="✓" if done else str(idx + 1))
            else:
                num.configure(bg=OK if self.finished else ("#4b6178" if active else RAIL_HI))

    # ------------------------------------------------------------------ main
    def goto(self, step: int) -> None:
        if self.finished:
            return
        self.step = step
        self.render()

    def _clear(self) -> None:
        for w in self.main.winfo_children():
            w.destroy()

    def _topbar(self, crumb: str) -> None:
        bar = tk.Frame(self.main, bg=CARD, height=58, highlightthickness=1, highlightbackground=LINE)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text=crumb, bg=CARD, fg=MUTED, font=(SANS, 11)).pack(side="left", padx=28)
        tk.Label(bar, text="New starter · Week 1", bg=CARD, fg=INK, font=(SANS, 11, "bold")).pack(side="right", padx=28)
        av = tk.Canvas(bar, width=34, height=34, bg=CARD, highlightthickness=0)
        av.pack(side="right")
        av.create_oval(2, 2, 32, 32, fill="#d9e2ea", outline="")
        av.create_oval(12, 8, 22, 18, fill="#8da2b6", outline="")
        av.create_arc(7, 18, 27, 38, start=0, extent=180, fill="#8da2b6", outline="")

    def render(self) -> None:
        self._clear()
        self._refresh_rail()
        if self.step < len(QUESTIONS):
            self._render_tool(self.step)
        else:
            self._render_review()

    def _render_tool(self, idx: int) -> None:
        qid, prompt, options = QUESTIONS[idx]
        self._topbar(f"Onboarding  ›  Tool {idx + 1} of {len(QUESTIONS)}")
        body = tk.Frame(self.main, bg=PAGE, padx=36, pady=22)
        body.pack(fill="both", expand=True)
        head = tk.Frame(body, bg=PAGE)
        head.pack(fill="x")
        tk.Label(head, text=f"TOOL {idx + 1} OF {len(QUESTIONS)}  ·  ASSET {ASSET_TAGS[idx]}", bg=PAGE, fg=ACCENT_DK,
                 font=(SANS, 10, "bold")).pack(anchor="w")
        tk.Label(head, text=prompt, bg=PAGE, fg=INK, font=(HEAD, 26, "bold")).pack(anchor="w", pady=(2, 2))
        tk.Label(head, text="Pick one onboarding path for this tool. Every path covers the same material "
                 "and ends with the same sign-off.", bg=PAGE, fg=MUTED, font=(SANS, 12),
                 wraplength=700, justify="left").pack(anchor="w", pady=(0, 16))

        chosen = self.selected.get(qid)
        for pos, (oid, text) in enumerate(options):
            is_on = oid == chosen
            card = tk.Frame(body, bg=ACCENT_BG if is_on else CARD, highlightthickness=2,
                            highlightbackground=ACCENT if is_on else LINE, cursor="hand2")
            card.pack(fill="x", pady=6)
            inner = tk.Frame(card, bg=card["bg"], padx=16, pady=14)
            inner.pack(fill="x")
            badge = tk.Canvas(inner, width=44, height=44, bg=card["bg"], highlightthickness=0)
            badge.pack(side="left", padx=(0, 16))
            badge.create_oval(2, 2, 42, 42, fill=ACCENT if is_on else "#e6ebf0", outline="")
            badge.create_text(22, 22, text="ABCD"[pos], fill="white" if is_on else INK, font=(SANS, 15, "bold"))
            txt = tk.Frame(inner, bg=card["bg"])
            txt.pack(side="left", fill="x", expand=True)
            tk.Label(txt, text=f"Path {'ABCD'[pos]}", bg=card["bg"], fg=MUTED, font=(SANS, 10, "bold"),
                     anchor="w").pack(fill="x")
            tk.Label(txt, text=text, bg=card["bg"], fg=INK, font=(SANS, 13), anchor="w", justify="left",
                     wraplength=450).pack(fill="x", pady=(2, 0))
            btn = tk.Button(inner, text="Selected ✓" if is_on else "Choose path",
                            command=lambda q=qid, o=oid: self.choose(q, o),
                            bg=ACCENT if is_on else "#e6ebf0", fg="white" if is_on else INK,
                            activebackground=ACCENT_DK, activeforeground="white", relief="flat", bd=0,
                            width=11, pady=8, font=(SANS, 11, "bold"), cursor="hand2")
            btn.pack(side="right", padx=(12, 0), before=txt)
            for w in (card, inner, badge, txt) + tuple(txt.winfo_children()):
                w.bind("<Button-1>", lambda _e, q=qid, o=oid: self.choose(q, o))

        nav = tk.Frame(body, bg=PAGE)
        nav.pack(side="bottom", fill="x")
        if idx > 0:
            tk.Button(nav, text="‹ Previous tool", command=lambda: self.goto(idx - 1), bg=PAGE, fg=INK,
                      activebackground=LINE, relief="flat", bd=0, padx=14, pady=10,
                      font=(SANS, 12), cursor="hand2").pack(side="left")
        nxt = "Next tool ›" if idx < len(QUESTIONS) - 1 else "Review choices ›"
        tk.Button(nav, text=nxt, command=lambda: self.goto(idx + 1), bg=RAIL, fg="white",
                  activebackground=RAIL_HI, activeforeground="white", relief="flat", bd=0, padx=22, pady=10,
                  font=(SANS, 12, "bold"), cursor="hand2").pack(side="right")
        self.status = tk.Label(nav, text=self._remaining_text(), bg=PAGE, fg=MUTED, font=(SANS, 11))
        self.status.pack(side="right", padx=16)

    def _remaining_text(self) -> str:
        left = len(QUESTIONS) - len(self.selected)
        return f"Choose {left} more" if left else "All tools chosen"

    def _render_review(self) -> None:
        self._topbar("Onboarding  ›  Review & confirm")
        body = tk.Frame(self.main, bg=PAGE, padx=36, pady=22)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="REVIEW", bg=PAGE, fg=ACCENT_DK, font=(SANS, 10, "bold")).pack(anchor="w")
        tk.Label(body, text="Your onboarding plan", bg=PAGE, fg=INK, font=(HEAD, 26, "bold")).pack(anchor="w", pady=(2, 2))
        tk.Label(body, text="Check the path you picked for each tool, then confirm to send it to the onboarding desk.",
                 bg=PAGE, fg=MUTED, font=(SANS, 12), wraplength=700, justify="left").pack(anchor="w", pady=(0, 16))
        for idx, (qid, prompt, options) in enumerate(QUESTIONS):
            card = tk.Frame(body, bg=CARD, highlightthickness=1, highlightbackground=LINE, padx=18, pady=14)
            card.pack(fill="x", pady=6)
            top = tk.Frame(card, bg=CARD)
            top.pack(fill="x")
            tk.Label(top, text=f"{idx + 1}. {prompt}", bg=CARD, fg=INK, font=(SANS, 13, "bold")).pack(side="left")
            if not self.finished:
                tk.Button(top, text=f"Change tool {idx + 1}", command=lambda s=idx: self.goto(s), bg="#e6ebf0",
                          fg=INK, activebackground=LINE, relief="flat", bd=0, padx=12, pady=6,
                          font=(SANS, 11), cursor="hand2").pack(side="right")
            oid = self.selected.get(qid)
            if oid:
                pos = [o for o, _ in options].index(oid)
                text = f"Path {'ABCD'[pos]}:  {options[pos][1]}"
                fg = INK
            else:
                text, fg = "No path chosen yet", ACCENT_DK
            tk.Label(card, text=text, bg=CARD, fg=fg, font=(SANS, 12), wraplength=620, justify="left",
                     anchor="w").pack(fill="x", pady=(8, 0))

        foot = tk.Frame(body, bg=PAGE)
        foot.pack(side="bottom", fill="x")
        ready = len(self.selected) == len(QUESTIONS)
        if self.finished:
            label, bg, state = "CHOICES CONFIRMED", OK, "disabled"
        else:
            label, bg, state = "CONFIRM CHOICES", ACCENT if ready else "#c3ccd5", "normal" if ready else "disabled"
        self.submit = tk.Button(foot, text=label, command=self.finish, state=state, bg=bg, fg="white",
                                disabledforeground="white" if self.finished else "#eef1f4",
                                activebackground=ACCENT_DK, activeforeground="white", relief="flat", bd=0,
                                padx=28, pady=13, font=(SANS, 13, "bold"), cursor="hand2")
        self.submit.pack(side="right")
        if self.finished:
            msg, col = "Saved — the onboarding desk has your plan.", OK
        else:
            msg, col = (("Ready to confirm", OK) if ready else (self._remaining_text(), MUTED))
        self.status = tk.Label(foot, text=msg, bg=PAGE, fg=col, font=(SANS, 12))
        self.status.pack(side="right", padx=16)

    # ---------------------------------------------------------------- logic
    def choose(self, qid: str, oid: str) -> None:
        if self.finished:
            return
        self.selected[qid] = oid
        self.events.append({"event": "select", "questionId": qid, "optionId": oid})
        self.render()

    def finish(self) -> None:
        if self.finished or len(self.selected) != len(QUESTIONS):
            return
        self.finished = True
        self.events.append({"event": "submit"})
        answers = [{"questionId": qid, "optionId": self.selected[qid]} for qid, _, _ in QUESTIONS]
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "selection.json"), "w", encoding="utf-8") as handle:
            json.dump({"submitted": True, "answers": answers, "events": self.events}, handle,
                      ensure_ascii=False, indent=2)
        self.render()


if __name__ == "__main__":
    window = tk.Tk()
    SkillLab(window)
    window.mainloop()
