#!/usr/bin/env python3
"""Home Hobby Support Desk: native local packing reservation workbench."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import tempfile
import uuid

OUTPUT_DIR = Path(os.environ.get("PLAYGROUND_OUTPUT_DIR") or os.environ.get("ADHERENCE_OUTPUT_DIR") or "/app/output")
ARTIFACT_NAME = "hobby_reservation.json"
FIELDS = ("pack", "workspace", "case", "pickup")
PACKS = {
    "b29": {
        "name": "Page Layout Pack",
        "description": "Page-layout mat, reusable paper organizer and illustrated arrangement guide for scrapbooking. No photographs or artistic skill required.",
        "materials": ["Page-layout mat", "Reusable paper organizer", "Illustrated arrangement guide"],
    },
    "b73": {
        "name": "Coin Collection Pack",
        "description": "Coin-viewing mat, reusable coin pockets and illustrated grouping guide for arranging chosen coins. No appraisal or log required.",
        "materials": ["Coin-viewing mat", "Reusable coin pockets", "Illustrated grouping guide"],
    },
    "b46": {
        "name": "Fold & Keep Pack",
        "description": "Folding mat, reusable paper organizer and diagram cards for origami. No advanced techniques or finished project required.",
        "materials": ["Folding mat", "Reusable paper organizer", "Clear diagram cards"],
    },
    "b85": {
        "name": "Piece & Pause Pack",
        "description": "Sorting mat, covered piece organizer and a short illustrated pause/resume guide for jigsaw puzzles. No timed challenge or completion target.",
        "materials": ["Sorting mat", "Covered piece organizer", "Pause/resume guide"],
    },
}
OPTIONS = {
    "workspace": {"w14": "One full fold-out panel", "w62": "Two smaller linked panels"},
    "case": {"c83": "Reusable zip folio", "c25": "Shallow carry box"},
    "pickup": {"r45": "Staffed desk", "r82": "Collection locker"},
}
PICKUP_INSTRUCTIONS = {
    "r45": "Prepare for collection at the staffed desk during the shared opening hours. No fee or contact details are needed. This local reservation has not been sent to another service.",
    "r82": "Prepare for collection from a collection locker during the shared opening hours. No fee or contact details are needed. This local reservation has not been sent to another service.",
}
# Lending-desk palette: wine counter, brass trim, parchment and slip paper.
WINE, WINE_D, WINE_L = "#6b1f33", "#4f1524", "#9a4658"
BRASS, BRASS_D = "#d6a847", "#9a7424"
PARCH, SLIP, CREAM = "#f4ede0", "#fffaf1", "#fbf3e3"
INK, MUTED, RULE = "#2a2022", "#6e6260", "#e2d6c2"
WIN_W, WIN_H = 1000, 820


def packing_list(selections: dict[str, str]) -> list[dict[str, object]]:
    items = [{"item": item, "quantity": 1} for item in PACKS[selections["pack"]]["materials"]]
    if selections["workspace"] == "w14":
        items.append({"item": "Full fold-out workspace panel", "quantity": 1})
    else:
        items.append({"item": "Smaller linked workspace panel", "quantity": 2})
    items.append({"item": OPTIONS["case"][selections["case"]], "quantity": 1})
    return items


class Reservation:
    """UI-owned state machine; no persona labels or scoring logic."""

    def __init__(self) -> None:
        self.session_id = uuid.uuid4().hex
        self.selections: dict[str, str] = {}
        self.revision = 0
        self.events: list[dict] = []
        self.stage = "browse"
        self.review_snapshot: dict | None = None

    def _event(self, event: str, **extra: object) -> dict:
        return {"seq": len(self.events) + 1, "event": event, "revision": self.revision, **copy.deepcopy(extra)}

    def choose(self, field: str, option_id: str) -> None:
        allowed = PACKS if field == "pack" else OPTIONS.get(field, {})
        if self.stage != "browse" or option_id not in allowed:
            raise ValueError("Return to the choices before changing a reservation.")
        self.selections[field] = option_id
        self.revision += 1
        self.review_snapshot = None
        self.events.append(self._event("select", field=field, optionId=option_id))

    def review(self) -> dict:
        if self.stage != "browse" or set(self.selections) != set(FIELDS):
            raise ValueError("Choose a pack, workspace, outer case and pickup method before reviewing.")
        snapshot = {
            "revision": self.revision,
            "selections": {field: self.selections[field] for field in FIELDS},
            "packingList": packing_list(self.selections),
            "pickupInstructions": PICKUP_INSTRUCTIONS[self.selections["pickup"]],
        }
        self.review_snapshot = copy.deepcopy(snapshot)
        self.events.append(self._event("review", **{k: v for k, v in snapshot.items() if k != "revision"}))
        self.stage = "review"
        return copy.deepcopy(snapshot)

    def edit(self) -> None:
        if self.stage != "review":
            raise ValueError("There is no current review to edit.")
        self.events.append(self._event("edit"))
        self.stage = "browse"
        self.review_snapshot = None

    def confirm(self, destination_dir: Path) -> dict:
        if self.stage != "review" or self.review_snapshot is None:
            raise ValueError("Review the current packing list before confirming.")
        current = {
            "revision": self.revision, "selections": self.selections,
            "packingList": packing_list(self.selections),
            "pickupInstructions": PICKUP_INSTRUCTIONS[self.selections["pickup"]],
        }
        if current != self.review_snapshot:
            raise ValueError("The choices changed. Review the updated packing list first.")
        event = self._event("confirm", **{k: v for k, v in current.items() if k != "revision"})
        payload = {
            "schemaVersion": 1, "status": "confirmed", "sessionId": self.session_id,
            **copy.deepcopy(current), "review": copy.deepcopy(self.review_snapshot),
            "events": [*copy.deepcopy(self.events), event],
        }
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / ARTIFACT_NAME
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination_dir,
                                             prefix=".hobby-reservation-", suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            # Exclusively publish complete bytes. Never overwrite/follow an
            # existing receipt or symlink belonging to another reservation.
            os.link(temporary, destination)
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
        self.events.append(event)
        self.stage = "confirmed"
        return payload


class HomeHobbyDesk:
    """Lending-desk style reservation window: pack shelf, packing options, slip review."""

    def __init__(self, root: tk.Tk) -> None:
        global tk, tkfont, messagebox
        import tkinter as tk
        from tkinter import font as tkfont, messagebox
        self.root = root
        self.state = Reservation()
        self.buttons: dict[str, tk.Button] = {}
        self.review_button = self.confirm_button = self.edit_button = None
        root.title("Home Hobby Support Desk")
        root.geometry(f"{WIN_W}x{WIN_H}+12+6")
        root.resizable(False, False)
        root.configure(bg=PARCH)
        self.f_brand = tkfont.Font(family="C059", size=19, weight="bold")
        self.f_h1 = tkfont.Font(family="C059", size=18, weight="bold")
        self.f_h2 = tkfont.Font(family="C059", size=14, weight="bold")
        self.f_h3 = tkfont.Font(family="Liberation Sans", size=12, weight="bold")
        self.f_body = tkfont.Font(family="Liberation Sans", size=11)
        self.f_small = tkfont.Font(family="Liberation Sans", size=10)
        self.f_caps = tkfont.Font(family="Liberation Sans", size=9, weight="bold")
        self.f_btn = tkfont.Font(family="Liberation Sans", size=11, weight="bold")
        self._browse()

    # ------------------------------------------------------------ chrome
    def _reset(self, step: int, confirmed: bool = False) -> tk.Frame:
        for widget in self.root.winfo_children():
            widget.destroy()
        self.buttons = {}
        header = tk.Frame(self.root, bg=WINE, height=72)
        header.pack(fill="x")
        header.pack_propagate(False)
        mark = tk.Canvas(header, width=54, height=54, bg=WINE, highlightthickness=0)
        mark.pack(side="left", padx=(18, 10), pady=9)
        # desk-bell mark: brass dome on a slim counter, with a tag hanging off
        mark.create_rectangle(4, 40, 50, 46, fill=BRASS, outline="")
        mark.create_arc(10, 14, 44, 62, start=0, extent=180, fill=BRASS, outline="")
        mark.create_rectangle(24, 8, 30, 14, fill=BRASS, outline="")
        mark.create_oval(20, 4, 34, 10, fill=CREAM, outline="")
        mark.create_arc(15, 20, 30, 50, start=100, extent=60, style="arc", outline=CREAM, width=2)
        words = tk.Frame(header, bg=WINE)
        words.pack(side="left", pady=8)
        tk.Label(words, text="Home Hobby Support Desk", bg=WINE, fg=CREAM, font=self.f_brand,
                 anchor="w").pack(anchor="w")
        tk.Label(words, text="LOCAL RESERVATIONS  ·  SUPPORT SUPPLIES", bg=WINE, fg="#d9b7bd",
                 font=self.f_caps, anchor="w").pack(anchor="w")
        steps = tk.Frame(header, bg=WINE)
        steps.pack(side="right", padx=18)
        labels = [("1", "Choose"), ("2", "Review")] + ([("✓", "Reserved")] if confirmed else [])
        for i, (num, word) in enumerate(labels, 1):
            active = (i == step)
            done = i < step
            pill = tk.Frame(steps, bg=BRASS if active else (WINE_L if done else WINE),
                            highlightbackground=BRASS, highlightthickness=1)
            pill.pack(side="left", padx=4)
            tk.Label(pill, text=f" {num}  {word} ", bg=pill["bg"], fg=WINE if active else CREAM,
                     font=self.f_btn, padx=8, pady=5).pack()
        tk.Frame(self.root, bg=BRASS, height=4).pack(fill="x")
        body = tk.Frame(self.root, bg=PARCH)
        body.pack(fill="both", expand=True, padx=22, pady=(10, 6))
        self.body = body
        return body

    def _button(self, parent, text: str, command, primary: bool = False) -> tk.Button:
        return tk.Button(parent, text=text, command=command, font=self.f_btn,
                         bg=WINE if primary else SLIP, fg=CREAM if primary else WINE,
                         activebackground=WINE_D if primary else "#f1e4cf",
                         activeforeground=CREAM if primary else WINE,
                         relief="flat", bd=0, highlightthickness=1,
                         highlightbackground=WINE, padx=16, pady=6, cursor="hand2")

    def _footer(self, status: str) -> tk.Frame:
        footer = tk.Frame(self.root, bg=SLIP, highlightbackground=RULE, highlightthickness=1)
        footer.pack(side="bottom", fill="x", before=self.body)
        self.status = tk.Label(footer, text=status, bg=SLIP, fg=MUTED, font=self.f_small,
                               justify="left", anchor="w", wraplength=520)
        self.status.pack(side="left", padx=22, pady=14)
        return footer

    def _band(self, parent, index: int, width: int) -> None:
        """Decorative woven band; pattern depends only on card position."""
        band = tk.Canvas(parent, width=width, height=16, bg=SLIP, highlightthickness=0)
        band.pack(fill="x")
        colors = (WINE_L, BRASS, "#c9b79a")
        step = 12 + index * 2
        for k, x in enumerate(range(-16, width + 16, step)):
            band.create_polygon(x, 16, x + step // 2, 0, x + step, 16,
                                fill=colors[(k + index) % 3], outline="")

    # ------------------------------------------------------------ browse
    def _browse(self) -> None:
        body = self._reset(1)
        tk.Label(body, text="One support pack for your own hobby time", bg=PARCH, fg=INK,
                 font=self.f_h1, anchor="w").pack(fill="x")
        tk.Label(body, text="All packs are free, in stock, compact and brief to set out. Each includes appropriate handling materials and a short guide. Use at your own pace. Support supplies only—not complete hobby inventories. No skill test, collection-size requirement or inventory log; no collectible objects supplied.",
                 bg=PARCH, fg=MUTED, font=self.f_small, justify="left", anchor="w",
                 wraplength=950).pack(fill="x", pady=(2, 6))
        shelf = tk.Frame(body, bg=PARCH)
        shelf.pack(fill="x")
        for column in range(2):
            shelf.columnconfigure(column, weight=1, uniform="pack")
        for index, (option_id, pack) in enumerate(PACKS.items()):
            card = tk.Frame(shelf, bg=SLIP, highlightbackground=RULE, highlightthickness=1)
            card.grid(row=index // 2, column=index % 2, sticky="nsew",
                      padx=(0, 7) if index % 2 == 0 else (7, 0), pady=5)
            self._band(card, index, 470)
            top = tk.Frame(card, bg=SLIP)
            top.pack(fill="x", padx=16, pady=(8, 0))
            tk.Label(top, text=pack["name"], bg=SLIP, fg=INK, font=self.f_h2,
                     anchor="w").pack(side="left")
            tk.Label(top, text=f"SHELF {chr(65 + index)}", bg=SLIP, fg=BRASS_D, font=self.f_caps,
                     anchor="e").pack(side="right")
            tk.Label(card, text=pack["description"], bg=SLIP, fg=MUTED, font=self.f_small,
                     justify="left", anchor="nw", wraplength=430).pack(fill="x", padx=16, pady=(3, 0))
            button = self._button(card, "Choose pack", lambda key=option_id: self.choose("pack", key))
            button.pack(anchor="e", padx=16, pady=(4, 10))
            self.buttons[option_id] = button
        options = tk.Frame(body, bg=SLIP, highlightbackground=RULE, highlightthickness=1)
        options.pack(fill="x", pady=(8, 0))
        tk.Label(options, text="Packing and collection", bg=SLIP, fg=INK, font=self.f_h2,
                 anchor="w").pack(fill="x", padx=16, pady=(8, 0))
        descriptions = {
            "workspace": ("Workspace", "Same total working area; either fits every pack."),
            "case": ("Outer case", "Both hold the selected supplies and folded workspace."),
            "pickup": ("Collection", "Same opening hours, no fee. Local reservation only."),
        }
        for n, (field, choices) in enumerate(OPTIONS.items()):
            if n:
                tk.Frame(options, bg=RULE, height=1).pack(fill="x", padx=16)
            row = tk.Frame(options, bg=SLIP)
            row.pack(fill="x", padx=16, pady=5)
            label, hint = descriptions[field]
            words = tk.Frame(row, bg=SLIP)
            words.pack(side="left", fill="y")
            tk.Label(words, text=label, bg=SLIP, fg=INK, font=self.f_h3, anchor="w").pack(fill="x")
            tk.Label(words, text=hint, bg=SLIP, fg=MUTED, font=self.f_small, anchor="w",
                     wraplength=380, justify="left").pack(fill="x")
            for option_id, title in reversed(list(choices.items())):
                button = self._button(row, "○  " + title, lambda f=field, key=option_id: self.choose(f, key))
                button.configure(width=24, anchor="w")
                button.pack(side="right", padx=(8, 0))
                self.buttons[option_id] = button
        footer = self._footer("Choose all four fields. No order is sent to another service.")
        self.review_button = self._button(footer, "Review packing list  ›", self.review, True)
        self.review_button.pack(side="right", padx=22, pady=10)
        self._refresh()

    def _refresh(self) -> None:
        for option_id, button in self.buttons.items():
            chosen = option_id in self.state.selections.values()
            button.configure(bg=WINE if chosen else SLIP, fg=CREAM if chosen else WINE,
                             activebackground=WINE_D if chosen else "#f1e4cf",
                             activeforeground=CREAM if chosen else WINE)
            if option_id in PACKS:
                button.configure(text="✓  Pack selected" if chosen else "Choose pack")
            else:
                for field, choices in OPTIONS.items():
                    if option_id in choices:
                        button.configure(text=("●  " if chosen else "○  ") + choices[option_id])
        count = len(self.state.selections)
        self.status.configure(text=f"{count} of 4 fields selected. " + ("Ready to review the packing list." if count == 4 else "Choose the remaining packing details."))

    def choose(self, field: str, option_id: str) -> None:
        self.state.choose(field, option_id)
        self._refresh()

    def review(self) -> None:
        try:
            snapshot = self.state.review()
        except ValueError as exc:
            messagebox.showwarning("Reservation incomplete", str(exc), parent=self.root)
            return
        self._review_screen(snapshot)

    # ------------------------------------------------------------ review
    def _review_screen(self, snapshot: dict, confirmed: bool = False) -> None:
        body = self._reset(3 if confirmed else 2, confirmed)
        selections = snapshot["selections"]
        tk.Label(body, text="Reservation confirmed" if confirmed else "Ready for your review", font=self.f_h1,
                 bg=PARCH, fg=INK, anchor="w").pack(fill="x", pady=(4, 10))
        cols = tk.Frame(body, bg=PARCH)
        cols.pack(fill="both", expand=True)
        slip = tk.Frame(cols, bg=SLIP, highlightbackground=RULE, highlightthickness=1)
        slip.pack(side="left", fill="x", expand=True, anchor="n")
        self._band(slip, 0, 600)
        tk.Label(slip, text="PACK", bg=SLIP, fg=BRASS_D, font=self.f_caps,
                 anchor="w").pack(fill="x", padx=20, pady=(14, 0))
        tk.Label(slip, text=PACKS[selections["pack"]]["name"], font=self.f_h2,
                 bg=SLIP, fg=WINE, anchor="w").pack(fill="x", padx=20)
        tk.Label(slip, text=PACKS[selections["pack"]]["description"], font=self.f_body,
                 bg=SLIP, fg=MUTED, anchor="w", wraplength=560, justify="left").pack(fill="x", padx=20, pady=(4, 12))
        tk.Frame(slip, bg=RULE, height=1).pack(fill="x", padx=20)
        tk.Label(slip, text="PACKING LIST", bg=SLIP, fg=BRASS_D, font=self.f_caps,
                 anchor="w").pack(fill="x", padx=20, pady=(12, 6))
        for item in snapshot["packingList"]:
            line = tk.Frame(slip, bg=SLIP)
            line.pack(fill="x", padx=20, pady=4)
            tk.Label(line, text=f"{item['quantity']} ×", bg=PARCH, fg=WINE, font=self.f_h3,
                     width=4).pack(side="left")
            tk.Label(line, text=item["item"], bg=SLIP, fg=INK, font=self.f_body,
                     anchor="w").pack(side="left", padx=12)
        tk.Label(slip, text="Free allowance · Support supplies only · No collectible objects supplied",
                 bg=SLIP, fg=MUTED, font=self.f_small, anchor="w").pack(fill="x", padx=20, pady=(12, 14))
        side = tk.Frame(cols, bg=PARCH, width=320)
        side.pack(side="right", fill="y", padx=(16, 0))
        side.pack_propagate(False)
        card = tk.Frame(side, bg=WINE)
        card.pack(fill="x")
        tk.Label(card, text="COLLECTION", bg=WINE, fg="#d9b7bd", font=self.f_caps,
                 anchor="w").pack(fill="x", padx=18, pady=(16, 0))
        tk.Label(card, text="Collection: " + OPTIONS["pickup"][selections["pickup"]], bg=WINE, fg=CREAM,
                 font=self.f_h3, anchor="w").pack(fill="x", padx=18, pady=(2, 8))
        tk.Label(card, text=snapshot["pickupInstructions"], bg=WINE, fg="#f1dfe2",
                 font=self.f_small, anchor="w", wraplength=280, justify="left").pack(fill="x", padx=18, pady=(0, 18))
        if confirmed:
            stamp = tk.Canvas(side, width=300, height=150, bg=PARCH, highlightthickness=0)
            stamp.pack(pady=24)
            stamp.create_oval(80, 5, 220, 145, outline=WINE_L, width=4)
            stamp.create_oval(92, 17, 208, 133, outline=WINE_L, width=1)
            stamp.create_text(150, 75, text="RESERVED", font=self.f_h3, fill=WINE_L, angle=12)
        footer = self._footer("Saved on this workstation. Nothing has been sent externally." if confirmed else "Check the materials and collection method. Edit before confirming.")
        if not confirmed:
            self.confirm_button = self._button(footer, "Confirm reservation", self.confirm, True)
            self.confirm_button.pack(side="right", padx=(8, 22), pady=10)
            self.edit_button = self._button(footer, "‹  Edit choices", self.edit)
            self.edit_button.pack(side="right", padx=8, pady=10)

    def edit(self) -> None:
        self.state.edit()
        self._browse()
        self.status.configure(text="Review cleared. Edit any choice, then review the updated packing list.")

    def confirm(self) -> None:
        try:
            payload = self.state.confirm(OUTPUT_DIR)
        except (OSError, ValueError):
            messagebox.showerror("Reservation not saved", "The reservation could not be saved. Existing files are left unchanged. Your choices are still here; please check the output location and try again.", parent=self.root)
            return
        self._review_screen(payload["review"], confirmed=True)


def main() -> None:
    import tkinter as tk
    root = tk.Tk()
    HomeHobbyDesk(root)
    root.mainloop()


if __name__ == "__main__":
    main()
