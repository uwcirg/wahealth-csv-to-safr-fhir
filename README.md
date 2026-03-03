# wahealth-csv-to-safr-fhir

Converts WA Health hospital bed capacity CSVs to FHIR R4 **SAFR Bed Capacity MeasureReport Bundles**.

Requires Python 3 (stdlib only — no pip install needed).

## Quick start

```bash
# 1. Create your config
cp config.example.json config.json
# Edit config.json with your hospital's NHSN Org ID, name, address, phone,
# location, and (optionally) FHIR server credentials.

# 2. Run the converter
python3 convert.py input.csv
```

## Usage

```
python3 convert.py input.csv [--config config.json] [--output-dir ./output] [--fhir-server URL]
```

| Flag | Default | Description |
|---|---|---|
| `csv_file` | *(required)* | Path to the input CSV file |
| `--config` | `config.json` | Path to configuration file |
| `--output-dir` | `./output` | Directory for generated JSON files |
| `--fhir-server` | *(none)* | FHIR server base URL (e.g. `http://localhost:8080/fhir`) |

## Output

For each CSV row the script produces:

- **Bundle** — `{output-dir}/{date}/{facility_name}.{date}.BedCapacity.json`
- **Individual resources** — `Organization.json`, `Device.json`, `MeasureReport.json`, `Location.json` in the same date subdirectory (useful for debugging)

Output is organized into per-date subdirectories under `--output-dir`.

## FHIR server persistence

With `--fhir-server` (or `server.base_url` in config), the script also persists resources directly to a FHIR server using **upsert semantics** (create on first run, update on subsequent runs). Resources persisted:

- Organization (by NHSN identifier)
- Location (by facility identifier)
- Device (by software identifier)
- MeasureReport (by measure + subject + date)
- Bundle (by deterministic UUID derived from facility GUID + date)

Organization, Location, and Device are upserted once and reused across all rows in a run.

### Authentication

If `server.token_endpoint`, `server.client_id`, and `server.client_secret` are set in `config.json`, the script performs an OAuth2 client-credentials grant to obtain a Bearer token before making FHIR requests.

## Configuration

Copy `config.example.json` to `config.json` and fill in:

```jsonc
{
  "organization": {
    "nhsn_org_id": "YOUR_NHSN_ORG_ID",
    "name": "Your Hospital Name",
    "phone": "+1-555-000-0000",
    "address": { "line": [...], "city": "...", "state": "WA", "postalCode": "...", "country": "USA" }
  },
  "location": {
    "identifier_system": "http://example.org/fhir/location-identifier",
    "identifier_value": "FACILITY-ID",
    "name": "Your Hospital Main Campus",
    "description": "Main hospital campus"
  },
  "software": {
    "name": "safr-csv-fhir",
    "version": "1.0.0",
    "identifier_system": "http://example.org/fhir/device-identifier",
    "identifier_value": "safr-csv-fhir"
  },
  "server": {           // optional — omit or leave empty to skip server persistence
    "base_url": "",
    "token_endpoint": "",
    "client_id": "",
    "client_secret": ""
  }
}
```

## Logging

Each run creates a timestamped log file in the `log/` directory (`convert_YYYYMMDD_HHMMSS.log`). The same output is mirrored to the console. Logs capture file generation events and FHIR server interactions (successes and errors) for post-run review.

## FHIR profiles used

| Resource | Profile |
|---|---|
| Bundle | `us-safr-measurereport-bundle` |
| MeasureReport | `indv-measurereport-deqm` (DEQM) |
| Organization | `us-safr-submitting-organization`, `qicore-organization` |
| Location | `qicore-location` |
| Device | `crmi-softwaresystemdevice` |

## CSV columns processed

The script reads bed capacity and ED visit columns from the WA Health CSV format. HRD / respiratory disease counts (COVID, influenza, RSV) are present in the CSV but are **not** processed by this tool.

**Bed types:** ICU (adult, pediatric), Acute/Non-ICU (adult, pediatric), NICU, Nursery, Surge/Overflow, Other Inpatient

**ED visits:** Adult and Pediatric emergency department visits

**Computed aggregates:** AllBeds, AdultTotal, PedsTotal, SpecialtyTotal (each with occupied + unoccupied counts)
