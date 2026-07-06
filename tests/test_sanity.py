"""Sanity-check rule behavior."""
from nanoform.designer import DesignInput, design
from nanoform.sanity import run_sanity


def _sev(warnings, sev):
    return [w for w in warnings if w.severity == sev]


def test_niosome_without_surfactant_errors():
    inp = DesignInput(family="niosome", drug="Dexamethasone",
                      components=[("Cholesterol", "sterol", 100.0)])
    ws = run_sanity(design(inp))
    assert _sev(ws, "error")


def test_liposome_requires_phospholipid():
    inp = DesignInput(family="liposome", drug="Doxorubicin",
                      components=[("Span 60", "surfactant", 100.0)])
    ws = run_sanity(design(inp))
    assert any("phospholipid" in w.message.lower() for w in ws)


def test_transfersome_needs_edge_activator():
    inp = DesignInput(family="transfersome", drug="Ketoprofen",
                      components=[("Soy phosphatidylcholine", "phospholipid", 100.0)])
    ws = run_sanity(design(inp))
    assert any("edge activator" in w.message.lower() for w in ws)


def test_high_sterol_warns():
    inp = DesignInput(family="niosome", drug="Dexamethasone",
                      components=[("Span 60", "surfactant", 30.0), ("Cholesterol", "sterol", 70.0)])
    ws = run_sanity(design(inp))
    assert any("sterol" in w.message.lower() for w in ws)


def test_sterol_not_double_counted():
    # 39 mol% cholesterol (a sterol type) must NOT trip the >55% sterol warning.
    inp = DesignInput(family="liposome", route="parenteral", drug="Doxorubicin",
                      components=[("HSPC", "phospholipid", 56.0), ("Cholesterol", "sterol", 39.0),
                                  ("DSPE-PEG2000", "peg_lipid", 5.0)])
    ws = run_sanity(design(inp))
    assert not any("sterol fraction" in w.message.lower() for w in ws)


def test_clean_design_has_no_errors():
    inp = DesignInput(family="niosome", route="topical", drug="Dexamethasone",
                      drug_mol_percent=5.0, solvent="Ethanol",
                      components=[("Span 60", "surfactant", 47.5), ("Cholesterol", "sterol", 47.5),
                                  ("Dicetyl phosphate", "charge_inducer", 5.0)])
    ws = run_sanity(design(inp))
    assert not _sev(ws, "error")
