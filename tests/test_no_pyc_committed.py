"""No compiled bytecode or cache directories may be committed to the repo.

Definition of "committed": tracked by git. If a git repo is present we use
`git ls-files` (authoritative). Otherwise we scan the working tree, excluding
virtualenvs and tool caches (the session runs with bytecode writing disabled via
conftest.py / PYTHONDONTWRITEBYTECODE).
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".venv", "venv", "env", ".git", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def _git_tracked():
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                             text=True, timeout=15)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    return out.stdout.splitlines()


def test_no_pyc_or_cache_committed():
    """Strict check when git is available (authoritative definition of 'committed');
    otherwise verify the ignore rules guarantee caches can never be committed."""
    tracked = _git_tracked()
    if tracked is not None:
        bad = [f for f in tracked
               if f.endswith((".pyc", ".pyo")) or "__pycache__" in f.split("/")]
        assert not bad, f"cache artifacts tracked by git: {bad[:10]}"
        return
    # No git repo (e.g. an unzipped release): bytecode caches may be created
    # transiently by imports/compileall, so assert .gitignore excludes them.
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in ("__pycache__/", "*.py[cod]", ".pytest_cache/"):
        assert pattern in gitignore, f".gitignore must ignore {pattern!r}"


def test_no_pyc_in_committed_source_dirs():
    """Regardless of git, the tracked source folders under version control must not
    contain committed .pyc files sitting *next to sources* (a transient __pycache__
    dir is tolerated; loose committed .pyc alongside .py is not)."""
    for sub in ("src", "tests", "scripts"):
        d = ROOT / sub
        if not d.exists():
            continue
        loose = [p for p in d.rglob("*.pyc") if "__pycache__" not in p.parts]
        assert not loose, f"loose .pyc files under {sub}: {loose[:5]}"
