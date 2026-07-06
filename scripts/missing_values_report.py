"""Print the highest-priority unresolved missing database values."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nanoform.curation import curation_queue  # noqa: E402


def main() -> int:
    rows = curation_queue(data_dir=ROOT / "data", top_n=40)
    if not rows:
        print("No unresolved missing values recorded.")
        return 0
    print(f"Top {len(rows)} unresolved missing values (by priority):\n")
    for r in rows:
        print(f"  [{r['priority']:>6}] {r['material_name']:<34} needs {r['missing_property']:<22} "
              f"-> {r['suggested_source']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
