# CLI Contract: `convert.py` (009-per-facility-output-layout)

This contract documents the **changed** parts of the `convert.py` command-line interface and output
layout. Everything not listed here is unchanged.

## Invocation

```bash
python3 convert.py <csv_file> [--config config.json] [--output-dir ./output] \
                   [--fhir-server URL] [--bundles-mrs-only]
```

## New option

| Option | Form | Default | Behavior |
|--------|------|---------|----------|
| `--bundles-mrs-only` | flag (no value) | absent | When present, the converter writes only the Bundle file(s) and the standalone `MeasureReport.json` for each facility; it does **not** write `Organization.json`, `Device.json`, or `Location.json`. When absent, the full set of individual resources is written. Does not affect FHIR-server persistence, Bundle/MeasureReport contents, logging, or exit codes. Appears in `--help`. |

## Output layout contract

For each `(facility, reporting date)` data row, with `D = {output-dir}/{reporting_date}` and
`F = D/{sanitized_facility_name}`:

| Path | When | Notes |
|------|------|-------|
| `D/{facility}.{date}.BedCapacity.json` | always | the Bundle; lives directly in `D` |
| `F/` | always | per-facility subdirectory; created if absent |
| `F/MeasureReport.json` | always | |
| `F/Organization.json` | only when `--bundles-mrs-only` is absent | |
| `F/Device.json` | only when `--bundles-mrs-only` is absent | |
| `F/Location.json` | only when `--bundles-mrs-only` is absent | |
| `D/{any-resource}.json` directly in `D` | **never** | individual resources are never written loose in the date directory |

`{sanitized_facility_name}` is `sanitize_filename(record["facility_name"] or "facility_{i}")` —
identical to the `{facility}` segment of the Bundle filename.

## Logging

Each generated file (Bundle and each individual resource actually written) is logged at INFO to both
console and the timestamped `log/convert_*.log`, as today. When `--bundles-mrs-only` is set, the
skipped files simply produce no "Generated …" lines.

## Exit codes

Unchanged. An unrecognized CSV header is still a hard error before any output is written.

## Backwards-incompatible change

The location of individual resource files moves from `{output-dir}/{date}/{ResourceType}.json` to
`{output-dir}/{date}/{facility}/{ResourceType}.json`. Any downstream tooling that read the old paths
must be updated. The Bundle file path is unchanged.
