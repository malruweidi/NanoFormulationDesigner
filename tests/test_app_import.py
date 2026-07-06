"""app.py must be syntactically valid and importable in a headless-safe way.

We compile/parse rather than execute, because executing Streamlit widget calls
outside a ScriptRunContext is noisy and not the property under test.
"""
import ast
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"


def test_app_exists():
    assert APP.exists()


def test_app_parses():
    ast.parse(APP.read_text(encoding="utf-8"))


def test_app_compiles():
    # Raises PyCompileError on syntax error.
    py_compile.compile(str(APP), doraise=True)


def test_app_imports_nanoform_symbols():
    src = APP.read_text(encoding="utf-8")
    for token in ("from nanoform", "get_database", "design", "run_sanity"):
        assert token in src
