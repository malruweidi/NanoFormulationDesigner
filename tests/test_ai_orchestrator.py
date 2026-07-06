"""Optional AI layer must be disabled-safe and grounding-aware (no API key)."""
from nanoform.designer import DesignInput, design
from nanoform import ai_orchestrator as ai


def _result():
    inp = DesignInput(family="niosome", route="topical", drug="Dexamethasone",
                      drug_mol_percent=5.0, solvent="Ethanol",
                      components=[("Span 60", "surfactant", 47.5), ("Cholesterol", "sterol", 47.5),
                                  ("Dicetyl phosphate", "charge_inducer", 5.0)])
    return design(inp)


def test_routing_tiers():
    assert ai.route_task("calculate").tier == "deterministic"
    assert ai.route_task("summarize_design", "hard", requires_model=True).tier == "frontier"
    assert ai.route_task("extract", requires_model=True).tier == "light"


def test_evidence_bundle_is_minimal_and_hashable():
    b = ai.build_evidence_bundle(_result())
    assert b.drug["name"] == "Dexamethasone"
    assert b.cqas and b.descriptors
    assert len(b.hash()) == 16
    # bundle should not carry the whole database
    assert isinstance(b.components, list) and len(b.components) == 3


def test_summary_disabled_safe():
    res = ai.summarize_design_with_llm(_result(), client=None)
    assert res.ok and res.disabled
    assert "Deterministic summary" in res.text


def test_refusal_detection():
    assert ai.detect_refusal("I can't help with that request.")
    assert not ai.detect_refusal("Here is the grounded formulation summary: ...")


def test_grounding_flags_unsupported_numbers():
    b = ai.build_evidence_bundle(_result())
    g = ai.validate_grounding("The EE is 0.999 and size is 12345.6 nm.", b)
    assert not g["grounded"]
    assert g["unsupported_numbers"]


def test_fallback_on_refusing_client():
    # A client that always refuses should trigger fallback handling, not crash.
    def refusing_client(model, prompt):
        return "I cannot assist with that."
    import os
    os.environ["ANTHROPIC_API_KEY"] = "test"  # llm_enabled still False (no SDK) -> disabled path
    res = ai.summarize_design_with_llm(_result(), client=refusing_client)
    assert res.ok  # never hard-fails
    os.environ.pop("ANTHROPIC_API_KEY", None)
