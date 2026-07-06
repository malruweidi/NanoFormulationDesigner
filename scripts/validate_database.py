"""Validate the internal database and exit non-zero on hard errors."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nanoform.validation import validate_database  # noqa: E402


def main() -> int:
    rep = validate_database()
    print(f"materials       : {rep['n_materials']}")
    print(f"property rows   : {rep['n_property_rows']}")
    print(f"status          : {'OK' if rep['ok'] else 'ERRORS'}")
    for e in rep["errors"]:
        print("  ERROR:", e)
    for w in rep["warnings"]:
        print("  warn :", w)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
