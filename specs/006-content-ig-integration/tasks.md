# Tasks: CDC NHSN SAFR Content IG Integration

**Input**: Design documents from `/specs/006-content-ig-integration/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project structure needed. This feature modifies existing files only.

(No setup tasks — project structure is already in place.)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the Content IG version constant, which US1 and US3 both depend on.

**CRITICAL**: User Story 1 (MEASURE_URL) and User Story 3 (validation pipeline) both depend on this constant existing.

- [X] T001 Add `NHSN_SAFR_IG_VERSION = "1.0.0"` constant in `convert.py` immediately after the existing `SAFR_IG_VERSION` constant (after line 38)
- [X] T002 Add startup validation for `NHSN_SAFR_IG_VERSION` in `convert.py` — reuse the same semver regex pattern as `SAFR_IG_VERSION` (lines 40-43), with error message referencing "NHSN_SAFR_IG_VERSION" and the Content IG package name `gov.cdc.nhsn.safr`
- [X] T003 Add inline comment above `NHSN_SAFR_IG_VERSION` in `convert.py` clarifying it tracks the CDC NHSN SAFR Content IG (`gov.cdc.nhsn.safr`), distinct from `SAFR_IG_VERSION` which tracks the base HL7 IG (`hl7.fhir.us.safr`)

**Checkpoint**: `NHSN_SAFR_IG_VERSION` constant exists with startup validation. Converter starts normally with valid version. Converter exits with clear error on invalid version. Both constants are independently documented.

---

## Phase 3: User Story 1 — Correct Measure Canonical URL (Priority: P1)

**Goal**: Update `MEASURE_URL` to reference the Content IG's authoritative BedCapacityMeasure canonical URL instead of the base IG's example Measure URL.

**Independent Test**: Convert a test CSV and verify `MeasureReport.measure` contains `http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure|1.0.0`.

- [X] T004 [US1] Update `MEASURE_URL` constant in `convert.py` (line 62) from `f"http://hl7.org/fhir/us/safr/Measure/BedCapacityMeasure|{SAFR_IG_VERSION}"` to `f"http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure|{NHSN_SAFR_IG_VERSION}"`
- [X] T005 [US1] Run converter against test fixture `input/2025.10.21.Test.Facility.BedCapacity.csv` with `--config config.example.json --output-dir output` and verify the `MeasureReport.measure` field in generated output contains the Content IG canonical URL

**Checkpoint**: Generated FHIR output references the Content IG's BedCapacityMeasure. Changing `NHSN_SAFR_IG_VERSION` updates the Measure URL automatically.

---

## Phase 4: User Story 3 — Dual-IG Validation Pipeline (Priority: P2)

**Goal**: Expand CI and LLM validation to load both the base IG and the Content IG, catching conformance issues against Content IG definitions.

**Independent Test**: Run the FHIR validator with both `-ig hl7.fhir.us.safr#1.0.0` and `-ig https://safr-ci.nhsnlink.org/package.tgz` against generated output and confirm it completes.

**Note**: Research found the Content IG package is NOT in the FHIR registry. Use the package URL `https://safr-ci.nhsnlink.org/package.tgz` instead of registry-style `gov.cdc.nhsn.safr#1.0.0`.

### Implementation for User Story 3

- [X] T006 [US3] Add step in `.github/workflows/ci.yml` to extract `NHSN_SAFR_IG_VERSION` from `convert.py` using `grep -oP 'NHSN_SAFR_IG_VERSION\s*=\s*"\K[^"]+'` (after the existing `SAFR_IG_VERSION` extraction at line 57), and export to `$GITHUB_ENV`
- [X] T007 [US3] Update the log step in `.github/workflows/ci.yml` (line 60) to log both IG versions: `echo "Validating against SAFR IG version: $SAFR_IG_VERSION, NHSN SAFR Content IG: $NHSN_SAFR_IG_VERSION"`
- [X] T008 [US3] Update the FHIR validator invocation in `.github/workflows/ci.yml` (line 66-68) to add `-ig https://safr-ci.nhsnlink.org/package.tgz` after the existing `-ig hl7.fhir.us.safr#$SAFR_IG_VERSION` argument
- [X] T009 [US3] Update the `::error::` message in `.github/workflows/ci.yml` (line 86) to include both IG versions in the output
- [X] T010 [US3] Update the `::warning::` message in `.github/workflows/ci.yml` (line 91) to include both IG versions in the output
- [X] T011 [P] [US3] Update the LLM Validation Pipeline section in `CLAUDE.md` — Step 2: change "Extract the `SAFR_IG_VERSION` constant" to "Extract the `SAFR_IG_VERSION` and `NHSN_SAFR_IG_VERSION` constants"
- [X] T012 [P] [US3] Update the LLM Validation Pipeline section in `CLAUDE.md` — Step 3: update the validator command to include `-ig https://safr-ci.nhsnlink.org/package.tgz` after the existing `-ig` argument
- [X] T013 [US3] Run the full FHIR validation pipeline locally with both IGs: convert test fixtures, then validate with `java -jar validator_cli.jar output/**/*.json -version 4.0.1 -ig hl7.fhir.us.safr#$SAFR_IG_VERSION -ig https://safr-ci.nhsnlink.org/package.tgz`
- [X] T014 [US3] Evaluate validator output from T013: if new errors appear beyond the existing known issues, document them in `known-validation-issues.md` following the established format (error message, affected resource, root cause, responsible package, reproduction steps)
- [X] T015 [US3] If new known issues were added in T014, update the CI `grep -v` filter patterns in `.github/workflows/ci.yml` (lines 78-82) to exclude those new known upstream error patterns

**Checkpoint**: CI validates against both IGs. LLM validation instructions reference both IGs. Any new upstream errors are documented and filtered. Validation passes with zero project-introduced errors.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and documentation consistency

- [X] T016 Update the constitution reference in `.specify/memory/constitution.md` to replace `SAFR_CI_IG_VERSION` with `NHSN_SAFR_IG_VERSION` throughout (the spec used the working name; research decided on the final name)
- [X] T017 Run `quickstart.md` verification steps from `specs/006-content-ig-integration/quickstart.md` to confirm all checks pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: No dependencies — can start immediately. BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2 (needs `NHSN_SAFR_IG_VERSION` constant)
- **User Story 3 (Phase 4)**: Depends on Phase 2 (needs constant for extraction). Can run in parallel with US1 since it modifies different files (CI/CLAUDE.md vs convert.py constants).
- **Polish (Phase 5)**: Depends on all user stories complete.

### Within Each User Story

- T004 before T005 (need URL change before verifying output)
- T006-T010 sequential within CI file (each depends on prior step's context)
- T011-T012 parallel with T006-T010 (different file: CLAUDE.md)
- T013 after T004 and T008 (needs both MEASURE_URL change and validator command update)
- T014 after T013 (needs validator output to evaluate)
- T015 after T014 (only if new known issues found)

### Parallel Opportunities

```text
# After Phase 2 completes, these can run in parallel:
Stream A (convert.py): T004 → T005
Stream B (CI + CLAUDE.md): T006 → T007 → T008 → T009 → T010
                           T011, T012 (parallel with Stream B, different file)

# Then converge:
T013 (needs both streams complete) → T014 → T015
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 2: Add `NHSN_SAFR_IG_VERSION` constant
2. Complete Phase 3: Update `MEASURE_URL`
3. **STOP and VALIDATE**: Convert test CSV, verify output references Content IG canonical
4. Output is now correct even without dual-IG validation

### Incremental Delivery

1. Phase 2 → Foundation ready
2. Phase 3: User Story 1 → Correct Measure URL (MVP!)
3. Phase 4: User Story 3 → Dual-IG validation pipeline
4. Phase 5: Polish → Constitution naming cleanup, final verification

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- User Story 2 from spec (Content IG Version Tracking) is implemented as the Foundational phase (Phase 2) since it's a prerequisite for both other stories
- The Content IG package URL (`https://safr-ci.nhsnlink.org/package.tgz`) is used instead of registry-style `gov.cdc.nhsn.safr#1.0.0` because the package is not yet in the FHIR registry
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
