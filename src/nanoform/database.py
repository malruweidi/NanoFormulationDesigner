"""Retrieval / database layer.

Loads the internal relational CSVs, folds property names to canonical form,
and provides material lookup, property retrieval, coverage, and provenance.

The database is local and internally stored. No live public dataset is queried
at runtime. All records carry provenance (`source_id`) and `confidence_score`.
"""
from __future__ import annotations

import functools
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from . import schema


# --------------------------------------------------------------------------- #
# Locating the data directory
# --------------------------------------------------------------------------- #
def find_data_dir(start: Optional[Path] = None) -> Path:
    """Locate the repository `data/` directory.

    Order: NANOFORM_DATA_DIR env var, then walk upward from this file / cwd
    looking for a `data/relational/materials.csv`.
    """
    env = os.environ.get("NANOFORM_DATA_DIR")
    if env:
        p = Path(env)
        if (p / "relational" / "materials.csv").exists():
            return p
    candidates = []
    here = Path(__file__).resolve()
    candidates.extend(here.parents)
    if start:
        candidates.insert(0, Path(start).resolve())
    candidates.append(Path.cwd())
    for base in candidates:
        cand = base / "data"
        if (cand / "relational" / "materials.csv").exists():
            return cand
        # also allow base itself being the data dir
        if (base / "relational" / "materials.csv").exists():
            return base
    raise FileNotFoundError(
        "Could not locate data/relational/materials.csv. "
        "Run scripts/build_database.py or set NANOFORM_DATA_DIR."
    )


@dataclass
class MaterialCard:
    """A resolved material with identity, canonical properties, and provenance."""

    material_id: str
    name: str
    material_type: str
    category: str
    identity: Dict[str, Any] = field(default_factory=dict)
    properties: Dict[str, float] = field(default_factory=dict)  # canonical -> value
    property_meta: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    confidence_score: float = 0.0
    route_suitability: str = ""
    safety_notes: str = ""

    def get(self, prop: str, default: Any = None) -> Any:
        return self.properties.get(schema.canonical_property(prop), default)

    def missing(self, wanted: List[str]) -> List[str]:
        return [p for p in wanted if self.get(p) is None]


class Database:
    """In-memory view over the internal CSV database."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = Path(data_dir) if data_dir else find_data_dir()
        self.rel = self.data_dir / "relational"
        self.const = self.data_dir / "internal_constants"
        self.materials = pd.read_csv(self.rel / "materials.csv", dtype=str).fillna("")
        self.properties = pd.read_csv(self.rel / "material_properties.csv", dtype=str).fillna("")
        self.sources = pd.read_csv(self.rel / "sources.csv", dtype=str).fillna("")
        # Derived internal-constant tables (loaded if present; not required for design).
        self.wide = self._maybe_read(self.const / "internal_constants_wide.csv")
        self.coverage_summary = self._maybe_read(self.const / "coverage_summary.csv")
        self.unresolved_missing = self._maybe_read(self.const / "unresolved_missing_values.csv")
        # Fold property names to canonical form once.
        self.properties["property_name"] = self.properties["property_name"].map(
            schema.canonical_property
        )
        self._by_id = {r["material_id"]: r for _, r in self.materials.iterrows()}
        self._name_index = self._build_name_index()

    @staticmethod
    def _maybe_read(path: Path) -> pd.DataFrame:
        """Read a CSV as strings if it exists, else return an empty DataFrame."""
        if path.exists():
            return pd.read_csv(path, dtype=str).fillna("")
        return pd.DataFrame()

    # ---- indexing -------------------------------------------------------- #
    def _build_name_index(self) -> Dict[str, str]:
        idx: Dict[str, str] = {}
        for _, row in self.materials.iterrows():
            mid = row["material_id"]
            idx[row["name"].strip().lower()] = mid
            for syn in str(row.get("synonyms", "")).split(";"):
                syn = syn.strip().lower()
                if syn:
                    idx.setdefault(syn, mid)
        return idx

    # ---- lookups --------------------------------------------------------- #
    def search(self, query: str, limit: int = 25) -> pd.DataFrame:
        """Case-insensitive substring search over name and synonyms."""
        q = str(query).strip().lower()
        if not q:
            return self.materials.head(limit)
        mask = self.materials.apply(
            lambda r: q in r["name"].lower() or q in str(r["synonyms"]).lower(),
            axis=1,
        )
        return self.materials[mask].head(limit)

    def resolve_id(self, name_or_id: str) -> Optional[str]:
        """Return a material_id for a name, synonym, or id (or None)."""
        key = str(name_or_id).strip()
        if key in self._by_id:
            return key
        return self._name_index.get(key.lower())

    @functools.lru_cache(maxsize=2048)
    def _props_for(self, material_id: str):
        sub = self.properties[self.properties["material_id"] == material_id]
        return sub

    def card(self, name_or_id: str) -> Optional[MaterialCard]:
        """Build a MaterialCard for a material name/synonym/id."""
        mid = self.resolve_id(name_or_id)
        if mid is None:
            return None
        row = self._by_id[mid]
        props: Dict[str, float] = {}
        meta: Dict[str, Dict[str, Any]] = {}
        for _, pr in self._props_for(mid).iterrows():
            key = pr["property_name"]
            raw = pr["value"]
            if key in schema.NON_NUMERIC_PROPERTIES:
                s = str(raw).strip()
                # Normalize accidental float strings like "2.0" -> "2".
                if s.endswith(".0") and s[:-2].isdigit():
                    s = s[:-2]
                val = s if s else None
            else:
                val = _to_number(raw)
            props[key] = val
            meta[key] = {
                "unit": pr.get("unit", ""),
                "source_id": pr.get("source_id", ""),
                "data_quality": pr.get("data_quality", ""),
                "confidence_score": _to_number(pr.get("confidence_score", "")),
                "notes": pr.get("notes", ""),
            }
        return MaterialCard(
            material_id=mid,
            name=row["name"],
            material_type=row["material_type"],
            category=row.get("category", ""),
            identity={
                "synonyms": row.get("synonyms", ""),
                "CAS": row.get("CAS", ""),
                "PubChem_CID": row.get("PubChem_CID", ""),
                "SMILES": row.get("SMILES", ""),
                "InChIKey": row.get("InChIKey", ""),
                "subcategory": row.get("subcategory", ""),
            },
            properties=props,
            property_meta=meta,
            confidence_score=_to_number(row.get("confidence_score", "")) or 0.0,
            route_suitability=row.get("route_suitability", ""),
            safety_notes=row.get("regulatory_or_safety_notes", ""),
        )

    def source(self, source_id: str) -> Dict[str, Any]:
        sub = self.sources[self.sources["source_id"] == source_id]
        if sub.empty:
            return {}
        return sub.iloc[0].to_dict()

    def by_type(self, material_type: str) -> pd.DataFrame:
        return self.materials[self.materials["material_type"] == material_type]

    # ---- coverage -------------------------------------------------------- #
    def coverage(self) -> Dict[str, Any]:
        n_mat = len(self.materials)
        n_prop = len(self.properties)
        with_mw = self.properties[self.properties["property_name"] == "MW"][
            "material_id"
        ].nunique()
        return {
            "n_materials": n_mat,
            "n_property_rows": n_prop,
            "n_with_MW": int(with_mw),
            "fraction_with_MW": round(with_mw / n_mat, 3) if n_mat else 0.0,
            "material_types": self.materials["material_type"].value_counts().to_dict(),
        }


def _to_number(x: Any) -> Any:
    """Best-effort numeric conversion; leaves non-numeric strings as-is, '' -> None."""
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s.lower() in {"nan", "na", "none", "missing"}:
        return None
    try:
        return float(s)
    except ValueError:
        return s


@functools.lru_cache(maxsize=1)
def get_database() -> Database:
    """Cached default database instance."""
    return Database()
