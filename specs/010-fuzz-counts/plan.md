# Implementation Plan: Fuzz Counts for Realistic but Non-Real Data

**Branch**: `010-fuzz-counts` | **Date**: 2026-06-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-fuzz-counts/spec.md`

## Summary

Add an **opt-in** mode that perturbs ("fuzzes") the count values emitted into the
FHIR output so they are no longer the facilities' real numbers but remain plausible
for a hospital of that size. Input is consumed exactly as today; fuzzing is applied
to the **normalized in-memory row** (the `{area}_occ` / `{area}_cap` and `adult_ed` /
`peds_ed` count fields) once per row, in the format-agnostic path, *before* group
computation. Because `compute_groups` derives unoccupied beds and all eight aggregates
from those base fields — and the server-upsert path reads the same record — perturbing
the base fields preserves every realism invariant for free (non-negativity, occupied ≤
capacity, aggregate = sum of fuzzed parts) and applies identically to local files and
server persistence. Reproducibility comes from a user-supplied seed combined
deterministically with each row's stable identity, so the same input + seed yields
identical output regardless of row order. The feature is off by default; when active it
logs loudly at WARNING so fuzzed output is never mistaken for real data.

## Technical Context

**Language/Version**: Python 3 (standard library only at runtime)
**Primary Dependencies**: None at runtime. Stdlib `random` (seedable PRNG), `argparse`, `logging`. Dev: `pytest`, `ruff`, `validator_cli.jar`, `gitleaks`
**Storage**: Filesystem — CSV input, JSON output, JSON config (unchanged)
**Testing**: `pytest` unit tests for fuzz invariants + determinism; end-to-end HL7 FHIR Reference Validator conformance pass (per constitution)
**Target Platform**: Python 3 on locked-down hospital data-manager workstations
**Project Type**: Single-file CLI utility (`convert.py` at repo root, ~941 lines)
**Performance Goals**: Negligible overhead; per-row O(number of count fields), no measurable slowdown on the ~100-row fixtures
**Constraints**: Zero runtime dependencies; deterministic output given a seed; must not alter any non-count FHIR content; disabled-mode output byte-identical to current baseline
**Scale/Scope**: ~10 base count fields per row (8 areas × occ/cap is 16, plus 2 ED), driving 25 MeasureReport groups; files of a few to ~100 rows

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Impact | Verdict |
|-----------|--------|---------|
| **Zero-Dependency Runtime** | Uses only stdlib `random` for seeded perturbation. | ✅ Pass |
| **FHIR Profile Conformance** | Counts remain non-negative integers in the same group/population structure; no profile, code, reference, or period changes. Output must pass the validator with zero project-introduced errors. | ✅ Pass (verified in Phase 1 validation) |
| **Validation-Driven Testing** | Add targeted unit tests for the fuzz computation (invariants + determinism + disabled-identity); run the full end-to-end validator pipeline with fuzzing on. Existing fixtures suffice — fuzzing is opt-in, so the default validation path is unchanged. | ✅ Pass |
| **Multi-Format CSV Input** | Fuzzing operates on the normalized row *after* format detection/parsing; the FHIR generation path stays format-agnostic and is not branched on input format. | ✅ Pass |
| **Data Integrity & Defensive Transformation** | This principle says "never produce silently incorrect output." Fuzzing *intentionally* produces non-real output — a deliberate tension. Resolved (not violated) by: (a) opt-in default off, (b) loud WARNING logging whenever active (FR-014), (c) preserving all defensive invariants (clamping, aggregate-from-raw). Documented as a deliberate, flagged behavior per Governance §Compliance. | ✅ Pass (documented exception) |
| **Scope — Bed Capacity & HRD** | No new measure domain; only perturbs existing bed-capacity/ED counts. | ✅ Pass |
| **Configuration over Code** | Fuzz parameters (enable, seed, magnitude) are runtime operational choices supplied via CLI flags (mirroring `--bundles-mrs-only` / `--fhir-server`), not hardcoded. | ✅ Pass |
| **Clear, Predictable Output** | Deterministic given a seed; output structure and naming unchanged. | ✅ Pass |
| **Single-File Simplicity** | `convert.py` is 941 lines; fuzz logic (~40–60 lines) keeps it under the 1000-line split threshold, so it stays in `convert.py`. | ✅ Pass |
| **README as Living Documentation** | New CLI flags and the fuzz behavior must be documented in `README.md` in the same PR. | ✅ Pass (task in Phase 2) |

**Result**: No violations. The Data Integrity tension is an intentional, opt-in, loudly-logged behavior, documented here per the constitution's Compliance clause. Complexity Tracking table not required.

## Project Structure

### Documentation (this feature)

```text
specs/010-fuzz-counts/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── cli-interface.md  # CLI flags + fuzz-config contract
└── checklists/
    └── requirements.md  # Spec quality checklist (already created)
```

### Source Code (repository root)

```text
convert.py               # Single entry point. Add: CLI flags (--fuzz, --fuzz-seed,
                         #   --fuzz-magnitude), a FuzzConfig holder, a fuzz_record()
                         #   step invoked per row before build_bundle/compute_groups,
                         #   and a WARNING log when fuzzing is active.
csv_formats.py           # Unchanged — fuzzing happens after normalization.
config.example.json      # Optional: document an analogous "fuzz" config section.
README.md                # Document the new flags and the fuzz behavior/warning.

tests/
├── test_compute.py      # Existing aggregate/clamping tests (unchanged baseline).
└── test_fuzz.py         # NEW: invariants (non-negative, occ ≤ cap, aggregate = sum
                         #   of fuzzed parts), determinism (same seed → same output;
                         #   different seed → different), disabled = identity,
                         #   magnitude bounds, zero/small-count edge cases.
```

**Structure Decision**: Single-project, single-entry-point CLI. All runtime changes
land in `convert.py`; tests in `tests/test_fuzz.py`. No new runtime module is created
(constitution's single-file rule — `convert.py` stays under 1000 lines). The fuzz step
is inserted in the format-agnostic path so it is independent of input format.

## Complexity Tracking

> No constitution violations — table intentionally omitted.
