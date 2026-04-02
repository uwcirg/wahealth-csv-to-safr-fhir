# Implementation Plan: Constitution v1.2.0 Repo Alignment

**Branch**: `003-constitution-repo-update` | **Date**: 2026-04-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-constitution-repo-update/spec.md`

## Summary

Constitution v1.2.0 elevated local FHIR validation from SHOULD to MUST for LLM agents. This feature updates CLAUDE.md to include the exact four-step LLM validation pipeline (convert test fixtures, extract IG version, run validator_cli.jar, zero-errors check) matching the CI workflow, so LLM agents can follow it without referencing the constitution directly.

## Technical Context

**Language/Version**: Python 3 (stdlib only at runtime)
**Primary Dependencies**: None at runtime. Dev: `ruff`, `validator_cli.jar`, `gitleaks`
**Storage**: Filesystem — CSV input, JSON output, JSON config
**Testing**: End-to-end FHIR validation via `validator_cli.jar`; `ruff` for linting
**Target Platform**: Linux/macOS/Windows workstations at ~100 WA hospitals
**Project Type**: CLI data transformation tool
**Performance Goals**: N/A (batch processing, not latency-sensitive)
**Constraints**: Zero runtime dependencies (stdlib only); single-file entry point (`convert.py`)
**Scale/Scope**: Single `convert.py` (~780 lines), documentation-only change for this feature

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Zero-Dependency Runtime | ✅ PASS | No code changes; documentation only |
| FHIR Profile Conformance | ✅ PASS | No changes to FHIR output generation |
| Validation-Driven Testing | ✅ PASS | This feature *implements* the LLM Development Validation requirement |
| Data Integrity and Defensive Transformation | ✅ PASS | No data transformation changes |
| Scope — Bed Capacity and HRD | ✅ PASS | No scope changes |
| Configuration over Code Changes | ✅ PASS | No config changes |
| Secret Protection | ✅ PASS | No secret handling changes |
| Clear, Predictable Output | ✅ PASS | No output format changes |
| CI Pipeline | ✅ PASS | CI unchanged; CLAUDE.md aligned to match CI |
| Single-File Simplicity | ✅ PASS | No code split |

**Gate result: PASS** — all principles satisfied. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/003-constitution-repo-update/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
convert.py               # Single entry point (unchanged)
config.example.json      # Config template (unchanged)
CLAUDE.md                # LLM agent instructions (MODIFIED — add validation pipeline)
.github/workflows/ci.yml # CI workflow (unchanged, used as reference)
input/                   # Test CSV fixtures
output/                  # Generated FHIR Bundles
```

**Structure Decision**: No structural changes. This feature modifies only CLAUDE.md to add the LLM validation pipeline instructions. No `contracts/` directory needed — this project's only external interface is the CLI (`python3 convert.py`), which is already documented.

## Complexity Tracking

No violations. No complexity justification needed.
