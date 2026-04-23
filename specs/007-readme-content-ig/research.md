# Research: Update README with Content IG Documentation

**Date**: 2026-04-23
**Branch**: `007-readme-content-ig`

## R1: What Content to Add

**Question**: What specific information about the Content IG needs
to appear in the README?

**Decision**: Add/update these sections:

1. **Introduction** — Expand the one-liner to mention both IGs.
2. **New section: "FHIR Implementation Guides"** — Explain the two-IG
   architecture with a table naming each IG, its package ID,
   publication URL, and what it provides.
3. **"FHIR profiles used" table** — Add a "Source IG" column and add
   a row for the BedCapacityMeasure from the Content IG.
4. **Version tracking note** — Brief mention that the converter
   tracks two independent IG versions via named constants.

**Rationale**: These additions give readers the full picture without
requiring them to read the constitution or spec files. The information
is derived from the work done in feature 006-content-ig-integration.

---

## R2: Where to Place the Content IG Section

**Question**: Should the IG documentation be a new top-level section
or woven into existing sections?

**Decision**: Add a new "## FHIR Implementation Guides" section after
the "## FHIR profiles used" section. This keeps the profile table
focused on per-resource profiles while the new section explains the
broader IG architecture. Mention version tracking inline in this new
section rather than creating a separate section.

**Alternatives considered**:
- Weave into the existing "FHIR profiles used" section — rejected;
  would make that section too long and mix two concerns (which
  profiles vs. which IGs).
- Add to the introduction — rejected; too much detail for the
  opening.
