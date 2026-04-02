# Data Model: IG Version Tracking

**Feature**: 002-ig-version-tracking | **Date**: 2026-04-02

## Entities

### SAFR IG Version (new constant)

| Field | Type | Description |
|-------|------|-------------|
| `SAFR_IG_VERSION` | `str` | Semver string with optional pre-release suffix (e.g., `"1.0.0-ballot"`, `"1.0.0"`). Single source of truth for the target US SAFR IG version. |

**Validation rule**: Must match `^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$`. Validated at startup; converter exits with error code 1 and clear message if invalid or empty.

**Relationships**: Used by all SAFR-specific profile URL constants and referenced by CI validation commands.

### SAFR Profile URL Constants (modified)

| Constant | Current Value | New Value |
|----------|--------------|-----------|
| `BUNDLE_PROFILE` | `http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-measurereport-bundle` | `f"http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-measurereport-bundle\|{SAFR_IG_VERSION}"` |
| `ORG_PROFILE` | `http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-submitting-organization` | `f"http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-submitting-organization\|{SAFR_IG_VERSION}"` |
| `MEASURE_URL` | `http://hl7.org/fhir/us/safr/Measure/BedCapacityMeasure\|1.0.0-ballot` | `f"http://hl7.org/fhir/us/safr/Measure/BedCapacityMeasure\|{SAFR_IG_VERSION}"` |

### External Profile URL Constants (unchanged)

| Constant | Value | Reason unchanged |
|----------|-------|-----------------|
| `MEASUREREPORT_PROFILE` | `http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/indv-measurereport-deqm` | DEQM profile — versioned by its own IG |
| `QICORE_ORG_PROFILE` | `http://hl7.org/fhir/us/qicore/StructureDefinition/qicore-organization` | QICore profile |
| `LOCATION_PROFILE` | `http://hl7.org/fhir/us/qicore/StructureDefinition/qicore-location` | QICore profile |
| `DEVICE_PROFILE` | `http://hl7.org/fhir/uv/crmi/StructureDefinition/crmi-softwaresystemdevice\|1.0.0` | CRMI profile — has its own version |

## State Transitions

N/A — IG version is a static constant, not stateful.

## CI Configuration Changes

| Element | Current | New |
|---------|---------|-----|
| Validator `-ig` argument | `-ig hl7.fhir.us.safr` | `-ig hl7.fhir.us.safr#1.0.0-ballot` (extracted from `SAFR_IG_VERSION` in `convert.py`) |
| IG version logging | None | Echo step before validation: `echo "Validating against SAFR IG version: $SAFR_IG_VERSION"` |
| Version extraction | N/A | `SAFR_IG_VERSION=$(python3 -c "import re; m=re.search(r\"SAFR_IG_VERSION\s*=\s*['\"]([^'\"]+)['\"]\", open('convert.py').read()); print(m.group(1))")` |
