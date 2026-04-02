# Implementation Plan: Constitution v1.3.0 Repo Sync

**Branch**: `005-constitution-repo-sync` | **Date**: 2026-04-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-constitution-repo-sync/spec.md`

## Summary

Bring the repository into full compliance with constitution v1.3.0 by adding unit tests for core computation functions (`safe_int`, `get_occupied_and_unoccupied`, `parse_reporting_date`, `compute_groups`), updating CLAUDE.md with LLM-specific known-issue filtering guidance, and enhancing CI with a unit test job and improved IG version logging.

## Technical Context

**Language/Version**: Python 3 (stdlib only at runtime)
**Primary Dependencies**: None at runtime. Dev: `ruff` (linter), `validator_cli.jar` (FHIR validation), `gitleaks` (secret scanning)
**Storage**: Filesystem — CSV input, JSON output, JSON config
**Testing**: Python `unittest` (stdlib) for unit tests; `validator_cli.jar` for FHIR conformance
**Target Platform**: Hospital workstations (diverse, locked-down environments) and GitHub Actions CI
**Project Type**: CLI data transformation tool
**Performance Goals**: N/A for this feature (testing and documentation changes only)
**Constraints**: Zero runtime dependencies (constitution: Zero-Dependency Runtime). Single-file simplicity until ~1000 lines (currently ~819).
**Scale/Scope**: ~100 Washington State hospitals; 25 MeasureReport groups per Bundle

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Zero-Dependency Runtime | PASS | Unit tests use `unittest` (stdlib). No runtime changes. |
| FHIR Profile Conformance | PASS | No changes to FHIR output. |
| Validation-Driven Testing | PASS | This feature directly implements the constitution's requirement for "supplementary unit tests for computation logic." |
| Data Integrity | PASS | No changes to data processing. Tests verify existing clamping and defensive behavior. |
| Scope | PASS | Bed capacity only. No new measure domains. |
| Configuration over Code | PASS | No config changes. |
| Secret Protection | PASS | No secret handling changes. |
| Clear Output | PASS | No output format changes. |
| CI Pipeline | PASS | Adds unit test job and improves logging per constitution requirements. |
| Single-File Simplicity | PASS | No file extraction. Tests are in separate `tests/` directory (explicitly excluded from single-file threshold per constitution). |
| LLM Development Validation | PASS | This feature improves LLM validation guidance per constitution v1.3.0. |

**Post-Phase 1 Re-check**: All gates remain PASS. No design decisions introduce violations.

## Project Structure

### Documentation (this feature)

```text
specs/005-constitution-repo-sync/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
convert.py                          # Existing — no changes (import target for tests)
tests/
└── test_compute.py                 # New — unit tests for computation functions
CLAUDE.md                           # Modified — add known-issue filtering to Step 4
.github/workflows/ci.yml            # Modified — add unit-test job, improve IG version log
known-validation-issues.md          # Existing — referenced by CLAUDE.md update (no changes)
```

**Structure Decision**: Tests go in `tests/` at the repo root, consistent with the `Project Structure` section in CLAUDE.md and constitution's mention of test directories being separate from the single-file threshold. No `src/` directory exists or is needed — `convert.py` is at the repo root.

## Complexity Tracking

No constitution violations to justify. All changes align with existing principles.
