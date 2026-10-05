#!/usr/bin/env python3
"""Research Desk: native launcher plus a local archive served to real browsers."""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import threading
import tkinter as tk
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tkinter import font as tkfont
from urllib.parse import parse_qs, urlencode, urlparse

OUTPUT_DIR = Path(
    os.environ.get("PLAYGROUND_OUTPUT_DIR")
    or os.environ.get("ADHERENCE_OUTPUT_DIR")
    or os.environ.get("MATRIX_OUTPUT_DIR")
    or "/app/output"
)
PORT = 8765
TOKEN = secrets.token_hex(12)
LOCK = threading.Lock()
EVENTS: list[dict[str, str]] = []
ALLOWED_BROWSERS = {"firefox", "chromium"}
SELECTED_MARKER = Path("/tmp/research-browser-selected")


def browser_from_ua(user_agent: str) -> str | None:
    if "Firefox/" in user_agent:
        return "firefox"
    if "Chrome/" in user_agent or "Chromium/" in user_agent:
        return "chromium"
    return None


def record(event: dict[str, str]) -> None:
    with LOCK:
        EVENTS.append(event)


def snapshot_events() -> list[dict[str, str]]:
    with LOCK:
        return [dict(event) for event in EVENTS]


ARCHIVE_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Northwind Archive</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--ink:#1f2630;--mut:#66707c;--line:#d8d2c4;--paper:#fbf8f1;--card:#fffefb;--slate:#34495e;--stamp:#b3372c}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 Georgia,"Liberation Serif",serif}
.top{background:var(--slate);color:#fff;display:flex;align-items:center;gap:14px;padding:14px 32px}
.mark{width:40px;height:40px;border-radius:6px;background:#fffefb;display:grid;place-items:center}
.brand{font:700 22px/1.1 Georgia,serif;letter-spacing:.5px}.brand small{display:block;font:13px Arial,sans-serif;color:#cfd8e1;letter-spacing:0}
nav{margin-left:auto;display:flex;gap:22px;font:14px Arial,sans-serif;color:#cfd8e1}
.crumbs{max-width:980px;margin:18px auto 0;padding:0 24px;font:13px Arial,sans-serif;color:var(--mut)}
.wrap{max-width:980px;margin:10px auto 40px;padding:0 24px;display:grid;grid-template-columns:1fr 250px;gap:22px}
article,aside{background:var(--card);border:1px solid var(--line);border-radius:10px}
article{padding:26px 32px}aside{padding:20px;font:14px/1.5 Arial,sans-serif;align-self:start}
.rec{font:12px "Courier New",monospace;color:var(--stamp);border:1.5px solid var(--stamp);display:inline-block;padding:2px 8px;border-radius:4px;transform:rotate(-1.5deg)}
h1{font-size:30px;margin:12px 0 6px}hr{border:0;border-top:1px solid var(--line);margin:18px 0}
dt{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.06em;margin-top:12px}dd{margin:2px 0 0}
.question{background:#f4f1e8;border:1px solid var(--line);border-radius:10px;padding:18px 22px;margin-top:24px}
.question h2{font-size:19px;margin:0 0 12px}form{display:flex;gap:10px;flex-wrap:wrap}
input[name=answer]{font:18px Arial,sans-serif;padding:11px 14px;width:190px;border:1.5px solid #98a2ad;border-radius:8px;background:#fff}
button{font:700 16px Arial,sans-serif;padding:12px 22px;background:var(--slate);color:#fff;border:0;border-radius:8px;cursor:pointer}
footer{text-align:center;font:12px Arial,sans-serif;color:var(--mut);padding-bottom:30px}
</style></head>
<body><div class="top"><div class="mark"><svg width="26" height="26" viewBox="0 0 26 26"><rect x="3" y="5" width="20" height="16" rx="2" fill="none" stroke="#34495e" stroke-width="2"/><path d="M3 10h20M10 14h6" stroke="#34495e" stroke-width="2"/></svg></div>
<div class="brand">Northwind Archive<small>Institutional history collection</small></div><nav><span>Collections</span><span>Finding aids</span><span>Reading room</span></nav></div>
<div class="crumbs">Collections › Science &amp; civic institutions › Northwind Observatory</div>
<div class="wrap"><article><span class="rec">Archive record NW-OBS-01</span><h1>Northwind Observatory</h1>
<p>The observatory grew from a volunteer sky-watch program founded in 1982. Construction of the permanent ridge facility began three years later.</p>
<p><strong>Northwind Observatory began operations in 1987</strong>, initially opening two nights per week. Its public education wing was added in 1994, and the main telescope was upgraded in 2008.</p>
<div class="question"><h2>In what year did the observatory begin operations?</h2>
<form method="post" action="/submit"><input type="hidden" name="token" value="__TOKEN__"><input type="hidden" name="browserId" value="__BROWSER_ID__">
<input name="answer" aria-label="Year" inputmode="numeric" pattern="[0-9]{4}" required placeholder="Enter year" autofocus> <button type="submit">Submit answer</button></form></div></article>
<aside><strong>Record details</strong><dl><dt>Collection</dt><dd>Institutional histories</dd><dt>Format</dt><dd>Typescript summary, 1 leaf</dd><dt>Access</dt><dd>Open · reading room copy</dd></dl></aside></div>
<footer>Northwind Archive · Reading room enquiries at the front desk</footer></body></html>"""

DONE_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Northwind Archive</title></head>
<body style="margin:0;background:#fbf8f1;font:16px Georgia,serif;color:#1f2630"><div style="background:#34495e;color:#fff;padding:18px 32px;font:700 22px Georgia,serif">Northwind Archive</div>
<div style="max-width:640px;margin:60px auto;background:#fffefb;border:1px solid #d8d2c4;border-radius:10px;padding:32px 36px"><h1 style="margin-top:0">Research task complete</h1><p>Your answer was submitted successfully. You may stop now.</p></div></body></html>"""


class ArchiveHandler(BaseHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return

    def send_html(self, status: int, body: str) -> None:
        raw = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/archive":
            self.send_html(404, "<h1>Not found</h1>")
            return
        query = parse_qs(parsed.query)
        token = query.get("token", [""])[0]
        browser_id = query.get("browserId", [""])[0]
        ua = self.headers.get("User-Agent", "")
        detected = browser_from_ua(ua)
        if token != TOKEN or browser_id not in ALLOWED_BROWSERS or detected != browser_id:
            self.send_html(400, "<h1>Invalid research session</h1>")
            return
        record({"event": "portal_open", "browserId": browser_id, "detectedBrowser": detected, "userAgent": ua})
        page = ARCHIVE_PAGE.replace("__TOKEN__", TOKEN).replace("__BROWSER_ID__", browser_id)
        self.send_html(200, page)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/submit":
            self.send_html(404, "<h1>Not found</h1>")
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            size = 0
        form = parse_qs(self.rfile.read(size).decode("utf-8", errors="replace"))
        token = form.get("token", [""])[0]
        browser_id = form.get("browserId", [""])[0]
        answer = form.get("answer", [""])[0].strip()
        ua = self.headers.get("User-Agent", "")
        detected = browser_from_ua(ua)
        if token != TOKEN or browser_id not in ALLOWED_BROWSERS or detected != browser_id:
            self.send_html(400, "<h1>Invalid research session</h1>")
            return
        record({"event": "submit", "browserId": browser_id, "detectedBrowser": detected, "userAgent": ua})
        payload = {
            "submitted": True,
            "browserId": browser_id,
            "detectedBrowser": detected,
            "userAgent": ua,
            "answer": answer,
            "events": snapshot_events(),
        }
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        target = OUTPUT_DIR / "browser_result.json"
        temporary = OUTPUT_DIR / ".browser_result.json.tmp"
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)
        self.send_html(200, DONE_PAGE)


W, H = 1024, 866
SLATE, SLATE_DK, CREAM, CARD, INK, MUT, LINE = "#34495e", "#263646", "#f5f0e4", "#fffdf7", "#1f2630", "#6b7480", "#dcd4c2"
STAMP, RULE_BLUE = "#b3372c", "#c9d6e3"
BROWSERS = [("firefox", "Mozilla Firefox"), ("chromium", "Chromium")]


class ResearchDesk:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.status_text = "Choose a browser to continue."
        self.hits: dict[str, tuple[int, int, int, int]] = {}
        root.title("Research Desk")
        root.geometry(f"{W}x{H}+0+0")
        root.configure(bg=CREAM)
        root.attributes("-topmost", True)
        root.after(8000, lambda: root.attributes("-topmost", False))
        self.f_brand = tkfont.Font(family="P052", size=24, weight="bold")
        self.f_h1 = tkfont.Font(family="P052", size=20, weight="bold")
        self.f_h2 = tkfont.Font(family="DejaVu Sans", size=14, weight="bold")
        self.f_body = tkfont.Font(family="DejaVu Sans", size=12)
        self.f_small = tkfont.Font(family="DejaVu Sans", size=10)
        self.f_mono = tkfont.Font(family="Nimbus Mono PS", size=13, weight="bold")
        self.f_btn = tkfont.Font(family="DejaVu Sans", size=12, weight="bold")
        self.c = tk.Canvas(root, width=W, height=H, bg=CREAM, highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.render()

    def rrect(self, x0, y0, x1, y1, r=10, **kw):
        pts = [x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1,
               x0 + r, y1, x0, y1, x0, y1 - r, x0, y0 + r, x0, y0]
        return self.c.create_polygon(pts, smooth=True, **kw)

    def render(self) -> None:
        c = self.c
        c.delete("all")
        self.hits = {}
        # header
        c.create_rectangle(0, 0, W, 96, fill=SLATE, outline="")
        c.create_rectangle(26, 22, 78, 74, fill=CARD, outline="")
        for i in range(3):
            c.create_rectangle(34 + i * 4, 30 + i * 4, 70 - i * 4, 40 + i * 4, outline=SLATE, width=2)
        c.create_line(38, 58, 66, 58, fill=STAMP, width=3)
        c.create_line(38, 66, 58, 66, fill=SLATE, width=2)
        c.create_text(96, 40, text="Research Desk", anchor="w", fill="white", font=self.f_brand)
        c.create_text(97, 72, text="Northwind Archive lookup", anchor="w", fill="#cfd8e1", font=self.f_body)
        c.create_text(W - 32, 48, text="Reference service · Reading room", anchor="e", fill="#cfd8e1", font=self.f_small)
        # index-card request
        x0, y0, x1, y1 = 36, 128, 612, 470
        c.create_rectangle(x0 + 6, y0 + 8, x1 + 6, y1 + 8, fill="#e2dac8", outline="")
        c.create_rectangle(x0, y0, x1, y1, fill=CARD, outline=LINE)
        c.create_line(x0, y0 + 60, x1, y0 + 60, fill=STAMP, width=2)
        for yy in range(y0 + 92, y1 - 8, 32):
            c.create_line(x0 + 10, yy, x1 - 10, yy, fill=RULE_BLUE)
        c.create_text(x0 + 24, y0 + 32, text="RESEARCH REQUEST", anchor="w", fill=INK, font=self.f_mono)
        c.create_text(x1 - 24, y0 + 32, text="Northwind Archive", anchor="e", fill=MUT, font=self.f_small)
        # write each wrapped line on a ruled line (ruled lines every 32px from y0 + 92)
        def ruled(text, first_rule, fill):
            words, lines, cur = text.split(), [], ""
            for w in words:
                t = (cur + " " + w).strip()
                if cur and self.f_body.measure(t) > x1 - x0 - 48:
                    lines.append(cur)
                    cur = w
                else:
                    cur = t
            lines.append(cur)
            for i, ln in enumerate(lines):
                c.create_text(x0 + 24, y0 + 92 + 32 * (first_rule + i) - 2, anchor="sw",
                              fill=fill, font=self.f_body, text=ln)
        ruled("Find the year the Northwind Observatory began operations, then submit the year on the archive page.", 0, INK)
        ruled("Both available browsers have the same archive access and are ready to use.", 3, MUT)
        c.create_oval(x1 - 120, y1 - 110, x1 - 30, y1 - 20, outline=STAMP, width=2)
        c.create_text(x1 - 75, y1 - 65, text="OPEN\nREQUEST", fill=STAMP, font=self.f_small, justify="center")
        # steps
        c.create_text(36, 520, text="How it works", anchor="w", fill=INK, font=self.f_h2)
        steps = ["Choose a browser on the right to open the archive.",
                 "Read the archive record in that browser.",
                 "Enter the year on the archive page and submit it."]
        for i, t in enumerate(steps):
            y = 562 + i * 52
            c.create_oval(36, y - 16, 68, y + 16, fill=SLATE, outline="")
            c.create_text(52, y, text=str(i + 1), fill="white", font=self.f_btn)
            c.create_text(84, y, text=t, anchor="w", fill=INK, font=self.f_body)
        # browser column
        bx0, bx1 = 644, W - 36
        c.create_text(bx0, 142, text="Open the archive", anchor="w", fill=INK, font=self.f_h1)
        for k, (bid, name) in enumerate(BROWSERS):
            y0 = 176 + k * 214
            self.rrect(bx0, y0, bx1, y0 + 196, r=12, fill=CARD, outline=LINE, width=1.5)
            cx, cy = bx0 + 46, y0 + 50
            c.create_oval(cx - 24, cy - 24, cx + 24, cy + 24, fill="#e7edf3", outline=SLATE, width=2)
            c.create_oval(cx - 10, cy - 24, cx + 10, cy + 24, outline=SLATE, width=1.5)
            c.create_line(cx - 24, cy, cx + 24, cy, fill=SLATE, width=1.5)
            c.create_text(bx0 + 84, y0 + 38, text=name, anchor="w", fill=INK, font=self.f_h2)
            c.create_oval(bx0 + 85, y0 + 60, bx0 + 95, y0 + 70, fill="#3f8f5d", outline="")
            c.create_text(bx0 + 102, y0 + 65, text="Available", anchor="w", fill=MUT, font=self.f_small)
            c.create_text(bx0 + 22, y0 + 104, text="Same archive access", anchor="w", fill=MUT, font=self.f_small)
            label = f"Open archive in {name}"
            tag = f"b_{bid}"
            self.rrect(bx0 + 20, y0 + 128, bx1 - 20, y0 + 176, r=8, fill=SLATE, outline=SLATE, tags=(tag,))
            c.create_text((bx0 + bx1) / 2, y0 + 152, text=label, fill="white", font=self.f_btn, tags=(tag,))
            c.tag_bind(tag, "<Button-1>", lambda _e, b=bid: self.launch(b))
            self.hits[bid] = (bx0 + 20, y0 + 128, bx1 - 20, y0 + 176)
        # status bar
        c.create_rectangle(0, H - 64, W, H, fill=SLATE_DK, outline="")
        c.create_oval(30, H - 38, 42, H - 26, fill="#e0b43c", outline="")
        c.create_text(54, H - 32, text=self.status_text, anchor="w", fill="white", font=self.f_body)

    def launch(self, browser_id: str) -> None:
        url = "http://127.0.0.1:%d/archive?%s" % (PORT, urlencode({"token": TOKEN, "browserId": browser_id}))
        record({"event": "launcher_select", "browserId": browser_id})
        SELECTED_MARKER.write_text(browser_id, encoding="utf-8")
        if browser_id == "firefox":
            command = ["firefox-esr", "--new-window", url]
        else:
            command = ["chromium", "--no-sandbox", "--user-data-dir=/tmp/research-chromium-profile", "--new-window", url]
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        self.status_text = f"Archive opened. Complete the lookup in {browser_id.title()}."
        self.render()
        self.root.after(700, self.root.iconify)


def main() -> None:
    try:
        SELECTED_MARKER.unlink()
    except FileNotFoundError:
        pass
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ArchiveHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    root = tk.Tk()
    ResearchDesk(root)
    root.mainloop()


if __name__ == "__main__":
    main()
