"""Carrier / cryoprotectant recommender.

Ranks solid carriers, cryo/lyoprotectants and dispersibility aids for a given
route, family and process (e.g. lyophilization, spray-drying, DPI). Transparent
weighted heuristic - a rational-screening aid, not a validated predictor.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import equations as eq
from .database import Database, MaterialCard, get_database


def _lyo_fit(card: MaterialCard) -> float:
    """Glass-former quality for freeze/spray drying (higher Tg = better cake)."""
    if not card.get("cryoprotectant"):
        return 0.2
    tg = card.get("Tg_C")
    if isinstance(tg, (int, float)):
        return eq.clamp(0.4 + 0.6 * eq.normalize_score(tg, 30, 120))
    return 0.6


def _dpi_fit(card: MaterialCard) -> float:
    """Dry-powder aerosol fit: porous/dispersibility aids and standard carriers."""
    score = 0.3
    if card.get("porous_carrier"):
        score += 0.4
    if "leucine" in card.name.lower():
        score += 0.3
    if "lactose" in card.name.lower():
        score += 0.35
    if card.get("cryoprotectant"):
        score += 0.15
    return eq.clamp(score)


def recommend_carriers(
    route: str = "general",
    family: str = "liposome",
    process: str = "lyophilization",
    powder_needed: bool = False,
    db: Optional[Database] = None,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    db = db or get_database()
    process = (process or "").lower()
    route = (route or "").lower()
    want_powder = powder_needed or route == "pulmonary" or family == "dry_powder_carrier" \
        or "spray" in process or "dpi" in process

    results = []
    for _, row in db.by_type("carrier").iterrows():
        card = db.card(row["material_id"])
        lyo = _lyo_fit(card)
        dpi = _dpi_fit(card)
        if want_powder:
            score = 0.55 * dpi + 0.45 * lyo
        else:
            score = 0.8 * lyo + 0.2 * dpi
        warns = []
        if route in ("parenteral",) and card.name in ("Microcrystalline cellulose", "Colloidal silicon dioxide"):
            warns.append("Insoluble solid - not suitable for parenteral solutions")
            score *= 0.3
        if card.name.startswith("Sulfobutylether") and route != "parenteral":
            warns.append("Parenteral-grade complexation host; may be overkill for other routes")
        results.append({
            "carrier": card.name,
            "category": card.category,
            "score": round(eq.clamp(score), 3),
            "cryoprotectant": bool(card.get("cryoprotectant")),
            "Tg_C": card.get("Tg_C"),
            "warnings": "; ".join(warns),
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:top_n]
