"""Missing/estimated values must be visible, not silently filled."""
from nanoform.database import get_database


def test_unresolved_missing_nonempty():
    db = get_database()
    df = db.unresolved_missing
    assert not df.empty
    for col in ("material_name", "material_type", "missing_property", "importance",
                "suggested_source", "priority"):
        assert col in df.columns


def test_includes_important_missing_properties():
    db = get_database()
    props = set(db.unresolved_missing["missing_property"])
    # At least some HSP/pKa/CMC-type gaps should be surfaced for curation.
    assert props & {"delta_D", "delta_P", "delta_H", "pKa", "CMC_mM", "headgroup_area_nm2"}


def test_design_surfaces_missing_for_incomplete_material():
    # A drug without HSP should surface a missing-value note, not a fabricated RED.
    from nanoform.designer import DesignInput, design
    # siRNA placeholder has no Hansen parameters in the seed DB.
    inp = DesignInput(family="niosome", route="topical", drug="siRNA (placeholder)",
                      drug_mol_percent=5.0, solvent="Ethanol",
                      components=[("Span 60", "surfactant", 50.0), ("Cholesterol", "sterol", 50.0)])
    r = design(inp)
    # RED requires drug HSP; it is absent (never invented) and the gap is surfaced.
    assert r.descriptors.values.get("drug_bilayer_red") is None
    assert any("HSP" in m for m in r.missing_values)
