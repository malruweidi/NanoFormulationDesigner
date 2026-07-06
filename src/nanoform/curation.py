"""Curation helpers.

Utilities for appending to the curation log and building a prioritized curation
queue from the unresolved-missing-values report. Curation edits should flow
through here so provenance is preserved.
"""
from __future__ import annotations

import csv
import datetime as _dt
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .database import find_data_dir


def log_change(material_id: str, action: str, property_name: str = "",
               old_value: Any = "", new_value: Any = "", source_id: str = "",
               curator_note: str = "", data_dir: Optional[Path] = None) -> None:
    data_dir = Path(data_dir) if data_dir else find_data_dir()
    path = data_dir / "relational" / "curation_log.csv"
    row = [_dt.date.today().isoformat(), material_id, action, property_name,
           old_value, new_value, source_id, curator_note]
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(row)


def curation_queue(data_dir: Optional[Path] = None, top_n: int = 25) -> List[Dict[str, Any]]:
    """Highest-priority unresolved missing values."""
    data_dir = Path(data_dir) if data_dir else find_data_dir()
    path = data_dir / "internal_constants" / "unresolved_missing_values.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path).fillna("")
    order = {"high": 0, "medium": 1, "low": 2}
    df["_o"] = df["priority"].map(lambda p: order.get(str(p).lower(), 3))
    df = df.sort_values("_o").drop(columns="_o")
    return df.head(top_n).to_dict("records")
