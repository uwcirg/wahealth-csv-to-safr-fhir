# Feature Specification: IG Version Tracking

**Feature Branch**: `002-ig-version-tracking`  
**Created**: 2026-04-02  
**Status**: Draft  
**Input**: User description: "update the repo based on the updated constitution."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declare Target IG Version (Priority: P1)

A developer or data manager can determine which version of the US SAFR Implementation Guide the converter targets by inspecting a single, clearly named constant or configuration value in the code. This version declaration is programmatically accessible and not buried in comments.

**Why this priority**: The constitution (v1.1.0) mandates that the code MUST declare the target IG version as a named constant or configuration value. This is the foundational requirement that all other IG version tracking features depend on.

**Independent Test**: Verify that a named constant exists in the converter source declaring the SAFR IG version (e.g., `SAFR_IG_VERSION = "1.0.0-ballot"`), and that this constant is used wherever the IG version appears in generated output.

**Acceptance Scenarios**:

1. **Given** the converter source code, **When** a developer searches for the IG version declaration, **Then** they find a single, clearly named constant (not a comment) that specifies the target US SAFR IG version.
2. **Given** the IG version constant, **When** it is changed, **Then** all generated FHIR output reflects the updated version without requiring changes elsewhere in the code.

---

### User Story 2 - Include IG Version in Generated FHIR Output (Priority: P2)

When the converter generates FHIR Bundles, the profile canonical URLs for SAFR-specific profiles include the target IG version (using the `|version` syntax), so that downstream consumers can determine which IG version the output conforms to.

**Why this priority**: The constitution states generated resources SHOULD include the target IG version in profile canonical URLs where the IG specifies versioned canonicals. This makes output self-describing and traceable.

**Independent Test**: Run the converter against a test CSV, inspect the output Bundle JSON, and verify that SAFR-specific profile URLs include the `|version` suffix derived from the declared IG version constant.

**Acceptance Scenarios**:

1. **Given** a test CSV input, **When** the converter produces a FHIR Bundle, **Then** the Bundle profile URL, Organization profile URL, and any other SAFR-defined profiles include the IG version suffix (e.g., `http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-measurereport-bundle|1.0.0-ballot`).
2. **Given** the IG version constant is updated to a new version, **When** the converter runs, **Then** all SAFR profile URLs in the output reflect the new version.

---

### User Story 3 - Validate Against Specific IG Version in CI (Priority: P3)

The CI pipeline invokes the HL7 FHIR Validator with an explicit, versioned IG reference (e.g., `-ig hl7.fhir.us.safr#1.0.0-ballot`) rather than an unversioned reference, so that validation results are reproducible and tied to a known IG release.

**Why this priority**: The constitution requires that validation be reproducible by specifying the exact IG version. This ensures that test results are meaningful and regressions from IG version changes are detectable.

**Independent Test**: Inspect the CI configuration and verify the FHIR validator command includes a versioned `-ig` argument. Run the CI pipeline and confirm the output logs record which IG version was used.

**Acceptance Scenarios**:

1. **Given** the CI pipeline configuration, **When** the FHIR validation step runs, **Then** the validator is invoked with `-ig hl7.fhir.us.safr#<version>` where `<version>` matches the declared IG version constant.
2. **Given** a CI run completes, **When** a developer reviews CI output, **Then** the log clearly states which SAFR IG version was used for validation.

---

### Edge Cases

- What happens when the IG version constant is empty or malformed? The converter should fail at startup with a clear error message rather than producing output with missing version information.
- What happens when profile URLs in the IG do not support versioned canonicals (e.g., external profiles like QICore or DEQM)? Only SAFR-defined profiles should include the SAFR IG version; external profiles should retain their own versioning.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST declare the target US SAFR IG version as a single named constant, programmatically accessible and not buried in comments.
- **FR-002**: System MUST use the declared IG version constant when constructing SAFR-specific profile canonical URLs in generated FHIR resources, appending `|<version>` to the profile URL.
- **FR-003**: System MUST apply versioned canonicals only to profiles defined by the US SAFR IG (`us-safr-measurereport-bundle`, `us-safr-submitting-organization`). External profiles (QICore, DEQM, CRMI) MUST retain their existing versioning.
- **FR-004**: System MUST derive the FHIR Validator `-ig` argument from the same IG version constant (or a CI configuration variable sourced from it), ensuring the validation target matches the code's declared conformance target.
- **FR-005**: CI output MUST log the SAFR IG version used for validation so results are traceable and reproducible.
- **FR-006**: When the IG version constant is updated, the change MUST be a deliberate, reviewable code change (not automatic or silent), and a full validation pass against the new version MUST succeed before merging.

### Key Entities

- **SAFR IG Version**: A version string (e.g., `"1.0.0-ballot"`) identifying which release of the US SAFR Implementation Guide the converter targets. Used in profile URLs, validation commands, and CI logging.
- **SAFR Profile URLs**: Canonical URLs for FHIR StructureDefinitions defined by the SAFR IG. These are the only URLs that receive the `|version` suffix from the IG version constant.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single source of truth for the target IG version exists in the codebase and is programmatically accessible (not a comment or documentation-only reference).
- **SC-002**: All SAFR-defined profile URLs in generated FHIR output include the declared IG version, verifiable by inspecting any output Bundle JSON.
- **SC-003**: Changing the IG version constant and re-running the converter produces output with updated profile URLs, requiring no other code changes.
- **SC-004**: CI validation logs explicitly state which SAFR IG version was used, verifiable by reading CI output from any pipeline run.
- **SC-005**: The FHIR Validator passes with zero errors when run against generated output using the versioned IG reference.

## Assumptions

- The current target SAFR IG version is `1.0.0-ballot`, based on the existing `MEASURE_URL` constant which already includes `|1.0.0-ballot`.
- Only profiles with the `http://hl7.org/fhir/us/safr/` prefix are SAFR-defined and should receive the IG version suffix. External profiles (QICore, DEQM, CRMI) are versioned independently by their own IGs.
- The CI pipeline uses GitHub Actions, as stated in the constitution.
- The HL7 FHIR Validator CLI (`validator_cli.jar`) supports the `-ig` flag with versioned package references (e.g., `hl7.fhir.us.safr#1.0.0-ballot`).
- The single-file structure of `convert.py` is maintained per the constitution's "Single-File Simplicity" principle.
