# Implementation Plan: Constitution Alignment

**Branch**: `001-constitution-alignment` | **Date**: 2026-04-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-constitution-alignment/spec.md`

## Summary

Bring the repository into compliance with its newly-written constitution by adding a `.gitignore` for secret protection, a GitHub Actions CI pipeline (lint, FHIR validation, secret scanning), updating `config.example.json` with obvious placeholder credentials, and establishing lint configuration. No functional changes to runtime code (`convert.py`); minor lint fixes may be needed to pass the linter.

## Technical Context

**Language/Version**: Python 3 (stdlib only for runtime; dev tools use pip)  
**Primary Dependencies**: None at runtime. Dev: `ruff` (linter), `validator_cli.jar` (FHIR validation), `gitleaks` (secret scanning)  
**Storage**: File-based (CSV input, JSON output)  
**Testing**: End-to-end FHIR validation via HL7 Reference Validator; `ruff` for lint  
**Target Platform**: GitHub Actions CI runners (Ubuntu latest), developer workstations (diverse)  
**Project Type**: CLI tool (single-file Python script)  
**Performance Goals**: CI pipeline completes in under 10 minutes  
**Constraints**: Zero runtime dependencies (constitution principle). Dev dependencies permitted.  
**Scale/Scope**: ~100 hospital deployments; 1 Python file (778 lines); 2 test CSV fixtures

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| Zero-Dependency Runtime | PASS | No runtime dependencies added. `ruff` and `gitleaks` are dev/CI-only. |
| FHIR Profile Conformance | PASS | CI validates output against SAFR profiles. Conformance is enforced, not changed. |
| Validation-Driven Testing | PASS | CI runs converter against test CSVs and validates with HL7 Reference Validator. |
| Data Integrity and Defensive Transformation | N/A | No changes to data transformation logic. |
| Scope — Bed Capacity and HRD | PASS | No new measure domains. CI validates existing bed capacity output. |
| Configuration over Code Changes | PASS | `config.example.json` updated with better placeholders. No hardcoded values added. |
| Secret Protection | PASS | `.gitignore` added with all required patterns. CI includes secret scanning. |
| Clear, Predictable Output | N/A | No changes to output format or structure. |
| CI Pipeline | PASS | This feature creates the CI pipeline. |
| Single-File Simplicity | PASS | No new Python files. convert.py unchanged at 778 lines (under 1000 threshold). |

**Gate result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-constitution-alignment/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
.                              # Repository root
├── convert.py                 # Existing — no changes (778 lines)
├── config.example.json        # Existing — update server placeholders
├── .gitignore                 # NEW — secret and cache exclusion
├── ruff.toml                  # NEW — lint configuration
├── input/                     # Existing — test CSV fixtures (no changes)
│   ├── 2025.10.21.Test.Facility.BedCapacity.csv
│   └── 2025.10.21.Test.Facility.BedCapacity.column-labels-only.csv
└── .github/
    └── workflows/
        └── ci.yml             # NEW — CI pipeline
```

**Structure Decision**: No new directories beyond `.github/workflows/` (required by GitHub Actions). All changes are repo infrastructure files at the root level, consistent with the single-file simplicity principle.

## Complexity Tracking

No constitution violations to justify. All changes align with stated principles.
