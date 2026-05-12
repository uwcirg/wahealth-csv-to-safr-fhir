# Feature Specification: Support multiple hospital CSV input formats

**Feature Branch**: `008-multi-format-csv-input`
**Created**: 2026-05-11
**Status**: Draft
**Input**: User description: "update per recent changes to the constitution."

## Context

Constitution v1.6.0 added the **Multi-Format CSV Input** principle: the converter
must accept three hospital CSV layouts and normalize each to a single internal row
model before generating FHIR, keeping the conformance-critical code path
format-agnostic. Today the converter only understands the first of the three:

1. **Original WA Health format** — snake_case headers, one facility per file;
   identifier columns `facility_guid`, `facility_name`, `reporting_date`
   (`MM/DD/YYYY`); bed columns `<area>_currently_occupied` / `<area>_capacity`
   for the eight bed areas; ED columns
   `previous_day_adult_emergency_department_visits` /
   `previous_day_pediatric_emergency_department_visits`; ~35 HRD (COVID /
   influenza / RSV) columns present in the file. *Already implemented.*
   Canonical fixture: `input/2025.10.21.Test.Facility.BedCapacity.csv`.
2. **"2026-04-30 WA Health dictionary from KC"** — data CSVs whose columns are the
   Variable Names defined in
   `WA-HEALTH-DataDictionary.Variable Catalog.KC.2026-04-30.csv`: Report fields
   (`facility`, `county`, `reportingday`, `created_on`); Bed Occupancy fields
   (`all_inpatient_cap` / `all_inpatient_occ`, plus `<area>_cap` / `<area>_occ`
   for the eight bed areas, `prevd_adult_ed`, `prevd_ped_ed`); and COVID-19,
   Influenza, and RSV Stats fields (`covid_*`, `flu_*`, `rsv_*`). No
   `facility_guid`. (The catalog file itself is a schema reference, **not** a data
   file the converter ingests.)
3. **"KC multi-hospital from MFT 2026-05-11"** — Title Case headers, **multiple
   facilities and multiple reporting dates per file**; columns `Facility`,
   `Contact`, `Reporting Date` (`YYYY-MM-DD`), `Created On` (ISO timestamp), bed
   occupancy/capacity per area (e.g., `ICU Adult Occupancy` / `ICU Adult
   Capacity`, `Neonatal ICU Beds Currently in Use` / `Neonatal ICU Beds
   Capacity`, `Surge Beds Currently in Use` / `Surge Beds Capacity`, `Adult Other
   Inpatient Beds Currently in Use` / `Adult Other Inpatient Beds Capacity`),
   `Previous Day Adult ED Visits`, `Previous Day Pediatric ED Visits`. No
   `facility_guid`; no HRD columns. Sample fixture:
   `input/census_20260511.FromKC.SubsetObfsctd.csv` (9 data rows).

All three carry the same bed-area and ED data and therefore produce the same
bed-capacity MeasureReport (the existing 25-group output). HRD measure output
remains "implementation pending" per the constitution and is **out of scope** for
this feature, even for the format that carries HRD columns.

## Clarifications

### Session 2026-05-11

- Q: When a multi-hospital row's facility has no config entry, what goes in the
  Organization's required NHSN OrgID `identifier` slot? → A: A deterministic
  placeholder — a fixed "unregistered facility" system URI plus the slugified
  facility name as the value, with a WARNING logged per affected facility. The
  top-level config's NHSN OrgID is NOT used as a fallback in this case.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Convert a King County multi-hospital census file (Priority: P1)

A King County data coordinator receives a single census export covering several
hospitals across several reporting dates ("KC multi-hospital from MFT
2026-05-11" format). They run the converter once on that file and receive one
SAFR bed-capacity Bundle per (facility, reporting date) row, each carrying that
hospital's identity, all passing FHIR validation.

**Why this priority**: This is the pressing operational need driving the change —
King County is already sending data in this layout, and a real sample exists.
Delivering just this story makes the tool usable for that workflow.

**Independent Test**: Run the converter on `census_20260511.FromKC.SubsetObfsctd.csv`
and confirm it emits one Bundle per data row, organized by reporting date, with
each Bundle's Organization/Location reflecting the correct facility, and that all
Bundles pass the HL7 FHIR validator with zero project-introduced errors.

**Acceptance Scenarios**:

1. **Given** a CSV with Title Case MFT-format headers and rows for multiple
   facilities and dates, **When** the converter runs, **Then** it produces one
   Bundle per (facility, reporting date) row, named
   `{facility_name}.{YYYY-MM-DD}.BedCapacity.json` under the matching date
   subdirectory.
2. **Given** an MFT-format row, **When** its bed-capacity Bundle is built,
   **Then** the 25 MeasureReport groups (per-area occupied/unoccupied, ED census,
   computed aggregates) are computed exactly as they are for the original format
   with equivalent inputs.
3. **Given** an MFT-format file with rows for two different hospitals, **When**
   the converter runs, **Then** the two hospitals' Bundles carry distinct
   Organization identities (name and NHSN OrgID) and Locations rather than a
   single shared identity.
4. **Given** an MFT-format file, **When** validated with the HL7 FHIR validator
   against the targeted SAFR IG versions, **Then** there are zero errors not
   attributable to documented known upstream issues.

---

### User Story 2 - Convert a file in the 2026-04-30 WA Health dictionary schema (Priority: P2)

A WA Health analyst exports hospital data in the layout defined by the 2026-04-30
variable catalog from King County. They run the converter and receive valid SAFR
bed-capacity Bundles, with the HRD columns in that layout simply ignored for now.

**Why this priority**: This layout is a defined, supported format per the
constitution, but no live data sample exists yet and HRD processing (the part of
that layout not already covered) is out of scope — so it is lower urgency than
the format King County is actively sending.

**Independent Test**: Convert a fixture whose header row is the Variable Names
from `WA-HEALTH-DataDictionary.Variable Catalog.KC.2026-04-30.csv` and confirm
the resulting Bundles are equivalent (modulo inherently-variable generated
values) to what the original format produces for the same underlying counts, and
that they pass FHIR validation.

**Acceptance Scenarios**:

1. **Given** a CSV with `facility`, `reportingday`, `<area>_occ` / `<area>_cap`,
   and `prevd_*_ed` columns, **When** the converter runs, **Then** it produces
   one bed-capacity Bundle per (facility, reporting date) row.
2. **Given** a dictionary-format row that also contains `covid_*` / `flu_*` /
   `rsv_*` columns, **When** the Bundle is built, **Then** those columns are not
   read and do not appear in the output (bed-capacity output only).
3. **Given** a dictionary-format file, **When** validated with the HL7 FHIR
   validator, **Then** there are zero errors not attributable to documented known
   upstream issues.

---

### User Story 3 - Safe handling of the original format and of unrecognized files (Priority: P3)

An existing user who runs the tool on the original WA Health format sees no change
in behavior or output. Anyone who feeds the tool a file that does not match any
supported layout — including the variable-catalog reference file itself — gets a
clear error and no output, rather than a silently zero-filled Bundle.

**Why this priority**: Regression protection and fail-loud behavior are
correctness guarantees rather than new capabilities, but they are non-negotiable
for a public-health reporting tool. They are P3 only because they gate, rather
than constitute, the new value.

**Independent Test**: (a) Convert the existing original-format fixture and diff
the output against pre-change output, ignoring generated UUIDs/timestamps —
expect no differences. (b) Run the converter on
`WA-HEALTH-DataDictionary.Variable Catalog.KC.2026-04-30.csv` and on an empty
file — expect a non-zero exit, an error naming the supported formats, and no
files written.

**Acceptance Scenarios**:

1. **Given** the original-format fixture `2025.10.21.Test.Facility.BedCapacity.csv`,
   **When** the converter runs after this change, **Then** the generated Bundle
   content matches the pre-change output except for fields that are random or
   time-based by design.
2. **Given** a CSV whose header row matches no supported format, **When** the
   converter runs, **Then** it exits with a non-zero status, logs an error that
   lists the supported formats, and writes no output files.
3. **Given** the variable-catalog reference file (which has a
   `Section,Variable Name,Data Type,...` header), **When** it is passed as input,
   **Then** it is rejected as an unrecognized format (it is documentation, not
   data).

---

### Edge Cases

- **Ambiguous header**: a header row that could plausibly match more than one
  format's signature → detection must resolve deterministically (most-specific
  signature wins) or fail loudly; it must never pick arbitrarily.
- **Recognized format, missing required column**: e.g., an MFT-format file
  missing `Reporting Date`, or a dictionary-format file missing `facility` → the
  converter reports which required column is absent and stops, rather than
  emitting rows with zeroed or blank fields.
- **Header-only file**: a recognized format with a header row but no data rows →
  errors with a clear "CSV file contains no data rows" message and exits non-zero,
  exactly as today. (This is why `*column-labels-only*` fixtures are excluded from
  the CI conversion loop — they exist to pin column names, not to be converted.)
- **Multi-hospital file referencing an unconfigured facility**: a facility name in
  an MFT-format row that has no config entry (no registry, or not found in one) →
  the converter still emits a Bundle for that row, building a sparsely-populated
  Organization and Location from the CSV row alone plus a deterministic
  placeholder NHSN OrgID, and logs a WARNING per affected facility. It does not
  skip the row or stop the run, and it does not borrow the top-level config's
  NHSN OrgID.
- **Awkward facility names in filenames**: MFT facility names contain spaces and
  hyphens (e.g., `AMC - University Triangle`) → existing filename sanitization
  applies; output filenames remain unambiguous because facility name and date are
  both present.
- **Multiple reporting dates in one file** → one date subdirectory per distinct
  reporting date, as today.
- **`Created On` timestamps with sub-second zeros** (e.g., `2026-04-27 13:55:02.0000000`)
  → tolerated; `created_on` is not consumed by this feature.
- **Reporting date in an unexpected style** for a given format (e.g., a
  dictionary-format file using `MM/DD/YYYY` instead of ISO) → the format's date
  parser SHOULD accept common alternatives and normalize; an entirely
  unparseable date is reported per the existing data-integrity behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST determine which supported input format a CSV uses
  from its header row (column-name signature) before parsing any data rows.
- **FR-002**: The system MUST continue to support the **Original WA Health
  format** with no change to its parsing, mapping, or output — existing
  conversions of that format produce the same Bundle content as before this
  change (apart from fields that are random or time-based by design).
- **FR-003**: The system MUST support the **"KC multi-hospital from MFT
  2026-05-11"** format: Title Case headers, multiple facilities and multiple
  reporting dates per file, ISO `YYYY-MM-DD` reporting dates, producing one
  bed-capacity MeasureReport Bundle per (facility, reporting date) row.
- **FR-004**: The system MUST support the **"2026-04-30 WA Health dictionary from
  KC"** format: data CSVs whose columns are the Variable Names defined in
  `WA-HEALTH-DataDictionary.Variable Catalog.KC.2026-04-30.csv`, producing one
  bed-capacity MeasureReport Bundle per (facility, reporting date) row.
- **FR-005**: The system MUST map each format's bed-area and ED columns to one
  shared internal row representation, so that bed-capacity group computation,
  aggregate calculation, Bundle assembly, FHIR-server persistence, and validation
  are identical regardless of the originating format. The FHIR-generation code
  path MUST NOT branch on which format a row came from.
- **FR-006**: When the input header matches no supported format, the system MUST
  stop with a non-zero exit status and an error message that lists the supported
  formats, and MUST NOT write any output files. It MUST NOT attempt a best-effort
  parse; in particular it MUST NOT emit Bundles whose counts are zero because
  column names did not match.
- **FR-007**: When a recognized format has no `facility_guid` (or equivalent GUID)
  column, the system MUST derive a stable, deterministic identifier from
  available fields (e.g., facility name + reporting date) for use as the Bundle's
  deterministic identifier and FHIR-server upsert key, producing the same
  identifier on repeated runs of the same input.
- **FR-008**: For multi-facility input files, each generated Bundle MUST carry the
  hospital identity for that row's facility — the Organization and the Location —
  resolved per facility rather than a single identity shared across the file.
  When the facility has a config entry, that entry supplies the full
  Organization/Location details (NHSN OrgID, name, address, telecom, location
  identifier, etc.). When it does not (no facility registry configured, or the
  facility name is absent from one), the converter MUST still emit the Bundle,
  building a sparsely-populated Organization and Location from the CSV row alone
  (e.g., Organization/Location name = the `Facility` value) plus a deterministic
  placeholder NHSN OrgID — `identifier.system` a fixed "unregistered facility"
  URI, `identifier.value` the slugified facility name — and MUST log a WARNING
  for each such facility. It MUST NOT use the top-level config's NHSN OrgID for
  an unconfigured facility, and MUST NOT skip the row or abort the run.
- **FR-008a**: The placeholder-identifier path notwithstanding, every generated
  Bundle (including those for unconfigured facilities) MUST still pass the HL7
  FHIR validator with zero project-introduced errors — the sparse resources are
  structurally conformant, just under-populated.
- **FR-008b**: When persisting to a FHIR server (`--fhir-server`), a multi-facility
  input file MUST upsert each distinct facility's Organization and Location
  separately (resolved per FR-008), rather than reusing one Organization/Location
  for the whole file; the Device is upserted once per run. Deterministic upsert
  keys use the stable facility identifier from FR-007 (the placeholder
  "unregistered facility" identifier for facilities without a config entry).
- **FR-009**: The system MUST parse each format's reporting-date convention
  (`MM/DD/YYYY` for the original format; ISO `YYYY-MM-DD` for the others) into a
  normalized internal date. Output filenames and FHIR `period` dates remain
  `YYYY-MM-DD` as today. A date parser SHOULD tolerate common alternative styles
  for the same field.
- **FR-010**: Adding a future input format MUST be achievable by extending the
  detection-and-parsing layer alone, without modifying the FHIR-generation,
  aggregate-computation, or validation code.
- **FR-011**: Every supported format MUST have at least one canonical test fixture
  under the project's test inputs directory, and CI MUST run the converter and
  the HL7 FHIR validator against all of them, requiring zero project-introduced
  errors.
- **FR-012**: HRD (COVID / influenza / RSV) columns present in any format MUST NOT
  be processed by this feature; conversions produce bed-capacity output only.
- **FR-013**: `README.md` MUST be updated to document the supported input formats,
  how format detection works, the GUID-fallback behavior, the multi-hospital
  identity/configuration model, and any new configuration fields.
- **FR-014**: All data-integrity behaviors required by the constitution
  (empty/non-numeric fields default to 0 with logging; computed values clamped to
  ≥ 0; aggregates computed from raw values; data-quality accommodations logged at
  WARNING+) MUST apply uniformly across all formats.

### Key Entities

- **Supported input format**: a recognized CSV layout — has a name, a header
  signature used for detection, a reporting-date convention, and the set of fields
  it carries (including whether it carries a GUID and/or HRD columns).
- **Hospital-day record (internal row model)**: a facility identity reference, a
  normalized reporting date, the eight bed areas' occupied and capacity counts,
  and the two ED visit counts; the single representation all formats normalize to
  and the only thing FHIR generation consumes.
- **Facility identity**: a hospital's name, NHSN OrgID, address, telecom, and
  Location details — supplied by configuration; for multi-hospital files, looked
  up per facility (e.g., from a facility registry in config keyed by facility
  name), with the existing single-facility config serving as the default.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three supported formats convert end-to-end; for each, 100% of
  generated Bundles pass the HL7 FHIR validator against the targeted SAFR IG
  versions with zero errors not attributable to documented known upstream issues.
- **SC-002**: Re-converting the existing original-format fixture
  (`2025.10.21.Test.Facility.BedCapacity.csv`) yields Bundle content identical to
  the pre-change output, apart from fields that are random or time-based by
  design — i.e., no regression.
- **SC-003**: Converting the King County sample
  (`census_20260511.FromKC.SubsetObfsctd.csv`, 9 data rows) produces 9 Bundles —
  one per (facility, reporting date) row — each carrying the correct facility's
  Organization and Location, organized into the appropriate date subdirectories.
- **SC-004**: Running the converter on an unrecognized file (the variable-catalog
  reference file, or an empty file) exits with a non-zero status, prints a message
  naming the supported formats, and creates no output files.
- **SC-005**: Each supported format has a committed test fixture, and the CI
  pipeline runs the converter plus FHIR validator over every one of them on each
  pull request.

## Assumptions

- **HRD remains out of scope.** This feature delivers bed-capacity output for all
  three formats; processing the COVID/influenza/RSV columns present in two of them
  is deferred to the separate, still-pending HRD work.
- **The variable-catalog file is documentation, not input.** `WA-HEALTH-DataDictionary.Variable Catalog.KC.2026-04-30.csv`
  defines the column names for the "2026-04-30 WA Health dictionary from KC"
  format; a real data file in that format has those Variable Names as its header
  row. The catalog file itself, if passed to the converter, is rejected as
  unrecognized.
- **No live sample exists for the dictionary format yet**, so a small synthetic
  test fixture in that layout will be created to satisfy FR-011.
- **`reportingday` / `created_on` in the dictionary format are ISO dates
  (`YYYY-MM-DD`).** The catalog only says "Date"; ISO is assumed for consistency
  with the MFT format, and the parser will also accept `MM/DD/YYYY`.
- **Multi-hospital identity: config when available, sparse-from-CSV otherwise.**
  Full per-facility identity (real NHSN OrgID, address, etc.) is not in the MFT
  census file, so it comes from `config.json`. The assumed approach: extend
  `config.json` with an optional facility registry (keyed by facility name)
  supplying each hospital's organization and location blocks; the existing
  top-level `organization` / `location` remain the config for single-facility
  files. The exact config schema is for `/speckit.plan` to settle. When a
  multi-hospital row's facility is not in the registry (or no registry is
  configured at all), the converter does not skip or abort — it builds sparse
  Organization/Location resources from the CSV row plus a deterministic
  placeholder NHSN OrgID (see FR-008), logging a WARNING. The top-level
  single-facility `organization`/`location` config is not used as a fallback for
  these rows, since it describes a different specific hospital.
- **`Contact`, `county`, and `created_on` are not consumed.** The converter reads
  only the columns it needs (facility, reporting date, bed/ED counts); other
  columns a format carries are ignored, as is current behavior.
- **The constitution's data-integrity and zero-dependency constraints continue to
  apply** — no new runtime dependencies; defensive parsing everywhere.
- **Single-file simplicity is preserved.** Detection/parsers are expected to live
  inside `convert.py` unless and until it exceeds the constitution's ~1000-line
  threshold.
