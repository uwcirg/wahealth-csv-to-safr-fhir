# Feature Specification: Update README with Content IG Documentation

**Feature Branch**: `007-readme-content-ig`
**Created**: 2026-04-23
**Status**: Draft
**Input**: Update the readme to incorporate the content IG capacity that we've added today.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Understand the Two-IG Architecture (Priority: P1)

A new contributor or hospital IT staff member reads the README to
understand how this project relates to the FHIR SAFR ecosystem.
They learn that the converter targets two IGs: the base US SAFR IG
(`hl7.fhir.us.safr`) for structural profiles and the CDC NHSN SAFR
Content IG (`gov.cdc.nhsn.safr`) for the authoritative Measure
definitions. They can find the URLs of both IGs and understand which
one provides what.

**Why this priority**: Without this context, readers assume the
project targets only one IG and may be confused by the two version
constants or the Measure canonical URL pointing to a CDC domain.

**Independent Test**: Read the README and confirm it names both IGs,
links to their publication sites, and explains the relationship
(Content IG depends on base IG; base provides profiles, Content
provides Measures).

**Acceptance Scenarios**:

1. **Given** the README, **When** a reader looks for IG information,
   **Then** they find both IG names, package IDs, publication URLs,
   and a brief description of what each provides.
2. **Given** the README, **When** a reader looks at the "FHIR profiles
   used" section, **Then** the Measure reference clarifies it comes
   from the Content IG, not the base IG.

---

### User Story 2 - Understand Version Tracking (Priority: P2)

A developer or LLM agent reads the README to understand how IG
versions are managed. They learn that the converter tracks two
independent version constants and can find the names of both constants
and what each controls.

**Why this priority**: Version tracking is a key project convention
that contributors need to understand to make correct changes. The
README is the first place they look.

**Independent Test**: Read the README and confirm it mentions both
version constants and explains they are independently versioned.

**Acceptance Scenarios**:

1. **Given** the README, **When** a contributor looks for version
   information, **Then** they find reference to both version tracking
   constants and understand how to update them.

---

### Edge Cases

- The Content IG package is not yet in the FHIR registry — the README
  should note this and point to the publication URL instead.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The README MUST name both IGs with their package IDs
  (`hl7.fhir.us.safr` and `gov.cdc.nhsn.safr`) and link to their
  publication sites.
- **FR-002**: The README MUST explain the relationship between the
  two IGs (Content IG depends on base IG; base provides profiles,
  Content provides Measure definitions and CodeSystems).
- **FR-003**: The "FHIR profiles used" section MUST indicate which
  IG each profile or Measure originates from.
- **FR-004**: The README MUST mention that the project tracks two
  independent IG version constants.
- **FR-005**: The README MUST note that the Content IG package is
  published at `https://safr-ci.nhsnlink.org` and is not yet in the
  standard FHIR package registry.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader can identify both IGs, their roles, and their
  publication URLs within the first 2 minutes of reading the README.
- **SC-002**: The "FHIR profiles used" table clearly attributes each
  profile to its source IG.
- **SC-003**: No existing README content is removed or degraded; all
  current sections remain functional and accurate.

## Assumptions

- The README update is purely documentation — no code changes are
  required.
- The target audience includes hospital IT staff, new contributors,
  and LLM agents. The language should be accessible to non-FHIR
  experts while remaining technically accurate.
- The existing README structure and sections are preserved; new
  content is added or woven into existing sections rather than
  replacing them.
