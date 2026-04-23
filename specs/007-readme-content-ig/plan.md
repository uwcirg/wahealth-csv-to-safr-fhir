# Implementation Plan: Update README with Content IG Documentation

**Branch**: `007-readme-content-ig` | **Date**: 2026-04-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-readme-content-ig/spec.md`

## Summary

Update `README.md` to document the dual-IG architecture introduced by
feature 006-content-ig-integration: the base US SAFR IG for structural
profiles and the CDC NHSN SAFR Content IG for Measure definitions and
CodeSystems. Documentation-only change — no code modifications.

## Technical Context

**Language/Version**: N/A (documentation only — Markdown)
**Primary Dependencies**: N/A
**Storage**: N/A
**Testing**: Manual review of README content
**Target Platform**: GitHub-rendered Markdown
**Project Type**: Documentation update
**Performance Goals**: N/A
**Constraints**: Preserve existing README structure; keep accessible
to non-FHIR experts
**Scale/Scope**: Single file (`README.md`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Zero-Dependency Runtime | N/A | No code changes |
| FHIR Profile Conformance | N/A | No output changes |
| Validation-Driven Testing | N/A | No FHIR output affected |
| Data Integrity | N/A | No data transformation changes |
| Scope | PASS | Documents existing bed capacity scope |
| Configuration over Code | N/A | No config changes |
| Secret Protection | N/A | No secrets involved |
| Clear Output | N/A | No output changes |
| CI Pipeline | N/A | No CI changes |
| Single-File Simplicity | N/A | No source changes |

All gates pass. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/007-readme-content-ig/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Repository root

```text
README.md                # The only file modified by this feature
```

**Structure Decision**: Single-file documentation update. No data
model or contracts needed.
