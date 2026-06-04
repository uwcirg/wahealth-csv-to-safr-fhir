# Phase 0 Research: Fuzz Counts

**Feature**: 010-fuzz-counts | **Date**: 2026-06-03

This document resolves the open decisions implied by the spec's Assumptions and the
plan's Technical Context. No external/unknown technologies are involved (stdlib only);
the "research" here is design-decision consolidation grounded in the existing code.

---

## D1. Where to apply the perturbation

**Decision**: Perturb the **normalized in-memory row's base count fields** once per row,
in the format-agnostic path, *before* `compute_groups` and *before* server upsert. The
fields fuzzed are the 8 areas' `{area}_occ` / `{area}_cap` and `adult_ed` / `peds_ed`.

**Rationale**:
- `compute_groups` (`convert.py:239`) derives unoccupied beds (`max(0, cap-occ)`) and all
  eight aggregates *from these base fields*. Perturbing the base fields makes every derived
  group automatically consistent — aggregates equal the sum of fuzzed parts, and the
  occupied/unoccupied/capacity relationships hold — satisfying FR-006 and FR-007 with no
  extra reconciliation logic.
- The server-persistence path (`upsert_measure_report`, `convert.py:925`) reads the same
  `record`. Fuzzing the record once means local files and server submissions carry the
  identical fuzzed values — no second code path to keep in sync.
- It honors FR-001/FR-002: input is consumed/normalized exactly as today; perturbation is a
  distinct step during FHIR generation, downstream of parsing and format detection
  (Multi-Format CSV Input principle stays satisfied — generation remains format-agnostic).

**Alternatives considered**:
- *Fuzz the output group counts in `build_group`/`compute_groups` output*: rejected —
  would require recomputing aggregates from already-fuzzed parts (or fuzzing aggregates
  independently and risking internal contradictions). Far more code to keep consistent.
- *Fuzz during CSV parsing in `csv_formats.py`*: rejected — violates "consume input as we
  do today" and would push perturbation into the format layer, breaking format-agnosticism.

---

## D2. Perturbation algorithm

**Decision**: For each base count `n`, draw a multiplicative jitter uniformly from
`[1 - m, 1 + m]` where `m` is the magnitude (default `0.15`), compute
`fuzzed = round(n * factor)`, then apply a **small-count floor**: if `n > 0` the result is
nudged so it differs from `n` and is meaningfully obfuscated (for tiny `n` like 1–3, draw a
small absolute delta in `[-k, +k]`, default `k = 2`, instead of a percentage that rounds
back to `n`). Clamp every result to `>= 0`.

Capacity is fuzzed first; occupied is fuzzed independently, then — **only when the source
row had `occ <= cap`** — the fuzzed occupied is clamped to `<= fuzzed capacity` so the
realism rule (FR-006) is preserved without "fixing" pre-existing source anomalies the
constitution says to tolerate (Data Integrity: occupied-over-capacity is a real-world case).

**Rationale**:
- Multiplicative jitter keeps perturbation *proportional* — large facilities move by tens of
  beds, small units by a bed or two — which is what "still realistic for a hospital of that
  size" (FR-008, SC-006) requires. A flat absolute noise would distort small units or barely
  touch large ones.
- The small-count floor addresses the edge case "very small counts must still be obfuscated"
  (spec Edge Cases, FR-013) — a ±15% on `n=2` rounds back to `2` and leaks the true value.
- Clamping occupied to fuzzed capacity only when the source was consistent avoids both
  impossible output and rewriting genuine source data-quality signals.

**Alternatives considered**:
- *Additive Gaussian noise*: rejected for runtime simplicity and because tuning a stddev per
  magnitude band is fiddlier than a bounded uniform factor; uniform is easy to reason about
  and bound-check in tests.
- *Always force a change even when `n = 0`*: rejected — a true 0 (empty pediatric unit) must
  stay realistic for an empty unit (spec Edge Cases); 0 stays 0.

---

## D3. Reproducibility / seeding

**Decision**: Use stdlib `random.Random` seeded **per row** from a deterministic combination
of the user seed and the row's stable identity, e.g.
`Random(f"{seed}|{stable_facility_key(record)}|{reporting_date}")`. Each row's count fields
are then drawn from that per-row PRNG in a fixed field order.

**Rationale**:
- Guarantees FR-012 / SC-005: same input + same seed → identical fuzzed counts, **independent
  of row processing order** or how many rows are in the file. A single global PRNG would make a
  row's values depend on how many rows preceded it, so re-running a single-facility subset
  would not reproduce the multi-facility run's values.
- `stable_facility_key` already exists (`convert.py:209`) and yields a deterministic per-facility
  key (GUID or slugified name), so no new identity concept is introduced.
- `random` is stdlib → Zero-Dependency Runtime preserved.

**Alternatives considered**:
- *Global single seed, sequential draws*: rejected — order-dependent, not reproducible across
  subsets.
- *Hashing each value with the seed deterministically (no PRNG object)*: viable but more code;
  the per-row `Random` is simpler and clearly bounded.

**Seed-absent behavior**: When fuzzing is enabled but no seed is given, derive a
non-reproducible seed at startup (e.g., from `os.urandom`, not `Math.random`/time which the
constitution-bound code already avoids elsewhere) so each run differs. Log the absence of a
fixed seed at WARNING so the user knows output is not reproducible.

---

## D4. Configuration surface

**Decision**: Expose three CLI flags on `convert.py`, mirroring the existing operational flags:
- `--fuzz` (store_true) — enable fuzzing (default off).
- `--fuzz-seed N` — integer/string seed for reproducible output (optional).
- `--fuzz-magnitude M` — float in `(0, 1]`, default `0.15` (±15%).

Optionally document an analogous `"fuzz"` section in `config.example.json` for parity, with the
CLI flag taking precedence (same override pattern as `--fhir-server` over `config.server.base_url`).

**Rationale**:
- Fuzzing is a per-run operational mode (like `--bundles-mrs-only`), not hospital-specific data,
  so a CLI flag is the natural home and keeps the decision visible in the command invocation.
- Honors Configuration-over-Code: nothing is hardcoded; defaults live in one place.

**Alternatives considered**:
- *Config-file only*: rejected — a config toggle is easier to leave on accidentally for a real
  submission; a CLI flag must be typed each run, reinforcing opt-in safety.
- *Environment variable*: rejected — less discoverable than `--help`-surfaced flags.

---

## D5. Making fuzzing loud (Data Integrity reconciliation)

**Decision**: When fuzzing is active, log a prominent **WARNING** at startup (e.g., "COUNT
FUZZING ENABLED — output counts are obfuscated and NOT real; do not submit as authentic data")
including the magnitude and whether a fixed seed is set. Per-row data-quality logging is
unchanged.

**Rationale**: Directly satisfies FR-014 and reconciles the Data Integrity principle — the
output is *intentionally* altered, so it must never be *silent*. Opt-in + WARNING means fuzzed
data cannot be mistaken for real.

**Alternatives considered**: *Embed a marker in the FHIR output itself* — rejected for v1
because FR-011 requires non-count FHIR content to be unchanged (a marker extension/tag could
affect conformance and defeats the "looks real" goal). Loud logging is the chosen signal.

---

## D6. Testing approach

**Decision**: Add `tests/test_fuzz.py` (pytest) covering, against a representative record:
1. **Disabled = identity** — fuzzing off yields the exact input counts (FR-009/FR-010, SC-003).
2. **Non-negativity & integer** — all fuzzed fields are non-negative ints (FR-005, SC-001).
3. **Occupied ≤ capacity preserved** — when source `occ ≤ cap`, fuzzed `occ ≤ cap` (FR-006).
4. **Aggregate consistency** — recomputed aggregates equal the sum of fuzzed parts (FR-007);
   reuse the existing aggregate assertions in `test_compute.py` against a fuzzed record.
5. **Determinism** — same seed → identical output; different seed → different output (FR-012, SC-005).
6. **Magnitude bound** — non-floor fuzzed values stay within `±m` (plus floor allowance) of truth (FR-008).
7. **Edge cases** — `n = 0` stays 0; small `n` (1–3) is obfuscated (FR-013, spec Edge Cases).

Then run the full end-to-end validator pipeline (constitution LLM Validation) **with fuzzing on**
to confirm FHIR conformance is unaffected (SC-004), and confirm the disabled run still matches the
regression baseline.

**Rationale**: Combines unit tests for computation correctness (constitution's "targeted unit
tests for computation logic") with the authoritative end-to-end conformance pass.

---

## Resolved unknowns

All Technical Context items are concrete; no `NEEDS CLARIFICATION` remains. Magnitude default
(`0.15`), small-count floor (`±2`), seeding strategy (per-row `Random`), and config surface
(CLI flags) are fixed above and are tunable defaults, not external hard requirements.
