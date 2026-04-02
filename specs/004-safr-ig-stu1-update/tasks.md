# Tasks: Update SAFR IG Version to STU 1

**Input**: Design documents from `/specs/004-safr-ig-stu1-update/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Not explicitly requested — test tasks omitted. Validation is covered by the FHIR validation pipeline (constitution requirement).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No project setup needed — existing project, single constant change.

*(No tasks — project structure already exists)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational work needed — the change has no blocking prerequisites.

*(No tasks — no new infrastructure required)*

---

## Phase 3: User Story 1 - Convert CSV using STU 1 profile version (Priority: P1) 🎯 MVP

**Goal**: Update the SAFR IG version constant so all generated FHIR Bundles declare conformance to version `1.0.0` instead of `1.0.0-ballot`.

**Independent Test**: Run the converter on any valid bed capacity CSV and inspect output JSON — all profile URLs and Measure URL should contain `|1.0.0` (not `|1.0.0-ballot`).

### Implementation for User Story 1

- [X] T001 [US1] Update SAFR_IG_VERSION constant from "1.0.0-ballot" to "1.0.0" in convert.py (line 38)
- [X] T002 [US1] Verify all derived constants (BUNDLE_PROFILE, ORG_PROFILE, MEASURE_URL) resolve correctly by running the converter against test fixtures and inspecting output in output/

**Checkpoint**: At this point, all generated FHIR Bundles reference IG version `1.0.0`. User Story 1 is complete and independently verifiable.

---

## Phase 4: User Story 2 - Validate output against published STU 1 IG (Priority: P1)

**Goal**: Confirm that generated FHIR Bundles pass validation against the published `hl7.fhir.us.safr#1.0.0` IG package with zero errors.

**Independent Test**: Run the FHIR validator with `-ig hl7.fhir.us.safr#1.0.0` against all output Bundles and confirm zero errors.

### Implementation for User Story 2

- [X] T003 [US2] Run the full LLM validation pipeline per CLAUDE.md: convert all test fixtures, extract IG version, validate with validator_cli.jar against hl7.fhir.us.safr#1.0.0, confirm zero errors
- [X] T004 [US2] If validation reveals structural differences between ballot and STU 1 profiles, fix any conformance issues in convert.py and re-validate

**Checkpoint**: FHIR validation passes with zero errors against the STU 1 IG. Feature is complete.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and cleanup.

- [X] T005 Run quickstart.md validation steps to confirm end-to-end workflow

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 3 (US1)**: No dependencies — can start immediately
- **Phase 4 (US2)**: Depends on Phase 3 (US1) completion — needs updated output to validate
- **Phase 5 (Polish)**: Depends on Phase 4 (US2) completion

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies — single constant change
- **User Story 2 (P1)**: Depends on US1 — validates the output produced by the updated converter

### Within Each User Story

- US1: T001 → T002 (change constant, then verify output)
- US2: T003 → T004 (validate, then fix if needed)

### Parallel Opportunities

- Limited parallelism for this feature due to sequential dependency (must change version before validating)
- T001 is the critical path — everything flows from this single change

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001: Update the version constant
2. Complete T002: Verify output contains correct version strings
3. **STOP and VALIDATE**: Inspect output JSON files

### Incremental Delivery

1. T001 → T002: Version constant updated, output verified → MVP complete
2. T003 → T004: FHIR validation confirms conformance → Feature complete
3. T005: Final quickstart walkthrough → Fully validated

---

## Notes

- This is a minimal-change feature: 1 constant, 0 new files, 0 structural changes
- The FHIR validation step (T003) is the most important quality gate
- If T003 reveals errors, T004 becomes the critical remediation task
- Commit after T001 (the version change) and again after T003 (validation pass)
