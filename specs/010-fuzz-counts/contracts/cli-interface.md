# Contract: CLI Interface for Count Fuzzing

**Feature**: 010-fuzz-counts | **Date**: 2026-06-03

The converter's external interface is its command line (`convert.py`). This contract defines
the new flags, their semantics, and the observable behavior the implementation MUST honor.

---

## New CLI flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--fuzz` | boolean (store_true) | off | Enable count fuzzing. When absent, output is identical to current behavior with real counts. |
| `--fuzz-seed` | integer | none | Seed for reproducible fuzzing. Same seed + same input → identical output. If omitted while `--fuzz` is set, a random seed is used and reproducibility is not guaranteed. |
| `--fuzz-magnitude` | float in `(0, 1]` | `0.15` | Maximum proportional perturbation per count (e.g. `0.15` = ±15%). |

All three MUST appear in `--help`. `--fuzz-seed` and `--fuzz-magnitude` have effect only when
`--fuzz` is present (if given without `--fuzz`, they are accepted but inert; the implementation
SHOULD log an informational note).

### Suggested values (MUST be conveyed in `--help`)

There is **no default seed** and no externally meaningful "valid range" for the seed — any
integer works equally well. The help text exists to guide usage, not to constrain values:

- **`--fuzz-seed`** — *Any integer.* For a repeatable demo, pick and record a fixed value
  (e.g. `42`, `12345`); rerunning with it reproduces the same fuzzed numbers. Omit it for
  one-off, non-reproducible output. Help text SHOULD read approximately:
  `"Integer seed for reproducible output (e.g. 42). Any value works; omit for a random, non-reproducible run."`
- **`--fuzz-magnitude`** — *Valid: `(0, 1]`. Suggested: `0.05`–`0.25` (±5%–25%); default `0.15`.*
  Values much above ~`0.30` tend to push counts out of a realistic range and are discouraged.
  Help text SHOULD read approximately:
  `"Max proportional perturbation per count, range (0,1] (default 0.15 = ±15%; suggested 0.05–0.25)."`

These are *guidance only*: the seed is unrestricted, and the magnitude's sole hard rule is the
`(0, 1]` validity check in contract C10. The suggested magnitude band is not enforced — a user
may pass `0.5` if they accept less-realistic output.

### Example invocations

```bash
# Real output (unchanged behavior)
python3 convert.py input/census.csv --config config.json --output-dir output

# Fuzzed, reproducible
python3 convert.py input/census.csv --config config.json --output-dir output \
  --fuzz --fuzz-seed 12345

# Fuzzed, wider spread, non-reproducible
python3 convert.py input/census.csv --config config.json --output-dir output \
  --fuzz --fuzz-magnitude 0.25
```

---

## Optional config parity (config.example.json)

An analogous section MAY be documented; CLI flags take precedence over config values
(same override pattern as `--fhir-server` vs `config.server.base_url`).

```json
"fuzz": {
  "enabled": false,
  "seed": null,
  "magnitude": 0.15
}
```

---

## Behavioral contract (MUST)

| # | Given | When | Then |
|---|-------|------|------|
| C1 | `--fuzz` absent | convert any input | output counts equal true input counts; output matches the existing regression baseline (FR-009, FR-010) |
| C2 | `--fuzz` present | convert | counts in FHIR output differ from true counts (non-zero counts obfuscated); the full set of true counts is never reproduced (FR-004, SC-002) |
| C3 | `--fuzz` present | inspect any count | value is a non-negative integer (FR-005) |
| C4 | `--fuzz` present, source `occ ≤ cap` | inspect a bed area | fuzzed `occupied ≤ fuzzed capacity` (FR-006) |
| C5 | `--fuzz` present | inspect any aggregate group | aggregate equals the sum of the fuzzed component counts (FR-007) |
| C6 | `--fuzz` present | compare to an unfuzzed run | resource types, ids, codes, references, periods, facility/location data, structure all identical; only count values differ (FR-011) |
| C7 | `--fuzz --fuzz-seed S` | convert same input twice | the two outputs are identical (FR-012, SC-005) |
| C8 | `--fuzz --fuzz-seed S1` vs `S2` (S1≠S2) | convert same input | the outputs' counts differ (FR-012, SC-005) |
| C9 | `--fuzz` present | start of run | a WARNING is logged stating fuzzing is active and counts are not real, including magnitude and whether a fixed seed is set (FR-014) |
| C10 | `--fuzz-magnitude` outside `(0, 1]` | start of run | clear error message; the run does not silently proceed with an invalid magnitude |
| C11 | `--fuzz` present, multi-facility/multi-date input | convert | fuzzing applies per (facility, date) row deterministically; row order does not change any row's fuzzed values when a seed is set (FR-012) |
| C12 | `--fuzz` present | run FHIR validation pipeline | zero project-introduced validator errors (same standard as today) (SC-004) |

## Non-goals (explicitly out of contract)

- No marker is embedded in the FHIR output itself (loud logging is the signal; FHIR content
  stays unchanged per C6/FR-011).
- Not a statistical-disclosure-control / formal small-cell-suppression guarantee.
- HRD and any non-bed-capacity counts are out of scope until those measures exist.
