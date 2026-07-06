# Evaluation and Monitoring

Even at v0.1 we treat evaluation as first-class. The tool makes *heuristic*
recommendations; the point of evaluation is to keep it honest, grounded, and
non-overclaiming — and to prepare for future outcome-based calibration.

## Metrics
| Metric | How | Status |
|---|---|---|
| Deterministic calculation correctness | unit tests vs known values (`tests/test_imports.py`) | ✅ |
| Database coverage | `coverage_summary.csv`, `Database.coverage()` | ✅ |
| Missing-value exposure | surfaced per design + `unresolved_missing_values.csv` | ✅ |
| Groundedness of explanations | `validate_grounding`, claim categories | ✅ |
| Unsupported-claim rate | `audit_claims_against_evidence` | ✅ |
| Refusal / fallback rate (LLM) | `detect_refusal`, fallback path | ✅ (simulated) |
| Report generation success | `tests/test_reporting.py` | ✅ |
| Schema failure rate | `validate_database` | ✅ |
| Latency / cost per design | to add when LLM enabled | ⏳ |
| CQA calibration (EE/size/…) | requires internal outcomes (DML-3) | ⏳ |

## Tests
- Deterministic chemistry kernels (`test_imports.py`).
- Retrieval/database + schema/aliasing/validation (`test_database.py`).
- Design pipeline + batch mass (`test_designer.py`).
- Solvent / carrier ranking incl. route-safety (`test_solvent_recommender.py`,
  `test_carrier_recommender.py`).
- Sanity rules (`test_sanity.py`).
- Report groundedness / no-overclaim (`test_reporting.py`).
- AI layer disabled-safe + refusal/fallback/grounding (`test_ai_orchestrator.py`).
- CLI smoke tests (`test_cli.py`).

CI runs `compileall`, `validate_database`, `pytest`, and CLI smoke tests on
3.10/3.11/3.12. No `pytest || true`.

## Monitoring hooks
For each design/request, capture: request ID · route/family · selected materials
· evidence-bundle hash · model name (if LLM) · refusal status · fallback status ·
output maturity level · estimated constants used · missing critical values. The
evidence hash makes runs reproducible and auditable.

## Safety note
Benign life-science/pharmaceutics prompts may trigger some model safeguards. The
app continues deterministic calculations even when LLM-assisted reasoning is
unavailable, and never silently fails a refusal.
