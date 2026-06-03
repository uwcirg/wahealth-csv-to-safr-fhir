---
description: "Task list for 010-fuzz-counts implementation"
---

# Tasks: Fuzz Counts for Realistic but Non-Real Data

**Input**: Design documents from `/specs/010-fuzz-counts/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-interface.md, quickstart.md

**Tests**: INCLUDED. The project constitution (Validation-Driven Testing) mandates targeted
unit tests for computation logic, and the design specifies `tests/test_fuzz.py`. Test tasks
are written before the implementation they cover.

**Organization**: Tasks are grouped by user story. All runtime changes land in the single
entry point `convert.py` (constitution: Single-File Simplicity — file stays under 1000 lines).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files / independent edits, no dependencies)
- **[Story]**: US1, US2, US3 — maps to spec.md user stories
- Single project: `convert.py` and `tests/` at repository root

## Path Conventions

- Runtime code: `convert.py` (repo root)
- Tests: `tests/test_fuzz.py` (repo root)
- Docs/config: `README.md`, `config.example.json` (repo root)

⚠️ **Shared-file note**: Most implementation tasks edit `convert.py`. Tasks that touch the
same function are sequential (no `[P]`). Test tasks edit `tests/test_fuzz.py` and are `[P]`
relative to `convert.py` work but sequential relative to each other (same file).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test scaffolding shared by all stories

- [X] T001 Create `tests/test_fuzz.py` with a reusable sample normalized-row fixture (all 8 `ALL_BED_AREAS` `{area}_occ`/`{area}_cap` keys plus `adult_ed`/`peds_ed`, a `facility_name`, and a `reporting_date`) and pytest scaffolding that imports the fuzz helpers from `convert.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: CLI surface, config holder, and the per-row call site that every story builds on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Add a `FuzzConfig` holder (fields: `enabled` bool, `seed`, `magnitude` float=0.15, `small_count_floor` int=2) near the top of `convert.py`
- [X] T003 Add `--fuzz` (store_true), `--fuzz-seed` (int, no default), and `--fuzz-magnitude` (float, default 0.15) argparse flags in `main()` in `convert.py`, surfaced in `--help`. Help text MUST convey suggested usage: `--fuzz-seed` is any integer (e.g. 42; omit for a random non-reproducible run) and `--fuzz-magnitude` is range `(0,1]`, default 0.15, suggested 0.05–0.25 (per `contracts/cli-interface.md` "Suggested values")
- [X] T004 Validate `--fuzz-magnitude` is within `(0, 1]` in `main()` in `convert.py`; exit with a clear error message if out of range (contract C10)
- [X] T005 Construct a `FuzzConfig` from parsed args in `main()` in `convert.py` (CLI flags are the source of truth for v1; config-file parity is documentation-only — see T024)
- [X] T006 Add a `fuzz_record(record, fuzz_config)` function to `convert.py` that initially returns the record unchanged, and call it per row in the records loop in `main()` immediately before `build_bundle(...)` so both local-file and server-upsert paths consume the same (eventually fuzzed) record

**Checkpoint**: Flags parse, `FuzzConfig` is built, and the per-row hook is wired (still a no-op). Existing output is unchanged.

---

## Phase 3: User Story 1 - Produce shareable output with obfuscated counts (Priority: P1) 🎯 MVP

**Goal**: With `--fuzz`, counts in the FHIR output are perturbed away from the true values yet
stay realistic (non-negative, occupied ≤ capacity, aggregates = sum of fuzzed parts), and the
run loudly announces that the data is not real.

**Independent Test**: Run `convert.py … --fuzz --fuzz-seed 1`, diff a generated `MeasureReport.json`
against an unfuzzed run — only `count` fields differ, every count satisfies the realism invariants,
and the FHIR validator reports zero project-introduced errors.

### Tests for User Story 1

- [X] T007 [US1] Add test: every fuzzed count field is a non-negative `int` (FR-005) in `tests/test_fuzz.py`
- [X] T008 [US1] Add test: when source `occ ≤ cap`, fuzzed `occ ≤ cap` for each bed area (FR-006) in `tests/test_fuzz.py`
- [X] T009 [US1] Add test: `compute_groups` aggregates (AllBeds/Adult/Peds/Specialty/Total ED) equal the sum of the fuzzed component counts (FR-007) in `tests/test_fuzz.py`
- [X] T010 [US1] Add test: non-zero counts are obfuscated (differ from truth) and the full true set is not reproduced (FR-004, SC-002) in `tests/test_fuzz.py`
- [X] T011 [US1] Add test: non-floor fuzzed values stay within `±magnitude` of truth; `n=0` stays `0`; small `n` (1–3) is changed (FR-008, FR-013) in `tests/test_fuzz.py`

### Implementation for User Story 1

- [X] T012 [US1] In `fuzz_record` in `convert.py`, build a per-row PRNG `Random(f"{seed}|{stable_facility_key(record)}|{record['reporting_date']}")` for order-independent draws
- [X] T013 [US1] In `fuzz_record` in `convert.py`, implement the per-field rule: `n<=0 → 0`; tiny `n` → bounded absolute jitter via `small_count_floor` ensuring it differs from `n`; otherwise `round(n * uniform(1-m, 1+m))`; clamp all results to `>= 0`
- [X] T014 [US1] In `fuzz_record` in `convert.py`, fuzz each area's `_cap` then `_occ`, and clamp fuzzed `_occ ≤` fuzzed `_cap` only when the source row had `occ ≤ cap`; fuzz `adult_ed`/`peds_ed` independently; leave all non-count keys untouched (FR-011)
- [X] T015 [US1] In `main()` in `convert.py`, log a prominent WARNING when `fuzz_config.enabled` ("COUNT FUZZING ENABLED — counts are not real; do not submit as authentic data"), including magnitude and whether a fixed seed is set (FR-014, contract C9)
- [X] T016 [US1] Run the end-to-end FHIR validation pipeline (per `CLAUDE.md`) on output generated **with `--fuzz`**; confirm zero project-introduced errors (SC-004, contract C12)

**Checkpoint**: Fuzzing produces realistic, obfuscated, conformant FHIR output. MVP delivered.

---

## Phase 4: User Story 2 - Preserve true-data behavior by default (Priority: P1)

**Goal**: With fuzzing off (the default), output is byte-for-byte identical to today's real-count
output, so fuzzed data can never leak into a real submission.

**Independent Test**: Run `convert.py` without `--fuzz` and confirm the output matches the existing
regression baseline with zero differences.

### Tests for User Story 2

- [X] T017 [US2] Add test: a `FuzzConfig` with `enabled=False` makes `fuzz_record` return counts identical to the input record (FR-009) in `tests/test_fuzz.py`

### Implementation for User Story 2

- [X] T018 [US2] In `fuzz_record` in `convert.py`, short-circuit to return the record unchanged when `fuzz_config.enabled` is `False` (no PRNG, no mutation) — confirms the default path is inert
- [X] T019 [US2] Generate output without `--fuzz` and diff against the existing regression baseline (e.g. `specs/008-multi-format-csv-input/regression-baseline.json`); confirm zero differences (FR-010, SC-003)

**Checkpoint**: Default runs are provably unchanged; fuzzing is strictly opt-in.

---

## Phase 5: User Story 3 - Reproducible fuzzing for repeatable demos (Priority: P2)

**Goal**: The same input plus the same seed yields identical fuzzed counts (order-independent);
different seeds yield different counts; omitting a seed gives non-reproducible output with a warning.

**Independent Test**: Run the seeded command twice and confirm identical output; run with a different
seed and confirm the counts differ.

### Tests for User Story 3

- [X] T020 [US3] Add test: same seed → identical fuzzed counts across two `fuzz_record` calls; different seed → different counts (FR-012, SC-005) in `tests/test_fuzz.py`
- [X] T021 [US3] Add test: row order independence — a row fuzzed alone reproduces the same counts it gets within a multi-row batch under the same seed (contract C11) in `tests/test_fuzz.py`

### Implementation for User Story 3

- [X] T022 [US3] In `main()`/`FuzzConfig` in `convert.py`, when `--fuzz` is set without `--fuzz-seed`, derive a non-reproducible seed (`os.urandom`-based) and log a WARNING that output is not reproducible (research D3)

**Checkpoint**: Seeded runs are reproducible; all three user stories function independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, config parity, lint, and full conformance per the constitution

- [X] T023 [P] Document `--fuzz`, `--fuzz-seed`, `--fuzz-magnitude`, and the "not real data" warning in `README.md` (options table + a fuzzing section) — constitution: README as Living Documentation
- [X] T024 [P] Add an optional `"fuzz": { "enabled": false, "seed": null, "magnitude": 0.15 }` section to `config.example.json` documenting CLI-precedence parity (contract: config parity)
- [X] T025 [P] Run `ruff check .` and fix any lint issues introduced in `convert.py` / `tests/test_fuzz.py`
- [X] T026 Run the full LLM validation pipeline per `CLAUDE.md` over **all** `input/` fixtures both without `--fuzz` (baseline) and with `--fuzz --fuzz-seed <n>`; confirm zero project-introduced validator errors in both modes
- [X] T027 Execute the `quickstart.md` verification steps (disabled=baseline, enabled-changes-counts, reproducible, conformance) and confirm each passes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1 / T001)**: No dependencies — start immediately.
- **Foundational (Phase 2 / T002–T006)**: Depends on Setup. **BLOCKS all user stories.** T002→T003→T004→T005 are sequential (same `main()` region); T006 after T002.
- **User Story 1 (Phase 3)**: Depends on Foundational. The MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational (T006's call site + T018's short-circuit). Independently testable; does not depend on US1.
- **User Story 3 (Phase 5)**: Depends on Foundational and reuses US1's per-row PRNG (T012); land after US1. Independently testable.
- **Polish (Phase 6)**: After all desired stories complete.

### User Story Dependencies

- **US1 (P1)** — only Foundational. Delivers obfuscation + realism (MVP).
- **US2 (P1)** — only Foundational. Delivers opt-in/disabled-identity guarantee. Independent of US1.
- **US3 (P2)** — Foundational + US1's seeding plumbing. Adds reproducibility guarantees.

### Within Each User Story

- Tests are written before the implementation they cover and should fail first.
- In `convert.py`, the perturbation tasks T012→T013→T014 are sequential (same `fuzz_record` function).

### Parallel Opportunities

- US1 test tasks T007–T011 all edit `tests/test_fuzz.py` (sequential to each other) but run in parallel with any `convert.py` work once the fixture (T001) exists.
- T017 (US2 test) and T020/T021 (US3 tests) can be drafted in parallel with US1 implementation since they target different behaviors.
- Polish T023, T024, T025 are `[P]` — different files.
- US2's verification (T019) and US1 can proceed independently once Foundational is done.

---

## Parallel Example: Polish Phase

```bash
# Different files — safe to run together:
Task: "Document fuzz flags in README.md"            # T023
Task: "Add fuzz section to config.example.json"     # T024
Task: "Run ruff check . and fix lint"               # T025
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: Setup (T001).
2. Phase 2: Foundational (T002–T006) — flags, `FuzzConfig`, no-op hook.
3. Phase 3: User Story 1 (T007–T016) — real perturbation + realism + WARNING + conformance.
4. **STOP and VALIDATE**: fuzzed output is realistic, obfuscated, and FHIR-conformant.

### Incremental Delivery

1. Setup + Foundational → wiring ready (default behavior unchanged).
2. US1 → fuzzed-but-realistic output (MVP).
3. US2 → provable opt-in/disabled-identity safety net.
4. US3 → reproducible seeded output for demos.
5. Polish → README, config parity, lint, full validation, quickstart.

---

## Notes

- All runtime edits stay in `convert.py` (Single-File Simplicity; file < 1000 lines).
- Fuzzing operates on the normalized row after format detection → FHIR generation stays
  format-agnostic (Multi-Format CSV Input principle).
- The intentional Data-Integrity tension is mitigated by opt-in default + loud WARNING
  (T015) — never silent.
- Commit after each task or logical group; stop at any checkpoint to validate a story.
