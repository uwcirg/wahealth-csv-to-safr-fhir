# Tasks: IG Version Tracking

**Input**: Design documents from `/specs/002-ig-version-tracking/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: No test tasks generated — tests were not explicitly requested in the feature specification. Validation is performed via `validator_cli.jar` in CI (User Story 3).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No project initialization needed — this feature modifies two existing files (`convert.py` and `.github/workflows/ci.yml`). No new files or dependencies are introduced per the Single-File Simplicity principle.

*(No setup tasks required)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational infrastructure needed — User Story 1 establishes the constant that US2 and US3 depend on. Proceeding directly to user story phases.

*(No foundational tasks required)*

---

## Phase 3: User Story 1 — Declare Target IG Version (Priority: P1) 🎯 MVP

**Goal**: Establish a single, clearly named `SAFR_IG_VERSION` constant in `convert.py` as the sole source of truth for the target US SAFR IG version. Refactor the existing hardcoded version in `MEASURE_URL` to use this constant.

**Independent Test**: Verify that `SAFR_IG_VERSION` exists as a named constant in `convert.py`, that `MEASURE_URL` derives its version from it, and that an empty or malformed version causes the converter to exit with a clear error at startup.

### Implementation for User Story 1

- [ ] T001 [US1] Add `SAFR_IG_VERSION = "1.0.0-ballot"` constant near the top of convert.py (before existing profile URL constants, around line 36)
- [ ] T002 [US1] Add startup validation for `SAFR_IG_VERSION` in convert.py — regex check `^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$`, exit with code 1 and clear error message if empty or malformed
- [ ] T003 [US1] Refactor `MEASURE_URL` in convert.py to use f-string with `SAFR_IG_VERSION` instead of hardcoded `|1.0.0-ballot` (line ~54)

**Checkpoint**: `SAFR_IG_VERSION` constant exists and is validated at startup. `MEASURE_URL` derives its version from the constant. Changing `SAFR_IG_VERSION` updates the Measure URL automatically. The converter exits with a clear error if the version is invalid.

---

## Phase 4: User Story 2 — Include IG Version in Generated FHIR Output (Priority: P2)

**Goal**: All SAFR-defined profile canonical URLs in generated FHIR output include the `|version` suffix derived from `SAFR_IG_VERSION`. External profiles (QICore, DEQM, CRMI) remain unchanged.

**Independent Test**: Run the converter against a test CSV, inspect the output Bundle JSON, and verify that `BUNDLE_PROFILE` and `ORG_PROFILE` URLs include `|1.0.0-ballot` while external profile URLs are unmodified.

### Implementation for User Story 2

- [ ] T004 [P] [US2] Update `BUNDLE_PROFILE` constant in convert.py to append `|{SAFR_IG_VERSION}` using f-string (line ~37)
- [ ] T005 [P] [US2] Update `ORG_PROFILE` constant in convert.py to append `|{SAFR_IG_VERSION}` using f-string (line ~38)
- [ ] T006 [US2] Verify external profile constants (`MEASUREREPORT_PROFILE`, `QICORE_ORG_PROFILE`, `LOCATION_PROFILE`, `DEVICE_PROFILE`) in convert.py are NOT modified — confirm they retain their existing versioning

**Checkpoint**: Generated FHIR output includes versioned SAFR profile URLs. External profiles are unchanged. Changing `SAFR_IG_VERSION` updates all SAFR profile URLs in output without other code changes.

---

## Phase 5: User Story 3 — Validate Against Specific IG Version in CI (Priority: P3)

**Goal**: CI pipeline validates generated FHIR output against the exact IG version declared in `SAFR_IG_VERSION`, and logs which version was used for traceability.

**Independent Test**: Inspect `.github/workflows/ci.yml` and verify the validator command uses `-ig hl7.fhir.us.safr#<version>` with the version extracted from `convert.py`. Confirm the CI output logs the IG version.

### Implementation for User Story 3

- [ ] T007 [US3] Add a step in .github/workflows/ci.yml to extract `SAFR_IG_VERSION` from convert.py using Python one-liner: `python3 -c "import re; m=re.search(r\"SAFR_IG_VERSION\s*=\s*['\"]([^'\"]+)['\"]\", open('convert.py').read()); print(m.group(1))"`
- [ ] T008 [US3] Add an echo step in .github/workflows/ci.yml to log the extracted IG version: `echo "Validating against SAFR IG version: $SAFR_IG_VERSION"`
- [ ] T009 [US3] Update the FHIR Validator invocation in .github/workflows/ci.yml to use `-ig hl7.fhir.us.safr#$SAFR_IG_VERSION` instead of unversioned `-ig hl7.fhir.us.safr` (line ~58)

**Checkpoint**: CI validates against the exact IG version. CI logs clearly state which SAFR IG version was used. Changing `SAFR_IG_VERSION` in `convert.py` automatically updates the CI validation target.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end verification across all stories

- [ ] T010 Run converter against test CSV (`input/2025.10.21.Test.Facility.BedCapacity.csv`) and verify output matches quickstart.md expectations in convert.py
- [ ] T011 Verify that changing `SAFR_IG_VERSION` to a different value (e.g., `"1.0.0"`) propagates to all SAFR profile URLs and CI validation without other code changes in convert.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Skipped — no initialization needed
- **Foundational (Phase 2)**: Skipped — no shared infrastructure needed
- **User Story 1 (Phase 3)**: Can start immediately — establishes the `SAFR_IG_VERSION` constant
- **User Story 2 (Phase 4)**: Depends on US1 (needs `SAFR_IG_VERSION` constant to exist)
- **User Story 3 (Phase 5)**: Depends on US1 (needs `SAFR_IG_VERSION` constant to extract)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies — MVP deliverable
- **User Story 2 (P2)**: Depends on US1 (T001 must be complete before T004/T005)
- **User Story 3 (P3)**: Depends on US1 (T001 must be complete before T007). Independent of US2.

### Within Each User Story

- US1: T001 → T002 (validation needs constant to exist) → T003 (refactor uses constant)
- US2: T004 and T005 can run in parallel [P]. T006 is a verification step after T004/T005.
- US3: T007 → T008 → T009 (sequential — each builds on previous CI step)

### Parallel Opportunities

- US2 T004 and T005 can run in parallel (different constants, no dependency)
- US2 and US3 can start in parallel after US1 completes (US2 modifies `convert.py`, US3 modifies `ci.yml` — different files)

---

## Parallel Example: User Story 2

```bash
# After US1 is complete, launch both profile updates in parallel:
Task: "Update BUNDLE_PROFILE constant in convert.py"
Task: "Update ORG_PROFILE constant in convert.py"
```

## Parallel Example: US2 + US3 Cross-Story

```bash
# After US1 is complete, both stories can start in parallel (different files):
Story US2: "Update profile constants in convert.py"
Story US3: "Update CI validation in .github/workflows/ci.yml"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 3: User Story 1 (T001 → T002 → T003)
2. **STOP and VALIDATE**: Verify `SAFR_IG_VERSION` exists, is validated at startup, and `MEASURE_URL` uses it
3. This alone satisfies SC-001 (single source of truth)

### Incremental Delivery

1. Add User Story 1 → Constant exists and is validated → MVP!
2. Add User Story 2 → All SAFR profiles versioned in output → SC-002, SC-003
3. Add User Story 3 → CI validates against exact version → SC-004, SC-005
4. Polish → End-to-end verification
5. Each story adds value without breaking previous stories

---

## Notes

- All changes are in two existing files: `convert.py` and `.github/workflows/ci.yml`
- No new files, dependencies, or project structure changes
- [P] tasks = different constants/files, no dependencies
- [Story] label maps task to specific user story for traceability
- External profiles (QICore, DEQM, CRMI) must NOT be modified per FR-003
- Initial version is `1.0.0-ballot`; upgrading to `1.0.0` is a follow-up change
