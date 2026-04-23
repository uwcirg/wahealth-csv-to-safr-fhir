# Feature Specification: CDC NHSN SAFR Content IG Integration

**Feature Branch**: `006-content-ig-integration`
**Created**: 2026-04-23
**Status**: Draft
**Input**: Research findings from conversation and constitution v1.4.0

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Correct Measure Canonical URL (Priority: P1)

A hospital data manager runs the converter against a bed capacity CSV.
The generated MeasureReport references the CDC NHSN Content IG's
canonical BedCapacityMeasure URL instead of the base IG's example
Measure URL. This ensures the MeasureReport points to the
authoritative, computable Measure definition that CDC systems expect.

**Why this priority**: The current `MEASURE_URL` points to a canonical
under `http://hl7.org/fhir/us/safr/Measure/BedCapacityMeasure`, but
the base IG only publishes an *example* Measure at
`Measure/BedCapacityMeasureExample` (informational). The real
computable BedCapacityMeasure is defined by the Content IG at
`http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure`.
Getting this canonical correct is the most impactful change because it
determines whether MeasureReports reference the right Measure.

**Independent Test**: Convert a test CSV fixture and verify the
`MeasureReport.measure` field in the output Bundle contains the
Content IG's canonical URL
(`http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure`)
with the Content IG version appended.

**Acceptance Scenarios**:

1. **Given** a valid bed capacity CSV and config, **When** the
   converter runs, **Then** every generated MeasureReport's `measure`
   field equals
   `http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure|<CONTENT_IG_VERSION>`.
2. **Given** the Content IG version constant is changed, **When** the
   converter runs, **Then** the updated version propagates to the
   `measure` field without other code changes.

---

### User Story 2 - Content IG Version Tracking (Priority: P1)

A developer or LLM agent can determine which version of the CDC NHSN
SAFR Content IG the converter targets by reading a single named
constant in `convert.py`. This constant is separate from the existing
`SAFR_IG_VERSION` (which tracks the base structural IG) because the
two IGs are independently versioned and published.

**Why this priority**: The constitution (v1.4.0) requires a separate
named constant for the Content IG version. This is a prerequisite for
User Stories 1 and 3 — the Measure URL and validation pipeline both
need this version value.

**Independent Test**: Verify that `convert.py` contains a named
constant (e.g., `SAFR_CI_IG_VERSION`) set to a valid semver string,
that it has startup validation matching the existing
`SAFR_IG_VERSION` pattern, and that it is distinct from
`SAFR_IG_VERSION`.

**Acceptance Scenarios**:

1. **Given** `convert.py` is loaded, **When** the Content IG version
   constant is read, **Then** it returns a valid semver string (e.g.,
   `"1.0.0"`).
2. **Given** the Content IG version constant is set to an invalid
   value (e.g., empty string or `"abc"`), **When** the converter
   starts, **Then** it exits with a clear error message referencing
   the Content IG.
3. **Given** the Content IG version constant exists, **When** CI
   extracts it, **Then** it is programmatically accessible via the
   same pattern used for `SAFR_IG_VERSION`.

---

### User Story 3 - Dual-IG Validation Pipeline (Priority: P2)

A developer, LLM agent, or CI pipeline validates generated FHIR
Bundles against both the base structural IG and the Content IG in a
single validator invocation. This catches conformance issues against
Measure definitions and CodeSystems published by the Content IG that
the base IG alone cannot validate.

**Why this priority**: Validation currently only references the base
IG. Adding the Content IG to validation may surface new errors or
warnings that need to be evaluated and potentially documented in
`known-validation-issues.md`. This is lower priority than getting the
Measure URL correct but essential for ongoing conformance assurance.

**Independent Test**: Run the FHIR validator with both `-ig
hl7.fhir.us.safr#1.0.0` and `-ig gov.cdc.nhsn.safr#1.0.0` against
generated output and confirm the validator resolves both IGs
successfully.

**Acceptance Scenarios**:

1. **Given** generated FHIR Bundles, **When** the validator runs with
   both IG arguments, **Then** validation completes and reports
   results referencing both IGs.
2. **Given** the CI workflow, **When** the FHIR validation step runs,
   **Then** it passes both `-ig hl7.fhir.us.safr#$SAFR_IG_VERSION`
   and `-ig gov.cdc.nhsn.safr#$SAFR_CI_IG_VERSION` to the validator.
3. **Given** the CLAUDE.md LLM validation instructions, **When** an
   LLM agent reads them, **Then** the instructions include both IG
   arguments in the validator command.
4. **Given** the validator reports new errors from the Content IG,
   **When** those errors are attributable to upstream issues, **Then**
   they are documented in `known-validation-issues.md` following the
   existing format.

---

### Edge Cases

- What happens when the Content IG package (`gov.cdc.nhsn.safr`) is
  not yet available in the FHIR package registry? The validator may
  fail to resolve it. This must be handled gracefully in CI and LLM
  validation instructions.
- What happens when the two IGs have version skew (e.g., Content IG
  publishes v1.1.0 while base IG remains at v1.0.0)? Each version
  constant is independent, so they can be updated separately.
- What if the Content IG's BedCapacityMeasure uses different
  population group codes than what the converter currently maps? This
  would be a separate feature/fix, not part of this integration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The converter MUST declare the Content IG version as a
  named constant separate from the base IG version constant.
- **FR-002**: The Content IG version constant MUST have startup
  validation matching the existing semver pattern used for
  `SAFR_IG_VERSION`.
- **FR-003**: The `MeasureReport.measure` field MUST reference the
  Content IG's canonical URL
  (`http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure`)
  with the Content IG version appended.
- **FR-004**: The CI validation pipeline MUST pass both base IG and
  Content IG as `-ig` arguments to the FHIR validator.
- **FR-005**: The CLAUDE.md LLM validation instructions MUST be
  updated to include both IG arguments.
- **FR-006**: CI output MUST log which versions of both IGs were used
  for validation.
- **FR-007**: Any new upstream validation errors introduced by adding
  the Content IG MUST be evaluated and, if attributable to upstream
  issues, documented in `known-validation-issues.md`.

### Key Entities

- **SAFR_CI_IG_VERSION**: Named constant in `convert.py` holding the
  target Content IG version (e.g., `"1.0.0"`). Independent of
  `SAFR_IG_VERSION`.
- **MEASURE_URL**: Existing constant in `convert.py` that must be
  updated to use the Content IG's canonical URL and Content IG
  version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Generated MeasureReports reference the Content IG's
  BedCapacityMeasure canonical URL, not the base IG's example URL.
- **SC-002**: The Content IG version is declared and validated
  independently from the base IG version, with no code duplication
  of the validation logic.
- **SC-003**: Validation pipeline passes with zero project-introduced
  errors when both IGs are supplied to the validator.
- **SC-004**: Changing either IG version constant propagates to all
  dependent outputs and validation commands without other code changes.

## Assumptions

- The Content IG package `gov.cdc.nhsn.safr#1.0.0` is available in
  the FHIR package registry (packages.fhir.org or packages2.fhir.org)
  and resolvable by the HL7 FHIR validator. If not, the validator can
  be pointed at the package URL directly.
- The Content IG's BedCapacityMeasure uses the same LOINC population
  group codes that the converter currently maps. Code alignment
  verification is in scope for this feature; remapping codes is not.
- The initial Content IG version to target is `1.0.0`, matching the
  base IG version, but the two are independently versioned going
  forward.
- The constant name `SAFR_CI_IG_VERSION` is a working name; the
  implementation plan may refine naming to best communicate the
  distinction from `SAFR_IG_VERSION`.
