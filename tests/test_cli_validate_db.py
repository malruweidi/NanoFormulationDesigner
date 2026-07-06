"""`validate-db` CLI command must succeed on the shipped database."""
from nanoform import cli
from nanoform.validation import validate_database
from nanoform.database import get_database


def test_cli_validate_db_returns_zero():
    assert cli.main(["validate-db"]) == 0


def test_validation_report_ok():
    rep = validate_database(get_database())
    assert rep["ok"], rep["errors"]
    assert rep["n_materials"] >= 150
