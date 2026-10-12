#!/usr/bin/env python3
"""CodeDesk, a native implementation-review application.

A reviewer works through a queue of maintenance tickets. Each ticket carries a
set of functionally equivalent patch proposals; the reviewer approves one per
ticket and submits the batch. The app writes reviews.json to the output dir.

Run: ADHERENCE_OUTPUT_DIR=/app/output python3 app.py
"""

from __future__ import annotations

import json
import os
import zlib
import tkinter as tk
from tkinter import font as tkfont


OUTPUT_DIR = (
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("ADHERENCE_OUTPUT_DIR")
    or "/logs/artifacts"
)

TICKETS = [
    {
        "id": "a1",
        "title": "Retention export builder",
        "summary": "Validate accounts, apply retention rules, group records, redact fields, calculate totals, and render an export manifest.",
        "options": [
            ("a1p1", "Patch Atlas", "Four collaborating classes divide loading, policy, aggregation, and rendering.", "Longest method: 36 lines · 12 methods"),
            ("a1p2", "Patch Beacon", "A coordinator delegates the phases to nine focused helpers; reviewers follow shared workflow state across the calls.", "Primary: build_retention_export — 24 lines · helpers: 7–23 lines · 9 call jumps"),
            ("a1p3", "Patch Cobalt", "The complete ordered workflow stays in the existing entry function, with local state readable top to bottom.", "Primary: build_retention_export — 123 lines · no helpers added · 0 call jumps"),
            ("a1p4", "Patch Delta", "A generic executor applies a declarative collection of policy and output stages.", "Primary: execute_export — 30 lines · 11 registered stages"),
        ],
    },
    {
        "id": "a2",
        "title": "Incident digest generator",
        "summary": "Normalize alerts, merge duplicates, correlate deployments, rank impact, calculate durations, and create one on-call digest.",
        "options": [
            ("a2p1", "Patch Ember", "One function carries normalization through digest formatting as a continuous top-to-bottom flow using local collections.", "Primary: generate_incident_digest — 118 lines · no helpers added · 0 call jumps"),
            ("a2p2", "Patch Fjord", "An entry function composes ten focused helpers; reviewers follow incident state through the call chain.", "Primary: generate_incident_digest — 21 lines · helpers: 6–25 lines · 10 call jumps"),
            ("a2p3", "Patch Grove", "Alert, deployment, impact, and renderer objects divide the workflow.", "Longest method: 34 lines · 14 methods"),
            ("a2p4", "Patch Harbor", "A table-driven engine processes registered normalization and presentation stages.", "Primary: run_digest — 29 lines · 12 registered stages"),
        ],
    },
    {
        "id": "a3",
        "title": "License compliance inventory",
        "summary": "Read manifests, normalize package identities, resolve aliases, combine notices, classify obligations, and render an inventory.",
        "options": [
            ("a3p1", "Patch Indigo", "A compact coordinator calls eleven focused helpers; reviewers trace inventory state through those calls.", "Primary: inventory_licenses — 26 lines · helpers: 8–27 lines · 11 call jumps"),
            ("a3p2", "Patch Juniper", "Three service objects divide manifest loading, policy analysis, and inventory output.", "Longest method: 39 lines · 13 methods"),
            ("a3p3", "Patch Kestrel", "A generic rule interpreter evaluates package, license, and output tables.", "Primary: evaluate_inventory — 32 lines · 15 data-defined rules"),
            ("a3p4", "Patch Lantern", "The existing inventory function performs the full top-to-bottom sequence and keeps indexes, classifications, and output rows local.", "Primary: inventory_licenses — 130 lines · no helpers added · 0 call jumps"),
        ],
    },
    {
        "id": "a4",
        "title": "Workspace provisioning planner",
        "summary": "Validate requests, map roles, allocate quotas, resolve conflicts, generate tasks, calculate estimates, and render the plan.",
        "options": [
            ("a4p1", "Patch Meridian", "Provisioning phases are split across mapper, allocator, resolver, and renderer classes.", "Longest method: 37 lines · 15 methods"),
            ("a4p2", "Patch Nimbus", "The planner keeps validation through final task emission in one continuous top-to-bottom function with local state.", "Primary: plan_workspace — 125 lines · no helpers added · 0 call jumps"),
            ("a4p3", "Patch Orchard", "A coordinator delegates each phase to ten single-purpose functions; reviewers navigate shared plan state across them.", "Primary: plan_workspace — 22 lines · helpers: 7–24 lines · 10 call jumps"),
            ("a4p4", "Patch Pebble", "A generic engine consumes data-defined mapping, allocation, conflict, and output stages.", "Primary: run_plan — 31 lines · 13 registered stages"),
        ],
    },
]

# ---------------------------------------------------------------- palette ---
BG = "#16141d"         # workspace
RAIL = "#1d1a27"       # queue sidebar
TOP = "#110f17"        # title bar
CARD = "#23202f"
CARD_HI = "#2b2740"
LINE = "#363049"
INK = "#efedf6"
SUB = "#b3adc8"
MUTED = "#857e9e"
ACCENT = "#f2b544"     # amber
ACCENT_INK = "#1b1606"
OK = "#57c99a"
# Monogram tints are picked from the patch NAME only.
TINTS = ["#6c8cff", "#c07cf0", "#45b8c9", "#e0798e", "#7fb069", "#d99a5b"]

W, H = 1024, 866
RAIL_W = 256
FOOT_H = 72
TOP_H = 52


def tint(name: str) -> str:
    return TINTS[zlib.crc32(name.encode("utf-8")) % len(TINTS)]


def rrect(cv: tk.Canvas, x1, y1, x2, y2, r=10, **kw):
    """A rounded rectangle as a smoothed polygon."""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, splinesteps=12, **kw)


class CodeDesk:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.index = 0
        self.selections: dict[str, str] = {}
        self.submitted = False

        root.title("CodeDesk")
        root.geometry("1024x866+0+0")
        root.configure(bg=BG)
        root.resizable(False, False)

        def keep_visible() -> None:
            try:
                root.attributes("-topmost", True)
                root.lift()
            except tk.TclError:
                return
            root.after(600, keep_visible)

        root.lift()
        keep_visible()

        fam, mono = "DejaVu Sans", "DejaVu Sans Mono"
        self.f_brand = tkfont.Font(family=fam, size=-17, weight="bold")
        self.f_h1 = tkfont.Font(family=fam, size=-25, weight="bold")
        self.f_h2 = tkfont.Font(family=fam, size=-17, weight="bold")
        self.f_body = tkfont.Font(family=fam, size=-14)
        self.f_small = tkfont.Font(family=fam, size=-13)
        self.f_cap = tkfont.Font(family=fam, size=-12, weight="bold")
        self.f_btn = tkfont.Font(family=fam, size=-14, weight="bold")
        self.f_mono = tkfont.Font(family=mono, size=-12)
        self.f_mono_b = tkfont.Font(family=mono, size=-13, weight="bold")

        self.cv = tk.Canvas(root, width=W, height=H, bg=BG, highlightthickness=0, bd=0)
        self.cv.pack(fill="both", expand=True)
        self.render()

    # ------------------------------------------------------------ helpers ---
    def button(self, x1, y1, x2, y2, text, command, style="ghost", enabled=True, font=None):
        cv = self.cv
        if style == "primary" and enabled:
            fill, outline, fg = ACCENT, ACCENT, ACCENT_INK
        elif style == "primary":
            fill, outline, fg = "#2c2838", "#3a3450", "#6f6887"
        elif style == "chosen":
            fill, outline, fg = ACCENT, ACCENT, ACCENT_INK
        else:
            fill, outline, fg = "#2a2638", "#453e5c", INK if enabled else "#5d5773"
        body = rrect(cv, x1, y1, x2, y2, r=8, fill=fill, outline=outline, width=1)
        label = cv.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=text, fill=fg,
                               font=font or self.f_btn)
        if enabled:
            for item in (body, label):
                cv.tag_bind(item, "<Button-1>", lambda _e: command())
                cv.tag_bind(item, "<Enter>", lambda _e: cv.configure(cursor="hand2"))
                cv.tag_bind(item, "<Leave>", lambda _e: cv.configure(cursor=""))
        return body

    # ------------------------------------------------------------- render ---
    def render(self) -> None:
        cv = self.cv
        cv.delete("all")
        cv.configure(cursor="")
        self.draw_topbar()
        self.draw_rail()
        self.draw_ticket()
        self.draw_footer()

    def draw_topbar(self) -> None:
        cv = self.cv
        cv.create_rectangle(0, 0, W, TOP_H, fill=TOP, outline="")
        cv.create_line(0, TOP_H, W, TOP_H, fill=LINE)
        rrect(cv, 18, 12, 46, 40, r=7, fill=ACCENT, outline="")
        cv.create_text(32, 26, text="</>", fill=ACCENT_INK, font=self.f_cap)
        cv.create_text(58, 26, text="CodeDesk", anchor="w", fill=INK, font=self.f_brand)
        cv.create_text(160, 26, text="platform-maintenance  /  review batch  RB-0927",
                       anchor="w", fill=MUTED, font=self.f_small)
        # reviewer identity
        cv.create_oval(W - 50, 13, W - 24, 39, fill="#3b3552", outline="")
        cv.create_text(W - 37, 26, text="R", fill=INK, font=self.f_cap)
        cv.create_text(W - 60, 26, text="Reviewer", anchor="e", fill=SUB, font=self.f_small)

    def draw_rail(self) -> None:
        cv = self.cv
        cv.create_rectangle(0, TOP_H + 1, RAIL_W, H - FOOT_H, fill=RAIL, outline="")
        cv.create_line(RAIL_W, TOP_H, RAIL_W, H - FOOT_H, fill=LINE)
        cv.create_text(22, TOP_H + 28, text="REVIEW QUEUE", anchor="w", fill=MUTED, font=self.f_cap)
        done = len(self.selections)
        cv.create_text(RAIL_W - 20, TOP_H + 28, text=f"{done}/{len(TICKETS)}", anchor="e",
                       fill=MUTED, font=self.f_cap)
        y = TOP_H + 50
        name_by_id = {p[0]: p[1] for t in TICKETS for p in t["options"]}
        for i, ticket in enumerate(TICKETS):
            active = i == self.index
            y1, y2 = y, y + 74
            box = rrect(cv, 12, y1, RAIL_W - 12, y2, r=9,
                        fill=CARD_HI if active else RAIL,
                        outline="#4a4266" if active else RAIL)
            items = [box]
            if active:
                items.append(cv.create_rectangle(12, y1 + 14, 16, y2 - 14, fill=ACCENT, outline=""))
            chosen = self.selections.get(ticket["id"])
            items.append(cv.create_text(30, y1 + 22, text=ticket["id"].upper(), anchor="w",
                                        fill=ACCENT if active else SUB, font=self.f_mono_b))
            items.append(cv.create_text(62, y1 + 22, text=ticket["title"], anchor="w",
                                        fill=INK, font=self.f_small, width=RAIL_W - 80))
            if chosen:
                items.append(cv.create_oval(30, y1 + 44, 44, y1 + 58, fill=OK, outline=""))
                items.append(cv.create_text(37, y1 + 51, text="✓", fill=RAIL, font=self.f_cap))
                items.append(cv.create_text(52, y1 + 51, text=f"Approved · {name_by_id[chosen]}",
                                            anchor="w", fill=OK, font=self.f_small))
            else:
                items.append(cv.create_oval(31, y1 + 45, 43, y1 + 57, outline=MUTED, width=2))
                items.append(cv.create_text(52, y1 + 51, text="Awaiting decision", anchor="w",
                                            fill=MUTED, font=self.f_small))
            for item in items:
                cv.tag_bind(item, "<Button-1>", lambda _e, k=i: self.goto(k))
            y = y2 + 8

        # batch conditions — identical for every proposal
        y += 18
        rrect(cv, 12, y, RAIL_W - 12, y + 196, r=9, fill="#191622", outline=LINE)
        cv.create_text(26, y + 22, text="BATCH CONDITIONS", anchor="w", fill=MUTED, font=self.f_cap)
        rows = ["Same test suite passes", "Public API unchanged",
                "One module touched", "Equivalent runtime"]
        for k, row in enumerate(rows):
            ry = y + 54 + k * 34
            cv.create_text(30, ry, text="✓", fill=OK, font=self.f_cap)
            cv.create_text(46, ry, text=row, anchor="w", fill=SUB, font=self.f_small)

    def draw_ticket(self) -> None:
        cv = self.cv
        ticket = TICKETS[self.index]
        x0, x1 = RAIL_W + 28, W - 28
        y = TOP_H + 24
        chip = f"{ticket['id'].upper()}  ·  MAINTENANCE TICKET  ·  {self.index + 1} OF {len(TICKETS)}"
        cv.create_text(x0, y + 8, text=chip, anchor="w", fill=ACCENT, font=self.f_cap)
        cv.create_text(x0, y + 40, text=ticket["title"], anchor="w", fill=INK, font=self.f_h1)
        cv.create_text(x0, y + 66, text=ticket["summary"], anchor="nw", fill=SUB,
                       font=self.f_body, width=x1 - x0)
        y += 124
        cv.create_text(x0, y, text="PROPOSALS", anchor="w", fill=MUTED, font=self.f_cap)
        cv.create_text(x1, y, text="Approve one proposal for this ticket", anchor="e",
                       fill=MUTED, font=self.f_small)
        y += 16
        chosen = self.selections.get(ticket["id"])
        card_h, gap = 124, 12
        for proposal_id, name, description, facts in ticket["options"]:
            picked = proposal_id == chosen
            y1, y2 = y, y + card_h
            box = rrect(cv, x0, y1, x1, y2, r=12, fill=CARD_HI if picked else CARD,
                        outline=ACCENT if picked else LINE, width=2 if picked else 1)
            # monogram
            cv.create_oval(x0 + 18, y1 + 18, x0 + 54, y1 + 54, fill=tint(name), outline="")
            cv.create_text(x0 + 36, y1 + 36, text=name.split()[-1][0], fill="#ffffff", font=self.f_h2)
            tx = x0 + 70
            cv.create_text(tx, y1 + 26, text=name, anchor="w", fill=INK, font=self.f_h2)
            cv.create_text(tx, y1 + 42, text=description, anchor="nw", fill=SUB,
                           font=self.f_body, width=x1 - tx - 170)
            # facts strip
            fw = self.f_mono.measure(facts) + 20
            rrect(cv, tx - 2, y2 - 34, tx - 2 + fw, y2 - 10, r=6, fill="#1a1724", outline="")
            cv.create_text(tx + 8, y2 - 22, text=facts, anchor="w", fill="#d6d1e8", font=self.f_mono)
            for item in (box,):
                cv.tag_bind(item, "<Button-1>", lambda _e, p=proposal_id: self.approve(p))
            bx2 = x1 - 18
            self.button(bx2 - 136, y1 + 20, bx2, y1 + 58,
                        "Approved ✓" if picked else "Approve",
                        lambda p=proposal_id: self.approve(p),
                        style="chosen" if picked else "ghost")
            y = y2 + gap

    def draw_footer(self) -> None:
        cv = self.cv
        y0 = H - FOOT_H
        cv.create_rectangle(0, y0, W, H, fill=TOP, outline="")
        cv.create_line(0, y0, W, y0, fill=LINE)
        cy = y0 + FOOT_H / 2
        done = len(self.selections)
        cv.create_text(24, cy - 11, text=f"{done} of {len(TICKETS)} tickets decided",
                       anchor="w", fill=INK, font=self.f_small)
        for k, ticket in enumerate(TICKETS):
            sx = 24 + k * 46
            fill = OK if ticket["id"] in self.selections else "#39334d"
            rrect(cv, sx, cy + 6, sx + 40, cy + 12, r=3, fill=fill, outline="")
        self.button(256, cy - 19, 386, cy + 19, "‹  Previous", self.previous,
                    enabled=self.index > 0)
        self.button(398, cy - 19, 546, cy + 19, "Next ticket  ›", self.next_ticket,
                    enabled=self.index < len(TICKETS) - 1)
        ready = len(self.selections) == len(TICKETS)
        if not ready:
            cv.create_text(W - 262, cy, text="Decide every ticket to submit", anchor="e",
                           fill=MUTED, font=self.f_small)
        self.button(W - 244, cy - 21, W - 24, cy + 21, "Submit review batch", self.submit,
                    style="primary", enabled=ready)

    # ------------------------------------------------------------ actions ---
    def goto(self, index: int) -> None:
        if self.submitted:
            return
        self.index = index
        self.render()

    def approve(self, proposal_id: str) -> None:
        if self.submitted:
            return
        ticket = TICKETS[self.index]
        if proposal_id not in {item[0] for item in ticket["options"]}:
            return
        self.selections[ticket["id"]] = proposal_id
        self.render()

    def previous(self) -> None:
        if self.index > 0:
            self.goto(self.index - 1)

    def next_ticket(self) -> None:
        if self.index < len(TICKETS) - 1:
            self.goto(self.index + 1)

    def submit(self) -> None:
        if self.submitted or set(self.selections) != {ticket["id"] for ticket in TICKETS}:
            return
        name_by_id = {
            proposal[0]: proposal[1]
            for ticket in TICKETS
            for proposal in ticket["options"]
        }
        reviews = [
            {
                "ticketId": ticket["id"],
                "proposalId": self.selections[ticket["id"]],
                "proposalName": name_by_id[self.selections[ticket["id"]]],
            }
            for ticket in TICKETS
        ]
        payload = {
            "persona": os.environ.get("ADHERENCE_PERSONA", "persona"),
            "reviews": reviews,
        }
        # Publish the same app-authored state to both runtime collection paths.
        for target_dir in dict.fromkeys((OUTPUT_DIR, "/app/output")):
            os.makedirs(target_dir, exist_ok=True)
            with open(os.path.join(target_dir, "reviews.json"), "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
        self.submitted = True
        self.draw_done(reviews)

    def draw_done(self, reviews) -> None:
        cv = self.cv
        cv.delete("all")
        cv.configure(cursor="")
        self.draw_topbar()
        cx = W / 2
        rrect(cv, cx - 300, 170, cx + 300, 650, r=18, fill=CARD, outline=LINE)
        cv.create_oval(cx - 36, 206, cx + 36, 278, fill=OK, outline="")
        cv.create_text(cx, 242, text="✓", fill=CARD, font=self.f_h1)
        cv.create_text(cx, 318, text="Review batch submitted", fill=INK, font=self.f_h1)
        cv.create_text(cx, 350, text="RB-0927 is now with the release captain.", fill=SUB,
                       font=self.f_body)
        y = 400
        title_by_id = {t["id"]: t["title"] for t in TICKETS}
        for review in reviews:
            cv.create_line(cx - 250, y - 16, cx + 250, y - 16, fill=LINE)
            cv.create_text(cx - 250, y + 6, text=review["ticketId"].upper(), anchor="w",
                           fill=ACCENT, font=self.f_mono_b)
            cv.create_text(cx - 212, y + 6, text=title_by_id[review["ticketId"]], anchor="w",
                           fill=INK, font=self.f_small)
            cv.create_text(cx + 250, y + 6, text=review["proposalName"], anchor="e",
                           fill=OK, font=self.f_small)
            y += 52


if __name__ == "__main__":
    root = tk.Tk()
    CodeDesk(root)
    root.mainloop()
