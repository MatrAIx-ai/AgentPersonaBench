import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
CORE_SRC = REPO_ROOT / "packages" / "playground" / "src"
APP_ROOT = REPO_ROOT / "application" / "playground"
RUNTIME_ROOT = REPO_ROOT / "environment" / "runtime"

# Put the extracted core package and app/runtime roots on sys.path.
for path in reversed((str(REPO_ROOT), str(RUNTIME_ROOT), str(CORE_SRC), str(APP_ROOT))):
    if path not in sys.path:
        sys.path.insert(0, path)
