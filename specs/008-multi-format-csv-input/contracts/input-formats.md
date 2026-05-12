# Contract: Input CSV Formats

The converter's input contract. Three layouts are recognized; each row maps to one
`NormalizedRow` (see `data-model.md`) and produces one bed-capacity Bundle.
Detection is by **column-name membership** in the header row only (order and
trailing empty columns are irrelevant).

The eight canonical bed areas: `adult_icu`, `peds_icu`, `adult_acute`,
`peds_acute`, `neonatal_icu`, `nursery`, `surge`, `other`.

---

## 1. `original` — "Original WA Health format"

- **Detection**: header contains both `facility_guid` and `reporting_date`.
- **Facility per file**: one (multiple rows = multiple reporting dates for that facility).
- **GUID**: yes (`facility_guid`).
- **Reporting date**: `MM/DD/YYYY`.
- **HRD columns present**: yes (~35 `*_laboratoryconfirmed_*` / `previous_days_admissions_*` columns) — **ignored**.
- **Identity source**: top-level `organization` / `location` in `config.json`.

| NormalizedRow field | CSV column |
|---|---|
| `facility_name` | `facility_name` |
| `facility_guid` | `facility_guid` |
| `reporting_date` | `reporting_date` |
| `adult_icu_occ` / `adult_icu_cap` | `icu_beds_adult_currently_occupied` / `icu_beds_adult_capacity` |
| `peds_icu_occ` / `peds_icu_cap` | `icu_beds_pediatric_currently_occupied` / `icu_beds_pediatric_capacity` |
| `adult_acute_occ` / `adult_acute_cap` | `acute_beds_adult_currently_occupied` / `acute_beds_adult_capacity` |
| `peds_acute_occ` / `peds_acute_cap` | `acute_beds_pediatric_currently_occupied` / `acute_beds_pediatric_capacity` |
| `neonatal_icu_occ` / `neonatal_icu_cap` | `neonatal_icu_beds_currently_occupied` / `neonatal_icu_beds_capacity` |
| `nursery_occ` / `nursery_cap` | `nursery_beds_currently_occupied` / `nursery_beds_capacity` |
| `surge_occ` / `surge_cap` | `beds_in_overflow_surge_expansion_areas_currently_occupied` / `beds_in_overflow_surge_expansion_areas_capacity` |
| `other_occ` / `other_cap` | `beds_in_other_inpatient_areas_currently_occupied` / `beds_in_other_inpatient_areas_capacity` |
| `adult_ed` | `previous_day_adult_emergency_department_visits` |
| `peds_ed` | `previous_day_pediatric_emergency_department_visits` |

Canonical fixture: `input/2025.10.21.Test.Facility.BedCapacity.csv` (+ the
`*.column-labels-only.csv` header-only sibling). **Output for this format must be
byte-equivalent to pre-feature output** apart from generated UUIDs/timestamps
(FR-002, SC-002).

---

## 2. `wahealth_dict_2026_04_30` — "2026-04-30 WA Health dictionary from KC"

- **Detection**: header contains both `facility` and `reportingday`.
- **Facility per file**: one.
- **GUID**: no → `facility_guid = None`; stable key = `slugify(facility_name)`.
- **Reporting date** (`reportingday`): ISO `YYYY-MM-DD` (parser also accepts `MM/DD/YYYY`).
- **HRD columns present**: yes (`covid_*`, `flu_*`, `rsv_*`) — **ignored**. The `all_inpatient_occ` / `all_inpatient_cap` totals are also **ignored** (aggregates are recomputed from raw per-area values).
- **Identity source**: top-level `organization` / `location` in `config.json`.
- **Note**: the schema reference file `WA-HEALTH-DataDictionary.Variable Catalog.KC.2026-04-30.csv` (header `Section,Variable Name,Data Type,Description,Notes`) is **not** a data file — it matches no detection signature and is rejected as unrecognized. A real data file in this format has the Variable Names as its header row.

| NormalizedRow field | CSV column |
|---|---|
| `facility_name` | `facility` |
| `facility_guid` | — (None) |
| `reporting_date` | `reportingday` |
| `adult_icu_occ` / `adult_icu_cap` | `adult_icu_occ` / `adult_icu_cap` |
| `peds_icu_occ` / `peds_icu_cap` | `ped_icu_occ` / `ped_icu_cap` |
| `adult_acute_occ` / `adult_acute_cap` | `adult_acute_occ` / `adult_acute_cap` |
| `peds_acute_occ` / `peds_acute_cap` | `ped_acute_occ` / `ped_acute_cap` |
| `neonatal_icu_occ` / `neonatal_icu_cap` | `neon_icu_occ` / `neon_icu_cap` |
| `nursery_occ` / `nursery_cap` | `nursery_occ` / `nursery_cap` |
| `surge_occ` / `surge_cap` | `surge_occ` / `surge_cap` |
| `other_occ` / `other_cap` | `other_occ` / `other_cap` |
| `adult_ed` | `prevd_adult_ed` |
| `peds_ed` | `prevd_ped_ed` |

Canonical fixture: `input/2026.04.30.Test.Facility.WAHealthDict.csv` — a small
synthetic data file to be created (no live sample exists yet).

---

## 3. `kc_mft_2026_05_11` — "KC multi-hospital from MFT 2026-05-11"

- **Detection**: header contains both `Facility` and `Reporting Date`.
- **Facility per file**: **many** (and many reporting dates). One Bundle per (facility, reporting date) row.
- **GUID**: no → `facility_guid = None`; stable key = `slugify(facility_name)`.
- **Reporting date** (`Reporting Date`): ISO `YYYY-MM-DD` (parser also accepts `MM/DD/YYYY`). `Created On` (ISO timestamp, e.g. `2026-04-27 13:55:02.0000000`) is **not parsed**. `Contact` (a person name) is **not used**.
- **HRD columns present**: no — bed-capacity output only.
- **Identity source**: `config.json` → `facilities[<Facility value>]` if present; otherwise a sparsely-populated Organization/Location built from the row plus a placeholder NHSN OrgID, with a WARNING (see `data-model.md` → FacilityProfile; FR-008/FR-008a).

| NormalizedRow field | CSV column |
|---|---|
| `facility_name` | `Facility` |
| `facility_guid` | — (None) |
| `reporting_date` | `Reporting Date` |
| `adult_icu_occ` / `adult_icu_cap` | `ICU Adult Occupancy` / `ICU Adult Capacity` |
| `peds_icu_occ` / `peds_icu_cap` | `ICU Pediatric Occupancy` / `ICU Pediatric Capacity` |
| `adult_acute_occ` / `adult_acute_cap` | `Acute Adult Occupancy` / `Acute Adult Capacity` |
| `peds_acute_occ` / `peds_acute_cap` | `Acute Pediatric Occupancy` / `Acute Pediatric Capacity` |
| `neonatal_icu_occ` / `neonatal_icu_cap` | `Neonatal ICU Beds Currently in Use` / `Neonatal ICU Beds Capacity` |
| `nursery_occ` / `nursery_cap` | `Nursery Current Occupancy` / `Nursery Staffed Bed Capacity` |
| `surge_occ` / `surge_cap` | `Surge Beds Currently in Use` / `Surge Beds Capacity` |
| `other_occ` / `other_cap` | `Adult Other Inpatient Beds Currently in Use` / `Adult Other Inpatient Beds Capacity` |
| `adult_ed` | `Previous Day Adult ED Visits` |
| `peds_ed` | `Previous Day Pediatric ED Visits` |

Canonical fixture: `input/census_20260511.FromKC.SubsetObfsctd.csv` (9 data rows,
already in the repo). Expected: 9 Bundles, one per row, distributed across the
distinct reporting-date subdirectories, each carrying that facility's identity
(registry entry or sparse placeholder).

---

## Error contract (FR-006, SC-004)

| Condition | Behavior |
|---|---|
| Header matches no format | Log an error naming all three `display_name`s; exit non-zero; **write no output files / directories**. |
| Header matches a format but a required mapped column is missing | Log which column is missing for which format; exit non-zero; write no output. |
| Recognized format, header row only, no data rows | Same as today's `*column-labels-only*` handling: recognized, no Bundles produced, no error. |
| Empty file | Error ("CSV file contains no data rows"), exit non-zero — unchanged. |

A recognized format **never** produces a Bundle whose counts are zero merely
because column names didn't line up — that situation is a detection/mapping error
and must fail loudly.
