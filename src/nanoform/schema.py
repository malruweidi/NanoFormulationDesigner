"""Canonical schema: table columns, property vocabulary, aliases, and enums.

This module is the single source of truth for column names and property keys so
that the database builder, loader, kernels, and UI never drift apart.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
# Relational table columns
# --------------------------------------------------------------------------- #
MATERIALS_COLUMNS = [
    "material_id", "name", "synonyms", "material_type", "category", "subcategory",
    "CAS", "PubChem_CID", "SMILES", "InChIKey", "supplier_or_grade_notes",
    "route_suitability", "regulatory_or_safety_notes", "source_id",
    "curation_status", "confidence_score", "notes",
]

MATERIAL_PROPERTIES_COLUMNS = [
    "material_id", "property_name", "value", "unit", "temperature_C", "pH",
    "method", "source_id", "data_quality", "confidence_score", "notes",
]

SOURCES_COLUMNS = [
    "source_id", "source_type", "citation", "DOI", "URL", "access_date", "notes",
]

FORMULATIONS_COLUMNS = [
    "formulation_id", "carrier_type", "route", "process_method", "aqueous_phase",
    "pH", "temperature_C", "source_id", "notes",
]

FORMULATION_COMPONENTS_COLUMNS = [
    "formulation_id", "material_id", "component_role", "amount_value",
    "amount_unit", "mol_percent", "mass_percent", "concentration_mg_ml",
]

OUTCOMES_COLUMNS = [
    "formulation_id", "endpoint", "value", "unit", "method", "timepoint_h",
    "condition", "source_id",
]

CURATION_LOG_COLUMNS = [
    "date", "material_id", "action", "property_name", "old_value", "new_value",
    "source_id", "curator_note",
]

# --------------------------------------------------------------------------- #
# Material types (drive required-field validation and UI grouping)
# --------------------------------------------------------------------------- #
MATERIAL_TYPES = [
    "api",
    "nonionic_surfactant",
    "ionic_surfactant",
    "phospholipid",
    "sterol",
    "bile_salt",
    "solid_lipid",
    "liquid_lipid",
    "solvent",
    "carrier",
    "polymer",
]

# --------------------------------------------------------------------------- #
# Canonical property names used by the kernels.
# The alias map lets the loader accept common spellings and fold them to the
# canonical key. Keys are canonical; values are accepted aliases (lowercased).
# --------------------------------------------------------------------------- #
CANONICAL_PROPERTIES = [
    "MW", "HLB", "logP", "logD_7.4", "pKa", "acid_base",
    "water_solubility_mg_ml", "melting_point_C", "Tm_C", "boiling_point_C",
    "density_g_ml", "dielectric_constant", "polarity_index", "water_miscibility",
    "ICH_class", "PDE_mg_day",
    "delta_D", "delta_P", "delta_H", "hsp_radius", "molar_volume_cm3_mol",
    "headgroup_area_nm2", "tail_carbons", "tail_unsaturation", "n_tails",
    "formal_charge", "CMC_mM", "cloud_point_C", "krafft_point_C", "Tg_C",
    "avg_MW", "TPSA", "HBD", "HBA", "rotatable_bonds", "aromatic_rings",
    "BCS_class",
    # Role / behavior flags (stored as 1.0 / 0.0)
    "pegylated", "ionizable", "edge_activator", "charge_inducer",
    "vesicle_anchor", "fusogenic", "cationic", "cryoprotectant", "porous_carrier",
    "toxicity_penalty",
]

PROPERTY_ALIASES = {
    "mw": "MW",
    "molecular_weight": "MW",
    "molecular_weight_g_mol": "MW",
    "molecular_weight_g/mol": "MW",
    "mol_weight": "MW",
    "hlb": "HLB",
    "logp": "logP",
    "log_p": "logP",
    "logd": "logD_7.4",
    "logd_7.4": "logD_7.4",
    "logd74": "logD_7.4",
    "pka": "pKa",
    "acid_base": "acid_base",
    "water_solubility": "water_solubility_mg_ml",
    "water_solubility_mg_ml": "water_solubility_mg_ml",
    "solubility_water": "water_solubility_mg_ml",
    "melting_point": "melting_point_C",
    "mp": "melting_point_C",
    "tm": "Tm_C",
    "transition_temp": "Tm_C",
    "phase_transition_temperature": "Tm_C",
    "bp": "boiling_point_C",
    "boiling_point": "boiling_point_C",
    "density": "density_g_ml",
    "dielectric": "dielectric_constant",
    "dielectric_constant": "dielectric_constant",
    "polarity": "polarity_index",
    "polarity_index": "polarity_index",
    "water_miscibility": "water_miscibility",
    "ich_class": "ICH_class",
    "pde": "PDE_mg_day",
    "dd": "delta_D",
    "delta_d": "delta_D",
    "dp": "delta_P",
    "delta_p": "delta_P",
    "dh": "delta_H",
    "delta_h": "delta_H",
    "r0": "hsp_radius",
    "hsp_radius": "hsp_radius",
    "molar_volume": "molar_volume_cm3_mol",
    "headgroup_area": "headgroup_area_nm2",
    "a0": "headgroup_area_nm2",
    "tail_carbons": "tail_carbons",
    "chain_length": "tail_carbons",
    "tail_unsaturation": "tail_unsaturation",
    "unsaturation": "tail_unsaturation",
    "n_tails": "n_tails",
    "number_of_tails": "n_tails",
    "formal_charge": "formal_charge",
    "charge": "formal_charge",
    "cmc": "CMC_mM",
    "cmc_mm": "CMC_mM",
    "cloud_point": "cloud_point_C",
    "krafft_point": "krafft_point_C",
    "tg": "Tg_C",
    "glass_transition": "Tg_C",
    "avg_mw": "avg_MW",
    "average_mw": "avg_MW",
    "tpsa": "TPSA",
    "hbd": "HBD",
    "hba": "HBA",
    "rotatable_bonds": "rotatable_bonds",
    "aromatic_rings": "aromatic_rings",
    "bcs_class": "BCS_class",
}


# Properties that must stay categorical strings (never numeric-cast by the loader).
NON_NUMERIC_PROPERTIES = {"ICH_class", "acid_base", "BCS_class"}


def canonical_property(name: str) -> str:
    """Fold a property name to its canonical form; unknown names pass through."""
    if name in CANONICAL_PROPERTIES:
        return name
    return PROPERTY_ALIASES.get(str(name).strip().lower(), name)


# --------------------------------------------------------------------------- #
# Required properties per material type (used by validation.py & Custom Material)
# --------------------------------------------------------------------------- #
REQUIRED_PROPERTIES = {
    "api": ["MW"],
    "nonionic_surfactant": ["MW", "HLB"],
    "ionic_surfactant": ["MW", "formal_charge"],
    "phospholipid": ["MW"],
    "sterol": ["MW"],
    "bile_salt": ["MW"],
    "solid_lipid": ["MW"],
    "liquid_lipid": ["MW"],
    "solvent": ["MW"],
    "carrier": [],
    "polymer": [],
}

# --------------------------------------------------------------------------- #
# CQA (critical quality attribute) definitions
# --------------------------------------------------------------------------- #
CQA_KEYS = [
    "encapsulation_efficiency",
    "particle_size",
    "pdi",
    "zeta_potential",
    "drug_loading",
    "release_tendency",
    "crystallization_risk",
    "solvent_suitability",
    "carrier_suitability",
    "nanoform_score",
]

# --------------------------------------------------------------------------- #
# Formulation families and their canonical membrane logic
# --------------------------------------------------------------------------- #
FORMULATION_FAMILIES = [
    "niosome", "proniosome", "liposome", "transfersome", "ethosome", "bilosome",
    "lipid_nanoparticle", "solid_lipid_nanoparticle", "nanostructured_lipid_carrier",
    "nanoemulsion", "polymeric_nanoparticle", "lipid_polymer_hybrid",
    "dry_powder_carrier",
]

ROUTES = ["oral", "topical", "transdermal", "ocular", "pulmonary", "parenteral", "nasal", "general"]
