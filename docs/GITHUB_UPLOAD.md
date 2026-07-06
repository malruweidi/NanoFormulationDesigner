# Publishing to GitHub

The repository is ready to publish as a local-first scientific Python project. The generated CSV database under `data/` is intentionally committed because it is part of the tool, not a cache. Runtime CSVs are also copied under `src/nanoform/data/` so editable and packaged installs both work.

## 1. Initialize and commit

```bash
cd NanoFormulationDesigner
git init
git add .
git commit -m "Initial commit: NanoFormulationDesigner v0.1.0"
```

## 2. Create the remote and push

Using GitHub CLI:

```bash
gh repo create NanoFormulationDesigner --public --source=. --remote=origin --push
```

Or manually:

```bash
git branch -M main
git remote add origin https://github.com/<your-github-username>/NanoFormulationDesigner.git
git push -u origin main
```

## 3. Verify CI

`.github/workflows/tests.yml` runs on push and pull request across Python 3.10, 3.11, and 3.12:

1. install package with development extras;
2. rebuild the database from the curated Excel master;
3. validate the database;
4. byte-compile source, app, and scripts;
5. run `pytest`;
6. run CLI smoke tests.

The Actions tab should turn green after the first push.

## 4. Recommended repository settings

- Add topics: `pharmaceutics`, `nanomedicine`, `formulation`, `drug-delivery`, `decision-support`, `python`, `streamlit`.
- Enable branch protection on `main` requiring the `tests` workflow.
- Add screenshots to `docs/img/` only after the Streamlit interface is visually finalized.
- Add a short repository description: `Materials-aware nanocarrier formulation design and decision-support workbench.`

## 5. Fresh-clone sanity check

```bash
git clone https://github.com/<your-github-username>/NanoFormulationDesigner.git
cd NanoFormulationDesigner
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/import_excel_database.py
python scripts/validate_database.py
pytest -q
streamlit run app.py
```
