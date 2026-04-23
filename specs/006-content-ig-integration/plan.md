# Implementation Plan: CDC NHSN SAFR Content IG Integration

**Branch**: `006-content-ig-integration` | **Date**: 2026-04-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-content-ig-integration/spec.md`

## Summary

Integrate the CDC NHSN SAFR Content IG (`gov.cdc.nhsn.safr`) as a
companion to the base US SAFR IG (`hl7.fhir.us.safr`). The Content IG
provides the authoritative, computable BedCapacityMeasure definition.
This feature adds a version-tracking constant for the Content IG,
updates the Measure canonical URL to reference the Content IG's
definition, and expands the validation pipeline to load both IGs.

## Technical Context

**Language/Version**: Python 3 (stdlib only at runtime)
**Primary Dependencies**: None at runtime. Dev: `ruff` (linter),
`validator_cli.jar` (FHIR validation), `gitleaks` (secret scanning)
**Storage**: Filesystem — CSV input, JSON output, JSON config
**Testing**: FHIR validator end-to-end conformance + Python unittest
**Target Platform**: Windows/Linux/macOS hospital workstations
**Project Type**: CLI data transformation tool
**Performance Goals**: N/A (batch processing)
**Constraints**: Zero runtime dependencies (stdlib only)
**Scale/Scope**: ~100 hospital deployments, single `convert.py` file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Zero-Dependency Runtime | PASS | No new runtime dependencies. Only constants and URL changes in `convert.py`. |
| FHIR Profile Conformance | PASS | This feature directly implements Content IG Version Tracking and Measure Canonical URLs rules from constitution v1.4.0. |
| IG Version Tracking | PASS | Adding `NHSN_SAFR_IG_VERSION` as a separate named constant with startup validation. |
| IG Version in Output | PASS | `MEASURE_URL` will use `NHSN_SAFR_IG_VERSION` in the version suffix. |
| Accommodating IG Changes | PASS | Content IG version is a deliberate, reviewable constant change. |
| Validation-Driven Testing | PASS | Validation pipeline expanded to include both IGs. LLM validation instructions updated. |
| Data Integrity | N/A | No data transformation logic changes. |
| Scope | PASS | Bed capacity measure stays in scope. No new measure domains added. |
| Configuration over Code | N/A | No config changes needed. |
| Secret Protection | N/A | No secret-related changes. |
| Clear Output | PASS | Only `MeasureReport.measure` field value changes in output. |
| CI Pipeline | PASS | CI updated to validate against both IGs. |
| Single-File Simplicity | PASS | Changes stay within `convert.py`. No new source files. |

## Project Structure

### Documentation (this feature)

```text
specs/006-content-ig-integration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
convert.py               # Line 38: SAFR_IG_VERSION, new: NHSN_SAFR_IG_VERSION
                         # Line 62: MEASURE_URL update
.github/workflows/ci.yml # Validation step: add Content IG
CLAUDE.md                # LLM validation pipeline instructions
known-validation-issues.md # Possible new entries
```

**Structure Decision**: Single-file project. All converter changes
are in `convert.py`. Pipeline changes in CI and CLAUDE.md.
