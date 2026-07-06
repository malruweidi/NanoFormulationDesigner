"""Formulation descriptor engine.

Turns a resolved component list (material cards + mol%) plus a drug, solvent and
process context into a descriptor row. Every descriptor is computed from
database-backed constants via the deterministic kernels in `equations.py`.

Descriptors are intermediate quantities; heuristic CQA estimates are derived
from them in `designer.py`. Missing constants are surfaced (never silently
guessed): each descriptor call records the properties it could not find.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import equations as eq
from .database import MaterialCard

# Representative acyl-bilayer HSP used only when a lipid's own HSP is unknown.
# (Approximate, heuristic - flagged wherever it drives an output.)
BILAYER_HSP = (17.0, 4.0, 6.0)


@dataclass
class Component:
    """A formulation component: a resolved material card + role + mol%."""

    card: MaterialCard
    role: str
    mol_percent: float

    @property
    def name(self) -> str:
        return self.card.name


@dataclass
class DescriptorResult:
    values: Dict[str, Any] = field(default_factory=dict)
    missing: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def __getitem__(self, k):
        return self.values.get(k)


def _mass_weights(components: List[Component]) -> List[float]:
    """Relative masses = mol% * MW (MW missing -> 0 weight)."""
    out = []
    for c in components:
        mw = c.card.get("MW") or c.card.get("avg_MW")
        out.append((c.mol_percent * mw) if isinstance(mw, (int, float)) else 0.0)
    return out


def _frac_by_flag(components: List[Component], flag: str) -> float:
    """Mol fraction of components carrying a truthy flag property."""
    tot = sum(c.mol_percent for c in components) or 1.0
    hit = sum(c.mol_percent for c in components if c.card.get(flag))
    return hit / tot


def _frac_by_type(components: List[Component], mtype: str) -> float:
    tot = sum(c.mol_percent for c in components) or 1.0
    hit = sum(c.mol_percent for c in components if c.card.material_type == mtype)
    return hit / tot


def compute_descriptors(
    components: List[Component],
    drug: Optional[MaterialCard] = None,
    drug_mol_percent: float = 0.0,
    solvent: Optional[MaterialCard] = None,
    pH: float = 7.4,
    temperature_C: float = 25.0,
) -> DescriptorResult:
    res = DescriptorResult()
    v = res.values
    if not components:
        res.notes.append("No membrane/matrix components supplied.")
        return res

    # ---- Mixed HLB (mass-weighted over components that have HLB) ---------- #
    hlbs = [c.card.get("HLB") for c in components]
    weights = _mass_weights(components)
    hlb_pairs = [(w, h) for w, h in zip(weights, hlbs) if isinstance(h, (int, float))]
    if hlb_pairs:
        v["mixed_hlb"] = eq.mixed_hlb([w for w, _ in hlb_pairs], [h for _, h in hlb_pairs])
    else:
        v["mixed_hlb"] = None
        res.missing.append("HLB (no component with a defined HLB)")

    # ---- Composition fractions ------------------------------------------- #
    surf = [c for c in components if isinstance(c.card.get("HLB"), (int, float))]
    tot = sum(c.mol_percent for c in components) or 1.0
    v["high_hlb_fraction"] = sum(
        c.mol_percent for c in surf if (c.card.get("HLB") or 0) >= 10) / tot
    v["low_hlb_fraction"] = sum(
        c.mol_percent for c in surf if (c.card.get("HLB") or 0) < 10) / tot
    v["cholesterol_fraction"] = sum(
        c.mol_percent for c in components if c.name.lower().startswith("cholesterol")) / tot
    v["sterol_fraction"] = _frac_by_type(components, "sterol")
    v["bile_salt_fraction"] = _frac_by_type(components, "bile_salt")
    v["pegylated_fraction"] = _frac_by_flag(components, "pegylated")
    v["charged_component_fraction"] = _frac_by_flag(components, "charge_inducer")
    v["ionizable_fraction"] = _frac_by_flag(components, "ionizable")
    v["edge_activator_fraction"] = _frac_by_flag(components, "edge_activator")

    # ---- Chain / thermotropic descriptors -------------------------------- #
    ncs, unsats, tms, cmols = [], [], [], []
    for c in components:
        nc = c.card.get("tail_carbons")
        un = c.card.get("tail_unsaturation")
        tm = c.card.get("Tm_C")
        if tm is None:
            tm = c.card.get("melting_point_C")
        if isinstance(nc, (int, float)) and nc > 0:
            ncs.append(nc); cmols.append(c.mol_percent)
        if isinstance(un, (int, float)):
            unsats.append((un, c.mol_percent))
        if isinstance(tm, (int, float)):
            tms.append((tm, c.mol_percent))
    v["avg_chain_length"] = eq.weighted_mean(ncs, cmols) if ncs else None
    v["unsaturation_fraction"] = (
        eq.weighted_mean([u for u, _ in unsats], [w for _, w in unsats]) if unsats else None)
    v["avg_transition_temperature"] = (
        eq.weighted_mean([t for t, _ in tms], [w for _, w in tms]) if tms else None)

    # ---- CPP (packing) estimate ------------------------------------------ #
    cpps, cpp_w = [], []
    cpp_missing = False
    for c in components:
        nc = c.card.get("tail_carbons")
        a0 = c.card.get("headgroup_area_nm2")
        ntails = c.card.get("n_tails") or 1
        if not (isinstance(nc, (int, float)) and nc > 0 and isinstance(a0, (int, float)) and a0 > 0):
            if c.card.material_type in ("nonionic_surfactant", "phospholipid", "ionic_surfactant"):
                cpp_missing = True
            continue
        vol = eq.tanford_v_nm3(nc, int(ntails))
        lc = eq.tanford_l_nm(nc)
        cpps.append(eq.cpp_value(vol, a0, lc))
        cpp_w.append(c.mol_percent)
    if cpps:
        cpp = eq.weighted_mean(cpps, cpp_w)
        v["cpp_estimate"] = cpp
        v["morphology_tendency"] = eq.cpp_class(cpp)
    else:
        v["cpp_estimate"] = None
        v["morphology_tendency"] = None
        res.missing.append("CPP (need tail_carbons + headgroup_area_nm2)")
    if cpp_missing:
        res.notes.append("Some surfactants lacked headgroup_area_nm2; CPP is partial.")

    # ---- Rigidity / fluidity --------------------------------------------- #
    # Rigidity rises with Tm, cholesterol content, saturation; falls with
    # unsaturation and edge activators. Score in [0,1], heuristic.
    tm = v["avg_transition_temperature"]
    chol = v["cholesterol_fraction"]
    unsat = v["unsaturation_fraction"] or 0.0
    rigidity = 0.0
    parts = 0
    if tm is not None:
        rigidity += eq.normalize_score(tm, -20, 70); parts += 1
    rigidity += chol; parts += 1
    rigidity += eq.clamp(1.0 - unsat / 2.0); parts += 1
    rigidity = rigidity / parts if parts else None
    if rigidity is not None:
        rigidity = eq.clamp(rigidity - 0.3 * v["edge_activator_fraction"])
    v["rigidity_score"] = rigidity
    v["fluidity_score"] = (1.0 - rigidity) if rigidity is not None else None

    # ---- Micellization risk ---------------------------------------------- #
    cpp = v.get("cpp_estimate")
    mic = 0.5 * v["high_hlb_fraction"]
    if cpp is not None and cpp < 0.5:
        mic += 0.5 * eq.normalize_score(0.5 - cpp, 0, 0.5)
    v["micellization_risk"] = eq.clamp(mic)

    # ---- Drug-bilayer Hansen RED ----------------------------------------- #
    if drug is not None:
        dD, dP, dH = drug.get("delta_D"), drug.get("delta_P"), drug.get("delta_H")
        R0 = drug.get("hsp_radius")
        if all(isinstance(x, (int, float)) for x in (dD, dP, dH)):
            bD, bP, bH = _bilayer_hsp(components, res)
            Ra = eq.hansen_distance(dD, dP, dH, bD, bP, bH)
            r0 = R0 if isinstance(R0, (int, float)) and R0 > 0 else 8.0
            v["drug_bilayer_red"] = eq.red_score(Ra, r0)
            if not (isinstance(R0, (int, float)) and R0 > 0):
                res.notes.append("Drug hsp_radius missing; used default R0=8 (heuristic).")
        else:
            v["drug_bilayer_red"] = None
            res.missing.append("Drug HSP (delta_D/P/H) for bilayer RED")

        # ---- Drug-solvent RED -------------------------------------------- #
        if solvent is not None and all(isinstance(x, (int, float)) for x in (dD, dP, dH)):
            sD, sP, sH = solvent.get("delta_D"), solvent.get("delta_P"), solvent.get("delta_H")
            if all(isinstance(x, (int, float)) for x in (sD, sP, sH)):
                Ra = eq.hansen_distance(dD, dP, dH, sD, sP, sH)
                r0 = R0 if isinstance(R0, (int, float)) and R0 > 0 else 8.0
                v["drug_solvent_red"] = eq.red_score(Ra, r0)
            else:
                v["drug_solvent_red"] = None
                res.missing.append("Solvent HSP for drug-solvent RED")

        # ---- Drug-excipient Flory-Huggins chi ---------------------------- #
        matrix = _dominant_matrix(components)
        if matrix is not None and all(isinstance(x, (int, float)) for x in (dD, dP, dH)):
            mD, mP, mH = _card_hsp(matrix.card)
            if all(isinstance(x, (int, float)) for x in (mD, mP, mH)):
                d1 = eq.hildebrand_delta(dD, dP, dH)
                d2 = eq.hildebrand_delta(mD, mP, mH)
                vref = drug.get("molar_volume_cm3_mol") or 250.0
                v["drug_excipient_chi"] = eq.flory_huggins_chi(d1, d2, vref, temperature_C)

        # ---- Ionization at working pH ------------------------------------ #
        pKa = drug.get("pKa")
        ab = str(drug.get("acid_base") or "").lower()
        if isinstance(pKa, (int, float)) and ab in ("acid", "base"):
            v["drug_neutral_fraction"] = eq.neutral_fraction(pKa, pH, ab == "acid")
            v["drug_ionized_fraction"] = 1.0 - v["drug_neutral_fraction"]

    return res


def _card_hsp(card: MaterialCard):
    return card.get("delta_D"), card.get("delta_P"), card.get("delta_H")


def _bilayer_hsp(components: List[Component], res: DescriptorResult):
    """Mass-weighted HSP of membrane lipids; falls back to BILAYER_HSP."""
    Ds, Ps, Hs, ws = [], [], [], []
    for c in components:
        d, p, h = _card_hsp(c.card)
        if all(isinstance(x, (int, float)) for x in (d, p, h)):
            Ds.append(d); Ps.append(p); Hs.append(h); ws.append(c.mol_percent)
    if ws:
        return (eq.weighted_mean(Ds, ws), eq.weighted_mean(Ps, ws), eq.weighted_mean(Hs, ws))
    res.notes.append("No component HSP; used representative bilayer HSP (17,4,6) - heuristic.")
    return BILAYER_HSP


def _dominant_matrix(components: List[Component]) -> Optional[Component]:
    """Highest-mol% structural lipid/polymer component (drug excluded upstream)."""
    struct = [c for c in components if c.card.material_type in
              ("phospholipid", "solid_lipid", "liquid_lipid", "polymer", "nonionic_surfactant")]
    if not struct:
        return None
    return max(struct, key=lambda c: c.mol_percent)
