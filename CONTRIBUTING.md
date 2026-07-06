# Contributing to NanoFormulationDesigner

Thank you for your interest. This project has two kinds of contributions:
**code** and **curated database values**. Both are welcome.

## Ground rules

1. **Never fabricate precise scientific constants.** If a value cannot be
   verified from a citable source, mark it `estimated`, `variable`, or
   `missing`, lower its `confidence_score`, and add a note. See
   [docs/CONTRIBUTING_DATABASE_VALUES.md](docs/CONTRIBUTING_DATABASE_VALUES.md).
2. **The deterministic kernels are authoritative.** The optional LLM layer must
   never introduce constants; it only reasons over kernel outputs and database
   records.
3. **Do not overclaim.** Outputs are descriptor-driven decision-support
   estimates that require laboratory verification.

## Development setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    |    Unix: source .venv/bin/activate
pip install -e ".[dev]"
python scripts/build_database.py      # regenerate CSVs from the seed source
python -m compileall src app.py
pytest
```

## Adding materials

1. Edit the seed dictionaries in `scripts/build_database.py`.
2. Run `python scripts/build_database.py` to regenerate the CSVs.
3. Run `python scripts/validate_database.py` and `pytest`.
4. Each property must carry `source_id`, `data_quality`, and `confidence_score`.

## Pull requests

- Keep modules small and single-purpose.
- Add or update tests for new behavior.
- CI must pass: `compileall`, `pytest`, and CLI smoke tests (no `pytest || true`).
