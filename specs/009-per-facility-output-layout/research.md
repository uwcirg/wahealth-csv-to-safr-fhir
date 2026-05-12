# Research: Per-Facility Output Layout and Bundles-MRs-Only Mode

No NEEDS CLARIFICATION markers were produced — the constitution (v1.7.0) pins the directory layout,
the file names, and the flag name. The notes below record the design decisions implied by the spec
and the existing code in `convert.py`.

## Decision 1: Per-facility subdirectory placement

- **Decision**: In `main()`'s row loop, after computing `date_dir = output_dir/{date_str}` and
  `facility_name = sanitize_filename(...)`, compute `facility_dir = date_dir/{facility_name}` and
  `os.makedirs(facility_dir, exist_ok=True)`. The Bundle file stays written to `date_dir`; each
  individual resource (`{res_type}.json`) is written to `facility_dir`.
- **Rationale**: Matches the constitution rule verbatim; minimal diff; reuses the existing
  `sanitize_filename` so the subdirectory name equals the `{facility_name}` segment of the Bundle
  filename, keeping them consistent (spec FR-003).
- **Alternatives considered**:
  - Subdirectory per (facility, date) at the top level (`output/{facility}/{date}/`) — rejected;
    contradicts the constitution's date-first ordering and the README's existing per-date grouping.
  - Suffixing individual-resource filenames with the facility name and keeping them in `date_dir`
    — rejected; the constitution explicitly requires a subdirectory ("never directly into the date
    directory") and an unambiguous owning path.

## Decision 2: `--bundles-mrs-only` flag

- **Decision**: Add `parser.add_argument("--bundles-mrs-only", action="store_true", help=...)`.
  When `args.bundles_mrs_only` is true, skip writing any **local** individual resource file whose
  `resourceType` is not `MeasureReport`; always write the Bundle. The per-facility subdirectory is
  still created (it holds `MeasureReport.json`). The **FHIR-server persistence block is left
  untouched** — see Decision 5.
- **Rationale**: `store_true` boolean is the simplest faithful implementation of an opt-in flag
  (spec assumption); gating on `resourceType` keeps the change inside the existing
  `for entry in bundle["entry"]` loop.
- **Alternatives considered**:
  - A value-taking option like `--skip-resources Organization,Device,Location` — rejected as
    over-engineered; the constitution specifies exactly one mode.
  - Making it the default — rejected; the constitution says the default writes the full set.

## Decision 5: `--bundles-mrs-only` and FHIR server persistence

- **Decision**: The flag governs only which **local files** are written. Server persistence is
  unchanged: `upsert_bundle` (self-contained Bundle) and `upsert_measure_report` (standalone
  MeasureReport) are the primary persisted artifacts, and `upsert_organization` /
  `upsert_location` / `upsert_device` continue to run as supporting upserts because
  `upsert_measure_report` needs the server-assigned Organization and Location references for the
  MeasureReport's `reporter`/`subject` (and the Bundle carries all of them inline anyway). So the
  same resource set is upserted whether or not the flag is present (confirmed with the user
  2026-05-12).
- **Rationale (why persistence does not read the local JSON files)**: The `upsert_*` functions
  build their payloads from the in-memory `record` / `profile` / `config` / `bundle` objects and do
  *search → create-or-update*, rewriting references to server-assigned IDs as they go (e.g. the
  persisted MeasureReport points at `Location/<server-id>`). The on-disk JSON files are
  pre-persistence resources without server IDs, so they are not a usable input for upsert. Thus
  "what's on disk" and "what's persisted" hold the same *content* derived from the same source;
  only the *set* of artifacts could diverge if one channel were gated and the other not — which is
  why we deliberately do **not** gate the persistence channel.
- **Alternatives considered**:
  - Persist only the Bundle when the flag is set — rejected; loses the individually-addressable
    MeasureReport on the server for no real footprint gain (the Bundle still carries everything).
  - Persist Bundle + MeasureReport but skip Organization/Location upserts — rejected; the standalone
    MeasureReport's references would dangle (or silently rely on a prior full run).

## Decision 3: `--help` and README

- **Decision**: The `help=` string on the new argument satisfies the `--help` requirement
  automatically. README's "Output" section is rewritten to describe `output/{date}/{facility}/` and
  the flag; the options table (currently listing `--output-dir`, `--fhir-server`) gains a
  `--bundles-mrs-only` row. This also clears the constitution's pending README follow-up TODO.
- **Rationale**: Single source of truth for the flag description; satisfies FR-007, FR-009, SC-005.

## Decision 4: Tests

- **Decision**: New `tests/test_output_layout.py` that invokes the converter (in-process via
  `main()` with patched `sys.argv`, or as a subprocess) against an existing canonical fixture and a
  multi-facility fixture in `input/`, then asserts:
  1. `output/{date}/` contains only the Bundle file(s) — no `*.json` resource files directly in it.
  2. For each facility, `output/{date}/{facility}/` contains the four individual resources with
     that facility's data, and a second facility's files do not overwrite the first's.
  3. With `--bundles-mrs-only`: Bundle present, `MeasureReport.json` present per facility, and no
     `Organization.json` / `Device.json` / `Location.json` anywhere under `output/`.
- **Rationale**: Covers spec FR-001..FR-006 and SC-001..SC-003; complements the mandatory
  `validator_cli.jar` pipeline run from CLAUDE.md (SC-004).
- **Alternatives considered**: Relying solely on the FHIR validator — rejected; the validator does
  not check directory layout or which files exist.

## Open questions

None.
