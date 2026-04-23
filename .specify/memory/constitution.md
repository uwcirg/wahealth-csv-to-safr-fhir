<!--
Sync Impact Report
- Version change: 1.3.0 → 1.4.0
- Modified principles:
  - FHIR Profile Conformance — expanded to distinguish the base
    structural IG (hl7.fhir.us.safr) from the CDC NHSN Content IG
    (gov.cdc.nhsn.safr). Added Content IG Version Tracking rule
    requiring a separate named constant. Updated Measure canonical
    URL guidance to reference the Content IG's canonical
    (http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/...).
  - Validation-Driven Testing — updated validation commands to
    include -ig gov.cdc.nhsn.safr alongside -ig hl7.fhir.us.safr.
    Updated LLM Development Validation section likewise.
  - CI Pipeline — updated FHIR Validation description to reference
    both IGs.
  - Scope — Bed Capacity and HRD Surveillance — added reference to
    the Content IG as the authoritative source for Measure definitions.
- Added sections: None
- Removed sections: None
- Templates requiring updates:
  - .specify/templates/plan-template.md — ✅ no updates needed
    (Constitution Check section is generic, references "constitution
    file")
  - .specify/templates/spec-template.md — ✅ no updates needed
    (no constitution-specific references)
  - .specify/templates/tasks-template.md — ✅ no updates needed
    (no constitution-specific references)
  - .specify/templates/commands/ — ✅ no command files exist
- Follow-up TODOs: None (implemented in feature 006-content-ig-integration)
-->

# WA Health SAFR CSV-to-FHIR Converter Constitution

> Principles governing the development, testing, and maintenance of a
> Python utility that converts Washington State hospital bed capacity
> and HRD surveillance CSV data into FHIR R4 Bundles compliant with
> the US SAFR Implementation Guide and the CDC NHSN SAFR Content
> Implementation Guide.

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
- The `input/` directory contains canonical test CSV files (currently
  `2025.10.21.Test.Facility.BedCapacity.csv`). These serve as
  regression inputs. Plan to relocate test fixtures to a `test/`
  directory.
- CI MUST run the converter against all test inputs, then validate
  every output Bundle with the HL7 FHIR Validator. Zero errors = pass.
- Developers SHOULD run FHIR validation locally during development,
  not only in CI. LLM agents MUST do so (see LLM Development
  Validation below).
- When adding new functionality (e.g., HRD surveillance measures), add
  corresponding test CSV rows that exercise the new columns.
- Supplement conformance tests with targeted unit tests for computation
  logic (e.g., aggregate calculations, unoccupied-bed clamping, date
  parsing) where correctness is not fully captured by profile
  validation alone.
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
  1. Run the converter against all test fixtures in `input/`
     (excluding `*column-labels-only*` files):
     `python3 convert.py "$csv" --config config.example.json --output-dir output`
  2. Extract the IG version constants from `convert.py`.
  3. Run the HL7 FHIR Validator against all generated Bundles:
     `java -jar validator_cli.jar output/**/*.json -version 4.0.1 -ig hl7.fhir.us.safr#$SAFR_IG_VERSION -ig https://safr-ci.nhsnlink.org/package.tgz`
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
- New mappings (e.g., HRD surveillance) must follow the same defensive
  patterns.

### Scope — Bed Capacity and HRD Surveillance

The converter covers two SAFR measure domains: **bed capacity**
(current) and **HRD surveillance** (planned).

**Rationale:** The initial scope was bed capacity only. The project
team has decided to expand to include Hospital Respiratory Data
(HRD) — COVID-19, influenza, and RSV hospitalization and admission
metrics from the ~35 currently-unused CSV columns. Both Measure
definitions (`BedCapacityMeasure` and `HRDMeasure`) are published by
the CDC NHSN SAFR Content IG (`gov.cdc.nhsn.safr`), which is the
authoritative source for computable Measure resources.

**Rules:**
- Bed capacity: 7 bed types x occupied/unoccupied, 3 ED visit groups,
  8 computed aggregates = 25 MeasureReport groups. This mapping is
  stable.
- HRD surveillance: Implementation pending. Will produce a separate
  MeasureReport (or extend the existing one) per the Content IG's
  `HRDMeasure` definition.
- Each measure domain MUST have its own test CSV fixtures and
  validation targets.
- Do not add measure domains beyond bed capacity and HRD without a
  constitution amendment.

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
- Bundle files: `{facility_name}.{reporting_date}.BedCapacity.json`
- Individual resources: `Organization.json`, `Device.json`,
  `MeasureReport.json`, `Location.json` alongside the Bundle.
- Output organized by date: `output/{YYYY-MM-DD}/`.
- JSON MUST be pretty-printed (indented) for human readability.
- Logging to both console (for immediate feedback) and timestamped
  file (for audit trail) in `log/`.

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

### Single-File Simplicity (Until It Hurts)

Prefer fewer, well-organized files over premature modularization.

**Rationale:** The converter is currently a single `convert.py` file
(~780 lines). For a focused data transformation tool deployed to
non-developer workstations, a single entry point is an advantage.
Split only when complexity demands it.

**Rules:**
- `convert.py` remains the single entry point for the converter.
- Extract modules only when a clear boundary emerges (e.g., FHIR
  client logic, HRD mapping logic) AND the single file exceeds ~1000
  lines.
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

**Version**: 1.4.0 | **Ratified**: 2026-04-01 | **Last Amended**: 2026-04-23
