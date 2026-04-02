# Tasks: Constitution v1.2.0 Repo Alignment

**Input**: Design documents from `/specs/003-constitution-repo-update/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Not requested in the feature specification. No test tasks generated.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- This is a documentation-only feature. All changes target `CLAUDE.md` at the repository root.
- Reference files: `.github/workflows/ci.yml`, `convert.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify the current state of CLAUDE.md and CI workflow before making changes

- [X] T001 Confirm `CLAUDE.md` contains `<!-- MANUAL ADDITIONS START -->` and `<!-- MANUAL ADDITIONS END -->` markers at CLAUDE.md
- [X] T002 [P] Confirm `.github/workflows/ci.yml` contains the four validation steps (convert, extract IG version, validate, zero-errors) at .github/workflows/ci.yml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational tasks needed — this is a documentation-only feature. The manual additions markers already exist in CLAUDE.md.

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - LLM Agent Runs Validation Before Completing Work (Priority: P1) MVP

**Goal**: Add the four-step LLM validation pipeline to CLAUDE.md so LLM agents know to run FHIR validation before completing development work.

**Independent Test**: Have an LLM agent make a trivial change to `convert.py` and observe that it runs the full validation pipeline before reporting done.

### Implementation for User Story 1

- [X] T003 [US1] Add "LLM Validation Pipeline" section header between manual additions markers in CLAUDE.md
- [X] T004 [US1] Add Step 1 — convert test fixtures command (with `*column-labels-only*` exclusion pattern) matching CI workflow lines 47–53 in CLAUDE.md
- [X] T005 [US1] Add Step 2 — extract `SAFR_IG_VERSION` command matching CI workflow line 57 in CLAUDE.md
- [X] T006 [US1] Add Step 3 — `validator_cli.jar` invocation command matching CI workflow lines 63–65 in CLAUDE.md
- [X] T007 [US1] Add Step 4 — zero-errors requirement with instruction to fix and re-validate if errors occur in CLAUDE.md
- [X] T008 [US1] Add instruction that LLM agents MUST NOT skip validation to save time or defer to CI in CLAUDE.md
- [X] T009 [US1] Add instruction that LLM agents must inform the user if `validator_cli.jar` or Java is unavailable in CLAUDE.md

**Checkpoint**: CLAUDE.md now contains the complete LLM validation pipeline. An LLM agent reading CLAUDE.md can follow the steps end-to-end.

---

## Phase 4: User Story 2 - Developer Instructions Reflect Constitution Requirements (Priority: P2)

**Goal**: Ensure the documented instructions are clear, actionable, and self-contained so any LLM agent given only CLAUDE.md can execute the validation pipeline.

**Independent Test**: Read CLAUDE.md and confirm it contains all four validation pipeline steps with executable commands and no ambiguity.

### Implementation for User Story 2

- [X] T010 [US2] Review the validation pipeline section in CLAUDE.md for clarity and completeness — ensure commands are copy-pasteable and self-contained
- [X] T011 [US2] Verify all commands in CLAUDE.md are executable shell commands (not pseudocode) by dry-running each step mentally against the repo structure in CLAUDE.md

**Checkpoint**: A developer or LLM agent reading only CLAUDE.md can execute the full validation pipeline without additional context.

---

## Phase 5: User Story 3 - CI and LLM Validation Use Identical Pipeline Steps (Priority: P3)

**Goal**: Verify parity between the CI workflow and the LLM validation instructions in CLAUDE.md.

**Independent Test**: Diff the commands in CLAUDE.md against `.github/workflows/ci.yml` and confirm functional equivalence.

### Implementation for User Story 3

- [X] T012 [US3] Compare each command in the CLAUDE.md validation pipeline against .github/workflows/ci.yml and fix any discrepancies in CLAUDE.md
- [X] T013 [US3] Verify the exclusion pattern `*column-labels-only*` in CLAUDE.md matches the CI pattern in .github/workflows/ci.yml line 49
- [X] T014 [US3] Verify the IG version extraction method in CLAUDE.md matches CI workflow .github/workflows/ci.yml line 57

**Checkpoint**: All LLM validation pipeline steps in CLAUDE.md are functionally identical to CI.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all stories

- [X] T015 Run quickstart.md verification commands (`grep` checks) to confirm CLAUDE.md contains all required content
- [X] T016 Run `ruff check convert.py` to confirm no linting regressions (no code changes expected, but validates clean state)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: No tasks — skip
- **User Story 1 (Phase 3)**: Depends on Setup (Phase 1) — T003 through T009 are sequential (all edit the same file section)
- **User Story 2 (Phase 4)**: Depends on User Story 1 (Phase 3) — reviews content written in US1
- **User Story 3 (Phase 5)**: Depends on User Story 1 (Phase 3) — verifies parity of content written in US1
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Setup — writes the validation pipeline content
- **User Story 2 (P2)**: Depends on US1 — reviews and refines the content US1 created
- **User Story 3 (P3)**: Depends on US1 — verifies CI parity of the content US1 created
- **US2 and US3**: Can run in parallel after US1 is complete

### Within Each User Story

- Tasks within US1 (T003–T009) are sequential since they all modify the same section of CLAUDE.md
- Tasks within US2 (T010–T011) are sequential (review then verify)
- Tasks within US3 (T012–T014) are sequential (compare then verify specifics)

### Parallel Opportunities

- T001 and T002 can run in parallel (different files)
- US2 (Phase 4) and US3 (Phase 5) can run in parallel after US1 completes
- T015 and T016 can run in parallel (different tools)

---

## Parallel Example: Setup Phase

```bash
# Launch both setup verification tasks together:
Task: "Confirm CLAUDE.md contains manual additions markers at CLAUDE.md"
Task: "Confirm .github/workflows/ci.yml contains the four validation steps at .github/workflows/ci.yml"
```

## Parallel Example: After User Story 1

```bash
# Launch US2 and US3 review phases together:
Task: "Review the validation pipeline section in CLAUDE.md for clarity"
Task: "Compare each command in CLAUDE.md against .github/workflows/ci.yml"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify markers and CI commands)
2. Phase 2: Foundational — no tasks needed
3. Complete Phase 3: User Story 1 (write the validation pipeline into CLAUDE.md)
4. **STOP and VALIDATE**: Run quickstart.md grep checks to confirm content exists
5. MVP is complete — LLM agents can now follow the validation pipeline

### Incremental Delivery

1. Complete Setup → Verify repo state
2. Add User Story 1 → Validation pipeline in CLAUDE.md → MVP!
3. Add User Story 2 → Review clarity and completeness
4. Add User Story 3 → Verify CI parity
5. Polish → Final verification

---

## Notes

- This is a documentation-only feature — all tasks modify or verify `CLAUDE.md`
- No new code, tests, models, or services are created
- The primary risk is command discrepancy between CLAUDE.md and CI — US3 mitigates this
- Commit after each user story phase is complete
- The manual additions section of CLAUDE.md survives auto-generation runs
