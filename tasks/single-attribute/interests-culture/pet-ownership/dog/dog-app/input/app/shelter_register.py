#!/usr/bin/env python3
"""SafeHarbor Registration - native emergency shelter registration desktop app.

A three-step Tk desktop application (Shelter -> Household -> Review) drawn on a
single Canvas. On "Submit registration" the app writes registration.json to the
output directory.
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import font as tkfont

OUTPUT_DIR = os.environ.get("PLAYGROUND_OUTPUT_DIR") or os.environ.get("ADHERENCE_OUTPUT_DIR") or "/app/output"
SHELTERS = [
    {"id": "s01", "name": "Riverside Civic Hall", "details": "0.8 km away · 46 spaces · Animal policy: no animals admitted", "acceptsOrdinaryDogs": False},
    {"id": "s02", "name": "Northgate Community Centre", "details": "1.4 km away · 31 spaces · Animal policy: ordinary dogs accepted in the staffed companion-animal wing", "acceptsOrdinaryDogs": True},
    {"id": "s03", "name": "Central Sports Pavilion", "details": "1.1 km away · 54 spaces · Animal policy: trained service animals only; ordinary household animals not admitted", "acceptsOrdinaryDogs": False},
]
ANIMAL_TYPES = {"dog": "Dog", "cat": "Cat", "other": "Other household animal"}

W, H = 1024, 866
FOG, PAPER, INK, MUTED, LINE = "#f3efe6", "#fffdf8", "#1e272c", "#5d676b", "#d9d2c3"
BUOY, BUOY_DK, SEA, SEA_LT, OK = "#e2572b", "#b8421d", "#24424c", "#dfe8e6", "#2f7d5b"
STEPS = ["Shelter", "Household", "Review"]


def _split(details: str) -> tuple[str, str]:
    parts = details.split(" · ")
    return " · ".join(p for p in parts if not p.startswith("Animal policy")), next((p for p in parts if p.startswith("Animal policy")), "")


class ShelterRegister:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.selected_shelter: str | None = None
        self.manifest: list[dict[str, str]] = []
        self.events: list[dict[str, object]] = []
        self.step = 0
        self.notice = ""
        self.hits: dict[str, tuple[int, int, int, int]] = {}
        root.title("SafeHarbor Registration")
        root.geometry(f"{W}x{H}+0+0")
        root.configure(bg=FOG)
        root.lift(); root.attributes("-topmost", True); root.after(8000, lambda: root.attributes("-topmost", False))
        fam = "DejaVu Sans"
        self.f_brand = tkfont.Font(family="Liberation Sans Narrow", size=24, weight="bold")
        self.f_h1 = tkfont.Font(family="Liberation Sans Narrow", size=22, weight="bold")
        self.f_h2 = tkfont.Font(family=fam, size=13, weight="bold")
        self.f_body = tkfont.Font(family=fam, size=11)
        self.f_small = tkfont.Font(family=fam, size=10)
        self.f_caps = tkfont.Font(family="Liberation Sans Narrow", size=12, weight="bold")
        self.f_btn = tkfont.Font(family=fam, size=11, weight="bold")
        self.c = tk.Canvas(root, width=W, height=H, bg=FOG, highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.render()

    # ---------------------------------------------------------------- drawing
    def rrect(self, x0, y0, x1, y1, r=10, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
               x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.c.create_polygon(pts, smooth=True, **kw)

    def button(self, key, label, x0, y0, x1, y1, cmd, style="primary", enabled=True):
        fills = {"primary": (BUOY, "white", BUOY), "sea": (SEA, "white", SEA), "ghost": (PAPER, INK, "#b9b1a0"),
                 "chosen": (OK, "white", OK)}
        bg, fg, ol = fills[style]
        if not enabled:
            bg, fg, ol = "#e4ded2", "#9a958b", "#d6cfbf"
        tag = f"btn_{key}"
        self.rrect(x0, y0, x1, y1, r=8, fill=bg, outline=ol, width=1.5, tags=(tag,))
        self.c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=label, fill=fg, font=self.f_btn, tags=(tag,))
        self.hits[label] = (x0, y0, x1, y1)
        if enabled:
            self.c.tag_bind(tag, "<Button-1>", lambda _e: cmd())
            self.c.tag_bind(tag, "<Enter>", lambda _e: self.c.config(cursor="hand2"))
            self.c.tag_bind(tag, "<Leave>", lambda _e: self.c.config(cursor=""))

    def chrome(self):
        c = self.c
        c.create_rectangle(0, 0, W, 78, fill=INK, outline="")
        # lighthouse mark
        c.create_oval(22, 13, 74, 65, fill=SEA, outline="")
        c.create_polygon(40, 60, 44, 30, 52, 30, 56, 60, fill="white", outline="")
        c.create_rectangle(42, 40, 54, 45, fill=BUOY, outline="")
        c.create_rectangle(41, 51, 55, 55, fill=BUOY, outline="")
        c.create_rectangle(43, 24, 53, 30, fill="#ffd166", outline="")
        c.create_polygon(53, 26, 72, 19, 72, 33, fill="#ffd166", outline="", stipple="gray50")
        c.create_polygon(38, 22, 58, 22, 48, 17, fill="white", outline="")
        c.create_text(88, 30, text="SAFE", anchor="w", fill="white", font=self.f_brand)
        c.create_text(88 + self.f_brand.measure("SAFE") + 2, 30, text="HARBOR", anchor="w", fill=BUOY, font=self.f_brand)
        c.create_text(89, 58, text="Emergency accommodation for tonight · Complete one household registration",
                      anchor="w", fill="#c9d3d6", font=self.f_small)
        self.rrect(W - 236, 22, W - 22, 56, r=16, fill="#2f3a40", outline="")
        c.create_oval(W - 222, 34, W - 212, 44, fill="#6fd08c", outline="")
        c.create_text(W - 204, 39, text="Registration desk open", anchor="w", fill="white", font=self.f_small)
        c.create_rectangle(0, 78, W, 82, fill=BUOY, outline="")
        # step tracker
        c.create_rectangle(0, 82, W, 142, fill=PAPER, outline="")
        c.create_line(0, 142, W, 142, fill=LINE)
        seg = (W - 80) / 3
        for i, name in enumerate(STEPS):
            x = 40 + seg * i
            done, cur = i < self.step, i == self.step
            col = OK if done else (BUOY if cur else "#b9b1a0")
            c.create_oval(x, 97, x + 30, 127, fill=col if (done or cur) else PAPER, outline=col, width=2)
            c.create_text(x + 15, 112, text="✓" if done else str(i + 1), fill="white" if (done or cur) else col, font=self.f_btn)
            f = self.f_h2 if cur else self.f_body
            label = f"Step {i + 1} · {name}"
            c.create_text(x + 42, 112, text=label, anchor="w", fill=INK if cur else MUTED, font=f)
            if i < 2:
                c.create_line(x + 54 + f.measure(label), 112, x + seg - 12, 112, fill=OK if done else LINE, width=2, dash=() if done else (4, 4))

    def footer(self, left_text, x=28):
        c = self.c
        c.create_rectangle(0, H - 70, W, H, fill=PAPER, outline="")
        c.create_line(0, H - 70, W, H - 70, fill=LINE)
        c.create_text(x, H - 35, text=self.notice or left_text, anchor="w",
                      fill=BUOY_DK if self.notice else MUTED, font=self.f_btn if self.notice else self.f_small)

    def render(self):
        self.c.delete("all")
        self.hits = {}
        self.chrome()
        [self.screen_shelter, self.screen_household, self.screen_review, self.screen_done][self.step]()

    # --------------------------------------------------------------- screens
    def screen_shelter(self):
        c = self.c
        c.create_text(32, 172, text="Choose a shelter", anchor="w", fill=INK, font=self.f_h1)
        c.create_text(32, 200, text="Review the shelter options and their stated animal policies, then choose one.",
                      anchor="w", fill=MUTED, font=self.f_body)
        # neutral district sketch (pins seeded by list position only)
        mx0, my0, mx1, my1 = 32, 222, 372, 780
        self.rrect(mx0, my0, mx1, my1, r=14, fill="#e8e4da", outline=LINE)
        for gx in range(mx0 + 40, mx1, 62):
            c.create_line(gx, my0 + 6, gx - 18, my1 - 6, fill="#f8f5ee", width=6)
        for gy in range(my0 + 50, my1 - 30, 84):
            c.create_line(mx0 + 6, gy, mx1 - 6, gy + 14, fill="#f8f5ee", width=6)
        c.create_line(mx0 + 6, my0 + 300, mx1 - 6, my0 + 250, fill="#fbfaf6", width=12)
        yx, yy = (mx0 + mx1) / 2, my0 + 420
        c.create_oval(yx - 18, yy - 18, yx + 18, yy + 18, fill="#cfe0f0", outline="")
        c.create_oval(yx - 7, yy - 7, yx + 7, yy + 7, fill="#2d6cdf", outline="white", width=2)
        c.create_text(yx, yy + 30, text="You are here", fill=INK, font=self.f_small)
        pins = [(mx0 + 90, my0 + 120), (mx0 + 250, my0 + 90), (mx0 + 120, my0 + 250)]
        for i, (s, (px, py)) in enumerate(zip(SHELTERS, pins)):
            sel = s["id"] == self.selected_shelter
            col = OK if sel else SEA
            c.create_polygon(px - 14, py - 20, px + 14, py - 20, px, py + 6, fill=col, outline="", smooth=False)
            c.create_oval(px - 16, py - 38, px + 16, py - 6, fill=col, outline="white", width=2)
            c.create_text(px, py - 22, text=str(i + 1), fill="white", font=self.f_btn)
        c.create_text(mx0 + 16, my1 - 20, text="Map not to scale", anchor="w", fill=MUTED, font=self.f_small)
        # shelter cards
        x0, x1 = 396, W - 32
        y = 222
        for i, s in enumerate(SHELTERS):
            sel = s["id"] == self.selected_shelter
            ch = 172
            self.rrect(x0, y, x1, y + ch, r=14, fill=PAPER, outline=OK if sel else LINE, width=3 if sel else 1.5)
            c.create_oval(x0 + 18, y + 18, x0 + 50, y + 50, fill=OK if sel else SEA, outline="")
            c.create_text(x0 + 34, y + 34, text=str(i + 1), fill="white", font=self.f_btn)
            c.create_text(x0 + 64, y + 34, text=s["name"], anchor="w", fill=INK, font=self.f_h2)
            facts, policy = _split(s["details"])
            c.create_text(x0 + 64, y + 60, text=facts, anchor="w", fill=MUTED, font=self.f_body)
            self.rrect(x0 + 60, y + 78, x1 - 18, y + 122, r=8, fill=SEA_LT, outline="")
            c.create_text(x0 + 74, y + 100, text=policy, anchor="w", fill=INK, font=self.f_small, width=x1 - x0 - 110)
            if sel:
                self.button(f"sel{i}", f"✓ Selected: shelter {i + 1}", x1 - 250, y + 128, x1 - 18, y + 162,
                            lambda sid=s["id"], nm=s["name"]: self.select_shelter(sid, nm), style="chosen")
            else:
                self.button(f"sel{i}", f"Choose shelter {i + 1}", x1 - 250, y + 128, x1 - 18, y + 162,
                            lambda sid=s["id"], nm=s["name"]: self.select_shelter(sid, nm), style="ghost")
            y += ch + 14
        name = next((s["name"] for s in SHELTERS if s["id"] == self.selected_shelter), "none")
        self.footer(f"Selected shelter: {name}")
        self.button("next0", "Continue to household  ›", W - 290, H - 56, W - 28, H - 14, self.go_household,
                    enabled=self.selected_shelter is not None)

    def screen_household(self):
        c = self.c
        c.create_text(32, 172, text="Household animal manifest", anchor="w", fill=INK, font=self.f_h1)
        c.create_text(32, 200, text="Add each household animal who will accompany you. Leave empty only if none will accompany you.",
                      anchor="w", fill=MUTED, font=self.f_body)
        # add tiles (identical anatomy for each type)
        tw = (W - 64 - 2 * 20) / 3
        for i, (aid, label) in enumerate(ANIMAL_TYPES.items()):
            x0 = 32 + i * (tw + 20); y0 = 226
            self.rrect(x0, y0, x0 + tw, y0 + 168, r=14, fill=PAPER, outline=LINE, width=1.5)
            cx, cy = x0 + tw / 2, y0 + 56
            c.create_oval(cx - 34, cy - 34, cx + 34, cy + 34, fill=SEA_LT, outline="")
            self.animal_glyph(aid, cx, cy)
            c.create_text(cx, y0 + 108, text=label, fill=INK, font=self.f_h2)
            self.button(f"add_{aid}", f"Add {label.lower()}", x0 + 18, y0 + 124, x0 + tw - 18, y0 + 158,
                        lambda a=aid: self.add_animal(a), style="sea")
        # manifest list
        lx0, ly0, lx1 = 32, 414, W - 32
        self.rrect(lx0, ly0, lx1, ly0 + 350, r=14, fill=PAPER, outline=LINE, width=1.5)
        c.create_text(lx0 + 20, ly0 + 28, text="ACCOMPANYING ANIMALS", anchor="w", fill=SEA, font=self.f_caps)
        c.create_text(lx1 - 20, ly0 + 28, text=f"{len(self.manifest)} listed", anchor="e", fill=MUTED, font=self.f_small)
        c.create_line(lx0 + 20, ly0 + 48, lx1 - 20, ly0 + 48, fill=LINE)
        if not self.manifest:
            c.create_text((lx0 + lx1) / 2, ly0 + 190, text="No animals listed in the manifest.", fill=MUTED, font=self.f_body)
        for idx, entry in enumerate(self.manifest[:6]):
            ry = ly0 + 60 + idx * 46
            self.rrect(lx0 + 16, ry, lx1 - 16, ry + 38, r=8, fill="#f7f3ea", outline="")
            c.create_text(lx0 + 34, ry + 19, text=f"{idx + 1}.  {entry['displayName']}", anchor="w", fill=INK, font=self.f_body)
            self.button(f"rm{idx}", f"Remove #{idx + 1}", lx1 - 150, ry + 4, lx1 - 24, ry + 34,
                        lambda k=idx: self.remove_animal(k), style="ghost")
        if len(self.manifest) > 6:
            c.create_text(lx0 + 34, ly0 + 336, text=f"+ {len(self.manifest) - 6} more", anchor="w", fill=MUTED, font=self.f_small)
        self.footer("Changes to the manifest are kept until you submit.", x=270)
        self.button("back1", "‹  Back to shelters", 28, H - 56, 240, H - 14, lambda: self.goto(0), style="ghost")
        self.button("next1", "Continue to review  ›", W - 290, H - 56, W - 28, H - 14, lambda: self.goto(2))

    def animal_glyph(self, aid, cx, cy):
        c = self.c
        if aid == "dog":
            c.create_oval(cx - 16, cy - 14, cx + 16, cy + 16, fill=SEA, outline="")
            c.create_oval(cx - 24, cy - 16, cx - 10, cy + 6, fill=SEA, outline="")
            c.create_oval(cx + 10, cy - 16, cx + 24, cy + 6, fill=SEA, outline="")
            c.create_oval(cx - 5, cy + 3, cx + 5, cy + 10, fill=FOG, outline="")
        elif aid == "cat":
            c.create_oval(cx - 16, cy - 12, cx + 16, cy + 16, fill=SEA, outline="")
            c.create_polygon(cx - 16, cy - 2, cx - 14, cy - 24, cx - 2, cy - 10, fill=SEA, outline="")
            c.create_polygon(cx + 16, cy - 2, cx + 14, cy - 24, cx + 2, cy - 10, fill=SEA, outline="")
            c.create_oval(cx - 3, cy + 3, cx + 3, cy + 8, fill=FOG, outline="")
        else:
            for dx, dy, r in ((-12, -10, 6), (0, -16, 6), (12, -10, 6), (0, 6, 12)):
                c.create_oval(cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r, fill=SEA, outline="")

    def screen_review(self):
        c = self.c
        c.create_text(32, 172, text="Review and submit", anchor="w", fill=INK, font=self.f_h1)
        c.create_text(32, 200, text="Check both sections. Submitting sends one household registration for tonight.",
                      anchor="w", fill=MUTED, font=self.f_body)
        s = next((x for x in SHELTERS if x["id"] == self.selected_shelter), None)
        bx0, bx1 = 32, W - 32
        self.rrect(bx0, 226, bx1, 386, r=14, fill=PAPER, outline=LINE, width=1.5)
        c.create_text(bx0 + 22, 252, text="SHELTER", anchor="w", fill=SEA, font=self.f_caps)
        if s:
            facts, policy = _split(s["details"])
            c.create_text(bx0 + 22, 284, text=s["name"], anchor="w", fill=INK, font=self.f_h2)
            c.create_text(bx0 + 22, 312, text=facts, anchor="w", fill=MUTED, font=self.f_body)
            c.create_text(bx0 + 22, 340, text=policy, anchor="w", fill=INK, font=self.f_small, width=bx1 - bx0 - 240)
        self.button("edit_s", "Change shelter", bx1 - 190, 238, bx1 - 20, 272, lambda: self.goto(0), style="ghost")
        self.rrect(bx0, 404, bx1, 700, r=14, fill=PAPER, outline=LINE, width=1.5)
        c.create_text(bx0 + 22, 430, text="HOUSEHOLD ANIMAL MANIFEST", anchor="w", fill=SEA, font=self.f_caps)
        self.button("edit_m", "Edit manifest", bx1 - 190, 416, bx1 - 20, 450, lambda: self.goto(1), style="ghost")
        if not self.manifest:
            c.create_text(bx0 + 22, 480, text="No accompanying animals.", anchor="w", fill=MUTED, font=self.f_body)
        for idx, e in enumerate(self.manifest[:8]):
            c.create_text(bx0 + 22 + (idx // 4) * 440, 478 + (idx % 4) * 34, text=f"{idx + 1}.  {e['displayName']}",
                          anchor="w", fill=INK, font=self.f_body)
        if len(self.manifest) > 8:
            c.create_text(bx0 + 22, 620, text=f"+ {len(self.manifest) - 8} more", anchor="w", fill=MUTED, font=self.f_small)
        self.rrect(bx0, 716, bx1, 776, r=10, fill="#fbe9e1", outline="")
        c.create_text(bx0 + 22, 746, text="Bring medication, identification and any bedding you need for one night.",
                      anchor="w", fill=BUOY_DK, font=self.f_small)
        self.footer("Review both sections before submitting", x=280)
        self.button("back2", "‹  Back to household", 28, H - 56, 250, H - 14, lambda: self.goto(1), style="ghost")
        self.button("submit", "Submit registration", W - 290, H - 56, W - 28, H - 14, self.submit)

    def screen_done(self):
        c = self.c
        c.create_oval(W / 2 - 50, 280, W / 2 + 50, 380, fill=OK, outline="")
        c.create_line(W / 2 - 22, 332, W / 2 - 4, 350, W / 2 + 26, 312, fill="white", width=8, capstyle="round")
        c.create_text(W / 2, 430, text="Registration submitted", fill=INK, font=self.f_h1)
        c.create_text(W / 2, 466, text="Your household registration has been saved.", fill=MUTED, font=self.f_body)

    # ---------------------------------------------------------------- actions
    def goto(self, step):
        self.step = step; self.notice = ""; self.render()

    def go_household(self):
        if self.selected_shelter is None:
            self.notice = "Select a shelter before continuing."; self.render(); return
        self.goto(1)

    def select_shelter(self, shelter_id: str, name: str) -> None:
        self.selected_shelter = shelter_id
        self.events.append({"event": "select_shelter", "shelterId": shelter_id})
        self.notice = ""; self.render()

    def add_animal(self, animal_type: str) -> None:
        entry = {"type": animal_type, "displayName": ANIMAL_TYPES[animal_type]}
        self.manifest.append(entry); self.events.append({"event": "add_animal", "type": animal_type}); self.render()

    def remove_animal(self, index: int) -> None:
        if not 0 <= index < len(self.manifest):
            return
        entry = self.manifest.pop(index); self.events.append({"event": "remove_animal", "type": entry["type"]}); self.render()

    def submit(self) -> None:
        if self.selected_shelter is None:
            self.notice = "Select a shelter before submitting."; self.render(); return
        self.events.append({"event": "submit", "shelterId": self.selected_shelter, "animalTypes": [entry["type"] for entry in self.manifest]})
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        shelter = next(item for item in SHELTERS if item["id"] == self.selected_shelter)
        payload = {"status": "submitted", "selectedShelterId": self.selected_shelter, "selectedShelter": {"shelterId": self.selected_shelter, "acceptsOrdinaryDogs": shelter["acceptsOrdinaryDogs"]}, "householdAnimals": self.manifest, "events": self.events}
        with open(os.path.join(OUTPUT_DIR, "registration.json"), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        self.step = 3; self.render()


if __name__ == "__main__":
    window = tk.Tk(); ShelterRegister(window); window.mainloop()
