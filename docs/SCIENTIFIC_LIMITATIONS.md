# Scientific Limitations

Read this before trusting any output.

## The headline
Outputs are **descriptor-driven, ranked decision-support estimates**. They are
**heuristic until trained/validated** on internal experimental outcomes and
**require laboratory verification**. Confidence depends on database coverage.

We deliberately avoid the words *guaranteed*, *optimal formulation*, *validated
predictor*, and *best formulation* (without qualification).

## What the tool actually does
- Computes physically meaningful descriptors (HLB, CPP, HSP RED, χ, ionization)
  from database constants using textbook relations.
- Maps those descriptors to **heuristic** CQA sub-scores with transparent,
  inspectable rules.
- Ranks materials and candidates and explains the drivers.

## What it does NOT do
- It does **not** predict numeric EE %, particle size in nm, PDI, or zeta in mV.
  CQA "estimates" are qualitative bands + 0–1 favorability scores.
- It has **no in-vivo / PK / biodistribution model**. Route logic is barrier-
  aware but qualitative.
- It does **not** model manufacturing scale-up, sterilization, or stability
  kinetics quantitatively.
- It cannot compensate for missing constants — those are surfaced, not guessed.

## Sources of uncertainty
1. **Estimated constants.** HSP components, headgroup areas, molar volumes, and
   some Tg values are marked `estimated` (confidence ≤ 0.40). They drive RED, χ,
   and CPP and should be replaced with measured values where decisions hinge.
2. **Grade/lot variability.** CMC, cloud point, polymer MW/Tg, carrier porosity,
   and natural-lipid composition vary by grade and are flagged accordingly.
3. **Heuristic weightings.** CQA rule weights are expert-set defaults, not fit to
   data. Design-goal profiles reweight them but do not calibrate them.
4. **Placeholder payloads.** Insulin/siRNA/mRNA/DNA/peptide/protein entries are
   PLACEHOLDERS with low confidence; verify every value before use.

## Design maturity levels (DML)
- **DML-0** no coherent design.
- **DML-1** descriptor-only / missing critical constants (heuristic).
- **DML-2** descriptor-supported rational design. **← current maximum.**
- **DML-3** trained on internal experimental outcomes (not in this build).
- **DML-4** prospectively validated (not in this build).

## Responsible use
Use this for **rational screening and prioritization** of candidates to take into
the lab — not for final formulation decisions, clinical use, or regulatory
claims.
