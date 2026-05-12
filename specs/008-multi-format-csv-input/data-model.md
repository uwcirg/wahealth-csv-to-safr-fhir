# Data Model: Support multiple hospital CSV input formats

Internal, in-memory structures only — there is no database. "Entities" here are the
shapes that flow through `convert.py`. Persisted FHIR resources (Bundle,
MeasureReport, Organization, Location, Device) are unchanged in structure and are
documented by the SAFR/QI-Core/CRMI IGs, not here.

---

## Entity: SupportedFormat (static table)

One per recognized CSV layout. Encoded as constant data in `convert.py` (or
`csv_formats.py` if split — see research R7).

| Field | Type | Notes |
|---|---|---|
| `id` | str | `"original"` \| `"wahealth_dict_2026_04_30"` \| `"kc_mft_2026_05_11"` |
| `display_name` | str | `"Original WA Health format"` \| `"2026-04-30 WA Health dictionary from KC"` \| `"KC multi-hospital from MFT 2026-05-11"` |
| `detect_columns` | tuple[str, …] | Header columns that must all be present for this format to match (see contract). |
| `multi_facility` | bool | `True` only for `kc_mft_2026_05_11`. |
| `has_guid` | bool | `True` only for `original`. |
| `date_formats` | tuple[str, …] | strptime patterns tried in order for the reporting-date column. |
| `column_map` | dict | Maps each normalized field (below) to this format's source column name; bed areas map to a `(occupied_col, capacity_col)` pair. HRD columns are intentionally absent from the map (ignored). |

**Detection rule** (FR-001, FR-006): `detect_format(header)` returns the first
`SupportedFormat` whose `detect_columns` are all in `header`; if none match, raise
`UnrecognizedFormatError` → caller logs an error listing the `display_name`s and
exits non-zero, having written nothing.

---

## Entity: NormalizedRow

The single representation every parser produces and the only thing
`compute_groups`, Bundle assembly, and FHIR-server upsert read (FR-005). A plain
`dict`:

| Key | Type | Source / rule |
|---|---|---|
| `facility_name` | str | The format's facility-name column (`facility_name` / `facility` / `Facility`). Used for the output filename, the `subject`/`reporter` displays, and (for sparse profiles) the Organization/Location `name`. |
| `facility_guid` | str \| None | The `facility_guid` column for the original format; `None` for the others. |
| `reporting_date` | datetime.date | Parsed from the format's reporting-date column via its `date_formats`. Normalizes away the per-format string convention. |
| `<area>_occ` | int | For each canonical area below — `safe_int` of the format's "currently occupied" column for that area (empty/blank → 0, logged; non-numeric → loud `ValueError`). |
| `<area>_cap` | int | Likewise for the format's "capacity" column. |
| `adult_ed` | int | `safe_int` of the format's previous-day adult ED visits column. |
| `peds_ed` | int | `safe_int` of the format's previous-day pediatric ED visits column. |

**Canonical bed areas** (8): `adult_icu`, `peds_icu`, `adult_acute`, `peds_acute`,
`neonatal_icu`, `nursery`, `surge`, `other`. (`other` participates only in the
`AllBeds` aggregate, as today.)

**Derived (not stored)**: `unoccupied = max(0, cap - occ)` per area, computed in
`get_occupied_and_unoccupied(record, area)`; the 25 MeasureReport groups computed
by `compute_groups(record)` exactly as before — per-area occupied/unoccupied (×7
direct areas), ED census (×3), and the computed aggregates AllBeds / AdultTotal /
PedsTotal / SpecialtyTotal (×8). Aggregates are summed from the raw `_occ`/`_cap`
values, never from intermediate group counts (constitution: Data Integrity).

**Notes**: columns a format carries but the model doesn't need — `county`,
`created_on`, `Contact`, `all_inpatient_occ/cap`, and all `covid_*`/`flu_*`/`rsv_*`
columns — are simply not read (FR-012, FR-005). The `all_inpatient_*` columns in
the dictionary format are *ignored*, not trusted, because the constitution requires
aggregates be computed from raw per-area values.

---

## Entity: FacilityProfile

The hospital-identity bundle used to build the per-row Organization and Location.
Produced by `resolve_facility_profile(record, config, format_id) -> (profile, unregistered: bool)`.

| Field | Type | Notes |
|---|---|---|
| `organization` | dict | Same shape `build_organization_resource` consumes today: `nhsn_org_id`, `name`, `phone`, `address{line[],city,state,postalCode,country}`. For a sparse profile only `name` (= `record["facility_name"]`) is populated; `nhsn_org_id` is unused (the placeholder identifier is built from the name instead); `phone`/`address` absent. |
| `location` | dict | Same shape `build_location_resource` consumes today: `identifier_system`, `identifier_value`, `name`, `description`. For a sparse profile: `name`/`description` = `record["facility_name"]`; identifier replaced by the placeholder (system = `UNREGISTERED_FACILITY_SYSTEM`, value = `<slug>:location`). |
| `unregistered` | bool | `True` ⇒ resource builders emit the placeholder NHSN OrgID / Location identifier and the caller logs one WARNING per facility. |

**Resolution rules**:
- `format_id ∈ {original, wahealth_dict_2026_04_30}` → `profile = {organization: config["organization"], location: config["location"]}`, `unregistered = False`. (Identical to today.)
- `format_id == kc_mft_2026_05_11`:
  - if `name in config.get("facilities", {})` → `profile = config["facilities"][name]` (validated to contain `organization` and `location`), `unregistered = False`;
  - else → synthesized sparse profile, `unregistered = True`, `logger.warning("Facility %r not in config 'facilities' registry; emitting sparsely-populated Organization/Location with a placeholder identifier (%s|%s)", name, UNREGISTERED_FACILITY_SYSTEM, slug)`.
- The top-level `organization`/`location` are **never** used as a partial fallback for an unregistered facility (research R6).

**Stable key** (FR-007): `stable_facility_key = record["facility_guid"] or slugify(record["facility_name"])`. Used as the seed for `upsert_bundle`'s deterministic UUID and to cache `org_ref`/`loc_ref` per facility within a `--fhir-server` run.

---

## Entity: Config (file: `config.json`) — schema delta

Unchanged required sections: `organization`, `location`, `software`. Unchanged
optional section: `server`. **New optional** section:

```jsonc
"facilities": {
  "<exact CSV Facility value>": {
    "organization": { "nhsn_org_id": "...", "name": "...", "phone": "...",
                      "address": { "line": ["..."], "city": "...", "state": "WA",
                                   "postalCode": "...", "country": "USA" } },
    "location":     { "identifier_system": "...", "identifier_value": "...",
                      "name": "...", "description": "..." }
  }
}
```

**Validation** (extends `load_config`): if `facilities` is present it must be an
object; each value must contain non-empty `organization` and `location` objects.
Absence of `facilities`, or a missing entry for some facility in a multi-facility
file, is *not* an error — it triggers the sparse path. `config.example.json` ships
a populated `facilities` example covering a subset of the census fixture's
facilities (the rest deliberately exercise the sparse path in CI).

---

## Slugify helper

`slugify(name: str) -> str`: lowercase; replace any run of non-`[a-z0-9]`
characters with a single `-`; strip leading/trailing `-`. Deterministic and
stable. Used for the placeholder identifier values and for `stable_facility_key`
when no GUID exists. (Distinct from `sanitize_filename`, which is for filesystem
paths and is unchanged.)

Example: `"AMC - University Triangle"` → `"amc-university-triangle"`.
