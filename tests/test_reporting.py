"""Report generation + groundedness (limitations section, no overclaiming)."""
from nanoform.designer import DesignInput, design
from nanoform.reporting import build_markdown_report, lab_plan


def _result():
    inp = DesignInput(family="niosome", route="topical", drug="Dexamethasone",
                      drug_mol_percent=5.0, solvent="Ethanol", design_goal="stability",
                      components=[("Span 60", "surfactant", 47.5), ("Cholesterol", "sterol", 47.5),
                                  ("Dicetyl phosphate", "charge_inducer", 5.0)])
    return design(inp)


def test_report_sections_present():
    md = build_markdown_report(_result())
    for section in ["Executive decision", "CQA decision table", "Batch mass table",
                    "Sanity checks", "Scientific limitations", "lab screening plan"]:
        assert section in md


def test_report_states_caution_not_overclaim():
    md = build_markdown_report(_result()).lower()
    assert "require" in md and "verification" in md
    # Must not use forbidden absolute claims.
    for banned in ["guaranteed", "optimal formulation", "validated predictor"]:
        assert banned not in md


def test_lab_plan_nonempty():
    steps = lab_plan(_result())
    assert len(steps) >= 5
    assert any("dls" in s.lower() or "light scattering" in s.lower() for s in steps)
