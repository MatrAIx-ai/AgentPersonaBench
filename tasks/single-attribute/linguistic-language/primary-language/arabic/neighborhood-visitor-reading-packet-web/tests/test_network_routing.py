"""Test the solver's routing branch without starting Docker."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
WINDOWS_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(WINDOWS_BASH) if os.name == "nt" and WINDOWS_BASH.exists() else shutil.which("bash")


@unittest.skipUnless(BASH, "Bash is required for shell routing tests")
class NetworkRouting(unittest.TestCase):
    def route(self, platform, url):
        source = (ROOT / "solution/solve.sh").read_text(encoding="utf-8")
        start = source.index("PROXY_IN_CONTAINER=")
        end = source.index("\ndocker run --rm", start)
        script = ('set -euo pipefail\nuname() { printf "%s\\n" "$TEST_PLATFORM"; }\n'
                  + source[start:end]
                  + '\nprintf "%s\\n" "$PROXY_IN_CONTAINER" "$'
                  + '{DOCKER_NETWORK_ARGS[@]}"\n')
        result = subprocess.run([BASH, "-c", script], text=True, capture_output=True,
                                env={**os.environ, "TEST_PLATFORM": platform, "LLM_PROXY_URL": url},
                                timeout=20, check=True)
        return result.stdout.splitlines()

    def test_linux_preserves_host_network(self):
        self.assertEqual(self.route("Linux", "http://127.0.0.1:8000/v1"),
                         ["http://127.0.0.1:8000/v1", "--network=host"])

    def test_darwin_rewrites_loopback(self):
        for host in ("localhost", "127.0.0.1"):
            with self.subTest(host=host):
                self.assertEqual(self.route("Darwin", f"http://{host}:8000/v1"),
                                 ["http://host.docker.internal:8000/v1",
                                  "--add-host=host.docker.internal:host-gateway"])

    def test_darwin_preserves_remote_proxy(self):
        self.assertEqual(self.route("Darwin", "https://proxy.example.test/v1"),
                         ["https://proxy.example.test/v1",
                          "--add-host=host.docker.internal:host-gateway"])


if __name__ == "__main__":
    unittest.main()
