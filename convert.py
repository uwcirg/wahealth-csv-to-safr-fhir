#!/usr/bin/env python3
"""Convert hospital bed capacity CSV to FHIR R4 SAFR Bed Capacity MeasureReport Bundles.

Usage:
    python3 convert.py input.csv [--config config.json] [--output-dir ./output]

Before first use, copy config.example.json to config.json and fill in your
hospital's NHSN Org ID, name, address, phone, and location details.

Outputs one JSON Bundle per CSV row to the output directory, named:
    {facility_name}.{reporting_date}.BedCapacity.json

Requires Python 3 (stdlib only — no pip install needed).
"""

import argparse
import csv
import json
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta


# --- Constants ---

BUNDLE_PROFILE = "http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-measurereport-bundle"
MEASUREREPORT_PROFILE = "http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/indv-measurereport-deqm"
ORG_PROFILE = "http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-submitting-organization"
LOCATION_PROFILE = "http://hl7.org/fhir/us/qicore/StructureDefinition/qicore-location"
DEVICE_PROFILE = "http://hl7.org/fhir/uv/crmi/StructureDefinition/crmi-softwaresystemdevice|1.0.0"

BED_CODE_SYSTEM = "http://hl7.org/fhir/us/safr/CodeSystem/us-safr-bed-capacity-example-codes"
MEASURE_POP_SYSTEM = "http://terminology.hl7.org/CodeSystem/measure-population"
MEASURE_SCORING_SYSTEM = "http://terminology.hl7.org/CodeSystem/measure-scoring"
IMPROVEMENT_SYSTEM = "http://terminology.hl7.org/CodeSystem/measure-improvement-notation"
ORG_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/organization-type"
ROLE_CODE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-RoleCode"
PHYSICAL_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/location-physical-type"
SOFTWARE_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/software-system-type-codes"
NHSN_SYSTEM = "https://www.cdc.gov/nhsn/OrgID"

MEASURE_URL = "http://hl7.org/fhir/us/safr/Measure/BedCapacityMeasure|1.0.0-ballot"

MEASURE_SCORING_EXT = "http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/extension-measureScoring"
DATA_LOCATION_EXT = "http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/extension-dataLocation"

# Direct bed type mappings: (csv_prefix, occupied_code, occupied_display, unoccupied_code, unoccupied_display)
BED_MAPPINGS = [
    ("icu_beds_adult", "AdultICUOccupied", "Adult ICU Census", "AdultICUUnoccupied", "Adult ICU Unoccupied"),
    ("icu_beds_pediatric", "PedsICUOccupied", "Peds ICU Census", "PedsICUUnoccupied", "Peds ICU Unoccupied"),
    ("acute_beds_adult", "AdultNonICUOccupied", "Adult Non-ICU Census", "AdultNonICUUnoccupied", "Adult Non-ICU Unoccupied"),
    ("acute_beds_pediatric", "PedsNonICUOccupied", "Peds Non-ICU Census", "PedsNonICUUnoccupied", "Peds Non-ICU Unoccupied"),
    ("neonatal_icu_beds", "NICUOccupied", "Specialty NICU Census", "NICUUnoccupied", "Specialty NICU Unoccupied"),
    ("nursery_beds", "NurseryOccupied", "Specialty Nursery Census", "NurseryUnoccupied", "Specialty Nursery Unoccupied"),
    ("beds_in_overflow_surge_expansion_areas", "SurgeActiveTotalOccupied", "Surge Total Active Census", "SurgeActiveTotalUnoccupied", "Surge Total Active Unoccupied"),
]

# All 8 bed prefixes (including other_inpatient for AllBeds totals)
ALL_BED_PREFIXES = [
    "icu_beds_adult",
    "icu_beds_pediatric",
    "acute_beds_adult",
    "acute_beds_pediatric",
    "neonatal_icu_beds",
    "nursery_beds",
    "beds_in_overflow_surge_expansion_areas",
    "beds_in_other_inpatient_areas",
]


def load_config(path):
    """Read and validate config.json."""
    with open(path, "r") as f:
        config = json.load(f)
    for section in ("organization", "location", "software"):
        if section not in config:
            print(f"Error: config.json missing '{section}' section.", file=sys.stderr)
            sys.exit(1)
    return config


def parse_csv(path):
    """Read CSV file, return list of row dicts."""
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        print("Error: CSV file contains no data rows.", file=sys.stderr)
        sys.exit(1)
    return rows


def safe_int(value):
    """Parse a string to int, defaulting to 0 for empty/missing values."""
    if value is None or value.strip() == "":
        return 0
    return int(value)


def get_occupied_and_unoccupied(row, prefix):
    """Return (occupied, unoccupied) for a bed prefix. Unoccupied is clamped to >= 0."""
    occupied = safe_int(row.get(f"{prefix}_currently_occupied", "0"))
    capacity = safe_int(row.get(f"{prefix}_capacity", "0"))
    unoccupied = max(0, capacity - occupied)
    return occupied, unoccupied


def parse_reporting_date(date_str):
    """Parse MM/DD/YYYY date string and return a date object."""
    return datetime.strptime(date_str.strip(), "%m/%d/%Y").date()


def make_uuid():
    """Generate a urn:uuid: identifier."""
    return f"urn:uuid:{uuid.uuid4()}"


def build_group(code, display, count):
    """Create one MeasureReport group entry."""
    return {
        "id": f"{code}-bed-capacity-group",
        "code": {
            "coding": [{
                "system": BED_CODE_SYSTEM,
                "code": code,
                "display": display,
            }]
        },
        "population": [{
            "id": f"{code}-initial-population",
            "code": {
                "coding": [{
                    "system": MEASURE_POP_SYSTEM,
                    "code": "initial-population",
                    "display": "Initial Population",
                }]
            },
            "count": count,
        }],
    }


def compute_groups(row):
    """Build all MeasureReport groups from a CSV row."""
    groups = []

    # Direct mappings (7 bed types -> occupied + unoccupied pairs)
    for prefix, occ_code, occ_display, unocc_code, unocc_display in BED_MAPPINGS:
        occupied, unoccupied = get_occupied_and_unoccupied(row, prefix)
        groups.append(build_group(occ_code, occ_display, occupied))
        groups.append(build_group(unocc_code, unocc_display, unoccupied))

    # ED mappings
    adult_ed = safe_int(row.get("previous_day_adult_emergency_department_visits", "0"))
    peds_ed = safe_int(row.get("previous_day_pediatric_emergency_department_visits", "0"))
    total_ed = adult_ed + peds_ed

    groups.append(build_group("AdultEDCensus", "Adult ED Total Census", adult_ed))
    groups.append(build_group("PedsEDCensus", "Peds ED Census", peds_ed))
    groups.append(build_group("TotalEDCensus", "Total ED Census", total_ed))

    # Computed aggregates

    # AllBeds (all 8 prefixes including other_inpatient)
    all_occ = 0
    all_unocc = 0
    for prefix in ALL_BED_PREFIXES:
        occ, unocc = get_occupied_and_unoccupied(row, prefix)
        all_occ += occ
        all_unocc += unocc
    groups.append(build_group("AllBedsOccupied", "All Beds Census", all_occ))
    groups.append(build_group("AllBedsUnoccupied", "All Beds Unoccupied", all_unocc))

    # AdultTotal (icu_adult + acute_adult)
    icu_adult_occ, icu_adult_unocc = get_occupied_and_unoccupied(row, "icu_beds_adult")
    acute_adult_occ, acute_adult_unocc = get_occupied_and_unoccupied(row, "acute_beds_adult")
    groups.append(build_group("AdultTotalOccupied", "Adult Total Census", icu_adult_occ + acute_adult_occ))
    groups.append(build_group("AdultTotalUnoccupied", "Adult Total Unoccupied", icu_adult_unocc + acute_adult_unocc))

    # PedsTotal (icu_peds + acute_peds)
    icu_peds_occ, icu_peds_unocc = get_occupied_and_unoccupied(row, "icu_beds_pediatric")
    acute_peds_occ, acute_peds_unocc = get_occupied_and_unoccupied(row, "acute_beds_pediatric")
    groups.append(build_group("PedsTotalOccupied", "Peds Total Census", icu_peds_occ + acute_peds_occ))
    groups.append(build_group("PedsTotalUnoccupied", "Peds Total Unoccupied", icu_peds_unocc + acute_peds_unocc))

    # SpecialtyTotal (neonatal + nursery)
    nicu_occ, nicu_unocc = get_occupied_and_unoccupied(row, "neonatal_icu_beds")
    nursery_occ, nursery_unocc = get_occupied_and_unoccupied(row, "nursery_beds")
    groups.append(build_group("SpecialtyTotalOccupied", "Specialty Total Census", nicu_occ + nursery_occ))
    groups.append(build_group("SpecialtyTotalUnoccupied", "Specialty Total Unoccupied", nicu_unocc + nursery_unocc))

    return groups


def build_organization(config, org_uuid):
    """Build the Organization resource."""
    org_cfg = config["organization"]
    addr = org_cfg.get("address", {})

    return {
        "fullUrl": org_uuid,
        "resource": {
            "resourceType": "Organization",
            "id": org_uuid.split(":")[-1],
            "meta": {
                "profile": [ORG_PROFILE]
            },
            "identifier": [{
                "system": NHSN_SYSTEM,
                "value": org_cfg["nhsn_org_id"],
            }],
            "active": True,
            "type": [{
                "coding": [{
                    "system": ORG_TYPE_SYSTEM,
                    "code": "prov",
                    "display": "Healthcare Provider",
                }]
            }],
            "name": org_cfg["name"],
            "telecom": [{
                "system": "phone",
                "value": org_cfg.get("phone", ""),
                "use": "work",
            }],
            "address": [{
                "line": addr.get("line", []),
                "city": addr.get("city", ""),
                "state": addr.get("state", ""),
                "postalCode": addr.get("postalCode", ""),
                "country": addr.get("country", "USA"),
            }],
        },
    }


def build_device(config, device_uuid):
    """Build the Device resource for the submitting software."""
    sw_cfg = config["software"]
    sw_name = sw_cfg.get("name", "safr-csv-fhir")
    sw_version = sw_cfg.get("version", "1.0.0")

    return {
        "fullUrl": device_uuid,
        "resource": {
            "resourceType": "Device",
            "id": device_uuid.split(":")[-1],
            "meta": {
                "profile": [DEVICE_PROFILE]
            },
            "manufacturer": sw_name,
            "deviceName": [{
                "name": sw_name,
                "type": "manufacturer-name",
            }],
            "type": {
                "coding": [{
                    "system": SOFTWARE_TYPE_SYSTEM,
                    "code": "tooling",
                }]
            },
            "version": [{
                "value": sw_version,
            }],
        },
    }


def build_location(config, loc_uuid, org_uuid):
    """Build the Location resource."""
    loc_cfg = config["location"]
    addr = config["organization"].get("address", {})

    return {
        "fullUrl": loc_uuid,
        "resource": {
            "resourceType": "Location",
            "id": loc_uuid.split(":")[-1],
            "meta": {
                "profile": [LOCATION_PROFILE]
            },
            "identifier": [{
                "system": loc_cfg.get("identifier_system", ""),
                "value": loc_cfg.get("identifier_value", ""),
            }],
            "status": "active",
            "name": loc_cfg.get("name", ""),
            "description": loc_cfg.get("description", ""),
            "mode": "instance",
            "type": [{
                "coding": [{
                    "system": ROLE_CODE_SYSTEM,
                    "code": "HOSP",
                    "display": "Hospital",
                }]
            }],
            "address": {
                "line": addr.get("line", []),
                "city": addr.get("city", ""),
                "state": addr.get("state", ""),
                "postalCode": addr.get("postalCode", ""),
                "country": addr.get("country", "USA"),
            },
            "physicalType": {
                "coding": [{
                    "system": PHYSICAL_TYPE_SYSTEM,
                    "version": "2.0.1",
                    "code": "bu",
                    "display": "Building",
                }]
            },
            "managingOrganization": {
                "reference": org_uuid,
            },
        },
    }


def build_measure_report(row, config, reporting_date, mr_uuid, org_uuid, loc_uuid):
    """Build the MeasureReport resource with all groups."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    date_str = reporting_date.strftime("%Y-%m-%d")
    loc_display = config["location"].get("name", "")
    org_display = config["organization"].get("name", "")

    groups = compute_groups(row)

    return {
        "fullUrl": mr_uuid,
        "resource": {
            "resourceType": "MeasureReport",
            "id": mr_uuid.split(":")[-1],
            "meta": {
                "profile": [MEASUREREPORT_PROFILE]
            },
            "extension": [
                {
                    "url": MEASURE_SCORING_EXT,
                    "valueCodeableConcept": {
                        "coding": [{
                            "system": MEASURE_SCORING_SYSTEM,
                            "code": "continuous-variable",
                            "display": "Continuous Variable",
                        }]
                    },
                },
                {
                    "url": DATA_LOCATION_EXT,
                    "valueReference": {
                        "reference": loc_uuid,
                        "display": loc_display,
                    },
                },
            ],
            "status": "complete",
            "type": "individual",
            "measure": MEASURE_URL,
            "subject": {
                "reference": loc_uuid,
                "display": loc_display,
            },
            "date": now,
            "reporter": {
                "reference": org_uuid,
                "display": org_display,
            },
            "period": {
                "start": f"{date_str}T00:00:00+00:00",
                "end": f"{date_str}T23:59:59+00:00",
            },
            "improvementNotation": {
                "coding": [{
                    "system": IMPROVEMENT_SYSTEM,
                    "code": "increase",
                    "display": "Increased score indicates improvement",
                }]
            },
            "group": groups,
        },
    }


def build_bundle(row, config):
    """Assemble the full FHIR Bundle for one CSV row."""
    reporting_date = parse_reporting_date(row["reporting_date"])

    org_uuid = make_uuid()
    device_uuid = make_uuid()
    mr_uuid = make_uuid()
    loc_uuid = make_uuid()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    bundle = {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "meta": {
            "profile": [BUNDLE_PROFILE]
        },
        "type": "collection",
        "timestamp": now,
        "entry": [
            build_organization(config, org_uuid),
            build_device(config, device_uuid),
            build_measure_report(row, config, reporting_date, mr_uuid, org_uuid, loc_uuid),
            build_location(config, loc_uuid, org_uuid),
        ],
    }

    return bundle, reporting_date


def sanitize_filename(name):
    """Replace characters that are problematic in filenames."""
    return name.replace(" ", "_").replace("/", "-").replace("\\", "-")


def main():
    parser = argparse.ArgumentParser(
        description="Convert hospital bed capacity CSV to FHIR R4 SAFR MeasureReport Bundles."
    )
    parser.add_argument("csv_file", help="Path to the input CSV file")
    parser.add_argument("--config", default="config.json", help="Path to config.json (default: config.json)")
    parser.add_argument("--output-dir", default="./output", help="Output directory (default: ./output)")
    args = parser.parse_args()

    config = load_config(args.config)
    rows = parse_csv(args.csv_file)

    os.makedirs(args.output_dir, exist_ok=True)

    for i, row in enumerate(rows):
        bundle, reporting_date = build_bundle(row, config)
        facility_name = sanitize_filename(row.get("facility_name", f"facility_{i}"))
        date_str = reporting_date.strftime("%Y-%m-%d")
        filename = f"{facility_name}.{date_str}.BedCapacity.json"
        filepath = os.path.join(args.output_dir, filename)

        with open(filepath, "w") as f:
            json.dump(bundle, f, indent=2)

        print(f"  Written: {filepath}")

    print(f"\nConverted {len(rows)} row(s) to FHIR Bundles in {args.output_dir}/")


if __name__ == "__main__":
    main()
