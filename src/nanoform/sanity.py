"""Formulation sanity checks.

Generates route/family/composition warnings from a DesignResult. Each warning
has a severity: 'error' (incoherent/unsafe logic), 'warn' (likely problem),
'info' (worth noting). These are rule-based and conservative; they flag issues,
they do not certify a formulation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .designer import DesignResult


@dataclass
class Warning:
    severity: str   # error | warn | info
    message: str


def run_sanity(result: DesignResult) -> List[Warning]:
    w: List[Warning] = []
    inp = result.inp
    comps = result.components
    v = result.descriptors.values

    # ---- Composition integrity ------------------------------------------- #
    molsum = sum(c.mol_percent for c in comps)
    if comps and abs(molsum - 100.0) > 1.0:
        w.append(Warning("warn", f"Component mol% sums to {molsum:.1f}, not 100. "
                                 "Batch fractions are normalized but check intent."))
    if not comps:
        w.append(Warning("error", "No membrane/matrix components — nothing to design."))
        return w

    has_surf = any(c.card.material_type in ("nonionic_surfactant", "ionic_surfactant") for c in comps)
    has_lipid = any(c.card.material_type in ("phospholipid", "solid_lipid", "liquid_lipid") for c in comps)
    has_polymer = any(c.card.material_type == "polymer" for c in comps)

    # ---- Family-specific logic ------------------------------------------- #
    fam = inp.family
    if fam in ("niosome", "proniosome") and not has_surf:
        w.append(Warning("error", "Niosomes require a vesicle-forming nonionic surfactant."))
    if fam in ("liposome",) and not any(c.card.material_type == "phospholipid" for c in comps):
        w.append(Warning("error", "Liposomes require a phospholipid."))
    if fam in ("transfersome",) and v.get("edge_activator_fraction", 0) < 0.05:
        w.append(Warning("warn", "Transfersomes need an edge activator (e.g. Tween 80, sodium cholate) "
                                 "for deformability — none/low detected."))
    if fam in ("ethosome",) and (inp.solvent is None or "ethanol" not in str(inp.solvent).lower()):
        w.append(Warning("warn", "Ethosomes rely on a high ethanol content — ethanol not selected as solvent."))
    if fam in ("bilosome",) and v.get("bile_salt_fraction", 0) < 0.02:
        w.append(Warning("warn", "Bilosomes require a bile salt — none detected in components."))
    if fam in ("solid_lipid_nanoparticle", "nanostructured_lipid_carrier", "nanoemulsion") and not has_lipid:
        w.append(Warning("error", f"{fam} requires a lipid/oil matrix."))
    if fam in ("solid_lipid_nanoparticle", "nanostructured_lipid_carrier", "nanoemulsion") and not has_surf:
        w.append(Warning("warn", "Lipid nanoparticles/emulsions need a surfactant/stabilizer to prevent coalescence."))
    if fam in ("polymeric_nanoparticle", "lipid_polymer_hybrid") and not has_polymer:
        w.append(Warning("error", f"{fam} requires a polymer."))
    if fam == "lipid_nanoparticle" and v.get("ionizable_fraction", 0) < 0.1 and _is_nucleic(result):
        w.append(Warning("warn", "Nucleic-acid LNPs typically need ~40-50 mol% ionizable lipid for "
                                 "encapsulation and endosomal escape."))

    # ---- Sterol content -------------------------------------------------- #
    # Cholesterol is a sterol material_type, so sterol_fraction already includes
    # it; take the max (never the sum) to avoid double-counting.
    chol = max(v.get("cholesterol_fraction", 0), v.get("sterol_fraction", 0))
    if chol > 0.55:
        w.append(Warning("warn", f"Sterol fraction {chol*100:.0f} mol% is high — may destabilize the "
                                 "bilayer / phase-separate above ~50 mol%."))

    # ---- Route-specific safety ------------------------------------------- #
    route = inp.route
    if route == "parenteral":
        if _has_flag(comps, "cationic"):
            w.append(Warning("warn", "Cationic components on an IV product: opsonization, hemolysis and "
                                     "cytotoxicity risk — justify and characterize."))
        if any(str(c.card.safety_notes).lower().find("cytotox") >= 0 for c in comps):
            w.append(Warning("info", "One or more components carry cytotoxicity notes — review for parenteral use."))
    if route == "pulmonary":
        if result.solvent_card is not None and str(result.solvent_card.get("ICH_class")) in ("1", "2"):
            w.append(Warning("warn", f"Solvent {result.solvent_card.name} is ICH class "
                                     f"{result.solvent_card.get('ICH_class')} — tighten residual limits for inhalation."))
        if not inp.carrier:
            w.append(Warning("info", "Pulmonary dry powders usually need a carrier / dispersibility aid (e.g. leucine, lactose)."))

    # ---- Drug loading ---------------------------------------------------- #
    if inp.drug_mol_percent > 20:
        w.append(Warning("warn", f"Drug loading {inp.drug_mol_percent:.0f} mol% is aggressive — "
                                 "expulsion/precipitation on storage is likely."))

    # ---- Toxicity flags -------------------------------------------------- #
    for c in comps:
        tox = c.card.get("toxicity_penalty")
        if isinstance(tox, (int, float)) and tox >= 0.4:
            w.append(Warning("warn", f"{c.name} carries a high toxicity flag — research-grade / justify for the route."))

    if not w:
        w.append(Warning("info", "No rule-based red flags. Outputs still require laboratory verification."))
    return w


def _has_flag(comps, flag) -> bool:
    return any(c.card.get(flag) for c in comps)


def _is_nucleic(result: DesignResult) -> bool:
    if result.drug_card is None:
        return False
    return "nucleic" in str(result.drug_card.identity.get("subcategory", "")).lower() \
        or result.drug_card.category == "biologic"
