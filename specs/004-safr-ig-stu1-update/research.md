# Research: Update SAFR IG Version to STU 1

**Feature**: 004-safr-ig-stu1-update  
**Date**: 2026-04-02

## Research Question 1: Are there structural profile changes between ballot and STU 1?

**Decision**: Treat this as a version-string-only change; validate to detect any structural differences.

**Rationale**: The SAFR IG STU 1 (`1.0.0`) is the first official Trial-use release following the `1.0.0-ballot`. STU 1 releases typically incorporate ballot reconciliation feedback but rarely change profile structures in breaking ways. The converter's output structure (Bundle containing MeasureReport, Organization, Location, Device) follows the ballot profiles. The FHIR validator will flag any structural mismatches when run against `hl7.fhir.us.safr#1.0.0`.

**Alternatives considered**:
- Pre-analyze the published IG diff manually — unnecessary overhead since the validator is authoritative.
- Wait for a detailed change log from HL7 — would delay the update; validation is sufficient.

## Research Question 2: Is the `hl7.fhir.us.safr#1.0.0` package available?

**Decision**: Assume availability as of the 2026-04-01 publication date. Validation step will confirm.

**Rationale**: The user provided the publication date (2026-04-01) and version (`1.0.0 | STU 1 (Trial-use)`), indicating the IG has been published. The FHIR package registry (`packages.fhir.org`) typically hosts packages within hours of publication. The validation step will confirm resolution.

**Alternatives considered**: None — this is a factual availability check resolved by running the validator.

## Research Question 3: What code locations reference the IG version?

**Decision**: Only `convert.py` line 38 (`SAFR_IG_VERSION = "1.0.0-ballot"`) needs to change. All downstream references use f-strings from this constant.

**Rationale**: Grep of the codebase shows:
- `SAFR_IG_VERSION` constant on line 38 — the single source of truth
- `BUNDLE_PROFILE` (line 45), `ORG_PROFILE` (line 47), `MEASURE_URL` (line 62) — all derived via f-strings from `SAFR_IG_VERSION`
- Version regex validation (line 40) accepts `X.Y.Z` format (no suffix), so `1.0.0` passes
- CI pipeline in `.github/workflows/ci.yml` extracts `SAFR_IG_VERSION` dynamically — no CI changes needed

**Alternatives considered**: None — the architecture is already designed for exactly this kind of update.
