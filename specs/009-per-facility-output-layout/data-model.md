# Data Model: Per-Facility Output Layout and Bundles-MRs-Only Mode

This feature changes the **on-disk output layout**, not the FHIR resource model. No FHIR resource
shapes change.

## Output directory tree

```text
{output-dir}/                              # default ./output
└── {YYYY-MM-DD}/                          # reporting date of the row(s)
    ├── {facility_name}.{YYYY-MM-DD}.BedCapacity.json   # Bundle — one per (facility, date) row
    ├── {facility_name_2}.{YYYY-MM-DD}.BedCapacity.json
    └── {facility_name}/                   # per-facility subdirectory of individual resources
        ├── Organization.json              # omitted when --bundles-mrs-only
        ├── Device.json                    # omitted when --bundles-mrs-only
        ├── Location.json                  # omitted when --bundles-mrs-only
        └── MeasureReport.json             # always written
```

### Entities

| Entity | Key | Notes |
|--------|-----|-------|
| Date directory | reporting date (`YYYY-MM-DD`) | Created if absent (`exist_ok=True`). Contains Bundle files and one subdirectory per facility; never contains loose individual-resource `*.json` files. |
| Facility subdirectory | `sanitize_filename(facility_name)` | Created if absent. Name is byte-identical to the `{facility_name}` segment of that facility's Bundle filename. Holds that facility's individual resources for the date. |
| Bundle file | `{facility_name}.{date}.BedCapacity.json` | One per `(facility, reporting date)` row; unchanged content. Lives directly in the date directory. |
| Individual resource file | `{resourceType}.json` | One file per resource type in the Bundle's `entry` array (`Organization`, `Device`, `Location`, `MeasureReport`). Written into the facility subdirectory. Subject to `--bundles-mrs-only` (only `MeasureReport.json` survives). |

### Name sanitization rule (unchanged, reused)

`sanitize_filename(name)` = `name.replace(" ", "_").replace("/", "-").replace("\\", "-")`. Applied
to `record["facility_name"]` (falling back to `facility_{i}` when absent). Used for **both** the
Bundle filename's facility segment and the facility subdirectory name — they always match.

### Overwrite semantics

- Two rows with the **same** sanitized facility name and reporting date → same Bundle filename and
  same facility subdirectory → later row overwrites earlier (unchanged behavior, now correctly
  scoped to that one facility).
- Two rows with **different** facility names, same reporting date → different Bundle filenames and
  different subdirectories → no overwrite (this is the bug being fixed; previously the individual
  resources collided in the shared date directory).

## CLI input model

| Argument | Type | Default | Effect |
|----------|------|---------|--------|
| `csv_file` (positional) | path | — | unchanged |
| `--config` | path | `config.json` | unchanged |
| `--output-dir` | path | `./output` | unchanged; now also the root of per-facility subdirs |
| `--fhir-server` | URL | none | unchanged; **not** affected by `--bundles-mrs-only` |
| `--bundles-mrs-only` | boolean flag (`store_true`) | absent (false) | when present, only Bundle file(s) + `MeasureReport.json` are written **locally**; `Organization.json` / `Device.json` / `Location.json` are skipped. FHIR-server persistence is unchanged (Bundle + standalone MeasureReport are the primary artifacts; Organization/Device/Location are still upserted as supporting resources the MeasureReport's references need) |

## State transitions

None — single-pass conversion, idempotent per `(facility, reporting date)`.
