"""Custom (session) materials.

Lets a user define a temporary material for a single session, validate that the
required fields for its type are present, see which calculations it enables or
disables, and export it as CSV rows compatible with the relational schema.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from . import schema
from .database import MaterialCard

# Which calculations each property unlocks (for the enabled/disabled report).
PROPERTY_ENABLES = {
    "MW": ["batch mass", "mixed HLB weighting"],
    "HLB": ["mixed HLB"],
    "tail_carbons": ["CPP / Tanford geometry", "chain descriptors"],
    "headgroup_area_nm2": ["CPP / morphology tendency"],
    "n_tails": ["CPP / Tanford geometry"],
    "delta_D": ["Hansen RED", "Flory-Huggins chi"],
    "delta_P": ["Hansen RED", "Flory-Huggins chi"],
    "delta_H": ["Hansen RED", "Flory-Huggins chi"],
    "pKa": ["ionization / neutral fraction"],
    "formal_charge": ["zeta tendency"],
    "Tm_C": ["rigidity / fluidity"],
    "melting_point_C": ["crystallization risk"],
}


@dataclass
class CustomMaterial:
    material_id: str
    name: str
    material_type: str
    category: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_card(self) -> MaterialCard:
        props = {schema.canonical_property(k): v for k, v in self.properties.items()}
        return MaterialCard(
            material_id=self.material_id, name=self.name,
            material_type=self.material_type, category=self.category,
            properties=props, confidence_score=0.3,
            safety_notes="Session-defined custom material (unverified).",
        )


def validate(material: CustomMaterial) -> Tuple[bool, List[str], List[str], List[str]]:
    """Return (ok, missing_required, enabled_calcs, disabled_calcs)."""
    if material.material_type not in schema.MATERIAL_TYPES:
        return False, [f"Unknown material_type '{material.material_type}'"], [], []
    present = {schema.canonical_property(k) for k, v in material.properties.items()
               if v not in (None, "")}
    required = schema.REQUIRED_PROPERTIES.get(material.material_type, [])
    missing = [r for r in required if r not in present]

    enabled, disabled = set(), set()
    for prop, calcs in PROPERTY_ENABLES.items():
        target = enabled if prop in present else disabled
        for calc in calcs:
            target.add(calc)
    enabled -= set()  # noop for clarity
    # A calc is only "enabled" if ALL of its required props are present.
    truly_enabled = _resolve_enabled(present)
    truly_disabled = sorted({c for cs in PROPERTY_ENABLES.values() for c in cs} - truly_enabled)
    return (len(missing) == 0, missing, sorted(truly_enabled), truly_disabled)


def _resolve_enabled(present: set) -> set:
    enabled = set()
    if "MW" in present:
        enabled.add("batch mass")
    if "HLB" in present:
        enabled.add("mixed HLB")
    if {"tail_carbons", "headgroup_area_nm2"} <= present:
        enabled.add("CPP / morphology tendency")
    if {"delta_D", "delta_P", "delta_H"} <= present:
        enabled.add("Hansen RED"); enabled.add("Flory-Huggins chi")
    if "pKa" in present:
        enabled.add("ionization / neutral fraction")
    if "formal_charge" in present:
        enabled.add("zeta tendency")
    if "Tm_C" in present or "melting_point_C" in present:
        enabled.add("rigidity / crystallization")
    return enabled


def to_csv_rows(material: CustomMaterial, source_id: str = "user_custom") -> Dict[str, List[List[Any]]]:
    """Return material + property rows matching the relational CSV schema."""
    mat_row = [
        material.material_id, material.name, "", material.material_type,
        material.category, "", "", "", "", "", "", "", "user-defined custom",
        source_id, "user", 0.3, "Session custom material",
    ]
    prop_rows = []
    for k, v in material.properties.items():
        if v in (None, ""):
            continue
        prop_rows.append([
            material.material_id, schema.canonical_property(k), v, "", "", "",
            "user", source_id, "user-provided", 0.3, "Custom material property",
        ])
    return {"materials": [mat_row], "material_properties": prop_rows}
