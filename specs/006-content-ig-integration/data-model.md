# Data Model: CDC NHSN SAFR Content IG Integration

**Date**: 2026-04-23
**Branch**: `006-content-ig-integration`

## Constants (convert.py)

| Constant | Current Value | New Value |
|----------|--------------|-----------|
| `SAFR_IG_VERSION` | `"1.0.0"` | Unchanged |
| `NHSN_SAFR_IG_VERSION` | (new) | `"1.0.0"` |
| `MEASURE_URL` | `f"http://hl7.org/fhir/us/safr/Measure/BedCapacityMeasure\|{SAFR_IG_VERSION}"` | `f"http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure\|{NHSN_SAFR_IG_VERSION}"` |

## Validation Pipeline Arguments

| Context | Current `-ig` Arguments | New `-ig` Arguments |
|---------|------------------------|---------------------|
| CI (`.github/workflows/ci.yml`) | `-ig hl7.fhir.us.safr#$SAFR_IG_VERSION` | `-ig hl7.fhir.us.safr#$SAFR_IG_VERSION -ig https://safr-ci.nhsnlink.org/package.tgz` |
| CLAUDE.md (LLM validation) | `-ig hl7.fhir.us.safr#$SAFR_IG_VERSION` | `-ig hl7.fhir.us.safr#$SAFR_IG_VERSION -ig https://safr-ci.nhsnlink.org/package.tgz` |

Note: The Content IG package `gov.cdc.nhsn.safr` is not yet published
to the FHIR package registry. The validator is pointed at the package
URL directly. When the package becomes available in the registry, the
argument can be changed to `-ig gov.cdc.nhsn.safr#$NHSN_SAFR_IG_VERSION`.

## CI Environment Variables

| Variable | Current | New |
|----------|---------|-----|
| `SAFR_IG_VERSION` | Extracted from `convert.py` | Unchanged |
| `NHSN_SAFR_IG_VERSION` | (new) | Extracted from `convert.py` |
| `NHSN_SAFR_IG_URL` | (new) | `https://safr-ci.nhsnlink.org/package.tgz` |

## FHIR Output Changes

The only change to generated FHIR output is the `MeasureReport.measure`
field value:

| Field | Current | New |
|-------|---------|-----|
| `MeasureReport.measure` | `http://hl7.org/fhir/us/safr/Measure/BedCapacityMeasure\|1.0.0` | `http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure\|1.0.0` |

All other generated resource fields are unchanged. Profile URLs,
CodeSystem references, and LOINC group codes remain as-is.

## Files Modified

| File | Change Type | Description |
|------|-------------|-------------|
| `convert.py` | Modify | Add `NHSN_SAFR_IG_VERSION` constant with startup validation; update `MEASURE_URL` canonical |
| `.github/workflows/ci.yml` | Modify | Extract `NHSN_SAFR_IG_VERSION`, add Content IG to validator `-ig` args, update log/summary messages |
| `CLAUDE.md` | Modify | Update LLM validation pipeline instructions to include Content IG |
| `known-validation-issues.md` | Possibly modify | Document any new upstream errors from Content IG validation |
