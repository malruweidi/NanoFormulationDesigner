"""Print the database coverage summary (per material type/category)."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    path = ROOT / "data" / "internal_constants" / "coverage_summary.csv"
    if not path.exists():
        print("coverage_summary.csv not found — run scripts/build_database.py first.")
        return 1
    df = pd.read_csv(path)
    print(df.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
