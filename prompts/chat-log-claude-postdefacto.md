# CSV to FHIR SAFR Bed Capacity Converter — Development Chat Log

## 1. Implementation

Implemented the plan to create a CSV-to-FHIR converter for the US SAFR Bed Capacity MeasureReport profile.

### Files Created

- **`convert.py`** — Main converter script (~300 lines, Python 3 stdlib only)
- **`config.example.json`** — Template config for hospital-specific data (NHSN Org ID, name, address, phone, location)

### Usage

```
python3 convert.py input.csv [--config config.json] [--output-dir ./output]
```

### Output

One FHIR R4 `collection` Bundle JSON per CSV row, containing:
- Organization (us-safr-submitting-organization)
- Device (crmi-softwaresystemdevice)
- MeasureReport (indv-measurereport-deqm) with 25 groups
- Location (qicore-location)

### CSV-to-SAFR Mapping

**Direct mappings** (7 bed types x occupied/unoccupied pairs = 14 groups):
- `icu_beds_adult` → AdultICUOccupied / AdultICUUnoccupied
- `icu_beds_pediatric` → PedsICUOccupied / PedsICUUnoccupied
- `acute_beds_adult` → AdultNonICUOccupied / AdultNonICUUnoccupied
- `acute_beds_pediatric` → PedsNonICUOccupied / PedsNonICUUnoccupied
- `neonatal_icu_beds` → NICUOccupied / NICUUnoccupied
- `nursery_beds` → NurseryOccupied / NurseryUnoccupied
- `beds_in_overflow_surge_expansion_areas` → SurgeActiveTotalOccupied / SurgeActiveTotalUnoccupied

**ED mappings** (3 groups):
- AdultEDCensus, PedsEDCensus, TotalEDCensus (computed: adult + peds)

**Computed aggregates** (8 groups):
- AllBedsOccupied/Unoccupied (all 8 bed types including other_inpatient)
- AdultTotalOccupied/Unoccupied (icu_adult + acute_adult)
- PedsTotalOccupied/Unoccupied (icu_peds + acute_peds)
- SpecialtyTotalOccupied/Unoccupied (neonatal + nursery)

### Initial Test

Ran against `2025.10.21.Test.Facility.BedCapacity.csv` — produced 2 JSON files (one per row). Verified:
- JSON well-formed
- AdultICUOccupied=4, AdultICUUnoccupied=0 (clamped from -1, since occupied=4 > capacity=3)
- AllBedsOccupied=65, AllBedsUnoccupied=2
- All internal urn:uuid references consistent

---

## 2. FHIR Validation

### Aidbox Validation (1.0.0-ballot)

First attempt using Aidbox with SAFR IG 1.0.0-ballot loaded reported:

```
Invalid slice cardinality: entry[0].resource.identifier
us-safr-submitting-organization: Invalid slice cardinality 'nhsn_org_id'.
Current count is '0', expected between '1' and '1'.
```

Investigation: Downloaded the 1.0.0-ballot FHIR package from `packages.simplifier.net` and compared the StructureDefinition. The `nhsn_org_id` slice uses `patternIdentifier: { "system": "https://www.cdc.gov/nhsn/OrgID" }` — our output has exactly that system. The IG's own example Organization is structurally identical to ours.

**Conclusion:** Aidbox-specific issue with `pattern`-type slice discriminator on `$this`.

### HL7 FHIR Validator (reference implementation)

Downloaded `validator_cli.jar` v6.8.0 and validated against `hl7.fhir.us.safr#1.0.0-ballot`.

**First run — 5 errors found:**

1. `period.start` / `period.end`: "If a date has a time, it must have a timezone" — **Fixed** by adding `+00:00`
2. `Location.identifier.system`: "Example URLs are not allowed" — Expected (template config)
3. Location reference: "Unable to find profile match for qicore-location" — Cascading from #2
4. `Bundle.entry:measurereport` slice not matched — **IG bug in 1.0.0-ballot** (Bundle profile references `summary-measurereport-deqm` instead of `indv-measurereport-deqm`; fixed in CI build)

**After timezone fix — 3 errors remaining:**
- 2 from template `config.example.json` placeholder values (disappear with real config)
- 1 from the IG bug (summary vs individual MeasureReport profile in Bundle slice)

No identifier slice errors — confirming the Aidbox issue was a false positive.

### Aidbox Validation (CI build)

User switched Aidbox to the CI build of the SAFR IG. The only remaining issue was the same `nhsn_org_id` identifier slice cardinality false positive.

### Aidbox False Positive Details

For reporting to Aidbox support:
- **Profile:** `us-safr-submitting-organization` (extends `us-core-organization`)
- **Element:** `Organization.identifier`
- **Slice:** `nhsn_org_id` — discriminator `{"type": "pattern", "path": "$this"}`, `patternIdentifier: {"system": "https://www.cdc.gov/nhsn/OrgID"}`
- **Behavior:** Aidbox reports count 0 despite identifier with matching system being present
- **HL7 FHIR Validator 6.8.0:** Passes without error

---

## 3. Code Fix Summary

Only one code change was needed after initial implementation:

**Period timezone** (`convert.py`): Changed period start/end from `2025-10-20T00:00:00` to `2025-10-20T00:00:00+00:00` — FHIR requires timezone when time component is present.

---

## 4. Known Issues

| Issue | Type | Status |
|---|---|---|
| Aidbox nhsn_org_id slice false positive | Aidbox validator bug | Cannot fix; safe to ignore |
| 1.0.0-ballot Bundle references summary-measurereport-deqm | IG bug | Fixed in CI build; awaiting next published version |
| dom-6 narrative warnings | Best practice | Optional; not required by profile |
| Measure canonical not resolvable | IG packaging | Measure resource not included in IG package |
