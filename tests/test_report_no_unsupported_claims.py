"""Reports must use caution language and must not overclaim."""
import pytest

from nanoform.designer import DesignInput, design
from nanoform.reporting import build_markdown_report

BANNED = ["guaranteed", "optimal formulation", "validated predictor",
          "best formulation"]


@pytest.fixture(scope="module")
def report():
    inp = DesignInput(
        family="liposome", route="parenteral", design_goal="parenteral_cautious",
        drug="Doxorubicin", drug_mol_percent=5.0, solvent="Ethanol", carrier="Sucrose",
        components=[("HSPC", "phospholipid", 56.0), ("Cholesterol", "sterol", 39.0),
                    ("DSPE-PEG2000", "peg_lipid", 5.0)],
    )
    return build_markdown_report(design(inp))


def test_no_banned_overclaims(report):
    low = report.lower()
    for phrase in BANNED:
        assert phrase not in low, f"report overclaims: {phrase!r}"


def test_has_caution_language(report):
    low = report.lower()
    assert "require" in low and "verification" in low
    assert "descriptor-driven" in low


def test_has_limitations_and_lab_plan(report):
    assert "Scientific limitations" in report
    assert "lab screening plan" in report.lower() or "screening plan" in report.lower()
