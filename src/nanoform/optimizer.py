"""Objective profiles and multi-candidate comparison.

Provides named objective profiles and utilities to score/rank several user
designs. This is a deterministic ranking aid over descriptor-driven CQA scores;
it does not search formulation space or guarantee an optimum.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .database import Database
from .designer import DesignInput, DesignResult, design, _goal_weights

OBJECTIVE_PROFILES = [
    "balanced", "high_EE", "small_size", "low_PDI", "pulmonary", "stability",
    "sustained_release", "transdermal_deformable", "oral_bilosome",
    "parenteral_cautious",
]


def objective_profiles() -> List[str]:
    return list(OBJECTIVE_PROFILES)


def profile_weights(goal: str) -> Dict[str, float]:
    return _goal_weights(goal)


@dataclass
class RankedDesign:
    label: str
    result: DesignResult
    score: float
    recommendation: str


def rescore(result: DesignResult, goal: str) -> float:
    """Recompute the composite score for a result under a different goal."""
    weights = _goal_weights(goal)
    num = den = 0.0
    for c in result.cqas:
        if c.key == "nanoform_score":
            continue
        w = weights.get(c.key, 0.1)
        num += w * c.score
        den += w
    return num / den if den else 0.0


def compare_designs(inputs: List[DesignInput], goal: str = "balanced",
                    db: Optional[Database] = None) -> List[RankedDesign]:
    ranked = []
    for i, inp in enumerate(inputs):
        res = design(inp, db=db)
        score = rescore(res, goal)
        ranked.append(RankedDesign(
            label=inp.formulation_id or f"design-{i+1}",
            result=res, score=score,
            recommendation=res.executive_decision,
        ))
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked


def comparison_table(ranked: List[RankedDesign]) -> List[Dict[str, Any]]:
    """Flatten a ranked comparison into rows for display/CSV."""
    rows = []
    for r in ranked:
        cq = {c.key: c for c in r.result.cqas}
        rows.append({
            "design": r.label,
            "goal_score": round(r.score, 3),
            "EE": cq["encapsulation_efficiency"].estimate,
            "size": cq["particle_size"].estimate,
            "PDI": cq["pdi"].estimate,
            "zeta": cq["zeta_potential"].estimate,
            "drug_loading": cq["drug_loading"].estimate,
            "release": cq["release_tendency"].estimate,
            "crystallization": cq["crystallization_risk"].estimate,
            "solvent": cq["solvent_suitability"].estimate,
            "recommendation": r.recommendation,
        })
    return rows
