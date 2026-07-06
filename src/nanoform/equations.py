"""Deterministic scientific kernels.

Every function here is a pure, testable calculation. No constant is invented at
call time; callers pass in database-backed values. These functions are the
authoritative computational layer of NanoFormulationDesigner.

References (methods, not fabricated constants):
    - Griffin HLB weighting (classical mixed-HLB rule).
    - Tanford, "The Hydrophobic Effect" (chain volume/length relations).
    - Israelachvili critical packing parameter, CPP = v / (a0 * lc).
    - Hansen, "Hansen Solubility Parameters: A User's Handbook"
      (distance Ra, sphere radius R0, RED = Ra/R0).
    - Hildebrand solubility parameter from HSP components.
    - Flory-Huggins interaction parameter from solubility-parameter difference.
    - Henderson-Hasselbalch neutral/ionized fraction.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

# Gas constant in cm^3 * MPa / (mol * K) so that (V[cm3/mol] * dDelta[MPa^0.5]^2)/(R*T)
# is dimensionless. R = 8.314 J/(mol*K) = 8.314 cm^3*MPa/(mol*K).
R_CM3_MPA = 8.314


# --------------------------------------------------------------------------- #
# Batch mass
# --------------------------------------------------------------------------- #
def mg_from_umol(umol: float, mw_g_per_mol: float) -> float:
    """Convert micromoles to milligrams: mg = umol * MW / 1000."""
    return float(umol) * float(mw_g_per_mol) / 1000.0


def umol_from_mg(mg: float, mw_g_per_mol: float) -> float:
    """Convert milligrams to micromoles."""
    if mw_g_per_mol == 0:
        raise ValueError("Molecular weight must be non-zero.")
    return float(mg) * 1000.0 / float(mw_g_per_mol)


# --------------------------------------------------------------------------- #
# Mixed HLB (mass-weighted Griffin rule)
# --------------------------------------------------------------------------- #
def mixed_hlb(weights: Sequence[float], hlbs: Sequence[float]) -> float:
    """Mass-weighted mixed HLB = sum(w_i * HLB_i) / sum(w_i).

    `weights` are relative masses (any consistent unit). Entries with a missing
    (None / NaN) HLB are skipped and excluded from the weight normalization.
    """
    num = 0.0
    den = 0.0
    for w, h in zip(weights, hlbs):
        if h is None or (isinstance(h, float) and math.isnan(h)):
            continue
        if w is None or (isinstance(w, float) and math.isnan(w)):
            continue
        num += w * h
        den += w
    if den == 0:
        raise ValueError("No surfactant with a defined HLB and weight provided.")
    return num / den


# --------------------------------------------------------------------------- #
# Tanford chain geometry + critical packing parameter (CPP)
# --------------------------------------------------------------------------- #
def tanford_v_nm3(n_carbons: float, n_tails: int = 1) -> float:
    """Hydrophobic tail volume (nm^3) via Tanford: v = n_tails*(0.0274 + 0.0269*nc)."""
    return float(n_tails) * (0.0274 + 0.0269 * float(n_carbons))


def tanford_l_nm(n_carbons: float) -> float:
    """Maximum extended tail length (nm) via Tanford: lc = 0.154 + 0.1265*nc."""
    return 0.154 + 0.1265 * float(n_carbons)


def cpp_value(v_nm3: float, a0_nm2: float, lc_nm: float) -> float:
    """Critical packing parameter CPP = v / (a0 * lc)."""
    if a0_nm2 <= 0 or lc_nm <= 0:
        raise ValueError("Headgroup area and chain length must be positive.")
    return v_nm3 / (a0_nm2 * lc_nm)


def cpp_class(cpp: float) -> str:
    """Map CPP to expected aggregate morphology (Israelachvili)."""
    if cpp < 1.0 / 3.0:
        return "spherical micelle"
    if cpp < 0.5:
        return "cylindrical/rod micelle"
    if cpp < 1.0:
        return "flexible bilayer / vesicle"
    if cpp <= 1.05:
        return "planar bilayer"
    return "inverted / non-lamellar (hexagonal)"


# --------------------------------------------------------------------------- #
# Hansen solubility parameters
# --------------------------------------------------------------------------- #
def hansen_distance(
    dD1: float, dP1: float, dH1: float, dD2: float, dP2: float, dH2: float
) -> float:
    """Hansen distance Ra = sqrt(4*(dD)^2 + (dP)^2 + (dH)^2)."""
    return math.sqrt(
        4.0 * (dD1 - dD2) ** 2 + (dP1 - dP2) ** 2 + (dH1 - dH2) ** 2
    )


def red_score(Ra: float, R0: float) -> float:
    """Relative Energy Difference RED = Ra / R0. RED < 1 => inside the solubility sphere."""
    if R0 <= 0:
        raise ValueError("Interaction radius R0 must be positive.")
    return Ra / R0


def hildebrand_delta(dD: float, dP: float, dH: float) -> float:
    """Total Hildebrand parameter from HSP components: sqrt(dD^2 + dP^2 + dH^2)."""
    return math.sqrt(dD ** 2 + dP ** 2 + dH ** 2)


# --------------------------------------------------------------------------- #
# Flory-Huggins interaction parameter
# --------------------------------------------------------------------------- #
def flory_huggins_chi(
    delta1: float,
    delta2: float,
    v_ref_cm3_mol: float,
    temperature_C: float = 25.0,
    offset: float = 0.34,
) -> float:
    """Flory-Huggins chi = offset + V_ref*(delta1 - delta2)^2 / (R*T).

    delta values are Hildebrand parameters in MPa^0.5, V_ref in cm^3/mol.
    The empirical 0.34 entropic offset is conventional; set offset=0 to omit it.
    """
    T = temperature_C + 273.15
    return offset + v_ref_cm3_mol * (delta1 - delta2) ** 2 / (R_CM3_MPA * T)


# --------------------------------------------------------------------------- #
# Ionization (Henderson-Hasselbalch)
# --------------------------------------------------------------------------- #
def neutral_fraction(pKa: float, pH: float, is_acid: bool) -> float:
    """Fraction of molecules in the neutral (un-ionized) state.

    Acid:  f_neutral = 1 / (1 + 10^(pH - pKa))
    Base:  f_neutral = 1 / (1 + 10^(pKa - pH))
    """
    if is_acid:
        return 1.0 / (1.0 + 10 ** (pH - pKa))
    return 1.0 / (1.0 + 10 ** (pKa - pH))


def ionized_fraction(pKa: float, pH: float, is_acid: bool) -> float:
    """Fraction ionized = 1 - neutral_fraction."""
    return 1.0 - neutral_fraction(pKa, pH, is_acid)


# --------------------------------------------------------------------------- #
# Generic helpers
# --------------------------------------------------------------------------- #
def weighted_mean(values: Sequence[float], weights: Sequence[float]) -> float:
    """Weighted mean, skipping None/NaN value-weight pairs. Returns NaN if empty."""
    num = 0.0
    den = 0.0
    for v, w in zip(values, weights):
        if v is None or w is None:
            continue
        if isinstance(v, float) and math.isnan(v):
            continue
        if isinstance(w, float) and math.isnan(w):
            continue
        num += v * w
        den += w
    if den == 0:
        return float("nan")
    return num / den


def normalize_score(x: float, lo: float, hi: float) -> float:
    """Clamp-and-scale x from [lo, hi] to [0, 1]."""
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp x into [lo, hi]."""
    return max(lo, min(hi, x))
