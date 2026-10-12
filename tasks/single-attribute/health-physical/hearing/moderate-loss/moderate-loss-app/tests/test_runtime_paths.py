"""Check the inner Harbor and outer host verifier output contracts."""
import importlib.util
import os
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location("app_paths", Path(__file__).with_name("verifier.py"))
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)

with mock.patch.dict(os.environ, {}, clear=True):
    assert verifier.verifier_dir() == verifier.output_dir()
    with mock.patch.dict(os.environ, {"ADHERENCE_OUTPUT_DIR": "/custom/artifacts"}):
        assert verifier.verifier_dir() == Path("/custom/artifacts")
    with mock.patch.object(verifier, "TESTS_DIR", Path("/tests")):
        assert verifier.verifier_dir() == Path("/logs/verifier")
        with mock.patch.dict(os.environ, {"ADHERENCE_VERIFIER_DIR": "/custom/results"}):
            assert verifier.verifier_dir() == Path("/custom/results")

print("moderate-loss app runtime paths passed")
