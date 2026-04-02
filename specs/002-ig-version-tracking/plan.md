# Implementation Plan: IG Version Tracking

**Branch**: `002-ig-version-tracking` | **Date**: 2026-04-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-ig-version-tracking/spec.md`

## Summary

Extract the SAFR IG version into a single named constant (`SAFR_IG_VERSION`), apply it as a `|version` suffix to all SAFR-defined profile URLs in generated FHIR output, update CI to validate against the versioned IG package, and add startup validation and CI logging for traceability.

## Technical Context

**Language/Version**: Python 3 (stdlib only at runtime)
**Primary Dependencies**: None at runtime. Dev: `ruff` (linter), `validator_cli.jar` (FHIR validation), `gitleaks` (secret scanning)
**Storage**: Filesystem — CSV input, JSON output, JSON config
**Testing**: End-to-end FHIR validation via `validator_cli.jar`; `pytest` for unit tests
**Target Platform**: Hospital data manager workstations (diverse OS), GitHub Actions CI
**Project Type**: CLI data transformation tool
**Performance Goals**: N/A (batch processing of small CSVs)
**Constraints**: Zero runtime dependencies (stdlib only); single-file converter (`convert.py` at repo root, ~782 lines)
**Scale/Scope**: ~100 hospital deployments; single `convert.py` file

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **Zero-Dependency Runtime** | ✅ PASS | Changes are to constants and string formatting in `convert.py` — no new imports or dependencies |
| **FHIR Profile Conformance** | ✅ PASS — this feature directly implements IG Version Tracking, IG Version in Output, and Accommodating IG Changes rules | Adding `SAFR_IG_VERSION` constant, applying `\|version` suffix to SAFR profiles, keeping external profiles unchanged |
| **Validation-Driven Testing** | ✅ PASS — this feature directly implements IG Version in Validation, Recording the IG Version, and Version Change as a Test Event rules | CI will use versioned `-ig hl7.fhir.us.safr#<version>` and log the version |
| **Data Integrity and Defensive Transformation** | ✅ PASS | Adding startup validation for empty/malformed IG version constant |
| **Configuration over Code Changes** | ✅ PASS | IG version is a code constant (not per-hospital config) — this is correct since all hospitals target the same IG version |
| **Secret Protection** | ✅ PASS | No secrets involved |
| **Clear, Predictable Output** | ✅ PASS | Output format unchanged; profile URLs gain version suffix |
| **Single-File Simplicity** | ✅ PASS | All changes within existing `convert.py` and `.github/workflows/ci.yml` |

**Gate result: PASS — no violations.**

## Project Structure

### Documentation (this feature)

```text
specs/002-ig-version-tracking/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
convert.py               # Single-file converter — all code changes here
.github/workflows/ci.yml # CI pipeline — validation command changes here
config.example.json      # No changes needed (IG version is not per-hospital)
input/                   # Test CSV fixtures — no changes needed
```

**Structure Decision**: This feature modifies two existing files (`convert.py` and `ci.yml`) and creates no new source files, consistent with the Single-File Simplicity principle.

## Complexity Tracking

No constitution violations — table not needed.
