<!--
Sync Impact Report
- Version change: 1.7.0 → 1.8.0
- Modified principles:
  - "Validation-Driven Testing" — replaced the stale "the `input/`
    directory contains canonical test CSV files ... Plan to relocate
    test fixtures to a `test/` directory" rule with a concrete
    convention: canonical fixtures now live in `test/input/`, and
    processing fixtures from that directory MUST write generated FHIR
    to `test/output/` (mirroring the production `output/` layout) so
    test artifacts never mix with production output. Updated the LLM
    Development Validation steps to read fixtures from `test/input/`
    and write to `test/output/`.
  - "Clear, Predictable Output" — clarified that the canonical layout
    rules describe the production `output/` tree, and that test runs
    over `test/input/` emit the same structure under `test/output/`.
- Added sections: None
- Removed sections: None
- Templates requiring updates:
  - .specify/templates/plan-template.md — ✅ no updates needed
    (Constitution Check section is generic)
  - .specify/templates/spec-template.md — ✅ no updates needed
  - .specify/templates/tasks-template.md — ✅ no updates needed
  - .specify/templates/commands/ — ✅ no command files exist
- Follow-up TODOs:
  - Physical relocation of fixtures from `input/` to `test/input/`,
    plus the corresponding `convert.py` / CI (`.github/workflows/ci.yml`)
    / `CLAUDE.md` / `README.md` updates that route fixture processing
    to `test/output/`, are a separate implementation change — ⚠ pending
    (constitution amended first to establish the convention).
-->

# WA Health SAFR CSV-to-FHIR Converter Constitution

> Principles governing the development, testing, and maintenance of a
> Python utility that converts Washington State hospital bed capacity
> and HRD surveillance CSV data into FHIR R4 Bundles compliant with
> the US SAFR Implementation Guide and the CDC NHSN SAFR Content
> Implementation Guide. Input arrives in several hospital CSV layouts;
> the converter normalizes them to a single internal model before
> generating FHIR.

## Core Principles

### Zero-Dependency Runtime

The converter MUST run on Python 3 standard library only. No
third-party packages may be added as runtime dependencies.

**Rationale:** This tool is deployed to data manager workstations at
~100 Washington State hospitals. These environments are diverse, often
locked-down, and managed by non-developers. Every external dependency
is a deployment barrier. The stdlib-only constraint was a founding
design decision and remains non-negotiable.

**Rules:**
- All runtime functionality uses only Python 3 built-in modules (csv,
  json, uuid, urllib, datetime, logging, argparse, os, sys, etc.).
- Dev/test dependencies (linters, validators, test frameworks) are
  permitted but MUST NOT be required to run the converter itself.
- If a capability cannot be achieved with stdlib, prefer a simpler
  design over adding a dependency.

### FHIR Profile Conformance

All generated resources MUST conform to the US SAFR Implementation
Guide profiles and the CDC NHSN SAFR Content IG Measure definitions,
and pass the HL7 FHIR Reference Validator with zero errors.

**Rationale:** The output is consumed by state and federal FHIR servers
that enforce profile validation. A non-conformant Bundle is a rejected
submission. Profile conformance is a correctness requirement, not a
nice-to-have. Two IGs govern this project's output:

- **Base structural IG** (`hl7.fhir.us.safr`, published at
  https://hl7.org/fhir/us/safr) — defines the FHIR profiles for
  Bundle, MeasureReport, and Organization resources.
- **Content IG** (`gov.cdc.nhsn.safr`, published at
  https://safr-ci.nhsnlink.org) — defines the computable Measure
  resources (BedCapacityMeasure, HRDMeasure), CDC-specific
  CodeSystems, ValueSets, and CapabilityStatements. This IG depends
  on the base structural IG.

The converter MUST track which version of each IG it targets and
accommodate version changes without ad-hoc code edits.

**Rules:**
- Bundle: `us-safr-measurereport-bundle` (base IG)
- MeasureReport: `indv-measurereport-deqm` (DaVinci DEQM individual)
- Organization: `us-safr-submitting-organization` (base IG) and
  `qicore-organization`
- Location: `qicore-location`
- Device: `crmi-softwaresystemdevice`
- All internal references use `urn:uuid:` format.
- Period timestamps MUST include timezone offsets (e.g., `+00:00`).
- Warnings from the HL7 validator are acceptable; errors are not.
- When either IG publishes new versions, validate against the latest
  and update profile/Measure URLs accordingly.
- **Base IG Version Tracking:** The code MUST declare which version of
  the US SAFR IG (`hl7.fhir.us.safr`) it was built to conform to.
  This declaration MUST be maintained as a named constant or
  configuration value (not buried in comments) so it is
  programmatically accessible.
- **Content IG Version Tracking:** The code MUST separately declare
  which version of the CDC NHSN SAFR Content IG
  (`gov.cdc.nhsn.safr`) it targets. This MUST be a named constant or
  configuration value distinct from the base IG version, since the
  two IGs are independently versioned.
- **Measure Canonical URLs:** The `MeasureReport.measure` field MUST
  reference the canonical URL defined by the Content IG (e.g.,
  `http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure`),
  not the example Measure URL from the base IG. The base IG's
  `BedCapacityMeasureExample` is informational only; the Content IG's
  `BedCapacityMeasure` is the computable, authoritative definition.
- **IG Version in Output:** Generated FHIR resources SHOULD include
  the target IG version in profile canonical URLs where the IG
  specifies versioned canonicals (e.g.,
  `http://hl7.org/fhir/us/safr/StructureDefinition/...|1.0.0`).
- **Accommodating IG Changes:** When either IG publishes a new
  version, updating the target version MUST be a deliberate,
  reviewable change (constant/config update + validation pass), not
  an automatic or silent upgrade.

### Validation-Driven Testing

The primary test strategy is **end-to-end conformance testing** — run
the converter against known input CSV files and validate the output
Bundles using the HL7 FHIR Reference Validator (`validator_cli.jar`).

**Rationale:** For a data transformation tool targeting a formal
specification, the most valuable test is "does the output conform to
the spec?" Unit tests on internal functions are secondary to this. The
HL7 Reference Validator is the authoritative arbiter of FHIR
conformance. Because both the base and content IGs evolve, tests MUST
record which IG versions they validated against so results are
reproducible and regressions from IG version changes are detectable.

**Rules:**
- The `test/input/` directory contains the canonical test CSV files
  (`2025.10.21.Test.Facility.BedCapacity.csv`,
  `2026.04.30.Test.Facility.WAHealthDict.csv`,
  `census_20260511.FromKC.SubsetObfsctd.csv`, plus any
  `*column-labels-only*` header references). These serve as regression
  inputs. When the converter processes fixtures from `test/input/`,
  generated FHIR MUST be written to `test/output/` — which mirrors the
  production `output/` layout (see "Clear, Predictable Output") — so
  that test artifacts never mix with production output.
- Every supported input CSV format (see "Multi-Format CSV Input")
  MUST have at least one canonical test fixture exercised by CI's
  validation pipeline. Adding a new input format without a
  corresponding fixture is incomplete work.
- CI MUST run the converter against all test inputs, then validate
  every output Bundle with the HL7 FHIR Validator. Zero errors = pass.
- Developers SHOULD run FHIR validation locally during development,
  not only in CI. LLM agents MUST do so (see LLM Development
  Validation below).
- When adding new functionality (e.g., HRD surveillance measures), add
  corresponding test CSV rows that exercise the new columns.
- Supplement conformance tests with targeted unit tests for computation
  logic (e.g., aggregate calculations, unoccupied-bed clamping, date
  parsing, format detection) where correctness is not fully captured
  by profile validation alone.
- **IG Version in Validation:** The HL7 FHIR Validator MUST be
  invoked with both SAFR IG packages versioned (e.g., via
  `-ig hl7.fhir.us.safr#1.0.0 -ig gov.cdc.nhsn.safr#1.0.0`) rather
  than unversioned references, so validation results are reproducible
  and cover both structural profiles and content definitions.
- **Recording the IG Version:** CI output and test artifacts MUST
  record which versions of both IGs were used for validation. This
  MAY be achieved by logging the `-ig` arguments, embedding them in
  test output, or maintaining them in CI configuration variables.
- **Version Change as a Test Event:** When either target IG version is
  updated, a full validation pass against the new version MUST be
  performed and its results reviewed before the version change is
  merged.
- **LLM Development Validation:** When an LLM agent (Claude Code,
  Copilot, etc.) performs development work that could affect FHIR
  output, it MUST run the same validation pipeline as GitHub CI
  before considering the work complete. Specifically:
  1. Run the converter against all test fixtures in `test/input/`
     (excluding `*column-labels-only*` files):
     `python3 convert.py "$csv" --config config.example.json --output-dir test/output`
  2. Extract the IG version constants from `convert.py`.
  3. Run the HL7 FHIR Validator against all generated Bundles:
     `java -jar validator_cli.jar $(find test/output -name '*.json') -version 4.0.1 -ig hl7.fhir.us.safr#$SAFR_IG_VERSION -ig https://safr-ci.nhsnlink.org/package.tgz`
  4. Zero errors required; warnings are acceptable.
  The LLM MUST NOT skip validation to save time or defer it to CI.
  If `validator_cli.jar` or Java is not available locally, the LLM
  MUST inform the user and request that the environment be set up
  before proceeding, rather than silently skipping validation.
- **Known Upstream Validation Issues:** Some FHIR validation errors
  originate in upstream IG dependencies (e.g., DEQM cross-version
  extension resolution failures) rather than in this project's
  converter output. These errors MUST be documented in
  `known-validation-issues.md` at the repository root and filtered
  in CI so the build stays green while they remain unresolved
  upstream.
  - Each entry in `known-validation-issues.md` MUST include: the
    exact validator error message, the affected resource type, root
    cause analysis, the responsible upstream package and HL7 working
    group, reproduction steps proving the error exists in the IG's
    own published examples, and the environment tested.
  - Known issues MUST NOT be silently ignored. They are tracked
    explicitly so the project can report them to the responsible HL7
    working groups (e.g., Da Vinci CQI for DEQM issues, SAFR WG for
    SAFR profile issues) and advocate for upstream fixes.
  - When an upstream fix is published (new IG version, validator
    update), the corresponding entry MUST be retested and removed
    from `known-validation-issues.md` if resolved.
  - CI filtering logic MUST match only the specific error patterns
    documented in `known-validation-issues.md` — never broad
    wildcards that could mask new, legitimate errors.
  - LLM agents performing local validation (see above) SHOULD apply
    the same known-issue filtering as CI. If they encounter errors
    matching documented known issues, they SHOULD note them but MUST
    NOT treat them as blockers. Errors not matching known issues
    remain blockers.

### Multi-Format CSV Input

The converter MUST accept the supported hospital CSV layouts and
normalize each to a single internal row model before any FHIR
generation. Downstream code (group computation, Bundle assembly,
server persistence, validation) MUST be format-agnostic.

**Rationale:** Source systems do not agree on a column schema.
Washington State hospitals submit data in at least three distinct
shapes today, and more reporting jurisdictions will appear over time.
Pushing format knowledge to a thin parsing/detection layer — rather
than threading conditionals through the FHIR generation logic — keeps
the conformance-critical code path stable and testable, and makes
adding a fourth format a localized change.

**Supported formats:**
- **Original WA Health format** — snake_case headers, one facility per
  file; identifier columns `facility_guid`, `facility_name`,
  `reporting_date` (`MM/DD/YYYY`); bed columns
  `<area>_currently_occupied` / `<area>_capacity` for the eight bed
  areas; ED columns
  `previous_day_adult_emergency_department_visits` /
  `previous_day_pediatric_emergency_department_visits`; ~35 HRD
  (COVID / influenza / RSV) columns present in the file. This is the
  format already implemented; canonical fixture:
  `2025.10.21.Test.Facility.BedCapacity.csv`.
- **"2026-04-30 WA Health dictionary from KC"** — the schema
  published in
  `WA-HEALTH-DataDictionary.Variable Catalog.KC.2026-04-30.csv`;
  a `Section, Variable Name, Data Type, Description, Notes` catalog
  defining: Report section (`facility`, `county`, `reportingday`,
  `created_on`); Bed Occupancy section (`all_inpatient_cap` /
  `all_inpatient_occ` plus `<area>_cap` / `<area>_occ` for the eight
  areas, `prevd_adult_ed`, `prevd_ped_ed`); COVID-19, Influenza, and
  RSV Stats sections (`covid_*`, `flu_*`, `rsv_*` hospitalization,
  ICU, and age-banded admission counts). No `facility_guid`.
- **"KC multi-hospital from MFT 2026-05-11"** — Title Case headers,
  **multiple facilities and multiple reporting dates per file**;
  columns `Facility`, `Contact`, `Reporting Date` (`YYYY-MM-DD`),
  `Created On` (ISO timestamp), bed occupancy/capacity per area
  (e.g., `ICU Adult Occupancy` / `ICU Adult Capacity`, `Neonatal ICU
  Beds Currently in Use` / `Neonatal ICU Beds Capacity`, `Surge Beds
  Currently in Use` / `Surge Beds Capacity`, `Adult Other Inpatient
  Beds Currently in Use` / `Adult Other Inpatient Beds Capacity`),
  `Previous Day Adult ED Visits`, `Previous Day Pediatric ED Visits`.
  No `facility_guid`; no HRD columns. Sample fixture:
  `census_20260511.FromKC.SubsetObfsctd.csv`.

**Rules:**
- A format-detection step MUST identify the input layout from its
  header signature (and, where needed, file structure) and dispatch
  to the matching parser/mapper. Detection MUST be deterministic.
- An unrecognized layout MUST fail loudly with a clear error naming
  the supported formats — never a silent best-effort or partial parse.
  (A row resolving to all-zero counts because column names did not
  match is the prohibited failure mode here.)
- Each format's parser maps to the same internal row model; the FHIR
  generation code MUST NOT branch on the originating format.
- Multi-facility input files MUST be supported: the converter
  processes every distinct (facility, reporting date) row and emits
  one Bundle per row, regardless of how many facilities appear in a
  single file.
- Date parsing MUST accommodate each format's date convention
  (`MM/DD/YYYY`, ISO `YYYY-MM-DD`, ISO timestamp); the internal model
  stores a normalized date.
- When `facility_guid` is absent (the "2026-04-30 WA Health
  dictionary from KC" and "KC multi-hospital from MFT 2026-05-11"
  formats), the converter MUST derive a stable identifier from
  available fields (e.g., facility name + reporting date) for
  deterministic Bundle identifiers and FHIR-server upsert keys. This
  fallback MUST be documented in `README.md`.
- Columns a given format does not carry (e.g., HRD counts in the "KC
  multi-hospital from MFT 2026-05-11" format, `county`/`created_on` in
  the original format) are simply absent from that format's row model;
  their corresponding outputs are omitted, not defaulted to fabricated
  values.
- New input formats MUST be added by extending the
  detection/parser/mapper layer — never by special-casing a layout
  inside the FHIR generation code or by mutating the shared internal
  model's contract.
- Each supported format MUST have a canonical test fixture (see
  "Validation-Driven Testing").

### Data Integrity and Defensive Transformation

The converter MUST handle real-world data quality issues gracefully,
never producing silently incorrect output.

**Rationale:** Hospital-reported CSV data is messy. Occupied counts can
exceed capacity. Fields can be empty or malformed. The converter must
be robust to these realities because a subtle data error in a public
health report is worse than a loud failure.

**Rules:**
- Empty or non-numeric fields default to 0 via `safe_int()`, with
  logging.
- Computed values (e.g., unoccupied beds) are clamped to 0 — never
  negative.
- Aggregates are computed from raw CSV values, not from intermediate
  mappings, to avoid compounding rounding or clamping artifacts.
- Every data quality accommodation MUST be logged at WARNING level or
  above.
- New mappings (e.g., HRD surveillance) and new input-format parsers
  MUST follow the same defensive patterns. Note that "missing column
  because the format does not define it" is a structural fact handled
  by format detection (see "Multi-Format CSV Input"), distinct from
  "expected column present but empty/malformed" handled here.

### Scope — Bed Capacity and HRD Surveillance

The converter covers two SAFR measure domains: **bed capacity**
(current) and **HRD surveillance** (planned).

**Rationale:** The initial scope was bed capacity only. The project
team has decided to expand to include Hospital Respiratory Data
(HRD) — COVID-19, influenza, and RSV hospitalization and admission
metrics. Both Measure definitions (`BedCapacityMeasure` and
`HRDMeasure`) are published by the CDC NHSN SAFR Content IG
(`gov.cdc.nhsn.safr`), which is the authoritative source for
computable Measure resources.

**Rules:**
- Bed capacity: 7 bed types x occupied/unoccupied, 3 ED visit groups,
  8 computed aggregates = 25 MeasureReport groups. This mapping is
  stable.
- HRD surveillance: Implementation pending. Will produce a separate
  MeasureReport (or extend the existing one) per the Content IG's
  `HRDMeasure` definition.
- HRD output is produced only for input formats that actually carry
  HRD columns (e.g., the original WA Health format and the "2026-04-30
  WA Health dictionary from KC"). A format without HRD columns (e.g.,
  "KC multi-hospital from MFT 2026-05-11") yields bed-capacity output
  only; this is expected, not an error.
- Each measure domain MUST have its own test CSV fixtures and
  validation targets.
- Do not add measure domains beyond bed capacity and HRD without a
  constitution amendment. (Adding a new *input format* for an
  existing measure domain is governed by "Multi-Format CSV Input" and
  does not require an amendment.)

## Deployment & Security

### Configuration over Code Changes

Hospital-specific data MUST live in configuration files, never
hardcoded.

**Rationale:** ~100 hospitals each have unique identifiers, addresses,
and credentials. A single script with per-hospital config files is the
deployment model. Hospital IT staff edit config; they do not edit
Python.

**Rules:**
- `config.example.json` is the canonical template. It MUST stay
  current with all supported configuration fields.
- `config.json` (the real config with secrets) MUST be `.gitignore`'d.
  A `.gitignore` file MUST exist in the repo and MUST include
  `config.json`.
- A pre-commit hook or CI check SHOULD reject commits that include
  `config.json` or files matching `*.secret*`.
- Required config sections are validated at startup with clear error
  messages.

### Secret Protection

OAuth credentials and other secrets MUST NOT enter version control.

**Rationale:** `config.json` contains `client_id` and `client_secret`
for FHIR server OAuth2 authentication. Leaking these credentials could
grant unauthorized access to state health data systems.

**Rules:**
- `.gitignore` MUST include: `config.json`, `*.secret*`, `.env`.
- CI SHOULD include a secret-scanning step (e.g., `git-secrets`,
  `trufflehog`, or GitHub's built-in secret scanning).
- `config.example.json` MUST use obvious placeholder values (e.g.,
  `YOUR_CLIENT_ID`) that would fail authentication if accidentally
  used.
- Documentation must warn users not to commit real configs.

### Clear, Predictable Output

Output files MUST be deterministic, well-named, and organized for
human inspection.

**Rationale:** Hospital data managers and state health officials need
to find, review, and troubleshoot submissions. Output structure is
part of the user experience.

**Rules:**
- Output is organized first by reporting date, then by facility:
  `output/{YYYY-MM-DD}/` holds the Bundle file(s) for that date, and
  `output/{YYYY-MM-DD}/{facility_name}/` holds that facility's
  individual resources.
- Bundle files: `output/{YYYY-MM-DD}/{facility_name}.{reporting_date}.BedCapacity.json`.
- Individual resources — `Organization.json`, `Device.json`,
  `MeasureReport.json`, `Location.json` — MUST be written into the
  per-facility subdirectory `output/{YYYY-MM-DD}/{facility_name}/`,
  never directly into the date directory. This guarantees that
  processing a multi-facility (or multi-row) input file never
  overwrites one facility's individual resources with another's; the
  facility owning a given resource file is unambiguous from its path.
- Multi-facility input files produce one Bundle per (facility,
  reporting date) row; Bundle filenames remain unambiguous because the
  facility name and reporting date are both in the name, and each
  facility's individual resources are isolated in its own subdirectory.
- The converter MUST provide an opt-in runtime flag
  `--bundles-mrs-only` that restricts output to the Bundle and the
  standalone `MeasureReport.json` artifacts and skips the
  rarely-changing `Organization.json`, `Device.json`, and
  `Location.json` files. The default (flag absent) writes the full
  set. The flag MUST be documented in `README.md` and surfaced in
  `--help`.
- JSON MUST be pretty-printed (indented) for human readability.
- Logging to both console (for immediate feedback) and timestamped
  file (for audit trail) in `log/`.
- The layout rules above describe the production `output/` tree. Runs
  over the regression fixtures in `test/input/` (see
  "Validation-Driven Testing") emit the identical structure rooted at
  `test/output/` instead, keeping test artifacts separate from
  production output.

## Development Workflow

### CI Pipeline

All pull requests MUST pass automated checks before merge.

**Rationale:** With AI-assisted development and a small team, CI is
the safety net that catches regressions before they reach hospital
workstations.

**Required checks:**
- **Lint:** Python linter (e.g., `ruff` or `flake8`) with consistent
  style rules.
- **FHIR Validation:** Run the converter against test inputs, then
  validate output with `validator_cli.jar` against both the base IG
  (`hl7.fhir.us.safr`) and the Content IG (`gov.cdc.nhsn.safr`).
  Zero project-introduced errors required. Known upstream errors
  documented in `known-validation-issues.md` MUST be filtered by
  matching their specific error patterns so the build passes while
  they remain unresolved upstream. Any error not matching a documented
  known issue MUST fail the build.
- **Secret scanning:** Reject commits containing likely credentials.
- Checks run via GitHub Actions.
- The CI pipeline itself is subject to this constitution — changes to
  CI config require the same review as code changes.

### README as Living Documentation

Any change that affects user-facing behavior, project architecture,
IG conformance, or developer workflow MUST be evaluated for a
corresponding `README.md` update.

**Rationale:** The README is the first document new contributors,
hospital IT staff, and LLM agents encounter. If it falls out of sync
with the code, users make incorrect assumptions — wrong IG versions,
missing configuration steps, or outdated profile references. Keeping
the README current is cheaper than debugging the confusion it causes
when stale.

**Rules:**
- When a feature adds or changes IG references, profile URLs, CLI
  flags, configuration fields, output structure, supported input
  formats, or version tracking constants, the implementer MUST check
  whether `README.md` needs a corresponding update.
- README updates SHOULD be included in the same PR as the code change,
  not deferred to a follow-up.
- LLM agents performing development work SHOULD flag README staleness
  if they notice the code has diverged from what the README describes.

### Single-File Simplicity (Until It Hurts)

Prefer fewer, well-organized files over premature modularization.

**Rationale:** The converter is currently a single `convert.py` file
(~780 lines). For a focused data transformation tool deployed to
non-developer workstations, a single entry point is an advantage.
Split only when complexity demands it.

**Rules:**
- `convert.py` remains the single entry point for the converter.
- Extract modules only when a clear boundary emerges (e.g., FHIR
  client logic, HRD mapping logic, input-format parsers) AND the
  single file exceeds ~1000 lines.
- Test files, CI config, and dev tooling live in their own directories
  and do not count toward the single-file threshold.
- Any split must preserve the zero-dependency runtime constraint.

## Governance

### Amendment Process

1. Propose the change as a pull request modifying this file.
2. The PR description MUST explain why the change is needed and what
   impact it has on existing specs and implementations.
3. At least one team member must approve.
4. Update version and last-amended date in the same PR.

### Versioning

- **MAJOR:** Removing or fundamentally changing an existing principle.
- **MINOR:** Adding a new principle or expanding scope of an existing
  one.
- **PATCH:** Clarifying language without changing intent.

### Compliance

- All specs and implementation plans MUST reference this constitution.
- AI agents (Claude Code, Copilot, etc.) operating on this repo SHOULD
  be given this constitution as context.
- When a principle conflicts with a practical constraint, document the
  exception and the reasoning in the relevant spec or PR — do not
  silently deviate.

**Version**: 1.8.0 | **Ratified**: 2026-04-01 | **Last Amended**: 2026-06-17
