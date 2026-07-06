# Contributing Database Values

We welcome curated material data. Quality and provenance matter more than volume.

## Rules
1. **One source per value.** Every property row needs a `source_id` that exists
   in `sources.csv`.
2. **Tag honestly.** Use `data_quality = estimated` (and confidence ≤ 0.40) for
   any value you cannot cite from a primary/secondary source.
3. **Never guess MW or formal charge.** If unknown, leave it out and add a row to
   the missing-values queue instead.
4. **Prefer canonical property names** (`nanoform/schema.py`); aliases are folded
   automatically, but canonical is cleaner.

## Workflow
```bash
# 1. add a source (if new) to scripts/build_database.py SOURCES
# 2. add the material via add(...) / helper (props vs est)
python scripts/build_database.py
python scripts/validate_database.py
pytest -q
```

## Property checklist by class
- **API:** MW, logP, pKa + acid_base, water solubility, HSP (dD/dP/dH), TPSA,
  HBD/HBA, BCS.
- **Surfactant:** MW, HLB, tail_carbons, tail_unsaturation, n_tails,
  headgroup_area_nm2, CMC, charge/flags.
- **Phospholipid/lipid:** MW, Tm_C, tails, charge, headgroup_area, molar_volume,
  flags (pegylated/ionizable/fusogenic).
- **Solvent:** MW, density, bp, HSP, ICH_class, water_miscibility, polarity.
- **Carrier:** cryoprotectant/porous flags, Tg, MW.
- **Polymer:** avg_MW, Tg, formal_charge, class flags.

## PR expectations
Include the citation in the source row, keep confidence honest, and add/adjust a
test if the value changes a documented behavior.
