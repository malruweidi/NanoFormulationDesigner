"""Solvent recommender ranking + safety behavior."""
import pytest

from nanoform.solvent_recommender import recommend_solvents


def test_ranks_and_sorts():
    recs = recommend_solvents("Curcumin", route="oral", process="nanoprecipitation")
    assert recs
    scores = [r["score"] for r in recs]
    assert scores == sorted(scores, reverse=True)


def test_ich_class_penalized():
    recs = recommend_solvents("Ibuprofen", route="pulmonary", process="nanoprecipitation", top_n=50)
    by_name = {r["solvent"]: r for r in recs}
    # A class-2 solvent for a pulmonary route should be penalized vs GRAS ethanol.
    if "Dichloromethane" in by_name and "Ethanol" in by_name:
        assert by_name["Ethanol"]["score"] >= by_name["Dichloromethane"]["score"]
    # class-2 solvents must carry a warning
    for r in recs:
        if r["ICH_class"] in ("1", "2"):
            assert "ICH class" in r["warnings"]


def test_allowed_filter():
    recs = recommend_solvents("Ibuprofen", allowed=["Ethanol", "Water"], top_n=50)
    names = {r["solvent"] for r in recs if r["type"] == "single"}
    assert names <= {"Ethanol", "Water"}


def test_blends_optional():
    recs = recommend_solvents("Curcumin", include_blends=True, top_n=30)
    assert any(r["type"] == "blend" for r in recs)


def test_unknown_drug_raises():
    with pytest.raises(ValueError):
        recommend_solvents("Nonexistent Drug XYZ")
