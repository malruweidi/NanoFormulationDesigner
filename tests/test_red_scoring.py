from nanoform.designer import DesignInput, design
from nanoform.solvent_recommender import recommend_solvents


def test_red_inside_sphere_is_not_poor():
    inp = DesignInput(
        family="niosome",
        route="topical",
        process_method="thin-film hydration",
        design_goal="stability",
        drug="Dexamethasone",
        drug_mol_percent=5.0,
        solvent="Ethanol",
        components=[
            ("Span 60", "surfactant", 47.5),
            ("Cholesterol", "sterol", 47.5),
            ("Dicetyl phosphate", "charge_inducer", 5.0),
        ],
    )
    solvent = design(inp).cqa("solvent_suitability")
    assert solvent.score >= 0.55
    assert "poor" not in solvent.estimate


def test_oral_curcumin_top_rank_not_class2():
    recs = recommend_solvents("Curcumin", route="oral", process="nanoprecipitation", top_n=3)
    assert all(r["ICH_class"] != "2" for r in recs)
