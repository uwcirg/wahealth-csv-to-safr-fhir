# Research: IG Version Tracking

**Feature**: 002-ig-version-tracking | **Date**: 2026-04-02

## R1: FHIR Profile Canonical URL Versioning Syntax

**Decision**: Use `{canonical-url}|{version}` syntax in `meta.profile` arrays for SAFR-defined profiles only.

**Rationale**: This is the standard FHIR R4 canonical reference versioning format (defined in http://hl7.org/fhir/R4/references.html#canonical). The existing codebase already uses this syntax for `MEASURE_URL` and `DEVICE_PROFILE`. The validator matches the `|version` suffix against loaded IG package versions, so the profile version and `-ig` package version must be kept in sync.

**Alternatives considered**:
- Unversioned profile URLs (current state for `BUNDLE_PROFILE` and `ORG_PROFILE`) — rejected because the constitution mandates traceability and the spec requires versioned SAFR profile URLs.
- Versioning external profiles (QICore, DEQM) with the SAFR version — rejected per FR-003; external profiles are versioned by their own IGs.

## R2: HL7 FHIR Validator `-ig` Versioned Package Syntax

**Decision**: Use `-ig hl7.fhir.us.safr#<version>` in CI validation commands.

**Rationale**: The `{package-id}#{version}` syntax is the standard way to specify a versioned IG package for the HL7 FHIR Validator. The validator resolves packages from the FHIR Package Registry (`packages.fhir.org`) and supports pre-release versions like `1.0.0-ballot`. Currently, CI uses unversioned `-ig hl7.fhir.us.safr`, which resolves to whatever the registry considers latest — non-reproducible.

**Alternatives considered**:
- Local IG package (download `.tgz` in CI) — adds complexity without benefit; registry resolution is reliable for published packages.
- Unversioned reference (status quo) — rejected because validation results are not reproducible.

## R3: SAFR IG Version Availability

**Decision**: The initial implementation will use `1.0.0-ballot` (the version already embedded in `MEASURE_URL`), but **note that `1.0.0` (STU 1 final) was published on April 1, 2026**. Upgrading to `1.0.0` should be a straightforward follow-up: change the single `SAFR_IG_VERSION` constant and run validation.

**Rationale**: The feature's goal is to establish the IG version tracking mechanism. Using the current declared version (`1.0.0-ballot`) first ensures the mechanism works correctly. A version upgrade (to `1.0.0`) is a separate deliberate change per the constitution's "Accommodating IG Changes" rule (FR-006).

**Published versions**:
| Version | Status | Date |
|---------|--------|------|
| `1.0.0` | STU 1 (Trial-use) | 2026-04-01 |
| `1.0.0-ballot` | Ballot | 2025-03-28 |

**Package name**: `hl7.fhir.us.safr`

**Alternatives considered**:
- Jump directly to `1.0.0` — possible but mixes two changes (mechanism + version upgrade); better to ship the mechanism first, then upgrade.

## R4: IG Version Constant Design

**Decision**: A simple string constant `SAFR_IG_VERSION = "1.0.0-ballot"` at the top of `convert.py`, used via f-strings to construct versioned URLs. Startup validation with a lightweight regex.

**Rationale**: Consistent with single-file simplicity, zero-dependency runtime, and the existing constant style in `convert.py`. F-strings are readable and make the version's use explicit. A regex check (`r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$'`) at startup catches empty/malformed values per the edge case requirement.

**Alternatives considered**:
- Structured version object (dataclass/namedtuple) — overengineered for a single string used in string interpolation.
- Config file (`config.json`) for IG version — rejected; the IG version is a code-level conformance declaration, not per-hospital configuration. All hospitals target the same IG version.
- Environment variable — rejected; same reasoning as config file, plus would break the "deliberate, reviewable change" requirement (FR-006).

## Existing Codebase State (Pre-Implementation)

**Currently versioned**:
- `MEASURE_URL` (line 54): `"...BedCapacityMeasure|1.0.0-ballot"` — uses embedded version
- `DEVICE_PROFILE` (line 42): `"...crmi-softwaresystemdevice|1.0.0"` — CRMI version, NOT SAFR

**Currently unversioned (need SAFR version suffix)**:
- `BUNDLE_PROFILE` (line 37): `"...us-safr-measurereport-bundle"` → needs `|{SAFR_IG_VERSION}`
- `ORG_PROFILE` (line 38): `"...us-safr-submitting-organization"` → needs `|{SAFR_IG_VERSION}`

**External profiles (keep as-is per FR-003)**:
- `MEASUREREPORT_PROFILE`: DEQM profile — versioned by DEQM IG
- `QICORE_ORG_PROFILE`, `LOCATION_PROFILE`: QICore profiles — versioned by QICore IG
- `DEVICE_PROFILE`: CRMI profile — already versioned with CRMI version `|1.0.0`

**CI gap**: `.github/workflows/ci.yml` line 58 uses `-ig hl7.fhir.us.safr` (unversioned)
