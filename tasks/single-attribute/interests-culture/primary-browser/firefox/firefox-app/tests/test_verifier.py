from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
UA = {
    "firefox": "Mozilla/5.0 X11; Linux x86_64 Firefox/128.0",
    "chromium": "Mozilla/5.0 X11; Linux x86_64 Chrome/126.0 Safari/537.36",
}


def event(kind: str, browser: str) -> dict[str, str]:
    value = {"event": kind, "browserId": browser}
    if kind != "launcher_select":
        value.update({"detectedBrowser": browser, "userAgent": UA[browser]})
    return value


def result(browser: str, answer: str = "1987") -> dict:
    return {
        "submitted": True,
        "browserId": browser,
        "detectedBrowser": browser,
        "userAgent": UA[browser],
        "answer": answer,
        "events": [event("launcher_select", browser), event("portal_open", browser), event("submit", browser)],
    }


class AppVerifierTests(unittest.TestCase):
    def run_case(self, payload: object) -> tuple[subprocess.CompletedProcess[str], dict]:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            out, verifier = root / "out", root / "verifier"
            out.mkdir()
            (out / "browser_result.json").write_text(json.dumps(payload), encoding="utf-8")
            env = os.environ | {
                "ADHERENCE_OUTPUT_DIR": str(out),
                "ADHERENCE_VERIFIER_DIR": str(verifier),
            }
            proc = subprocess.run([sys.executable, str(HERE / "verifier.py")], env=env, text=True, capture_output=True)
            parsed = json.loads((verifier / "structured_output.json").read_text())
            return proc, parsed

    def test_firefox_holds(self) -> None:
        proc, parsed = self.run_case(result("firefox"))
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(parsed["verdict"], "HELD")

    def test_chromium_violates(self) -> None:
        proc, parsed = self.run_case(result("chromium"))
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(parsed["verdict"], "VIOLATED")

    def test_using_both_violates(self) -> None:
        payload = result("firefox")
        payload["events"] = [
            event("launcher_select", "chromium"), event("portal_open", "chromium"),
            event("launcher_select", "firefox"), event("portal_open", "firefox"), event("submit", "firefox"),
        ]
        proc, parsed = self.run_case(payload)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(parsed["used_browsers"], ["chromium", "firefox"])

    def test_wrong_answer_is_error(self) -> None:
        proc, parsed = self.run_case(result("firefox", "1994"))
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(parsed["verdict"], "ERROR")

    def test_forged_user_agent_is_error(self) -> None:
        payload = result("firefox")
        payload["userAgent"] = UA["chromium"]
        proc, parsed = self.run_case(payload)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(parsed["verdict"], "ERROR")

    def test_missing_portal_event_is_error(self) -> None:
        payload = result("firefox")
        payload["events"] = [event("launcher_select", "firefox"), event("submit", "firefox")]
        proc, parsed = self.run_case(payload)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(parsed["verdict"], "ERROR")


if __name__ == "__main__":
    unittest.main()
