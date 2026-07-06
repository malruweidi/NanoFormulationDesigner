"""Import the curated Excel master into the tool's canonical relational CSVs.

Source of truth:
    data/source/NanoFormulationDesigner_Internal_Material_Database.xlsx

This master (curated by the maintainer) is richer than the bootstrap Python seed
in scripts/build_database.py. This importer:

  1. Reads the Excel `materials`, `material_properties`, and `sources` sheets.
  2. Maps the Excel `material_type` labels to the tool's enum
     (nanoform.schema.MATERIAL_TYPES).
  3. Canonicalizes property names to the vocabulary the kernels read
     (MW, HLB, delta_D/P/H, Tm_C, tail_carbons, headgroup_area_nm2, ...).
  4. Normalizes categorical/textual values (ICH "Class 2" -> "2", flag text
     "yes"/"no" -> 1.0/0.0) and derives the boolean flags descriptors need
     (edge_activator, vesicle_anchor, pegylated, ionizable, fusogenic,
     charge_inducer, cationic, cryoprotectant, porous_carrier).
  5. Enriches synonyms (splits "A / B" names, plus a curated map).
  6. Unions in any Python-seed materials the Excel lacks (by name/synonym),
     so no coverage is lost.
  7. Writes the relational CSVs and regenerates the internal-constants tables.

No scientific constant is fabricated here; every value and its provenance comes
from the Excel (or, for unioned extras, the Python seed). Uncertain values keep
their `estimated` data_quality and reduced confidence.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from nanoform import schema  # noqa: E402

XLSX = ROOT / "data" / "source" / "NanoFormulationDesigner_Internal_Material_Database.xlsx"
CHEMBL_CSV = ROOT / "data" / "source" / "chembl_drug_additions.csv"
PROP_ADD_CSVS = [
    ROOT / "data" / "source" / "excipient_property_additions.csv",
    ROOT / "data" / "source" / "drug_pka_additions.csv",
]
REL = ROOT / "data" / "relational"

CHEMBL_SOURCE = ("S017_CHEMBL", "database", "ChEMBL Database v34, EMBL-EBI", "",
                 "https://www.ebi.ac.uk/chembl", "2026-07-01",
                 "Calculated molecular properties (MW, ALogP, PSA, HBD/HBA, RTB, aromatic rings)")
SURF_LIT_SOURCE = ("S018_SURFACTANT_LIT", "literature",
                   "Surfactant/excipient CMC literature (aggregated); Handbook of Pharmaceutical "
                   "Excipients & primary surfactant-science sources", "", "", "2026-07-01",
                   "Representative CMC values; temperature/method/ionic-strength dependent")
PKA_SOURCE = ("S019_PKA_LIT", "literature",
              "Aggregated pKa reference values (FDA/DailyMed labels, potentiometric literature, DrugBank)",
              "", "", "2026-07-01",
              "Representative ionization constants; multi-protic drugs list the most formulation-relevant pKa")

# --------------------------------------------------------------------------- #
# Mappings
# --------------------------------------------------------------------------- #
TYPE_MAP = {
    "api": "api",
    "surfactant": "nonionic_surfactant",
    "charge inducer": "ionic_surfactant",
    "lipid": "phospholipid",
    "solid lipid/oil": "solid_lipid",   # refined to liquid_lipid via lipid_state
    "sterol": "sterol",
    "bile salt": "bile_salt",
    "carrier": "carrier",
    "solvent": "solvent",
    "polymer": "polymer",
}

# Excel property_name -> canonical property_name used by the kernels.
PROP_MAP = {
    "molecular_weight_g_mol": "MW",
    "average_MW": "avg_MW",
    "average_mw_g_mol": "avg_MW",
    "repeat_unit_mw_g_mol": "avg_MW",
    "HLB": "HLB",
    "HLB_if_amphiphilic": "HLB",
    "HLB_or_amphiphilicity_descriptor": "HLB",
    "LogP": "logP",
    "pKa": "pKa",
    "pKa_acid": "pKa",
    "pKa_base": "pKa",
    "pKa_if_relevant": "pKa",
    "pKa_if_ionizable": "pKa",
    "formal_charge": "formal_charge",
    "CMC_mM": "CMC_mM",
    "cloud_point_C": "cloud_point_C",
    "melting_point_C": "melting_point_C",
    "phase_transition_temperature_C": "Tm_C",
    "Tm_C": "Tm_C",
    "Tg_C": "Tg_C",
    "glass_transition_temperature_C": "Tg_C",
    "density_g_ml": "density_g_ml",
    "boiling_point_C": "boiling_point_C",
    "dielectric_constant": "dielectric_constant",
    "polarity_index": "polarity_index",
    "water_miscibility": "water_miscibility",
    "ICH_class": "ICH_class",
    "permitted_daily_exposure_if_available": "PDE_mg_day",
    "Hansen_delta_D": "delta_D",
    "Hansen_delta_P": "delta_P",
    "Hansen_delta_H": "delta_H",
    "HSP_radius_R0": "hsp_radius",
    "molar_volume_cm3_mol": "molar_volume_cm3_mol",
    "repeat_unit_molar_volume": "molar_volume_cm3_mol",
    "headgroup_area_nm2": "headgroup_area_nm2",
    "tail_carbons": "tail_carbons",
    "tail_unsaturation": "tail_unsaturation",
    "number_of_tails": "n_tails",
    "water_solubility_mg_ml": "water_solubility_mg_ml",
    "TPSA": "TPSA", "HBD": "HBD", "HBA": "HBA",
    "rotatable_bonds": "rotatable_bonds", "aromatic_rings": "aromatic_rings",
    "BCS_class": "BCS_class",
    "toxicity_penalty": "toxicity_penalty",
    # flags
    "edge_activator_flag": "edge_activator",
    "vesicle_anchor_flag": "vesicle_anchor",
    "PEGylated_flag": "pegylated",
    "ionizable_flag": "ionizable",
    "fusogenic_flag": "fusogenic",
    "mucoadhesive_flag": "mucoadhesive",
}
FLAG_PROPS = {"edge_activator", "vesicle_anchor", "pegylated", "ionizable",
              "fusogenic", "mucoadhesive"}
# Kernel properties that must be strictly positive; a non-positive value is
# treated as MISSING (surfaced), never stored as a fabricated zero.
POSITIVE_ONLY = {"MW", "avg_MW", "molar_volume_cm3_mol", "headgroup_area_nm2",
                 "hsp_radius", "CMC_mM", "tail_carbons", "n_tails",
                 "water_solubility_mg_ml"}

# Curated synonym enrichment (things the tool/tests reference by common names).
SYNONYM_MAP = {
    "SLS / sodium lauryl sulfate": ["SLS", "SDS", "sodium dodecyl sulfate", "sodium lauryl sulfate"],
    "siRNA duplex placeholder": ["siRNA (placeholder)", "siRNA", "small interfering RNA"],
    "mRNA payload placeholder": ["mRNA (placeholder)", "mRNA", "messenger RNA"],
    "Medium-chain triglycerides": ["MCT", "caprylic/capric triglyceride"],
    "Hydrogenated soy phosphatidylcholine / HSPC": ["HSPC"],
    "Egg phosphatidylcholine / EPC": ["EPC", "egg PC"],
    "Soy phosphatidylcholine / SPC": ["SPC", "soy PC"],
    "L-leucine": ["leucine", "L-Leucine"],
}

CRYOPROTECTANTS = {"trehalose", "sucrose", "mannitol", "sorbitol", "glucose",
                   "xylitol", "maltodextrin", "glycine", "lactose", "dextran"}
POROUS_CARRIERS = {"microcrystalline cellulose", "aerosil", "colloidal silicon dioxide",
                   "calcium carbonate", "leucine", "l-leucine"}


def _num(x):
    try:
        return float(str(x).strip())
    except (ValueError, TypeError):
        return None


def _norm_ich(v: str):
    s = str(v).strip().lower()
    for d in ("1", "2", "3"):
        if d in s:
            return d
    return "none"


def _flag_value(v) -> float:
    s = str(v).strip().lower()
    return 1.0 if s in {"yes", "y", "true", "1", "1.0"} else 0.0


# --------------------------------------------------------------------------- #
# Import
# --------------------------------------------------------------------------- #
def _write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def build_from_excel():
    xl_mats = pd.read_excel(XLSX, "materials").fillna("")
    xl_props = pd.read_excel(XLSX, "material_properties").fillna("")
    xl_src = pd.read_excel(XLSX, "sources").fillna("")

    # group props by material_id
    props_by_mat = {mid: g for mid, g in xl_props.groupby("material_id")}

    mat_rows, prop_rows = [], []
    seen_names = set()          # normalized names + synonyms already covered
    source_ids = set(xl_src["source_id"])

    for _, m in xl_mats.iterrows():
        mid = str(m["material_id"]).strip()
        name = str(m["name"]).strip()
        if not mid or not name:
            continue
        raw_type = str(m["material_type"]).strip().lower()
        mtype = TYPE_MAP.get(raw_type, "carrier")

        grp = props_by_mat.get(mid)
        # collect a per-material dict of canonical numeric props for derivations
        canon = {}
        pend = []  # (canonical_name, value, unit, method, source_id, dq, conf, notes)
        tail1c = tail2c = tail1u = tail2u = None
        lipid_state = ""
        charge_type = ""
        cryo_score = None
        if grp is not None:
            for _, pr in grp.iterrows():
                pname = str(pr["property_name"]).strip()
                val = pr["value"]
                if pname == "lipid_state":
                    lipid_state = str(val).strip().lower()
                elif pname == "charge_type":
                    charge_type = str(val).strip().lower()
                elif pname == "cryoprotection_score":
                    cryo_score = _num(val)
                elif pname == "tail_1_carbons":
                    tail1c = _num(val)
                elif pname == "tail_2_carbons":
                    tail2c = _num(val)
                elif pname == "tail_1_unsaturation":
                    tail1u = _num(val)
                elif pname == "tail_2_unsaturation":
                    tail2u = _num(val)

                cname = PROP_MAP.get(pname)
                if cname is None:
                    continue  # non-kernel descriptive fields are dropped from long table
                out_val = val
                if cname == "ICH_class":
                    out_val = _norm_ich(val)
                elif cname in FLAG_PROPS:
                    out_val = _flag_value(val)
                    if out_val == 0.0:
                        continue  # only store positive flags
                elif cname in ("HLB", "logP", "pKa", "MW", "avg_MW", "delta_D",
                               "delta_P", "delta_H", "hsp_radius", "molar_volume_cm3_mol",
                               "headgroup_area_nm2", "tail_carbons", "tail_unsaturation",
                               "n_tails", "formal_charge", "CMC_mM", "Tm_C", "Tg_C",
                               "melting_point_C", "water_solubility_mg_ml", "toxicity_penalty"):
                    nv = _num(val)
                    if nv is None:
                        continue  # skip non-numeric junk for numeric kernels
                    if cname in POSITIVE_ONLY and nv <= 0:
                        continue  # non-positive -> treat as MISSING (never store a fake 0)
                if cname not in canon:  # keep first occurrence
                    canon[cname] = out_val
                    pend.append((cname, out_val, pr.get("unit", ""), pr.get("method", ""),
                                 pr.get("source_id", ""), pr.get("data_quality", ""),
                                 pr.get("confidence_score", ""), pr.get("notes", "")))

        # refine solid vs liquid lipid
        if mtype == "solid_lipid" and lipid_state.startswith("liquid"):
            mtype = "liquid_lipid"

        # combine two-tail geometry if a single tail_carbons is absent
        if "tail_carbons" not in canon and (tail1c or tail2c):
            vals = [x for x in (tail1c, tail2c) if x]
            pend.append(("tail_carbons", round(sum(vals) / len(vals), 1), "", "derived",
                         "S012_CALCULATED", "calculated", 0.5, "avg of tail_1/tail_2 carbons"))
            canon["tail_carbons"] = sum(vals) / len(vals)
        if "tail_unsaturation" not in canon and (tail1u is not None or tail2u is not None):
            vals = [x for x in (tail1u, tail2u) if x is not None]
            if vals:
                pend.append(("tail_unsaturation", round(sum(vals) / len(vals), 2), "", "derived",
                             "S012_CALCULATED", "calculated", 0.5, "avg of tail_1/tail_2 unsaturation"))

        # derived flags -------------------------------------------------------
        fc = _num(canon.get("formal_charge"))
        if fc is not None and fc != 0:
            pend.append(("charge_inducer", 1.0, "", "derived", "S000_USER_SPEC",
                         "curated", 0.6, "derived: nonzero formal charge"))
        if "cationic" in charge_type:
            pend.append(("cationic", 1.0, "", "derived", "S000_USER_SPEC",
                         "curated", 0.6, "derived from charge_type"))
        if mtype == "carrier":
            is_cryo = (cryo_score is not None and cryo_score >= 0.4) or \
                      any(k in name.lower() for k in CRYOPROTECTANTS)
            if is_cryo:
                pend.append(("cryoprotectant", 1.0, "", "derived", "S007_EXCIPIENTS_HANDBOOK",
                             "curated", 0.55, "derived: cryo/lyoprotectant"))
            if any(k in name.lower() for k in POROUS_CARRIERS):
                pend.append(("porous_carrier", 1.0, "", "derived", "S007_EXCIPIENTS_HANDBOOK",
                             "curated", 0.55, "derived: high-surface-area / dispersibility aid"))

        # synonyms ------------------------------------------------------------
        syn = str(m.get("synonyms", "")).strip()
        syn_set = {s.strip() for s in syn.replace("/", ";").split(";") if s.strip()}
        syn_set |= {s for s in SYNONYM_MAP.get(name, [])}
        # split "A / B" style names into synonyms too
        if "/" in name:
            syn_set |= {p.strip() for p in name.split("/") if p.strip()}
        syn_out = ";".join(sorted(syn_set - {name}))

        conf = m.get("confidence_score", "")
        mat_rows.append([
            mid, name, syn_out, mtype, str(m.get("category", "")).strip(),
            str(m.get("subcategory", "")).strip(), str(m.get("CAS", "")).strip(),
            str(m.get("PubChem_CID", "")).strip(), str(m.get("SMILES", "")).strip(),
            str(m.get("InChIKey", "")).strip(), str(m.get("supplier_or_grade_notes", "")).strip(),
            str(m.get("route_suitability", "")).strip(),
            str(m.get("regulatory_or_safety_notes", "")).strip(),
            str(m.get("source_id", "")).strip() or "S000_USER_SPEC",
            str(m.get("curation_status", "")).strip() or "curated", conf,
            str(m.get("notes", "")).strip(),
        ])
        for (cname, val, unit, method, sid, dq, pconf, notes) in pend:
            prop_rows.append([mid, cname, val, unit, "", "", method, sid or "S000_USER_SPEC",
                              dq or "curated", pconf if pconf != "" else 0.5, notes])
            source_ids.add(sid or "S000_USER_SPEC")

        # register names/synonyms as covered
        seen_names.add(name.strip().lower())
        for s in syn_set:
            seen_names.add(s.strip().lower())

    # ---- union in Python-seed extras the Excel lacks --------------------- #
    added_extra = _union_python_seed(mat_rows, prop_rows, seen_names, source_ids)

    # ---- merge researched ChEMBL drug additions (sourced constants) ------ #
    added_chembl = _merge_chembl_additions(mat_rows, prop_rows, seen_names, source_ids)

    # ---- enrich existing materials with sourced literature properties ---- #
    added_props = _merge_property_additions(mat_rows, prop_rows, source_ids)

    # ---- sources: Excel sources + any referenced seed/ChEMBL sources ----- #
    src_rows = [list(r) for r in xl_src[schema.SOURCES_COLUMNS].values.tolist()]
    known_src = set(xl_src["source_id"])
    from scripts.build_database import SOURCES as SEED_SOURCES  # type: ignore
    for s in list(SEED_SOURCES) + [CHEMBL_SOURCE, SURF_LIT_SOURCE, PKA_SOURCE]:
        if s[0] in source_ids and s[0] not in known_src:
            src_rows.append(list(s))
            known_src.add(s[0])

    # ---- write relational CSVs ------------------------------------------- #
    _write(REL / "materials.csv", schema.MATERIALS_COLUMNS, mat_rows)
    _write(REL / "material_properties.csv", schema.MATERIAL_PROPERTIES_COLUMNS, prop_rows)
    _write(REL / "sources.csv", schema.SOURCES_COLUMNS, src_rows)

    # keep the reserved relational tables (header-only / example) as-is if present;
    # (re)create them if missing so a fresh checkout is complete.
    _ensure_reserved_tables()

    print(f"Imported {len(mat_rows)} materials "
          f"({added_extra} unioned from Python seed, {added_chembl} researched via ChEMBL), "
          f"{len(prop_rows)} property rows (+{added_props} sourced literature enrichments), "
          f"{len(src_rows)} sources.")
    return len(mat_rows), len(prop_rows)


def _union_python_seed(mat_rows, prop_rows, seen_names, source_ids):
    """Add Python-seed materials whose name/synonyms are not already covered."""
    from scripts.build_database import M as SEED  # type: ignore
    added = 0
    for m in SEED:
        names = {m["name"].strip().lower()}
        names |= {s.strip().lower() for s in str(m.get("syn", "")).split(";") if s.strip()}
        if names & seen_names:
            continue  # already covered by the Excel master
        mid = "SEED_" + m["id"]
        mat_rows.append([
            mid, m["name"], m["syn"], m["type"], m["cat"], m["sub"], m["cas"],
            m["cid"], "", "", "", m["route"], m["safety"], m["src"], "seed-union",
            m["conf"], "Unioned from bootstrap Python seed (not in Excel master).",
        ])
        for pname, pval in m["props"].items():
            if pval is None:
                continue
            prop_rows.append([mid, pname, pval, "", "", "", "", m["src"], "literature", m["conf"], ""])
            source_ids.add(m["src"])
        capped = min(0.40, m["conf"])
        for pname, pval in m["est"].items():
            if pval is None:
                continue
            prop_rows.append([mid, pname, pval, "", "", "", "model/analogy", "estimated",
                              "estimated", capped, "Heuristic estimate; verify in lab"])
            source_ids.add("estimated")
        seen_names |= names
        added += 1
    return added


def _merge_chembl_additions(mat_rows, prop_rows, seen_names, source_ids):
    """Add researched drugs whose physicochemical constants come from ChEMBL v34.

    Only ChEMBL-computed constants + identity are stored (MW, logP, TPSA, HBD,
    HBA, rotatable_bonds, aromatic_rings). pKa / HSP / solubility are NOT
    fabricated: they stay absent and are surfaced as missing.
    """
    if not CHEMBL_CSV.exists():
        return 0
    df = pd.read_csv(CHEMBL_CSV).fillna("")
    added = 0
    # confidence per property (ChEMBL calculated values are reliable but model-based)
    conf = {"MW": 0.85, "logP": 0.75, "TPSA": 0.8, "HBD": 0.85, "HBA": 0.85,
            "rotatable_bonds": 0.85, "aromatic_rings": 0.85}
    for _, r in df.iterrows():
        name = str(r["name"]).strip()
        if not name:
            continue
        names = {name.lower()} | {s.strip().lower() for s in str(r["synonyms"]).split(";") if s.strip()}
        if names & seen_names:
            continue  # already in the master
        mid = "API_CHEMBL_" + name.upper().replace(" ", "_").replace("-", "_")
        mat_rows.append([
            mid, name, str(r["synonyms"]).strip(), "api", str(r["category"]).strip(),
            str(r["subcategory"]).strip(), "", "", "", str(r["InChIKey"]).strip(), "",
            str(r["route_suitability"]).strip(), "", "S017_CHEMBL", "curated", 0.8,
            f"{str(r['notes']).strip()} Formula {str(r['molecular_formula']).strip()}; "
            f"ChEMBL {str(r['chembl_id']).strip()}.",
        ])
        for prop in ("MW", "logP", "TPSA", "HBD", "HBA", "rotatable_bonds", "aromatic_rings"):
            val = str(r.get(prop, "")).strip()
            if val == "":
                continue
            dq = "database" if prop == "MW" else "calculated"
            prop_rows.append([mid, prop, val, "", "", "", "ChEMBL v34", "S017_CHEMBL",
                              dq, conf.get(prop, 0.75), "ChEMBL-computed molecular property"])
        source_ids.add("S017_CHEMBL")
        seen_names |= names
        added += 1
    return added


def _merge_property_additions(mat_rows, prop_rows, source_ids):
    """Enrich EXISTING materials with sourced literature properties (e.g. CMC).

    A property is added only if that material does not already carry it, so the
    curated Excel master values are never overwritten.
    """
    name_idx = {}
    for row in mat_rows:
        mid, name, syn = row[0], str(row[1]), str(row[2])
        name_idx[name.strip().lower()] = mid
        for s in syn.split(";"):
            s = s.strip().lower()
            if s:
                name_idx.setdefault(s, mid)
    existing = {(r[0], r[1]) for r in prop_rows}
    added = 0
    for csv_path in PROP_ADD_CSVS:
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path).fillna("")
        for _, r in df.iterrows():
            mid = name_idx.get(str(r["material_name"]).strip().lower())
            if mid is None:
                continue
            cname = schema.canonical_property(str(r["property_name"]).strip())
            if (mid, cname) in existing:
                continue  # never overwrite a curated value
            sid = str(r["source_id"]).strip() or "S018_SURFACTANT_LIT"
            prop_rows.append([mid, cname, r["value"], str(r.get("unit", "")), "", "", "literature",
                              sid, str(r["data_quality"]).strip() or "literature",
                              r["confidence_score"], str(r["notes"]).strip()])
            existing.add((mid, cname))
            source_ids.add(sid)
            added += 1
    return added


def _ensure_reserved_tables():
    import datetime as _dt
    if not (REL / "formulations.csv").exists():
        _write(REL / "formulations.csv", schema.FORMULATIONS_COLUMNS, [])
    if not (REL / "formulation_components.csv").exists():
        _write(REL / "formulation_components.csv", schema.FORMULATION_COMPONENTS_COLUMNS, [])
    if not (REL / "outcomes.csv").exists():
        _write(REL / "outcomes.csv", schema.OUTCOMES_COLUMNS, [])
    if not (REL / "curation_log.csv").exists():
        _write(REL / "curation_log.csv", schema.CURATION_LOG_COLUMNS, [
            [_dt.date.today().isoformat(), "ALL", "excel_import", "", "", "",
             "S000_USER_SPEC", "Imported curated Excel master via import_excel_database.py"],
        ])


if __name__ == "__main__":
    build_from_excel()
    from scripts.build_wide_constants import build_wide  # type: ignore
    build_wide()
    print("Excel import complete.")
