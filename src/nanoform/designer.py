from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import equations as eq
from .carrier_recommender import recommend_carriers
from .database import Database, MaterialCard, get_database
from .descriptors import Component, DescriptorResult, compute_descriptors


@dataclass
class DesignInput:
    family: str = "niosome"
    route: str = "topical"
    process_method: str = "thin-film hydration"
    design_goal: str = "balanced"
    drug: Optional[str] = None
    drug_mol_percent: float = 5.0
    pH: float = 7.4
    temperature_C: float = 25.0
    solvent: Optional[str] = None
    carrier: Optional[str] = None
    total_membrane_umol: float = 200.0
    components: List[Tuple[str, str, float]] = field(default_factory=list)
    formulation_id: str = "design-001"


@dataclass
class CQA:
    key: str
    label: str
    estimate: str
    score: float
    drivers: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)


@dataclass
class DesignResult:
    inp: DesignInput
    components: List[Component]
    drug_card: Optional[MaterialCard]
    solvent_card: Optional[MaterialCard]
    descriptors: DescriptorResult
    cqas: List[CQA]
    batch_table: List[Dict[str, Any]]
    maturity_level: int
    maturity_label: str
    executive_decision: str
    nanoform_score: float
    missing_values: List[str] = field(default_factory=list)

    def cqa(self, key: str) -> Optional[CQA]:
        return next((c for c in self.cqas if c.key == key), None)


MATURITY = {
    0: "DML-0: no coherent design",
    1: "DML-1: descriptor-only / missing constants (heuristic)",
    2: "DML-2: descriptor-supported rational design",
    3: "DML-3: trained on internal outcomes (not yet available)",
    4: "DML-4: prospectively validated (not yet available)",
}


def design(inp: DesignInput, db: Optional[Database] = None) -> DesignResult:
    db = db or get_database()
    comps: List[Component] = []
    missing_materials: List[str] = []

    for name, role, molp in inp.components:
        card = db.card(name)
        if card is None:
            missing_materials.append(name)
            continue
        comps.append(Component(card=card, role=role, mol_percent=float(molp)))

    drug_card = db.card(inp.drug) if inp.drug else None
    solvent_card = db.card(inp.solvent) if inp.solvent else None

    desc = compute_descriptors(
        comps,
        drug=drug_card,
        drug_mol_percent=inp.drug_mol_percent,
        solvent=solvent_card,
        pH=inp.pH,
        temperature_C=inp.temperature_C,
    )
    if inp.drug and drug_card is None:
        missing_materials.append(inp.drug)
    if inp.solvent and solvent_card is None:
        missing_materials.append(inp.solvent)

    cqas = _estimate_cqas(inp, comps, drug_card, solvent_card, desc, db)
    nano = next(c.score for c in cqas if c.key == "nanoform_score")
    batch = _batch_table(inp, comps, drug_card)
    missing = list(desc.missing)
    if missing_materials:
        missing.append("Unresolved materials: " + ", ".join(sorted(set(missing_materials))))
    level, label = _maturity(desc, comps, missing)
    decision = _executive_decision(nano, missing, comps)

    return DesignResult(
        inp=inp,
        components=comps,
        drug_card=drug_card,
        solvent_card=solvent_card,
        descriptors=desc,
        cqas=cqas,
        batch_table=batch,
        maturity_level=level,
        maturity_label=label,
        executive_decision=decision,
        nanoform_score=nano,
        missing_values=missing,
    )


def _estimate_cqas(inp, comps, drug, solvent, desc, db) -> List[CQA]:
    v = desc.values
    cqas: List[CQA] = []

    ee_score, ee_dr, ee_rk = 0.5, [], []
    logp = drug.get("logP") if drug else None
    if isinstance(logp, (int, float)):
        if logp >= 2:
            ee_score += 0.2
            ee_dr.append(f"Lipophilic drug (logP {logp:.1f}) partitions into carrier")
        elif logp < 0:
            ee_score -= 0.2
            ee_rk.append(f"Hydrophilic drug (logP {logp:.1f}); low passive lipid entrapment")
    red = v.get("drug_bilayer_red")
    if isinstance(red, (int, float)):
        if red < 1:
            ee_score += 0.15
            ee_dr.append(f"Drug-bilayer RED {red:.2f} < 1 (compatible)")
        else:
            ee_score -= 0.1
            ee_rk.append(f"Drug-bilayer RED {red:.2f} > 1 (limited compatibility)")
    rig = v.get("rigidity_score")
    if isinstance(rig, (int, float)):
        ee_score += 0.1 * (rig - 0.5) * 2
        if rig > 0.6:
            ee_dr.append("Rigid membrane reduces leakage/expulsion")
    ee_score = eq.clamp(ee_score)
    cqas.append(CQA("encapsulation_efficiency", "Encapsulation efficiency", _band(ee_score, ("low", "moderate", "high")), ee_score, ee_dr, ee_rk))

    ps_score, ps_dr, ps_rk = 0.5, [], []
    high_hlb = v.get("high_hlb_fraction", 0)
    peg = v.get("pegylated_fraction", 0)
    proc = inp.process_method.lower()
    if any(k in proc for k in ("microfluid", "high-pressure", "homogen", "sonicat", "extrus")):
        ps_score += 0.2
        ps_dr.append("High-energy process favors smaller particles")
    if any(k in proc for k in ("hydration", "hand-shaken", "vortex")):
        ps_score -= 0.15
        ps_rk.append("Low-energy hydration tends to larger vesicles (needs size reduction)")
    ps_score += 0.2 * high_hlb + 0.15 * peg
    if peg > 0:
        ps_dr.append("PEGylation adds steric stabilization")
    ps_score = eq.clamp(ps_score)
    cqas.append(CQA("particle_size", "Particle size tendency", _band(ps_score, ("large", "moderate", "small")), ps_score, ps_dr, ps_rk))

    pdi_score, pdi_dr, pdi_rk = 0.55, [], []
    n_struct = len([c for c in comps if c.role not in ("drug",)])
    if n_struct <= 3:
        pdi_score += 0.15
        pdi_dr.append("Few components -> simpler self-assembly")
    if n_struct >= 5:
        pdi_score -= 0.15
        pdi_rk.append("Many components can broaden the distribution")
    if high_hlb + peg > 0.05:
        pdi_score += 0.1
        pdi_dr.append("Adequate stabilizer present")
    pdi_score = eq.clamp(pdi_score)
    cqas.append(CQA("pdi", "PDI (uniformity) tendency", _band(pdi_score, ("broad", "moderate", "narrow")), pdi_score, pdi_dr, pdi_rk))

    zt_score, zt_dr, zt_rk = 0.4, [], []
    charged = v.get("charged_component_fraction", 0)
    sign = _charge_sign(comps)
    if charged > 0.02:
        zt_score += 0.4
        zt_dr.append(f"{'Anionic' if sign < 0 else 'Cationic' if sign > 0 else 'Charged'} inducer ({charged*100:.0f} mol%) raises |zeta|")
    else:
        zt_rk.append("No charge inducer -> low |zeta|; rely on steric stabilization")
    if peg > 0:
        zt_dr.append("PEG shields surface charge (steric, not electrostatic, stabilization)")
    if sign > 0:
        zt_rk.append("Cationic surface needs cytocompatibility justification")
    zt_score = eq.clamp(zt_score)
    cqas.append(CQA("zeta_potential", "Zeta-potential tendency", _zeta_label(zt_score, sign), zt_score, zt_dr, zt_rk))

    dl = inp.drug_mol_percent
    dl_score = eq.clamp(1.0 - abs(dl - 8) / 20) if dl <= 25 else 0.3
    dl_dr, dl_rk = [], []
    if dl > 15:
        dl_rk.append(f"High drug mol% ({dl:.0f}%) risks expulsion/crystallization on storage")
    else:
        dl_dr.append(f"Drug mol% ({dl:.0f}%) within a typical starting window")
    cqas.append(CQA("drug_loading", "Drug loading", f"{dl:.1f} mol% of membrane", dl_score, dl_dr, dl_rk))

    rel_score, rel_dr, rel_rk = 0.5, [], []
    if isinstance(rig, (int, float)):
        if rig > 0.6:
            rel_score += 0.2
            rel_dr.append("Rigid/ordered membrane -> slower, sustained release")
        elif rig < 0.4:
            rel_score -= 0.1
            rel_rk.append("Fluid membrane -> faster release / burst risk")
    if v.get("edge_activator_fraction", 0) > 0.1:
        rel_rk.append("High edge-activator content increases permeability/leakage")
    rel_score = eq.clamp(rel_score)
    cqas.append(CQA("release_tendency", "Release control tendency", _band(rel_score, ("burst-prone", "moderate", "sustained")), rel_score, rel_dr, rel_rk))

    cr_score, cr_dr, cr_rk = 0.6, [], []
    if inp.family in ("solid_lipid_nanoparticle",):
        cr_score -= 0.2
        cr_rk.append("SLN with pure solid lipid: perfect crystal lattice can expel drug")
        if not any(c.card.material_type == "liquid_lipid" for c in comps):
            cr_rk.append("No liquid lipid present - consider NLC (add oil) to lower crystallinity")
    if inp.family == "nanostructured_lipid_carrier" and any(c.card.material_type == "liquid_lipid" for c in comps):
        cr_score += 0.2
        cr_dr.append("Liquid-lipid domain disrupts crystallinity (NLC advantage)")
    highmelt = [c for c in comps if isinstance(c.card.get("melting_point_C"), (int, float)) and c.card.get("melting_point_C") > 65]
    if highmelt:
        cr_rk.append("High-melting lipid(s) present: " + ", ".join(c.name for c in highmelt))
    cr_score = eq.clamp(cr_score)
    cqas.append(CQA("crystallization_risk", "Crystallization / expulsion risk", _band(cr_score, ("high risk", "moderate", "low risk")), cr_score, cr_dr, cr_rk))

    sv_score, sv_dr, sv_rk = 0.5, [], []
    sred = v.get("drug_solvent_red")
    if isinstance(sred, (int, float)):
        sv_score = eq.red_affinity_score(sred)
        (sv_dr if sred < 1 else sv_rk).append(f"Drug-solvent RED {sred:.2f} ({'inside' if sred < 1 else 'outside'} solubility sphere)")
    elif solvent is None:
        sv_rk.append("No solvent selected")
    else:
        sv_rk.append("Drug or solvent HSP missing -> suitability uncertain")
    if solvent is not None and str(solvent.get("ICH_class")) in ("1", "2"):
        sv_rk.append(f"{solvent.name}: ICH class {solvent.get('ICH_class')} residual limits apply")
    cqas.append(CQA("solvent_suitability", "Solvent suitability", _band(sv_score, ("poor", "moderate", "good")), sv_score, sv_dr, sv_rk))

    ca_score, ca_dr, ca_rk = 0.5, [], []
    carrier_card = db.card(inp.carrier) if inp.carrier else None
    if inp.carrier and carrier_card is not None:
        recs = recommend_carriers(inp.route, inp.family, inp.process_method, db=db, top_n=50)
        cname = carrier_card.name.lower()
        match = next((r for r in recs if r["carrier"].lower() == cname), None)
        if match:
            ca_score = match["score"]
            (ca_dr if ca_score >= 0.5 else ca_rk).append(f"{match['carrier']} rational-fit score {ca_score:.2f} for {inp.route}/{inp.process_method}")
            if match["warnings"]:
                ca_rk.append(match["warnings"])
        else:
            ca_rk.append("Selected carrier not found in carrier table")
    elif inp.carrier:
        ca_rk.append(f"Carrier '{inp.carrier}' not resolved in database")
        ca_score = 0.4
    else:
        ca_dr.append("No carrier/cryoprotectant selected (may be fine for liquid dispersions)")
        ca_score = 0.55
    cqas.append(CQA("carrier_suitability", "Carrier / cryoprotectant suitability", _band(ca_score, ("poor", "moderate", "good")), ca_score, ca_dr, ca_rk))

    weights = _goal_weights(inp.design_goal)
    total = sum(weights.get(c.key, 0.1) * c.score for c in cqas)
    wsum = sum(weights.get(c.key, 0.1) for c in cqas)
    nano = eq.clamp(total / wsum if wsum else 0.5)
    cqas.append(CQA("nanoform_score", "NanoForm composite score", f"{nano:.2f} / 1.00", nano, [f"Weighted by design goal '{inp.design_goal}'"], []))
    return cqas


def _goal_weights(goal: str) -> Dict[str, float]:
    base = {
        "encapsulation_efficiency": 0.2,
        "particle_size": 0.15,
        "pdi": 0.1,
        "zeta_potential": 0.1,
        "drug_loading": 0.1,
        "release_tendency": 0.1,
        "crystallization_risk": 0.1,
        "solvent_suitability": 0.1,
        "carrier_suitability": 0.05,
    }
    overrides = {
        "high_EE": {"encapsulation_efficiency": 0.35, "drug_loading": 0.15},
        "small_size": {"particle_size": 0.35, "pdi": 0.2},
        "low_PDI": {"pdi": 0.35, "particle_size": 0.2},
        "pulmonary": {"particle_size": 0.25, "carrier_suitability": 0.2, "crystallization_risk": 0.15},
        "stability": {"crystallization_risk": 0.25, "zeta_potential": 0.2, "release_tendency": 0.1},
        "sustained_release": {"release_tendency": 0.35, "crystallization_risk": 0.15},
        "transdermal_deformable": {"release_tendency": 0.2, "particle_size": 0.2},
        "oral_bilosome": {"encapsulation_efficiency": 0.25, "crystallization_risk": 0.15},
        "parenteral_cautious": {"zeta_potential": 0.15, "pdi": 0.2, "solvent_suitability": 0.2},
    }
    weights = dict(base)
    weights.update(overrides.get(goal, {}))
    return weights


def _batch_table(inp, comps, drug) -> List[Dict[str, Any]]:
    rows = []
    for c in comps:
        umol = inp.total_membrane_umol * c.mol_percent / 100.0
        mw = c.card.get("MW") or c.card.get("avg_MW")
        mg = eq.mg_from_umol(umol, mw) if isinstance(mw, (int, float)) else None
        rows.append({"component": c.name, "role": c.role, "mol_percent": c.mol_percent, "umol": round(umol, 3), "MW": mw, "mg": round(mg, 3) if mg is not None else None})
    if drug is not None:
        umol = inp.total_membrane_umol * inp.drug_mol_percent / 100.0
        mw = drug.get("MW")
        mg = eq.mg_from_umol(umol, mw) if isinstance(mw, (int, float)) else None
        rows.append({"component": drug.name, "role": "drug", "mol_percent": inp.drug_mol_percent, "umol": round(umol, 3), "MW": mw, "mg": round(mg, 3) if mg is not None else None})
    return rows


def _maturity(desc, comps, missing) -> Tuple[int, str]:
    if not comps:
        return 0, MATURITY[0]
    critical_missing = [m for m in missing if "HSP" in m or "MW" in m or "CPP" in m]
    level = 1 if critical_missing else 2
    return level, MATURITY[level]


def _executive_decision(nano, missing, comps) -> str:
    if not comps:
        return "Exploratory only - no valid components resolved."
    critical = any(("MW" in m or "Unresolved materials" in m) for m in missing)
    if critical:
        return "Revise before lab - critical constants/materials missing."
    if nano >= 0.7:
        return "Good candidate for a first lab screen (descriptor-supported)."
    if nano >= 0.55:
        return "Screen as a comparator arm alongside a stronger candidate."
    if nano >= 0.4:
        return "Revise before lab - several descriptors are unfavorable."
    return "Exploratory only - weak descriptor profile."


def _band(score: float, labels: Tuple[str, str, str]) -> str:
    if score < 0.4:
        return labels[0]
    if score < 0.66:
        return labels[1]
    return labels[2]


def _charge_sign(comps) -> int:
    charge = 0.0
    for c in comps:
        if c.card.get("charge_inducer"):
            q = c.card.get("formal_charge")
            if isinstance(q, (int, float)):
                charge += q * c.mol_percent
    return 1 if charge > 0 else -1 if charge < 0 else 0


def _zeta_label(score, sign):
    mag = _band(score, ("low |zeta|", "moderate |zeta|", "high |zeta|"))
    if score < 0.4:
        return mag
    return f"{mag} ({'negative' if sign < 0 else 'positive' if sign > 0 else 'sign undetermined'})"
