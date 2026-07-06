# Database Schema

The database is **local** and **material-property based**. It is generated into
CSVs under `data/relational/` from two sources, then unioned:

1. **The curated Excel master** —
   `data/source/NanoFormulationDesigner_Internal_Material_Database.xlsx` — the
   authoritative maintainer-curated dataset, converted by
   `scripts/import_excel_database.py`. This importer maps the Excel property
   vocabulary (`Hansen_delta_D`, `phase_transition_temperature_C`,
   `*_flag`, `Class 2`, ...) to the canonical names the kernels read, and derives
   the boolean flags descriptors need.
2. **The bootstrap Python seed** — `scripts/build_database.py` — used only to
   union in materials that are absent from the Excel master.

Never hand-edit generated CSVs — edit the Excel master (or the Python seed) and
re-run `python scripts/import_excel_database.py`.

## Relational tables (`data/relational/`)

### `materials.csv`
`material_id, name, synonyms, material_type, category, subcategory, CAS,
PubChem_CID, SMILES, InChIKey, supplier_or_grade_notes, route_suitability,
regulatory_or_safety_notes, source_id, curation_status, confidence_score, notes`

`material_type` ∈ {api, nonionic_surfactant, ionic_surfactant, phospholipid,
sterol, bile_salt, solid_lipid, liquid_lipid, solvent, carrier, polymer}.

### `material_properties.csv` (long format)
`material_id, property_name, value, unit, temperature_C, pH, method, source_id,
data_quality, confidence_score, notes`

`data_quality` ∈ {literature, estimated, grade-dependent, variable, missing,
user-provided}. Canonical `property_name` values and aliases live in
`nanoform/schema.py`. Categorical properties (`ICH_class`, `acid_base`,
`BCS_class`) are kept as strings by the loader; everything else is numeric.

### `sources.csv`
`source_id, source_type, citation, DOI, URL, access_date, notes`

### `formulations.csv`, `formulation_components.csv`, `outcomes.csv`
Reserved for **user-created history** and **future internal experimental
outcomes**. Ship empty except clearly-marked `EXAMPLE-*` rows. No feature depends
on these being populated.

### `curation_log.csv`
`date, material_id, action, property_name, old_value, new_value, source_id,
curator_note` — append-only audit trail (see `nanoform.curation.log_change`).

## Derived tables (`data/internal_constants/`)

- `internal_constants_wide.csv` — materials joined to a wide property pivot.
- `coverage_summary.csv` — per type/category counts of key constants + curation priority.
- `unresolved_missing_values.csv` — prioritized missing-value queue.

## Examples (`data/examples/`)
`example_user_designs.csv`, `example_batch_table.csv` — inputs the app/CLI can load.

## Rebuild
```bash
python scripts/import_excel_database.py   # authoritative full rebuild + packaged runtime CSV sync
python scripts/validate_database.py       # structural + content checks
```

`build_database.py` remains available as a bootstrap seed builder, but the normal maintainer workflow should use `import_excel_database.py`.
