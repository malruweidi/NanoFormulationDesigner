"""Solvent recommender.

Ranks single solvents (and optional binary blends) for dissolving a chosen drug,
subject to process and route constraints. Scoring is a transparent weighted sum
of database-backed terms; it is a rational-screening heuristic, not a validated
solubility predictor.

Score drivers:
    * affinity      : bounded RED-to-affinity mapping (Hansen; closer = better)
    * process_fit   : volatility for evaporation methods, safety for injection
    * safety        : ICH class penalty + explicit toxicity penalty
    * route_fit     : pulmonary/parenteral acceptability
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Dict, List, Optional

from . import equations as eq
from .database import Database, MaterialCard, get_database

ICH_PENALTY = {"none": 0.0, "3": 0.1, "2": 0.45, "1": 0.9, "": 0.15}


def _miscibility_score(value) -> float:
    """Return approximate aqueous miscibility score from numeric or curated text."""
    if isinstance(value, (int, float)):
        return eq.clamp(float(value))
    txt = str(value or "").strip().lower()
    if txt in {"miscible", "fully miscible", "yes"}:
        return 1.0
    if "slightly" in txt:
        return 0.2
    if "partial" in txt or "moderate" in txt:
        return 0.5
    if txt in {"immiscible", "no", "0"}:
        return 0.0
    return 0.5


def _red(drug: MaterialCard, dD, dP, dH) -> Optional[float]:
    d = (drug.get("delta_D"), drug.get("delta_P"), drug.get("delta_H"))
    if not all(isinstance(x, (int, float)) for x in d):
        return None
    if not all(isinstance(x, (int, float)) for x in (dD, dP, dH)):
        return None
    R0 = drug.get("hsp_radius")
    r0 = R0 if isinstance(R0, (int, float)) and R0 > 0 else 8.0
    return eq.red_score(eq.hansen_distance(d[0], d[1], d[2], dD, dP, dH), r0)


def _safety_penalty(card: MaterialCard) -> float:
    ich = str(card.get("ICH_class") or "").strip()
    pen = ICH_PENALTY.get(ich, 0.15)
    tox = card.get("toxicity_penalty")
    if isinstance(tox, (int, float)):
        # Curated toxicity_penalty is an ordinal hazard flag, not an absolute
        # 0-1 probability. Convert 0-5-ish values to a bounded additive penalty.
        pen += min(max(float(tox), 0.0), 5.0) / 10.0
    return eq.clamp(pen, 0, 1)


def _process_fit(card: MaterialCard, process: str) -> float:
    bp = card.get("boiling_point_C")
    process = (process or "").lower()
    if any(k in process for k in ("nanoprecip", "evapor", "emulsion", "spray", "film")):
        # Volatile solvents are easier to remove during process development.
        if isinstance(bp, (int, float)):
            return eq.clamp(1.0 - eq.normalize_score(bp, 40, 200))
        return 0.5
    if "inject" in process or "parenteral" in process:
        # Non-volatile, water-miscible, GRAS-like solvents are preferred.
        m = _miscibility_score(card.get("water_miscibility"))
        return eq.clamp(0.3 + 0.7 * m)
    return 0.5


RESTRICTIVE_ROUTES = ("pulmonary", "parenteral", "ocular")


def _route_fit(card: MaterialCard, route: str) -> float:
    route = (route or "").lower()
    ich = str(card.get("ICH_class") or "")
    if route in RESTRICTIVE_ROUTES:
        if ich in ("1", "2"):
            return 0.2
        return 0.9
    if route in ("oral", "topical", "transdermal", "nasal"):
        if ich == "1":
            return 0.2
        if ich == "2":
            return 0.45
        if ich == "3":
            return 0.75
        return 0.85
    return 0.7


def _route_safety_gate(ich: str, route: str) -> float:
    """Multiplicative route gate for residual-solvent risk."""
    route = (route or "").lower()
    if route in RESTRICTIVE_ROUTES:
        if ich == "1":
            return 0.25
        if ich == "2":
            return 0.5
    if route in ("oral", "topical", "transdermal", "nasal"):
        if ich == "1":
            return 0.4
        if ich == "2":
            return 0.65
    return 1.0


def recommend_solvents(
    drug_name: str,
    route: str = "general",
    process: str = "nanoprecipitation",
    allowed: Optional[List[str]] = None,
    include_blends: bool = False,
    db: Optional[Database] = None,
    top_n: int = 12,
) -> List[Dict[str, Any]]:
    db = db or get_database()
    drug = db.card(drug_name)
    if drug is None:
        raise ValueError(f"Unknown drug: {drug_name!r}")

    solvents = []
    for _, row in db.by_type("solvent").iterrows():
        card = db.card(row["material_id"])
        if allowed and card.name not in allowed and card.material_id not in allowed:
            continue
        solvents.append(card)

    results = []
    for card in solvents:
        red = _red(drug, card.get("delta_D"), card.get("delta_P"), card.get("delta_H"))
        affinity = eq.red_affinity_score(red)
        safety = 1.0 - _safety_penalty(card)
        pfit = _process_fit(card, process)
        rfit = _route_fit(card, route)
        ich = str(card.get("ICH_class") or "")
        score = (0.45 * affinity + 0.2 * safety + 0.2 * pfit + 0.15 * rfit) \
            * _route_safety_gate(ich, route)
        warns = []
        if ich in ("1", "2"):
            warns.append(f"ICH class {ich} residual-solvent limit applies")
        if red is None:
            warns.append("Drug HSP missing -> affinity is a neutral placeholder")
        results.append({
            "solvent": card.name,
            "type": "single",
            "score": round(score, 3),
            "RED": round(red, 3) if red is not None else None,
            "ICH_class": card.get("ICH_class"),
            "boiling_point_C": card.get("boiling_point_C"),
            "warnings": "; ".join(warns),
        })

    if include_blends:
        results.extend(_blend_candidates(drug, solvents, route, process))

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_n]


def _blend_candidates(drug, solvents, route, process, max_pairs=40):
    """50:50-ish binary blends whose volume-mixed HSP may approach the drug."""
    out = []
    scored = [s for s in solvents if all(
        isinstance(s.get(k), (int, float)) for k in ("delta_D", "delta_P", "delta_H"))]
    for a, b in list(combinations(scored, 2))[:max_pairs]:
        best = None
        for f in (0.25, 0.5, 0.75):
            dD = f * a.get("delta_D") + (1 - f) * b.get("delta_D")
            dP = f * a.get("delta_P") + (1 - f) * b.get("delta_P")
            dH = f * a.get("delta_H") + (1 - f) * b.get("delta_H")
            red = _red(drug, dD, dP, dH)
            if red is None:
                continue
            if best is None or red < best[0]:
                best = (red, f)
        if best is None:
            continue
        red, f = best
        affinity = eq.red_affinity_score(red)
        safety = 1.0 - max(_safety_penalty(a), _safety_penalty(b))
        pfit = 0.5 * (_process_fit(a, process) + _process_fit(b, process))
        rfit = min(_route_fit(a, route), _route_fit(b, route))
        gate = min(_route_safety_gate(str(a.get("ICH_class") or ""), route),
                   _route_safety_gate(str(b.get("ICH_class") or ""), route))
        score = (0.45 * affinity + 0.2 * safety + 0.2 * pfit + 0.15 * rfit) * gate
        out.append({
            "solvent": f"{a.name} + {b.name} ({int(f*100)}:{int((1-f)*100)} v/v)",
            "type": "blend",
            "score": round(score, 3),
            "RED": round(red, 3),
            "ICH_class": f"{a.get('ICH_class')}/{b.get('ICH_class')}",
            "boiling_point_C": None,
            "warnings": "Blend ratio is a starting estimate; verify miscibility & residual limits",
        })
    return out
