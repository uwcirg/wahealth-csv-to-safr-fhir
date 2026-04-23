# Quickstart: CDC NHSN SAFR Content IG Integration

**Branch**: `006-content-ig-integration`

## What Changed

This feature integrates the CDC NHSN SAFR Content Implementation
Guide (`gov.cdc.nhsn.safr`) alongside the existing base US SAFR IG
(`hl7.fhir.us.safr`). Three things change:

1. **Measure canonical URL** — `MeasureReport.measure` now references
   the Content IG's authoritative BedCapacityMeasure instead of the
   base IG's example Measure.
2. **Content IG version tracking** — A new `NHSN_SAFR_IG_VERSION`
   constant in `convert.py` tracks the Content IG version separately
   from `SAFR_IG_VERSION`.
3. **Dual-IG validation** — CI and LLM validation now load both IGs
   into the FHIR validator.

## Verify It Works

```bash
# 1. Check the new constant exists
grep -q "NHSN_SAFR_IG_VERSION" convert.py && echo "PASS: Content IG version constant exists"

# 2. Check MEASURE_URL references the Content IG canonical
grep "www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure" convert.py \
  && echo "PASS: Measure URL points to Content IG"

# 3. Convert a test fixture and check the output
python3 convert.py input/2025.10.21.Test.Facility.BedCapacity.csv \
  --config config.example.json --output-dir output

# 4. Verify the MeasureReport.measure field in output
grep -r '"measure"' output/ | head -1
# Should show: http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure|1.0.0

# 5. Validate with both IGs
SAFR_IG_VERSION=$(grep -oP 'SAFR_IG_VERSION\s*=\s*"\K[^"]+' convert.py | head -1)
java -jar validator_cli.jar output/**/*.json \
  -version 4.0.1 \
  -ig hl7.fhir.us.safr#$SAFR_IG_VERSION \
  -ig https://safr-ci.nhsnlink.org/package.tgz
```

## Files Changed

- `convert.py` — `NHSN_SAFR_IG_VERSION` constant, `MEASURE_URL`
  update
- `.github/workflows/ci.yml` — Dual-IG validation pipeline
- `CLAUDE.md` — Updated LLM validation instructions
- `known-validation-issues.md` — New entries if Content IG introduces
  upstream errors
