"""NanoFormulationDesigner — Streamlit application.

Run with:  streamlit run app.py

Ten tabs: Dashboard, Guided Wizard, Formulation Builder, Solvent Recommender,
Carrier Recommender, Compare Designs, Material Explorer, Custom Material,
Reports, AI Orchestration.

The app is a thin presentation layer over the deterministic kernels and the
internal database. Outputs are descriptor-driven decision-support estimates that
require laboratory verification.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `streamlit run app.py` without an editable install.
SRC = Path(__file__).resolve().parent / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd
import streamlit as st

from nanoform import CAUTION, __version__
from nanoform.database import get_database
from nanoform.designer import DesignInput, design
from nanoform.solvent_recommender import recommend_solvents
from nanoform.carrier_recommender import recommend_carriers
from nanoform.guided import run_wizard
from nanoform.optimizer import compare_designs, comparison_table, objective_profiles
from nanoform.sanity import run_sanity
from nanoform.reporting import build_markdown_report, lab_plan
from nanoform.explainability import improvement_suggestions, explain_all
from nanoform.output_ui import (cqa_table_df, descriptor_df, batch_df,
                                material_card_dict, confidence_badge)
from nanoform.custom_materials import CustomMaterial, validate, to_csv_rows
from nanoform.validation import validate_database
from nanoform.curation import curation_queue
from nanoform import schema
from nanoform import ai_orchestrator as ai

st.set_page_config(page_title="NanoFormulationDesigner", layout="wide")
db = get_database()


def _names(mtype):
    return sorted(db.by_type(mtype)["name"].tolist())


def _role_for(name: str) -> str:
    """Infer a component role from its material type (UI convenience)."""
    card = db.card(name)
    if card is None:
        return "component"
    if card.get("charge_inducer"):
        return "charge_inducer"
    if card.get("pegylated"):
        return "peg_lipid"
    return {
        "nonionic_surfactant": "surfactant", "ionic_surfactant": "surfactant",
        "phospholipid": "phospholipid", "sterol": "sterol", "bile_salt": "bile_salt",
        "solid_lipid": "solid_lipid", "liquid_lipid": "liquid_lipid",
        "polymer": "polymer", "carrier": "carrier",
    }.get(card.material_type, "component")


ALL_COMPONENT_NAMES = sorted(db.materials[
    db.materials["material_type"].isin([
        "nonionic_surfactant", "ionic_surfactant", "phospholipid", "sterol",
        "bile_salt", "solid_lipid", "liquid_lipid", "polymer", "carrier",
    ])]["name"].tolist())
DRUG_NAMES = _names("api")
SOLVENT_NAMES = _names("solvent")
CARRIER_NAMES = _names("carrier")

st.title("NanoFormulationDesigner")
st.caption(f"v{__version__} — materials-aware nanocarrier formulation design & decision support")
st.warning(CAUTION)

tabs = st.tabs([
    "Dashboard", "Guided Wizard", "Formulation Builder", "Solvent Recommender",
    "Carrier Recommender", "Compare Designs", "Material Explorer",
    "Custom Material", "Reports", "AI Orchestration",
])

# --------------------------------------------------------------------------- #
# 1. Dashboard
# --------------------------------------------------------------------------- #
with tabs[0]:
    st.header("Dashboard")
    cov = db.coverage()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Materials", cov["n_materials"])
    c2.metric("Property rows", cov["n_property_rows"])
    c3.metric("With MW", cov["n_with_MW"])
    c4.metric("MW coverage", f"{cov['fraction_with_MW']*100:.0f}%")
    st.subheader("Materials by type")
    st.bar_chart(pd.Series(cov["material_types"]))
    rep = validate_database(db)
    st.subheader("Database status")
    st.write(f"Validation: {'OK' if rep['ok'] else 'ERRORS'} | "
             f"{len(rep['warnings'])} warnings, {len(rep['required_missing'])} type-required gaps")
    st.subheader("Quick workflow")
    st.markdown(
        "1. **Guided Wizard** — pick a drug/route/family to get starting candidates.\n"
        "2. **Formulation Builder** — refine your own composition and read the CQA card.\n"
        "3. **Solvent / Carrier Recommender** — rank process materials.\n"
        "4. **Compare Designs** — rank several candidates under a design goal.\n"
        "5. **Reports** — export a grounded Markdown report.")
    st.info("Scientific caution: outputs are descriptor-driven estimates. Nothing here is a "
            "validated predictor; all candidates require laboratory verification.")

# --------------------------------------------------------------------------- #
# 2. Guided Wizard
# --------------------------------------------------------------------------- #
with tabs[1]:
    st.header("Guided Wizard")
    col = st.columns(4)
    w_drug = col[0].selectbox("Drug / API", DRUG_NAMES, key="w_drug")
    w_route = col[1].selectbox("Route", schema.ROUTES, key="w_route")
    w_family = col[2].selectbox("Family", schema.FORMULATION_FAMILIES, key="w_family")
    w_goal = col[3].selectbox("Design goal", objective_profiles(), key="w_goal")
    if st.button("Run wizard", key="run_wizard"):
        out = run_wizard(w_drug, w_route, w_family, w_goal)
        st.subheader("Payload profile")
        st.json(out.payload_profile)
        st.subheader("Suggested material classes")
        st.write(", ".join(out.suggested_classes) or "—")
        if out.route_warnings:
            st.subheader("Route warnings")
            for wmsg in out.route_warnings:
                st.warning(wmsg)
        st.subheader("Candidate starting points (temporary — not stored)")
        for cand in out.candidates:
            res = design(cand)
            comp = ", ".join(f"{n} {m}%" for (n, r, m) in cand.components)
            with st.expander(f"{cand.formulation_id} — score {res.nanoform_score:.2f} — {res.executive_decision}"):
                st.write(f"Process: {cand.process_method}")
                st.write(f"Components: {comp}")
                st.dataframe(cqa_table_df(res), use_container_width=True)

# --------------------------------------------------------------------------- #
# 3. Formulation Builder
# --------------------------------------------------------------------------- #
with tabs[2]:
    st.header("Formulation Builder")
    c = st.columns(4)
    b_family = c[0].selectbox("Family", schema.FORMULATION_FAMILIES, key="b_family")
    b_route = c[1].selectbox("Route", schema.ROUTES, key="b_route")
    b_goal = c[2].selectbox("Design goal", objective_profiles(), key="b_goal")
    b_process = c[3].text_input("Process method", "thin-film hydration", key="b_process")
    c = st.columns(4)
    b_drug = c[0].selectbox("Drug / API", DRUG_NAMES, key="b_drug")
    b_drugmol = c[1].number_input("Drug mol% of membrane", 0.0, 50.0, 5.0, key="b_drugmol")
    b_solvent = c[2].selectbox("Solvent", ["(none)"] + SOLVENT_NAMES, key="b_solvent")
    b_carrier = c[3].selectbox("Carrier", ["(none)"] + CARRIER_NAMES, key="b_carrier")
    c = st.columns(3)
    b_ph = c[0].number_input("pH", 1.0, 12.0, 7.4, key="b_ph")
    b_temp = c[1].number_input("Temperature (C)", 0.0, 120.0, 60.0, key="b_temp")
    b_umol = c[2].number_input("Total membrane umol", 1.0, 5000.0, 200.0, key="b_umol")

    st.subheader("Components")
    picked = st.multiselect("Select components", ALL_COMPONENT_NAMES,
                            default=["Span 60", "Cholesterol", "Dicetyl phosphate"], key="b_comps")
    comp_rows = []
    if picked:
        cols = st.columns(min(len(picked), 4) or 1)
        for i, name in enumerate(picked):
            mol = cols[i % len(cols)].number_input(f"{name} mol%", 0.0, 100.0,
                                                   round(100 / len(picked), 1), key=f"mol_{name}")
            comp_rows.append((name, _role_for(name), mol))

    if st.button("Design", key="run_design") and comp_rows:
        inp = DesignInput(
            family=b_family, route=b_route, process_method=b_process, design_goal=b_goal,
            drug=b_drug, drug_mol_percent=b_drugmol,
            solvent=None if b_solvent == "(none)" else b_solvent,
            carrier=None if b_carrier == "(none)" else b_carrier,
            pH=b_ph, temperature_C=b_temp, total_membrane_umol=b_umol, components=comp_rows,
        )
        res = design(inp)
        st.session_state["last_result"] = res

        st.subheader("Executive decision")
        m = st.columns(3)
        m[0].metric("NanoForm score", f"{res.nanoform_score:.2f}")
        m[1].metric("Maturity", f"DML-{res.maturity_level}")
        m[2].write(res.executive_decision)

        st.subheader("CQA decision table")
        st.dataframe(cqa_table_df(res), use_container_width=True)
        colA, colB = st.columns(2)
        with colA:
            st.subheader("Descriptors")
            st.dataframe(descriptor_df(res), use_container_width=True, height=360)
        with colB:
            st.subheader("Batch mass table")
            st.dataframe(batch_df(res), use_container_width=True, height=360)

        st.subheader("Why (drivers / risks / recommended change)")
        for e in explain_all(res):
            with st.expander(e.cqa_key):
                if e.positive_drivers:
                    st.write("**Positive:** " + "; ".join(e.positive_drivers))
                if e.risk_drivers:
                    st.write("**Risks:** " + "; ".join(e.risk_drivers))
                st.write("**Change:** " + e.recommended_change)

        st.subheader("Improvement suggestions")
        for s in improvement_suggestions(res):
            st.write("- " + s)
        st.subheader("Sanity checks")
        for wmsg in run_sanity(res):
            {"error": st.error, "warn": st.warning, "info": st.info}[wmsg.severity](wmsg.message)
        st.subheader("Suggested lab plan")
        for i, step in enumerate(lab_plan(res), 1):
            st.write(f"{i}. {step}")
        st.download_button("Download batch table (CSV)", batch_df(res).to_csv(index=False),
                           "batch_table.csv", "text/csv")

# --------------------------------------------------------------------------- #
# 4. Solvent Recommender
# --------------------------------------------------------------------------- #
with tabs[3]:
    st.header("Solvent Recommender")
    c = st.columns(4)
    s_drug = c[0].selectbox("Drug / API", DRUG_NAMES, key="s_drug")
    s_route = c[1].selectbox("Route", schema.ROUTES, key="s_route")
    s_proc = c[2].text_input("Process", "nanoprecipitation", key="s_proc")
    s_blend = c[3].checkbox("Include binary blends", key="s_blend")
    s_allowed = st.multiselect("Restrict to solvents (optional)", SOLVENT_NAMES, key="s_allowed")
    if st.button("Rank solvents", key="run_solv"):
        recs = recommend_solvents(s_drug, route=s_route, process=s_proc,
                                  allowed=s_allowed or None, include_blends=s_blend, top_n=15)
        df = pd.DataFrame(recs)
        st.dataframe(df, use_container_width=True)
        st.download_button("Download (CSV)", df.to_csv(index=False), "solvents.csv", "text/csv")

# --------------------------------------------------------------------------- #
# 5. Carrier Recommender
# --------------------------------------------------------------------------- #
with tabs[4]:
    st.header("Carrier Recommender")
    c = st.columns(4)
    cr_route = c[0].selectbox("Route", schema.ROUTES, key="cr_route")
    cr_family = c[1].selectbox("Family", schema.FORMULATION_FAMILIES, key="cr_family")
    cr_proc = c[2].text_input("Process", "lyophilization", key="cr_proc")
    cr_powder = c[3].checkbox("Powder / inhalation needed", key="cr_powder")
    if st.button("Rank carriers", key="run_carr"):
        recs = recommend_carriers(route=cr_route, family=cr_family, process=cr_proc,
                                  powder_needed=cr_powder, top_n=15)
        df = pd.DataFrame(recs)
        st.dataframe(df, use_container_width=True)
        st.download_button("Download (CSV)", df.to_csv(index=False), "carriers.csv", "text/csv")

# --------------------------------------------------------------------------- #
# 6. Compare Designs
# --------------------------------------------------------------------------- #
with tabs[5]:
    st.header("Compare Designs")
    st.caption("Load the bundled example designs and rank them under a chosen goal.")
    goal = st.selectbox("Design goal", objective_profiles(), key="cmp_goal")
    ex_path = Path(__file__).resolve().parent / "data" / "examples" / "example_user_designs.csv"
    if ex_path.exists():
        ex = pd.read_csv(ex_path)
        st.dataframe(ex, use_container_width=True)
        if st.button("Compare example designs", key="run_cmp"):
            inputs = []
            for _, r in ex.iterrows():
                comps = []
                for chunk in str(r["components"]).split("|"):
                    name, mol = chunk.rsplit(":", 1)
                    comps.append((name, _role_for(name), float(mol)))
                inputs.append(DesignInput(
                    family=r["family"], route=r["route"], drug=r["drug"],
                    drug_mol_percent=float(r["drug_mol_percent"]),
                    solvent=str(r.get("solvent") or "") or None,
                    carrier=str(r.get("carrier") or "") or None,
                    total_membrane_umol=float(r.get("total_membrane_umol", 200)),
                    pH=float(r.get("pH", 7.4)), temperature_C=float(r.get("temperature_C", 25)),
                    design_goal=goal, components=comps, formulation_id=r["design_id"]))
            ranked = compare_designs(inputs, goal=goal)
            st.dataframe(pd.DataFrame(comparison_table(ranked)), use_container_width=True)

# --------------------------------------------------------------------------- #
# 7. Material Explorer
# --------------------------------------------------------------------------- #
with tabs[6]:
    st.header("Material Explorer")
    q = st.text_input("Search name or synonym", "", key="mx_q")
    hits = db.search(q, limit=50) if q else db.materials.head(50)
    st.dataframe(hits[["material_id", "name", "material_type", "category", "confidence_score"]],
                 use_container_width=True, height=300)
    pick = st.selectbox("Inspect material", hits["name"].tolist() if not hits.empty else [], key="mx_pick")
    if pick:
        card = db.card(pick)
        info = material_card_dict(card)
        st.subheader(f"{info['name']}  ·  {info['material_type']}  ·  {confidence_badge(card.confidence_score)}")
        st.write(f"Route suitability: {info['route_suitability'] or '—'}")
        if info["safety_notes"]:
            st.warning(info["safety_notes"])
        st.write("Identity:", info["identity"])
        prop_rows = [{"property": k, **d} for k, d in info["properties"].items()]
        st.dataframe(pd.DataFrame(prop_rows), use_container_width=True)
        est = [k for k, d in info["properties"].items() if d["quality"] == "estimated"]
        if est:
            st.info("Estimated (low-confidence) properties: " + ", ".join(est))

# --------------------------------------------------------------------------- #
# 8. Custom Material
# --------------------------------------------------------------------------- #
with tabs[7]:
    st.header("Custom Material (session only)")
    c = st.columns(3)
    cm_id = c[0].text_input("material_id", "USER001", key="cm_id")
    cm_name = c[1].text_input("name", "My surfactant", key="cm_name")
    cm_type = c[2].selectbox("material_type", schema.MATERIAL_TYPES, key="cm_type")
    st.caption("Enter any known properties (leave blank if unknown). Blank = disabled calculation.")
    props = {}
    grid = st.columns(4)
    for i, p in enumerate(["MW", "HLB", "tail_carbons", "n_tails", "headgroup_area_nm2",
                           "formal_charge", "pKa", "Tm_C", "melting_point_C",
                           "delta_D", "delta_P", "delta_H"]):
        val = grid[i % 4].text_input(p, "", key=f"cm_{p}")
        if val.strip():
            try:
                props[p] = float(val)
            except ValueError:
                props[p] = val
    if st.button("Validate", key="cm_validate"):
        mat = CustomMaterial(cm_id, cm_name, cm_type, properties=props)
        ok, missing, enabled, disabled = validate(mat)
        (st.success if ok else st.error)(
            "All required fields present." if ok else "Missing required: " + ", ".join(missing))
        st.write("**Enabled calculations:** " + (", ".join(enabled) or "none"))
        st.write("**Disabled (missing data):** " + (", ".join(disabled) or "none"))
        rows = to_csv_rows(mat)
        st.download_button("Export material row (CSV)",
                           pd.DataFrame(rows["materials"], columns=schema.MATERIALS_COLUMNS).to_csv(index=False),
                           "custom_material.csv", "text/csv")

# --------------------------------------------------------------------------- #
# 9. Reports
# --------------------------------------------------------------------------- #
with tabs[8]:
    st.header("Reports")
    res = st.session_state.get("last_result")
    if res is None:
        st.info("Run a design in the Formulation Builder first, then return here.")
    else:
        md = build_markdown_report(res)
        st.download_button("Download report (Markdown)", md, "design_report.md", "text/markdown")
        st.markdown(md)
    st.subheader("Curation queue (highest-priority missing values)")
    st.dataframe(pd.DataFrame(curation_queue(top_n=25)), use_container_width=True)

# --------------------------------------------------------------------------- #
# 10. AI Orchestration
# --------------------------------------------------------------------------- #
with tabs[9]:
    st.header("AI Orchestration / Advanced Reasoning (optional)")
    enabled = ai.llm_enabled()
    st.write(f"LLM integration enabled: **{enabled}** "
             f"(set ANTHROPIC_API_KEY and install `anthropic` to enable)")
    st.write("Routing tiers: deterministic - light - mid - frontier (Fable 5) - fallback")
    st.markdown(
        "- The LLM is **not** the source of scientific constants.\n"
        "- The database and deterministic kernels are authoritative.\n"
        "- LLM outputs are interpretive and grounded against an evidence bundle.\n"
        "- Benign life-science refusals fall back to a secondary model or deterministic output.")
    res = st.session_state.get("last_result")
    if res is not None:
        bundle = ai.build_evidence_bundle(res, [w.message for w in run_sanity(res)])
        st.subheader("Evidence bundle preview (minimal grounded context)")
        st.write(f"Evidence hash: `{bundle.hash()}`")
        st.json({"drug": bundle.drug, "descriptors": bundle.descriptors,
                 "cqas": bundle.cqas, "missing_values": bundle.missing_values,
                 "sources": bundle.sources})
        summary = ai.summarize_design_with_llm(res, client=None,
                                               sanity_messages=[w.message for w in run_sanity(res)])
        st.subheader("Summary (deterministic fallback shown when LLM disabled)")
        st.write(f"tier={summary.tier} · disabled={summary.disabled} · refused={summary.refused}")
        st.code(summary.text)
    else:
        st.info("Run a design first to preview an evidence bundle.")
