# Material Coverage

The internal database is built from a curated Excel master at `data/source/NanoFormulationDesigner_Internal_Material_Database.xlsx`, converted into canonical relational CSVs by `scripts/import_excel_database.py`, unioned with any seed materials missing from the Excel master, and enriched with selected literature/property overlays.

The database is deliberately conservative. Values are imported only when the material identity is clear and the property can be represented in the canonical schema. Non-positive placeholders and mismatched identities are excluded rather than stored as false precision.

## Current generated snapshot

- 321 materials
- 3,449 property rows
- 25 source records
- 313 prioritized unresolved missing-value rows

## Counts by material type

| material_type | count |
|---|---:|
| api | 76 |
| nonionic_surfactant | 57 |
| phospholipid | 44 |
| polymer | 40 |
| solvent | 23 |
| carrier | 22 |
| liquid_lipid | 21 |
| solid_lipid | 19 |
| bile_salt | 9 |
| sterol | 6 |
| ionic_surfactant | 4 |
| **total** | **321** |

## Constant coverage

| Constant | # materials carrying the constant |
|---|---:|
| MW or avg_MW | 317 |
| Hansen δD/δP/δH | 261 |
| HSP radius R0 | 227 |
| molar volume | 238 |
| formal charge | 194 |
| HLB | 71 |
| tail carbons | 109 |
| headgroup area | 108 |
| pKa | 76 |
| transition temperature, Tm | 42 |

## Enrichment overlays

Property overlays under `data/source/*.csv` add values only when a material has no curated value for that property. They do not overwrite the Excel master.

- `chembl_drug_additions.csv` adds researched API identity and molecular descriptor records where the ChEMBL identity match is clear.
- `excipient_property_additions.csv` adds representative CMC values for selected water-soluble surfactants.
- `drug_pka_additions.csv` adds formulation-relevant pKa and acid/base annotations when curated source information is available.

If an identity match is ambiguous, the candidate is dropped. For example, intended API additions that resolve to a glycoside, dimer, salt, or non-target entity should not be accepted as the parent compound.

## Curation priorities

The most important gaps are API solubility/Hansen parameters, surfactant CMC values, phospholipid transition temperatures, carrier/polymer Tg values, and material-class-specific charge or molecular-weight records. These are exposed in `data/internal_constants/unresolved_missing_values.csv` rather than silently imputed.

Regenerate the live reports with:

```bash
python scripts/coverage_report.py
python scripts/missing_values_report.py
```

See [`SCIENTIFIC_LIMITATIONS.md`](SCIENTIFIC_LIMITATIONS.md) for how missing and estimated values affect design maturity.
