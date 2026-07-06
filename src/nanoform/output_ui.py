"""UI-agnostic output helpers.

Converts DesignResult / recommender outputs into pandas DataFrames and small
display primitives (badges, confidence labels) used by the Streamlit app and
the CLI. No Streamlit import here so the module stays testable headless.
"""
from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .designer import DesignResult
from .explainability import explain_all, improvement_suggestions


def cqa_table_df(result: DesignResult) -> pd.DataFrame:
    rows = [{
        "CQA": c.label, "Estimate": c.estimate, "Score": round(c.score, 2),
        "Top driver": c.drivers[0] if c.drivers else "",
        "Top risk": c.risks[0] if c.risks else "",
    } for c in result.cqas]
    return pd.DataFrame(rows)


def descriptor_df(result: DesignResult) -> pd.DataFrame:
    rows = [{"Descriptor": k, "Value": _round(v)} for k, v in result.descriptors.values.items()]
    return pd.DataFrame(rows)


def batch_df(result: DesignResult) -> pd.DataFrame:
    return pd.DataFrame(result.batch_table)


def explanations_df(result: DesignResult) -> pd.DataFrame:
    rows = []
    for e in explain_all(result):
        rows.append({
            "CQA": e.cqa_key,
            "Positive drivers": "; ".join(e.positive_drivers),
            "Risk drivers": "; ".join(e.risk_drivers),
            "Recommended change": e.recommended_change,
        })
    return pd.DataFrame(rows)


def suggestions_list(result: DesignResult) -> List[str]:
    return improvement_suggestions(result)


def confidence_badge(score: float) -> str:
    if score is None:
        return "unknown"
    if score >= 0.7:
        return "high confidence"
    if score >= 0.4:
        return "medium confidence"
    return "low confidence"


def material_card_dict(card) -> Dict[str, Any]:
    """Flatten a MaterialCard for display, including provenance + missing flags."""
    props = {}
    for k, val in card.properties.items():
        meta = card.property_meta.get(k, {})
        props[k] = {
            "value": val, "unit": meta.get("unit", ""),
            "quality": meta.get("data_quality", ""),
            "source": meta.get("source_id", ""),
            "confidence": meta.get("confidence_score", ""),
        }
    return {
        "name": card.name, "material_type": card.material_type,
        "category": card.category, "identity": card.identity,
        "confidence_score": card.confidence_score,
        "route_suitability": card.route_suitability,
        "safety_notes": card.safety_notes,
        "properties": props,
    }


def _round(v):
    if isinstance(v, float):
        return round(v, 3)
    return v
