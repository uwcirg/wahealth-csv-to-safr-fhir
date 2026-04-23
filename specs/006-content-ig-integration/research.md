# Research: CDC NHSN SAFR Content IG Integration

**Date**: 2026-04-23
**Branch**: `006-content-ig-integration`

## R1: Content IG Package Availability

**Question**: Is `gov.cdc.nhsn.safr#1.0.0` available in the FHIR
package registries (`packages.fhir.org`, `packages2.fhir.org`)?

**Finding**: No. Both registries return 404 for `gov.cdc.nhsn.safr`.
The package is not published to the standard FHIR registries as of
2026-04-23.

**Decision**: The FHIR validator supports loading IGs from a URL to
a `package.tgz` file. Use
`https://safr-ci.nhsnlink.org/package.tgz` as the `-ig` argument
instead of the registry-style `gov.cdc.nhsn.safr#1.0.0` identifier.
This is a supported validator feature. When the package eventually
appears in a registry, the `-ig` argument can be switched to the
`gov.cdc.nhsn.safr#X.Y.Z` form with a simple constant change.

**Alternatives considered**:
- Wait for registry publication — rejected; blocks all work
  indefinitely.
- Download `package.tgz` to repo and use `-ig` with a local path —
  viable fallback if URL approach has issues in CI. The file is ~2MB
  and could be cached.

---

## R2: Content IG BedCapacityMeasure Population Group Codes

**Question**: Does the Content IG's BedCapacityMeasure use the same
LOINC codes the converter currently maps?

**Finding**: No. The Content IG's BedCapacityMeasure uses CQL
criteria names for its population definitions (e.g., "All Beds
Occupied Initial Population", "Adult ICU Beds Occupied Initial
Population") and references the `nhsn-safr-bed-capacity-codes`
CodeSystem for facility-type classification (HOSP, CHLD, IPF, IRF,
OTH, ICU, ED, PEDS). It does not use LOINC codes like 112579-8 to
identify individual population groups.

The converter currently uses LOINC codes in `MeasureReport.group.code`
(e.g., `112579-8` for "AllBedsOccupied"). These LOINC codes came from
the base IG's example Measure.

**Decision**: This feature focuses on three things: adding the Content
IG version constant, updating the `MEASURE_URL` canonical, and adding
the Content IG to the validation pipeline. The population group code
question (whether MeasureReport.group.code values need to change from
LOINC to CQL criteria names or some other system) is a deeper
alignment issue that may surface during validation and would be
addressed as a separate follow-up feature if needed.

**Rationale**: Changing the MEASURE_URL and adding dual-IG validation
are independently valuable — they get the canonical reference correct
and expand validation coverage. Code alignment is a separate concern
that should be informed by actual validator output when both IGs are
loaded.

---

## R3: Measure Canonical URL Confirmation

**Question**: What is the exact canonical URL for the Content IG's
BedCapacityMeasure, and should it include a version suffix?

**Finding**: The Content IG defines:
- Canonical URL:
  `http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure`
- Version: `1.0.0`
- Status: Draft
- Experimental: true

The current converter uses:
```
http://hl7.org/fhir/us/safr/Measure/BedCapacityMeasure|1.0.0
```

The base IG (`hl7.fhir.us.safr`) only publishes an *example* Measure
at `http://hl7.org/fhir/us/safr/Measure/BedCapacityMeasureExample`
(informational, status informative). The canonical the converter
currently uses (`/Measure/BedCapacityMeasure` without the `Example`
suffix) does not match the base IG's published artifact.

**Decision**: Update `MEASURE_URL` to use the Content IG's canonical
URL with the Content IG version appended:
```
http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure|{SAFR_CI_IG_VERSION}
```

---

## R4: Content IG Version Constant Naming

**Question**: What should the Content IG version constant be named?

**Decision**: `NHSN_SAFR_IG_VERSION`. Rationale:
- The Content IG's package name is `gov.cdc.nhsn.safr`, and "NHSN
  SAFR" is the IG's own title prefix.
- `SAFR_CI_IG_VERSION` (from the spec) could be confused with
  "Continuous Integration" rather than "Content Implementation."
- `NHSN_SAFR_IG_VERSION` clearly identifies the CDC NHSN-published
  IG and pairs naturally with the existing `SAFR_IG_VERSION` for the
  base HL7 IG.
- The existing `SAFR_IG_VERSION` tracks `hl7.fhir.us.safr`; the new
  `NHSN_SAFR_IG_VERSION` tracks `gov.cdc.nhsn.safr`.

**Alternatives considered**:
- `SAFR_CI_IG_VERSION` — "CI" is ambiguous (Continuous Integration
  vs Content Implementation). Rejected.
- `SAFR_CONTENT_IG_VERSION` — clear but verbose. Acceptable
  alternative.
- `CDC_NHSN_SAFR_IG_VERSION` — too long. Rejected.

---

## R5: Validator Behavior with Package URL

**Question**: Can the FHIR validator accept a URL to `package.tgz`
as an `-ig` argument?

**Decision**: Yes. The HL7 FHIR validator supports `-ig` with:
- Registry-style: `hl7.fhir.us.safr#1.0.0`
- URL to package: `https://safr-ci.nhsnlink.org/package.tgz`
- Local file path: `./path/to/package.tgz`

The URL approach is preferred for now. If the CI build site is
unreliable, a cached local copy can be used as fallback.

---

## R6: Content IG Dependencies and Validation Impact

**Question**: Will adding the Content IG to validation introduce new
errors?

**Finding**: The Content IG (`gov.cdc.nhsn.safr#1.0.0`) depends on
`hl7.fhir.us.safr#1.0.0` and 25 other packages. The base IG is
already loaded by the current validator invocation, so the Content IG
adds the Measure/Library/CodeSystem definitions on top.

**Decision**: Adding the Content IG to validation will likely surface
new validation results related to the Measure reference. Any new
errors must be evaluated:
- Errors caused by the MEASURE_URL change (expected — that's the
  point of the change).
- Errors from upstream Content IG dependencies — document in
  `known-validation-issues.md`.
- Errors revealing actual converter output issues — fix as part of
  this feature.

The validator run with the Content IG loaded is the key verification
step. It should be done early in implementation (User Story 3) even
though it's P2, to inform whether additional changes are needed.
