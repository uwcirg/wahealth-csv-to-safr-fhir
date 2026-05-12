---

description: "Task list for feature 009-per-facility-output-layout"
---

# Tasks: Per-Facility Output Layout and Bundles-MRs-Only Mode

**Input**: Design documents from `/specs/009-per-facility-output-layout/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: Test tasks ARE included — FR-010 requires the test suite to cover the new layout and both
modes of the `--bundles-mrs-only` flag.

**Organization**: Tasks are grouped by user story (US1 = per-facility layout, US2 =
`--bundles-mrs-only`) so each can be implemented and verified independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 or US2 (Setup / Foundational / Polish tasks have no story label)
- Exact file paths are included in each task

## Path Conventions

Single-file CLI tool at repo root: `convert.py`, `README.md`, tests in `tests/`. Existing canonical
CSV fixtures live in `input/` (including a multi-facility fixture). Generated output goes to
`output/` (not committed).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the working baseline before changing output behavior.

- [ ] T001 Confirm baseline: from repo root run `pytest` and `ruff check .`; run `python3 convert.py input/<a-fixture>.csv --config config.example.json --output-dir /tmp/out-baseline` and note the current output layout (individual resources directly in `output/{date}/`). Identify the multi-facility fixture filename under `input/` for use in later tasks.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: None required — `sanitize_filename`, the `argparse` parser, and the row write loop in `convert.py` `main()` already exist. No foundational refactor is needed before the user stories.

**Checkpoint**: Proceed directly to User Story 1.

---

## Phase 3: User Story 1 - Isolated individual resources per facility (Priority: P1) 🎯 MVP

**Goal**: Each `(facility, reporting date)` row writes its standalone `Organization.json`, `Device.json`, `MeasureReport.json`, `Location.json` into `output/{YYYY-MM-DD}/{facility_name}/`; the Bundle file stays in `output/{YYYY-MM-DD}/`; multi-facility input no longer overwrites one facility's individual resources with another's.

**Independent Test**: Convert the multi-facility fixture; assert each facility has its own `output/{date}/{facility}/` directory with that facility's four resources, and `output/{date}/` itself contains only `*.BedCapacity.json` Bundle files.

### Tests for User Story 1 ⚠️ (write first, ensure they FAIL before implementation)

- [ ] T002 [P] [US1] In `tests/test_output_layout.py` (new file): add a test that runs the converter (invoke `convert.main()` with patched `sys.argv`, or run `convert.py` as a subprocess) against a single-facility fixture in `input/` with `--output-dir` pointed at a tmp dir, then asserts (a) the Bundle file exists at `{tmp}/{date}/{facility}.{date}.BedCapacity.json`, (b) `{tmp}/{date}/{facility}/` exists and contains `Organization.json`, `Device.json`, `Location.json`, `MeasureReport.json`, (c) no `*.json` resource files (other than the `*.BedCapacity.json` Bundle) sit directly in `{tmp}/{date}/`.
- [ ] T003 [P] [US1] In `tests/test_output_layout.py`: add a test that runs the converter against the multi-facility fixture identified in T001, then asserts that for each distinct facility a subdirectory `{tmp}/{date}/{sanitized_facility}/` exists, each containing that facility's own `Organization.json` (verify the `id`/identifier differs between two facilities so we know files were not overwritten), and that the count of facility subdirectories equals the number of distinct `(facility, date)` rows.

### Implementation for User Story 1

- [ ] T004 [US1] In `convert.py` `main()` row loop (around lines 876–898): after computing `date_dir` and `facility_name`, add `facility_dir = os.path.join(date_dir, facility_name)` and `os.makedirs(facility_dir, exist_ok=True)`; keep the Bundle write targeting `date_dir`; change the individual-resource write so `res_filepath = os.path.join(facility_dir, f"{res_type}.json")`. Keep the existing `logger.info("Generated %s", ...)` lines (now logging the per-facility paths).
- [ ] T005 [US1] Run `tests/test_output_layout.py` (T002, T003) and `ruff check .`; confirm pass.

**Checkpoint**: User Story 1 is functional — per-facility layout works for single- and multi-facility input.

---

## Phase 4: User Story 2 - Bundles-and-MeasureReports-only output mode (Priority: P2)

**Goal**: An opt-in `--bundles-mrs-only` flag restricts **local** output to the Bundle file(s) and each facility's `MeasureReport.json`, skipping the local `Organization.json`, `Device.json`, `Location.json`. Default (flag absent) writes the full local set. FHIR-server persistence is unchanged in either mode (Bundle + standalone MeasureReport are the primary persisted artifacts; Organization/Device/Location are still upserted as supporting resources the MeasureReport's references require). Flag appears in `--help`.

**Independent Test**: Run the converter on any fixture with `--bundles-mrs-only`; assert the Bundle file(s) exist, each facility subdirectory contains only `MeasureReport.json`, and no `Organization.json`/`Device.json`/`Location.json` exists anywhere under the output dir; `python3 convert.py --help` lists `--bundles-mrs-only`.

### Tests for User Story 2 ⚠️ (write first, ensure they FAIL before implementation)

- [ ] T006 [P] [US2] In `tests/test_output_layout.py`: add a test that runs the converter with `--bundles-mrs-only` against a fixture in `input/`, then asserts (a) the Bundle file(s) exist in `{tmp}/{date}/`, (b) each `{tmp}/{date}/{facility}/` contains `MeasureReport.json`, (c) `find` over `{tmp}` yields zero `Organization.json`, `Device.json`, and `Location.json` files.
- [ ] T007 [P] [US2] In `tests/test_output_layout.py`: add a test asserting that without `--bundles-mrs-only` the full set of four individual resources is still written (regression guard for the default), and a test asserting `convert.py --help` output (capture via subprocess) contains the string `--bundles-mrs-only`.
- [ ] T007a [P] [US2] In `tests/test_output_layout.py`: add a regression test that runs the converter on a fixture **with** and **without** `--bundles-mrs-only` (no `--fhir-server`) and asserts the process exits 0 in both cases and the generated **Bundle file bytes are identical** between the two runs (FR-008a — the flag must not alter Bundle/MeasureReport contents). FR-008b (server persistence unchanged) is covered by code review of T009 — the FHIR-server block is untouched — not by a live-server test.

### Implementation for User Story 2

- [ ] T008 [US2] In `convert.py` `main()` `argparse` setup (around lines 823–831): add `parser.add_argument("--bundles-mrs-only", action="store_true", help="Write only the Bundle and MeasureReport.json for each facility locally; skip the rarely-changing Organization.json, Device.json, and Location.json files. Does not change what is persisted to a --fhir-server.")`.
- [ ] T009 [US2] In `convert.py` `main()` row loop, in the `for entry in bundle["entry"]` block: when `args.bundles_mrs_only` is true, skip writing any **local** resource file whose `resourceType` is not `MeasureReport` (always write the Bundle and `MeasureReport.json`). Leave the FHIR-server persistence block (around lines 900–921) **entirely untouched** — Organization/Device/Location must still be upserted there because `upsert_measure_report` needs their server references.
- [ ] T010 [US2] Run `tests/test_output_layout.py` (T006, T007, T007a) plus the full `pytest` suite and `ruff check .`; confirm pass.

**Checkpoint**: Both user stories work independently; default behavior unchanged except for the new subdirectory location.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T011 [P] Update `README.md` "Output" section (around lines 34–42): describe `output/{date}/{facility_name}/` for individual resources, the Bundle staying in `output/{date}/`, and that multi-facility input no longer overwrites individual resources. Add a `--bundles-mrs-only` row to the options table (around lines 27–30) and mention it in the Output section. Ensure wording matches `contracts/cli.md`.
- [ ] T012 Remove the README "Follow-up TODOs" item in `.specify/memory/constitution.md`'s Sync Impact Report block that says the README update is pending (it is now done), or note that it is resolved — coordinate with the user before editing the constitution file.
- [ ] T013 Run the mandatory FHIR validation pipeline from `CLAUDE.md`: convert every non-`*column-labels-only*` fixture in `input/` to `output/`, extract `SAFR_IG_VERSION` and `NHSN_SAFR_IG_VERSION`, then validate **all** generated JSON regardless of nesting depth — `java -jar validator_cli.jar $(find output -name '*.json') -version 4.0.1 -ig hl7.fhir.us.safr#$SAFR_IG_VERSION -ig https://safr-ci.nhsnlink.org/package.tgz` (the new per-facility subdirectories add a third path level that the `output/**/*.json` glob does not match without `shopt -s globstar`). Confirm zero errors other than the two known upstream patterns. If `validator_cli.jar`/Java is unavailable, inform the user immediately rather than skipping.
- [ ] T014 Run `quickstart.md` verification steps end-to-end (layout, isolation, flag, tests, validation, docs) and confirm all pass.
- [ ] T015 Propose to the user an update to the manual "LLM Validation Pipeline" section of `CLAUDE.md` (and the matching `java`/`grep` lines in `.github/workflows/ci.yml` if present): replace `output/**/*.json` with `$(find output -name '*.json')` (or add `shopt -s globstar`) so Step 3 reaches the per-facility-subdirectory resource files. Do not edit `CLAUDE.md` or CI without user confirmation.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies — start immediately.
- **Foundational (Phase 2)**: empty — nothing to do.
- **User Story 1 (Phase 3)**: depends on Setup.
- **User Story 2 (Phase 4)**: depends on Setup; T009 edits the same `for entry in bundle["entry"]` block changed by US1's T004, so US2 implementation should follow US1 implementation (or be merged carefully). US2's tests/help (T006, T007, T007a) are independent of US1.
- **Polish (Phase 5)**: depends on US1 and US2 implementation being complete (T013/T014 validate the combined result).

### Within Each User Story

- Write the story's tests first (they should FAIL), then implement, then re-run tests + `ruff`.

### Parallel Opportunities

- T002 and T003 ([P] [US1]) can be written in parallel.
- T006, T007, and T007a ([P] [US2]) can be written in parallel.
- T011 ([P], README) can proceed in parallel with T013 once code is done.
- US1 and US2 *test-writing* can overlap; their *implementation* edits to `convert.py` `main()` should be sequenced to avoid merge conflicts in the row loop.

---

## Parallel Example: User Story 1

```bash
# Write both US1 tests together (same new file — coordinate, or split into two test functions):
Task: "test_output_layout.py — single-facility per-facility-subdir layout assertions (T002)"
Task: "test_output_layout.py — multi-facility no-overwrite assertions (T003)"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup → 2. (Phase 2 empty) → 3. Phase 3: write T002/T003 (fail), implement T004, pass T005.
4. STOP and validate: multi-facility conversion isolates individual resources. This alone delivers the constitution's correctness fix.

### Incremental Delivery

1. US1 (per-facility layout) → test → done.
2. US2 (`--bundles-mrs-only`) → test → done.
3. Polish: README, constitution TODO note, FHIR validation, quickstart check.

---

## Notes

- [P] = different files / independent; the two `convert.py` `main()` edits (T004, T009) are in the same function and are NOT [P] relative to each other.
- Reuse `sanitize_filename` unchanged so the facility subdirectory name equals the `{facility_name}` segment of the Bundle filename (FR-003).
- Do not alter FHIR-server persistence, Bundle/MeasureReport contents, logging format, or exit codes (FR-008a/FR-008b). `--bundles-mrs-only` only suppresses *local* individual-resource file writes; the persistence block keeps upserting Organization/Device/Location because `upsert_measure_report` needs their server references.
- Commit after each task or logical group; re-run `ruff check .` before committing.
