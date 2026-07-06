"""NanoFormulationDesigner (`nanoform`).

A materials-aware nanocarrier formulation design and decision-support platform.

Architecture (authoritative order):
    1. Deterministic scientific kernels  -> nanoform.equations, nanoform.descriptors
    2. Retrieval / database layer        -> nanoform.database, nanoform.schema
    3. Design + recommenders             -> nanoform.designer, *_recommender, guided
    4. Explainability / sanity / reports -> nanoform.explainability, sanity, reporting
    5. Optional LLM orchestration        -> nanoform.ai_orchestrator (disabled-safe)

All outputs are descriptor-driven decision-support estimates that require
laboratory verification. This is NOT a validated predictor.
"""

__version__ = "0.1.0"

CAUTION = (
    "Outputs are descriptor-driven, ranked decision-support estimates. They are "
    "heuristic until trained/validated on internal experimental outcomes and "
    "require laboratory verification. Confidence depends on database coverage."
)

__all__ = ["__version__", "CAUTION"]
