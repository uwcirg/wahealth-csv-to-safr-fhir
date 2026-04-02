# Feature Specification: Constitution v1.3.0 Repo Sync

**Feature Branch**: `005-constitution-repo-sync`  
**Created**: 2026-04-02  
**Status**: Draft  
**Input**: User description: "update the repo based on the updated constitution."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unit Tests for Computation Logic (Priority: P1)

A developer modifying aggregate bed calculations or data-parsing functions needs targeted unit tests that catch computation errors not detectable by FHIR profile validation alone. The constitution (Validation-Driven Testing) requires supplementary unit tests for computation logic such as aggregate calculations, unoccupied-bed clamping, and date parsing.

Currently the `tests/` directory does not exist and no unit tests are present. The only testing is end-to-end FHIR validation.

**Why this priority**: Computation correctness is a data integrity requirement. Profile validation confirms structure but cannot verify that aggregate sums are calculated correctly or that `safe_int()` handles edge cases properly. Incorrect aggregate counts in public health reports are worse than structural errors because they pass validation silently.

**Independent Test**: Can be fully tested by running a test suite against `convert.py` functions and verifying correct outputs for known inputs, independent of FHIR validation.

**Acceptance Scenarios**:

1. **Given** the converter codebase, **When** a developer runs the test suite, **Then** unit tests execute for `safe_int()`, `get_occupied_and_unoccupied()`, `parse_reporting_date()`, `compute_groups()`, and aggregate calculation functions.
2. **Given** a CSV row with empty or non-numeric fields, **When** `safe_int()` processes them, **Then** it returns 0 and the test confirms logging occurred.
3. **Given** a CSV row where occupied beds exceed total capacity, **When** `get_occupied_and_unoccupied()` computes unoccupied, **Then** the result is clamped to 0 (never negative).
4. **Given** a complete CSV row, **When** `compute_groups()` runs, **Then** all 25 groups are produced and aggregate sums (AllBeds, AdultTotal, PedsTotal, SpecialtyTotal) match manual calculations.

---

### User Story 2 - Known-Issue Filtering Parity Between LLM and CI (Priority: P2)

An LLM agent developing on the repo must apply the same known-issue filtering as CI when running local validation. The constitution (v1.3.0) explicitly states: "LLM agents performing local validation SHOULD apply the same known-issue filtering as CI." Currently, CLAUDE.md documents the 4-step validation pipeline but does not include filtering instructions matching the CI's `grep -v` patterns.

**Why this priority**: Without filtering instructions, LLM agents may report known upstream errors as blockers, wasting development time and creating unnecessary back-and-forth with the user.

**Independent Test**: Can be tested by verifying that CLAUDE.md contains filtering guidance consistent with CI and `known-validation-issues.md`.

**Acceptance Scenarios**:

1. **Given** the CLAUDE.md validation pipeline instructions, **When** an LLM agent follows them, **Then** the instructions include how to identify and filter known upstream errors documented in `known-validation-issues.md`.
2. **Given** FHIR validation output containing only known upstream errors, **When** the LLM agent applies filtering, **Then** the agent treats validation as passing (not a blocker).

---

### User Story 3 - CI Logs IG Version for Reproducibility (Priority: P3)

A developer reviewing CI output needs to know exactly which SAFR IG version was used for validation. The constitution requires: "CI output and test artifacts MUST record which version of the SAFR IG was used for validation." The current CI logs the version but could be more prominent and formatted for traceability.

**Why this priority**: Reproducibility and auditability of validation results. When investigating a CI failure weeks later, the IG version used must be unambiguous in the logs.

**Independent Test**: Can be tested by reviewing CI workflow output and confirming the IG version appears clearly in the log.

**Acceptance Scenarios**:

1. **Given** a CI run, **When** the FHIR validation step executes, **Then** the log output prominently displays the SAFR IG version used.
2. **Given** a CI run, **When** the validation completes, **Then** the summary includes the IG version alongside the pass/fail result.

---

### Edge Cases

- What happens when `known-validation-issues.md` documents a new upstream error pattern? The CI filter and LLM instructions must both be updated in tandem.
- What happens when an upstream fix resolves a known issue? The corresponding entry must be retested and removed, and CI filters updated.
- What happens when unit tests are added but `compute_groups()` behavior changes for a new IG version? Tests must be updated alongside the IG version bump.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST include unit tests for core computation functions: `safe_int()`, `get_occupied_and_unoccupied()`, `parse_reporting_date()`, and `compute_groups()`.
- **FR-002**: Unit tests MUST verify that aggregate calculations (AllBeds, AdultTotal, PedsTotal, SpecialtyTotal) produce correct sums from raw CSV values.
- **FR-003**: Unit tests MUST verify that `safe_int()` returns 0 for empty strings, non-numeric values, and None inputs.
- **FR-004**: Unit tests MUST verify that unoccupied bed counts are clamped to 0 when occupied exceeds capacity.
- **FR-005**: The CLAUDE.md validation pipeline MUST include guidance on filtering known upstream validation errors, referencing `known-validation-issues.md`.
- **FR-006**: The CI pipeline MUST log the SAFR IG version prominently in validation output.
- **FR-007**: Unit tests MUST run as part of the CI pipeline.

### Key Entities

- **Test Fixture**: Known CSV input data with expected computation outputs, used to verify converter logic independent of FHIR validation.
- **Known Validation Issue**: A documented upstream FHIR validation error with exact error pattern, root cause, and responsible party. Used by both CI and LLM agents for filtering.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of core computation functions (`safe_int`, `get_occupied_and_unoccupied`, `parse_reporting_date`, `compute_groups`) have at least one passing unit test.
- **SC-002**: All 25 MeasureReport groups produced by `compute_groups()` are verified against manually calculated expected values in at least one test case.
- **SC-003**: LLM agents following CLAUDE.md instructions can distinguish known upstream errors from project-introduced errors without consulting additional files beyond those referenced.
- **SC-004**: CI logs display the SAFR IG version in every FHIR validation run, identifiable within 10 seconds of reviewing the output.
- **SC-005**: The CI pipeline runs unit tests and reports pass/fail status alongside lint and FHIR validation results.

## Assumptions

- The existing `convert.py` functions (`safe_int`, `get_occupied_and_unoccupied`, `parse_reporting_date`, `compute_groups`) are importable for unit testing without modification to the file structure (no module extraction needed at ~819 lines, under the ~1000-line threshold).
- The test framework will use Python's built-in `unittest` module to maintain the zero-dependency runtime philosophy (dev dependencies are acceptable but stdlib is preferred where sufficient).
- The existing test CSV fixture (`input/2025.10.21.Test.Facility.BedCapacity.csv`) provides sufficient data for unit test verification.
- Test fixture relocation to a `test/` directory (mentioned in the constitution as planned) is not in scope for this feature; tests will work with the current `input/` directory layout.
