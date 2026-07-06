"""Explainability layer.

Turns descriptor-driven CQA scores into human-readable interpretation and
concrete improvement suggestions. Every statement is tied to a claim category so
the report generator can label grounding:

    database-backed | calculator-backed | source-backed | heuristic | unsupported

This module never invents constants; it reasons only over DesignResult contents.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .designer import CQA, DesignResult


@dataclass
class Explanation:
    cqa_key: str
    positive_drivers: List[str]
    risk_drivers: List[str]
    interpretation: str
    recommended_change: str
    claim_category: str = "calculator-backed"


def explain_cqa(cqa: CQA) -> Explanation:
    interp = _interpretation(cqa)
    change = _recommended_change(cqa)
    return Explanation(
        cqa_key=cqa.key,
        positive_drivers=cqa.drivers,
        risk_drivers=cqa.risks,
        interpretation=interp,
        recommended_change=change,
        claim_category="heuristic" if cqa.key in ("particle_size", "pdi") else "calculator-backed",
    )


def explain_all(result: DesignResult) -> List[Explanation]:
    return [explain_cqa(c) for c in result.cqas if c.key != "nanoform_score"]


def _interpretation(cqa: CQA) -> str:
    band = "favorable" if cqa.score >= 0.66 else "borderline" if cqa.score >= 0.4 else "unfavorable"
    return f"{cqa.label}: estimated '{cqa.estimate}' ({band}, score {cqa.score:.2f}). " \
           "Descriptor-driven estimate; requires laboratory verification."


def _recommended_change(cqa: CQA) -> str:
    if cqa.score >= 0.66:
        return "Retain current choice for this attribute."
    table = {
        "encapsulation_efficiency": "Increase membrane rigidity (add cholesterol / higher-Tm lipid) or "
                                    "improve drug-carrier HSP match; consider active/remote loading for ionizable drugs.",
        "particle_size": "Apply higher-energy processing (sonication, microfluidization, HPH) or increase "
                         "high-HLB stabilizer / PEG-lipid fraction.",
        "pdi": "Reduce the number of components, ensure sufficient stabilizer, and add a size-reduction step.",
        "zeta_potential": "Add a charge inducer (dicetyl phosphate for negative; stearylamine/DOTAP for positive) "
                          "or rely on documented steric stabilization if PEGylated.",
        "drug_loading": "Reduce drug mol% toward 5-10% to limit expulsion, or switch to a higher-capacity carrier (NLC).",
        "release_tendency": "For sustained release increase rigidity/Tm and reduce edge activator; for faster "
                            "release do the opposite.",
        "crystallization_risk": "Convert SLN to NLC by adding a liquid lipid (e.g. oleic acid, MCT) to disrupt "
                               "the crystal lattice; avoid highly ordered pure triglycerides.",
        "solvent_suitability": "Choose a solvent (or binary blend) with lower drug RED from the Solvent Recommender; "
                              "respect ICH residual-solvent class for the route.",
        "carrier_suitability": "Pick a higher-ranked carrier/cryoprotectant from the Carrier Recommender for this "
                             "route/process (e.g. trehalose for lyophilization, leucine for DPI).",
    }
    return table.get(cqa.key, "Revisit the drivers above before lab work.")


def improvement_suggestions(result: DesignResult) -> List[str]:
    """Prioritized, concrete suggestions across the whole design."""
    out: List[str] = []
    v = result.descriptors.values
    inp = result.inp

    weakest = sorted((c for c in result.cqas if c.key != "nanoform_score"),
                     key=lambda c: c.score)[:3]
    for c in weakest:
        if c.score < 0.66:
            out.append(f"[{c.label}] {_recommended_change(c)}")

    if inp.drug_mol_percent > 12:
        out.append("Reduce drug mol% to a 5-10% starting window to limit expulsion.")
    # Cholesterol is a sterol type; sterol_fraction already includes it -> max, not sum.
    chol = max(v.get("cholesterol_fraction", 0), v.get("sterol_fraction", 0))
    if chol > 0.5:
        out.append("Reduce sterol below ~50 mol% to avoid phase separation.")
    if v.get("high_hlb_fraction", 0) > 0.4:
        out.append("Excess high-HLB surfactant favors micelles over vesicles; reduce or rebalance with a low-HLB anchor.")
    if v.get("micellization_risk", 0) > 0.5:
        out.append("High micellization risk: lower high-HLB fraction or raise the low-HLB / cholesterol content.")
    if result.solvent_card is not None and str(result.solvent_card.get("ICH_class")) in ("1", "2"):
        out.append(f"Swap {result.solvent_card.name} (ICH class {result.solvent_card.get('ICH_class')}) "
                   "for a class-3/GRAS solvent where possible.")
    if not any(c.card.get("charge_inducer") for c in result.components) and v.get("pegylated_fraction", 0) == 0:
        out.append("Add electrostatic (charge inducer) or steric (PEG-lipid) stabilization for colloidal stability.")

    # De-duplicate while preserving order.
    seen = set()
    uniq = []
    for s in out:
        if s not in seen:
            uniq.append(s); seen.add(s)
    return uniq


def claim_categories(result: DesignResult) -> Dict[str, str]:
    """Map each descriptor to how it is grounded (for the limitations section)."""
    cats = {}
    v = result.descriptors.values
    for key in v:
        if key in ("mixed_hlb", "cpp_estimate", "drug_bilayer_red", "drug_solvent_red",
                   "drug_excipient_chi", "drug_neutral_fraction", "drug_ionized_fraction"):
            cats[key] = "calculator-backed"
        elif key in ("rigidity_score", "fluidity_score", "micellization_risk", "morphology_tendency"):
            cats[key] = "heuristic"
        else:
            cats[key] = "database-backed"
    return cats
