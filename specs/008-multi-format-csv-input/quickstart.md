# Quickstart: Multi-format CSV conversion

What changes for users once this feature lands. (Implementation reference for
developers; this is also the basis for the README update required by FR-013.)

## Converting a file — same command, three accepted layouts

```bash
python3 convert.py <input.csv> --config config.json --output-dir ./output
```

The converter inspects the CSV header and picks the matching layout automatically:

| If the header has… | …it's treated as | Notes |
|---|---|---|
| `facility_guid` + `reporting_date` | Original WA Health format | one facility per file; ~35 HRD columns ignored |
| `facility` + `reportingday` | "2026-04-30 WA Health dictionary from KC" | one facility per file; `covid_*`/`flu_*`/`rsv_*` and `all_inpatient_*` columns ignored |
| `Facility` + `Reporting Date` | "KC multi-hospital from MFT 2026-05-11" | **many** facilities/dates per file; one Bundle per (facility, date) row |

If the header matches none of these, the converter prints an error listing the
supported formats and exits without writing anything — e.g. feeding it
`WA-HEALTH-DataDictionary.Variable Catalog.KC.2026-04-30.csv` (that's the *schema*
document, not data).

Output is unchanged in shape: `output/<YYYY-MM-DD>/<facility_name>.<YYYY-MM-DD>.BedCapacity.json`
plus the per-resource debug files, one Bundle per data row.

```bash
# Convert the King County multi-hospital sample → 9 Bundles across several date dirs
python3 convert.py input/census_20260511.FromKC.SubsetObfsctd.csv \
  --config config.json --output-dir ./output
```

## Multi-hospital files: the `facilities` registry

A multi-hospital census file (the MFT format) has only facility *names* — not NHSN
OrgIDs or addresses. Provide those in `config.json` under a new optional
`facilities` map, keyed by the exact `Facility` string:

```jsonc
{
  "organization": { … },   // still used for single-facility files
  "location":     { … },
  "software":     { … },
  "facilities": {
    "Seaside Medical Center": {
      "organization": { "nhsn_org_id": "10001", "name": "Seaside Medical Center",
                        "phone": "+1-555-0100",
                        "address": { "line": ["1 Ocean Ave"], "city": "Seaside",
                                     "state": "WA", "postalCode": "98000", "country": "USA" } },
      "location":     { "identifier_system": "http://example.org/fhir/location-identifier",
                        "identifier_value": "SEASIDE-MAIN",
                        "name": "Seaside Medical Center", "description": "Main campus" }
    }
  }
}
```

- Facility **in** the registry → its Bundle gets the full Organization/Location from that entry.
- Facility **not** in the registry (or no `facilities` section at all) → the converter still produces the Bundle, but with a **sparsely-populated** Organization/Location built from the CSV row, and an Organization identifier that is a deterministic *placeholder*:
  `{"system": "urn:wahealth:csv-to-safr:unregistered-facility", "value": "<slugified-facility-name>"}`.
  You'll see a warning like:
  ```
  WARNING Facility 'Nordic Issaquah' not in config 'facilities' registry; emitting
          sparsely-populated Organization/Location with a placeholder identifier
          (urn:wahealth:csv-to-safr:unregistered-facility|nordic-issaquah)
  ```
  These Bundles still pass FHIR validation — they're structurally valid, just
  under-populated. Add a `facilities` entry to fill them in. The top-level
  `organization`/`location` are **not** borrowed for unregistered facilities.

Single-facility formats (original, dictionary) are unaffected: they keep using the
top-level `organization`/`location`, and the CSV facility name still only drives
the output filename.

## Validation (developers — mandatory per CLAUDE.md / constitution)

Run the four-step pipeline against **all** `input/*.csv` fixtures (the loop now
covers the new format fixtures too; `*column-labels-only*` files are still skipped):

```bash
# 1. convert every fixture
for csv in input/*.csv; do
  case "$csv" in *column-labels-only*) continue ;; esac
  echo "Converting: $csv"
  python3 convert.py "$csv" --config config.example.json --output-dir output
done

# 2. extract IG versions
SAFR_IG_VERSION=$(grep -oP '^SAFR_IG_VERSION\s*=\s*"\K[^"]+' convert.py)
NHSN_SAFR_IG_VERSION=$(grep -oP 'NHSN_SAFR_IG_VERSION\s*=\s*"\K[^"]+' convert.py)

# 3. validate all generated Bundles
java -jar validator_cli.jar output/**/*.json \
  -version 4.0.1 \
  -ig hl7.fhir.us.safr#$SAFR_IG_VERSION \
  -ig https://safr-ci.nhsnlink.org/package.tgz

# 4. zero errors not matching the patterns in known-validation-issues.md
```

`config.example.json` registers a subset of the census fixture's facilities, so the
pipeline exercises both the registry path and the sparse-placeholder path — both
must yield zero project-introduced validator errors. Also run `python3 -m unittest
discover tests` (covers `compute_groups`, format detection, and the per-format
parsers) and `ruff check convert.py`.
