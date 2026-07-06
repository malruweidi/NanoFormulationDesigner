"""The designer must depend only on materials + user composition.

We copy the data dir, blank the formulations/components/outcomes tables to
header-only, and confirm a full design still runs end-to-end against that DB.
"""
import shutil
from pathlib import Path

from nanoform.database import Database, find_data_dir
from nanoform.designer import DesignInput, design


def _blank_to_header(path: Path):
    header = path.read_text(encoding="utf-8").splitlines()[0]
    path.write_text(header + "\n", encoding="utf-8")


def test_design_runs_with_empty_formulation_tables(tmp_path):
    src = find_data_dir()
    dest = tmp_path / "data"
    shutil.copytree(src, dest)
    for name in ("formulations.csv", "formulation_components.csv", "outcomes.csv"):
        _blank_to_header(dest / "relational" / name)

    db = Database(data_dir=dest)
    inp = DesignInput(
        family="niosome", route="topical", design_goal="stability",
        drug="Dexamethasone", drug_mol_percent=5.0, solvent="Ethanol",
        components=[("Span 60", "surfactant", 47.5), ("Cholesterol", "sterol", 47.5),
                    ("Dicetyl phosphate", "charge_inducer", 5.0)],
    )
    r = design(inp, db=db)
    assert 0.0 <= r.nanoform_score <= 1.0
    assert r.batch_table and any(row["role"] == "drug" for row in r.batch_table)
    assert r.cqa("nanoform_score") is not None


def test_formulation_tables_ship_without_outcome_data():
    db = Database(data_dir=find_data_dir())
    # outcomes must be header-only in the shipped seed (no fabricated outcomes).
    import pandas as pd
    outcomes = pd.read_csv(db.rel / "outcomes.csv")
    assert len(outcomes) == 0
