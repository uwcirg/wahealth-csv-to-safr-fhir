# Tasks: Update README with Content IG Documentation

**Input**: Design documents from `/specs/007-readme-content-ig/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup

(No setup tasks — single-file documentation update, no project initialization needed.)

---

## Phase 2: User Story 1 — Understand the Two-IG Architecture (Priority: P1)

**Goal**: README documents both IGs, their relationship, publication URLs, and what each provides. The "FHIR profiles used" table attributes each entry to its source IG.

**Independent Test**: Read the README and confirm it names both IGs (`hl7.fhir.us.safr` and `gov.cdc.nhsn.safr`), links to both publication sites, and explains the Content IG depends on the base IG.

- [X] T001 [US1] Expand the opening description in `README.md` (line 3) to mention the converter targets both the US SAFR IG and the CDC NHSN SAFR Content IG
- [X] T002 [US1] Add a new "## FHIR Implementation Guides" section in `README.md` after the existing "## FHIR profiles used" section, containing a table with columns: IG Name, Package ID, Publication URL, What It Provides — with rows for `hl7.fhir.us.safr` (profiles) and `gov.cdc.nhsn.safr` (Measures, CodeSystems). Note that the Content IG package is not yet in the FHIR registry and is published at `https://safr-ci.nhsnlink.org`
- [X] T003 [US1] Update the "## FHIR profiles used" table in `README.md` (lines 96-103) to add a "Source" column indicating which IG each profile originates from, and add a row for `BedCapacityMeasure` from the Content IG

**Checkpoint**: README clearly documents both IGs, their roles, and their publication URLs. A new reader can understand the two-IG architecture.

---

## Phase 3: User Story 2 — Understand Version Tracking (Priority: P2)

**Goal**: README documents the two independent version tracking constants so contributors know how IG versions are managed.

**Independent Test**: Read the README and confirm it mentions both `SAFR_IG_VERSION` and `NHSN_SAFR_IG_VERSION` and explains they are independently versioned.

- [X] T004 [US2] Add a version tracking paragraph to the "## FHIR Implementation Guides" section in `README.md`, explaining that the converter declares two independent version constants (`SAFR_IG_VERSION` for the base IG, `NHSN_SAFR_IG_VERSION` for the Content IG) and that updating either is a deliberate, reviewable change

**Checkpoint**: Contributors can find version tracking information in the README without reading the constitution.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T005 Run `quickstart.md` verification steps from `specs/007-readme-content-ig/quickstart.md` to confirm all checks pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **User Story 1 (Phase 2)**: No dependencies — can start immediately
- **User Story 2 (Phase 3)**: Depends on T002 (adds content to the section T002 creates)
- **Polish (Phase 4)**: Depends on all user stories complete

### Within Each User Story

- T001 → T002 → T003 (sequential within the same file)
- T004 depends on T002 (adds to section created by T002)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001-T003: Two-IG architecture documented
2. **STOP and VALIDATE**: Reader can understand both IGs
3. This alone delivers the primary documentation value

### Incremental Delivery

1. T001-T003: Two-IG architecture (MVP)
2. T004: Version tracking
3. T005: Final verification

---

## Notes

- All tasks modify the same file (`README.md`) so must run sequentially
- No code changes — documentation only
- Commit after T003 (US1 complete) and again after T004 (US2 complete)
