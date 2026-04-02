# Quickstart: IG Version Tracking

**Feature**: 002-ig-version-tracking | **Date**: 2026-04-02

## What This Feature Does

Adds a single source of truth (`SAFR_IG_VERSION` constant) for which version of the US SAFR Implementation Guide the converter targets. This version is:
1. Declared as a named constant at the top of `convert.py`
2. Applied to all SAFR-defined profile URLs in generated FHIR output
3. Used by CI to validate against the exact IG version
4. Logged in CI output for traceability

## How to Change the Target IG Version

1. Open `convert.py`
2. Find `SAFR_IG_VERSION = "1.0.0-ballot"` (near line 36)
3. Change the version string (e.g., to `"1.0.0"`)
4. Run the converter against test inputs: `python3 convert.py input/2025.10.21.Test.Facility.BedCapacity.csv --config config.example.json --output-dir output`
5. Verify profile URLs in output Bundle JSON include the new version
6. Push and let CI run full FHIR validation against the new IG version
7. Review CI output to confirm the logged IG version matches

## What Changes in Generated Output

**Before** (profile URLs unversioned):
```json
"meta": {
  "profile": ["http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-measurereport-bundle"]
}
```

**After** (SAFR profile URLs include version):
```json
"meta": {
  "profile": ["http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-measurereport-bundle|1.0.0-ballot"]
}
```

External profiles (QICore, DEQM, CRMI) are **not changed** — they retain their own versioning.

## Files Modified

- `convert.py` — new `SAFR_IG_VERSION` constant, refactored profile URL constants, startup validation
- `.github/workflows/ci.yml` — versioned `-ig` argument, IG version logging
