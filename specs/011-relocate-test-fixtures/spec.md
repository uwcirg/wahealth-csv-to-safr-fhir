# Feature Specification: Relocate test fixtures to test/input and route their output to test/output

**Feature Branch**: `011-relocate-test-fixtures`
**Created**: 2026-06-17
**Status**: Draft
**Input**: User description: "changes to accomodate the constitution edits."

## Context

Constitution v1.8.0 amended the "Validation-Driven Testing" principle: the canonical
regression CSV fixtures now live in `test/input/` (not `input/`), and when the converter
processes fixtures from `test/input/`, the generated FHIR MUST be written to `test/output/`
(mirroring the production `output/` layout) so that test artifacts never mix with production
output. This feature brings the repository's files, tooling, and documentation into
compliance with that amended principle. The constitution change is already merged; this
spec covers the implementation that "accommodates" it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run the regression validation against relocated fixtures (Priority: P1)

A developer, CI, or an LLM agent runs the four-step FHIR validation pipeline. The fixtures
are read from `test/input/`, every generated Bundle and individual resource is written under
`test/output/`, and the HL7 validator runs against everything in `test/output/`. The run
produces zero project-introduced errors, exactly as it did before the relocation.

**Why this priority**: This is the core of the change. The whole point of the constitution
amendment is that the regression pipeline operates over `test/input/` → `test/output/`. If
this works end to end with green validation, the feature delivers its value.

**Independent Test**: Run the converter against each fixture in `test/input/`
(excluding `*column-labels-only*` files) with output directed to `test/output`, then run the
HL7 validator over `test/output`. Confirm zero errors not attributable to the documented known
upstream issues.

**Acceptance Scenarios**:

1. **Given** the fixtures have been relocated to `test/input/`, **When** the converter is run
   against each data fixture with output directed to `test/output`, **Then** the same set of
   Bundle and per-facility resource files is produced as before, now rooted at `test/output/`.
2. **Given** generated output exists under `test/output/`, **When** the HL7 FHIR validator is
   run against all JSON files found under `test/output`, **Then** validation reports zero
   errors other than the documented known upstream issues.
3. **Given** the relocation is complete, **When** a developer lists `input/`, **Then** the old
   fixture files are no longer present there (they live in `test/input/`).

---

### User Story 2 - CI validates over the new paths (Priority: P1)

A pull request triggers the GitHub Actions CI pipeline. The FHIR-validation job iterates the
fixtures in `test/input/`, converts them to `test/output/`, and validates `test/output/`,
passing as it did under the old paths.

**Why this priority**: CI is the project's safety net and is itself governed by the
constitution. If CI still pointed at `input/`/`output/` it would either fail (no fixtures
found) or validate stale output, defeating the relocation. CI must move in lockstep with the
fixtures.

**Independent Test**: Open a PR on the feature branch and confirm the CI FHIR-validation job
references `test/input/` and `test/output/` and completes green.

**Acceptance Scenarios**:

1. **Given** the CI workflow has been updated, **When** the FHIR-validation job runs, **Then**
   it loops over the fixtures in `test/input/` (excluding `*column-labels-only*` files) and
   writes generated output to `test/output`.
2. **Given** output was generated to `test/output/` in CI, **When** the validator step runs,
   **Then** it discovers the JSON files under `test/output` and the job passes with zero
   project-introduced errors.

---

### User Story 3 - Documentation reflects the new convention (Priority: P2)

A contributor or LLM agent reading `CLAUDE.md` (and the README where relevant) finds the
validation pipeline instructions pointing at `test/input/` and `test/output/`, matching the
constitution and the actual repository layout.

**Why this priority**: Per the "README as Living Documentation" and LLM-validation principles,
stale instructions cause agents and contributors to run the wrong paths. Documentation must
not contradict the code, but it does not block the pipeline from functioning, so it is P2.

**Independent Test**: Read `CLAUDE.md`'s LLM Validation Pipeline section and confirm every
command references `test/input/`/`test/output/`; copy-paste and run them to confirm they work.

**Acceptance Scenarios**:

1. **Given** the relocation is done, **When** a reader follows `CLAUDE.md`'s validation steps
   verbatim, **Then** the commands operate on `test/input/` and `test/output/` and succeed.
2. **Given** the README documents how output is organized or how to run the regression
   fixtures, **When** a reader follows it, **Then** any references to the fixture/test paths
   are consistent with `test/input/` and `test/output/`.

---

### Edge Cases

- **Generated test output committed by accident**: `test/output/` holds generated artifacts
  and MUST be ignored by version control just as `output/` is, so a contributor running the
  pipeline locally does not accidentally commit generated Bundles.
- **The `*column-labels-only*` reference file**: this header-only file moves with the other
  fixtures into `test/input/` but continues to be excluded from conversion, exactly as today.
- **Production runs are unaffected**: a user converting a real CSV without specifying an output
  directory still gets output under the default `./output`; the relocation changes only the
  test/regression convention, not the converter's production default.
- **Git history preservation**: relocating fixtures should preserve their version history
  (a move/rename, not a delete-and-recreate).
- **Stale references remain somewhere**: any lingering reference to the old `input/` fixture
  directory in tooling or docs would silently break the pipeline; the change must leave no
  tooling pointing at the old fixture path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The canonical regression CSV fixtures currently in `input/` MUST be relocated to
  `test/input/`, preserving their filenames and their version-control history.
- **FR-002**: After relocation, the old fixtures MUST NOT remain in `input/` (no duplicate
  copies in two locations).
- **FR-003**: When the converter processes fixtures from `test/input/`, the generated FHIR
  output MUST be written under `test/output/`, mirroring the production output layout
  (`{root}/{date}/...` with per-facility subdirectories).
- **FR-004**: The converter's default production output location MUST remain unchanged
  (`./output`); the `test/output/` routing applies to fixture/regression processing and is
  achieved by directing output to `test/output` when running the fixtures.
- **FR-005**: The CI FHIR-validation pipeline MUST read fixtures from `test/input/`, write
  generated output to `test/output/`, and run the validator against files discovered under
  `test/output/`.
- **FR-006**: The CI pipeline MUST continue to exclude `*column-labels-only*` files from
  conversion and MUST continue to pass with zero project-introduced errors (known upstream
  issues filtered as before).
- **FR-007**: `CLAUDE.md`'s LLM Validation Pipeline instructions MUST be updated so every step
  references `test/input/` and `test/output/` and remains runnable verbatim.
- **FR-008**: Version control MUST ignore the generated `test/output/` directory, consistent
  with how `output/` is ignored today.
- **FR-009**: `README.md` MUST be updated wherever it references the fixture directory or the
  regression/test workflow so it is consistent with `test/input/`/`test/output/`; generic
  illustrative examples that use a placeholder input filename and the production `./output`
  default need not change.
- **FR-010**: After the change, no project tooling or maintained documentation may reference
  the old `input/` fixture directory as the source of regression fixtures.

### Key Entities

- **Regression fixtures**: the canonical CSV files (one per supported input format, plus the
  header-only `*column-labels-only*` reference) that exercise the converter. Relocating from
  `input/` to `test/input/`.
- **Test output tree**: generated FHIR artifacts produced from the regression fixtures,
  rooted at `test/output/`, structurally identical to the production `output/` tree, and
  excluded from version control.
- **Validation pipeline**: the four-step convert-then-validate procedure run by CI, developers,
  and LLM agents, defined in `CLAUDE.md` and `.github/workflows/ci.yml`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All regression fixtures (3 data files plus the header-only reference) are present
  in `test/input/` and absent from `input/`.
- **SC-002**: Running the validation pipeline over `test/input/` produces output exclusively
  under `test/output/`, and the HL7 validator reports zero errors other than the documented
  known upstream issues.
- **SC-003**: CI passes on the feature branch with the FHIR-validation job operating entirely
  over `test/input/` and `test/output/`.
- **SC-004**: A reader can follow `CLAUDE.md`'s validation steps verbatim with no path
  corrections needed and reach a green validation result.
- **SC-005**: A repository-wide search for the old fixture directory path turns up no
  references in active tooling or maintained documentation as the fixture source.
- **SC-006**: A production conversion run with no output-directory override still writes to
  `./output`, confirming non-test behavior is unchanged.

## Assumptions

- The constitution amendment (v1.8.0) establishing the `test/input/` → `test/output/`
  convention is already merged; this feature implements the file/tooling/doc changes that
  conform to it.
- The three current data fixtures
  (`2025.10.21.Test.Facility.BedCapacity.csv`, `2026.04.30.Test.Facility.WAHealthDict.csv`,
  `census_20260511.FromKC.SubsetObfsctd.csv`) and the
  `2025.10.21.Test.Facility.BedCapacity.column-labels-only.csv` reference file are the complete
  set to relocate.
- `test/output/` routing is accomplished by passing the output directory to the converter when
  running fixtures (the converter already accepts an output-directory argument); no new
  auto-detection of `test/input/` is required, and the converter's default output location is
  not changed.
- The README's generic usage examples that use a placeholder input filename and the default
  `./output` are illustrative of production usage and are out of scope unless they specifically
  reference the regression-fixture directory or test workflow.
- The production `output/` directory and its version-control ignore entry remain in place for
  production runs.
