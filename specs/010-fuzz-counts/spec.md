# Feature Specification: Fuzz Counts for Realistic but Non-Real Data

**Feature Branch**: `010-fuzz-counts`  
**Created**: 2026-06-03  
**Status**: Draft  
**Input**: User description: "I need to fiddle with the data so that the counts aren't real, but are still realistic. So, consume the input as we currently do, and then during gen of the FHIR resource fiddle with counts."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Produce shareable output with obfuscated counts (Priority: P1)

A data steward needs to share or demonstrate FHIR output derived from a real
hospital census file without disclosing the facilities' true bed-occupancy and
emergency-department numbers. They run the conversion with count fuzzing turned
on. The resulting FHIR resources carry counts that have been perturbed away from
their true values, yet every count remains plausible for a hospital of that size
(non-negative, occupied never exceeds capacity, aggregates consistent with their
parts). The original real numbers cannot be recovered from the output.

**Why this priority**: This is the entire purpose of the feature — replacing real
counts with realistic decoys so output can be circulated for testing, demos, or
external review without exposing sensitive operational data. Without it, no value
is delivered.

**Independent Test**: Convert a known input file with fuzzing enabled, then compare
the count values in the generated FHIR resources against the input. The counts must
differ from the real values while still satisfying every realism constraint, and the
set of resources, codes, and structure must otherwise be identical to a normal run.

**Acceptance Scenarios**:

1. **Given** a census input file and fuzzing enabled, **When** the file is converted,
   **Then** the counts in the FHIR output differ from the true input counts.
2. **Given** fuzzing enabled, **When** the output is inspected, **Then** every count is
   a non-negative integer and no occupied count exceeds its corresponding capacity.
3. **Given** fuzzing enabled, **When** an aggregate count (e.g., total adult beds,
   all beds) is inspected, **Then** it equals the sum of the fuzzed component counts it
   is composed of (no internal contradictions).
4. **Given** fuzzing enabled, **When** the output is compared to a normal run,
   **Then** the resource types, identifiers, codes, periods, and overall structure are
   unchanged — only count values differ.

---

### User Story 2 - Preserve true-data behavior by default (Priority: P1)

An operator running the converter for real reporting must be confident that the tool
does not silently alter counts. With fuzzing turned off (the default), the output is
byte-for-byte the same as today, carrying the real numbers.

**Why this priority**: Fuzzed data must never leak into a real submission. Making the
feature opt-in protects existing production use and prevents accidental falsification.

**Independent Test**: Convert a file without enabling fuzzing and confirm the output
matches the current (pre-feature) output exactly.

**Acceptance Scenarios**:

1. **Given** fuzzing is not enabled, **When** a file is converted, **Then** all counts in
   the output equal the true input counts.
2. **Given** fuzzing is not enabled, **When** the output is compared to the existing
   regression baseline, **Then** there is no difference.

---

### User Story 3 - Reproducible fuzzing for repeatable demos (Priority: P2)

A user generating a fixed demo dataset wants the same input to yield the same fuzzed
output across runs, so screenshots, documentation, and downstream tests stay stable.
They supply a seed value; rerunning with the same seed and input reproduces identical
fuzzed counts.

**Why this priority**: Reproducibility is valuable for demos and regression testing but
is not required to deliver the core obfuscation value, so it ranks below P1.

**Independent Test**: Convert the same input twice with the same seed and confirm the
fuzzed counts are identical; convert again with a different seed and confirm the counts
differ.

**Acceptance Scenarios**:

1. **Given** a chosen seed, **When** the same input is converted twice with that seed,
   **Then** the two outputs contain identical counts.
2. **Given** two different seeds, **When** the same input is converted with each,
   **Then** the resulting counts differ.

---

### Edge Cases

- **Zero counts**: When a true count is 0 (e.g., an empty pediatric unit), fuzzing must
  keep the value realistic for an empty/near-empty unit and never produce a negative
  number.
- **Occupied exceeds capacity in source data**: The source occasionally reports occupied
  greater than capacity (an existing data-quality case). Fuzzing must not worsen this into
  output that violates the occupied ≤ capacity realism rule.
- **Small counts**: Very small counts (e.g., 1–3) must still be obfuscated meaningfully
  rather than left unchanged, so the real value is not trivially recoverable, while staying
  plausible.
- **Large facilities**: Large aggregate counts (several hundred beds) must be perturbed
  proportionally so the result stays realistic for a large hospital.
- **Missing/blank input cells**: Cells that are currently treated as 0 must continue to
  behave consistently when fuzzing is enabled.
- **Fuzzing requested but no counts present**: Conversion must complete normally without error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST consume input exactly as it does today; fuzzing MUST NOT
  change how input is parsed, normalized, or validated.
- **FR-002**: The system MUST apply count perturbation during generation of the FHIR
  resources, after input has been consumed and normalized.
- **FR-003**: The system MUST perturb every count that appears in the FHIR output,
  including per-area occupied and unoccupied bed counts, emergency-department counts, and
  all computed aggregate counts.
- **FR-004**: Fuzzed counts MUST differ from the true input counts (the feature MUST
  actually obfuscate, not pass values through unchanged).
- **FR-005**: Every fuzzed count MUST be a non-negative integer.
- **FR-006**: A fuzzed occupied count MUST NOT exceed its corresponding (fuzzed) capacity.
- **FR-007**: Fuzzed aggregate counts MUST remain internally consistent — each aggregate
  MUST equal the sum of the fuzzed component counts it represents.
- **FR-008**: Each fuzzed count MUST stay within a realistic neighborhood of its true
  value (plausible for a hospital of that size), not an arbitrary or wildly different number.
- **FR-009**: Fuzzing MUST be opt-in; when not enabled, the system MUST produce output
  identical to the current behavior with real counts.
- **FR-010**: When fuzzing is disabled, the output MUST match the existing regression
  baseline with no differences.
- **FR-011**: The system MUST NOT alter any non-count content of the FHIR output (resource
  types, identifiers, codes, reporting periods, facility/location data, structure) when
  fuzzing is enabled.
- **FR-012**: The system MUST support reproducible fuzzing such that the same input plus
  the same seed yields identical fuzzed counts, and different seeds yield different counts.
- **FR-013**: The obfuscation MUST be such that the true counts cannot be reliably recovered
  from the fuzzed output alone.
- **FR-014**: The system MUST clearly indicate (e.g., in run output or logging) when fuzzing
  is active, so fuzzed output is not mistaken for real data.

### Key Entities *(include if feature involves data)*

- **Count**: A non-negative integer reported for a measured population — bed occupancy,
  bed capacity, emergency-department census, or a computed aggregate. The unit of data the
  feature perturbs.
- **Fuzzing configuration**: The user's choice to enable obfuscation, the perturbation
  magnitude (how far counts may stray from truth), and an optional seed controlling
  reproducibility.
- **Realism constraints**: The invariants a fuzzed count set must satisfy — non-negativity,
  occupied ≤ capacity, and aggregate-equals-sum-of-parts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With fuzzing enabled, 100% of counts in the FHIR output satisfy all realism
  constraints (non-negative integer, occupied ≤ capacity, aggregates equal the sum of their
  fuzzed parts).
- **SC-002**: With fuzzing enabled, the overwhelming majority of non-zero counts differ from
  their true values, and no run reproduces the full set of true counts.
- **SC-003**: With fuzzing disabled, the output is identical to the current baseline (zero
  differences).
- **SC-004**: With fuzzing enabled, generated FHIR output passes the project's FHIR validation
  pipeline with zero project-introduced errors (same standard as today).
- **SC-005**: Re-running the same input with the same seed produces identical output 100% of
  the time; running with a different seed changes the counts.
- **SC-006**: A reviewer inspecting fuzzed output cannot distinguish it from plausible real
  data on the basis of impossible or contradictory counts.

## Assumptions

- **Opt-in default**: Fuzzing is off by default. Real reporting runs are unaffected unless a
  user explicitly turns fuzzing on. This protects against fuzzed data reaching a real submission.
- **Scope of counts**: "Counts" means the numeric population values emitted into the FHIR
  resources — per-area occupied/unoccupied bed counts, emergency-department counts, and the
  computed aggregates. No other fields are treated as counts.
- **Realism over precision**: "Realistic" means each fuzzed count stays in a plausible
  neighborhood of the true value (a moderate perturbation, defaulting to roughly ±10–15% with
  a small floor for tiny counts) while honoring the realism constraints. The exact magnitude is
  a tunable default chosen for plausibility, not a hard external requirement.
- **Internal consistency preserved**: Aggregates and the occupied/unoccupied/capacity
  relationships remain coherent after fuzzing, because the entire point is output that looks real.
- **No suppression intent**: This feature obfuscates counts for sharing/demo purposes; it is not
  a formal statistical-disclosure-control or small-cell-suppression mechanism, and no compliance
  guarantee is claimed.
- **Reuses existing structure**: The conversion's existing input formats, FHIR resource shapes,
  per-facility output layout, and validation pipeline are reused unchanged; only count values are
  affected.
- **Configuration location**: The enable toggle, magnitude, and seed are supplied through the
  converter's existing configuration mechanism (configuration file and/or command-line options),
  consistent with how the tool is already operated.
