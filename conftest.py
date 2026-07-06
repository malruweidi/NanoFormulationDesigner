"""Repo-root pytest configuration.

- Disables .pyc generation for the session so `test_no_pyc_committed` stays
  stable (belt-and-suspenders with PYTHONDONTWRITEBYTECODE in CI).
- Ensures the src/ layout is importable even without an editable install.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
