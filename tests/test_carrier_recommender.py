"""Carrier / cryoprotectant recommender behavior."""
from nanoform.carrier_recommender import recommend_carriers


def test_ranks_and_sorts():
    recs = recommend_carriers(route="oral", family="liposome", process="lyophilization")
    assert recs
    scores = [r["score"] for r in recs]
    assert scores == sorted(scores, reverse=True)


def test_trehalose_top_for_lyophilization():
    recs = recommend_carriers(route="parenteral", family="liposome", process="lyophilization", top_n=3)
    top_names = [r["carrier"] for r in recs]
    assert "Trehalose" in top_names  # best glass former in the seed set


def test_leucine_favored_for_dpi():
    recs = recommend_carriers(route="pulmonary", family="dry_powder_carrier",
                              process="spray drying", powder_needed=True, top_n=5)
    names = [r["carrier"] for r in recs]
    # A leucine grade (spelled "L-leucine" / "Leucine for inhalation powders" in
    # the curated master) must appear among the top DPI carriers.
    assert any("leucine" in n.lower() for n in names), names


def test_insoluble_carrier_penalized_parenteral():
    recs = recommend_carriers(route="parenteral", family="liposome", process="lyophilization", top_n=50)
    mcc = next((r for r in recs if r["carrier"] == "Microcrystalline cellulose"), None)
    if mcc:
        assert mcc["warnings"]
