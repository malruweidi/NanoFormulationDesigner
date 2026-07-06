"""CLI smoke tests — every subcommand returns 0 and prints something."""
import pytest

from nanoform import cli


def test_search(capsys):
    assert cli.main(["search", "--query", "Span 60"]) == 0
    assert "Span 60" in capsys.readouterr().out


def test_design(capsys):
    rc = cli.main([
        "design", "--drug", "Dexamethasone", "--family", "niosome", "--route", "topical",
        "--solvent", "Ethanol",
        "--components", "Span 60:surfactant:47.5|Cholesterol:sterol:47.5|Dicetyl phosphate:charge_inducer:5",
    ])
    assert rc == 0
    assert "NanoForm composite score" in capsys.readouterr().out


def test_cqa_table(capsys):
    rc = cli.main([
        "cqa-table", "--drug", "Curcumin", "--family", "solid_lipid_nanoparticle",
        "--components", "Glyceryl behenate:solid_lipid:80|Tween 80:surfactant:20",
    ])
    assert rc == 0
    assert "Encapsulation" in capsys.readouterr().out


def test_recommend_solvent(capsys):
    assert cli.main(["recommend-solvent", "--drug", "Curcumin", "--route", "oral"]) == 0
    assert "Ranked solvents" in capsys.readouterr().out


def test_recommend_carrier(capsys):
    assert cli.main(["recommend-carrier", "--route", "pulmonary",
                     "--family", "dry_powder_carrier"]) == 0
    assert "Ranked carriers" in capsys.readouterr().out


def test_wizard_candidates(capsys):
    assert cli.main(["wizard-candidates", "--drug", "Dexamethasone",
                     "--route", "topical", "--family", "niosome"]) == 0
    assert "candidate starting points" in capsys.readouterr().out


def test_design_report(capsys, tmp_path):
    out = tmp_path / "r.md"
    rc = cli.main([
        "design-report", "--drug", "Dexamethasone", "--family", "niosome",
        "--components", "Span 60:surfactant:50|Cholesterol:sterol:50", "--out", str(out),
    ])
    assert rc == 0
    assert out.exists() and "Scientific limitations" in out.read_text(encoding="utf-8")


def test_validate_db():
    assert cli.main(["validate-db"]) == 0


def test_component_parser():
    parsed = cli._parse_components("A:role:1.5|B:2")
    assert parsed == [("A", "role", 1.5), ("B", "component", 2.0)]
