# Solvent Recommender

`nanoform.solvent_recommender.recommend_solvents(...)` ranks single solvents and
optional binary blends for dissolving a chosen drug under process/route
constraints. It is a **rational-screening heuristic**, not a solubility
predictor.

## Score
```
score = (0.45*affinity + 0.20*safety + 0.20*process_fit + 0.15*route_fit) * route_safety_gate
```
- **affinity** = `1 − RED(drug, solvent)` using Hansen distance and the drug's
  interaction radius R0 (default 8 if unknown). Closer HSP → higher affinity.
- **safety** = `1 − ICH_penalty − toxicity_penalty` (class 1 ≫ class 2 > class 3).
- **process_fit** — evaporation/nanoprecipitation favor volatile (low-bp)
  solvents; injection favors non-volatile, water-miscible, GRAS solvents.
- **route_fit** — pulmonary/parenteral/ocular disfavor class 1/2.
- **route_safety_gate** — a *hard multiplier* (×0.25 class 1, ×0.5 class 2) for
  restrictive routes: you cannot inhale/inject residual class-2 solvent regardless
  of how well it dissolves the drug.

## Blends
With `include_blends=True`, volume-mixed HSP for pairs is scanned at 25/50/75%
to find a ratio that lowers drug RED. Blend ratios are **starting estimates**;
verify miscibility and residual-solvent limits.

## Warnings
Class-1/2 solvents always carry an ICH residual-limit warning; missing drug HSP
downgrades affinity to a neutral placeholder and is flagged.

## Example
```bash
python -m nanoform.cli recommend-solvent --drug Curcumin --route oral --blends
```
```python
from nanoform.solvent_recommender import recommend_solvents
recommend_solvents("Paclitaxel", route="parenteral", process="nanoprecipitation")
```
