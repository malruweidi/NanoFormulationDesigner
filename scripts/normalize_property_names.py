"""Normalize property_name values in material_properties.csv to canonical form.

Idempotent maintenance tool: folds aliases (e.g. 'molecular_weight' -> 'MW')
using nanoform.schema and rewrites the CSV in place. Prints a diff summary.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nanoform import schema  # noqa: E402


def main() -> int:
    path = ROOT / "data" / "relational" / "material_properties.csv"
    df = pd.read_csv(path, dtype=str).fillna("")
    before = df["property_name"].copy()
    df["property_name"] = df["property_name"].map(schema.canonical_property)
    changed = (before != df["property_name"]).sum()
    df.to_csv(path, index=False)
    print(f"Normalized {changed} property_name value(s) in {path.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
