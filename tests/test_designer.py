"""Design pipeline: descriptors, CQAs, batch masses, maturity."""
import pytest

from nanoform.designer import DesignInput, design


@pytest.fixture
def niosome():
    return DesignInput(
        family="niosome", route="topical", process_method="thin-film hydration",
        design_goal="stability", drug="Dexamethasone", drug_mol_percent=5.0,
        solvent="Ethanol", total_membrane_umol=200.0, pH=7.4, temperature_C=60.0,
        components=[("Span 60", "surfactant", 47.5), ("Cholesterol", "sterol", 47.5),
                    ("Dicetyl phosphate", "charge_inducer", 5.0)],
    )


def test_design_runs(niosome):
    r = design(niosome)
    assert 0.0 <= r.nanoform_score <= 1.0
    assert r.maturity_level in (1, 2)
    assert r.cqa("nanoform_score") is not None
    assert len(r.cqas) == 10


def test_descriptors_present(niosome):
    v = design(niosome).descriptors.values
    # Mass-weighted mixed HLB of a Span 60 / cholesterol / dicetyl-phosphate
    # niosome sits in the low, vesicle-forming range (cholesterol and the charge
    # inducer carry no HLB in the curated master, so Span 60's 4.7 dominates).
    assert 3.5 <= v["mixed_hlb"] <= 5.5
    assert v["cpp_estimate"] is not None
    assert v["morphology_tendency"] is not None
    assert v["rigidity_score"] is not None


def test_batch_masses(niosome):
    r = design(niosome)
    span = next(x for x in r.batch_table if x["component"] == "Span 60")
    # 200 umol * 47.5% = 95 umol; 95 umol * 430.62/1000 = 40.9 mg
    assert span["umol"] == pytest.approx(95.0)
    assert span["mg"] == pytest.approx(40.9, abs=0.5)
    drug = next(x for x in r.batch_table if x["role"] == "drug")
    assert drug["umol"] == pytest.approx(10.0)


def test_charge_gives_negative_zeta(niosome):
    r = design(niosome)
    zeta = r.cqa("zeta_potential")
    assert "negative" in zeta.estimate


def test_sln_flags_crystallization():
    inp = DesignInput(
        family="solid_lipid_nanoparticle", route="oral",
        process_method="high-pressure homogenization", design_goal="high_EE",
        drug="Curcumin", drug_mol_percent=8.0, solvent="Ethanol",
        components=[("Glyceryl behenate", "solid_lipid", 80.0), ("Tween 80", "surfactant", 20.0)],
    )
    r = design(inp)
    cr = r.cqa("crystallization_risk")
    assert cr.risks  # should warn about crystal lattice / no liquid lipid


def test_unresolved_material_flagged():
    inp = DesignInput(family="niosome", drug="Dexamethasone",
                      components=[("NotARealMaterial", "surfactant", 100.0)])
    r = design(inp)
    assert any("Unresolved materials" in m for m in r.missing_values)


def test_no_dependency_on_stored_formulations():
    # A design must be computable purely from materials + user composition.
    inp = DesignInput(family="liposome", route="parenteral", drug="Doxorubicin",
                      drug_mol_percent=5.0, solvent="Ethanol", carrier="Sucrose",
                      design_goal="parenteral_cautious",
                      components=[("HSPC", "phospholipid", 56.0), ("Cholesterol", "sterol", 39.0),
                                  ("DSPE-PEG2000", "peg_lipid", 5.0)])
    r = design(inp)
    assert r.nanoform_score > 0
