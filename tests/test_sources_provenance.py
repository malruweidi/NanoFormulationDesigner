"""Every property row must carry provenance: source_id, data_quality, confidence.

Notes column must exist (it may legitimately be blank). Dimensionless properties
may have an empty unit, so unit is not required to be non-empty.
"""
import pandas as pd

from nanoform.database import get_database


def test_provenance_columns_present_and_filled():
    db = get_database()
    props = db.properties
    for col in ("material_id", "property_name", "value", "unit", "source_id",
                "data_quality", "confidence_score", "notes"):
        assert col in props.columns, f"missing column {col}"

    def blank(series):
        return series.astype(str).str.strip().eq("")

    assert not blank(props["material_id"]).any()
    assert not blank(props["property_name"]).any()
    assert not blank(props["source_id"]).any(), "some property rows lack a source_id"
    assert not blank(props["data_quality"]).any(), "some property rows lack a data_quality"
    assert not blank(props["confidence_score"]).any(), "some property rows lack a confidence_score"


def test_every_source_id_resolves():
    db = get_database()
    known = set(db.sources["source_id"])
    used = set(db.properties["source_id"])
    unknown = used - known
    assert not unknown, f"property rows reference unknown source_id(s): {unknown}"


def test_chembl_researched_drugs_have_provenance_and_no_fabrication():
    db = get_database()
    for name in ("Imatinib", "Tamoxifen", "Metformin", "Gemcitabine"):
        c = db.card(name)
        assert c is not None, f"{name} not imported"
        assert c.property_meta["MW"]["source_id"] == "S017_CHEMBL"
        assert isinstance(c.get("logP"), float)
        # Hansen parameters are NOT in ChEMBL -> must not be fabricated for these.
        assert c.get("delta_D") is None


def test_pka_enrichment_provenance_and_ionization_kernel():
    db = get_database()
    c = db.card("Rosuvastatin")
    assert c.get("acid_base") == "acid"
    assert c.property_meta["pKa"]["source_id"] == "S019_PKA_LIT"
    # The added pKa now drives the Henderson-Hasselbalch ionization kernel.
    from nanoform.descriptors import compute_descriptors, Component
    comps = [Component(db.card("Cholesterol"), "sterol", 50.0),
             Component(db.card("Span 60"), "surfactant", 50.0)]
    d = compute_descriptors(comps, drug=c, pH=7.4)
    assert d.values["drug_ionized_fraction"] > 0.9  # acid pKa 4.5 -> ~fully ionized at pH 7.4


def test_confidence_scores_in_range():
    db = get_database()
    vals = pd.to_numeric(db.properties["confidence_score"], errors="coerce").dropna()
    assert (vals >= 0).all() and (vals <= 1).all()
