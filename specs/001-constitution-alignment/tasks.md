# Tasks: Constitution Alignment

**Input**: Design documents from `/specs/001-constitution-alignment/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Not explicitly requested. Test tasks omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: No new project structure needed — this feature adds configuration files to an existing repo.

- [ ] T001 Verify current branch is `001-constitution-alignment` and working tree is clean

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No foundational blockers — all user stories operate on independent files.

**Checkpoint**: No blocking prerequisites. User story implementation can begin immediately after T001.

---

## Phase 3: User Story 1 — Secrets Are Protected from Accidental Commit (Priority: P1) MVP

**Goal**: Create `.gitignore` that prevents `config.json`, `*.secret*`, `.env`, and generated files from being committed.

**Independent Test**: Create a `config.json` and `.env` file, run `git status`, confirm neither appears as untracked.

### Implementation for User Story 1

- [ ] T002 [US1] Create `.gitignore` at repository root with entries: `config.json`, `*.secret*`, `.env`, `__pycache__/`, `*.pyc`, `output/`, `log/`
- [ ] T003 [US1] Verify that existing untracked `__pycache__/` directory is now ignored by running `git status`
- [ ] T004 [US1] Test secret protection by creating a temporary `config.json` and `.env`, confirming `git status` does not show them, then removing the test files

**Checkpoint**: `.gitignore` is in place. Secrets cannot be accidentally staged.

---

## Phase 4: User Story 2 — CI Pipeline Catches Regressions Before Merge (Priority: P1)

**Goal**: Create a GitHub Actions workflow with lint, FHIR validation, and secret scanning jobs that run on all PRs to `main`.

**Independent Test**: Push the branch and open a PR — CI should trigger and all three jobs should run.

### Implementation for User Story 2

- [ ] T005 [US2] Create directory `.github/workflows/` at repository root
- [ ] T006 [US2] Create `.github/workflows/ci.yml` with workflow trigger on `pull_request` to `main` and `push` to `main`
- [ ] T007 [US2] Add lint job to `.github/workflows/ci.yml`: checkout repo, install `ruff` via pip, run `ruff check convert.py`
- [ ] T008 [US2] Add FHIR validation job to `.github/workflows/ci.yml`: checkout repo, setup Java 17, download/cache `validator_cli.jar` from `https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar`, run `python3 convert.py` against each CSV in `input/` matching `*.BedCapacity.csv` (excluding `*column-labels-only*`), then validate all output JSON Bundles with `java -jar validator_cli.jar output/**/*.json -version 4.0.1 -ig hl7.fhir.us.safr`
- [ ] T009 [US2] Add secret scanning job to `.github/workflows/ci.yml`: use `gitleaks/gitleaks-action@v2` to scan for committed credentials
- [ ] T010 [P] [US2] Create `ruff.toml` at repository root with minimal configuration (line-length = 120 or match existing convert.py style)
- [ ] T011 [US2] Run `ruff check convert.py` locally and fix any lint violations in `convert.py` (minor style fixes only — no functional changes)

**Checkpoint**: CI workflow is defined. Lint, FHIR validation, and secret scanning will run on the next PR.

---

## Phase 5: User Story 3 — Config Example Uses Obvious Placeholders (Priority: P2)

**Goal**: Update `config.example.json` so server credential fields use `YOUR_*` placeholder values instead of empty strings.

**Independent Test**: Read `config.example.json` and verify `client_id`, `client_secret`, `token_endpoint`, and `base_url` all contain `YOUR_*` placeholder strings.

### Implementation for User Story 3

- [ ] T012 [US3] Update `config.example.json` server section: replace `"base_url": ""` with `"base_url": "YOUR_FHIR_SERVER_URL"`, `"token_endpoint": ""` with `"token_endpoint": "YOUR_TOKEN_ENDPOINT"`, `"client_id": ""` with `"client_id": "YOUR_CLIENT_ID"`, `"client_secret": ""` with `"client_secret": "YOUR_CLIENT_SECRET"`

**Checkpoint**: `config.example.json` has obvious non-functional placeholders. Accidental use will fail clearly.

---

## Phase 6: User Story 4 — Test Fixtures Are Organized for CI (Priority: P2)

**Goal**: Ensure test CSV fixtures in `input/` are discoverable by CI and documented.

**Independent Test**: Confirm CI workflow globs `input/*.BedCapacity.csv` and the canonical test file is picked up.

### Implementation for User Story 4

- [ ] T013 [US4] Verify that the CI workflow in `.github/workflows/ci.yml` (from T008) correctly globs `input/*.BedCapacity.csv` and excludes `*column-labels-only*` files
- [ ] T014 [US4] Add a comment in `.github/workflows/ci.yml` documenting how to add new test fixtures (place CSV in `input/` with `*.BedCapacity.csv` naming convention)

**Checkpoint**: Test fixtures are organized and CI-discoverable. Adding a new CSV to `input/` will automatically be picked up.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all user stories.

- [ ] T015 Run `ruff check convert.py` to confirm lint passes
- [ ] T016 Run `python3 convert.py input/2025.10.21.Test.Facility.BedCapacity.csv --config config.example.json` to confirm converter still works with updated config placeholders (expect graceful handling of placeholder values when no `--fhir-server` is used)
- [ ] T017 Review all new/modified files for consistency with constitution principles
- [ ] T018 Run quickstart.md validation steps locally

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: No blocking tasks
- **User Story 1 (Phase 3)**: No dependencies — can start immediately
- **User Story 2 (Phase 4)**: No dependencies on other stories — can start immediately or in parallel with US1
- **User Story 3 (Phase 5)**: No dependencies on other stories — can start immediately or in parallel
- **User Story 4 (Phase 6)**: Depends on US2 (T008) since it validates the CI workflow's fixture discovery
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Independent — no dependencies on other stories
- **User Story 2 (P1)**: Independent — no dependencies on other stories (T010/T011 can run in parallel with T005-T009)
- **User Story 3 (P2)**: Independent — no dependencies on other stories
- **User Story 4 (P2)**: Depends on User Story 2 (validates CI workflow)

### Within Each User Story

- Tasks are sequential unless marked [P]
- T010 is marked [P] because `ruff.toml` is a different file from `ci.yml`

### Parallel Opportunities

- US1 (`.gitignore`) and US2 (CI pipeline) can be implemented in parallel — different files entirely
- US3 (`config.example.json`) can be implemented in parallel with US1 and US2
- T010 (`ruff.toml`) can be created in parallel with the CI workflow tasks (T006-T009)

---

## Parallel Example: User Stories 1, 2, 3

```text
# These three stories touch entirely different files and can run in parallel:
Stream A: T002 → T003 → T004          (US1: .gitignore)
Stream B: T005 → T006 → T007-T009 → T011  (US2: CI pipeline + lint fixes)
          T010 in parallel with T007-T009  (US2: ruff.toml)
Stream C: T012                         (US3: config.example.json)

# Then sequential:
T013-T014 (US4: depends on T008)
T015-T018 (Polish: depends on all)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001: Verify branch
2. T002-T004: Create `.gitignore` and verify secret protection
3. **STOP and VALIDATE**: Secrets are protected immediately

### Incremental Delivery

1. Add `.gitignore` (US1) → Secrets protected (immediate value)
2. Add CI pipeline (US2) → PRs are automatically checked
3. Update config placeholders (US3) → Better developer experience
4. Verify fixture discovery (US4) → CI completeness

### Single Developer Strategy

Recommended execution order: T001 → T002-T004 → T005-T011 → T012 → T013-T014 → T015-T018

---

## Notes

- No runtime code changes to `convert.py` except potential minor lint fixes (T011)
- All new files are repo infrastructure — no impact on the converter's behavior
- The FHIR validation CI job depends on `config.example.json` being usable as a config file for local file output (no server interaction)
- Commit after each user story checkpoint for clean git history
