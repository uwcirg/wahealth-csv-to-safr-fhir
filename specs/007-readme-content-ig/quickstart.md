# Quickstart: Update README with Content IG Documentation

**Branch**: `007-readme-content-ig`

## What Changed

The README now documents the dual-IG architecture:
- Base IG (`hl7.fhir.us.safr`) for structural profiles
- Content IG (`gov.cdc.nhsn.safr`) for Measure definitions

## Verify It Works

```bash
# 1. Check both IGs are mentioned
grep -q "hl7.fhir.us.safr" README.md && \
grep -q "gov.cdc.nhsn.safr" README.md && \
echo "PASS: Both IGs documented"

# 2. Check Content IG URL is present
grep -q "safr-ci.nhsnlink.org" README.md && \
echo "PASS: Content IG publication URL present"

# 3. Check BedCapacityMeasure attribution
grep -q "BedCapacityMeasure" README.md && \
echo "PASS: Measure documented"
```

## Files Changed

- `README.md` — Added "FHIR Implementation Guides" section, updated
  "FHIR profiles used" table with source IG attribution
