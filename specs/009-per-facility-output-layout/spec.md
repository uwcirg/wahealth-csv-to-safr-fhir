# Feature Specification: Per-Facility Output Layout and Bundles-MRs-Only Mode

**Feature Branch**: `009-per-facility-output-layout`  
**Created**: 2026-05-12  
**Status**: Draft  
**Input**: User description: "update per recent changes to the constitution."

## Context

The project constitution (v1.7.0, amended 2026-05-12) revised the **Clear, Predictable Output**
principle in two ways:

1. Individual resource files MUST live in a per-facility subdirectory
   `output/{YYYY-MM-DD}/{facility_name}/` rather than directly in the date directory, so a
   multi-facility (or multi-row) input file never overwrites one facility's individual resources
   with another's.
2. The converter MUST offer an opt-in runtime flag `--bundles-mrs-only` that restricts output to
   the Bundle and the individual `MeasureReport.json` and skips the rarely-changing
   `Organization.json`, `Device.json`, and `Location.json` files; the flag MUST be documented in
   `README.md` and surfaced in `--help`.

This feature brings the converter's behavior, the README, and the test suite into alignment with
that revised principle.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Isolated individual resources per facility (Priority: P1)

A surveillance analyst converts a multi-hospital CSV file. For every (facility, reporting date) row
the converter writes the facility's individual `Organization.json`, `Device.json`,
`MeasureReport.json`, and `Location.json` into a subdirectory named for that facility, so no
facility's individual resources clobber another's, and the owning facility of any individual resource
file is unambiguous from its path.

**Why this priority**: This is the core correctness fix in the constitution change — without it,
individual resource files from a multi-facility run are unusable because only the last row survives.

**Independent Test**: Convert a multi-facility fixture and confirm that each facility has its own
`output/{date}/{facility_name}/` directory containing that facility's four individual resource
files, and that the date directory itself contains only Bundle files (no loose individual
resources).

**Acceptance Scenarios**:

1. **Given** a multi-facility CSV with rows for facilities A and B on the same reporting date,
   **When** the converter runs with default options, **Then** `output/{date}/A/` and
   `output/{date}/B/` each contain `Organization.json`, `Device.json`, `MeasureReport.json`, and
   `Location.json` with that facility's data, and neither facility's files are overwritten.
2. **Given** any successful conversion, **When** output is written, **Then** the Bundle file is
   `output/{date}/{facility_name}.{date}.BedCapacity.json` (directly in the date directory) and the
   individual resources are inside `output/{date}/{facility_name}/`.
3. **Given** a single-facility CSV, **When** the converter runs, **Then** the same layout applies —
   one per-facility subdirectory is created even though there is only one facility.

---

### User Story 2 - Bundles-and-MeasureReports-only output mode (Priority: P2)

An operator who runs the converter routinely and only cares about the submission payload passes
`--bundles-mrs-only`. The converter writes the Bundle file(s) and the individual
`MeasureReport.json` for each facility but skips writing `Organization.json`, `Device.json`, and
`Location.json`.

**Why this priority**: A convenience / noise-reduction option that depends on the layout in Story 1
being in place; valuable but not a correctness fix.

**Independent Test**: Run the converter on any fixture with `--bundles-mrs-only` and confirm the
date directory has the Bundle file(s), each per-facility subdirectory has only `MeasureReport.json`,
and no `Organization.json` / `Device.json` / `Location.json` files exist anywhere in the output.

**Acceptance Scenarios**:

1. **Given** `--bundles-mrs-only` is supplied, **When** the converter runs, **Then** it writes the
   Bundle file(s) and each facility's `MeasureReport.json` and writes no `Organization.json`,
   `Device.json`, or `Location.json` files.
2. **Given** `--bundles-mrs-only` is **not** supplied, **When** the converter runs, **Then** the
   full set of individual resources is written (current default behavior, in the new layout).
3. **Given** `--help` is invoked, **When** the help text is shown, **Then** `--bundles-mrs-only` is
   listed with a description of its effect.
4. **Given** FHIR server persistence is also requested, **When** `--bundles-mrs-only` is supplied,
   **Then** the Bundle and the standalone MeasureReport are persisted as the primary artifacts and
   the Organization, Device, and Location are still upserted as supporting resources (the Bundle is
   self-contained and the standalone MeasureReport's `subject`/`reporter` references require the
   Location/Organization to exist on the server) — i.e. the flag governs which **local files** are
   written, not what is persisted.

---

### Edge Cases

- **Facility names unsafe for filesystem paths**: A facility name containing path separators or
  other characters not safe in a directory name is sanitized the same way it is already sanitized
  for the Bundle filename, so the subdirectory name and the Bundle filename stay consistent with
  each other.
- **Two rows for the same facility and reporting date**: They resolve to the same per-facility
  subdirectory; the later row overwrites the earlier one's individual resources (unchanged from
  today's per-row overwrite behavior, but now scoped to that one facility rather than all
  facilities).
- **`--bundles-mrs-only` with a format that carries HRD columns**: The flag affects only which of
  the individual Organization/Device/Location files are written; the Bundle and MeasureReport
  content (including any HRD data) is unchanged.
- **Empty or header-only input**: No data rows means no output directories are created — unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For each (facility, reporting date) data row, the converter MUST write the Bundle file
  as `output/{YYYY-MM-DD}/{facility_name}.{YYYY-MM-DD}.BedCapacity.json` — directly in the date
  directory.
- **FR-002**: The converter MUST write each row's individual `Organization.json`, `Device.json`,
  `MeasureReport.json`, and `Location.json` into the per-facility subdirectory
  `output/{YYYY-MM-DD}/{facility_name}/`, never directly into the date directory.
- **FR-003**: The per-facility subdirectory name MUST be derived from the facility name using the
  same sanitization rule already applied to the facility name in the Bundle filename.
- **FR-004**: Processing a multi-facility or multi-row input file MUST NOT cause one facility's
  individual resource files to overwrite another facility's.
- **FR-005**: The converter MUST accept an opt-in runtime flag `--bundles-mrs-only`. When supplied,
  it MUST write only the Bundle file(s) and the individual `MeasureReport.json` for each facility,
  and MUST NOT write `Organization.json`, `Device.json`, or `Location.json`.
- **FR-006**: When `--bundles-mrs-only` is absent (the default), the converter MUST write the full
  set of individual resources in the layout from FR-002.
- **FR-007**: `--bundles-mrs-only` MUST appear in the converter's `--help` output with a
  description of its effect.
- **FR-008a**: `--bundles-mrs-only` MUST NOT alter Bundle contents, MeasureReport contents, the
  logging format, or exit codes — it governs only which local individual resource files are written.
- **FR-008b**: `--bundles-mrs-only` MUST NOT alter FHIR server persistence behavior. The Bundle and
  the standalone MeasureReport are the primary persisted artifacts; the Organization, Device, and
  Location continue to be upserted as supporting resources (the standalone MeasureReport's
  `subject`/`reporter` references require the Location/Organization to exist on the server, and the
  Bundle already carries all of them inline). Net effect: the same resource set is upserted whether
  or not the flag is present — the flag only changes which local files are written.
- **FR-009**: `README.md` MUST be updated to describe the per-facility subdirectory layout and the
  `--bundles-mrs-only` flag, replacing the current description of individual resources sharing the
  date directory.
- **FR-010**: The test suite MUST cover the per-facility layout (including a multi-facility input
  that previously would have overwritten files) and both modes of the `--bundles-mrs-only` flag.

### Key Entities *(include if feature involves data)*

- **Output directory tree**: `output/` → date directory (`YYYY-MM-DD`) → contains Bundle file(s)
  and one subdirectory per facility → each facility subdirectory contains that facility's individual
  resource files (`Organization.json`, `Device.json`, `MeasureReport.json`, `Location.json`, subject
  to `--bundles-mrs-only`).
- **Facility**: Identified by name (sanitized for use in both the Bundle filename and the
  subdirectory name) and reporting date; each (facility, reporting date) row owns one Bundle file
  and one per-facility subdirectory of individual resources.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Converting a multi-facility input file yields, for every facility in the file, a
  distinct per-facility subdirectory whose individual resource files contain that facility's data —
  0% of facilities lose their individual resources to overwrite.
- **SC-002**: After any conversion, the date directory contains only Bundle files; 100% of
  individual resource files are inside per-facility subdirectories.
- **SC-003**: Running with `--bundles-mrs-only` produces output containing Bundle file(s) and
  `MeasureReport.json` only — 0 `Organization.json`, `Device.json`, or `Location.json` files
  written.
- **SC-004**: The full FHIR validation pipeline (per `CLAUDE.md`) passes with zero
  project-introduced errors against output produced in the new layout.
- **SC-005**: `README.md` and `--help` both describe `--bundles-mrs-only`; a reader can determine
  the output layout and the flag's effect without reading the code.

## Assumptions

- "Facility name" in path / filename contexts means the same sanitized value the converter already
  uses for the `{facility_name}` segment of the Bundle filename; no new sanitization scheme is
  introduced.
- The per-facility subdirectory layout applies uniformly to single-facility and multi-facility
  input formats (the constitution does not exempt single-facility layouts).
- `--bundles-mrs-only` is a boolean flag (present / absent); there is no need for a value or for
  finer-grained selection of which individual resources to write.
- FHIR server persistence continues to upsert the same resource set regardless of
  `--bundles-mrs-only` (the Bundle and standalone MeasureReport are the primary artifacts;
  Organization/Device/Location remain as supporting resources). Persistence builds its payloads from
  the in-memory resources and rewrites references to server-assigned IDs — it does not read the
  local JSON files — so reducing the local file set does not change what is sent to the server.
- Existing behavior not mentioned here (header-based format detection, logging to console and
  timestamped file, exit-on-unrecognized-header, HRD handling) is unchanged.
