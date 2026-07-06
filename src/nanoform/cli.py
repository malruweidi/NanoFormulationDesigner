"""Command-line interface for NanoFormulationDesigner.

    python -m nanoform.cli search --query "Span 60"
    python -m nanoform.cli design --drug Dexamethasone --family niosome \
        --components "Span 60:surfactant:47.5|Cholesterol:sterol:47.5|Dicetyl phosphate:charge_inducer:5"
    python -m nanoform.cli recommend-solvent --drug Curcumin --route oral
    python -m nanoform.cli recommend-carrier --route pulmonary --family dry_powder_carrier
    python -m nanoform.cli wizard-candidates --drug Dexamethasone --route topical --family niosome
    python -m nanoform.cli design-report --drug Dexamethasone --family niosome --components "..."
    python -m nanoform.cli cqa-table --drug Dexamethasone --family niosome --components "..."
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Tuple

from . import __version__, CAUTION


def _fix_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # py3.7+
    except Exception:
        pass


def _parse_components(spec: str) -> List[Tuple[str, str, float]]:
    """'Name:role:mol|Name:mol' -> [(name, role, mol)]. Role defaults to 'component'."""
    out = []
    if not spec:
        return out
    for chunk in spec.split("|"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [p.strip() for p in chunk.split(":")]
        if len(parts) == 3:
            out.append((parts[0], parts[1], float(parts[2])))
        elif len(parts) == 2:
            out.append((parts[0], "component", float(parts[1])))
        else:
            raise ValueError(f"Bad component spec: {chunk!r} (use Name:role:mol)")
    return out


def _add_design_args(p: argparse.ArgumentParser):
    p.add_argument("--drug", required=True)
    p.add_argument("--family", default="niosome")
    p.add_argument("--route", default="topical")
    p.add_argument("--process", default="thin-film hydration")
    p.add_argument("--goal", default="balanced")
    p.add_argument("--components", default="", help="Name:role:mol|... ")
    p.add_argument("--drug-mol", type=float, default=5.0)
    p.add_argument("--solvent", default="")
    p.add_argument("--carrier", default="")
    p.add_argument("--ph", type=float, default=7.4)
    p.add_argument("--temp", type=float, default=25.0)
    p.add_argument("--umol", type=float, default=200.0)


def _build_input(args):
    from .designer import DesignInput
    return DesignInput(
        family=args.family, route=args.route, process_method=args.process,
        design_goal=args.goal, drug=args.drug, drug_mol_percent=args.drug_mol,
        pH=args.ph, temperature_C=args.temp, solvent=args.solvent or None,
        carrier=args.carrier or None, total_membrane_umol=args.umol,
        components=_parse_components(args.components),
    )


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_search(args) -> int:
    from .database import get_database
    db = get_database()
    df = db.search(args.query, limit=args.limit)
    if df.empty:
        print(f"No materials match {args.query!r}.")
        return 0
    for _, r in df.iterrows():
        print(f"{r['material_id']:>8}  {r['name']:<38} [{r['material_type']}]  conf={r['confidence_score']}")
    return 0


def cmd_design(args) -> int:
    from .designer import design
    res = design(_build_input(args))
    print(f"Decision : {res.executive_decision}")
    print(f"Maturity : {res.maturity_label}")
    print(f"Score    : {res.nanoform_score:.2f} / 1.00")
    print("CQAs:")
    for c in res.cqas:
        print(f"  {c.label:<36} {str(c.estimate):<24} {c.score:.2f}")
    if res.missing_values:
        print("Missing/uncertain: " + "; ".join(res.missing_values))
    print("\n" + CAUTION)
    return 0


def cmd_cqa_table(args) -> int:
    from .designer import design
    from .output_ui import cqa_table_df
    res = design(_build_input(args))
    print(cqa_table_df(res).to_string(index=False))
    return 0


def cmd_design_report(args) -> int:
    from .designer import design
    from .reporting import build_markdown_report, save_report
    res = design(_build_input(args))
    md = build_markdown_report(res)
    if args.out:
        save_report(md, args.out)
        print(f"Report written to {args.out}")
    else:
        print(md)
    return 0


def cmd_recommend_solvent(args) -> int:
    from .solvent_recommender import recommend_solvents
    allowed = [s.strip() for s in args.allowed.split("|")] if args.allowed else None
    recs = recommend_solvents(args.drug, route=args.route, process=args.process,
                              allowed=allowed, include_blends=args.blends, top_n=args.top)
    print(f"Ranked solvents for {args.drug} ({args.route}/{args.process}):")
    for r in recs:
        print(f"  {r['score']:.3f}  {r['solvent']:<42} RED={r['RED']}  ICH={r['ICH_class']}  {r['warnings']}")
    return 0


def cmd_recommend_carrier(args) -> int:
    from .carrier_recommender import recommend_carriers
    recs = recommend_carriers(route=args.route, family=args.family, process=args.process,
                              powder_needed=args.powder, top_n=args.top)
    print(f"Ranked carriers ({args.route}/{args.family}/{args.process}):")
    for r in recs:
        print(f"  {r['score']:.3f}  {r['carrier']:<34} cryo={r['cryoprotectant']}  Tg={r['Tg_C']}  {r['warnings']}")
    return 0


def cmd_wizard_candidates(args) -> int:
    from .guided import run_wizard
    from .designer import design
    out = run_wizard(args.drug, args.route, args.family, args.goal, args.drug_mol)
    print(f"Payload profile: {out.payload_profile}")
    print(f"Suggested classes: {', '.join(out.suggested_classes)}")
    for w in out.route_warnings:
        print(f"  [route] {w}")
    print(f"\nGenerated candidate starting points ({len(out.candidates)}):")
    for cand in out.candidates:
        res = design(cand)
        comp = ", ".join(f"{n} {m}%" for (n, r, m) in cand.components)
        print(f"  {cand.formulation_id}: score {res.nanoform_score:.2f} | {comp}")
    print("\nNote: candidates are temporary starting points, not stored formulations. "
          + CAUTION)
    return 0


def cmd_validate(args) -> int:
    from .validation import validate_database
    rep = validate_database()
    print(f"materials={rep['n_materials']} properties={rep['n_property_rows']} ok={rep['ok']}")
    for e in rep["errors"]:
        print("  ERROR:", e)
    for w in rep["warnings"]:
        print("  warn :", w)
    return 0 if rep["ok"] else 1


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nanoform", description="NanoFormulationDesigner CLI")
    p.add_argument("--version", action="version", version=f"nanoform {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="Search the material database")
    s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=25)
    s.set_defaults(func=cmd_search)

    d = sub.add_parser("design", help="Run a design and print CQAs")
    _add_design_args(d); d.set_defaults(func=cmd_design)

    ct = sub.add_parser("cqa-table", help="Print the CQA decision table")
    _add_design_args(ct); ct.set_defaults(func=cmd_cqa_table)

    dr = sub.add_parser("design-report", help="Generate a Markdown design report")
    _add_design_args(dr); dr.add_argument("--out", default="")
    dr.set_defaults(func=cmd_design_report)

    rs = sub.add_parser("recommend-solvent", help="Rank solvents for a drug")
    rs.add_argument("--drug", required=True); rs.add_argument("--route", default="general")
    rs.add_argument("--process", default="nanoprecipitation"); rs.add_argument("--allowed", default="")
    rs.add_argument("--blends", action="store_true"); rs.add_argument("--top", type=int, default=12)
    rs.set_defaults(func=cmd_recommend_solvent)

    rc = sub.add_parser("recommend-carrier", help="Rank carriers/cryoprotectants")
    rc.add_argument("--route", default="general"); rc.add_argument("--family", default="liposome")
    rc.add_argument("--process", default="lyophilization"); rc.add_argument("--powder", action="store_true")
    rc.add_argument("--top", type=int, default=10)
    rc.set_defaults(func=cmd_recommend_carrier)

    wc = sub.add_parser("wizard-candidates", help="Generate candidate starting points")
    wc.add_argument("--drug", required=True); wc.add_argument("--route", default="topical")
    wc.add_argument("--family", default="niosome"); wc.add_argument("--goal", default="balanced")
    wc.add_argument("--drug-mol", type=float, default=5.0, dest="drug_mol")
    wc.set_defaults(func=cmd_wizard_candidates)

    v = sub.add_parser("validate-db", help="Validate the internal database")
    v.set_defaults(func=cmd_validate)
    return p


def main(argv=None) -> int:
    _fix_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
