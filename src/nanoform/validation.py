"""Database validation.

Structural + content checks used by scripts/validate_database.py and the test
suite. Returns a report dict; `ok` is False if any hard error is found.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from . import schema
from .database import Database, get_database


def validate_database(db: Optional[Database] = None) -> Dict[str, Any]:
    db = db or get_database()
    errors: List[str] = []
    warnings: List[str] = []

    # ---- Required columns ------------------------------------------------ #
    _check_columns(db.materials, schema.MATERIALS_COLUMNS, "materials.csv", errors)
    _check_columns(db.properties, schema.MATERIAL_PROPERTIES_COLUMNS, "material_properties.csv", errors)
    _check_columns(db.sources, schema.SOURCES_COLUMNS, "sources.csv", errors)

    # ---- Duplicate material IDs ------------------------------------------ #
    dups = db.materials["material_id"][db.materials["material_id"].duplicated()].tolist()
    if dups:
        errors.append(f"Duplicate material_id(s): {sorted(set(dups))}")

    # ---- Every material has a type in the enum --------------------------- #
    bad_types = sorted(set(db.materials["material_type"]) - set(schema.MATERIAL_TYPES))
    if bad_types:
        errors.append(f"Unknown material_type(s): {bad_types}")

    # ---- Orphan properties (material_id not in materials) ---------------- #
    mat_ids = set(db.materials["material_id"])
    orphans = sorted(set(db.properties["material_id"]) - mat_ids)
    if orphans:
        errors.append(f"Property rows reference unknown material_id(s): {orphans[:10]}")

    # ---- Property provenance --------------------------------------------- #
    missing_src = db.properties[db.properties["source_id"].astype(str).str.strip() == ""]
    if len(missing_src):
        warnings.append(f"{len(missing_src)} property rows have no source_id.")

    # ---- Required properties per material type --------------------------- #
    have = db.properties.groupby("material_id")["property_name"].apply(set).to_dict()
    req_missing = []
    for _, m in db.materials.iterrows():
        present = have.get(m["material_id"], set())
        for req in schema.REQUIRED_PROPERTIES.get(m["material_type"], []):
            if req not in present:
                req_missing.append(f"{m['name']} missing required {req}")
    if req_missing:
        warnings.append(f"{len(req_missing)} materials miss a type-required property "
                        f"(e.g. {req_missing[0]}).")

    # ---- Numeric sanity -------------------------------------------------- #
    neg_mw = 0
    for _, p in db.properties[db.properties["property_name"] == "MW"].iterrows():
        try:
            if float(p["value"]) <= 0:
                neg_mw += 1
        except (ValueError, TypeError):
            neg_mw += 1
    if neg_mw:
        errors.append(f"{neg_mw} non-positive/non-numeric MW values.")

    return {
        "ok": len(errors) == 0,
        "n_materials": len(db.materials),
        "n_property_rows": len(db.properties),
        "errors": errors,
        "warnings": warnings,
        "required_missing": req_missing,
    }


def _check_columns(df: pd.DataFrame, cols: List[str], label: str, errors: List[str]):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        errors.append(f"{label} missing columns: {missing}")
