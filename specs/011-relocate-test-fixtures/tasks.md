---
description: "Task list for feature 011-relocate-test-fixtures"
---

# Tasks: Relocate test fixtures to test/input and route their output to test/output

**Input**: Design documents from `/specs/011-relocate-test-fixtures/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: No automated test tasks are generated — the spec requests none. Verification for this
feature *is* the end-to-end FHIR validation pipeline (US1), which is the project's primary test
strategy per the constitution.

**Organization**: Tasks are grouped by user story. The converter's source code is NOT modified;
all work is a history-preserving file move plus reference updates in CI, docs, and `.gitignore`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in each description

## Path Conventions

Single-project CLI at repository root. Fixtures move `input/` → `test/input/`; generated test
output goes to `test/output/`. Production default (`./output`) and `convert.py` are unchanged.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm starting state before relocating anything

- [X] T001 Confirm the working tree is on branch `011-relocate-test-fixtures` and clean, and that the four fixtures exist in `input/` (`2025.10.21.Test.Facility.BedCapacity.csv`, `2025.10.21.Test.Facility.BedCapacity.column-labels-only.csv`, `2026.04.30.Test.Facility.WAHealthDict.csv`, `census_20260511.FromKC.SubsetObfsctd.csv`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The physical relocation and ignore rule that every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Relocate the fixtures preserving git history: `mkdir -p test/input && git mv input/*.csv test/input/`, then remove the now-empty directory with `rmdir input` (verifies FR-001, FR-002)
- [X] T003 [P] Add `test/output/` to `.gitignore` directly beneath the existing `output/` entry (FR-008)

**Checkpoint**: Fixtures live in `test/input/`, `input/` is gone, generated test output is ignored — user stories can now begin (and run in parallel)

---

## Phase 3: User Story 1 - Run the regression validation against relocated fixtures (Priority: P1) 🎯 MVP

**Goal**: Prove the convert-then-validate pipeline works end to end over `test/input/` →
`test/output/` with zero project-introduced errors, and that production behavior is unchanged.

**Independent Test**: Convert every data fixture in `test/input/` to `test/output/`, run the HL7
validator over `test/output/`, and confirm zero errors beyond the two documented known-upstream
patterns.

### Implementation for User Story 1

- [X] T004 [US1] Convert each data fixture in `test/input/` (skipping `*column-labels-only*`) with `python3 convert.py "$csv" --config config.example.json --output-dir test/output`, confirming output lands only under `test/output/` in the per-facility layout (FR-003)
- [X] T005 [US1] Extract IG versions from `convert.py` and run `java -jar validator_cli.jar $(find test/output -name '*.json') -version 4.0.1 -ig hl7.fhir.us.safr#$SAFR_IG_VERSION -ig https://safr-ci.nhsnlink.org/package.tgz`; confirm zero errors except `extension-MeasureReport.supplementalData` and `Slice 'Bundle.entry:measurereport'...` (SC-002). If `validator_cli.jar`/Java is unavailable, report to the user rather than skipping
- [X] T006 [US1] Confirm `input/` no longer exists and `test/input/` holds all 4 fixtures (SC-001), and that a run with no `--output-dir` still writes to `./output` (SC-006, FR-004)

**Checkpoint**: The relocated regression pipeline passes locally — this is the MVP

---

## Phase 4: User Story 2 - CI validates over the new paths (Priority: P1)

**Goal**: GitHub Actions FHIR-validation job operates entirely over `test/input/` →
`test/output/` and passes.

**Independent Test**: Inspect `.github/workflows/ci.yml`; confirm it loops `test/input/` and
validates `test/output/`, then confirm the job is green on the branch PR.

### Implementation for User Story 2

- [X] T007 [US2] In `.github/workflows/ci.yml` "Run converter against test fixtures" step, change the loop to `for csv in test/input/*.csv` and the converter call to `--output-dir test/output`, and update the explanatory comment that says "in input/" (FR-005, FR-006)
- [X] T008 [US2] In `.github/workflows/ci.yml` "Validate FHIR Bundles" step, change `find output` to `find test/output` and update the surrounding comment referencing `output/{date}/{facility}/*.json` to `test/output/...` (FR-005)
- [ ] T009 [US2] Push the branch / open the PR and confirm the `FHIR Validation` job passes with the new paths (SC-003)

**Checkpoint**: CI mirrors the local pipeline over the new paths and is green

---

## Phase 5: User Story 3 - Documentation reflects the new convention (Priority: P2)

**Goal**: `CLAUDE.md` and `README.md` name `test/input/`/`test/output/` so contributors and LLM
agents run the correct paths; no maintained doc/tooling references the old fixture directory.

**Independent Test**: Follow `CLAUDE.md`'s validation steps verbatim and confirm they operate on
`test/input/`/`test/output/`; grep the repo for stale `input/` fixture references.

### Implementation for User Story 3

- [X] T010 [P] [US3] Update the `## LLM Validation Pipeline` section of `CLAUDE.md`: Step 1 loop to `for csv in test/input/*.csv` with `--output-dir test/output`, Step 3 validator to `$(find test/output -name '*.json')`, and the Step 3 comment referencing `output/{date}/{facility}/*.json` → `test/output/...` (FR-007, SC-004)
- [X] T011 [P] [US3] Update `README.md` only where it names the regression-fixture directory or the test workflow to `test/input/`/`test/output/`; leave generic production examples (placeholder input filename + default `./output`) unchanged. If no such references exist, note that no change was needed (FR-009)
- [X] T012 [US3] Run `grep -rn 'input/' .github/workflows CLAUDE.md README.md` and confirm no result names the old `input/` directory as the fixture source (FR-010, SC-005) — depends on T007, T008, T010, T011

**Checkpoint**: Documentation and tooling are consistent; no stale fixture-path references remain

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final end-to-end confirmation

- [X] T013 Run the full `specs/011-relocate-test-fixtures/quickstart.md` verification sequence end to end and confirm every acceptance check (SC-001 through SC-006) passes
- [X] T014 [P] Sanity-check that unrelated checks still pass: `ruff check convert.py csv_formats.py tests` and `python -m unittest discover -s tests -p "test_*.py"` (no source changed, expect green)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — **BLOCKS all user stories** (the move must happen first)
- **User Stories (Phase 3–5)**: All depend only on Foundational; they touch disjoint files and can proceed in parallel
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Foundational. Independent — verifies the relocated pipeline locally
- **US2 (P1)**: After Foundational. Independent — edits `.github/workflows/ci.yml` only
- **US3 (P2)**: After Foundational. Independent of US1/US2 *except* T012's grep, which should run after the CI (T007–T008) and doc (T010–T011) edits to be meaningful

### Within Each User Story

- US1: T004 → T005 (need output before validating); T006 independent verification
- US2: T007 and T008 edit the same file (`ci.yml`) → sequential; T009 after both
- US3: T010 and T011 edit different files → parallel; T012 grep last

### Parallel Opportunities

- T003 (`.gitignore`) can run alongside T002 conceptually, but keep T002 first since the move is the gate
- After Foundational, US1 / US2 / US3 can be worked in parallel by different people (disjoint files: validation run vs `ci.yml` vs `CLAUDE.md`/`README.md`)
- T010 and T011 are `[P]` (different files); T014 is `[P]` against T013

---

## Parallel Example: After Foundational

```bash
# These touch disjoint files and can run concurrently:
US1: Convert test/input/ fixtures to test/output and validate (T004–T006)
US2: Edit .github/workflows/ci.yml convert + validate steps (T007–T008)
US3: Edit CLAUDE.md (T010) and README.md (T011)
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: Setup (T001)
2. Phase 2: Foundational — the move + `.gitignore` (T002–T003) — **blocks everything**
3. Phase 3: US1 — convert to `test/output/` and validate green (T004–T006)
4. **STOP and VALIDATE**: the relocated regression pipeline passes locally — MVP done

### Incremental Delivery

1. Foundational → fixtures relocated
2. US1 → local pipeline green (MVP)
3. US2 → CI green over new paths
4. US3 → docs consistent, no stale references
5. Polish → full quickstart + lint/unit sanity pass

---

## Notes

- The converter's source (`convert.py`, `csv_formats.py`) is intentionally NOT modified — `test/output/` routing is achieved entirely via `--output-dir`.
- `test/output/` is git-ignored; never commit generated Bundles.
- Re-running the FHIR validation pipeline is mandatory before considering the work complete (constitution: LLM Development Validation). If Java/validator is unavailable locally, report it instead of skipping.
- Commit after the move (T002–T003) and after each user story for clean, reviewable history.
