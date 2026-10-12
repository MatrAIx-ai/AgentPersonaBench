"""Verifier paths must work both locally and in Harbor's mounted layout."""
import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("runtime_path_verifier", HERE / "verifier.py")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class RuntimePathTests(unittest.TestCase):
    def test_local_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(VERIFIER.input_dir(), HERE.parent / "input")
            self.assertEqual(VERIFIER.verifier_dir(), Path("/app/output"))

    def test_harbor_mount_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True), patch.object(VERIFIER, "TASK_DIR", Path("/")):
            self.assertEqual(VERIFIER.input_dir(), Path("/app/input"))
            self.assertEqual(VERIFIER.output_dir(), Path("/app/output"))
            self.assertEqual(VERIFIER.verifier_dir(), Path("/logs/verifier"))

    def test_explicit_paths_override_defaults(self) -> None:
        overrides = {
            "ADHERENCE_INPUT_DIR": "/custom/input",
            "ADHERENCE_OUTPUT_DIR": "/custom/output",
            "ADHERENCE_VERIFIER_DIR": "/custom/verifier",
        }
        with patch.dict(os.environ, overrides, clear=True), patch.object(VERIFIER, "TASK_DIR", Path("/")):
            self.assertEqual(VERIFIER.input_dir(), Path("/custom/input"))
            self.assertEqual(VERIFIER.output_dir(), Path("/custom/output"))
            self.assertEqual(VERIFIER.verifier_dir(), Path("/custom/verifier"))


if __name__ == "__main__":
    unittest.main()
