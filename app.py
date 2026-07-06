"""NanoFormulationDesigner — Streamlit application.

Run with: streamlit run app.py

The interface is a thin presentation layer over the deterministic formulation
kernels and the bundled internal material database. Outputs are descriptor-driven
screening estimates and require laboratory verification before use.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `streamlit run app.py` from a source checkout without an editable install.
SRC = Path(__file__).resolve().parent / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd
import streamlit as st

from nanoform import CAUTION, __version__
from nanoform import ai_orchestrator as ai
from nanoform import schema
from nanoform.carrier_recommender import recommend_carriers
from nanoform.curation import curation_queue
from nanoform.custom_materials import CustomMaterial, to_csv_rows, validate
from nanoform.database import get_database
from nanoform.designer import DesignInput, design
from nanoform.explainability import explain_all, improvement_suggestions
from nanoform.guided import run_wizard
from nanoform.optimizer import compare_designs, comparison_table, objective_profiles
from nanoform.output_ui import batch_df, confidence_badge, cqa_table_df, descriptor_df, material_card_dict
from nanoform.reporting import build_markdown_report, lab_plan
from nanoform.sanity import run_sanity
from nanoform.solvent_recommender import recommend_solvents
from nanoform.validation import validate_database


st.set_page_config(page_title="NanoFormulationDesigner", layout="wide")
db = get_database()


def _names(material_type: str) -> list[str]:
    values = db.by_type(material_type)["name"].dropna().astype(str).tolist()
    return sorted(values)


def _first(options: list[str], fallback: str = "") -> str:
    return options[0] if options else fallback


def _role_for(name: str) -> str:
    """Infer a reasonable formulation role from database flags and material type."""
    card = db.card(name)
    if card is None:
        return "component"
    if card.get("charge_inducer"):
        return "charge_inducer"
    if card.get("pegylated"):
        return "peg_lipid"
    return {
        "nonionic_surfactant": "surfactant",
        "ionic_surfactant": "surfactant",
        "phospholipid": "phospholipid",
        "sterol": "sterol",
        "bile_salt": "bile_salt",
        "solid_lipid": "solid_lipid",
        "liquid_lipid": "liquid_lipid",
        "polymer": "polymer",
        "carrier": "carrier",
    }.get(card.material_type, "component")


def _component_names() -> list[str]:
    allowed = {
        "nonionic_surfactant", "ionic_surfactant", "phospholipid", "sterol",
        "bile_salt", "solid_lipid", "liquid_lipid", "polymer", "carrier",
    }
    frame = db.materials[db.materials["material_type"].isin(allowed)]
    return sorted(frame["name"].dropna().astype(str).tolist())


def _default_components(options: list[str]) -> list[str]:
    preferred = ["Span 60", "Cholesterol", "Dicetyl phosphate"]
    return [x for x in preferred if x in options] or options[:3]


def _render_design_result(res) -> None:
    st.subheader("Executive decision")
    c1, c2, c3 = st.columns(3)
    c1.metric("NanoForm score", f"{res.nanoform_score:.2f}")
    c2.metric("Design maturity", f"DML-{res.maturity_level}")
    c3.write(res.executive_decision)

    st.subheader("CQA decision table")
    st.dataframe(cqa_table_df(res), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Descriptors")
        st.dataframe(descriptor_df(res), use_container_width=True, height=360)
    with c2:
        st.subheader("Batch mass table")
        st.dataframe(batch_df(res), use_container_width=True, height=360)

    st.subheader("Mechanistic interpretation")
    for item in explain_all(res):
        with st.expander(item.cqa_key):
            if item.positive_drivers:
                st.write("**Positive drivers:** " + "; ".join(item.positive_drivers))
            if item.risk_drivers:
                st.write("**Risk drivers:** " + "; ".join(item.risk_drivers))
            st.write("**Recommended change:** " + item.recommended_change)

    st.subheader("Improvement suggestions")
    for suggestion in improvement_suggestions(res):
        st.write("- " + suggestion)

    st.subheader("Sanity checks")
    for message in run_sanity(res):
        renderer = {"error": st.error, "warn": st.warning, "info": st.info}.get(message.severity, st.info)
        renderer(message.message)

    st.subheader("Suggested laboratory screening plan")
    for i, step in enumerate(lab_plan(res), 1):
        st.write(f"{i}. {step}")

    st.download_button(
        "Download batch table (CSV)",
        batch_df(res).to_csv(index=False),
        "batch_table.csv",
        "text/csv",
    )


DRUG_NAMES = _names("api")
SOLVENT_NAMES = _names("solvent")
CARRIER_NAMES = _names("carrier")
COMPONENT_NAMES = _component_names()

st.title("NanoFormulationDesigner")
st.caption(f"v{__version__} — materials-aware nanocarrier formulation design and decision support")
st.warning(CAUTION)

if not DRUG_NAMES or not COMPONENT_NAMES:
    st.error("The internal database did not load correctly. Check data/relational/materials.csv.")
    st.stop()

TABS = st.tabs([
    "Dashboard",
    "Guided Wizard",
    "Formulation Builder",
    "Solvent Recommender",
    "Carrier Recommender",
    "Compare Designs",
    "Material Explorer",
    "Custom Material",
    "Reports",
    "AI Orchestration",
])

with TABS[0]:
    st.header("Dashboard")
    coverage = db.coverage()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Materials", coverage["n_materials"])
    c2.metric("Property rows", coverage["n_property_rows"])
    c3.metric("Materials with MW", coverage["n_with_MW"])
    c4.metric("MW coverage", f"{coverage['fraction_with_MW'] * 100:.0f}%")

    st.subheader("Materials by type")
    st.bar_chart(pd.Series(coverage["material_types"]))

    report = validate_database(db)
    st.subheader("Database status")
    st.write(
        f"Validation: {'OK' if report['ok'] else 'ERRORS'} | "
        f"{len(report['warnings'])} warnings | "
        f"{len(report['required_missing'])} type-required gaps"
    )
    if report["warnings"]:
        with st.expander("Validation warnings"):
            for warning in report["warnings"][:50]:
                st.write("- " + str(warning))

    st.subheader("Suggested workflow")
    st.markdown(
        "1. Start with **Guided Wizard** for candidate classes.\n"
        "2. Refine composition in **Formulation Builder**.\n"
        "3. Rank process inputs through **Solvent** and **Carrier** recommenders.\n"
        "4. Export a grounded Markdown report from **Reports**."
    )

with TABS[1]:
    st.header("Guided Wizard")
    c1, c2, c3, c4 = st.columns(4)
    w_drug = c1.selectbox("Drug / API", DRUG_NAMES, key="w_drug")
    w_route = c2.selectbox("Route", schema.ROUTES, key="w_route")
    w_family = c3.selectbox("Family", schema.FORMULATION_FAMILIES, key="w_family")
    w_goal = c4.selectbox("Design goal", objective_profiles(), key="w_goal")

    if st.button("Run wizard", key="run_wizard"):
        wizard = run_wizard(w_drug, w_route, w_family, w_goal)
        st.subheader("Payload profile")
        st.json(wizard.payload_profile)
        st.subheader("Suggested material classes")
        st.write(", ".join(wizard.suggested_classes) or "—")
        for warning in wizard.route_warnings:
            st.warning(warning)
        st.subheader("Candidate starting points")
        for candidate in wizard.candidates:
            result = design(candidate)
            label = f"{candidate.formulation_id} — score {result.nanoform_score:.2f} — {result.executive_decision}"
            with st.expander(label):
                st.write(f"Process: {candidate.process_method}")
                st.write(", ".join(f"{n} {m}%" for n, _r, m in candidate.components))
                st.dataframe(cqa_table_df(result), use_container_width=True)

with TABS[2]:
    st.header("Formulation Builder")
    c1, c2, c3, c4 = st.columns(4)
    b_family = c1.selectbox("Family", schema.FORMULATION_FAMILIES, key="b_family")
    b_route = c2.selectbox("Route", schema.ROUTES, key="b_route")
    b_goal = c3.selectbox("Design goal", objective_profiles(), key="b_goal")
    b_process = c4.text_input("Process method", "thin-film hydration", key="b_process")

    c1, c2, c3, c4 = st.columns(4)
    b_drug = c1.selectbox("Drug / API", DRUG_NAMES, key="b_drug")
    b_drugmol = c2.number_input("Drug mol% of membrane", 0.0, 50.0, 5.0, key="b_drugmol")
    b_solvent = c3.selectbox("Solvent", ["(none)"] + SOLVENT_NAMES, key="b_solvent")
    b_carrier = c4.selectbox("Carrier", ["(none)"] + CARRIER_NAMES, key="b_carrier")

    c1, c2, c3 = st.columns(3)
    b_ph = c1.number_input("pH", 1.0, 12.0, 7.4, key="b_ph")
    b_temp = c2.number_input("Temperature (°C)", 0.0, 120.0, 60.0, key="b_temp")
    b_umol = c3.number_input("Total membrane (µmol)", 1.0, 5000.0, 200.0, key="b_umol")

    st.subheader("Components")
    selected = st.multiselect(
        "Select formulation components",
        COMPONENT_NAMES,
        default=_default_components(COMPONENT_NAMES),
        key="b_components",
    )
    component_rows = []
    if selected:
        columns = st.columns(min(len(selected), 4))
        default_mol = round(100.0 / len(selected), 1)
        for i, name in enumerate(selected):
            mol = columns[i % len(columns)].number_input(
                f"{name} mol%", 0.0, 100.0, default_mol, key=f"mol_{name}"
            )
            component_rows.append((name, _role_for(name), mol))

    if st.button("Design formulation", key="run_design"):
        if not component_rows:
            st.error("Select at least one component.")
        else:
            design_input = DesignInput(
                family=b_family,
                route=b_route,
                process_method=b_process,
                design_goal=b_goal,
                drug=b_drug,
                drug_mol_percent=b_drugmol,
                solvent=None if b_solvent == "(none)" else b_solvent,
                carrier=None if b_carrier == "(none)" else b_carrier,
                pH=b_ph,
                temperature_C=b_temp,
                total_membrane_umol=b_umol,
                components=component_rows,
            )
            result = design(design_input)
            st.session_state["last_result"] = result
            _render_design_result(result)

with TABS[3]:
    st.header("Solvent Recommender")
    c1, c2, c3, c4 = st.columns(4)
    s_drug = c1.selectbox("Drug / API", DRUG_NAMES, key="s_drug")
    s_route = c2.selectbox("Route", schema.ROUTES, key="s_route")
    s_process = c3.text_input("Process", "nanoprecipitation", key="s_process")
    include_blends = c4.checkbox("Include binary blends", key="s_blends")
    allowed = st.multiselect("Restrict to solvents", SOLVENT_NAMES, key="s_allowed")
    if st.button("Rank solvents", key="rank_solvents"):
        rows = recommend_solvents(
            s_drug,
            route=s_route,
            process=s_process,
            allowed=allowed or None,
            include_blends=include_blends,
            top_n=15,
        )
        out = pd.DataFrame(rows)
        st.dataframe(out, use_container_width=True)
        st.download_button("Download CSV", out.to_csv(index=False), "solvent_ranking.csv", "text/csv")

with TABS[4]:
    st.header("Carrier Recommender")
    c1, c2, c3, c4 = st.columns(4)
    cr_route = c1.selectbox("Route", schema.ROUTES, key="cr_route")
    cr_family = c2.selectbox("Family", schema.FORMULATION_FAMILIES, key="cr_family")
    cr_process = c3.text_input("Process", "lyophilization", key="cr_process")
    powder_needed = c4.checkbox("Powder/inhalation needed", key="cr_powder")
    if st.button("Rank carriers", key="rank_carriers"):
        rows = recommend_carriers(
            route=cr_route,
            family=cr_family,
            process=cr_process,
            powder_needed=powder_needed,
            top_n=15,
        )
        out = pd.DataFrame(rows)
        st.dataframe(out, use_container_width=True)
        st.download_button("Download CSV", out.to_csv(index=False), "carrier_ranking.csv", "text/csv")

with TABS[5]:
    st.header("Compare Designs")
    st.caption("Uses bundled example designs from the internal database package.")
    goal = st.selectbox("Comparison goal", objective_profiles(), key="cmp_goal")
    examples_path = db.data_dir / "examples" / "example_user_designs.csv"
    if not examples_path.exists():
        st.info("No example design table was found in the database package.")
    else:
        examples = pd.read_csv(examples_path)
        st.dataframe(examples, use_container_width=True)
        if st.button("Compare example designs", key="run_compare"):
            inputs = []
            for _, row in examples.iterrows():
                components = []
                for chunk in str(row["components"]).split("|"):
                    name, mol = chunk.rsplit(":", 1)
                    components.append((name, _role_for(name), float(mol)))
                inputs.append(
                    DesignInput(
                        formulation_id=str(row["design_id"]),
                        family=str(row["family"]),
                        route=str(row["route"]),
                        design_goal=goal,
                        drug=str(row["drug"]),
                        drug_mol_percent=float(row["drug_mol_percent"]),
                        solvent=str(row.get("solvent") or "") or None,
                        carrier=str(row.get("carrier") or "") or None,
                        pH=float(row.get("pH", 7.4)),
                        temperature_C=float(row.get("temperature_C", 25)),
                        total_membrane_umol=float(row.get("total_membrane_umol", 200)),
                        components=components,
                    )
                )
            ranked = compare_designs(inputs, goal=goal)
            st.dataframe(pd.DataFrame(comparison_table(ranked)), use_container_width=True)

with TABS[6]:
    st.header("Material Explorer")
    query = st.text_input("Search name or synonym", "", key="material_query")
    hits = db.search(query, limit=50) if query else db.materials.head(50)
    if hits.empty:
        st.info("No matching materials found.")
    else:
        st.dataframe(
            hits[["material_id", "name", "material_type", "category", "confidence_score"]],
            use_container_width=True,
            height=300,
        )
        selected_material = st.selectbox("Inspect material", hits["name"].tolist(), key="material_pick")
        card = db.card(selected_material)
        if card is not None:
            info = material_card_dict(card)
            st.subheader(f"{info['name']} · {info['material_type']} · {confidence_badge(card.confidence_score)}")
            st.write(f"Route suitability: {info['route_suitability'] or '—'}")
            if info["safety_notes"]:
                st.warning(info["safety_notes"])
            st.write("Identity", info["identity"])
            prop_rows = [{"property": key, **value} for key, value in info["properties"].items()]
            st.dataframe(pd.DataFrame(prop_rows), use_container_width=True)

with TABS[7]:
    st.header("Custom Material")
    st.caption("Session-only helper for checking which calculations a user-defined material can support.")
    c1, c2, c3 = st.columns(3)
    cm_id = c1.text_input("material_id", "USER001", key="cm_id")
    cm_name = c2.text_input("name", "My surfactant", key="cm_name")
    cm_type = c3.selectbox("material_type", schema.MATERIAL_TYPES, key="cm_type")

    properties = {}
    grid = st.columns(4)
    for i, prop in enumerate([
        "MW", "HLB", "tail_carbons", "n_tails", "headgroup_area_nm2", "formal_charge",
        "pKa", "Tm_C", "melting_point_C", "delta_D", "delta_P", "delta_H",
    ]):
        raw = grid[i % 4].text_input(prop, "", key=f"cm_{prop}")
        if raw.strip():
            try:
                properties[prop] = float(raw)
            except ValueError:
                properties[prop] = raw

    if st.button("Validate custom material", key="validate_custom"):
        custom = CustomMaterial(cm_id, cm_name, cm_type, properties=properties)
        ok, missing, enabled, disabled = validate(custom)
        if ok:
            st.success("Required fields are present for this material type.")
        else:
            st.error("Missing required fields: " + ", ".join(missing))
        st.write("**Enabled calculations:** " + (", ".join(enabled) or "none"))
        st.write("**Disabled calculations:** " + (", ".join(disabled) or "none"))
        rows = to_csv_rows(custom)
        st.download_button(
            "Export material row (CSV)",
            pd.DataFrame(rows["materials"], columns=schema.MATERIALS_COLUMNS).to_csv(index=False),
            "custom_material.csv",
            "text/csv",
        )

with TABS[8]:
    st.header("Reports")
    result = st.session_state.get("last_result")
    if result is None:
        st.info("Run a formulation design first, then return here to export the report.")
    else:
        markdown = build_markdown_report(result)
        st.download_button("Download report (Markdown)", markdown, "design_report.md", "text/markdown")
        st.markdown(markdown)

    st.subheader("Curation queue")
    queue = pd.DataFrame(curation_queue(data_dir=db.data_dir, top_n=25))
    if queue.empty:
        st.info("No unresolved curation queue was found.")
    else:
        st.dataframe(queue, use_container_width=True)

with TABS[9]:
    st.header("AI Orchestration / Advanced Reasoning")
    st.write(f"LLM integration enabled: **{ai.llm_enabled()}**")
    st.write("Routing tiers: deterministic → light → mid → frontier → fallback")
    st.markdown(
        "The optional model layer is disabled by default and is restricted to evidence bundles "
        "created by the deterministic layer. It must not invent constants or override the database."
    )

    result = st.session_state.get("last_result")
    if result is None:
        st.info("Run a design first to preview an evidence bundle.")
    else:
        bundle = ai.build_evidence_bundle(result, [m.message for m in run_sanity(result)])
        st.subheader("Evidence bundle preview")
        st.write(f"Evidence hash: `{bundle.hash()}`")
        st.json({
            "drug": bundle.drug,
            "descriptors": bundle.descriptors,
            "cqa_count": len(bundle.cqas),
            "sources": bundle.sources,
        })
        summary = ai.summarize_design(result)
        st.subheader("Summary")
        st.write(f"tier={summary.tier} · disabled={summary.disabled} · refused={summary.refused}")
        st.code(summary.text)
