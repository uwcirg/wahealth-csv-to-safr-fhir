# Tasks: Support multiple hospital CSV input formats

**Input**: Design documents from `/specs/008-multi-format-csv-input/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test tasks ARE included — FR-011 and the constitution's Validation-Driven
Testing principle require per-format fixtures, unit tests for detection/parsing, a
no-regression check on the original format, and an end-to-end FHIR-validator pass.
This is a refactor of existing single-file code, so the existing `tests/test_compute.py`
acts as the regression safety net rather than a strict red-green-refactor cycle.

**Organization**: Tasks grouped by user story. Note: this feature is almost entirely
edits to one file (`convert.py`), so `[P]` markers are sparse — most code tasks
serialize on `convert.py`. Separate-file work (fixtures, `tests/test_formats.py`,
`README.md`, `ci.yml`, `CLAUDE.md`, `config.example.json`) can overlap with `convert.py`
work but not with each other when they touch the same file.

## Path Conventions

Single-file CLI tool at repo root: `convert.py`, tests in `tests/`, fixtures in
`input/`, config `config.example.json`, CI `.github/workflows/ci.yml`. No `src/`.

---

## Phase 1: Setup

**Purpose**: Capture the pre-change baseline needed by the regression test.

- [x] T001 On the current `main` (pre-change) tree, run `python3 convert.py input/2025.10.21.Test.Facility.BedCapacity.csv --config config.example.json --output-dir /tmp/baseline-008`, then save the generated Bundle(s) — minus the volatile fields (`Bundle.id`, `Bundle.timestamp`, all `fullUrl`/`resource.id` UUIDs, `MeasureReport.date`) — as `specs/008-multi-format-csv-input/regression-baseline.json` (a JSON array of normalized Bundles). This is the fixture the US3/foundational regression test diffs against.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The format-detection + normalized-row machinery and the `compute_groups`
refactor. After this phase the **original WA Health format** runs end-to-end through
the new pipeline with byte-equivalent output, and adding a new format is a data-only
descriptor change.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 In `convert.py`, add `slugify(name)` (lowercase; collapse runs of non-`[a-z0-9]` to a single `-`; strip leading/trailing `-`) and the constant `UNREGISTERED_FACILITY_SYSTEM = "urn:wahealth:csv-to-safr:unregistered-facility"`. Keep `sanitize_filename` unchanged.
- [x] T003 In `convert.py`, add the `SUPPORTED_FORMATS` table (list of descriptor dicts with keys `id`, `display_name`, `detect_columns`, `multi_facility`, `has_guid`, `date_formats`, `column_map`) and populate **only** the `original` descriptor exactly per `contracts/input-formats.md` §1 (`detect_columns=("facility_guid","reporting_date")`, `multi_facility=False`, `has_guid=True`, `date_formats=("%m/%d/%Y",)`, full `column_map` for the 8 canonical bed areas + `adult_ed`/`peds_ed` + `facility_name`/`facility_guid`/`reporting_date`).
- [x] T004 In `convert.py`, add `class UnrecognizedFormatError(Exception)` and `detect_format(header)` → returns the first `SUPPORTED_FORMATS` descriptor whose `detect_columns` are all present in `header`, else raises `UnrecognizedFormatError` (the exception message need not list formats — the `main()` handler does that, T007).
- [x] T005 In `convert.py`, add `parse_date_flexible(value, formats)` (tries each `strptime` pattern in order, returns a `datetime.date`, raises `ValueError` naming the patterns on total failure) and rewrite `parse_reporting_date` as a thin wrapper `parse_date_flexible(date_str, ("%m/%d/%Y",))` so its existing unit tests still pass.
- [x] T006 In `convert.py`, add the generic `parse_rows(reader, descriptor)`: first verify every source column named in `descriptor["column_map"]` exists in `reader.fieldnames` — if not, raise a clear `ValueError` ("format '<display_name>' expects column '<col>' which is missing"); then for each row produce a NormalizedRow dict per `data-model.md` (`safe_int` for the count columns with the existing empty→0 logging; `parse_date_flexible(..., descriptor["date_formats"])` for the reporting date; `facility_guid = row[...] if descriptor["has_guid"] else None`). Return the list; if there are no data rows, log "CSV file contains no data rows" and exit non-zero, as today.
- [x] T007 In `convert.py`, rewire `parse_csv`/`main()`: open the CSV, read the header via `csv.DictReader`, call `detect_format(reader.fieldnames)` and then `parse_rows(reader, descriptor)` — **before** `os.makedirs(args.output_dir, ...)` or any file write. Catch `UnrecognizedFormatError` and the `ValueError` from missing columns: log an error that names every `display_name` in `SUPPORTED_FORMATS`, and `sys.exit(1)` without creating the output directory or any files. Thread the chosen `descriptor` through to where it's needed (date already normalized in the record).
- [x] T008 In `convert.py`, refactor the group computation to the canonical model: `ALL_BED_PREFIXES` → `ALL_BED_AREAS = ["adult_icu","peds_icu","adult_acute","peds_acute","neonatal_icu","nursery","surge","other"]`; re-key `BED_MAPPINGS` by canonical area; `get_occupied_and_unoccupied(record, area)` reads `record[f"{area}_occ"]`/`record[f"{area}_cap"]` (still clamps unoccupied ≥ 0); `compute_groups(record)` reads canonical keys and `record["adult_ed"]`/`record["peds_ed"]`. The 25-group output, group `id`s, and LOINC codes must be unchanged.
- [x] T009 Update `tests/test_compute.py` for the new signatures: `_make_row` builds a NormalizedRow (canonical keys, ints), `get_occupied_and_unoccupied` tests pass a record + area, `parse_reporting_date` tests stay as-is; add `test_original_format_no_regression`: run the converter on `input/2025.10.21.Test.Facility.BedCapacity.csv`, strip volatile fields, and `assertEqual` against `specs/008-multi-format-csv-input/regression-baseline.json`.
- [x] T010 [P] Create `tests/test_formats.py`: `slugify` cases (incl. `"AMC - University Triangle" → "amc-university-triangle"`); `detect_format` returns the `original` descriptor for the original fixture's header; `detect_format` raises `UnrecognizedFormatError` for the header of `WA-HEALTH-DataDictionary.Variable Catalog.KC.2026-04-30.csv`; `parse_rows` on the original fixture yields the expected number of NormalizedRows with correct canonical-key values for a known row.
- [x] T011 Run the foundational gate: `ruff check convert.py`; `python3 -m unittest discover tests`; the four-step FHIR validation pipeline (per `quickstart.md` / CLAUDE.md) over `input/2025.10.21.Test.Facility.BedCapacity.csv` with `config.example.json` → zero project-introduced validator errors. Fix and re-run until green.

**Checkpoint**: Original format works through the new pipeline with no regression; detection + normalized-row plumbing in place.

---

## Phase 3: User Story 1 — Convert a King County multi-hospital census file (Priority: P1) 🎯 MVP

**Goal**: `python3 convert.py input/census_20260511.FromKC.SubsetObfsctd.csv …` produces one valid bed-capacity Bundle per (facility, reporting date) row, each carrying that facility's identity (config registry entry, or a sparse Organization/Location with a deterministic placeholder NHSN OrgID + a WARNING).

**Independent Test**: Run the converter on `input/census_20260511.FromKC.SubsetObfsctd.csv`; expect 9 Bundles across the distinct `Reporting Date` subdirectories, distinct Organization identities per facility, registered facilities fully populated and unregistered ones sparsely populated, and all 9 passing the HL7 FHIR validator with zero project-introduced errors.

- [x] T012 [US1] In `convert.py`, add the `kc_mft_2026_05_11` descriptor to `SUPPORTED_FORMATS` exactly per `contracts/input-formats.md` §3 (`detect_columns=("Facility","Reporting Date")`, `multi_facility=True`, `has_guid=False`, `date_formats=("%Y-%m-%d","%m/%d/%Y")`, full `column_map`; `Created On`/`Contact` deliberately absent from the map). No parser code needed — `parse_rows` is generic.
- [x] T013 [US1] In `convert.py`, extend `load_config`: accept an optional top-level `facilities` object; if present it must be a dict and every value must contain non-empty `organization` and `location` objects, else exit with a clear error. Absence (or a missing entry) is not an error.
- [x] T014 [US1] In `convert.py`, add `resolve_facility_profile(record, config, descriptor) -> (profile, unregistered: bool)` per `data-model.md`: for `multi_facility=False` descriptors return `{"organization": config["organization"], "location": config["location"]}, False`; for `multi_facility=True` return `config["facilities"][name], False` when present, else a synthesized sparse profile (`organization.name`/`location.name`/`location.description` = `record["facility_name"]`; no address/phone) with `unregistered=True` and `logger.warning("Facility %r not in config 'facilities' registry; emitting sparsely-populated Organization/Location with a placeholder identifier (%s|%s)", name, UNREGISTERED_FACILITY_SYSTEM, slugify(name))`. The top-level `organization`/`location` are never a partial fallback for an unregistered facility.
- [x] T015 [US1] In `convert.py`, re-sign `build_organization_resource(profile, unregistered=False)` and `build_location_resource(profile, org_ref, unregistered=False)`: when `unregistered`, set `Organization.identifier = [{"system": UNREGISTERED_FACILITY_SYSTEM, "value": slugify(profile["organization"]["name"])}]` and `Location.identifier = [{"system": UNREGISTERED_FACILITY_SYSTEM, "value": slugify(...) + ":location"}]`, omit `address`, keep everything else identical. Update `build_organization_entry`, `build_location_entry`, `build_measure_report_resource`/`build_measure_report_entry`, and `build_device_*` (Device is unchanged but its builder still takes `config["software"]`) call sites to pass the resolved profile + flag.
- [x] T016 [US1] In `convert.py`, update `build_bundle`/`main()`: per row, call `resolve_facility_profile`; build Org/Location/MeasureReport from the resolved profile; compute `stable_facility_key = record["facility_guid"] or slugify(record["facility_name"])` and use it (instead of `row.get("facility_guid")`) when seeding `upsert_bundle`'s deterministic UUID. Output filename stays `{sanitize_filename(facility_name)}.{YYYY-MM-DD}.BedCapacity.json` under the date subdir.
- [x] T017 [US1] In `convert.py`, update the `--fhir-server` path (FR-008b): cache `org_ref` and `loc_ref` in dicts keyed by facility name (not once-per-run); `upsert_organization`/`upsert_location` take the resolved `profile` + `unregistered` flag; when `unregistered`, search by `UNREGISTERED_FACILITY_SYSTEM|<slug>` instead of `NHSN_SYSTEM|<id>`; Device still upserted once.
- [x] T018 [US1] Update `config.example.json`: add a `facilities` block registering a subset of the census fixture's facilities (e.g. `"Seaside Medical Center"` and `"AMC - Southeast"`) with placeholder-but-structurally-valid `organization`/`location`; leave the remaining census facilities unregistered so CI exercises the sparse path. Also `git add input/census_20260511.FromKC.SubsetObfsctd.csv` — it is currently untracked and is the canonical fixture for `kc_mft_2026_05_11`.
- [x] T019 [US1] Add to `tests/test_formats.py`: `detect_format` returns the `kc_mft_2026_05_11` descriptor for the census fixture header; `parse_rows` yields 9 NormalizedRows with the expected `facility_name`/`reporting_date`/bed counts for a couple of known rows; `resolve_facility_profile` returns `unregistered=False` for a registered facility and `unregistered=True` (with the placeholder identifier) for an unregistered one.
- [x] T020 [US1] Run the validation pipeline on `input/census_20260511.FromKC.SubsetObfsctd.csv` with `config.example.json`: confirm 9 Bundles, correct date subdirs, distinct identities, and zero project-introduced validator errors. **If** the validator flags a slice error on `Organization.identifier` for the sparse Bundles, switch the placeholder to the contingency form (system = `https://www.cdc.gov/nhsn/OrgID` per `NHSN_SYSTEM`, value = `UNREGISTERED-<slug>`) per research R1 in T015, and re-run until green.

**Checkpoint**: KC multi-hospital files convert end-to-end and validate; original format still green. MVP complete.

---

## Phase 4: User Story 2 — Convert a file in the 2026-04-30 WA Health dictionary schema (Priority: P2)

**Goal**: A data CSV whose header is the Variable Names from the 2026-04-30 catalog converts to valid bed-capacity Bundles, with `all_inpatient_*` and the `covid_*`/`flu_*`/`rsv_*` columns ignored.

**Independent Test**: Run the converter on `input/2026.04.30.Test.Facility.WAHealthDict.csv`; expect one bed-capacity Bundle per row, the HRD/`all_inpatient_*` columns absent from output, and the Bundles passing FHIR validation.

- [x] T021 [US2] In `convert.py`, add the `wahealth_dict_2026_04_30` descriptor to `SUPPORTED_FORMATS` exactly per `contracts/input-formats.md` §2 (`detect_columns=("facility","reportingday")`, `multi_facility=False`, `has_guid=False`, `date_formats=("%Y-%m-%d","%m/%d/%Y")`, `column_map` covering only the 8 bed areas + `prevd_adult_ed`/`prevd_ped_ed` + `facility`/`reportingday` — `all_inpatient_*`, `county`, `created_on`, and all `covid_*`/`flu_*`/`rsv_*` columns are intentionally NOT in the map).
- [x] T022 [US2] Create `input/2026.04.30.Test.Facility.WAHealthDict.csv`: header row = the Variable Names from `WA-HEALTH-DataDictionary.Variable Catalog.KC.2026-04-30.csv` (in section order), plus 1–2 synthetic data rows with realistic bed/ED numbers and *also* populated `all_inpatient_*` and a few `covid_*`/`flu_*`/`rsv_*` values (so tests can prove they're ignored). Commit the new fixture (`git add input/2026.04.30.Test.Facility.WAHealthDict.csv`).
- [x] T023 [US2] Add to `tests/test_formats.py`: `detect_format` returns the `wahealth_dict_2026_04_30` descriptor for the new fixture; `parse_rows` on it yields NormalizedRows whose canonical values come from `*_occ`/`*_cap`/`prevd_*_ed` (and whose aggregates, via `compute_groups`, do **not** equal the `all_inpatient_*` columns when those were set inconsistently).
- [x] T024 [US2] Run the validation pipeline on `input/2026.04.30.Test.Facility.WAHealthDict.csv` with `config.example.json` → zero project-introduced validator errors.

**Checkpoint**: All three formats parse and validate.

---

## Phase 5: User Story 3 — Safe handling of the original format and of unrecognized files (Priority: P3)

**Goal**: Original-format output is provably unchanged (regression test, already added in T009); unrecognized files (incl. the variable-catalog reference file) fail loudly with no output written.

**Independent Test**: (a) the T009 regression test stays green; (b) `python3 convert.py "WA-HEALTH-DataDictionary.Variable Catalog.KC.2026-04-30.csv"` and `python3 convert.py /tmp/empty.csv` each exit non-zero, print a message naming the three supported formats, and create no files; (c) a CSV whose header matches a format but lacks a mapped column errors with that column named.

- [x] T025 [US3] In `convert.py`, harden the `main()` error path (building on T007): the `UnrecognizedFormatError` handler logs `"Unrecognized CSV layout. Supported formats: <display_name>; <display_name>; <display_name>"` and exits non-zero; verify `os.makedirs(output_dir)` and every file write happen strictly after successful detection+parse; the missing-mapped-column `ValueError` from `parse_rows` is caught and reported the same way (loud, non-zero, no output).
- [x] T026 [US3] Add to `tests/test_formats.py`: feeding `detect_format` the variable-catalog file's header raises `UnrecognizedFormatError`; invoking `main()` (or a small wrapper) on that file and on an empty file exits non-zero, the log/stderr names all three formats, and the output directory was not created; a header matching a known format but missing a mapped column raises the expected `ValueError` naming the column.

**Checkpoint**: All three user stories independently functional and tested.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T027 [P] Update `README.md` (FR-013): document the three supported input formats and how detection works (header signatures), the `facility_guid`→`slugify(facility_name)` fallback, the optional `config.json` `facilities` registry, and the sparse-Organization/Location + placeholder-identifier behavior with its WARNING. Note that the variable-catalog `.csv` is a schema reference, not an input file.
- [x] T028 Update `.github/workflows/ci.yml`: change the "Run converter against test fixtures" loop from `for csv in input/*.BedCapacity.csv` to `for csv in input/*.csv` (keep the `*column-labels-only*` skip) and update the inline comment to match.
- [x] T029 Update `CLAUDE.md` "LLM Validation Pipeline" Step 1: change the loop to `for csv in input/*.csv` (keep the `*column-labels-only*` skip) so the documented pipeline matches CI.
- [x] T030 [P] If T020/T024 surfaced any new validator-error pattern attributable to an upstream IG (not expected), add a documented entry to `known-validation-issues.md` (exact message, resource type, root cause, upstream package/WG, repro, environment) and add the matching `grep -v` filter in `.github/workflows/ci.yml`. Otherwise no-op.
- [x] T031 Final validation per `quickstart.md`: `ruff check convert.py`; `python3 -m unittest discover tests`; the four-step FHIR pipeline over **all** `input/*.csv` fixtures (skipping `*column-labels-only*`) with `config.example.json` → zero project-introduced errors; spot-check that the run produced one Bundle per data row across all fixtures and that the sparse-facility WARNINGs appeared as expected.
- [x] T032 If `convert.py` now exceeds ~1000 lines, extract `csv_formats.py` containing exactly `detect_format`, `UnrecognizedFormatError`, `SUPPORTED_FORMATS`, `parse_rows`, `parse_date_flexible`, and `slugify`; `convert.py` imports from it. Update `tests/test_formats.py` imports and the `ci.yml`/`CLAUDE.md` `grep -oP ... convert.py` IG-version lines only if those constants moved (they don't). Re-run T031. (Skip if under the threshold — see research R7.)

---

## Dependencies & Execution Order

- **Phase 1 (Setup, T001)** — must run on the pre-change tree; do it first.
- **Phase 2 (Foundational, T002–T011)** — depends on T001 (for T009). Internally mostly sequential on `convert.py`: T002 → T003 → T004 → T005 → T006 → T007 → T008; then tests T009 (needs T007+T008) and T010 [P with T009, different file]; then gate T011 (needs all). **Blocks all user stories.**
- **Phase 3 (US1, T012–T020)** — after Phase 2. Sequential on `convert.py`: T012 → T013 → T014 → T015 → T016 → T017; T018 [P, config file] and T019 [P, test file] after T012–T014; T020 last (needs T012–T018).
- **Phase 4 (US2, T021–T024)** — after Phase 2 (independent of US1's identity code, but T021/T023 touch `SUPPORTED_FORMATS`/`test_formats.py`, so run after US1 to avoid merge conflicts unless coordinated). T021 → T022 [P] → T023 → T024.
- **Phase 5 (US3, T025–T026)** — after Phase 2 (T025 builds on T007; T026 touches `test_formats.py`). The regression half is already delivered by T009.
- **Phase 6 (Polish, T027–T032)** — after all stories. T027/T030 [P]; T028 then T029 then T031; T032 conditional, last.

### User Story independence

- **US1 (P1)**: independently testable via the census fixture once Foundational is done. The MVP.
- **US2 (P2)**: independently testable via the new dictionary fixture; needs only Foundational (the generic parser already handles it once the descriptor exists).
- **US3 (P3)**: the "no regression" guarantee is delivered by Foundational + T009; this phase adds the unrecognized-file behavior + tests. Independently testable.

### Parallel opportunities

Limited — this is a single-file feature. Genuinely parallelizable: T009 ∥ T010 (different test concerns/files once their `convert.py` deps land); T018 (config) ∥ T019 (test) ∥ continued `convert.py` edits; T027 (README) ∥ T030 ∥ code. Everything that edits `convert.py`, `tests/test_formats.py`, or `SUPPORTED_FORMATS` serializes.

---

## Implementation Strategy

### MVP (delivers the P1 value)

1. Phase 1 (T001) — capture baseline.
2. Phase 2 (T002–T011) — detection + normalized model + `compute_groups` refactor; original format green, no regression.
3. Phase 3 (T012–T020) — KC multi-hospital end-to-end, validated.
4. **STOP & VALIDATE**: census fixture → 9 valid Bundles; original fixture still green.

### Incremental delivery

MVP → add US2 (T021–T024: dictionary format) → add US3 (T025–T026: hardened errors + tests) → Polish (T027–T032: README, CI/CLAUDE.md loop, final pipeline, optional file split).

---

## Notes

- `[P]` = different file, no dependency on an incomplete task. The single-file nature of `convert.py` means most code tasks are sequential — don't fake parallelism.
- Each user story phase ends at a checkpoint where you can run that story's Independent Test.
- The constitution mandates the four-step FHIR validation pipeline before completing any work that touches `convert.py`, config, or FHIR output — T011, T020, T024, and T031 are not optional. If `validator_cli.jar`/Java is unavailable locally, stop and tell the user rather than skipping.
- Watch the research R1 risk in T020: if the SAFR submitting-organization profile requires the NHSN-system identifier slice, use the contingency placeholder form — the spec (FR-008/FR-008a) is satisfied either way; zero validator errors is the hard constraint.
- Commit after each task or logical group; keep the README change in the same PR as the code (constitution: README as Living Documentation).
