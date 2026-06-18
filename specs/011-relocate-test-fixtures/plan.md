# Implementation Plan: Relocate test fixtures to test/input and route their output to test/output

**Branch**: `011-relocate-test-fixtures` | **Date**: 2026-06-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-relocate-test-fixtures/spec.md`

## Summary

Bring the repository into compliance with Constitution v1.8.0's amended "Validation-Driven
Testing" principle: relocate the canonical regression CSV fixtures from `input/` to
`test/input/`, and route the FHIR they generate to `test/output/` (mirroring the production
`output/` layout) so test artifacts never mix with production output. The change is a
history-preserving file move plus reference updates in CI (`.github/workflows/ci.yml`),
`CLAUDE.md`, `.gitignore`, and `README.md` where it names the fixture/test paths. The
converter's code and its default production output location (`./output`) are unchanged — the
`test/output/` routing is achieved purely by passing `--output-dir test/output` when running
the fixtures.

## Technical Context

**Language/Version**: Python 3 (stdlib only at runtime) — unchanged; no source code edits to `convert.py`
**Primary Dependencies**: None at runtime. Dev/CI: `ruff`, `validator_cli.jar` (HL7 FHIR validator), `gitleaks`
**Storage**: Filesystem — CSV input fixtures, generated JSON output
**Testing**: End-to-end FHIR conformance validation (the four-step pipeline) + `unittest` in `tests/`
**Target Platform**: Linux (CI: ubuntu-latest); developer/data-manager workstations
**Project Type**: Single-file CLI converter (single project)
**Performance Goals**: N/A — no runtime behavior change; relocation is build/test tooling only
**Constraints**: Preserve git history on moved files; zero project-introduced FHIR validation errors must be maintained; no new runtime dependencies
**Scale/Scope**: 4 fixture files relocated; 4 reference sites updated (CI workflow, CLAUDE.md, .gitignore, README.md)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

This feature is itself a constitution-compliance change (conforms to v1.8.0). Relevant gates:

- **Zero-Dependency Runtime** — ✅ No runtime code change; no dependencies added. PASS.
- **FHIR Profile Conformance** — ✅ Output content is byte-identical (only its root directory
  moves); validation still runs against both IGs. PASS.
- **Validation-Driven Testing** — ✅ This change *implements* the amended principle: fixtures
  in `test/input/`, output in `test/output/`, validator run over `test/output/`. Every
  supported format keeps its canonical fixture; `*column-labels-only*` stays excluded. PASS.
- **Multi-Format CSV Input** — ✅ All format fixtures move together; detection/parsing
  untouched. PASS.
- **Clear, Predictable Output** — ✅ Output layout is preserved exactly, only re-rooted under
  `test/output/` for test runs; production default `./output` unchanged. PASS.
- **CI Pipeline** — ✅ CI is updated in the same change; it remains subject to (and now
  matches) the constitution. PASS.
- **README as Living Documentation** — ✅ README updated wherever it names the fixture/test
  paths, in the same PR. PASS.
- **Single-File Simplicity** — ✅ No new modules; `convert.py` untouched. PASS.
- **Configuration over Code / Secret Protection** — ✅ Not affected; `.gitignore` continues to
  ignore generated output (now also `test/output/`). PASS.

No violations. Complexity Tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/011-relocate-test-fixtures/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── checklists/
│   └── requirements.md  # Spec quality checklist (/speckit.specify)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

No `contracts/` directory: this feature changes no external interface. The converter's CLI
contract (`--output-dir`, positional CSV path) is unchanged; only the *values* passed when
running the regression fixtures change, plus where the fixtures physically live.

### Source Code (repository root)

```text
test/
├── input/                 # NEW — relocated canonical regression fixtures (was input/)
│   ├── 2025.10.21.Test.Facility.BedCapacity.csv
│   ├── 2025.10.21.Test.Facility.BedCapacity.column-labels-only.csv
│   ├── 2026.04.30.Test.Facility.WAHealthDict.csv
│   └── census_20260511.FromKC.SubsetObfsctd.csv
└── output/                # NEW — generated FHIR from fixtures (git-ignored, created at run time)

input/                     # REMOVED after relocation (no fixtures remain)
output/                    # UNCHANGED — production default output dir (git-ignored)

convert.py                 # UNCHANGED — default --output-dir stays ./output
csv_formats.py             # UNCHANGED
tests/                     # UNCHANGED — Python unittest suite
.github/workflows/ci.yml   # EDIT — fixture loop reads test/input/, writes/validates test/output/
.gitignore                 # EDIT — add test/output/ alongside output/
CLAUDE.md                  # EDIT — LLM validation pipeline uses test/input/ + test/output/
README.md                  # EDIT (conditional) — any fixture/test-path references
```

**Structure Decision**: Single-project CLI. The only structural change is the introduction of
the `test/` directory holding `input/` (fixtures, version-controlled) and `output/` (generated,
git-ignored). The converter, its CLI surface, and the production `output/` directory are
untouched; everything else is reference updates in tooling and documentation.

## Complexity Tracking

No constitution violations — section intentionally empty.
