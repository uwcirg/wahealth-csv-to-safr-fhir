# Planning Conversation: CSV to FHIR R4 SAFR Bed Capacity MeasureReport Converter

## Initial Prompt (User)

> I want you to write a script to convert a CSV file to a FHIR R4 MeasureReport, compliant with the Bed Capacity Profile (https://build.fhir.org/ig/HL7/us-safr/StructureDefinition-us-safr-measurereport-bundle.html) in the SAFR IG (https://build.fhir.org/ig/HL7/us-safr).
> The CSV file is in a format designed by a state department of health ("DOH"); hospitals throughout the state (~100) use this format to send hospital bed occupancy information to the DOH.
> The script that you write will be run at these hospitals. Instead of sending the CSV to DOH, they will send the FHIR MeasureReport(s) to the DOH FHIR server. The DOH FHIR server will validate the MeasureReport against the Profile and reject submissions that don't comply with it.
> The script will need to be runnable on a variety of systems, mostly on data manager's workstations. I don't know what the workstations' configurations are, nor the data managers' skills, so make it easy to run.
> The script only needs to do the conversion, not submit the MeasureReport to the DOH FHIR server.
> There is a sample CSV file in this directory.

Plan mode was enabled.

---

## Research Phase

### CSV File Analysis

The sample CSV file (`2025.10.21.Test.Facility.BedCapacity.csv`) contains 57 columns with 2 data rows. Key column categories:

**Facility Identification:**
- `facility_guid` — unique facility identifier
- `facility_name` — hospital name
- `reporting_date` — date in MM/DD/YYYY format

**Bed Capacity (8 bed types × 2 metrics = 16 columns):**
Each bed type has `_currently_occupied` and `_capacity` columns:
- `icu_beds_adult`
- `icu_beds_pediatric`
- `acute_beds_adult`
- `acute_beds_pediatric`
- `neonatal_icu_beds`
- `nursery_beds`
- `beds_in_overflow_surge_expansion_areas`
- `beds_in_other_inpatient_areas`

**ED Visits (2 columns):**
- `previous_day_adult_emergency_department_visits`
- `previous_day_pediatric_emergency_department_visits`

**Disease Surveillance (~35 columns):**
- COVID-19: hospitalized (adult/pediatric), ICU (adult/pediatric), admissions by age group
- Influenza: hospitalized (adult/pediatric), ICU (adult/pediatric), admissions by age group
- RSV: hospitalized (adult/pediatric), ICU (adult/pediatric), admissions by age group

### SAFR IG Profile Research

#### Bundle Profile (`us-safr-measurereport-bundle`)

- **URL:** `http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-measurereport-bundle`
- **Version:** 1.0.0, Trial-use (Maturity Level 1)
- **Bundle type:** Fixed value `collection`
- **Entries:** 2..* (sliced, unordered, open)
- **Purpose:** Valid submission bundle to NHSN, federal and jurisdictional Public Health Agencies

**Required Entry Slices:**

| Slice | Cardinality | Profile |
|---|---|---|
| `submitting-organization` | 1..* | `us-safr-submitting-organization` (Organization) |
| `submitting-device` | 0..* | `crmi-softwaresystemdevice` (Device) |
| `measurereport` | 1..* | `DEQMIndividualMeasureReportProfile` (MeasureReport) |

**Key Constraints:**
- `bundle-contain-all-references` (error): All referenced resources SHALL be contained within the Bundle
- `bundle-no-modifier-extensions` (error): Must not contain any modifierExtensions
- `bdl-8` (error): fullUrl cannot contain `/_history/`

#### MeasureReport Structure (from example `Bundle-HospitalBedCapacityReportBundle.json`)

The MeasureReport uses `DEQMIndividualMeasureReportProfile` with:
- **status:** `complete`
- **type:** `individual`
- **measure:** `http://hl7.org/fhir/us/safr/Measure/BedCapacityMeasure|1.0.0-ballot`
- **subject:** Reference to Location entry
- **reporter:** Reference to Organization entry
- **period:** Full day (start T00:00:00, end T23:59:59)
- **improvementNotation:** `increase`
- **Extensions:**
  - `extension-measureScoring` = `continuous-variable`
  - `extension-dataLocation` = Reference to Location

**Group structure — each group has:**
```json
{
  "id": "{Code}-bed-capacity-group",
  "code": {
    "coding": [{
      "system": "http://hl7.org/fhir/us/safr/CodeSystem/us-safr-bed-capacity-example-codes",
      "code": "{Code}",
      "display": "{Display}"
    }]
  },
  "population": [{
    "id": "{Code}-initial-population",
    "code": {
      "coding": [{
        "system": "http://terminology.hl7.org/CodeSystem/measure-population",
        "code": "initial-population",
        "display": "Initial Population"
      }]
    },
    "count": {value}
  }]
}
```

#### Supporting Resources in the Bundle

**Organization (entry[0]):**
- Profile: `us-safr-submitting-organization`
- identifier: NHSN OrgID (`https://www.cdc.gov/nhsn/OrgID`)
- type: Healthcare Provider (`prov`)
- name, telecom, address

**Device (entry[1]):**
- Profile: `crmi-softwaresystemdevice|1.0.0`
- manufacturer, deviceName, type (`tooling`), version

**Location (entry[3]):**
- Profile: `qicore-location`
- identifier, status (`active`), name, description
- type: Hospital (`HOSP` from `v3-RoleCode`)
- physicalType: Building (`bu`)
- managingOrganization: Reference to Organization

#### Bed Capacity Code System (`us-safr-bed-capacity-example-codes`)

167 total codes. Key codes relevant to the CSV mapping:

**All Beds:**
- `AllBedsOccupied` — "All Beds Census"
- `AllBedsUnoccupied` — "All Beds Unoccupied"

**Adult Total:**
- `AdultTotalOccupied` — "Adult Total Census"
- `AdultTotalUnoccupied` — "Adult Total Unoccupied"

**Adult ICU:**
- `AdultICUOccupied` — "Adult ICU Census"
- `AdultICUUnoccupied` — "Adult ICU Unoccupied"

**Adult Non-ICU:**
- `AdultNonICUOccupied` — "Adult Non-ICU Census" (covers PCU + MT/MS + OBS)
- `AdultNonICUUnoccupied` — "Adult Non-ICU Unoccupied"

**Pediatric Total:**
- `PedsTotalOccupied` — "Peds Total Census"
- `PedsTotalUnoccupied` — "Peds Total Unoccupied"

**Pediatric ICU:**
- `PedsICUOccupied` — "Peds ICU Census"
- `PedsICUUnoccupied` — "Peds ICU Unoccupied"

**Pediatric Non-ICU:**
- `PedsNonICUOccupied` — "Peds Non-ICU Census"
- `PedsNonICUUnoccupied` — "Peds Non-ICU Unoccupied"

**NICU:**
- `NICUOccupied` — "Specialty NICU Census"
- `NICUUnoccupied` — "Specialty NICU Unoccupied"

**Nursery:**
- `NurseryOccupied` — "Specialty Nursery Census"
- `NurseryUnoccupied` — "Specialty Nursery Unoccupied"

**Surge:**
- `SurgeActiveTotalOccupied` — "Surge Total Active Census"
- `SurgeActiveTotalUnoccupied` — "Surge Total Active Unoccupied"

**Specialty Total:**
- `SpecialtyTotalOccupied` — "Specialty Total Census"
- `SpecialtyTotalUnoccupied` — "Specialty Total Unoccupied"

**Emergency Department:**
- `AdultEDCensus` — "Adult ED Total Census"
- `PedsEDCensus` — "Peds ED Census"
- `TotalEDCensus` — "Total ED Census"

---

## Clarifying Questions & Answers

### Q1: Acute beds mapping
**Question:** The CSV has 'acute beds' (adult/pediatric) which could map to different SAFR granularity levels. The SAFR codes distinguish AdultNonICU (broad: PCU+MT/MS+OBS), AdultMTMS (med/surg only), AdultPCU (step-down), and AdultObs (observation). Which mapping is correct for the DOH's 'acute beds'?

**Answer:** AdultNonICU / PedsNonICU (Recommended) — Map acute_beds_adult to AdultNonICU (the broad non-ICU category covering PCU + MT/MS + OBS combined). This is the safest mapping when the source data isn't broken down further.

### Q2: Other inpatient beds
**Question:** The CSV has 'beds_in_other_inpatient_areas' (occupied/capacity). There's no obvious direct SAFR equivalent. How should these be handled?

**Answer:** Include in AllBeds totals only (Recommended) — Include in computed aggregate AllBedsOccupied/Unoccupied totals but don't create a separate group for them, since there's no matching SAFR code.

### Q3: Organization/Location details
**Question:** The CSV only has facility_guid and facility_name, but the SAFR Bundle needs a full Organization (with NHSN OrgID, address, phone) and Location. Where should this data come from?

**Answer:** Config file (Recommended) — A separate JSON config file per hospital with organization details (NHSN OrgID, address, phone, NPI). Each hospital sets this up once.

### Q4: Scope (disease data)
**Question:** The CSV contains COVID/Influenza/RSV surveillance data (35 columns) which belong to the HRD Measure, not the Bed Capacity Measure. Should the script handle only bed capacity, or also generate an HRD MeasureReport?

**Answer:** Bed Capacity only (Recommended) — Only convert the bed capacity and ED visit columns. Ignore COVID/Influenza/RSV columns. This matches the stated requirement.

---

## Implementation Plan

### Approach: Single Python Script, No Dependencies

**Language:** Python 3 (stdlib only — `csv`, `json`, `uuid`, `argparse`, `datetime`)
- Pre-installed on macOS/Linux; widely available on Windows
- Zero `pip install` needed
- Single file: `convert.py`

**Configuration:** A `config.json` file per hospital for Organization/Location details not in the CSV (NHSN OrgID, address, phone, NPI). Created once per hospital.

### CSV → SAFR Code Mapping

Each CSV bed type has `_currently_occupied` and `_capacity` columns. SAFR uses `Occupied` (census) and `Unoccupied` (= capacity − occupied) pairs.

#### Direct Mappings

| CSV Prefix | SAFR Occupied Code | SAFR Unoccupied Code |
|---|---|---|
| `icu_beds_adult` | `AdultICUOccupied` | `AdultICUUnoccupied` |
| `icu_beds_pediatric` | `PedsICUOccupied` | `PedsICUUnoccupied` |
| `acute_beds_adult` | `AdultNonICUOccupied` | `AdultNonICUUnoccupied` |
| `acute_beds_pediatric` | `PedsNonICUOccupied` | `PedsNonICUUnoccupied` |
| `neonatal_icu_beds` | `NICUOccupied` | `NICUUnoccupied` |
| `nursery_beds` | `NurseryOccupied` | `NurseryUnoccupied` |
| `beds_in_overflow_surge_expansion_areas` | `SurgeActiveTotalOccupied` | `SurgeActiveTotalUnoccupied` |

#### ED Mappings

| CSV Column | SAFR Code |
|---|---|
| `previous_day_adult_emergency_department_visits` | `AdultEDCensus` |
| `previous_day_pediatric_emergency_department_visits` | `PedsEDCensus` |
| Computed: adult + pediatric | `TotalEDCensus` |

#### Computed Aggregates

| SAFR Code | Formula |
|---|---|
| `AllBedsOccupied` | Sum of ALL 8 occupied columns (including `other_inpatient`) |
| `AllBedsUnoccupied` | Sum of ALL 8 (capacity − occupied) |
| `AdultTotalOccupied` | `icu_adult_occ` + `acute_adult_occ` |
| `AdultTotalUnoccupied` | `(icu_adult_cap − occ)` + `(acute_adult_cap − occ)` |
| `PedsTotalOccupied` | `icu_peds_occ` + `acute_peds_occ` |
| `PedsTotalUnoccupied` | `(icu_peds_cap − occ)` + `(acute_peds_cap − occ)` |
| `SpecialtyTotalOccupied` | `neonatal_occ` + `nursery_occ` |
| `SpecialtyTotalUnoccupied` | `(neonatal_cap − occ)` + `(nursery_cap − occ)` |

**Note:** `beds_in_other_inpatient_areas` is included only in `AllBeds*` aggregates (no direct SAFR sub-category code).

#### Columns NOT Mapped (out of scope)
- All COVID/Influenza/RSV surveillance columns (35 columns) — these belong to the HRD Measure

### Output FHIR Bundle Structure

Per the SAFR profile `us-safr-measurereport-bundle`, each output is a `collection` Bundle:

```
Bundle (type: "collection")
├── entry[0]: Organization (us-safr-submitting-organization)
│   - identifier: NHSN OrgID from config.json
│   - name, address, phone from config.json
├── entry[1]: Device (crmi-softwaresystemdevice)
│   - Identifies this converter script as the submitting software
├── entry[2]: MeasureReport (DEQM Individual MeasureReport)
│   - status: "complete"
│   - type: "individual"
│   - measure: "http://hl7.org/fhir/us/safr/Measure/BedCapacityMeasure|1.0.0-ballot"
│   - subject: Reference to Location entry
│   - reporter: Reference to Organization entry
│   - period: reporting_date (full day)
│   - extension: measureScoring = "continuous-variable"
│   - extension: dataLocation = Reference to Location
│   - improvementNotation: "increase"
│   - group[]: One group per SAFR code (see mapping above)
│       - code: from us-safr-bed-capacity-example-codes
│       - population[0]: code = "initial-population", count = value
└── entry[3]: Location (qicore-location)
    - identifier, name, type from config.json
    - type: HOSP
    - managingOrganization: Reference to Organization
```

One Bundle JSON file per CSV row (each row = one facility + one reporting date).

### Files to Create

#### 1. `convert.py` — Main script (~300-400 lines)

```
Usage: python3 convert.py input.csv [--config config.json] [--output-dir ./output]
```

**Structure:**
- `load_config(path)` — read and validate config.json
- `parse_csv(path)` — read CSV, return list of row dicts
- `build_group(code, display, count)` — create one MeasureReport group
- `build_measure_report(row, config, uuids)` — create MeasureReport with all groups
- `build_bundle(row, config)` — assemble full Bundle
- `main()` — CLI entry point, iterate rows, write output files

**Output files named:** `{facility_name}.{reporting_date}.BedCapacity.json`

#### 2. `config.example.json` — Template for hospitals to fill in

```json
{
  "organization": {
    "nhsn_org_id": "YOUR_NHSN_ORG_ID",
    "name": "Your Hospital Name",
    "phone": "+1-555-000-0000",
    "address": {
      "line": ["123 Main Street"],
      "city": "City",
      "state": "ST",
      "postalCode": "00000",
      "country": "USA"
    }
  },
  "location": {
    "identifier_system": "http://example.org/fhir/location-identifier",
    "identifier_value": "FACILITY-ID",
    "name": "Your Hospital Main Campus",
    "description": "Main hospital campus"
  },
  "software": {
    "name": "safr-csv-fhir",
    "version": "1.0.0"
  }
}
```

### Key Implementation Details

- **UUIDs**: Generate `urn:uuid:` fullUrls for each Bundle entry; use consistent references within the Bundle
- **Date handling**: Parse CSV `MM/DD/YYYY` → FHIR `YYYY-MM-DD` with timezone; period spans full day
- **Unoccupied calculation**: `capacity − occupied`; clamp to 0 if negative (data quality issue)
- **Profile URLs**:
  - Bundle: `http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-measurereport-bundle`
  - MeasureReport: `http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/indv-measurereport-deqm`
  - Organization: `http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-submitting-organization`
  - Location: `http://hl7.org/fhir/us/qicore/StructureDefinition/qicore-location`
  - Device: `http://hl7.org/fhir/uv/crmi/StructureDefinition/crmi-softwaresystemdevice|1.0.0`
- **Code system**: `http://hl7.org/fhir/us/safr/CodeSystem/us-safr-bed-capacity-example-codes`
- **Population code system**: `http://terminology.hl7.org/CodeSystem/measure-population`
- **All references must be internal** (urn:uuid within the Bundle)
- **No modifier extensions** anywhere in the Bundle

### Verification

1. Run `python3 convert.py 2025.10.21.Test.Facility.BedCapacity.csv --config config.example.json` — should produce 2 JSON files (one per CSV row)
2. Validate each output JSON is well-formed: `python3 -m json.tool output/*.json`
3. Spot-check values: e.g., row 1 has `icu_beds_adult_currently_occupied=4, capacity=3` → `AdultICUOccupied` count=4, `AdultICUUnoccupied` count=0 (clamped from -1)
4. Verify Bundle structure matches the example at `Bundle-HospitalBedCapacityReportBundle.json`
5. Validate against SAFR profile using the FHIR Validator if possible
