"""Every module imports, and the deterministic kernels give known values."""
import importlib

import pytest

MODULES = [
    "nanoform", "nanoform.equations", "nanoform.schema", "nanoform.database",
    "nanoform.descriptors", "nanoform.designer", "nanoform.solvent_recommender",
    "nanoform.carrier_recommender", "nanoform.guided", "nanoform.sanity",
    "nanoform.explainability", "nanoform.optimizer", "nanoform.reporting",
    "nanoform.output_ui", "nanoform.custom_materials", "nanoform.validation",
    "nanoform.curation", "nanoform.ai_orchestrator", "nanoform.cli",
]


@pytest.mark.parametrize("mod", MODULES)
def test_import(mod):
    importlib.import_module(mod)


def test_kernel_known_values():
    from nanoform import equations as eq
    assert eq.mg_from_umol(200, 386.65) == pytest.approx(77.33, rel=1e-3)
    assert eq.mixed_hlb([1, 1], [4.7, 15.0]) == pytest.approx(9.85, rel=1e-3)
    # CPP of a single-tail C16 with a0=0.6 nm^2 -> vesicle/micelle regime
    v = eq.tanford_v_nm3(16, 1)
    lc = eq.tanford_l_nm(16)
    cpp = eq.cpp_value(v, 0.6, lc)
    assert 0.2 < cpp < 1.0
    # Hansen distance to self is zero; RED accordingly zero
    assert eq.hansen_distance(18, 8, 10, 18, 8, 10) == 0.0
    # Neutral fraction of an acid at pH == pKa is 0.5
    assert eq.neutral_fraction(4.4, 4.4, is_acid=True) == pytest.approx(0.5)
    # Base is more ionized below its pKa
    assert eq.ionized_fraction(8.0, 6.0, is_acid=False) > 0.9
