# Implementation Plan: Support multiple hospital CSV input formats

**Branch**: `008-multi-format-csv-input` | **Date**: 2026-05-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-multi-format-csv-input/spec.md`

## Summary

Teach the converter to accept three hospital CSV layouts — the existing **Original
WA Health format**, the **"2026-04-30 WA Health dictionary from KC"** schema, and
the multi-facility **"KC multi-hospital from MFT 2026-05-11"** format — by adding a
header-signature **format-detection step** and a thin **per-format parser layer**
that normalizes every row to one internal record. Downstream code (group
computation, Bundle assembly, FHIR-server upsert, validation) consumes only the
normalized record and is unchanged in behavior. Multi-facility files resolve each
row's hospital identity from an optional `facilities` registry in `config.json`;
when a facility is absent from that registry (or no registry is configured), the
converter still emits the Bundle with a sparsely-populated Organization/Location
built from the CSV row plus a deterministic placeholder NHSN OrgID, logging a
WARNING. HRD (COVID/influenza/RSV) columns present in two of the formats remain
unprocessed (out of scope; HRD measure work is still pending per the constitution).

## Technical Context

**Language/Version**: Python 3 (stdlib only at runtime)
**Primary Dependencies**: None at runtime. Dev: `ruff` (linter), `validator_cli.jar` (FHIR validation), `gitleaks`/`git-secrets` (secret scanning)
**Storage**: Filesystem — CSV input, JSON output, JSON config
**Testing**: HL7 FHIR validator end-to-end conformance + Python `unittest` (`tests/test_compute.py`, plus new `tests/test_formats.py`)
**Target Platform**: Windows/Linux/macOS hospital and county data-manager workstations
**Project Type**: Single-file CLI data-transformation tool
**Performance Goals**: N/A (one-shot batch conversion; files are small — tens to low hundreds of rows)
**Constraints**: Zero runtime dependencies (stdlib only); single-file simplicity (`convert.py`) until it exceeds ~1000 lines; FHIR output must validate with zero project-introduced errors
**Scale/Scope**: ~100 hospital deployments + county-level multi-hospital runs; `convert.py` (~825 lines today)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Zero-Dependency Runtime | PASS | New code uses only stdlib (`csv`, `re`, `datetime`). No runtime deps added. |
| FHIR Profile Conformance | PASS (1 risk) | Output Bundles for configured facilities are byte-equivalent to today. Sparse resources for unregistered facilities MUST still validate (FR-008a). **Risk:** if `us-safr-submitting-organization` mandates the NHSN-system identifier specifically (not just `identifier 1..*`), a placeholder under a different system may not satisfy the slice — see research.md R1; verified by running the validator during implementation. |
| Validation-Driven Testing | PASS | Adds one canonical fixture per format; broadens the CI/LLM conversion loop to cover them; adds `tests/test_formats.py` (detection + parsers) and a `compute_groups` regression test. |
| Data Integrity & Defensive Transformation | PASS | `safe_int`/clamping applied uniformly via the normalized record. Format-detection failure is loud (non-zero exit, no output) — never silent zero-filled Bundles. WARNING on unregistered facility and on every data-quality fallback. |
| Multi-Format CSV Input | PASS | This feature *is* the implementation of the v1.6.0 principle: detection layer, single normalized model, multi-facility support, GUID fallback, per-format fixtures, FHIR-generation code free of format branching. |
| Scope — Bed Capacity and HRD Surveillance | PASS | Bed-capacity output only. HRD columns in the original and dictionary formats are ignored, consistent with "HRD surveillance: implementation pending". No new measure domain. |
| Configuration over Code Changes | PASS | New optional `facilities` registry in `config.json`; `config.example.json` updated to demonstrate it; startup validation extended (registry optional; entries validated when present). |
| Secret Protection | N/A | No secret-handling changes; `config.example.json` keeps placeholder values. |
| Clear, Predictable Output | PASS | Same `{facility_name}.{date}.BedCapacity.json` scheme and date subdirectories; multi-facility files yield one Bundle per (facility, date) row; `sanitize_filename` already covers spaces/hyphens in MFT facility names. |
| CI Pipeline | PASS | Conversion loop broadened from `input/*.BedCapacity.csv` to all `input/*.csv` except `*column-labels-only*`; lint and secret-scan steps unchanged. |
| README as Living Documentation | PASS | FR-013: README updated in the same PR (supported formats, detection, GUID fallback, `facilities` registry, sparse-resource behavior). CLAUDE.md's documented validation pipeline updated to match the new CI loop. |
| Single-File Simplicity | PASS (decision) | Target: keep detection + parsers + column maps in `convert.py`. If the addition pushes `convert.py` past ~1000 lines, extract them to `csv_formats.py` (a clear boundary), leaving FHIR generation in `convert.py` — permitted by the constitution. See research.md R7. |

**Result: PASS** — no unjustified violations; Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/008-multi-format-csv-input/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── input-formats.md #   header signatures + column maps for the 3 formats
│   └── config.md        #   config.json schema (incl. new `facilities` registry)
├── checklists/
│   └── requirements.md  # spec quality checklist (from /speckit.specify)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
convert.py                 # the converter — gains: detect_format(), per-format
                           #   parsers, FORMAT column maps, normalized-row model,
                           #   resolve_facility_profile(), sparse Org/Location +
                           #   placeholder identifier, GUID fallback; compute_groups
                           #   & BED_MAPPINGS refactored to canonical area names.
                           #   (If it crosses ~1000 lines → split out csv_formats.py.)
config.example.json        # gains an example `facilities` registry block
README.md                  # gains: supported input formats, detection, GUID
                           #   fallback, `facilities` registry, sparse behavior
CLAUDE.md                  # validation-pipeline conversion loop updated to match CI
.github/workflows/ci.yml   # conversion loop: input/*.csv minus column-labels-only
known-validation-issues.md # updated only if sparse resources surface a new
                           #   upstream-attributable pattern (not expected)
input/
├── 2025.10.21.Test.Facility.BedCapacity.csv                  # original format (existing)
├── 2025.10.21.Test.Facility.BedCapacity.column-labels-only.csv  # existing
├── census_20260511.FromKC.SubsetObfsctd.csv                  # KC MFT format (existing sample → canonical fixture)
└── 2026.04.30.Test.Facility.WAHealthDict.csv                 # NEW synthetic fixture for the dictionary format
tests/
├── test_compute.py        # updated for new compute_groups signature + regression test
└── test_formats.py        # NEW: detect_format(), per-format parsers, unrecognized-format error
```

**Structure Decision**: Keep the existing single-file CLI layout — `convert.py` at
the repo root, tests in `tests/`, fixtures in `input/`. No `src/` reorganization.
The new detection/parser code lives in `convert.py` unless it pushes the file past
the constitution's ~1000-line threshold, in which case it moves to a sibling
`csv_formats.py` (detection + parsers + column maps only).

## Phase 0 — Research

See `research.md`. Key decisions:

- **R1 — Sparse Organization identifier**: synthesize `identifier = [{system: "urn:wahealth:csv-to-safr:unregistered-facility", value: <slugified facility name>}]`; do not use the config's NHSN OrgID. Assume the SAFR org profile requires `identifier 1..*` (any system), so this satisfies it; confirm by running the validator during implementation.
- **R2 — Sparse Location identifier**: same placeholder system, value `<slug>:location`; `name` = facility name; `description` = facility name; address omitted; everything else (status/mode/type/physicalType/managingOrganization) as today.
- **R3 — Date parsing per format**: original = `%m/%d/%Y` (unchanged); dictionary & MFT = ISO `%Y-%m-%d`, with a fallback that also accepts `%m/%d/%Y`; MFT `Created On` is ignored (not parsed).
- **R4 — Format-detection signatures**: `original` ⇐ `{"facility_guid","reporting_date"} ⊆ header`; `wahealth_dict_2026_04_30` ⇐ `{"facility","reportingday"} ⊆ header`; `kc_mft_2026_05_11` ⇐ `{"Facility","Reporting Date"} ⊆ header`; no match ⇒ `UnrecognizedFormatError` (non-zero exit, message lists supported formats, no output written). The variable-catalog reference file (`Section,Variable Name,...`) matches none ⇒ rejected.
- **R5 — Normalized row model**: a plain dict with canonical keys — `facility_name`, `facility_guid` (`str|None`), `reporting_date` (`datetime.date`), `{area}_occ`/`{area}_cap` for the 8 canonical areas (`adult_icu, peds_icu, adult_acute, peds_acute, neonatal_icu, nursery, surge, other`), and `adult_ed`/`peds_ed`. `compute_groups`, `BED_MAPPINGS`, `ALL_BED_PREFIXES` refactored to these names.
- **R6 — `facilities` config schema**: optional top-level `"facilities": { "<facility name>": { "organization": {…}, "location": {…} } }`; entries are validated (must contain `organization` and `location`) when present. Single-facility formats keep using top-level `organization`/`location`; the top-level block is NOT a fallback for unregistered facilities in a multi-facility file.
- **R7 — File organization**: keep in `convert.py`; extract `csv_formats.py` only if the file crosses ~1000 lines.
- **R8 — CI/LLM conversion loop**: change `for csv in input/*.BedCapacity.csv` → `for csv in input/*.csv` with the `*column-labels-only*` skip retained; mirror the change in `CLAUDE.md` and the constitution-referenced LLM pipeline wording (constitution text already says "all test fixtures in `input/`").
- **R9 — FHIR-server upsert for multi-facility**: cache `org_ref`/`loc_ref` per facility name (not once per run); Device still upserted once; upsert search keys use the placeholder system for unregistered facilities.

## Phase 1 — Design & Contracts

- `data-model.md` — the **NormalizedRow**, **SupportedFormat**, and **FacilityProfile** entities; the `config.json` schema delta; validation rules drawn from FR-001…FR-014.
- `contracts/input-formats.md` — for each of the three formats: detection signature, full column → canonical-field map, date convention, whether it carries a GUID / HRD columns, single- vs multi-facility.
- `contracts/config.md` — the `config.json` contract including the new optional `facilities` registry and the unchanged CLI invocation contract.
- `quickstart.md` — converting a file in each format; setting up the `facilities` registry; what a sparse-resource WARNING looks like; running the four-step validation pipeline.
- Agent context refreshed via `.specify/scripts/bash/update-agent-context.sh claude`.

## Re-evaluation after Phase 1

Constitution Check re-run after the Phase 1 artifacts: still **PASS**. The design
introduces no new runtime dependency, keeps FHIR generation format-agnostic, adds
fixtures + tests, and leaves the output contract (filenames, resources, IG
versions) intact. The single open risk (R1: does the SAFR org profile mandate the
NHSN-system identifier?) is a validation-time confirmation, not a design blocker —
if it fails, the contingency is to keep the placeholder under the NHSN system URI
with a clearly-fake value pattern (e.g. `UNREGISTERED-<slug>`) rather than a
separate system, which still satisfies the user's "don't use the config's OrgID"
constraint.

## Complexity Tracking

No constitution violations requiring justification.
