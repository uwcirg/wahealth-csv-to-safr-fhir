# wahealth-csv-to-safr-fhir
Utilities for converting WA Health CSVs to FHIR R4 SAFR Bed Capacity MeasureReport Bundles.

Usage:
```
    python3 convert.py input.csv [--config config.json] [--output-dir ./output]
```
Before first use, copy config.example.json to config.json and fill in your
hospital's NHSN Org ID, name, address, phone, and location details.

Outputs one JSON Bundle per CSV row to the output directory, named:
    `{facility_name}.{reporting_date}.BedCapacity.json`

Requires Python 3 (stdlib only — no pip install needed).
