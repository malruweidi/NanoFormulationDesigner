"""The database must load after a plain package import (no cwd assumptions)."""
import nanoform
from nanoform.database import get_database


def test_package_version():
    assert nanoform.__version__


def test_database_loads_after_import():
    db = get_database()
    assert len(db.materials) >= 150
    # internal-constant tables are loaded too (Phase 5)
    assert not db.coverage_summary.empty
    assert not db.unresolved_missing.empty


def test_env_var_override(tmp_path, monkeypatch):
    # NANOFORM_DATA_DIR must take precedence when it points at a valid data dir.
    import shutil
    from nanoform.database import find_data_dir, Database
    real = find_data_dir()
    dest = tmp_path / "data"
    shutil.copytree(real, dest)
    monkeypatch.setenv("NANOFORM_DATA_DIR", str(dest))
    assert find_data_dir() == dest
    db = Database()
    assert len(db.materials) >= 150
