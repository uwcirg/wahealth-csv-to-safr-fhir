# Quickstart: Update SAFR IG Version to STU 1

**Feature**: 004-safr-ig-stu1-update  
**Date**: 2026-04-02

## What Changes

One constant in `convert.py`:

```
SAFR_IG_VERSION = "1.0.0-ballot"  →  SAFR_IG_VERSION = "1.0.0"
```

All FHIR profile URLs and the Measure URL are derived from this constant via f-strings, so they update automatically.

## How to Verify

1. Run the converter against test fixtures:
   ```bash
   for csv in input/*.BedCapacity.csv; do
     case "$csv" in *column-labels-only*) continue ;; esac
     python3 convert.py "$csv" --config config.example.json --output-dir output
   done
   ```

2. Inspect any output JSON — confirm version strings show `1.0.0` (not `1.0.0-ballot`).

3. Run FHIR validation:
   ```bash
   java -jar validator_cli.jar output/**/*.json \
     -version 4.0.1 \
     -ig hl7.fhir.us.safr#1.0.0
   ```

4. Zero errors required.

## Risk

**Low**. This is a single-constant version bump. The only risk is if the STU 1 IG introduced structural profile changes that require code changes beyond the version string. The FHIR validator will detect this.
