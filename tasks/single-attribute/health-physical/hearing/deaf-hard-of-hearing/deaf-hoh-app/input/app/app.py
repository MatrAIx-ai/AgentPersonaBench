#!/usr/bin/env python3
"""Bramblewood Home Safety Scheme - Free home-safety visit — choose your kit and visit arrangements. Native desktop app."""
from __future__ import annotations

import json
import os

try:
    import tkinter as tk
    from tkinter import font as tkfont
except ImportError:  # Session works without Tk; only the window needs it
    tk = None
    tkfont = None

OUTPUT_DIR = (os.environ.get("PLAYGROUND_OUTPUT_DIR") or os.environ.get("ADHERENCE_OUTPUT_DIR")
              or "/app/output")
ARTIFACT_NAME = "safety_kit.json"
SELECTION_KEY = "order"
REFERENCE_KEY = "reference"
REFERENCE = "BW-HS-2207"
SITE_NAME = "Bramblewood Home Safety Scheme"
TAGLINE = "Free home-safety visit — choose your kit and visit arrangements"
INTRO = "Pick one option in every section. Everything in the kit is supplied and fitted by the scheme at no charge."
SUBMIT_TEXT = "Submit application"
CONFIRMATION = f"Application {REFERENCE} submitted"
# One entry per section, in display order.
CATALOG = [
    {'id': 'smoke', 'title': '1. Smoke alarm',
     'options': [
         {'id': 'sa-std', 'name': 'Standard smoke alarm', 'detail': '85 dB siren, sealed ten-year battery, no socket needed. Fitted on the first visit.', 'note': 'Recommended', 'channel': 'voice'},
         {'id': 'sa-talk', 'name': 'Talking smoke alarm', 'detail': 'Siren plus a spoken "Fire!" warning and low-battery prompt. Fitted on the first visit.', 'channel': 'voice'},
         {'id': 'sa-strobe', 'name': 'Strobe and pad smoke alarm', 'detail': 'Siren, strobe and a vibrating pad. Needs a socket by the bed; second visit in two weeks.', 'channel': 'visual'},
     ]},
    {'id': 'door', 'title': '2. Doorbell',
     'options': [
         {'id': 'db-chime', 'name': 'Wireless doorbell chime', 'detail': 'Plug-in chime, three tones, 80 dB. Works straight from the box.', 'note': 'Standard', 'channel': 'voice'},
         {'id': 'db-flash', 'name': 'Doorbell with flashing lamps', 'detail': 'Two plug-in lamps flash when the bell rings, in the hall and living room. Second visit.', 'channel': 'visual'},
         {'id': 'db-loud', 'name': 'Extra-loud doorbell chime', 'detail': 'Plug-in chime with a 95 dB tone that carries to the garden. Works from the box.', 'channel': 'voice'},
     ]},
    {'id': 'visit', 'title': '3. How the fitter confirms your slot',
     'options': [
         {'id': 'vc-sms', 'name': 'Text the evening before', 'detail': 'A text with your two-hour slot arrives by 7 pm the evening before.', 'channel': 'text'},
         {'id': 'vc-call', 'name': 'Fitter phones in the morning', 'detail': 'The fitter rings between 8 and 9 am with your slot and can move it there and then.', 'note': 'Most reliable', 'channel': 'voice'},
         {'id': 'vc-auto', 'name': 'Automated call the day before', 'detail': 'A recorded message with your slot the evening before; rings again if you miss it.', 'channel': 'voice'},
     ]},
    {'id': 'guide', 'title': '4. Kit instructions',
     'options': [
         {'id': 'ug-spoken', 'name': 'Fitter talks you through it', 'detail': 'A spoken walkthrough at the visit, for as long as you need it.', 'note': 'Recommended', 'channel': 'voice'},
         {'id': 'ug-print', 'name': 'Printed guide', 'detail': 'Booklet with step-by-step pictures, posted the week after the visit.', 'channel': 'text'},
         {'id': 'ug-video', 'name': 'Captioned video guide', 'detail': 'A six-minute video with captions, emailed after the visit.', 'channel': 'visual'},
         {'id': 'ug-callback', 'name': 'Follow-up call later', 'detail': 'The fitter rings a week later to go over the kit.', 'channel': 'voice'},
     ]},
    {'id': 'annual', 'title': '5. Yearly visit reminder',
     'options': [
         {'id': 'rc-call', 'name': 'Reminder call', 'detail': "The scheme team phones when next year's visit is due and books it on the spot.", 'note': 'Standard — one call', 'channel': 'voice'},
         {'id': 'rc-voice', 'name': 'Recorded reminder message', 'detail': 'A recorded message left on your phone with the date and the number to ring.', 'channel': 'voice'},
         {'id': 'rc-letter', 'name': 'Reminder letter', 'detail': 'A letter each year with a date to reply to by post or online.', 'note': 'Reply needed', 'channel': 'text'},
     ]},
]
# 1024x900 is the CUA framebuffer; xfwm4 takes ~24-32 px for its title bar, so the client
# area is requested at 868 px (app_env_check.py reads the literal geometry string below).
WINDOW_W, WINDOW_H = 1024, 868
# The CUA desktop is exactly 1024x900 and the window manager draws a title bar,
# so the last ~40px of a +0+0 window sit under the screen edge: keep the action
# bar above that band.
SAFE_BOTTOM = 22
# bramble palette: berry-plum, leaf green, parchment
BG, CARD, INK, MUTED, BRAND, ACCENT = "#f7f2e8", "#fffdf8", "#241a22", "#6d6168", "#4a2545", "#8a5a1f"
EDGE, PICKED = "#ddd2c2", "#eaf2e1"
LEAF, LEAF_D, BERRY, PLUM_L, SAND = "#4f7a3a", "#3a5c2a", "#7b2d5e", "#6a3d63", "#efe6d6"


class Session:
    """Selections, the ordered click trace and the artifact writer; needs no display."""

    def __init__(self, output_dir: str | None = None) -> None:
        self.output_dir = output_dir or OUTPUT_DIR
        self.groups: dict[str, dict] = {group["id"]: group for group in CATALOG}
        self.selected: dict[str, dict | None] = {group["id"]: None for group in CATALOG}
        self.events: list[dict] = []
        self.completed = False

    def option(self, group_id: str, option_id: str) -> dict | None:
        group = self.groups.get(group_id)
        if group is None:
            return None
        return next((item for item in group["options"] if item["id"] == option_id), None)

    def _log(self, kind: str, **data: object) -> None:
        self.events.append({"seq": len(self.events) + 1, "type": kind, **data})

    def select(self, group_id: str, option_id: str) -> bool:
        option = None if self.completed else self.option(group_id, option_id)
        if option is None:
            return False
        self.selected[group_id] = dict(option)
        self._log("select", group=group_id, optionId=option_id)
        return True

    def chosen_ids(self) -> dict[str, str]:
        return {group_id: option["id"] for group_id, option in self.selected.items() if option is not None}

    def ready(self) -> bool:
        return not self.completed and all(option is not None for option in self.selected.values())

    def submit(self) -> bool:
        if not self.ready():
            return False
        self.completed = True
        self._log("submit", optionIds=self.chosen_ids())
        self.write_artifact()
        return True

    def artifact_path(self) -> str:
        return os.path.join(self.output_dir, ARTIFACT_NAME)

    def write_artifact(self) -> str:
        order = {**self.selected, REFERENCE_KEY: REFERENCE}
        payload = {SELECTION_KEY: order, "events": self.events, "completed": self.completed}
        os.makedirs(self.output_dir, exist_ok=True)
        path = self.artifact_path()
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return path


class App:
    """The window: every control calls a Session method."""

    HEADER_H = 74
    BAR_H = 54
    COL_W = 164  # section label column

    def __init__(self, root: "tk.Tk", session: Session | None = None) -> None:
        self.root = root
        self.session = session or Session()
        self.cards: dict[tuple[str, str], int] = {}
        self.buttons: dict[tuple[str, str], tk.Button] = {}
        self.ticks: dict[str, int] = {}
        self.chosen_lbl: dict[str, int] = {}
        root.title(SITE_NAME)
        root.geometry("1024x868+0+0")  # keep in sync with WINDOW_W / WINDOW_H
        root.configure(bg=BG)
        root.resizable(False, False)
        root.lift()
        try:
            root.attributes("-topmost", True)
            root.after(6000, lambda: root.attributes("-topmost", False))
        except tk.TclError:
            pass
        F = lambda fam, size, weight="normal", slant="roman": tkfont.Font(
            family=fam, size=size, weight=weight, slant=slant)
        self.f_word = F("Nimbus Roman", 21, "bold")
        self.f_caps = F("Nimbus Sans Narrow", 11, "bold")
        self.f_num = F("Nimbus Roman", 18, "bold")
        self.f_sec = F("Nimbus Sans", 12, "bold")
        self.f_name = F("Nimbus Sans", 11, "bold")
        self.f_body = F("Nimbus Sans", 10)
        self.f_note = F("Nimbus Sans Narrow", 10, "bold")
        self.f_btn = F("Nimbus Sans", 10, "bold")
        self.f_status = F("Nimbus Sans", 11, "bold")
        self.f_big = F("Nimbus Roman", 24, "bold")

        self.c = tk.Canvas(root, width=WINDOW_W, height=WINDOW_H, bg=BG, highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self._header()
        self._body()
        self._bar()
        self.overlay = tk.Canvas(root, bg=BG, highlightthickness=0)
        self._refresh()

    # ---- drawing helpers ---------------------------------------------------
    def rrect(self, x0, y0, x1, y1, r, canvas=None, **kw):
        c = canvas or self.c
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1,
               x1 - r, y1, x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return c.create_polygon(pts, smooth=True, **kw)

    def _crest(self, c, x, y):
        """Drawn bramble crest: shield with a leaf and a berry cluster."""
        c.create_polygon(x, y, x + 44, y, x + 44, y + 30, x + 22, y + 48, x, y + 30,
                         fill=CARD, outline=SAND, width=2)
        c.create_polygon(x + 8, y + 30, x + 16, y + 12, x + 26, y + 8, x + 22, y + 22,
                         smooth=True, fill=LEAF, outline="")
        c.create_line(x + 9, y + 30, x + 22, y + 14, fill=LEAF_D, width=1)
        for dx, dy in ((28, 20), (35, 20), (31.5, 26), (28, 32), (35, 32), (31.5, 38)):
            c.create_oval(x + dx - 4, y + dy - 4, x + dx + 4, y + dy + 4, fill=BERRY, outline=BRAND)

    def _header(self) -> None:
        c = self.c
        c.create_rectangle(0, 0, WINDOW_W, self.HEADER_H, fill=BRAND, outline="")
        for i in range(0, WINDOW_W, 22):  # hedgerow scallop along the lower edge
            c.create_arc(i, self.HEADER_H - 11, i + 22, self.HEADER_H + 11, start=180, extent=180,
                         fill=LEAF, outline="")
        self._crest(c, 22, 10)
        c.create_text(82, 30, text="Bramblewood", anchor="w", font=self.f_word, fill=CARD)
        c.create_text(84, 54, text="HOME SAFETY SCHEME  ·  " + TAGLINE.upper()[:24].rstrip(" —"),
                      anchor="w", font=self.f_caps, fill="#e6cfe0")
        x = 612
        for label in ("Apply", "Your visit", "Contact the scheme"):
            c.create_text(x, 30, text=label, anchor="w", font=self.f_caps,
                          fill=CARD if label == "Apply" else "#cdb2c7")
            if label == "Apply":
                c.create_line(x, 42, x + self.f_caps.measure(label), 42, fill="#d6b24a", width=3)
            x += self.f_caps.measure(label) + 30
        self.rrect(868, 48, 1004, 64, 8, fill=PLUM_L, outline="")
        c.create_text(936, 56, text=f"Ref {REFERENCE}", font=self.f_note, fill=CARD)

    def _layout(self, group: dict) -> tuple[float, float, float]:
        """Card x-origin, width and the content height the tallest card in this section needs."""
        options = group["options"]
        gx0, gx1, gap = 16 + self.COL_W, WINDOW_W - 24, 8
        cw = (gx1 - gx0 - gap * (len(options) - 1)) / len(options)
        need = 0
        for option in options:
            a = self.c.create_text(0, 0, text=option["name"], anchor="nw", width=cw - 22, font=self.f_name)
            b = self.c.create_text(0, 0, text=option["detail"], anchor="nw", width=cw - 22, font=self.f_body)
            need = max(need, self.c.bbox(a)[3] + 3 + self.c.bbox(b)[3])
            self.c.delete(a, b)
        return gx0, cw, need

    def _body(self) -> None:
        c = self.c
        top = self.HEADER_H + 17
        c.create_text(22, top + 4, text=INTRO, anchor="w", font=self.f_body, fill=MUTED)
        y = top + 16
        avail = WINDOW_H - self.BAR_H - SAFE_BOTTOM - y - 4
        needs = [self._layout(g)[2] + 16 + 8 + 38 + 8 for g in CATALOG]  # card pad + button row + band gap
        extra = max(0, (avail - sum(needs)) / len(CATALOG))
        for group, need in zip(CATALOG, needs):
            h = int(need + extra)
            self._band(group, y, h - 8)
            y += h

    def _band(self, group: dict, y: int, h: int) -> None:
        c = self.c
        x0 = 16
        self.rrect(x0, y, WINDOW_W - 16, y + h, 14, fill=SAND, outline="")
        title = group["title"]
        num, _, text = title.partition(". ")
        if not text:
            num, text = "", title
        c.create_oval(x0 + 14, y + 14, x0 + 50, y + 50, fill=BRAND, outline="")
        c.create_text(x0 + 32, y + 32, text=num, font=self.f_num, fill=CARD)
        c.create_text(x0 + 14, y + 60, text=text, anchor="nw", width=self.COL_W - 26,
                      font=self.f_sec, fill=INK)
        self.ticks[group["id"]] = c.create_text(x0 + 60, y + 32, text="", anchor="w",
                                                font=self.f_note, fill=LEAF_D)
        options = group["options"]
        gx0, cw, _need = self._layout(group)
        gap = 8
        for i, option in enumerate(options):
            cx0 = gx0 + i * (cw + gap)
            cx1 = cx0 + cw
            cy0, cy1 = y + 8, y + h - 8
            key = (group["id"], option["id"])
            card = self.rrect(cx0, cy0, cx1, cy1, 10, fill=CARD, outline=EDGE, width=1)
            tag = f"card-{option['id']}"
            c.itemconfigure(card, tags=(tag,))
            name = c.create_text(cx0 + 11, cy0 + 8, text=option["name"], anchor="nw",
                                 width=cw - 22, font=self.f_name, fill=INK, tags=(tag,))
            c.create_text(cx0 + 11, c.bbox(name)[3] + 3, text=option["detail"], anchor="nw",
                          width=cw - 22, font=self.f_body, fill=MUTED, tags=(tag,))
            if option.get("note"):
                c.create_text(cx0 + 11, cy1 - 22, text=option["note"], anchor="w",
                              font=self.f_note, fill=ACCENT, tags=(tag,))
            button = tk.Button(c, text="Select", command=lambda g=group["id"], o=option["id"]: self.choose(g, o),
                               bg=CARD, fg=BRAND, activebackground=PICKED, activeforeground=BRAND,
                               font=self.f_btn, relief="solid", bd=1, padx=12, pady=3,
                               highlightthickness=0, cursor="hand2")
            c.create_window(cx1 - 9, cy1 - 7, window=button, anchor="se")
            c.tag_bind(tag, "<Button-1>", lambda _e, g=group["id"], o=option["id"]: self.choose(g, o))
            self.cards[key] = card
            self.buttons[key] = button

    def _bar(self) -> None:
        c = self.c
        y0 = WINDOW_H - SAFE_BOTTOM - self.BAR_H
        c.create_rectangle(0, y0, WINDOW_W, WINDOW_H, fill=CARD, outline="")
        c.create_line(0, y0, WINDOW_W, y0, fill=EDGE)
        self.dots = []
        for i in range(len(CATALOG)):
            self.dots.append(c.create_oval(22 + i * 22, y0 + 22, 36 + i * 22, y0 + 36,
                                           fill=SAND, outline=EDGE))
        self.status = tk.Label(c, text="", bg=CARD, fg=MUTED, font=self.f_status, anchor="w")
        c.create_window(22 + len(CATALOG) * 22 + 10, y0 + self.BAR_H // 2, window=self.status, anchor="w")
        self.submit_button = tk.Button(c, text=SUBMIT_TEXT, command=self.submit, bg=BRAND, fg=CARD,
                                       activebackground=PLUM_L, activeforeground=CARD,
                                       disabledforeground="#b9a6b5", font=self.f_status, relief="flat",
                                       padx=20, pady=7, highlightthickness=0, cursor="hand2")
        c.create_window(WINDOW_W - 22, y0 + self.BAR_H // 2, window=self.submit_button, anchor="e")

    # ---- behaviour ----------------------------------------------------------
    def choose(self, group_id: str, option_id: str) -> None:
        if self.session.select(group_id, option_id):
            self._refresh()

    def _refresh(self) -> None:
        chosen = self.session.chosen_ids()
        for (group_id, option_id), card in self.cards.items():
            picked = chosen.get(group_id) == option_id
            self.c.itemconfigure(card, fill=PICKED if picked else CARD,
                                 outline=LEAF if picked else EDGE, width=2 if picked else 1)
            self.buttons[(group_id, option_id)].configure(
                text="Selected" if picked else "Select", bg=LEAF if picked else CARD,
                fg=CARD if picked else BRAND, activebackground=LEAF_D if picked else PICKED)
        for i, group in enumerate(CATALOG):
            done = group["id"] in chosen
            self.c.itemconfigure(self.ticks[group["id"]], text="✓ chosen" if done else "")
            self.c.itemconfigure(self.dots[i], fill=LEAF if done else SAND, outline=LEAF if done else EDGE)
        total, done = len(CATALOG), len(chosen)
        ready = self.session.ready()
        self.submit_button.configure(state="normal" if ready else "disabled",
                                     bg=BRAND if ready else "#d8ccd5")
        self.status.configure(text=(f"All {total} sections chosen. Click {SUBMIT_TEXT} to finish." if ready else
                                    f"{done} of {total} sections chosen. Choose one option in each section."))

    def submit(self) -> None:
        if not self.session.submit():
            return
        o = self.overlay
        o.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Misc.lift(o)
        o.delete("all")
        o.create_rectangle(0, 0, WINDOW_W, self.HEADER_H, fill=BRAND, outline="")
        self._crest(o, 22, 10)
        o.create_text(82, 37, text="Bramblewood", anchor="w", font=self.f_word, fill=CARD)
        self.rrect(192, 150, 832, 690, 22, canvas=o, fill=CARD, outline=EDGE)
        o.create_oval(472, 196, 552, 276, fill=LEAF, outline="")
        o.create_line(492, 236, 506, 252, 534, 218, fill=CARD, width=7, capstyle="round", joinstyle="round")
        o.create_text(512, 318, text=CONFIRMATION, font=self.f_big, fill=INK)
        o.create_text(512, 352, text="The scheme team will be in touch about your visit slot.",
                      font=self.f_body, fill=MUTED)
        chosen = self.session.selected
        for i, group in enumerate(CATALOG):
            yy = 400 + i * 50
            self.rrect(252, yy, 772, yy + 40, 10, canvas=o, fill=SAND, outline="")
            o.create_text(270, yy + 20, text=group["title"], anchor="w", font=self.f_sec, fill=INK)
            o.create_text(754, yy + 20, text=chosen[group["id"]]["name"], anchor="e",
                          font=self.f_body, fill=INK)


if __name__ == "__main__":
    if tk is None:
        raise SystemExit("tkinter is required to open the window")
    window = tk.Tk()
    App(window)
    window.mainloop()
