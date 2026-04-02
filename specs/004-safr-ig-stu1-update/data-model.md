# Data Model: Update SAFR IG Version to STU 1

**Feature**: 004-safr-ig-stu1-update  
**Date**: 2026-04-02

## Entities

No new entities are introduced by this feature. The existing data model is unchanged.

## Affected Constants

| Constant | Current Value | New Value |
|----------|--------------|-----------|
| `SAFR_IG_VERSION` | `1.0.0-ballot` | `1.0.0` |

## Derived Values (automatically updated)

| Derived Constant | Current Resolved Value | New Resolved Value |
|-----------------|----------------------|-------------------|
| `BUNDLE_PROFILE` | `...us-safr-measurereport-bundle\|1.0.0-ballot` | `...us-safr-measurereport-bundle\|1.0.0` |
| `ORG_PROFILE` | `...us-safr-submitting-organization\|1.0.0-ballot` | `...us-safr-submitting-organization\|1.0.0` |
| `MEASURE_URL` | `...BedCapacityMeasure\|1.0.0-ballot` | `...BedCapacityMeasure\|1.0.0` |

## Validation

No schema or data model validation changes. The existing semver regex on line 40 of `convert.py` accepts `1.0.0` (matches `^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$`).
