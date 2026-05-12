# Implementation Plan: Per-Facility Output Layout and Bundles-MRs-Only Mode

**Branch**: `009-per-facility-output-layout` | **Date**: 2026-05-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-per-facility-output-layout/spec.md`

## Summary

Bring the converter's local output into line with constitution v1.7.0's revised *Clear, Predictable
Output* principle: write each row's standalone resource files (`Organization.json`, `Device.json`,
`MeasureReport.json`, `Location.json`) into a per-facility subdirectory
`output/{YYYY-MM-DD}/{facility_name}/` instead of directly in the date directory, so multi-facility
input files no longer overwrite one facility's individual resources with another's; and add an
opt-in `--bundles-mrs-only` flag that limits local output to the Bundle file(s) and
`MeasureReport.json`, skipping the rarely-changing Organization/Device/Location files. Update the
write loop and `argparse` setup in `convert.py`, refresh the README "Output" section, and add tests.

## Technical Context

**Language/Version**: Python 3 (stdlib only at runtime)  
**Primary Dependencies**: None at runtime. Dev: `ruff`, `pytest`, `validator_cli.jar`, `gitleaks`  
**Storage**: Filesystem — CSV input, JSON output, JSON config  
**Testing**: `pytest` (`tests/`)  
**Target Platform**: Linux / cross-platform CLI  
**Project Type**: Single-file CLI tool (`convert.py` + `csv_formats.py`)  
**Performance Goals**: N/A — bounded by CSV row count (tens to low thousands of rows)  
**Constraints**: Stdlib-only at runtime; deterministic, human-readable output; FHIR validation must
pass with zero project-introduced errors  
**Scale/Scope**: Small change confined to `convert.py` `main()` write loop + `argparse`, plus README
and tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Stdlib-only runtime | ✅ PASS | Uses `os.path` / `os.makedirs` / `argparse` only |
| Validation-Driven Testing | ✅ PASS | Tests added for new layout + flag; full FHIR validation pipeline (CLAUDE.md) re-run, invoking the validator via `find output -name '*.json'` so the new 3-level per-facility files are covered (a 2-level `output/**/*.json` glob would miss them); existing per-format fixtures unchanged |
| Clear, Predictable Output | ✅ PASS | This feature *implements* the revised rule: per-facility subdirectory + `--bundles-mrs-only` flag, both documented in README and `--help` |
| Scope — Bed Capacity & HRD Surveillance | ✅ PASS | No measure-domain change; only file layout / CLI |
| Multi-Format CSV Input | ✅ PASS | Format detection and internal row model untouched |
| Configuration over Code | ✅ PASS | New behavior is a runtime flag, not hard-coded |
| Simplicity | ✅ PASS | No new module; changes localized to `main()` |

No violations — Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/009-per-facility-output-layout/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── cli.md           # CLI contract (flags, output layout)
├── checklists/
│   └── requirements.md  # Spec quality checklist (already created by /speckit.specify)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
convert.py               # MODIFIED: argparse adds --bundles-mrs-only; write loop creates
                         #   output/{date}/{facility_name}/ and gates individual-resource writes
csv_formats.py           # unchanged
README.md                # MODIFIED: "Output" section + options table describe new layout + flag
tests/
├── test_compute.py      # unchanged
├── test_formats.py      # unchanged
└── test_output_layout.py  # NEW: per-facility subdir layout + --bundles-mrs-only behavior
input/                   # existing canonical fixtures (incl. a multi-facility one) — reused
output/                  # generated; not committed
```

**Structure Decision**: Single-project CLI. The feature is a localized change to `convert.py`'s
`main()` (the post-`build_bundle` write loop and the `argparse` setup) plus README text and a new
test module. No new source modules; `sanitize_filename` is reused unchanged for the subdirectory
name so the directory name and the Bundle filename's `{facility_name}` segment are always identical.

## Complexity Tracking

> No constitution violations — section intentionally empty.
