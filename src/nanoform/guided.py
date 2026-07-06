"""Guided formulation wizard.

Given a drug, route, family and goal, produces a payload profile, suggested
material classes/categories, route warnings, and temporary candidate starting
points. Candidates are NOT stored formulations; they are heuristic starting
compositions to help a user begin, and must be verified experimentally.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .database import Database, get_database
from .designer import DesignInput

# Canonical membrane skeletons per family (mol% templates). Names must exist in
# the seed DB; if a preferred material is absent the wizard falls back.
FAMILY_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "niosome": [
        {"components": [("Span 60", "surfactant", 47.5), ("Cholesterol", "sterol", 47.5),
                        ("Dicetyl phosphate", "charge_inducer", 5.0)],
         "process": "thin-film hydration", "note": "Rigid Span 60 / cholesterol niosome, anionic"},
        {"components": [("Span 80", "surfactant", 50.0), ("Cholesterol", "sterol", 50.0)],
         "process": "thin-film hydration", "note": "Fluid Span 80 niosome"},
    ],
    "liposome": [
        {"components": [("HSPC", "phospholipid", 56.0), ("Cholesterol", "sterol", 39.0),
                        ("DSPE-PEG2000", "peg_lipid", 5.0)],
         "process": "thin-film hydration + extrusion", "note": "Stealth (PEGylated) rigid liposome"},
        {"components": [("DPPC", "phospholipid", 60.0), ("Cholesterol", "sterol", 40.0)],
         "process": "thin-film hydration + extrusion", "note": "Conventional DPPC/cholesterol liposome"},
    ],
    "transfersome": [
        {"components": [("Soy phosphatidylcholine", "phospholipid", 85.0), ("Tween 80", "edge_activator", 15.0)],
         "process": "thin-film hydration", "note": "Deformable transfersome (PC + edge activator)"},
    ],
    "ethosome": [
        {"components": [("Soy phosphatidylcholine", "phospholipid", 100.0)],
         "process": "cold method (high ethanol)", "note": "Ethosome — pair with ethanol 20-45% v/v"},
    ],
    "bilosome": [
        {"components": [("Span 60", "surfactant", 47.5), ("Cholesterol", "sterol", 42.5),
                        ("Sodium deoxycholate", "bile_salt", 10.0)],
         "process": "thin-film hydration", "note": "Bile-salt-stabilized oral vesicle"},
    ],
    "solid_lipid_nanoparticle": [
        {"components": [("Glyceryl behenate", "solid_lipid", 80.0), ("Tween 80", "surfactant", 20.0)],
         "process": "high-pressure homogenization", "note": "Compritol SLN"},
    ],
    "nanostructured_lipid_carrier": [
        {"components": [("Glyceryl behenate", "solid_lipid", 60.0), ("Oleic acid", "liquid_lipid", 20.0),
                        ("Tween 80", "surfactant", 20.0)],
         "process": "high-pressure homogenization", "note": "NLC (solid + liquid lipid)"},
    ],
    "nanoemulsion": [
        {"components": [("Medium-chain triglycerides", "liquid_lipid", 70.0), ("Kolliphor EL", "surfactant", 30.0)],
         "process": "high-pressure homogenization", "note": "O/W nanoemulsion"},
    ],
    "lipid_nanoparticle": [
        {"components": [("SM-102", "ionizable_lipid", 50.0), ("DSPC", "phospholipid", 10.0),
                        ("Cholesterol", "sterol", 38.5), ("DMG-PEG2000", "peg_lipid", 1.5)],
         "process": "microfluidic mixing", "note": "mRNA LNP (ionizable/helper/sterol/PEG)"},
    ],
    "polymeric_nanoparticle": [
        {"components": [("PLGA 50:50", "polymer", 90.0), ("PVA", "surfactant", 10.0)],
         "process": "nanoprecipitation", "note": "PLGA nanoparticle, PVA-stabilized"},
    ],
    "lipid_polymer_hybrid": [
        {"components": [("PLGA 50:50", "polymer", 70.0), ("Lecithin", "phospholipid", 20.0),
                        ("DSPE-PEG2000", "peg_lipid", 10.0)],
         "process": "nanoprecipitation", "note": "Polymer core + lipid/PEG shell"},
    ],
    "dry_powder_carrier": [
        {"components": [("Glyceryl behenate", "solid_lipid", 80.0), ("L-Leucine", "carrier", 20.0)],
         "process": "spray drying", "note": "Carrier-based dry powder"},
    ],
}

SUGGESTED_CLASSES = {
    "niosome": ["nonionic_surfactant", "sterol", "ionic_surfactant (charge inducer)"],
    "liposome": ["phospholipid", "sterol", "PEG-lipid", "charge inducer (optional)"],
    "transfersome": ["phospholipid", "edge activator (Tween/bile salt)"],
    "ethosome": ["phospholipid", "ethanol (solvent)"],
    "bilosome": ["nonionic_surfactant", "sterol", "bile_salt"],
    "solid_lipid_nanoparticle": ["solid_lipid", "surfactant/stabilizer"],
    "nanostructured_lipid_carrier": ["solid_lipid", "liquid_lipid", "surfactant"],
    "nanoemulsion": ["liquid_lipid (oil)", "surfactant", "co-surfactant"],
    "lipid_nanoparticle": ["ionizable lipid", "helper phospholipid", "sterol", "PEG-lipid"],
    "polymeric_nanoparticle": ["polymer", "stabilizer"],
    "lipid_polymer_hybrid": ["polymer", "phospholipid", "PEG-lipid"],
    "dry_powder_carrier": ["solid_lipid or polymer", "carrier / dispersibility aid"],
}


@dataclass
class WizardOutput:
    payload_profile: Dict[str, Any]
    suggested_classes: List[str]
    suggested_categories: List[str]
    route_warnings: List[str]
    candidates: List[DesignInput] = field(default_factory=list)


def payload_profile(drug_name: str, db: Optional[Database] = None) -> Dict[str, Any]:
    db = db or get_database()
    card = db.card(drug_name)
    if card is None:
        return {"resolved": False, "name": drug_name,
                "note": "Drug not in database — add it via Custom Material to enable HSP/pKa-based logic."}
    logp = card.get("logP")
    solub = card.get("water_solubility_mg_ml")
    prof = {
        "resolved": True, "name": card.name, "MW": card.get("MW"), "logP": logp,
        "pKa": card.get("pKa"), "acid_base": card.get("acid_base"),
        "water_solubility_mg_ml": solub, "BCS_class": card.get("BCS_class"),
        "payload_class": card.identity.get("subcategory") or card.category,
    }
    hints = []
    if isinstance(logp, (int, float)):
        if logp >= 3:
            hints.append("Highly lipophilic -> favors lipid core loading (SLN/NLC/nanoemulsion, bilayer).")
        elif logp < 0:
            hints.append("Hydrophilic -> passive lipid entrapment is low; consider aqueous core, "
                         "complexation, or active loading.")
    if card.category == "biologic":
        hints.append("Biologic/nucleic-acid payload -> full delivery-chain design required "
                     "(protection, uptake, endosomal escape, unpacking).")
    prof["formulation_hints"] = hints
    return prof


def route_warnings(route: str, family: str) -> List[str]:
    out = []
    if route == "parenteral":
        out.append("Parenteral: sterility, endotoxin, isotonicity, and hemocompatibility are mandatory CQAs.")
        out.append("Prefer GRAS/class-3 solvents; avoid cationic surfaces unless justified.")
    if route == "pulmonary":
        out.append("Pulmonary: aerodynamic size (~1-5 um), device compatibility, and lung tolerability matter more than DLS size.")
        out.append("Add a dispersibility aid (leucine) and verify post-nebulization integrity.")
    if route == "ocular":
        out.append("Ocular: sterility, comfort/tonicity, and short residence time — consider mucoadhesion.")
    if route == "oral" and family in ("liposome", "niosome"):
        out.append("Oral vesicles face bile/enzymatic destabilization — bilosomes or coatings may be needed.")
    if route in ("topical", "transdermal") and family not in ("transfersome", "ethosome", "nanoemulsion", "solid_lipid_nanoparticle", "nanostructured_lipid_carrier"):
        out.append("For skin delivery, deformable/penetration-enhancing systems usually outperform rigid vesicles.")
    return out


def generate_candidates(drug: str, route: str, family: str, goal: str = "balanced",
                        drug_mol_percent: float = 5.0, solvent: Optional[str] = None,
                        carrier: Optional[str] = None, db: Optional[Database] = None) -> List[DesignInput]:
    db = db or get_database()
    templates = FAMILY_TEMPLATES.get(family, [])
    cands = []
    for i, t in enumerate(templates):
        # Keep only components that resolve; note fallbacks.
        comps = [(n, r, m) for (n, r, m) in t["components"] if db.card(n) is not None]
        if not comps:
            continue
        default_solvent = solvent or ("Ethanol" if family in ("ethosome", "liposome", "niosome") else "Ethanol")
        cands.append(DesignInput(
            family=family, route=route, process_method=t["process"], design_goal=goal,
            drug=drug, drug_mol_percent=drug_mol_percent, solvent=default_solvent,
            carrier=carrier or "", total_membrane_umol=200.0,
            components=comps, formulation_id=f"{family}_cand_{i+1}",
        ))
    return cands


def run_wizard(drug: str, route: str, family: str, goal: str = "balanced",
               drug_mol_percent: float = 5.0, db: Optional[Database] = None) -> WizardOutput:
    db = db or get_database()
    return WizardOutput(
        payload_profile=payload_profile(drug, db),
        suggested_classes=SUGGESTED_CLASSES.get(family, []),
        suggested_categories=SUGGESTED_CLASSES.get(family, []),
        route_warnings=route_warnings(route, family),
        candidates=generate_candidates(drug, route, family, goal, drug_mol_percent, db=db),
    )
