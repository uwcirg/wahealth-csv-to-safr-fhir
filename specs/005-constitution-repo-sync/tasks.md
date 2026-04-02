# Tasks: Constitution v1.3.0 Repo Sync

**Input**: Design documents from `/specs/005-constitution-repo-sync/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Unit tests are explicitly requested in this feature (User Story 1 is specifically about adding unit tests). Test tasks are included.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create test directory structure and verify import prerequisites

- [ ] T001 Create `tests/` directory with `tests/__init__.py` (empty) to establish the test package
- [ ] T002 Verify `convert.py` is importable by running `python -c "import convert"` from repo root

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blocking tasks for this feature. All three user stories are independent of each other and only depend on Phase 1 setup (tests/ directory existing for US1; no structural prerequisites for US2 or US3).

**Checkpoint**: Setup complete — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 — Unit Tests for Computation Logic (Priority: P1) MVP

**Goal**: Add unit tests for `safe_int()`, `get_occupied_and_unoccupied()`, `parse_reporting_date()`, and `compute_groups()` using Python stdlib `unittest`, verifying computation correctness that FHIR profile validation cannot detect.

**Independent Test**: Run `python -m unittest discover -s tests -p "test_*.py"` — all tests must pass.

### Implementation for User Story 1

- [ ] T003 [US1] Create test file `tests/test_compute.py` with unittest scaffolding: import `unittest`, add `sys.path` setup to import from repo root `convert.py`, create `TestSafeInt` class
- [ ] T004 [US1] Implement `TestSafeInt` tests in `tests/test_compute.py`: verify returns 0 for empty string, None, whitespace; returns correct int for valid numeric strings; verify behavior for non-numeric non-empty strings
- [ ] T005 [US1] Implement `TestGetOccupiedAndUnoccupied` tests in `tests/test_compute.py`: verify normal occupied/unoccupied split, verify unoccupied clamped to 0 when occupied > capacity, verify zero capacity edge case
- [ ] T006 [US1] Implement `TestParseReportingDate` tests in `tests/test_compute.py`: verify `MM/DD/YYYY` format returns correct `datetime.date`, verify edge cases (year boundaries, leap year dates)
- [ ] T007 [US1] Implement `TestComputeGroups` tests in `tests/test_compute.py`: build a complete CSV row dict using known values, call `compute_groups()`, verify exactly 25 groups returned, verify aggregate sums (AllBeds, AdultTotal, PedsTotal, SpecialtyTotal) match manual calculations from raw input values
- [ ] T008 [US1] Run full test suite via `python -m unittest discover -s tests -p "test_*.py"` and confirm all tests pass

**Checkpoint**: Unit tests for all four core computation functions pass. User Story 1 complete.

---

## Phase 4: User Story 2 — Known-Issue Filtering Parity Between LLM and CI (Priority: P2)

**Goal**: Update CLAUDE.md Step 4 of the LLM Validation Pipeline to include explicit known-issue filtering guidance matching CI's `grep -v` patterns, referencing `known-validation-issues.md`.

**Independent Test**: Read updated CLAUDE.md Step 4 and confirm it includes: (1) reference to `known-validation-issues.md`, (2) the specific error patterns to filter (`extension-MeasureReport.supplementalData` and `Slice 'Bundle.entry:measurereport': a matching slice is required`), (3) instruction that validation passes if only known upstream errors remain.

### Implementation for User Story 2

- [ ] T009 [US2] Update Step 4 in `CLAUDE.md` to add explicit filtering guidance: list the two known upstream error patterns (matching CI's `grep -v` in `.github/workflows/ci.yml`), reference `known-validation-issues.md` as the source of truth, and instruct LLM agents to treat validation as passing when only known upstream errors are present
- [ ] T010 [US2] Verify consistency: confirm the error patterns in updated CLAUDE.md match both the CI `grep -v` patterns in `.github/workflows/ci.yml` and the entries in `known-validation-issues.md`

**Checkpoint**: CLAUDE.md provides LLM agents with the same known-issue filtering as CI. User Story 2 complete.

---

## Phase 5: User Story 3 — CI Logs IG Version for Reproducibility (Priority: P3)

**Goal**: Improve CI IG version logging so the version is prominent in both pre-validation and post-validation output, and add a `unit-test` job to the CI pipeline.

**Independent Test**: Review `.github/workflows/ci.yml` diff and confirm: (1) IG version log line has a space after the colon, (2) IG version appears in the post-validation summary, (3) a new `unit-test` job runs `python -m unittest discover`.

### Implementation for User Story 3

- [ ] T011 [P] [US3] Fix IG version log formatting in `.github/workflows/ci.yml`: add space after colon in `echo "Validating against SAFR IG version:$SAFR_IG_VERSION"` → `echo "Validating against SAFR IG version: $SAFR_IG_VERSION"`
- [ ] T012 [P] [US3] Add IG version to post-validation summary in `.github/workflows/ci.yml`: include `$SAFR_IG_VERSION` in both the `::error::` and `::warning::` output messages
- [ ] T013 [US3] Add `unit-test` job to `.github/workflows/ci.yml`: new job using `actions/setup-python@v5` with `python-version: "3.x"`, running `python -m unittest discover -s tests -p "test_*.py"`

**Checkpoint**: CI logs IG version prominently and runs unit tests. User Story 3 complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all changes

- [ ] T014 Run the full LLM Validation Pipeline (Steps 1–4 from CLAUDE.md) to confirm no regressions
- [ ] T015 Run quickstart.md validation: execute unit tests, verify CLAUDE.md changes, confirm CI changes match spec

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: No blocking tasks for this feature
- **User Story 1 (Phase 3)**: Depends on Phase 1 (`tests/` directory exists)
- **User Story 2 (Phase 4)**: No dependencies on other stories — modifies `CLAUDE.md` only
- **User Story 3 (Phase 5)**: No dependencies on other stories — modifies `.github/workflows/ci.yml` only. T013 (unit-test job) is most meaningful after US1 creates the tests, but the job itself can be added at any time.
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent. Creates `tests/test_compute.py`.
- **User Story 2 (P2)**: Independent. Modifies `CLAUDE.md`.
- **User Story 3 (P3)**: Independent. Modifies `.github/workflows/ci.yml`. Logically benefits from US1 (tests to run), but the CI job can be created in parallel.

### Within Each User Story

- US1: Scaffold → individual test classes → run suite
- US2: Update CLAUDE.md → verify consistency
- US3: Fix logging (parallel) → add unit-test job

### Parallel Opportunities

- **US1, US2, and US3 can all be worked on in parallel** — they modify different files with no dependencies
- Within US3: T011 and T012 can run in parallel (both modify `ci.yml` but different sections)

---

## Parallel Example: User Story 1

```bash
# T004, T005, T006 could technically be parallelized (different test classes)
# but they share the same file (tests/test_compute.py), so sequential is safer.
# T007 depends on understanding of compute_groups() output structure.

# Cross-story parallelism is the main opportunity:
Task: "T009 [US2] Update Step 4 in CLAUDE.md"  # can run alongside US1
Task: "T011 [US3] Fix IG version log formatting in ci.yml"  # can run alongside US1
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`tests/` directory)
2. Complete Phase 3: User Story 1 (unit tests)
3. **STOP and VALIDATE**: Run `python -m unittest discover -s tests -p "test_*.py"` — all tests pass
4. This delivers the highest-value constitution compliance: computation correctness verification

### Incremental Delivery

1. Complete Setup → `tests/` directory ready
2. Add User Story 1 (unit tests) → Test independently → Constitution: Validation-Driven Testing satisfied
3. Add User Story 2 (CLAUDE.md update) → Verify filtering guidance → Constitution: LLM filtering parity satisfied
4. Add User Story 3 (CI improvements) → Push branch, check Actions → Constitution: CI Pipeline requirements satisfied
5. Polish → Full validation pipeline run → All constitution v1.3.0 requirements met

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- All three user stories are fully independent — they touch different files
- The spec explicitly requests unit tests (US1), so test tasks are included
- Total: 15 tasks across 6 phases
- Commit after each user story completion for clean git history
