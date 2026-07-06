# Curation Workflow

## Principle
**Never fabricate precise values.** Stable constants → `literature`. Uncertain,
grade-dependent, or model-derived values → `estimated` with capped confidence and
a note. Important gaps → `unresolved_missing_values.csv`.

## Adding or editing a material
1. Edit the seed dictionaries in `scripts/build_database.py`
   (`props` = well-established; `est` = estimated/heuristic).
2. Regenerate:
   ```bash
   python scripts/build_database.py
   python scripts/validate_database.py
   ```
3. Log manual edits via the curation log:
   ```python
   from nanoform.curation import log_change
   log_change("SUR003", "update", "CMC_mM", old_value="", new_value="0.05",
              source_id="supplier", curator_note="Croda datasheet")
   ```
4. Run `pytest`.

## Data-quality tags
`literature`, `estimated`, `grade-dependent`, `variable`, `missing`,
`user-provided`. Each property row also carries `source_id` and
`confidence_score`.

## Often-variable properties (tag carefully)
CMC, cloud point, Krafft point, HSP components and radius, molar volume of
mixtures, polymer average MW/Tg, carrier porosity/surface area, powder density,
solvent-specific solubility, excipient route suitability.

## Recommended sources
PubChem · supplier datasheets (Croda, BASF, Gattefossé, Lipoid) · Avanti Polar
Lipids · Handbook of Pharmaceutical Excipients · ICH Q3C(R8) · Hansen Solubility
Parameters handbook · peer-reviewed literature · pharmacopeial/regulatory sources.

## Reports
```bash
python scripts/coverage_report.py
python scripts/missing_values_report.py
```
