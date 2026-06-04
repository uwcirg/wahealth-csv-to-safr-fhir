# Quickstart: Count Fuzzing

**Feature**: 010-fuzz-counts | **Date**: 2026-06-03

Fuzzing replaces the real bed-occupancy / capacity / ED counts in the FHIR output with
**plausible but fake** numbers, so you can share or demo output without exposing a facility's
true operational data. It is **off by default** — you must opt in with `--fuzz`.

> ⚠️ Fuzzed output is **not real data**. When fuzzing is on, the converter logs a loud WARNING.
> Never submit fuzzed output as an authentic report.

## Generate fuzzed output (reproducible)

```bash
python3 convert.py input/census_20260511.FromKC.SubsetObfsctd.csv \
  --config config.example.json --output-dir output \
  --fuzz --fuzz-seed 12345
```

Re-running the exact command produces the **same** fuzzed counts (good for stable demos,
screenshots, and tests).

## Generate fuzzed output (non-reproducible, wider spread)

```bash
python3 convert.py input/census_20260511.FromKC.SubsetObfsctd.csv \
  --config config.example.json --output-dir output \
  --fuzz --fuzz-magnitude 0.25
```

`--fuzz-magnitude 0.25` perturbs each count by up to ±25% (default is ±15%).

## Real output (default — unchanged)

```bash
python3 convert.py input/census_20260511.FromKC.SubsetObfsctd.csv \
  --config config.example.json --output-dir output
```

Without `--fuzz`, output carries the true counts and is identical to prior releases.

---

## What fuzzing guarantees

- Counts differ from the real numbers, but stay realistic for a hospital of that size.
- Every count is a non-negative integer.
- Occupied never exceeds capacity (when the source data was consistent).
- Aggregates (all beds, adult/peds/specialty totals, total ED) still equal the sum of their
  fuzzed parts — no contradictory numbers.
- Only count values change; resource structure, codes, references, dates, and facility data are
  untouched.

## Verify it works

1. **Disabled = baseline**: run without `--fuzz` and confirm output matches the regression
   baseline (no differences).
2. **Enabled changes counts**: run with `--fuzz --fuzz-seed 1` and diff a `MeasureReport.json`
   against the unfuzzed run — only `count` fields should differ.
3. **Reproducible**: run the seeded command twice; the two outputs are identical.
4. **Conformance**: run the FHIR validation pipeline (see `CLAUDE.md` / CI) on the fuzzed
   output — zero project-introduced errors.

## Unit tests

```bash
cd /home/debadmin/uwcirg_misc-repos/wahealth-csv-to-safr-fhir
pytest tests/test_fuzz.py
```

Covers: disabled-identity, non-negativity, occupied ≤ capacity, aggregate consistency,
determinism (same/different seed), magnitude bounds, and zero/small-count edge cases.
