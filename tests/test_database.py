"""Database loading, schema, aliasing, search, and validation."""
import pytest

from nanoform import schema
from nanoform.database import get_database
from nanoform.validation import validate_database


@pytest.fixture(scope="module")
def db():
    return get_database()


def test_required_columns(db):
    for col in schema.MATERIALS_COLUMNS:
        assert col in db.materials.columns
    for col in schema.MATERIAL_PROPERTIES_COLUMNS:
        assert col in db.properties.columns


def test_no_duplicate_material_ids(db):
    ids = db.materials["material_id"].tolist()
    assert len(ids) == len(set(ids))


def test_meaningful_seed_size(db):
    assert len(db.materials) >= 150
    # coverage across classes
    types = set(db.materials["material_type"])
    for t in ("api", "nonionic_surfactant", "phospholipid", "sterol",
              "bile_salt", "solid_lipid", "solvent", "carrier", "polymer"):
        assert t in types


def test_property_aliasing():
    assert schema.canonical_property("molecular_weight") == "MW"
    assert schema.canonical_property("chain_length") == "tail_carbons"
    assert schema.canonical_property("a0") == "headgroup_area_nm2"


def test_search_and_synonym(db):
    assert not db.search("Span 60").empty
    # resolve by synonym
    assert db.resolve_id("SDS") == db.resolve_id("Sodium lauryl sulfate")


def test_card_and_missing(db):
    card = db.card("Span 60")
    assert card is not None
    assert card.get("HLB") == pytest.approx(4.7)
    assert card.get("tail_carbons") == 18
    assert card.missing(["nonexistent_prop"]) == ["nonexistent_prop"]


def test_ich_class_is_categorical(db):
    dcm = db.card("Dichloromethane")
    assert dcm.get("ICH_class") == "2"  # not 2.0


def test_validation_passes(db):
    rep = validate_database(db)
    assert rep["ok"], rep["errors"]
