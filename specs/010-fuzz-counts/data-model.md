# Phase 1 Data Model: Fuzz Counts

**Feature**: 010-fuzz-counts | **Date**: 2026-06-03

This feature introduces no new persisted data and no change to the FHIR resource shape.
It adds one in-memory configuration entity and a transformation over existing fields of the
already-defined normalized row.

---

## Entity: FuzzConfig (new, in-memory)

Holds the run's fuzzing parameters. Created once in `main()` from CLI flags (and optional
config), passed into the per-row generation path.

| Field | Type | Default | Validation | Source |
|-------|------|---------|------------|--------|
| `enabled` | bool | `false` | — | `--fuzz` flag (or `config.fuzz.enabled`) |
| `seed` | str \| int \| None | `None` | If `None` while enabled → derive a random run seed and log WARNING | `--fuzz-seed` (or `config.fuzz.seed`) |
| `magnitude` | float | `0.15` | Must be in `(0, 1]`; reject/clamp otherwise with a clear error | `--fuzz-magnitude` (or `config.fuzz.magnitude`) |
| `small_count_floor` | int | `2` | `>= 1` | Constant default (not exposed in v1 CLI) |

**Lifecycle**: constructed at startup, immutable for the run. When `enabled` is false the
object is inert and the generation path is byte-for-byte identical to today (FR-009/FR-010).

**Invariant**: a `FuzzConfig` with `enabled=false` MUST cause zero change to any output.

---

## Transformation: fuzz_record(record, fuzz_config) (new)

A pure, deterministic function applied **once per normalized row**, before `compute_groups`
and before server upsert. Returns a new record (or mutates a copy) with perturbed count fields;
all non-count fields are passed through untouched.

### Inputs (existing fields of the Normalized Row it perturbs)

| Field group | Keys | Meaning |
|-------------|------|---------|
| Bed occupied | `{area}_occ` for each of the 8 `ALL_BED_AREAS` | beds currently occupied |
| Bed capacity | `{area}_cap` for each of the 8 `ALL_BED_AREAS` | bed capacity |
| ED census | `adult_ed`, `peds_ed` | previous-day ED counts |

All other normalized-row keys (`facility_name`, `facility_guid`, `reporting_date`, `county`,
`created_on`, HRD columns, etc.) are **not** counts and MUST be passed through unchanged (FR-011).

### Per-row PRNG

`rng = Random(f"{fuzz_config.seed}|{stable_facility_key(record)}|{reporting_date}")` — gives
order-independent reproducibility (research D3).

### Per-field rule (research D2)

```
fuzz_value(n):
    if n <= 0:            return 0                      # true zero stays zero
    if n <= small_floor_threshold:                      # tiny counts: absolute jitter
        delta = rng.randint(-small_count_floor, +small_count_floor)
        return max(0, n + (delta or 1))                 # ensure it differs from n
    factor = rng.uniform(1 - magnitude, 1 + magnitude)
    return max(0, round(n * factor))
```

For each area: fuzz `_cap`, then fuzz `_occ`; if the **source** had `occ <= cap`, clamp the
fuzzed `occ` to `<= fuzzed cap` (FR-006). ED fields are fuzzed independently.

### Derived values (unchanged code, automatically consistent)

`compute_groups` recomputes the following from the fuzzed base fields, so no separate fuzzing
is needed and consistency is guaranteed (FR-007):

- Per-area unoccupied = `max(0, fuzzed_cap - fuzzed_occ)`
- `total_ed = adult_ed + peds_ed`
- `AllBeds*`, `AdultTotal*`, `PedsTotal*`, `SpecialtyTotal*` aggregates

---

## Validation Rules (mapped to requirements)

| Rule | Requirement |
|------|-------------|
| Every emitted count is a non-negative integer | FR-005, SC-001 |
| Fuzzed `occ <= cap` whenever source `occ <= cap` | FR-006, SC-001 |
| Aggregates equal the sum of fuzzed component counts | FR-007, SC-001 |
| Non-zero counts generally differ from truth; full true set never reproduced | FR-004, FR-013, SC-002 |
| Fuzzed value within `±magnitude` of truth (outside the small-count floor band) | FR-008, SC-006 |
| `enabled=false` → identical to baseline | FR-009, FR-010, SC-003 |
| Non-count FHIR content unchanged | FR-011 |
| Same seed → identical output; different seed → different | FR-012, SC-005 |

---

## State Transitions

None. `FuzzConfig` is immutable for a run; `fuzz_record` is a stateless pure function of
(record, FuzzConfig). No persistence, no lifecycle beyond the process.
