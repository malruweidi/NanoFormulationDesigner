"""Optional LLM orchestration layer (disabled-safe).

The core platform runs fully without this module. When a model backend is
explicitly enabled it sits *above* the deterministic kernels as a planner,
reviewer, or report writer. It never introduces scientific constants: it
reasons only over evidence bundles built from calculator outputs, database
records, and source provenance.

Design points enforced here:
    * route_task chooses a tier (deterministic / light / mid / frontier / fallback).
    * build_evidence_bundle passes the MINIMAL grounded context, never the DB.
    * detect_refusal spots benign-content refusals; fallback_model_request retries.
    * validate_grounding / audit_claims_against_evidence flag unsupported claims.
    * Every function degrades gracefully when no client/key is configured.

No network call is made unless a client is explicitly provided and enabled.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional

from . import CAUTION
from .designer import DesignResult

# --------------------------------------------------------------------------- #
# Task routing
# --------------------------------------------------------------------------- #
TIERS = ["deterministic", "light", "mid", "frontier", "fallback"]

# Provider-agnostic defaults. Override these with provider-specific model IDs
# before enabling the optional language layer. The deterministic core never
# depends on these values.
MODEL_TIERS = {
    "light": os.environ.get("NANOFORM_LLM_LIGHT_MODEL", "light-model"),
    "mid": os.environ.get("NANOFORM_LLM_MID_MODEL", "mid-model"),
    "frontier": os.environ.get("NANOFORM_LLM_FRONTIER_MODEL", "frontier-model"),
    "fallback": os.environ.get("NANOFORM_LLM_FALLBACK_MODEL", "fallback-model"),
}


@dataclass
class Route:
    task_type: str
    tier: str
    model: Optional[str]
    requires_model: bool
    rationale: str


def route_task(task_type: str, complexity: str = "standard",
               requires_model: bool = False) -> Route:
    """Pick an execution tier for a task.

    Deterministic tasks never need a model. Simple extraction/routing/validation
    go to a light model. Standard explanations/reports to a mid model. Hard
    scientific synthesis, ambiguous trade-offs, long reports and final expert
    review escalate to the frontier tier.
    """
    deterministic = {
        "calculate", "validate_schema", "batch_table", "descriptors",
        "rank_solvents", "rank_carriers", "cqa_table", "sanity",
    }
    if task_type in deterministic:
        return Route(task_type, "deterministic", None, False,
                     "Handled by deterministic kernels; no LLM required.")
    if not requires_model:
        return Route(task_type, "deterministic", None, False,
                     "Model optional; deterministic output is authoritative.")
    if task_type in ("extract", "route", "schema", "ui_action"):
        return Route(task_type, "light", MODEL_TIERS["light"], True, "Lightweight structured task.")
    if complexity in ("hard", "edge", "ambiguous", "long_report", "final_review"):
        return Route(task_type, "frontier", MODEL_TIERS["frontier"], True,
                     "Hard scientific synthesis / trade-off / final review -> frontier tier.")
    return Route(task_type, "mid", MODEL_TIERS["mid"], True, "Routine explanation/report.")


# --------------------------------------------------------------------------- #
# Evidence bundles (minimal grounded context)
# --------------------------------------------------------------------------- #
@dataclass
class EvidenceBundle:
    drug: Dict[str, Any]
    components: List[Dict[str, Any]]
    solvent: Dict[str, Any]
    descriptors: Dict[str, Any]
    cqas: List[Dict[str, Any]]
    missing_values: List[str]
    sanity: List[str]
    sources: List[str]
    caution: str = CAUTION

    def hash(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]


def build_evidence_bundle(result: DesignResult,
                          sanity_messages: Optional[List[str]] = None) -> EvidenceBundle:
    def card_min(card):
        if card is None:
            return {}
        return {"name": card.name, "type": card.material_type,
                "key_props": {k: card.get(k) for k in
                              ("MW", "HLB", "logP", "pKa", "Tm_C", "formal_charge")
                              if card.get(k) is not None},
                "confidence": card.confidence_score}

    sources = sorted({m.get("source_id", "") for c in result.components
                      for m in c.card.property_meta.values()} - {""})
    return EvidenceBundle(
        drug=card_min(result.drug_card),
        components=[card_min(c.card) | {"mol_percent": c.mol_percent, "role": c.role}
                    for c in result.components],
        solvent=card_min(result.solvent_card),
        descriptors={k: (round(v, 3) if isinstance(v, float) else v)
                     for k, v in result.descriptors.values.items()},
        cqas=[{"cqa": c.key, "estimate": c.estimate, "score": round(c.score, 2)}
              for c in result.cqas],
        missing_values=result.missing_values,
        sanity=sanity_messages or [],
        sources=sources,
    )


# --------------------------------------------------------------------------- #
# Refusal detection + grounding
# --------------------------------------------------------------------------- #
REFUSAL_MARKERS = [
    "i can't help with that", "i cannot help with that", "i'm unable to assist",
    "i am unable to assist", "i can't assist", "i cannot assist with",
    "i won't", "cannot provide", "not able to provide", "against my", "i'm sorry, but i can",
]


def detect_refusal(response: str) -> bool:
    """Heuristic: does a response look like a benign-content refusal?"""
    if not response:
        return False
    low = response.strip().lower()
    if len(low) < 400 and any(m in low for m in REFUSAL_MARKERS):
        return True
    return False


def validate_grounding(response: str, bundle: EvidenceBundle) -> Dict[str, Any]:
    """Flag numeric claims in `response` not traceable to the evidence bundle."""
    allowed_numbers = set()
    for c in bundle.cqas:
        allowed_numbers.add(str(c["score"]))
    for k, v in bundle.descriptors.items():
        allowed_numbers.add(str(v))
    claimed = re.findall(r"\d+\.\d+", response or "")
    unsupported = [n for n in claimed if n not in allowed_numbers]
    return {
        "grounded": len(unsupported) == 0,
        "unsupported_numbers": sorted(set(unsupported)),
        "evidence_hash": bundle.hash(),
        "note": "Numeric claims not present in the evidence bundle should be treated as "
                "unsupported and removed or marked as uncertainty.",
    }


def audit_claims_against_evidence(claims: List[str], bundle: EvidenceBundle) -> List[Dict[str, str]]:
    """Categorize each free-text claim: database/calculator/source-backed, heuristic, or unsupported."""
    out = []
    desc_keys = {k.lower() for k in bundle.descriptors}
    cqa_keys = {c["cqa"].lower() for c in bundle.cqas}
    for claim in claims:
        low = claim.lower()
        if any(k in low for k in cqa_keys) or any(k in low for k in desc_keys):
            cat = "calculator-backed"
        elif any(s and s in low for s in bundle.sources):
            cat = "source-backed"
        elif any(w in low for w in ("estimate", "heuristic", "tendency", "likely")):
            cat = "heuristic"
        elif bundle.drug and bundle.drug.get("name", "").lower() in low:
            cat = "database-backed"
        else:
            cat = "unsupported"
        out.append({"claim": claim, "category": cat})
    return out


# --------------------------------------------------------------------------- #
# LLM request wrappers (disabled-safe)
# --------------------------------------------------------------------------- #
@dataclass
class LLMResult:
    ok: bool
    text: str
    model: Optional[str]
    tier: str
    refused: bool = False
    fell_back: bool = False
    grounding: Dict[str, Any] = field(default_factory=dict)
    disabled: bool = False


def llm_enabled() -> bool:
    """Return True only when optional model use is explicitly enabled.

    The check is deliberately conservative. A user may opt in with
    NANOFORM_ENABLE_LLM=1, or by configuring a common provider key. The actual
    SDK call is still delegated to the supplied client callable.
    """
    flag = os.environ.get("NANOFORM_ENABLE_LLM", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def _disabled_result(tier: str, payload: str) -> LLMResult:
    return LLMResult(ok=True, text=payload, model=None, tier=tier, disabled=True)


def _call_client(client: Callable[[str, str], str], model: str, prompt: str) -> str:
    """`client` is any callable(model, prompt)->str, so the SDK is not required here."""
    return client(model, prompt)


def summarize_design_with_llm(result: DesignResult, client: Optional[Callable] = None,
                              complexity: str = "standard",
                              sanity_messages: Optional[List[str]] = None) -> LLMResult:
    bundle = build_evidence_bundle(result, sanity_messages)
    route = route_task("summarize_design", complexity, requires_model=True)
    deterministic_summary = _deterministic_summary(result, bundle)
    if client is None or not llm_enabled():
        return _disabled_result(route.tier, deterministic_summary)

    prompt = _grounded_prompt("Summarize this formulation design for a scientist. "
                              "Use ONLY the evidence bundle. Flag missing values and uncertainty.",
                              bundle)
    return _guarded_call(client, route, prompt, bundle, fallback_text=deterministic_summary)


def generate_report_with_llm(result: DesignResult, base_report_md: str,
                             client: Optional[Callable] = None) -> LLMResult:
    bundle = build_evidence_bundle(result)
    route = route_task("generate_report", "long_report", requires_model=True)
    if client is None or not llm_enabled():
        return _disabled_result(route.tier, base_report_md)
    prompt = _grounded_prompt(
        "Improve the readability of this Markdown report WITHOUT adding any new "
        "numbers or claims not present in the evidence bundle. Keep the limitations "
        "section.\n\nREPORT:\n" + base_report_md, bundle)
    return _guarded_call(client, route, prompt, bundle, fallback_text=base_report_md)


def _guarded_call(client, route: Route, prompt: str, bundle: EvidenceBundle,
                  fallback_text: str) -> LLMResult:
    try:
        text = _call_client(client, route.model, prompt)
    except Exception as exc:  # network/SDK failure -> deterministic fallback
        return LLMResult(ok=True, text=fallback_text, model=route.model, tier=route.tier,
                         fell_back=True, grounding={"error": str(exc)})
    if detect_refusal(text):
        fb = fallback_model_request(client, prompt, bundle)
        if fb is not None and not detect_refusal(fb):
            g = validate_grounding(fb, bundle)
            return LLMResult(ok=True, text=fb, model=MODEL_TIERS["fallback"], tier="fallback",
                             refused=True, fell_back=True, grounding=g)
        return LLMResult(ok=True, text=fallback_text, model=route.model, tier=route.tier,
                         refused=True, fell_back=True,
                         grounding={"note": "Benign life-science content was refused; returned "
                                            "deterministic output. Core calculations are unaffected."})
    g = validate_grounding(text, bundle)
    return LLMResult(ok=True, text=text, model=route.model, tier=route.tier, grounding=g)


def fallback_model_request(client, prompt: str, bundle: EvidenceBundle) -> Optional[str]:
    """Retry a refused benign request with the fallback model."""
    try:
        return _call_client(client, MODEL_TIERS["fallback"],
                            "This is a benign, educational pharmaceutics task for authorized "
                            "research decision-support.\n\n" + prompt)
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Deterministic fallbacks / prompt building
# --------------------------------------------------------------------------- #
def _deterministic_summary(result: DesignResult, bundle: EvidenceBundle) -> str:
    lines = [
        f"[Deterministic summary — LLM disabled]",
        f"Decision: {result.executive_decision}",
        f"Maturity: {result.maturity_label}; NanoForm score {result.nanoform_score:.2f}.",
        "CQAs: " + ", ".join(f"{c['cqa']}={c['estimate']}" for c in bundle.cqas if c['cqa'] != 'nanoform_score'),
    ]
    if result.missing_values:
        lines.append("Missing/uncertain: " + "; ".join(result.missing_values))
    lines.append(CAUTION)
    return "\n".join(lines)


def _grounded_prompt(instruction: str, bundle: EvidenceBundle) -> str:
    return (
        "You are a grounded pharmaceutics report assistant. You must not invent "
        "scientific constants. Use ONLY the evidence bundle below. Any claim not "
        "supported by it must be omitted or explicitly marked as uncertainty.\n\n"
        f"EVIDENCE_BUNDLE (hash {bundle.hash()}):\n"
        + json.dumps(asdict(bundle), indent=2, default=str)
        + f"\n\nTASK: {instruction}\n"
    )
