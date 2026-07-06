"""Build the internal relational CSV database from the curated seed source.

This script is the single authoritative source of seed material data. Running it
regenerates every CSV under data/. Curation happens here (and via the curation
log), not by hand-editing generated CSVs.

Data-quality discipline:
    * `props`  -> well-established constants (MW, HLB, charge, Tm, ...): quality
                  "literature", material-level confidence.
    * `est`    -> approximate / grade-dependent / model values (HSP, headgroup
                  area, molar volume, some Tg): quality "estimated", confidence
                  capped at 0.40. These MUST be treated as heuristic.

No value here is presented as validated experimental outcome data. See
docs/SCIENTIFIC_LIMITATIONS.md.
"""
from __future__ import annotations

import csv
import datetime as _dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REL = DATA / "relational"
CONST = DATA / "internal_constants"
EX = DATA / "examples"

# --------------------------------------------------------------------------- #
# Sources
# --------------------------------------------------------------------------- #
SOURCES = [
    ("pubchem", "database", "PubChem, NIH National Library of Medicine", "", "https://pubchem.ncbi.nlm.nih.gov", "2026-06-01", "Identity + physicochemical constants"),
    ("hpe", "handbook", "Handbook of Pharmaceutical Excipients, 9th ed.", "", "", "2026-06-01", "Excipient properties (HLB, function, safety)"),
    ("avanti", "supplier", "Avanti Polar Lipids product data", "", "https://avantilipids.com", "2026-06-01", "Phospholipid Tm, purity, structure"),
    ("supplier", "supplier", "Supplier technical datasheet (Croda/BASF/Gattefosse/Lipoid)", "", "", "2026-06-01", "Grade-dependent excipient data"),
    ("ich_q3c", "guideline", "ICH Q3C(R8) Impurities: Guideline for Residual Solvents", "", "https://www.ich.org", "2026-06-01", "Solvent class + PDE"),
    ("hsp_handbook", "handbook", "Hansen, Hansen Solubility Parameters: A User's Handbook, 2nd ed.", "10.1201/9781420006834", "", "2026-06-01", "HSP components dD/dP/dH"),
    ("estimated", "estimation", "Internal estimation / group-contribution / analogy", "", "", "2026-06-01", "Heuristic value, low confidence, needs verification"),
    ("literature", "literature", "Peer-reviewed literature (aggregated)", "", "", "2026-06-01", "Aggregated literature values"),
]

# --------------------------------------------------------------------------- #
# Material seed. Each entry:
#   (id, name, synonyms, type, category, subcategory, CAS, CID,
#    route, safety, conf, src, props, est)
# props / est are {canonical_property: value}
# --------------------------------------------------------------------------- #
M = []


def add(id, name, syn, type, cat, sub, cas, cid, route, safety, conf, src, props, est=None):
    M.append(dict(id=id, name=name, syn=syn, type=type, cat=cat, sub=sub, cas=cas,
                  cid=cid, route=route, safety=safety, conf=conf, src=src,
                  props=props, est=est or {}))


# ------------------------------- APIs -------------------------------------- #
add("API001", "Dexamethasone", "DEX", "api", "corticosteroid", "glucocorticoid", "50-02-2", "5743",
    "oral;topical;ocular;parenteral;pulmonary", "Potent glucocorticoid; systemic exposure limits", 0.75, "pubchem",
    {"MW": 392.46, "logP": 1.83, "water_solubility_mg_ml": 0.089, "melting_point_C": 262,
     "acid_base": "neutral", "TPSA": 94.8, "HBD": 3, "HBA": 6, "aromatic_rings": 0, "BCS_class": 2},
    {"delta_D": 18.0, "delta_P": 9.0, "delta_H": 11.0, "hsp_radius": 9.0, "molar_volume_cm3_mol": 300})
add("API002", "Dexamethasone sodium phosphate", "DSP", "api", "corticosteroid", "glucocorticoid salt", "2392-39-4", "16961",
    "ocular;parenteral;pulmonary", "Water-soluble prodrug salt", 0.7, "pubchem",
    {"MW": 516.4, "logP": -0.5, "water_solubility_mg_ml": 50, "acid_base": "acid", "pKa": 1.9, "BCS_class": 3},
    {"delta_D": 17.5, "delta_P": 12.0, "delta_H": 16.0, "hsp_radius": 10.0, "molar_volume_cm3_mol": 330})
add("API003", "Budesonide", "BUD", "api", "corticosteroid", "glucocorticoid", "51333-22-3", "5281004",
    "pulmonary;oral;topical", "Inhaled corticosteroid; potent", 0.75, "pubchem",
    {"MW": 430.53, "logP": 2.32, "water_solubility_mg_ml": 0.028, "melting_point_C": 226,
     "acid_base": "neutral", "TPSA": 93.1, "HBD": 2, "HBA": 6, "BCS_class": 2},
    {"delta_D": 17.8, "delta_P": 8.0, "delta_H": 9.5, "hsp_radius": 8.5, "molar_volume_cm3_mol": 350})
add("API004", "Fluticasone propionate", "FP", "api", "corticosteroid", "glucocorticoid", "80474-14-2", "444036",
    "pulmonary;topical;nasal", "Highly lipophilic ICS", 0.72, "pubchem",
    {"MW": 500.57, "logP": 3.7, "water_solubility_mg_ml": 0.00014, "melting_point_C": 273,
     "acid_base": "neutral", "BCS_class": 2},
    {"delta_D": 18.0, "delta_P": 6.5, "delta_H": 7.5, "hsp_radius": 8.0, "molar_volume_cm3_mol": 400})
add("API005", "Beclomethasone dipropionate", "BDP", "api", "corticosteroid", "glucocorticoid", "5534-09-8", "21700",
    "pulmonary;nasal;topical", "Prodrug ICS; very lipophilic", 0.7, "pubchem",
    {"MW": 521.04, "logP": 4.0, "water_solubility_mg_ml": 0.00013, "melting_point_C": 117, "acid_base": "neutral", "BCS_class": 2},
    {"delta_D": 18.0, "delta_P": 6.0, "delta_H": 7.0, "hsp_radius": 8.0, "molar_volume_cm3_mol": 420})
add("API006", "Prednisolone", "", "api", "corticosteroid", "glucocorticoid", "50-24-8", "5755",
    "oral;topical;ocular;parenteral", "Glucocorticoid", 0.75, "pubchem",
    {"MW": 360.44, "logP": 1.62, "water_solubility_mg_ml": 0.223, "melting_point_C": 235, "acid_base": "neutral", "BCS_class": 2},
    {"delta_D": 18.0, "delta_P": 9.5, "delta_H": 12.0, "hsp_radius": 9.5, "molar_volume_cm3_mol": 290})
add("API007", "Hydrocortisone", "cortisol", "api", "corticosteroid", "glucocorticoid", "50-23-7", "5754",
    "topical;oral;parenteral", "Glucocorticoid", 0.75, "pubchem",
    {"MW": 362.46, "logP": 1.61, "water_solubility_mg_ml": 0.32, "melting_point_C": 212, "acid_base": "neutral", "BCS_class": 2},
    {"delta_D": 17.8, "delta_P": 9.5, "delta_H": 12.5, "hsp_radius": 9.5, "molar_volume_cm3_mol": 290})
add("API008", "Triamcinolone acetonide", "TA", "api", "corticosteroid", "glucocorticoid", "76-25-5", "6436",
    "topical;ocular;parenteral;pulmonary", "Potent glucocorticoid", 0.72, "pubchem",
    {"MW": 434.5, "logP": 2.53, "water_solubility_mg_ml": 0.021, "melting_point_C": 292, "acid_base": "neutral", "BCS_class": 2},
    {"delta_D": 17.9, "delta_P": 8.0, "delta_H": 9.0, "hsp_radius": 8.5, "molar_volume_cm3_mol": 350})
add("API009", "Curcumin", "diferuloylmethane", "api", "polyphenol", "nutraceutical", "458-37-7", "969516",
    "oral;topical", "Poor aqueous solubility & stability; BCS IV-like", 0.7, "pubchem",
    {"MW": 368.38, "logP": 3.2, "water_solubility_mg_ml": 0.0004, "melting_point_C": 183,
     "acid_base": "acid", "pKa": 8.1, "HBD": 2, "HBA": 6, "BCS_class": 4},
    {"delta_D": 18.5, "delta_P": 7.0, "delta_H": 9.0, "hsp_radius": 8.0, "molar_volume_cm3_mol": 320})
add("API010", "Quercetin", "", "api", "polyphenol", "flavonoid", "117-39-5", "5280343",
    "oral;topical", "Poorly soluble flavonoid", 0.68, "pubchem",
    {"MW": 302.24, "logP": 1.54, "water_solubility_mg_ml": 0.06, "melting_point_C": 316,
     "acid_base": "acid", "pKa": 7.0, "HBD": 5, "HBA": 7, "BCS_class": 4},
    {"delta_D": 19.0, "delta_P": 9.0, "delta_H": 16.0, "hsp_radius": 9.0, "molar_volume_cm3_mol": 220})
add("API011", "Resveratrol", "", "api", "polyphenol", "stilbene", "501-36-0", "445154",
    "oral;topical", "Photolabile polyphenol", 0.68, "pubchem",
    {"MW": 228.24, "logP": 3.1, "water_solubility_mg_ml": 0.03, "melting_point_C": 261,
     "acid_base": "acid", "pKa": 9.2, "HBD": 3, "HBA": 3, "BCS_class": 2},
    {"delta_D": 19.0, "delta_P": 7.0, "delta_H": 12.0, "hsp_radius": 8.5, "molar_volume_cm3_mol": 190})
add("API012", "Ibuprofen", "", "api", "nsaid", "propionic acid", "15687-27-1", "3672",
    "oral;topical", "Weak acid NSAID", 0.8, "pubchem",
    {"MW": 206.28, "logP": 3.97, "logD_7.4": 0.9, "water_solubility_mg_ml": 0.021, "melting_point_C": 76,
     "acid_base": "acid", "pKa": 4.4, "HBD": 1, "HBA": 2, "BCS_class": 2},
    {"delta_D": 17.6, "delta_P": 4.5, "delta_H": 8.0, "hsp_radius": 7.0, "molar_volume_cm3_mol": 200})
add("API013", "Ketoprofen", "", "api", "nsaid", "propionic acid", "22071-15-4", "3825",
    "oral;topical", "Weak acid NSAID", 0.78, "pubchem",
    {"MW": 254.28, "logP": 3.12, "water_solubility_mg_ml": 0.051, "melting_point_C": 94,
     "acid_base": "acid", "pKa": 4.45, "BCS_class": 2},
    {"delta_D": 18.5, "delta_P": 6.0, "delta_H": 8.0, "hsp_radius": 7.5, "molar_volume_cm3_mol": 210})
add("API014", "Diclofenac", "", "api", "nsaid", "acetic acid", "15307-86-5", "3033",
    "oral;topical;ocular", "Weak acid NSAID", 0.78, "pubchem",
    {"MW": 296.15, "logP": 4.51, "water_solubility_mg_ml": 0.0024, "melting_point_C": 157,
     "acid_base": "acid", "pKa": 4.15, "BCS_class": 2},
    {"delta_D": 19.0, "delta_P": 6.5, "delta_H": 8.5, "hsp_radius": 7.5, "molar_volume_cm3_mol": 210})
add("API015", "Indomethacin", "", "api", "nsaid", "acetic acid", "53-86-1", "3715",
    "oral;topical;ocular", "Weak acid NSAID", 0.78, "pubchem",
    {"MW": 357.79, "logP": 4.27, "water_solubility_mg_ml": 0.0009, "melting_point_C": 158,
     "acid_base": "acid", "pKa": 4.5, "BCS_class": 2},
    {"delta_D": 19.0, "delta_P": 7.0, "delta_H": 8.0, "hsp_radius": 7.5, "molar_volume_cm3_mol": 270})
add("API016", "Celecoxib", "", "api", "nsaid", "coxib", "169590-42-5", "2662",
    "oral", "COX-2 inhibitor; BCS II", 0.75, "pubchem",
    {"MW": 381.37, "logP": 3.9, "water_solubility_mg_ml": 0.0034, "melting_point_C": 158,
     "acid_base": "acid", "pKa": 11.1, "BCS_class": 2},
    {"delta_D": 18.5, "delta_P": 8.0, "delta_H": 6.0, "hsp_radius": 8.0, "molar_volume_cm3_mol": 280})
add("API017", "Meloxicam", "", "api", "nsaid", "oxicam", "71125-38-7", "54677470",
    "oral;parenteral", "Amphoteric NSAID", 0.72, "pubchem",
    {"MW": 351.4, "logP": 3.43, "water_solubility_mg_ml": 0.012, "melting_point_C": 254,
     "acid_base": "acid", "pKa": 4.08, "BCS_class": 2},
    {"delta_D": 19.0, "delta_P": 9.0, "delta_H": 9.0, "hsp_radius": 8.5, "molar_volume_cm3_mol": 250})
add("API018", "Paclitaxel", "PTX", "api", "anticancer", "taxane", "33069-62-4", "36314",
    "parenteral", "Very poorly soluble; cremophor-associated toxicity historically", 0.72, "pubchem",
    {"MW": 853.91, "logP": 3.0, "water_solubility_mg_ml": 0.0003, "melting_point_C": 216,
     "acid_base": "neutral", "HBD": 4, "HBA": 14, "BCS_class": 4},
    {"delta_D": 18.5, "delta_P": 7.5, "delta_H": 9.0, "hsp_radius": 8.0, "molar_volume_cm3_mol": 700})
add("API019", "Docetaxel", "DTX", "api", "anticancer", "taxane", "114977-28-5", "148124",
    "parenteral", "Poorly soluble taxane", 0.7, "pubchem",
    {"MW": 807.88, "logP": 2.9, "water_solubility_mg_ml": 0.0068, "acid_base": "neutral", "BCS_class": 4},
    {"delta_D": 18.5, "delta_P": 8.0, "delta_H": 10.0, "hsp_radius": 8.0, "molar_volume_cm3_mol": 660})
add("API020", "Doxorubicin", "DOX", "api", "anticancer", "anthracycline", "23214-92-8", "31703",
    "parenteral", "Amphiphilic weak base; remote-loading candidate", 0.72, "pubchem",
    {"MW": 543.52, "logP": 1.27, "water_solubility_mg_ml": 1.18, "acid_base": "base", "pKa": 8.2,
     "HBD": 6, "HBA": 12, "BCS_class": 3},
    {"delta_D": 18.0, "delta_P": 10.0, "delta_H": 14.0, "hsp_radius": 9.0, "molar_volume_cm3_mol": 380})
add("API021", "Amphotericin B", "AmB", "api", "antifungal", "polyene", "1397-89-3", "5280965",
    "parenteral", "Nephrotoxic; aggregation-state dependent toxicity", 0.68, "pubchem",
    {"MW": 924.08, "logP": 0.8, "water_solubility_mg_ml": 0.00075, "acid_base": "acid", "pKa": 5.5, "BCS_class": 4},
    {"delta_D": 18.0, "delta_P": 11.0, "delta_H": 15.0, "hsp_radius": 10.0, "molar_volume_cm3_mol": 720})
add("API022", "Itraconazole", "ITZ", "api", "antifungal", "azole", "84625-61-6", "55283",
    "oral", "Very lipophilic weak base; BCS II", 0.72, "pubchem",
    {"MW": 705.63, "logP": 5.66, "water_solubility_mg_ml": 0.000001, "acid_base": "base", "pKa": 3.7, "BCS_class": 2},
    {"delta_D": 19.5, "delta_P": 6.0, "delta_H": 5.0, "hsp_radius": 8.0, "molar_volume_cm3_mol": 580})
add("API023", "Fluconazole", "", "api", "antifungal", "azole", "86386-73-4", "3365",
    "oral;parenteral", "Water-soluble azole", 0.75, "pubchem",
    {"MW": 306.27, "logP": 0.5, "water_solubility_mg_ml": 5.0, "acid_base": "base", "pKa": 2.0, "BCS_class": 1},
    {"delta_D": 17.0, "delta_P": 10.0, "delta_H": 9.0, "hsp_radius": 9.0, "molar_volume_cm3_mol": 220})
add("API024", "Ciprofloxacin", "CIP", "api", "antibiotic", "fluoroquinolone", "85721-33-1", "2764",
    "oral;parenteral;ocular;pulmonary", "Zwitterionic antibiotic", 0.72, "pubchem",
    {"MW": 331.34, "logP": 0.28, "water_solubility_mg_ml": 0.03, "acid_base": "amphoteric", "pKa": 6.1, "BCS_class": 4},
    {"delta_D": 18.5, "delta_P": 10.0, "delta_H": 11.0, "hsp_radius": 9.5, "molar_volume_cm3_mol": 240})
add("API025", "Rifampicin", "RIF", "api", "antibiotic", "rifamycin", "13292-46-1", "5381226",
    "oral;pulmonary", "Amphoteric; oxidation-sensitive", 0.68, "pubchem",
    {"MW": 822.94, "logP": 2.7, "water_solubility_mg_ml": 1.4, "acid_base": "amphoteric", "pKa": 7.9, "BCS_class": 2},
    {"delta_D": 18.5, "delta_P": 8.0, "delta_H": 10.0, "hsp_radius": 9.0, "molar_volume_cm3_mol": 680})
add("API026", "Cyclosporine A", "CsA", "api", "immunosuppressant", "cyclic peptide", "59865-13-3", "5284373",
    "oral;ocular;parenteral", "Cyclic peptide; very lipophilic", 0.7, "pubchem",
    {"MW": 1202.61, "logP": 3.0, "water_solubility_mg_ml": 0.0065, "acid_base": "neutral", "BCS_class": 2},
    {"delta_D": 17.5, "delta_P": 5.0, "delta_H": 6.0, "hsp_radius": 8.0, "molar_volume_cm3_mol": 1100})
add("API027", "Tacrolimus", "FK506", "api", "immunosuppressant", "macrolide", "104987-11-3", "445643",
    "oral;topical", "Poorly soluble macrolide", 0.7, "pubchem",
    {"MW": 804.02, "logP": 3.3, "water_solubility_mg_ml": 0.004, "acid_base": "neutral", "BCS_class": 2},
    {"delta_D": 17.8, "delta_P": 6.0, "delta_H": 7.0, "hsp_radius": 8.0, "molar_volume_cm3_mol": 700})
add("API028", "Atorvastatin", "", "api", "statin", "lipid-lowering", "134523-00-5", "60823",
    "oral", "Weak acid statin", 0.72, "pubchem",
    {"MW": 558.64, "logP": 5.7, "water_solubility_mg_ml": 0.0011, "acid_base": "acid", "pKa": 4.46, "BCS_class": 2},
    {"delta_D": 18.5, "delta_P": 7.0, "delta_H": 9.0, "hsp_radius": 8.0, "molar_volume_cm3_mol": 480})
add("API029", "Simvastatin", "", "api", "statin", "lipid-lowering", "79902-63-9", "54454",
    "oral", "Lactone prodrug statin", 0.72, "pubchem",
    {"MW": 418.57, "logP": 4.68, "water_solubility_mg_ml": 0.03, "acid_base": "neutral", "BCS_class": 2},
    {"delta_D": 17.8, "delta_P": 4.5, "delta_H": 6.5, "hsp_radius": 7.5, "molar_volume_cm3_mol": 420})
add("API030", "Fenofibrate", "", "api", "fibrate", "lipid-lowering", "49562-28-9", "3339",
    "oral", "Lipophilic; classic lipid-formulation candidate; BCS II", 0.74, "pubchem",
    {"MW": 360.83, "logP": 5.19, "water_solubility_mg_ml": 0.0002, "melting_point_C": 80, "acid_base": "neutral", "BCS_class": 2},
    {"delta_D": 18.0, "delta_P": 4.0, "delta_H": 4.0, "hsp_radius": 7.0, "molar_volume_cm3_mol": 320})
add("API031", "Lidocaine", "", "api", "local anesthetic", "amide", "137-58-6", "3676",
    "topical;parenteral", "Weak base local anesthetic", 0.78, "pubchem",
    {"MW": 234.34, "logP": 2.44, "water_solubility_mg_ml": 4.1, "acid_base": "base", "pKa": 8.0, "BCS_class": 1},
    {"delta_D": 17.0, "delta_P": 5.0, "delta_H": 6.0, "hsp_radius": 8.0, "molar_volume_cm3_mol": 230})
add("API032", "Insulin (placeholder)", "insulin", "api", "biologic", "peptide payload", "", "",
    "parenteral;pulmonary", "PLACEHOLDER payload; conformational/aggregation liabilities; verify all data", 0.3, "estimated",
    {"MW": 5808, "acid_base": "amphoteric"},
    {"delta_D": 18.0, "delta_P": 14.0, "delta_H": 20.0, "hsp_radius": 12.0})
add("API033", "siRNA (placeholder)", "small interfering RNA", "api", "biologic", "nucleic acid payload", "", "",
    "parenteral", "PLACEHOLDER payload; polyanion, nuclease-sensitive; needs condensation/endosomal escape", 0.3, "estimated",
    {"MW": 13300, "acid_base": "acid", "formal_charge": -40},
    {})
add("API034", "mRNA (placeholder)", "messenger RNA", "api", "biologic", "nucleic acid payload", "", "",
    "parenteral;pulmonary", "PLACEHOLDER payload; large polyanion; requires ionizable-lipid LNP", 0.3, "estimated",
    {"MW": 330000, "acid_base": "acid", "formal_charge": -1000},
    {})

# --------------------------- Nonionic surfactants -------------------------- #
def surf(id, name, syn, cat, cas, cid, hlb, mw, nc, unsat, ntails, conf, notes, flags=None, est=None):
    props = {"MW": mw, "HLB": hlb, "tail_carbons": nc, "tail_unsaturation": unsat,
             "n_tails": ntails, "formal_charge": 0}
    props.update(flags or {})
    add(id, name, syn, "nonionic_surfactant", cat, "", cas, cid,
        "oral;topical;parenteral;pulmonary", notes, conf, "hpe", props, est or {})


surf("SUR001", "Span 20", "sorbitan monolaurate", "sorbitan ester", "1338-39-2", "9920342", 8.6, 346.46, 12, 0, 1, 0.75,
     "Low-HLB sorbitan ester; vesicle former", {"vesicle_anchor": 1}, {"headgroup_area_nm2": 0.45, "molar_volume_cm3_mol": 340})
surf("SUR002", "Span 40", "sorbitan monopalmitate", "sorbitan ester", "26266-57-9", "9920343", 6.7, 402.57, 16, 0, 1, 0.75,
     "Low-HLB; higher Tm vesicles", {"vesicle_anchor": 1}, {"headgroup_area_nm2": 0.43, "molar_volume_cm3_mol": 400})
surf("SUR003", "Span 60", "sorbitan monostearate", "sorbitan ester", "1338-41-6", "9920344", 4.7, 430.62, 18, 0, 1, 0.8,
     "Classic niosome former; rigid bilayer", {"vesicle_anchor": 1}, {"headgroup_area_nm2": 0.42, "molar_volume_cm3_mol": 430})
surf("SUR004", "Span 65", "sorbitan tristearate", "sorbitan ester", "26658-19-5", "", 2.1, 963.5, 18, 0, 3, 0.7,
     "Very low HLB tri-ester", {"vesicle_anchor": 1}, {"headgroup_area_nm2": 0.5, "molar_volume_cm3_mol": 960})
surf("SUR005", "Span 80", "sorbitan monooleate", "sorbitan ester", "1338-43-8", "9920345", 4.3, 428.6, 18, 1, 1, 0.8,
     "Unsaturated; fluid vesicle former", {"vesicle_anchor": 1}, {"headgroup_area_nm2": 0.46, "molar_volume_cm3_mol": 430})
surf("SUR006", "Span 85", "sorbitan trioleate", "sorbitan ester", "26266-58-0", "", 1.8, 957.5, 18, 1, 3, 0.7,
     "Very low HLB tri-oleate", {"vesicle_anchor": 1}, {"headgroup_area_nm2": 0.55, "molar_volume_cm3_mol": 950})
surf("SUR007", "Tween 20", "polysorbate 20", "polysorbate", "9005-64-5", "443314", 16.7, 1227.5, 12, 0, 1, 0.8,
     "High-HLB; micelle-forming stabilizer", {"edge_activator": 1}, {"headgroup_area_nm2": 0.9, "molar_volume_cm3_mol": 1150})
surf("SUR008", "Tween 40", "polysorbate 40", "polysorbate", "9005-66-7", "", 15.6, 1277.5, 16, 0, 1, 0.75,
     "High-HLB stabilizer", {"edge_activator": 1}, {"headgroup_area_nm2": 0.88, "molar_volume_cm3_mol": 1200})
surf("SUR009", "Tween 60", "polysorbate 60", "polysorbate", "9005-67-8", "", 14.9, 1311.7, 18, 0, 1, 0.8,
     "High-HLB; pairs with Span 60", {"edge_activator": 1}, {"headgroup_area_nm2": 0.86, "molar_volume_cm3_mol": 1250})
surf("SUR010", "Tween 80", "polysorbate 80", "polysorbate", "9005-65-6", "5281955", 15.0, 1310.0, 18, 1, 1, 0.85,
     "Most common polysorbate; edge activator", {"edge_activator": 1}, {"headgroup_area_nm2": 0.9, "molar_volume_cm3_mol": 1250})
surf("SUR011", "Tween 85", "polysorbate 85", "polysorbate", "9005-70-3", "", 11.0, 1839.0, 18, 1, 3, 0.7,
     "Tri-ester polysorbate", {}, {"headgroup_area_nm2": 1.0, "molar_volume_cm3_mol": 1800})
surf("SUR012", "Brij 35", "polyoxyethylene (23) lauryl ether", "brij", "9002-92-0", "", 16.9, 1198.0, 12, 0, 1, 0.75,
     "High-HLB; strong micelle former", {"edge_activator": 1}, {"headgroup_area_nm2": 0.9, "molar_volume_cm3_mol": 1150})
surf("SUR013", "Brij 52", "polyoxyethylene (2) cetyl ether", "brij", "9004-95-9", "", 5.3, 330.5, 16, 0, 1, 0.7,
     "Low-HLB vesicle former", {"vesicle_anchor": 1}, {"headgroup_area_nm2": 0.42, "molar_volume_cm3_mol": 330})
surf("SUR014", "Brij 58", "polyoxyethylene (20) cetyl ether", "brij", "9004-95-9", "", 15.7, 1124.0, 16, 0, 1, 0.72,
     "High-HLB stabilizer", {"edge_activator": 1}, {"headgroup_area_nm2": 0.85, "molar_volume_cm3_mol": 1100})
surf("SUR015", "Brij 72", "polyoxyethylene (2) stearyl ether", "brij", "9005-00-9", "", 4.9, 358.6, 18, 0, 1, 0.72,
     "Low-HLB rigid vesicle former", {"vesicle_anchor": 1}, {"headgroup_area_nm2": 0.42, "molar_volume_cm3_mol": 360})
surf("SUR016", "Brij 78", "polyoxyethylene (20) stearyl ether / Brij S20", "brij", "9005-00-9", "", 15.3, 1152.0, 18, 0, 1, 0.72,
     "High-HLB stabilizer", {"edge_activator": 1}, {"headgroup_area_nm2": 0.85, "molar_volume_cm3_mol": 1130})
surf("SUR017", "Brij 93", "polyoxyethylene (2) oleyl ether", "brij", "9004-98-2", "", 4.9, 357.0, 18, 1, 1, 0.7,
     "Low-HLB unsaturated vesicle former", {"vesicle_anchor": 1}, {"headgroup_area_nm2": 0.46, "molar_volume_cm3_mol": 360})
surf("SUR018", "Poloxamer 188", "Pluronic F68 / Kolliphor P188", "poloxamer", "9003-11-6", "", 29.0, 8400.0, 0, 0, 0, 0.7,
     "Steric stabilizer; PEO-PPO-PEO; HLB>24 nominal", {"edge_activator": 1}, {"headgroup_area_nm2": 2.0, "molar_volume_cm3_mol": 7000})
surf("SUR019", "Poloxamer 407", "Pluronic F127 / Kolliphor P407", "poloxamer", "9003-11-6", "", 22.0, 12600.0, 0, 0, 0, 0.7,
     "Steric stabilizer; thermogelling", {"edge_activator": 1}, {"headgroup_area_nm2": 2.2, "molar_volume_cm3_mol": 10500})
surf("SUR020", "Kolliphor HS15", "Solutol HS15 / macrogol-15-hydroxystearate", "solubilizer", "70142-34-6", "", 15.0, 960.0, 18, 0, 1, 0.7,
     "Parenteral solubilizer", {"edge_activator": 1}, {"headgroup_area_nm2": 0.8, "molar_volume_cm3_mol": 900})
surf("SUR021", "Kolliphor EL", "Cremophor EL / polyoxyl-35 castor oil", "solubilizer", "61791-12-6", "", 13.0, 2500.0, 18, 1, 1, 0.68,
     "Solubilizer; hypersensitivity risk", {"toxicity_penalty": 0.3}, {"headgroup_area_nm2": 1.2, "molar_volume_cm3_mol": 2400})
surf("SUR022", "Kolliphor RH40", "Cremophor RH40 / polyoxyl-40 hydrogenated castor oil", "solubilizer", "61788-85-0", "", 15.0, 2500.0, 18, 0, 1, 0.68,
     "Solubilizer", {}, {"headgroup_area_nm2": 1.2, "molar_volume_cm3_mol": 2400})
surf("SUR023", "Labrasol", "caprylocaproyl polyoxyl-8 glycerides", "solubilizer", "85536-07-8", "", 12.0, 600.0, 8, 0, 1, 0.65,
     "Oral solubilizer / permeation enhancer", {}, {"headgroup_area_nm2": 0.7, "molar_volume_cm3_mol": 560})
surf("SUR024", "Transcutol P", "diethylene glycol monoethyl ether", "cosolvent", "111-90-0", "8177", 4.2, 134.17, 4, 0, 1, 0.68,
     "Solubilizer / permeation enhancer (also co-solvent)", {}, {"headgroup_area_nm2": 0.3, "molar_volume_cm3_mol": 130})
surf("SUR025", "Vitamin E TPGS", "D-alpha-tocopheryl PEG-1000 succinate", "solubilizer", "9002-96-4", "", 13.2, 1513.0, 16, 0, 1, 0.7,
     "P-gp inhibitor; stabilizer; solubilizer", {"edge_activator": 1}, {"headgroup_area_nm2": 0.9, "molar_volume_cm3_mol": 1400})
surf("SUR026", "Soluplus", "PVCL-PVA-PEG graft copolymer", "polymeric solubilizer", "402932-23-4", "", 14.0, 118000.0, 0, 0, 0, 0.62,
     "Amphiphilic graft copolymer for ASD/micelles", {}, {"headgroup_area_nm2": 3.0, "molar_volume_cm3_mol": 90000})
surf("SUR027", "Gelucire 44/14", "lauroyl polyoxyl-32 glycerides", "solubilizer", "", "", 14.0, 900.0, 12, 0, 1, 0.62,
     "Self-emulsifying oral solubilizer (mp ~44C)", {}, {"headgroup_area_nm2": 0.8, "molar_volume_cm3_mol": 850})

# ------------------ Ionic surfactants / charge inducers -------------------- #
add("ION001", "Sodium lauryl sulfate", "SLS;SDS;sodium dodecyl sulfate", "ionic_surfactant", "anionic surfactant", "", "151-21-3", "3423265",
    "topical;oral", "Anionic; membrane-lytic above CMC; irritant", 0.8, "hpe",
    {"MW": 288.38, "HLB": 40.0, "tail_carbons": 12, "tail_unsaturation": 0, "n_tails": 1,
     "formal_charge": -1, "charge_inducer": 1, "CMC_mM": 8.2, "toxicity_penalty": 0.3},
    {"headgroup_area_nm2": 0.6, "molar_volume_cm3_mol": 250})
add("ION002", "Sodium oleate", "", "ionic_surfactant", "anionic (fatty acid salt)", "", "143-19-1", "23665730",
    "topical;oral", "Anionic charge inducer; pH sensitive", 0.72, "pubchem",
    {"MW": 304.44, "HLB": 18.0, "tail_carbons": 18, "tail_unsaturation": 1, "n_tails": 1,
     "formal_charge": -1, "charge_inducer": 1},
    {"headgroup_area_nm2": 0.35, "molar_volume_cm3_mol": 320})
add("ION003", "Cetyltrimethylammonium bromide", "CTAB", "ionic_surfactant", "cationic surfactant", "", "57-09-0", "5974",
    "topical", "Cationic; cytotoxic; research charge inducer", 0.75, "pubchem",
    {"MW": 364.45, "HLB": 10.0, "tail_carbons": 16, "tail_unsaturation": 0, "n_tails": 1,
     "formal_charge": 1, "charge_inducer": 1, "cationic": 1, "CMC_mM": 1.0, "toxicity_penalty": 0.5},
    {"headgroup_area_nm2": 0.6, "molar_volume_cm3_mol": 350})
add("ION004", "Dimethyldioctadecylammonium bromide", "DDAB", "ionic_surfactant", "cationic lipid", "", "3700-67-2", "13013",
    "parenteral;topical", "Cationic bilayer former; cytotoxic", 0.7, "pubchem",
    {"MW": 630.95, "HLB": 5.0, "tail_carbons": 18, "tail_unsaturation": 0, "n_tails": 2,
     "formal_charge": 1, "charge_inducer": 1, "cationic": 1, "vesicle_anchor": 1, "toxicity_penalty": 0.4},
    {"headgroup_area_nm2": 0.55, "molar_volume_cm3_mol": 640})
add("ION005", "Dicetyl phosphate", "DCP", "ionic_surfactant", "anionic charge inducer", "", "2197-63-9", "",
    "topical;oral;parenteral", "Classic negative charge inducer for niosomes/liposomes", 0.72, "pubchem",
    {"MW": 546.85, "HLB": 2.0, "tail_carbons": 16, "tail_unsaturation": 0, "n_tails": 2,
     "formal_charge": -1, "charge_inducer": 1, "vesicle_anchor": 1},
    {"headgroup_area_nm2": 0.4, "molar_volume_cm3_mol": 560})
add("ION006", "Stearylamine", "octadecylamine", "ionic_surfactant", "cationic charge inducer", "", "124-30-1", "15793",
    "topical;parenteral", "Positive charge inducer; cytotoxic at high levels", 0.7, "pubchem",
    {"MW": 269.51, "HLB": 3.0, "tail_carbons": 18, "tail_unsaturation": 0, "n_tails": 1,
     "formal_charge": 1, "charge_inducer": 1, "cationic": 1, "toxicity_penalty": 0.3},
    {"headgroup_area_nm2": 0.35, "molar_volume_cm3_mol": 300})
add("ION007", "DOTAP", "1,2-dioleoyl-3-trimethylammonium-propane", "ionic_surfactant", "cationic lipid", "", "132172-61-3", "6437392",
    "parenteral", "Cationic lipid for nucleic-acid complexation", 0.72, "avanti",
    {"MW": 698.54, "tail_carbons": 18, "tail_unsaturation": 1, "n_tails": 2,
     "formal_charge": 1, "charge_inducer": 1, "cationic": 1, "vesicle_anchor": 1, "Tm_C": -12},
    {"headgroup_area_nm2": 0.7, "molar_volume_cm3_mol": 700, "HLB": 6.0})
add("ION008", "DC-Cholesterol", "DC-Chol", "ionic_surfactant", "cationic sterol", "", "166023-21-8", "",
    "parenteral", "Cationic cholesterol derivative; gene delivery", 0.68, "avanti",
    {"MW": 537.3, "formal_charge": 1, "charge_inducer": 1, "cationic": 1, "vesicle_anchor": 1},
    {"headgroup_area_nm2": 0.4, "molar_volume_cm3_mol": 520, "HLB": 5.0})

# ------------------------------ Phospholipids ------------------------------ #
def plip(id, name, syn, cat, cid, mw, tm, nc, unsat, ntails, charge, conf, notes, extra=None, est=None):
    props = {"MW": mw, "Tm_C": tm, "tail_carbons": nc, "tail_unsaturation": unsat,
             "n_tails": ntails, "formal_charge": charge, "vesicle_anchor": 1}
    props.update(extra or {})
    e = {"headgroup_area_nm2": 0.65, "molar_volume_cm3_mol": mw * 0.95}
    e.update(est or {})
    add(id, name, syn, "phospholipid", cat, "", "", cid, "parenteral;pulmonary;topical",
        notes, conf, "avanti", props, e)


plip("PL001", "Lecithin", "phosphatidylcholine mixture", "natural PC", "", 770.0, -20, 17, 1.5, 2, 0, 0.65,
     "Natural PC mixture; grade/source dependent", {"HLB": 4.0}, {"headgroup_area_nm2": 0.68})
plip("PL002", "Egg phosphatidylcholine", "EPC", "natural PC", "", 770.0, -15, 17, 1.2, 2, 0, 0.7,
     "Fluid natural PC", {"HLB": 4.0})
plip("PL003", "Soy phosphatidylcholine", "SPC", "natural PC", "", 780.0, -20, 18, 1.8, 2, 0, 0.7,
     "Highly unsaturated natural PC", {"HLB": 4.0})
plip("PL004", "Hydrogenated soy phosphatidylcholine", "HSPC", "saturated PC", "", 783.8, 53, 18, 0, 2, 0, 0.75,
     "Rigid saturated PC; long-circulating liposomes", {"HLB": 4.0})
plip("PL005", "DLPC", "1,2-dilauroyl-sn-glycero-3-PC", "saturated PC", "", 621.83, -1, 12, 0, 2, 0, 0.75, "Short-chain PC")
plip("PL006", "DMPC", "1,2-dimyristoyl-sn-glycero-3-PC", "saturated PC", "", 677.93, 24, 14, 0, 2, 0, 0.8, "Common model PC")
plip("PL007", "DPPC", "1,2-dipalmitoyl-sn-glycero-3-PC", "saturated PC", "452110", 733.95, 41, 16, 0, 2, 0, 0.85,
     "Lung surfactant lipid; Tm ~41C")
plip("PL008", "DSPC", "1,2-distearoyl-sn-glycero-3-PC", "saturated PC", "94190", 790.15, 55, 18, 0, 2, 0, 0.85,
     "Rigid; LNP/liposome helper")
plip("PL009", "DOPC", "1,2-dioleoyl-sn-glycero-3-PC", "unsaturated PC", "5497103", 786.11, -17, 18, 1, 2, 0, 0.85,
     "Fluid unsaturated PC")
plip("PL010", "POPC", "1-palmitoyl-2-oleoyl-sn-glycero-3-PC", "unsaturated PC", "", 760.08, -2, 17, 0.5, 2, 0, 0.82,
     "Common fluid membrane PC")
plip("PL011", "DOPE", "1,2-dioleoyl-sn-glycero-3-PE", "PE (fusogenic)", "", 744.03, -16, 18, 1, 2, 0, 0.8,
     "Fusogenic helper; endosomal escape", {"fusogenic": 1}, {"headgroup_area_nm2": 0.5})
plip("PL012", "DSPE", "1,2-distearoyl-sn-glycero-3-PE", "PE", "", 748.07, 74, 18, 0, 2, 0, 0.75, "Saturated PE", {}, {"headgroup_area_nm2": 0.5})
plip("PL013", "DSPE-PEG2000", "1,2-distearoyl-sn-glycero-3-PE-N-[amino(PEG)-2000]", "PEG-lipid", "", 2805.5, 0, 18, 0, 2, -1, 0.75,
     "Steric shield; long-circulating; ~5 mol% typical", {"pegylated": 1, "edge_activator": 1}, {"headgroup_area_nm2": 1.2})
plip("PL014", "DMG-PEG2000", "1,2-dimyristoyl-rac-glycero-3-methoxy-PEG-2000", "PEG-lipid", "", 2509.2, 0, 14, 0, 2, 0, 0.72,
     "LNP PEG-lipid (mRNA)", {"pegylated": 1}, {"headgroup_area_nm2": 1.2})
plip("PL015", "DOPS", "1,2-dioleoyl-sn-glycero-3-phospho-L-serine", "anionic PS", "", 810.02, -11, 18, 1, 2, -1, 0.72,
     "Anionic PS; charge inducer", {"charge_inducer": 1}, {"headgroup_area_nm2": 0.6})
plip("PL016", "DPPG", "1,2-dipalmitoyl-sn-glycero-3-PG", "anionic PG", "", 744.96, 41, 16, 0, 2, -1, 0.75,
     "Anionic charge; lung surfactant component", {"charge_inducer": 1}, {"headgroup_area_nm2": 0.6})
plip("PL017", "DOPG", "1,2-dioleoyl-sn-glycero-3-PG", "anionic PG", "", 797.03, -18, 18, 1, 2, -1, 0.75,
     "Fluid anionic PG", {"charge_inducer": 1}, {"headgroup_area_nm2": 0.64})
plip("PL018", "Sphingomyelin", "egg SM", "sphingolipid", "", 703.0, 39, 17, 0.2, 2, 0, 0.65,
     "Sphingolipid; rigidifies with cholesterol", {}, {"headgroup_area_nm2": 0.6})
# Ionizable lipids
add("PL019", "DLin-MC3-DMA", "MC3", "phospholipid", "ionizable lipid", "", "", "",
    "parenteral", "Benchmark ionizable lipid (siRNA LNP); apparent pKa ~6.4", 0.68, "literature",
    {"MW": 642.1, "tail_carbons": 18, "tail_unsaturation": 2, "n_tails": 2, "formal_charge": 0,
     "pKa": 6.44, "acid_base": "base", "ionizable": 1, "vesicle_anchor": 1, "fusogenic": 1},
    {"headgroup_area_nm2": 0.6, "molar_volume_cm3_mol": 640, "HLB": 4.0})
add("PL020", "SM-102", "", "phospholipid", "ionizable lipid", "", "2089251-47-6", "",
    "parenteral;pulmonary", "mRNA-vaccine ionizable lipid; apparent pKa ~6.7", 0.66, "literature",
    {"MW": 710.2, "tail_carbons": 9, "tail_unsaturation": 0, "n_tails": 2, "formal_charge": 0,
     "pKa": 6.68, "acid_base": "base", "ionizable": 1, "vesicle_anchor": 1, "fusogenic": 1},
    {"headgroup_area_nm2": 0.65, "molar_volume_cm3_mol": 720, "HLB": 4.0})
add("PL021", "DODAP", "1,2-dioleoyl-3-dimethylammonium-propane", "phospholipid", "ionizable lipid", "", "127512-63-0", "",
    "parenteral", "pH-titratable ionizable lipid; apparent pKa ~6.6", 0.66, "literature",
    {"MW": 648.06, "tail_carbons": 18, "tail_unsaturation": 1, "n_tails": 2, "formal_charge": 0,
     "pKa": 6.6, "acid_base": "base", "ionizable": 1, "vesicle_anchor": 1},
    {"headgroup_area_nm2": 0.62, "molar_volume_cm3_mol": 650, "HLB": 4.0})

# -------------------------------- Sterols ---------------------------------- #
add("STE001", "Cholesterol", "CHOL", "sterol", "sterol", "", "57-88-5", "5997",
    "parenteral;pulmonary;topical;oral", "Membrane rigidity/fluidity modulator; reduces leakage", 0.85, "avanti",
    {"MW": 386.65, "melting_point_C": 148, "formal_charge": 0, "vesicle_anchor": 1},
    {"headgroup_area_nm2": 0.38, "molar_volume_cm3_mol": 380, "delta_D": 17.0, "delta_P": 3.0, "delta_H": 4.0})
add("STE002", "Cholesteryl hemisuccinate", "CHEMS", "sterol", "anionic sterol", "", "1510-21-0", "97570",
    "parenteral", "pH-sensitive anionic sterol; endosomal escape systems", 0.68, "avanti",
    {"MW": 486.73, "formal_charge": -1, "charge_inducer": 1, "vesicle_anchor": 1, "acid_base": "acid", "pKa": 5.8},
    {"headgroup_area_nm2": 0.4, "molar_volume_cm3_mol": 480})
add("STE003", "Ergosterol", "", "sterol", "sterol", "", "57-87-4", "444679",
    "topical;oral", "Fungal sterol analog", 0.65, "pubchem",
    {"MW": 396.65, "melting_point_C": 160, "formal_charge": 0, "vesicle_anchor": 1},
    {"headgroup_area_nm2": 0.39, "molar_volume_cm3_mol": 390})
add("STE004", "Beta-sitosterol", "", "sterol", "phytosterol", "", "83-46-5", "222284",
    "oral;topical", "Phytosterol cholesterol alternative", 0.65, "pubchem",
    {"MW": 414.71, "melting_point_C": 140, "formal_charge": 0, "vesicle_anchor": 1},
    {"headgroup_area_nm2": 0.4, "molar_volume_cm3_mol": 410})
add("STE005", "Stigmasterol", "", "sterol", "phytosterol", "", "83-48-7", "5280794",
    "oral;topical", "Phytosterol", 0.63, "pubchem",
    {"MW": 412.69, "melting_point_C": 170, "formal_charge": 0, "vesicle_anchor": 1},
    {"headgroup_area_nm2": 0.4, "molar_volume_cm3_mol": 410})

# ------------------------------- Bile salts -------------------------------- #
def bile(id, name, syn, cid, mw, conf, notes):
    add(id, name, syn, "bile_salt", "bile salt", "", "", cid, "oral", notes, conf, "pubchem",
        {"MW": mw, "HLB": 18.0, "formal_charge": -1, "charge_inducer": 1, "edge_activator": 1,
         "tail_carbons": 0, "n_tails": 0},
        {"headgroup_area_nm2": 0.9, "molar_volume_cm3_mol": mw * 0.85, "CMC_mM": 5.0})


bile("BIL001", "Sodium cholate", "SC", "23668196", 430.55, 0.72, "Bilosome edge activator; oral vesicle stabilization")
bile("BIL002", "Sodium deoxycholate", "SDC", "23668195", 414.55, 0.72, "Strong edge activator; more lytic")
bile("BIL003", "Sodium taurocholate", "STC", "23666345", 537.68, 0.7, "Taurine-conjugated bile salt")
bile("BIL004", "Sodium glycocholate", "SGC", "23673453", 487.6, 0.68, "Glycine-conjugated bile salt")
bile("BIL005", "Sodium taurodeoxycholate", "STDC", "", 521.68, 0.66, "Conjugated deoxycholate")
bile("BIL006", "Sodium chenodeoxycholate", "SCDC", "", 414.55, 0.66, "Chenodeoxycholate salt")
bile("BIL007", "Sodium ursodeoxycholate", "SUDC", "", 414.55, 0.66, "UDCA salt; milder")

# --------------------- Solid lipids / fatty acids / waxes ------------------ #
def slipid(id, name, syn, type, cat, cas, cid, mw, mp, nc, unsat, conf, notes, est=None):
    add(id, name, syn, type, cat, "", cas, cid, "oral;parenteral;topical;pulmonary", notes, conf, "hpe",
        {"MW": mw, "melting_point_C": mp, "tail_carbons": nc, "tail_unsaturation": unsat, "formal_charge": 0},
        est or {"delta_D": 16.5, "delta_P": 3.5, "delta_H": 6.0, "molar_volume_cm3_mol": mw * 1.1})


slipid("FA001", "Lauric acid", "C12:0", "solid_lipid", "fatty acid", "143-07-7", "3893", 200.32, 44, 12, 0, 0.8, "Saturated FA")
slipid("FA002", "Myristic acid", "C14:0", "solid_lipid", "fatty acid", "544-63-8", "11005", 228.37, 54, 14, 0, 0.8, "Saturated FA")
slipid("FA003", "Palmitic acid", "C16:0", "solid_lipid", "fatty acid", "57-10-3", "985", 256.42, 63, 16, 0, 0.82, "Saturated FA")
slipid("FA004", "Stearic acid", "C18:0", "solid_lipid", "fatty acid", "57-11-4", "5281", 284.48, 69, 18, 0, 0.85, "SLN matrix FA")
slipid("FA005", "Oleic acid", "C18:1", "liquid_lipid", "fatty acid", "112-80-1", "445639", 282.46, 13, 18, 1, 0.82,
       "Liquid FA; NLC oil; permeation enhancer", {"delta_D": 16.5, "delta_P": 2.8, "delta_H": 6.2, "molar_volume_cm3_mol": 320})
slipid("FA006", "Linoleic acid", "C18:2", "liquid_lipid", "fatty acid", "60-33-3", "5280450", 280.45, -5, 18, 2, 0.78,
       "Polyunsaturated liquid FA", {"delta_D": 16.5, "delta_P": 2.8, "delta_H": 6.5, "molar_volume_cm3_mol": 320})
slipid("SL001", "Glyceryl monostearate", "GMS", "solid_lipid", "glyceride", "31566-31-1", "24699", 358.56, 58, 18, 0, 0.75,
       "SLN matrix lipid; emulsifier")
slipid("SL002", "Glyceryl behenate", "Compritol 888 ATO", "solid_lipid", "glyceride", "", "", 1059.0, 72, 22, 0, 0.72,
       "SLN/sustained-release matrix; mp ~70-72C")
slipid("SL003", "Glyceryl palmitostearate", "Precirol ATO 5", "solid_lipid", "glyceride", "", "", 700.0, 56, 17, 0, 0.72,
       "SLN matrix; mp ~52-56C")
slipid("SL004", "Tripalmitin", "Dynasan 116", "solid_lipid", "triglyceride", "555-44-2", "11147", 807.32, 66, 16, 0, 0.75,
       "Highly crystalline; drug expulsion risk")
slipid("SL005", "Tristearin", "Dynasan 118", "solid_lipid", "triglyceride", "555-43-1", "10850", 891.48, 73, 18, 0, 0.75,
       "Highly crystalline triglyceride")
slipid("SL006", "Cetyl palmitate", "", "solid_lipid", "wax ester", "540-10-3", "10723", 480.85, 54, 16, 0, 0.72,
       "Wax ester SLN matrix")
slipid("SL007", "Beeswax", "cera alba", "solid_lipid", "wax", "8012-89-3", "", 677.0, 64, 26, 0, 0.6,
       "Natural wax; variable composition")
slipid("SL008", "Carnauba wax", "", "solid_lipid", "wax", "8015-86-9", "", 700.0, 83, 28, 0, 0.6,
       "High-melting natural wax")

# ------------------------------ Liquid lipids ------------------------------ #
def olipid(id, name, syn, cas, cid, mw, conf, notes, est):
    add(id, name, syn, "liquid_lipid", "oil", "", cas, cid, "oral;topical;parenteral", notes, conf, "supplier",
        {"MW": mw, "formal_charge": 0}, est)


olipid("OIL001", "Ethyl oleate", "", "111-62-6", "5364423", 310.51, 0.75,
       "Parenteral oil vehicle; NLC oil", {"delta_D": 16.2, "delta_P": 2.6, "delta_H": 4.2, "molar_volume_cm3_mol": 350, "density_g_ml": 0.87})
olipid("OIL002", "Medium-chain triglycerides", "MCT;Miglyol 812;caprylic/capric triglyceride", "73398-61-5", "", 500.0, 0.72,
       "Common NLC/nanoemulsion oil", {"delta_D": 16.0, "delta_P": 3.0, "delta_H": 4.5, "molar_volume_cm3_mol": 520, "density_g_ml": 0.95})
olipid("OIL003", "Isopropyl myristate", "IPM", "110-27-0", "8042", 270.45, 0.75,
       "Topical/transdermal oil; permeation enhancer", {"delta_D": 16.1, "delta_P": 3.7, "delta_H": 4.0, "molar_volume_cm3_mol": 310, "density_g_ml": 0.85})
olipid("OIL004", "Castor oil", "ricinus oil", "8001-79-4", "", 933.0, 0.68,
       "Hydroxylated triglyceride oil", {"delta_D": 16.0, "delta_P": 3.5, "delta_H": 7.0, "molar_volume_cm3_mol": 950, "density_g_ml": 0.96})
olipid("OIL005", "Soybean oil", "", "8001-22-7", "", 874.0, 0.7,
       "Parenteral emulsion oil (long-chain triglyceride)", {"delta_D": 16.2, "delta_P": 2.9, "delta_H": 4.6, "molar_volume_cm3_mol": 900, "density_g_ml": 0.92})
olipid("OIL006", "Squalene", "", "111-02-4", "638072", 410.72, 0.7,
       "Adjuvant/emulsion oil (MF59-like)", {"delta_D": 16.0, "delta_P": 1.0, "delta_H": 2.0, "molar_volume_cm3_mol": 520, "density_g_ml": 0.86})
olipid("OIL007", "Squalane", "", "111-01-3", "12626", 422.81, 0.7,
       "Saturated stable emulsion oil", {"delta_D": 15.9, "delta_P": 0.5, "delta_H": 1.5, "molar_volume_cm3_mol": 530, "density_g_ml": 0.81})
olipid("OIL008", "Capryol 90", "propylene glycol monocaprylate", "", "", 244.0, 0.62,
       "Self-emulsifying oil/solubilizer", {"delta_D": 16.3, "delta_P": 4.5, "delta_H": 8.0, "molar_volume_cm3_mol": 270, "density_g_ml": 0.95})

# -------------------------------- Solvents --------------------------------- #
def solv(id, name, syn, cas, cid, mw, dens, bp, dD, dP, dH, ich, misc, pol, conf, notes, pde=""):
    props = {"MW": mw, "density_g_ml": dens, "boiling_point_C": bp, "water_miscibility": misc,
             "polarity_index": pol, "ICH_class": ich}
    if pde != "":
        props["PDE_mg_day"] = pde
    add(id, name, syn, "solvent", "solvent", "", cas, cid, "process", notes, conf, "ich_q3c",
        props, {"delta_D": dD, "delta_P": dP, "delta_H": dH, "molar_volume_cm3_mol": mw / dens if dens else None})


solv("SOL001", "Water", "purified water", "7732-18-5", "962", 18.02, 1.00, 100, 15.5, 16.0, 42.3, "none", 1.0, 10.2, 0.9, "Aqueous phase / hydration medium")
solv("SOL002", "Ethanol", "EtOH", "64-17-5", "702", 46.07, 0.789, 78, 15.8, 8.8, 19.4, "3", 1.0, 5.2, 0.9, "GRAS; ethosome/injection cosolvent", 50)
solv("SOL003", "Methanol", "MeOH", "67-56-1", "887", 32.04, 0.792, 65, 15.1, 12.3, 22.3, "2", 1.0, 5.1, 0.85, "Toxic; class 2", 30)
solv("SOL004", "Acetone", "", "67-64-1", "180", 58.08, 0.784, 56, 15.5, 10.4, 7.0, "3", 1.0, 5.1, 0.85, "Nanoprecipitation solvent", 50)
solv("SOL005", "Ethyl acetate", "EtOAc", "141-78-6", "8857", 88.11, 0.902, 77, 15.8, 5.3, 7.2, "3", 0.3, 4.4, 0.82, "Emulsion/nanoprecipitation solvent", 50)
solv("SOL006", "Chloroform", "", "67-66-3", "6212", 119.38, 1.489, 61, 17.8, 3.1, 5.7, "2", 0.0, 4.1, 0.82, "Lipid film solvent; toxic class 2", 0.6)
solv("SOL007", "Dichloromethane", "DCM;methylene chloride", "75-09-2", "6344", 84.93, 1.326, 40, 18.2, 6.3, 6.1, "2", 0.02, 3.1, 0.82, "Emulsion solvent; class 2", 6.0)
solv("SOL008", "Dimethyl sulfoxide", "DMSO", "67-68-5", "679", 78.13, 1.100, 189, 18.4, 16.4, 10.2, "3", 1.0, 7.2, 0.82, "High-boiling aprotic; class 3", 50)
solv("SOL009", "Acetonitrile", "MeCN", "75-05-8", "6342", 41.05, 0.786, 82, 15.3, 18.0, 6.1, "2", 1.0, 5.8, 0.8, "Class 2 solvent", 4.1)
solv("SOL010", "Isopropanol", "IPA;2-propanol", "67-63-0", "3776", 60.10, 0.786, 82, 15.8, 6.1, 16.4, "3", 1.0, 3.9, 0.85, "GRAS cosolvent", 50)
solv("SOL011", "Propylene glycol", "PG", "57-55-6", "1030", 76.09, 1.036, 188, 16.8, 9.4, 23.3, "none", 1.0, 5.5, 0.85, "GRAS cosolvent/humectant")
solv("SOL012", "PEG 400", "polyethylene glycol 400", "25322-68-3", "", 400.0, 1.125, 250, 16.4, 9.0, 18.0, "none", 1.0, 5.0, 0.7, "Liquid PEG cosolvent")
solv("SOL013", "Glycerol", "glycerin", "56-81-5", "753", 92.09, 1.261, 290, 17.4, 12.1, 29.3, "none", 1.0, 6.2, 0.85, "GRAS humectant/cosolvent")
solv("SOL014", "N-methyl-2-pyrrolidone", "NMP", "872-50-4", "13387", 99.13, 1.028, 202, 18.0, 12.3, 7.2, "2", 1.0, 6.7, 0.7, "Strong aprotic; class 2 (reproductive)", 5.3)
solv("SOL015", "tert-Butanol", "TBA", "75-65-0", "6386", 74.12, 0.781, 82, 15.2, 5.1, 14.7, "3", 1.0, 3.9, 0.72, "Lyophilization cosolvent", 50)
solv("SOL016", "n-Hexane", "", "110-54-3", "8058", 86.18, 0.655, 69, 14.9, 0.0, 0.0, "2", 0.0, 0.1, 0.75, "Nonpolar; class 2", 2.9)
solv("SOL017", "n-Heptane", "", "142-82-5", "8900", 100.2, 0.684, 98, 15.3, 0.0, 0.0, "3", 0.0, 0.1, 0.75, "Nonpolar; class 3", 50)
solv("SOL018", "Toluene", "", "108-88-3", "1140", 92.14, 0.867, 111, 18.0, 1.4, 2.0, "2", 0.0, 2.4, 0.75, "Aromatic; class 2", 8.9)
solv("SOL019", "Tetrahydrofuran", "THF", "109-99-9", "8028", 72.11, 0.889, 66, 16.8, 5.7, 8.0, "2", 1.0, 4.0, 0.75, "Peroxide-forming; class 2", 7.2)
solv("SOL020", "Triacetin", "glyceryl triacetate", "102-76-1", "5541", 218.20, 1.156, 259, 16.5, 4.5, 9.1, "none", 0.06, 4.5, 0.68, "Plasticizer/oil-like cosolvent")

# -------------------------------- Carriers --------------------------------- #
def carrier(id, name, syn, cat, cas, cid, mw, conf, notes, flags):
    props = {"formal_charge": 0}
    if mw:
        props["MW"] = mw
    props.update(flags)
    add(id, name, syn, "carrier", cat, "", cas, cid, "pulmonary;oral", notes, conf, "hpe", props,
        {"Tg_C": None})


carrier("CAR001", "Mannitol", "", "sugar alcohol", "69-65-8", "6251", 182.17, 0.82,
        "Cryo/lyoprotectant; DPI carrier; crystalline", {"cryoprotectant": 1, "melting_point_C": 166})
carrier("CAR002", "Trehalose", "", "disaccharide", "99-20-7", "7427", 342.30, 0.82,
        "Superior cryo/lyoprotectant (glass former)", {"cryoprotectant": 1, "Tg_C": 117})
carrier("CAR003", "Sucrose", "", "disaccharide", "57-50-1", "5988", 342.30, 0.8,
        "Cryo/lyoprotectant", {"cryoprotectant": 1, "Tg_C": 74})
carrier("CAR004", "Lactose monohydrate", "", "disaccharide", "64044-51-5", "", 360.31, 0.82,
        "Standard DPI carrier", {"porous_carrier": 0})
carrier("CAR005", "Sorbitol", "", "sugar alcohol", "50-70-4", "5780", 182.17, 0.75,
        "Cryoprotectant/plasticizer", {"cryoprotectant": 1})
carrier("CAR006", "L-Leucine", "leucine", "amino acid", "61-90-5", "6106", 131.17, 0.78,
        "Aerosolization/dispersibility enhancer for DPI", {"porous_carrier": 1})
carrier("CAR007", "Glycine", "", "amino acid", "56-40-6", "750", 75.07, 0.72,
        "Bulking agent / lyo", {"cryoprotectant": 1})
carrier("CAR008", "Beta-cyclodextrin", "b-CD", "cyclodextrin", "7585-39-9", "444041", 1134.98, 0.75,
        "Complexation host; limited aqueous solubility", {})
carrier("CAR009", "Hydroxypropyl-beta-cyclodextrin", "HP-b-CD", "cyclodextrin", "128446-35-5", "", 1400.0, 0.75,
        "Highly soluble complexation host; parenteral-grade available", {})
carrier("CAR010", "Sulfobutylether-beta-cyclodextrin", "SBE-b-CD;Captisol", "cyclodextrin", "182410-00-0", "", 2163.0, 0.72,
        "Anionic parenteral complexation host", {"formal_charge": -7})
carrier("CAR011", "Microcrystalline cellulose", "MCC;Avicel", "cellulose", "9004-34-6", "", None, 0.7,
        "Solid carrier/adsorbent", {"porous_carrier": 1})
carrier("CAR012", "Colloidal silicon dioxide", "Aerosil;fumed silica", "silica", "7631-86-9", "", 60.08, 0.72,
        "High-surface-area adsorbent carrier for liquisolid/DPI", {"porous_carrier": 1})
carrier("CAR013", "Maltodextrin", "", "polysaccharide", "9050-36-6", "", None, 0.65,
        "Spray-drying matrix former", {"cryoprotectant": 1})
carrier("CAR014", "Pullulan", "", "polysaccharide", "9057-02-7", "", None, 0.62,
        "Film/matrix former; glass former", {"cryoprotectant": 1})

# -------------------------------- Polymers --------------------------------- #
def poly(id, name, syn, cat, cas, avgmw, tg, charge, conf, notes, flags=None):
    props = {"avg_MW": avgmw, "formal_charge": charge}
    if tg is not None:
        props["Tg_C"] = tg
    props.update(flags or {})
    add(id, name, syn, "polymer", cat, "", cas, "", "parenteral;oral;topical", notes, conf, "supplier",
        props, {"delta_D": 17.0, "delta_P": 7.0, "delta_H": 8.0})


poly("POL001", "PLGA 50:50", "poly(lactic-co-glycolic acid) 50:50", "polyester", "26780-50-7", 30000, 45, 0, 0.75,
     "Biodegradable; fastest-degrading PLGA ratio")
poly("POL002", "PLGA 75:25", "poly(lactic-co-glycolic acid) 75:25", "polyester", "26780-50-7", 40000, 48, 0, 0.72,
     "Slower degradation, more lactide")
poly("POL003", "PLA", "poly(lactic acid)", "polyester", "26100-51-6", 50000, 55, 0, 0.72, "Slow-degrading polyester")
poly("POL004", "PCL", "polycaprolactone", "polyester", "24980-41-4", 45000, -60, 0, 0.72, "Very slow-degrading; low Tg")
poly("POL005", "PEG 2000", "polyethylene glycol 2000", "PEG", "25322-68-3", 2000, -20, 0, 0.75, "Steric shield / hydrophilic block")
poly("POL006", "PEG 5000", "polyethylene glycol 5000", "PEG", "25322-68-3", 5000, -15, 0, 0.72, "Longer PEG shield")
poly("POL007", "PVA", "polyvinyl alcohol", "vinyl polymer", "9002-89-5", 30000, 85, 0, 0.72,
     "Common nanoparticle stabilizer")
poly("POL008", "PVP K30", "povidone K30", "vinyl polymer", "9003-39-8", 50000, 168, 0, 0.72,
     "Stabilizer / crystallization inhibitor")
poly("POL009", "HPMC", "hypromellose", "cellulose ether", "9004-65-3", 22000, 175, 0, 0.7,
     "Stabilizer / matrix former")
poly("POL010", "Chitosan (low MW)", "", "polysaccharide (cationic)", "9012-76-4", 50000, 150, 1, 0.7,
     "Mucoadhesive cationic polymer; pKa ~6.5", {"cationic": 1, "charge_inducer": 1, "pKa": 6.5, "acid_base": "base"})
poly("POL011", "Trimethyl chitosan", "TMC", "polysaccharide (cationic)", "", 50000, None, 1, 0.62,
     "Permanently charged chitosan derivative", {"cationic": 1, "charge_inducer": 1})
poly("POL012", "Polyethylenimine (branched)", "PEI 25k", "cationic polymer", "9002-98-6", 25000, None, 1, 0.62,
     "Strong condenser; cytotoxic (proton sponge)", {"cationic": 1, "charge_inducer": 1, "toxicity_penalty": 0.5})
poly("POL013", "Hyaluronic acid", "HA;sodium hyaluronate", "polysaccharide (anionic)", "9004-61-9", 100000, None, -1, 0.68,
     "CD44-targeting anionic mucoadhesive", {"charge_inducer": 1})
poly("POL014", "Sodium alginate", "", "polysaccharide (anionic)", "9005-38-3", 120000, None, -1, 0.68,
     "Ionotropic gelling anionic polymer", {"charge_inducer": 1})
poly("POL015", "Dextran", "", "polysaccharide (neutral)", "9004-54-0", 40000, None, 0, 0.68, "Neutral hydrophilic polymer")
poly("POL016", "Eudragit RS", "poly(ethyl acrylate-co-methyl methacrylate-co-trimethylammonioethyl methacrylate)", "acrylate", "33434-24-1", 32000, 65, 1, 0.68,
     "Low-permeability sustained-release cationic acrylate", {"cationic": 1})
poly("POL017", "Eudragit L100", "poly(methacrylic acid-co-methyl methacrylate) 1:1", "acrylate", "25086-15-1", 125000, 130, -1, 0.68,
     "Enteric (dissolves > pH 6)", {"charge_inducer": 1, "acid_base": "acid", "pKa": 6.0})
poly("POL018", "Eudragit E PO", "poly(butyl methacrylate-co-dimethylaminoethyl methacrylate-co-methyl methacrylate)", "acrylate", "24938-16-7", 47000, 48, 1, 0.66,
     "Cationic; dissolves < pH 5; taste masking", {"cationic": 1, "acid_base": "base", "pKa": 6.0})
poly("POL019", "Gelatin", "", "protein", "9000-70-8", 50000, None, 0, 0.62, "Amphoteric protein carrier")
poly("POL020", "Human serum albumin", "HSA;albumin", "protein", "70024-90-7", 66500, None, -1, 0.65,
     "Nab-technology carrier protein", {"charge_inducer": 1})
poly("POL021", "Zein", "", "protein (prolamin)", "9010-66-6", 25000, 165, 0, 0.6, "Hydrophobic plant protein carrier")


# --------------------------------------------------------------------------- #
# Emit CSVs
# --------------------------------------------------------------------------- #
def _w(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(header)
        wr.writerows(rows)


def build():
    from nanoform import schema

    # sources.csv
    _w(REL / "sources.csv", schema.SOURCES_COLUMNS, SOURCES)

    # materials.csv + material_properties.csv
    mat_rows = []
    prop_rows = []
    for m in M:
        mat_rows.append([
            m["id"], m["name"], m["syn"], m["type"], m["cat"], m["sub"], m["cas"],
            m["cid"], "", "", "", m["route"], m["safety"], m["src"], "seed",
            m["conf"], "",
        ])
        for pname, pval in m["props"].items():
            if pval is None:
                continue
            prop_rows.append([m["id"], pname, pval, "", "", "", "", m["src"],
                              "literature", m["conf"], ""])
        capped = min(0.40, m["conf"])
        for pname, pval in m["est"].items():
            if pval is None:
                continue
            prop_rows.append([m["id"], pname, pval, "", "", "", "model/analogy",
                              "estimated", "estimated", capped,
                              "Heuristic estimate; verify in lab"])
    _w(REL / "materials.csv", schema.MATERIALS_COLUMNS, mat_rows)
    _w(REL / "material_properties.csv", schema.MATERIAL_PROPERTIES_COLUMNS, prop_rows)

    # Empty relational tables (headers only) + a clearly-marked example.
    _w(REL / "formulations.csv", schema.FORMULATIONS_COLUMNS, [
        ["EXAMPLE-001", "niosome", "topical", "thin-film hydration", "PBS",
         "7.4", "60", "literature", "EXAMPLE ROW ONLY - not an experimental outcome"],
    ])
    _w(REL / "formulation_components.csv", schema.FORMULATION_COMPONENTS_COLUMNS, [
        ["EXAMPLE-001", "SUR003", "surfactant", "", "", "47.5", "", ""],
        ["EXAMPLE-001", "STE001", "sterol", "", "", "47.5", "", ""],
        ["EXAMPLE-001", "ION005", "charge_inducer", "", "", "5.0", "", ""],
    ])
    _w(REL / "outcomes.csv", schema.OUTCOMES_COLUMNS, [])
    _w(REL / "curation_log.csv", schema.CURATION_LOG_COLUMNS, [
        [_dt.date.today().isoformat(), "ALL", "seed_build", "", "", "",
         "estimated;pubchem;hpe;avanti;ich_q3c;hsp_handbook",
         "Initial seed database generated by build_database.py"],
    ])

    print(f"Wrote {len(mat_rows)} materials and {len(prop_rows)} property rows.")
    return mat_rows, prop_rows


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    build()
    # Build derived internal-constant tables.
    from scripts.build_wide_constants import build_wide  # type: ignore
    build_wide()
    print("Database build complete.")
