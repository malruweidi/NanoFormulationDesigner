# Guided Designer (Wizard)

`nanoform.guided.run_wizard(drug, route, family, goal)` helps a user *begin* a
design. It returns:

1. **Payload profile** — MW, logP, pKa, acid/base, solubility, BCS, payload
   class, plus formulation hints (e.g. lipophilic → lipid core; biologic →
   delivery-chain design).
2. **Suggested material classes / categories** for the family.
3. **Route warnings** — route-specific CQAs and pitfalls.
4. **Candidate starting points** — a few `DesignInput` templates whose
   components are checked against the database.

> Candidates are **temporary starting points, not stored formulations.** They
> exist to help you begin and must be verified experimentally.

## Templates
Family templates live in `FAMILY_TEMPLATES` (`nanoform/guided.py`), e.g.:
- niosome → Span 60 / cholesterol / dicetyl phosphate (rigid, anionic)
- liposome → HSPC / cholesterol / DSPE-PEG2000 (stealth)
- SLN → Compritol / Tween 80; NLC adds a liquid lipid
- LNP → SM-102 / DSPC / cholesterol / DMG-PEG2000 (mRNA)

Unresolved template components are dropped automatically so the wizard still
produces a valid starting design on partial databases.

## Example
```bash
python -m nanoform.cli wizard-candidates --drug Dexamethasone --route topical --family niosome
```
```python
from nanoform.guided import run_wizard
out = run_wizard("Curcumin", "oral", "solid_lipid_nanoparticle", "high_EE")
```
