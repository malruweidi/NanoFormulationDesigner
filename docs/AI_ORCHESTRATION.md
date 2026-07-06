# Optional AI Orchestration

`nanoform.ai_orchestrator` is an optional reporting layer that sits above the deterministic formulation engine. It is intentionally conservative: the scientific calculations remain authoritative, and the model layer may only summarize or polish evidence that the platform has already generated.

No API key is required for normal use. If no model client is configured, every AI-assisted function returns deterministic text and marks the result as disabled-safe.

## Architecture

```text
Streamlit UI / CLI / future API
   -> task router
   -> deterministic kernels and database retrieval       # authoritative
   -> minimal evidence bundle                            # hashed, auditable
   -> optional model-assisted wording/review              # no new constants
   -> grounding audit / deterministic fallback
```

## Routing tiers

The router distinguishes deterministic tasks from optional language tasks:

- `deterministic`: calculations, validation, ranking, descriptors, batch tables, sanity checks.
- `light`: extraction or structured UI/routing tasks when a model is explicitly enabled.
- `mid`: routine scientific explanation or report polishing.
- `frontier`: hard synthesis, ambiguous trade-offs, long reports, or final review.
- `fallback`: deterministic return path or secondary model path after a benign refusal.

Model names are not hard-coded to a public claim. They are configurable through environment variables:

```bash
export NANOFORM_LLM_LIGHT_MODEL="your-light-model-id"
export NANOFORM_LLM_MID_MODEL="your-mid-model-id"
export NANOFORM_LLM_FRONTIER_MODEL="your-frontier-model-id"
export NANOFORM_LLM_FALLBACK_MODEL="your-fallback-model-id"
```

A client is any callable with the signature `(model: str, prompt: str) -> str`, so the orchestration layer is provider-agnostic.

## Grounding discipline

`build_evidence_bundle` passes only the minimal context required for the requested task: drug card, component cards, solvent card, descriptors, CQA tendencies, missing values, sanity messages, source IDs, and the caution statement. The bundle is content-hashed for auditability.

The prompt explicitly prohibits invented constants. `validate_grounding` flags numeric claims not present in the evidence bundle. `audit_claims_against_evidence` classifies claims as `database-backed`, `calculator-backed`, `source-backed`, `heuristic`, or `unsupported`.

Unsupported claims should be removed, not dressed up.

## Refusal and fallback handling

Benign pharmaceutics prompts can occasionally trigger generic model refusals. The wrapper detects short refusal-like responses, retries once through the fallback tier, and then returns the deterministic output if the model remains unavailable or refuses. Core calculations never depend on model cooperation.

## Enabling model-assisted text

```bash
pip install -e ".[llm]"   # optional provider SDK dependencies, if used
export NANOFORM_ENABLE_LLM=1
```

Then pass a provider-specific client callable to `summarize_design_with_llm` or `generate_report_with_llm`. Without `NANOFORM_ENABLE_LLM=1` or a recognized provider key, the layer remains disabled-safe.
