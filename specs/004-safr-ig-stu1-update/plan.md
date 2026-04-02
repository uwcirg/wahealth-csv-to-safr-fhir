# Implementation Plan: Update SAFR IG Version to STU 1

**Branch**: `004-safr-ig-stu1-update` | **Date**: 2026-04-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-safr-ig-stu1-update/spec.md`

## Summary

Update the converter's SAFR IG version constant from `1.0.0-ballot` to `1.0.0` to target the official STU 1 (Trial-use) release published 2026-04-01. All generated FHIR profile URLs are derived from this constant, so the change propagates automatically. Validate output against the published `hl7.fhir.us.safr#1.0.0` IG package to confirm conformance.

## Technical Context

**Language/Version**: Python 3 (stdlib only)  
**Primary Dependencies**: None at runtime  
**Storage**: Filesystem — CSV input, JSON output, JSON config  
**Testing**: FHIR validator (`validator_cli.jar`), `ruff` (linter)  
**Target Platform**: Linux/Windows workstations at WA hospitals  
**Project Type**: CLI tool  
**Performance Goals**: N/A (batch conversion, not performance-sensitive)  
**Constraints**: Zero third-party runtime dependencies  
**Scale/Scope**: Single constant change in `convert.py` line 38

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Zero-Dependency Runtime | PASS | No new dependencies introduced |
| FHIR Profile Conformance | PASS | This change directly serves this principle — updating to the published IG version |
| IG Version Tracking | PASS | `SAFR_IG_VERSION` constant is the single source of truth; update is deliberate and reviewable |
| IG Version in Output | PASS | All profile URLs derive from the constant via f-strings |
| Accommodating IG Changes | PASS | This is exactly the prescribed workflow: constant update + validation pass |
| Validation-Driven Testing | PASS | Full validation pipeline will be run against `hl7.fhir.us.safr#1.0.0` |
| LLM Development Validation | PASS | Will run the 4-step validation pipeline before completion |
| Data Integrity | PASS | No data transformation logic changes |
| Single-File Simplicity | PASS | Single constant change in `convert.py` |
| Configuration over Code | PASS | No config changes needed |
| Secret Protection | PASS | No secrets involved |

No violations. No complexity justifications needed.

## Project Structure

### Documentation (this feature)

```text
specs/004-safr-ig-stu1-update/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
convert.py               # Single-file converter — line 38: SAFR_IG_VERSION constant
config.example.json      # Configuration template (no changes needed)
input/                   # Test CSV fixtures
output/                  # Generated FHIR Bundles
```

**Structure Decision**: No structural changes. The existing single-file layout is correct for this feature. The change is limited to one constant on line 38 of `convert.py`.
