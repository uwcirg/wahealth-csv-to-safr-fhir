# Phase 1 Data Model: Relocate test fixtures

This feature has no application data model — it is a filesystem/tooling relocation. The
"entities" are directories, files, and the reference sites that point at them.

## Entities

### Regression fixture set

The canonical CSV files that exercise the converter, one per supported input format plus a
header-only reference. Relocating from `input/` → `test/input/`.

| File | Role | Converted by pipeline? |
|------|------|------------------------|
| `2025.10.21.Test.Facility.BedCapacity.csv` | Original WA Health format fixture | Yes |
| `2026.04.30.Test.Facility.WAHealthDict.csv` | "2026-04-30 WA Health dictionary from KC" fixture | Yes |
| `census_20260511.FromKC.SubsetObfsctd.csv` | "KC multi-hospital from MFT 2026-05-11" fixture | Yes |
| `2025.10.21.Test.Facility.BedCapacity.column-labels-only.csv` | Header-only column reference | No (excluded via `*column-labels-only*`) |

- **Source location (before)**: `input/`
- **Target location (after)**: `test/input/`
- **Invariant**: After the move, none of these remain in `input/` (FR-002).
- **Version control**: tracked; moved with `git mv` to preserve history (FR-001).

### Test output tree

Generated FHIR artifacts produced from the regression fixtures.

- **Location**: `test/output/`
- **Structure**: identical to production `output/` — `{root}/{date}/{facility}.{date}.BedCapacity.json`
  for Bundles and `{root}/{date}/{facility}/` for per-facility individual resources.
- **Lifecycle**: created on demand by each converter run; regenerated, never hand-edited.
- **Version control**: git-ignored (FR-008).

### Production output tree (unchanged)

- **Location**: `output/` (the converter's default `--output-dir ./output`)
- **State**: unchanged by this feature; remains git-ignored and is what production runs use.

## Reference sites (must be consistent after the change)

| Site | Current reference | Target reference |
|------|-------------------|------------------|
| `.github/workflows/ci.yml` (convert step) | loops `input/*.csv`, `--output-dir output` | loops `test/input/*.csv`, `--output-dir test/output` |
| `.github/workflows/ci.yml` (validate step) | `find output -name '*.json'` | `find test/output -name '*.json'` |
| `CLAUDE.md` (LLM Validation Pipeline) | `input/`, `--output-dir output`, `find output` | `test/input/`, `--output-dir test/output`, `find test/output` |
| `.gitignore` | `output/` | add `test/output/` |
| `README.md` | fixture/test-path references (if any) | `test/input/` / `test/output/` (production examples untouched) |

## Consistency rule

After implementation, no maintained tooling or documentation may name `input/` as the
regression-fixture source (FR-010). A repository-wide search for the old path is the
acceptance check (SC-005).
