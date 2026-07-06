"""Build wide internal-constant tables and coverage/missing-value reports.

Derives:
    data/internal_constants/internal_constants_wide.csv
    data/internal_constants/coverage_summary.csv
    data/internal_constants/unresolved_missing_values.csv
    data/examples/example_user_designs.csv
    data/examples/example_batch_table.csv
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

REL = ROOT / "data" / "relational"
CONST = ROOT / "data" / "internal_constants"
EX = ROOT / "data" / "examples"

# Properties considered "important" per material type for the missing-values report.
IMPORTANT = {
    "api": ["MW", "logP", "pKa", "delta_D", "delta_P", "delta_H", "water_solubility_mg_ml"],
    "nonionic_surfactant": ["MW", "HLB", "tail_carbons", "headgroup_area_nm2", "CMC_mM"],
    "ionic_surfactant": ["MW", "formal_charge", "HLB"],
    "phospholipid": ["MW", "Tm_C", "tail_carbons", "headgroup_area_nm2"],
    "sterol": ["MW", "molar_volume_cm3_mol"],
    "bile_salt": ["MW", "HLB", "CMC_mM"],
    "solid_lipid": ["MW", "melting_point_C"],
    "liquid_lipid": ["MW", "delta_D", "delta_P", "delta_H"],
    "solvent": ["MW", "delta_D", "delta_P", "delta_H", "ICH_class"],
    "carrier": ["Tg_C"],
    "polymer": ["avg_MW", "Tg_C", "formal_charge"],
}


def build_wide():
    from nanoform import schema

    mats = pd.read_csv(REL / "materials.csv", dtype=str).fillna("")
    props = pd.read_csv(REL / "material_properties.csv", dtype=str).fillna("")
    props["property_name"] = props["property_name"].map(schema.canonical_property)

    # Wide pivot: one row per material, one column per property (first value).
    wide = props.pivot_table(
        index="material_id", columns="property_name", values="value",
        aggfunc="first",
    )
    wide = mats.set_index("material_id").join(wide)
    CONST.mkdir(parents=True, exist_ok=True)
    wide.to_csv(CONST / "internal_constants_wide.csv")

    # Coverage summary by material_type + category.
    cov_rows = []
    have = props.groupby("property_name")["material_id"].apply(set).to_dict()

    def n_with(ids, prop):
        return len(ids & have.get(prop, set()))

    for (mtype, cat), grp in mats.groupby(["material_type", "category"]):
        ids = set(grp["material_id"])
        keymiss = [p for p in IMPORTANT.get(mtype, []) if n_with(ids, p) < len(ids)]
        cov_rows.append({
            "material_type": mtype,
            "category": cat,
            "number_of_materials": len(ids),
            "number_with_MW": n_with(ids, "MW") + n_with(ids, "avg_MW"),
            "number_with_HLB": n_with(ids, "HLB"),
            "number_with_chain_data": n_with(ids, "tail_carbons"),
            "number_with_charge": n_with(ids, "formal_charge"),
            "number_with_HSP": n_with(ids, "delta_D"),
            "number_with_molar_volume": n_with(ids, "molar_volume_cm3_mol"),
            "number_with_transition_or_melting_temperature":
                n_with(ids, "Tm_C") + n_with(ids, "melting_point_C"),
            "key_missing_values": ";".join(keymiss) if keymiss else "",
            "priority_for_curation": "high" if keymiss else "low",
        })
    pd.DataFrame(cov_rows).to_csv(CONST / "coverage_summary.csv", index=False)

    # Unresolved missing values (important props missing per material).
    miss_rows = []
    mat_have = props.groupby("material_id")["property_name"].apply(set).to_dict()
    for _, m in mats.iterrows():
        mid = m["material_id"]
        present = mat_have.get(mid, set())
        for prop in IMPORTANT.get(m["material_type"], []):
            if prop not in present:
                miss_rows.append({
                    "material_name": m["name"],
                    "material_type": m["material_type"],
                    "missing_property": prop,
                    "importance": "high" if prop in ("MW", "avg_MW", "formal_charge") else "medium",
                    "suggested_source": _suggest(prop),
                    "whether_estimation_is_allowed": "no" if prop in ("MW", "formal_charge") else "yes (flag as estimated)",
                    "priority": "high" if prop in ("MW", "avg_MW") else "medium",
                })
    pd.DataFrame(miss_rows, columns=[
        "material_name", "material_type", "missing_property", "importance",
        "suggested_source", "whether_estimation_is_allowed", "priority",
    ]).to_csv(CONST / "unresolved_missing_values.csv", index=False)

    _build_examples()
    _sync_runtime_package_data()
    print(f"Wide constants: {wide.shape[0]} materials x {wide.shape[1]} columns. "
          f"Unresolved missing values: {len(miss_rows)}.")


def _sync_runtime_package_data():
    """Copy runtime CSV tables into the package for installed use.

    The repository keeps maintainer-facing data under ./data. A package install
    may not preserve the repository root, so the runtime CSV subset is mirrored
    into src/nanoform/data and included as package data.
    """
    pkg_data = ROOT / "src" / "nanoform" / "data"
    for name in ("relational", "internal_constants", "examples"):
        src = ROOT / "data" / name
        dst = pkg_data / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.xlsx", "__pycache__"))



def _suggest(prop):
    return {
        "delta_D": "Hansen Solubility Parameters handbook / HSPiP",
        "delta_P": "Hansen Solubility Parameters handbook / HSPiP",
        "delta_H": "Hansen Solubility Parameters handbook / HSPiP",
        "CMC_mM": "Supplier datasheet / primary literature",
        "headgroup_area_nm2": "SAXS / Langmuir isotherm literature",
        "Tm_C": "Avanti / DSC literature",
        "Tg_C": "Supplier datasheet / DSC",
        "pKa": "PubChem / DrugBank / potentiometric literature",
        "logP": "PubChem / experimental logP",
        "water_solubility_mg_ml": "PubChem / intrinsic solubility literature",
        "ICH_class": "ICH Q3C(R8)",
    }.get(prop, "PubChem / supplier / primary literature")


def _build_examples():
    EX.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"design_id": "niosome_dex_topical", "family": "niosome", "route": "topical",
         "drug": "Dexamethasone", "drug_mol_percent": 5, "solvent": "Ethanol",
         "carrier": "", "components": "Span 60:47.5|Cholesterol:42.5|Dicetyl phosphate:5",
         "design_goal": "stability", "total_membrane_umol": 200, "pH": 7.4, "temperature_C": 60},
        {"design_id": "sln_curcumin_oral", "family": "solid_lipid_nanoparticle", "route": "oral",
         "drug": "Curcumin", "drug_mol_percent": 8, "solvent": "Ethanol",
         "carrier": "Trehalose", "components": "Glyceryl behenate:80|Tween 80:20",
         "design_goal": "high_EE", "total_membrane_umol": 300, "pH": 6.8, "temperature_C": 75},
        {"design_id": "liposome_dox_iv", "family": "liposome", "route": "parenteral",
         "drug": "Doxorubicin", "drug_mol_percent": 5, "solvent": "Ethanol",
         "carrier": "Sucrose", "components": "HSPC:56|Cholesterol:39|DSPE-PEG2000:5",
         "design_goal": "parenteral_cautious", "total_membrane_umol": 200, "pH": 6.5, "temperature_C": 60},
    ]).to_csv(EX / "example_user_designs.csv", index=False)

    pd.DataFrame([
        {"component": "Span 60", "role": "surfactant", "mol_percent": 47.5, "umol": 95.0, "mg": 40.9},
        {"component": "Cholesterol", "role": "sterol", "mol_percent": 47.5, "umol": 95.0, "mg": 36.7},
        {"component": "Dicetyl phosphate", "role": "charge_inducer", "mol_percent": 5.0, "umol": 10.0, "mg": 5.5},
        {"component": "Dexamethasone", "role": "drug", "mol_percent": 5.0, "umol": 10.0, "mg": 3.9},
    ]).to_csv(EX / "example_batch_table.csv", index=False)


if __name__ == "__main__":
    build_wide()
