# Contract: `config.json` and CLI invocation

## CLI invocation (unchanged)

```
python3 convert.py <input.csv> [--config config.json] [--output-dir ./output] [--fhir-server URL]
```

No new flags. The input format is auto-detected from the CSV header (see
`contracts/input-formats.md`); behavior on an unrecognized header is a non-zero
exit with no output written.

## `config.json` schema

Required and previously-existing sections are unchanged:

```jsonc
{
  "organization": {            // REQUIRED — the submitting hospital for single-facility files
    "nhsn_org_id": "...",
    "name": "...",
    "phone": "+1-555-000-0000",
    "address": { "line": ["..."], "city": "...", "state": "WA", "postalCode": "...", "country": "USA" }
  },
  "location": {                // REQUIRED — that hospital's reporting Location
    "identifier_system": "http://example.org/fhir/location-identifier",
    "identifier_value": "FACILITY-ID",
    "name": "...",
    "description": "..."
  },
  "software": {                // REQUIRED — the Device resource for this tool
    "name": "safr-csv-fhir",
    "version": "1.0.0",
    "identifier_system": "http://example.org/fhir/device-identifier",
    "identifier_value": "safr-csv-fhir"
  },

  "facilities": {              // NEW, OPTIONAL — per-facility identity for multi-facility files
    "Seaside Medical Center": {
      "organization": { "nhsn_org_id": "...", "name": "Seaside Medical Center",
                        "phone": "...", "address": { "line": ["..."], "city": "...",
                        "state": "WA", "postalCode": "...", "country": "USA" } },
      "location":     { "identifier_system": "...", "identifier_value": "...",
                        "name": "Seaside Medical Center", "description": "..." }
    }
    // ... key = the exact `Facility` string from the CSV; one entry per known facility
  },

  "server": {                  // OPTIONAL — FHIR server persistence; omit to skip
    "base_url": "", "token_endpoint": "", "client_id": "", "client_secret": ""
  }
}
```

### Validation rules (`load_config`)

- `organization`, `location`, `software` — required; missing → clear error, exit non-zero (unchanged).
- `facilities` — optional. If present: must be an object; every value must contain non-empty `organization` and `location` objects (same shapes as the top-level ones). A malformed entry → clear error, exit non-zero.
- A missing `facilities` section, or no entry for a facility named in a multi-facility CSV, is **not** an error: that row's Organization/Location are built sparsely from the CSV plus a placeholder NHSN OrgID, and a WARNING is logged once per such facility.

### Identity-resolution behavior by format

| Format | Identity source |
|---|---|
| `original`, `wahealth_dict_2026_04_30` (single-facility) | Top-level `organization` / `location`. (The CSV facility name affects only the output filename, as today.) |
| `kc_mft_2026_05_11` (multi-facility), facility in `facilities` | That entry's `organization` / `location`. |
| `kc_mft_2026_05_11`, facility not in `facilities` (or no `facilities`) | Sparse Organization/Location from the CSV row; `Organization.identifier = [{system: "urn:wahealth:csv-to-safr:unregistered-facility", value: slugify(Facility)}]`; the top-level `organization`/`location` are **not** used as a fallback. WARNING logged. Bundle still validates (FR-008a). |

`config.example.json` is updated to include a `facilities` example that covers a
subset of the `census_20260511.FromKC.SubsetObfsctd.csv` facilities; the remaining
facilities in that fixture deliberately exercise the sparse path under CI.
