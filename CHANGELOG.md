# Changelog

All notable changes to NanoFormulationDesigner are documented in this file. The format follows the spirit of Keep a Changelog.

## [0.1.0] - 2026-07-01

### Added

- Deterministic scientific kernel layer for batch mass, mixed HLB, Tanford chain volume/length, CPP, Hansen distance and RED, Hildebrand parameter, Flory-Huggins chi, and ionization/neutral fraction.
- Local material-property database with relational CSVs, wide internal constants, provenance, confidence scores, and missing-value tracking.
- Formulation designer producing descriptors, heuristic CQA tendencies, batch tables, design maturity level, and executive decision text.
- Solvent and carrier recommenders with route/process constraints.
- Guided wizard, sanity checks, explainability helpers, optimizer profiles, and Markdown report generation.
- Streamlit application with ten workflow tabs.
- CLI with search, design, CQA table, design report, solvent recommendation, carrier recommendation, wizard candidates, and database validation commands.
- Optional disabled-safe model orchestration layer with task routing, evidence bundles, grounding audit, and deterministic fallback.
- Test suite, GitHub Actions CI, and documentation.

### Notes

- Outputs are descriptor-driven decision-support estimates and require laboratory verification.
- The current maximum design maturity is DML-2 because no calibrated internal outcome dataset is bundled.
- The database is an extensible curated starting point, not an exhaustive excipient encyclopedia.
