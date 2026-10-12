#!/usr/bin/env python3
"""Pathway Grants native Tkinter application.

A scholarship foundation's desktop portal: browse the eight six-month evening
certificate awards, open a program's prospectus, select one, review and submit.
The app writes /app/output/application.json itself on submit.
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = (
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("ADHERENCE_OUTPUT_DIR")
    or "/app/output"
)

PROGRAMS = [
    {
        "id": "g01",
        "name": "Civic Path Award",
        "subject": "Project coordination certificate",
        "schedule": "Tue/Thu evenings · six months",
        "eligibility": "Applicant documentation must show current citizenship in the country, whether obtained at birth or later.",
        "status": "citizen",
    },
    {
        "id": "g02",
        "name": "Evergreen Award",
        "subject": "Digital operations certificate",
        "schedule": "Mon/Wed evenings · six months",
        "eligibility": "Applicant documentation must show indefinite authorization to reside, supported by a current permanent-resident card.",
        "status": "permanent_resident",
    },
    {
        "id": "g03",
        "name": "Bridgeway Award",
        "subject": "Business systems certificate",
        "schedule": "Tue/Thu evenings · six months",
        "eligibility": "Applicant documentation must show current citizenship, including citizenship obtained through naturalization.",
        "status": "citizen",
    },
    {
        "id": "g04",
        "name": "Atlas Award",
        "subject": "Service design certificate",
        "schedule": "Mon/Wed evenings · six months",
        "eligibility": "Applicant documentation must show indefinite resident authorization supported by a current permanent-resident card.",
        "status": "permanent_resident",
    },
    {
        "id": "g05",
        "name": "Harborlight Award",
        "subject": "Operations planning certificate",
        "schedule": "Tue/Thu evenings · six months",
        "eligibility": "Applicant documentation may be a current passport plus a valid time-limited visa authorizing residence through the course end date.",
        "status": "temporary_visa",
    },
    {
        "id": "g06",
        "name": "Keystone Award",
        "subject": "Community leadership certificate",
        "schedule": "Mon/Wed evenings · six months",
        "eligibility": "Applicant documentation must include a current national passport or certificate of citizenship issued by this country.",
        "status": "citizen",
    },
    {
        "id": "g07",
        "name": "Orchard Award",
        "subject": "Applied communications certificate",
        "schedule": "Tue/Thu evenings · six months",
        "eligibility": "Applicant documentation must show permanent authorization to remain, with no scheduled expiration date.",
        "status": "permanent_resident",
    },
    {
        "id": "g08",
        "name": "Crosswind Award",
        "subject": "Research administration certificate",
        "schedule": "Mon/Wed evenings · six months",
        "eligibility": "Applicant documentation may be a current passport together with an unexpired temporary visa permitting residence through the course end date.",
        "status": "temporary_visa",
    },
]
BY_ID = {program["id"]: program for program in PROGRAMS}

# Foundation palette: warm ivory paper, oxblood, antique gold, near-black ink.
PAPER = "#faf6ee"
SHEET = "#fffdf8"
OX = "#7a1f2b"
OX_D = "#5e1621"
GOLD = "#c9a13b"
GOLD_L = "#efe2bd"
INK = "#231c19"
MUTED = "#6e635b"
RULE = "#e2d8c6"
TILE_ON = "#f6ecd9"
W, H = 1024, 866


class PathwayApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.active_id: str | None = None
        self.selected_id: str | None = None
        self.events: list[dict[str, str]] = []
        self.tiles: dict[str, tk.Frame] = {}
        root.title("Pathway Grants")
        root.geometry("1024x866+0+0")
        root.configure(bg=PAPER)
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
        root.lift()
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))

        F = lambda fam, px, w="normal", s="roman": tkfont.Font(family=fam, size=-px, weight=w, slant=s)
        self.f_brand = F("C059", 27, "bold")
        self.f_tag = F("C059", 14, "normal", "italic")
        self.f_nav = F("Liberation Sans", 14)
        self.f_step = F("Liberation Sans", 13, "bold")
        self.f_h1 = F("C059", 25, "bold")
        self.f_h2 = F("C059", 19, "bold")
        self.f_tile = F("C059", 17, "bold")
        self.f_body = F("Liberation Sans", 14)
        self.f_small = F("Liberation Sans", 13)
        self.f_cap = F("Liberation Sans", 12, "bold")
        self.f_btn = F("Liberation Sans", 14, "bold")
        self.f_cta = F("Liberation Sans", 16, "bold")
        self.f_crest = F("C059", 18, "bold")

        self._header()
        self._stepper()
        content = tk.Frame(root, bg=PAPER)
        content.pack(fill="both", expand=True, padx=22, pady=(4, 12))
        grid = tk.Frame(content, bg=PAPER)
        grid.pack(side="left", fill="both", expand=True)
        for i, program in enumerate(PROGRAMS):
            self._tile(grid, i, program)
        for c in range(2):
            grid.grid_columnconfigure(c, weight=1, uniform="c")
        for r in range(4):
            grid.grid_rowconfigure(r, weight=1, uniform="r")
        self.detail = tk.Frame(content, bg=SHEET, width=410, highlightthickness=1,
                               highlightbackground=RULE)
        self.detail.pack(side="right", fill="y", padx=(16, 0))
        self.detail.pack_propagate(False)
        self._footer()
        self.show_placeholder()

    # ── chrome ─────────────────────────────────────────────────────────
    def _header(self) -> None:
        hd = tk.Canvas(self.root, height=78, bg=OX, highlightthickness=0)
        hd.pack(fill="x")
        # mark: gold arch gateway with a path rising through it
        x, y = 26, 13
        hd.create_oval(x, y, x + 52, y + 52, fill=OX_D, outline=GOLD, width=2)
        hd.create_arc(x + 12, y + 12, x + 40, y + 44, start=0, extent=180, style="arc",
                      outline=GOLD, width=3)
        hd.create_line(x + 12, y + 28, x + 12, y + 42, fill=GOLD, width=3)
        hd.create_line(x + 40, y + 28, x + 40, y + 42, fill=GOLD, width=3)
        hd.create_polygon(x + 20, y + 42, x + 32, y + 42, x + 28, y + 24, x + 24, y + 24,
                          fill=SHEET, outline="")
        hd.create_text(92, 30, text="Pathway Grants", anchor="w", fill="white", font=self.f_brand)
        hd.create_text(93, 56, text="Evening certificate awards · foundation portal", anchor="w",
                       fill=GOLD_L, font=self.f_tag)
        nx = 560
        for i, t in enumerate(("Awards", "My applications", "Guidance", "Contact")):
            hd.create_text(nx, 40, text=t, anchor="w", fill="white" if i == 0 else "#e3c3c7",
                           font=self.f_nav)
            if i == 0:
                hd.create_line(nx, 56, nx + self.f_nav.measure(t), 56, fill=GOLD, width=3)
            nx += self.f_nav.measure(t) + 26
        tk.Frame(self.root, bg=GOLD, height=4).pack(fill="x")

    def _stepper(self) -> None:
        bar = tk.Frame(self.root, bg=PAPER)
        bar.pack(fill="x", padx=22, pady=(12, 8))
        left = tk.Frame(bar, bg=PAPER)
        left.pack(side="left")
        tk.Label(left, text="Choose one program", bg=PAPER, fg=INK, font=self.f_h1).pack(anchor="w")
        tk.Label(left, text="Every award covers full tuition. Open a program to read its prospectus "
                            "and applicant terms.", bg=PAPER, fg=MUTED,
                 font=self.f_small).pack(anchor="w", pady=(2, 0))
        self.step_cv = tk.Canvas(bar, width=300, height=46, bg=PAPER, highlightthickness=0)
        self.step_cv.pack(side="right", anchor="s")
        self._draw_steps(0)

    def _draw_steps(self, active: int) -> None:
        cv = self.step_cv
        cv.delete("all")
        labels = ("Browse", "Review", "Submit")
        for i, t in enumerate(labels):
            cx = 30 + i * 118
            if i < 2:
                cv.create_line(cx + 14, 16, cx + 104, 16, fill=GOLD if i < active else RULE, width=3)
            on = i <= active
            cv.create_oval(cx - 13, 3, cx + 13, 29, fill=OX if on else SHEET,
                           outline=OX if on else RULE, width=2)
            cv.create_text(cx, 16, text=str(i + 1), fill="white" if on else MUTED, font=self.f_step)
            cv.create_text(cx, 39, text=t, fill=INK if on else MUTED, font=self.f_cap)

    def _footer(self) -> None:
        ft = tk.Frame(self.root, bg="#efe7d8")
        ft.pack(fill="x", side="bottom")
        tk.Label(ft, text="One application per applicant this intake  ·  Tuition paid directly to "
                          "the college  ·  Help desk weekdays 9–5",
                 bg="#efe7d8", fg=MUTED, font=self.f_small).pack(side="left", padx=22, pady=9)

    def _tile(self, grid: tk.Frame, i: int, program: dict) -> None:
        t = tk.Frame(grid, bg=SHEET, highlightthickness=2, highlightbackground=RULE)
        t.grid(row=i // 2, column=i % 2, sticky="nsew", padx=6, pady=6)
        self.tiles[program["id"]] = t
        top = tk.Frame(t, bg=SHEET)
        top.pack(fill="x", padx=14, pady=(12, 0))
        crest = tk.Canvas(top, width=38, height=38, bg=SHEET, highlightthickness=0)
        crest.pack(side="left", anchor="n")
        crest.create_oval(2, 2, 36, 36, outline=GOLD, width=2, fill=GOLD_L)
        crest.create_text(19, 20, text=program["name"][0], fill=OX, font=self.f_crest)
        txt = tk.Frame(top, bg=SHEET)
        txt.pack(side="left", fill="x", expand=True, padx=(10, 0))
        tk.Label(txt, text=program["name"], bg=SHEET, fg=INK, font=self.f_tile,
                 anchor="w").pack(fill="x")
        tk.Label(txt, text=program["subject"], bg=SHEET, fg=MUTED, font=self.f_small,
                 anchor="w", justify="left", wraplength=210).pack(fill="x")
        tk.Label(txt, text=program["schedule"], bg=SHEET, fg=INK, font=self.f_small,
                 anchor="w").pack(fill="x", pady=(8, 0))
        bot = tk.Frame(t, bg=SHEET)
        bot.pack(fill="x", side="bottom", padx=14, pady=(0, 12))
        tk.Label(bot, text=f"No. {program['id'][1:]}", bg=SHEET, fg=GOLD,
                 font=self.f_cap).pack(side="left")
        tk.Button(bot, text="Open details", bg=OX, fg="white", activebackground=OX_D,
                  activeforeground="white", font=self.f_btn, relief="flat", bd=0, padx=14,
                  pady=6, cursor="hand2",
                  command=lambda pid=program["id"]: self.show_details(pid)).pack(side="right")

    def _mark_tiles(self) -> None:
        for pid, t in self.tiles.items():
            on = pid == self.active_id
            t.configure(highlightbackground=OX if on else RULE)

    # ── detail pane ───────────────────────────────────────────────────
    def clear_detail(self) -> None:
        for child in self.detail.winfo_children():
            child.destroy()

    def _sheet_head(self, kicker: str) -> None:
        tk.Frame(self.detail, bg=OX, height=8).pack(fill="x")
        tk.Label(self.detail, text=kicker.upper(), bg=SHEET, fg=GOLD,
                 font=self.f_cap).pack(anchor="w", padx=24, pady=(20, 2))

    def show_placeholder(self) -> None:
        self.active_id = None
        self.selected_id = None
        self._mark_tiles()
        self._draw_steps(0)
        self.clear_detail()
        self._sheet_head("Prospectus")
        tk.Label(self.detail, text="Program details", bg=SHEET, fg=INK,
                 font=self.f_h1).pack(anchor="w", padx=24)
        tk.Label(self.detail, text="Select Open details on any program to read its course "
                                   "information, funding and applicant documentation here.",
                 bg=SHEET, fg=MUTED, font=self.f_body, wraplength=320,
                 justify="left").pack(anchor="w", padx=24, pady=(10, 0))
        cv = tk.Canvas(self.detail, width=360, height=220, bg=SHEET, highlightthickness=0)
        cv.pack(pady=40)
        for k in range(3):
            y = 30 + k * 60
            cv.create_rectangle(70 + k * 18, y, 290 - k * 18, y + 44, outline=RULE, width=2,
                                fill=SHEET)
            cv.create_line(90 + k * 18, y + 16, 250 - k * 18, y + 16, fill=GOLD_L, width=4)
            cv.create_line(90 + k * 18, y + 30, 210 - k * 18, y + 30, fill=RULE, width=4)

    def _section(self, title: str, text: str, bg: str = SHEET) -> None:
        tk.Label(self.detail, text=title, bg=SHEET, fg=INK, font=self.f_h2).pack(anchor="w", padx=24, pady=(14, 4))
        tk.Label(self.detail, text=text, bg=bg, fg=INK, font=self.f_body, wraplength=300,
                 justify="left", anchor="w", padx=12 if bg != SHEET else 0,
                 pady=10 if bg != SHEET else 0).pack(fill="x", padx=24)

    def show_details(self, program_id: str) -> None:
        self.active_id = program_id
        self.events.append({"event": "view_details", "programId": program_id})
        program = BY_ID[program_id]
        self._mark_tiles()
        self._draw_steps(0)
        self.clear_detail()
        self._sheet_head(f"Prospectus · No. {program_id[1:]}")
        tk.Label(self.detail, text=program["name"], bg=SHEET, fg=INK,
                 font=self.f_h1).pack(anchor="w", padx=24)
        tk.Label(self.detail, text=program["subject"], bg=SHEET, fg=OX, font=self.f_btn,
                 wraplength=320, justify="left").pack(anchor="w", padx=24, pady=(4, 0))
        tk.Frame(self.detail, bg=RULE, height=1).pack(fill="x", padx=24, pady=(12, 0))
        self._section("Schedule", program["schedule"])
        self._section("Funding", "Full tuition for the six-month certificate.")
        self._section("Applicant documentation", program["eligibility"], bg=GOLD_L)
        tk.Button(self.detail, text="Select this program", bg=OX, fg="white",
                  activebackground=OX_D, activeforeground="white", font=self.f_cta,
                  relief="flat", bd=0, padx=20, pady=11, cursor="hand2",
                  command=lambda: self.select_program(program_id)).pack(anchor="w", padx=24, pady=(22, 0))

    def select_program(self, program_id: str) -> None:
        self.selected_id = program_id
        self.events.append({"event": "select_program", "programId": program_id})
        program = BY_ID[program_id]
        self._draw_steps(1)
        self.clear_detail()
        self._sheet_head("Review application")
        tk.Label(self.detail, text="Review and submit", bg=SHEET, fg=INK,
                 font=self.f_h1).pack(anchor="w", padx=24)
        box = tk.Frame(self.detail, bg=TILE_ON, highlightthickness=1, highlightbackground=GOLD)
        box.pack(fill="x", padx=24, pady=(16, 0))
        tk.Label(box, text="SELECTED PROGRAM", bg=TILE_ON, fg=GOLD, font=self.f_cap).pack(anchor="w", padx=14, pady=(12, 0))
        tk.Label(box, text=f"Selected program: {program['name']}", bg=TILE_ON, fg=INK,
                 font=self.f_h2, wraplength=300, justify="left").pack(anchor="w", padx=14)
        tk.Label(box, text=f"{program['subject']} · {program['schedule']}", bg=TILE_ON, fg=MUTED,
                 font=self.f_small, wraplength=300, justify="left").pack(anchor="w", padx=14, pady=(2, 12))
        tk.Label(self.detail, text="Confirm that you meet the applicant terms shown in the program details.",
                 bg=SHEET, fg=MUTED, font=self.f_body, wraplength=320,
                 justify="left").pack(anchor="w", padx=24, pady=(16, 22))
        tk.Button(self.detail, text="Submit application", bg=OX, fg="white", activebackground=OX_D,
                  activeforeground="white", font=self.f_cta, relief="flat", bd=0, padx=22, pady=12,
                  cursor="hand2", command=self.submit).pack(anchor="w", padx=24)
        tk.Button(self.detail, text="Choose another program", bg=SHEET, fg=OX, activebackground=TILE_ON,
                  font=self.f_btn, relief="flat", bd=0, highlightthickness=1, padx=16, pady=8,
                  cursor="hand2", command=self.show_placeholder).pack(anchor="w", padx=24, pady=14)

    def submit(self) -> None:
        if self.selected_id is None:
            return
        program = BY_ID[self.selected_id]
        self.events.append({"event": "submit_application", "programId": self.selected_id})
        artifact = {
            "state": "submitted",
            "selectedProgram": {
                "id": program["id"],
                "name": program["name"],
                "eligibilityGroup": program["status"],
            },
            "events": self.events,
        }
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "application.json"), "w", encoding="utf-8") as handle:
            json.dump(artifact, handle, ensure_ascii=False, indent=2)
        self._draw_steps(2)
        ov = tk.Frame(self.root, bg=PAPER)
        ov.place(relx=0, rely=0, relwidth=1, relheight=1)
        card = tk.Frame(ov, bg=SHEET, highlightthickness=1, highlightbackground=RULE)
        card.place(relx=0.5, rely=0.45, anchor="center", width=560, height=290)
        tk.Frame(card, bg=OX, height=10).pack(fill="x")
        tk.Label(card, text="✓", bg=SHEET, fg=GOLD, font=self.f_h1).pack(pady=(30, 0))
        tk.Label(card, text="Application submitted", bg=SHEET, fg=OX, font=self.f_h1).pack(pady=(4, 8))
        tk.Label(card, text=program["name"], bg=SHEET, fg=INK, font=self.f_h2).pack()
        tk.Label(card, text=f"Reference PG-{program['id'].upper()}-{len(self.events):02d}",
                 bg=SHEET, fg=MUTED, font=self.f_body).pack(pady=(6, 0))
        tk.Label(card, text="The foundation will be in touch by email about next steps.",
                 bg=SHEET, fg=MUTED, font=self.f_body).pack(pady=(16, 0))


if __name__ == "__main__":
    root = tk.Tk()
    PathwayApp(root)
    root.mainloop()
