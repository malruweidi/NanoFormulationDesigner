# Repository Overview

NanoFormulationDesigner is a scientific software prototype for early nanocarrier formulation screening. It is designed around a simple premise: before running wet-lab formulation experiments, the scientist should be able to audit the material constants, calculate the relevant descriptors, identify missing data, and rank candidate compositions under explicit assumptions.

## Scientific positioning

The project belongs in the preformulation and formulation-informatics layer, not in the clinical prediction layer. It estimates design tendencies from material properties; it does not claim validated prediction of encapsulation efficiency, particle size, PDI, zeta potential, pharmacokinetics, biodistribution, toxicity, or clinical performance.

Its strongest use case is rational prioritization: selecting candidates for initial screening, rejecting weak compositions early, and exposing which material constants must be curated before a formulation decision is defensible.

## Engineering positioning

The project is intentionally local-first. The Streamlit app and CLI read a local CSV database, run deterministic calculations, and generate reports without external services. Optional model-assisted text generation is isolated from the scientific core and cannot introduce constants.

## Main modules

- `database.py`: loads material identities, properties, provenance, and derived coverage tables.
- `equations.py`: pure scientific equations.
- `descriptors.py`: converts a candidate composition into physicochemical descriptors.
- `designer.py`: orchestrates a design run and assigns CQA tendencies.
- `solvent_recommender.py` and `carrier_recommender.py`: rank process materials under route/process constraints.
- `guided.py`: generates candidate starting points from route, payload, and family logic.
- `reporting.py`: creates grounded Markdown reports.
- `ai_orchestrator.py`: optional disabled-safe language layer over evidence bundles.

## Why the boundaries matter

Nanocarrier formulation data are highly context-dependent: grade, supplier, hydration conditions, process energy, payload loading, buffer, storage, sterilization, and assay method all influence the result. A tool that pretends to generate an optimal formulation without calibrated experimental outcomes would be scientifically misleading. This repository therefore favors transparency over theatrical certainty.

## Suggested GitHub description

Materials-aware nanocarrier formulation design and decision-support workbench.

## Suggested topics

`pharmaceutics`, `nanomedicine`, `drug-delivery`, `formulation`, `preformulation`, `decision-support`, `streamlit`, `python`, `materials-informatics`
