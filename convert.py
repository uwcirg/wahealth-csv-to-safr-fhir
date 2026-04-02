#!/usr/bin/env python3
"""Convert hospital bed capacity CSV to FHIR R4 SAFR Bed Capacity MeasureReport Bundles.

Usage:
    python3 convert.py input.csv [--config config.json] [--output-dir ./output] [--fhir-server URL]

Before first use, copy config.example.json to config.json and fill in your
hospital's NHSN Org ID, name, address, phone, and location details.

Outputs one JSON Bundle per CSV row to the output directory, named:
    {facility_name}.{reporting_date}.BedCapacity.json

With --fhir-server, also persists individual resources to the FHIR server
using upsert semantics (create on first run, update on subsequent runs).

Requires Python 3 (stdlib only — no pip install needed).
"""

import argparse
import copy
import csv
import json
import logging
import os
import re
import sys
import uuid
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# --- Constants ---

SAFR_IG_VERSION = "1.0.0-ballot"

if not re.match(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$", SAFR_IG_VERSION):
    print(f"ERROR: SAFR_IG_VERSION is invalid: '{SAFR_IG_VERSION}'. "
          "Expected semver format (e.g., '1.0.0' or '1.0.0-ballot').", file=sys.stderr)
    sys.exit(1)

BUNDLE_PROFILE = f"http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-measurereport-bundle|{SAFR_IG_VERSION}"
MEASUREREPORT_PROFILE = "http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/indv-measurereport-deqm"
ORG_PROFILE = f"http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-submitting-organization|{SAFR_IG_VERSION}"
QICORE_ORG_PROFILE = "http://hl7.org/fhir/us/qicore/StructureDefinition/qicore-organization"
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

MEASURE_URL = f"http://hl7.org/fhir/us/safr/Measure/BedCapacityMeasure|{SAFR_IG_VERSION}"

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
            logger.error("config.json missing '%s' section.", section)
            sys.exit(1)
    return config


def parse_csv(path):
    """Read CSV file, return list of row dicts."""
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        logger.error("CSV file contains no data rows.")
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


def build_organization_resource(config):
    """Build the bare Organization FHIR resource (no fullUrl or id)."""
    org_cfg = config["organization"]
    addr = org_cfg.get("address", {})

    return {
        "resourceType": "Organization",
        "meta": {
            "profile": [ORG_PROFILE, QICORE_ORG_PROFILE]
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
    }


def build_organization_entry(config, org_uuid):
    """Build the Organization Bundle entry with fullUrl and id."""
    resource = build_organization_resource(config)
    resource["id"] = org_uuid.split(":")[-1]
    return {
        "fullUrl": org_uuid,
        "resource": resource,
    }


def build_device_resource(config):
    """Build the bare Device FHIR resource (no fullUrl or id)."""
    sw_cfg = config["software"]
    sw_name = sw_cfg.get("name", "safr-csv-fhir")
    sw_version = sw_cfg.get("version", "1.0.0")

    resource = {
        "resourceType": "Device",
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
    }

    id_system = sw_cfg.get("identifier_system")
    id_value = sw_cfg.get("identifier_value")
    if id_system and id_value:
        resource["identifier"] = [{
            "system": id_system,
            "value": id_value,
        }]

    return resource


def build_device_entry(config, device_uuid):
    """Build the Device Bundle entry with fullUrl and id."""
    resource = build_device_resource(config)
    resource["id"] = device_uuid.split(":")[-1]
    return {
        "fullUrl": device_uuid,
        "resource": resource,
    }


def build_location_resource(config, org_ref):
    """Build the bare Location FHIR resource (no fullUrl or id).

    Args:
        config: Config dict.
        org_ref: Organization reference string (urn:uuid:... or Organization/...).
    """
    loc_cfg = config["location"]
    addr = config["organization"].get("address", {})

    return {
        "resourceType": "Location",
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
            "reference": org_ref,
        },
    }


def build_location_entry(config, loc_uuid, org_uuid):
    """Build the Location Bundle entry with fullUrl and id."""
    resource = build_location_resource(config, org_uuid)
    resource["id"] = loc_uuid.split(":")[-1]
    return {
        "fullUrl": loc_uuid,
        "resource": resource,
    }


def build_measure_report_resource(row, config, reporting_date, org_ref, loc_ref):
    """Build the bare MeasureReport FHIR resource (no fullUrl or id).

    Args:
        row: CSV row dict.
        config: Config dict.
        reporting_date: date object for the reporting period.
        org_ref: Organization reference string (urn:uuid:... or Organization/...).
        loc_ref: Location reference string (urn:uuid:... or Location/...).
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    date_str = reporting_date.strftime("%Y-%m-%d")
    loc_display = config["location"].get("name", "")
    org_display = config["organization"].get("name", "")

    groups = compute_groups(row)

    return {
        "resourceType": "MeasureReport",
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
                    "reference": loc_ref,
                    "display": loc_display,
                },
            },
        ],
        "status": "complete",
        "type": "individual",
        "measure": MEASURE_URL,
        "subject": {
            "reference": loc_ref,
            "display": loc_display,
        },
        "date": now,
        "reporter": {
            "reference": org_ref,
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
    }


def build_measure_report_entry(row, config, reporting_date, mr_uuid, org_uuid, loc_uuid):
    """Build the MeasureReport Bundle entry with fullUrl and id."""
    resource = build_measure_report_resource(row, config, reporting_date, org_uuid, loc_uuid)
    resource["id"] = mr_uuid.split(":")[-1]
    return {
        "fullUrl": mr_uuid,
        "resource": resource,
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
            build_organization_entry(config, org_uuid),
            build_device_entry(config, device_uuid),
            build_measure_report_entry(row, config, reporting_date, mr_uuid, org_uuid, loc_uuid),
            build_location_entry(config, loc_uuid, org_uuid),
        ],
    }

    return bundle, reporting_date


# --- FHIR Server Client ---

def fetch_access_token(token_endpoint, client_id, client_secret):
    """Exchange client credentials for an access token (OAuth2 client_credentials grant)."""
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }).encode("utf-8")
    req = urllib.request.Request(token_endpoint, data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            token_response = json.loads(resp.read().decode("utf-8"))
            logger.info("Obtained access token from %s", token_endpoint)
            return token_response["access_token"]
    except urllib.error.HTTPError as e:
        logger.error("Failed to obtain access token: HTTP %s", e.code)
        raise
    except KeyError:
        logger.error("Token response missing 'access_token'")
        raise


def fhir_request(url, method="GET", body=None, auth_token=None):
    """Make an HTTP request to a FHIR server. Returns parsed JSON or None."""
    headers = {
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            logger.info("FHIR %s %s — OK", method, url)
            if resp_body:
                return json.loads(resp_body)
            return None
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode("utf-8", errors="replace")
        logger.error("FHIR %s %s — HTTP %s", method, url, e.code)
        if resp_body:
            try:
                outcome = json.loads(resp_body)
                if outcome.get("resourceType") == "OperationOutcome":
                    for issue in outcome.get("issue", []):
                        logger.error("  %s: %s", issue.get('severity', '?'), issue.get('diagnostics', issue.get('details', {}).get('text', '')))
                else:
                    logger.error("  %s", resp_body[:500])
            except json.JSONDecodeError:
                logger.error("  %s", resp_body[:500])
        raise


def fhir_search(base_url, resource_type, params, auth_token=None):
    """Search for a resource. Returns first match or None."""
    query = urllib.parse.urlencode(params)
    url = f"{base_url}/{resource_type}?{query}"
    result = fhir_request(url, method="GET", auth_token=auth_token)
    if result and result.get("total", 0) > 0:
        entries = result.get("entry", [])
        if entries:
            return entries[0]["resource"]
    return None


def fhir_create(base_url, resource_type, resource, auth_token=None):
    """POST a new resource. Returns server-assigned ID."""
    url = f"{base_url}/{resource_type}"
    result = fhir_request(url, method="POST", body=resource, auth_token=auth_token)
    if result and "id" in result:
        return result["id"]
    return None


def fhir_update(base_url, resource_type, server_id, resource, auth_token=None):
    """PUT an existing resource. Returns the ID."""
    url = f"{base_url}/{resource_type}/{server_id}"
    resource["id"] = server_id
    result = fhir_request(url, method="PUT", body=resource, auth_token=auth_token)
    if result and "id" in result:
        return result["id"]
    return server_id


# --- Upsert Functions ---

def upsert_organization(config, base_url, auth_token=None):
    """Search by NHSN OrgID identifier; create or update. Returns server reference."""
    resource = build_organization_resource(config)
    nhsn_id = config["organization"]["nhsn_org_id"]

    existing = fhir_search(base_url, "Organization",
                           {"identifier": f"{NHSN_SYSTEM}|{nhsn_id}"},
                           auth_token)
    if existing:
        server_id = existing["id"]
        fhir_update(base_url, "Organization", server_id, resource, auth_token)
    else:
        server_id = fhir_create(base_url, "Organization", resource, auth_token)

    return f"Organization/{server_id}"


def upsert_location(config, org_server_ref, base_url, auth_token=None):
    """Search by location identifier; create or update with org reference. Returns server reference."""
    resource = build_location_resource(config, org_server_ref)
    loc_cfg = config["location"]
    id_system = loc_cfg.get("identifier_system", "")
    id_value = loc_cfg.get("identifier_value", "")

    existing = fhir_search(base_url, "Location",
                           {"identifier": f"{id_system}|{id_value}"},
                           auth_token)
    if existing:
        server_id = existing["id"]
        fhir_update(base_url, "Location", server_id, resource, auth_token)
    else:
        server_id = fhir_create(base_url, "Location", resource, auth_token)

    return f"Location/{server_id}"


def upsert_device(config, base_url, auth_token=None):
    """Search by device identifier; create or update. Returns server reference."""
    resource = build_device_resource(config)
    sw_cfg = config["software"]
    id_system = sw_cfg.get("identifier_system")
    id_value = sw_cfg.get("identifier_value")

    existing = None
    if id_system and id_value:
        existing = fhir_search(base_url, "Device",
                               {"identifier": f"{id_system}|{id_value}"},
                               auth_token)

    if existing:
        server_id = existing["id"]
        fhir_update(base_url, "Device", server_id, resource, auth_token)
    else:
        server_id = fhir_create(base_url, "Device", resource, auth_token)

    return f"Device/{server_id}"


def upsert_measure_report(row, config, reporting_date, org_server_ref, loc_server_ref,
                           base_url, auth_token=None):
    """Search by measure+subject+date; create or update with server refs. Returns server reference."""
    resource = build_measure_report_resource(row, config, reporting_date,
                                             org_server_ref, loc_server_ref)
    date_str = reporting_date.strftime("%Y-%m-%d")

    existing = fhir_search(base_url, "MeasureReport", {
        "measure": MEASURE_URL,
        "subject": loc_server_ref,
        "date": date_str,
    }, auth_token)

    if existing:
        server_id = existing["id"]
        fhir_update(base_url, "MeasureReport", server_id, resource, auth_token)
    else:
        server_id = fhir_create(base_url, "MeasureReport", resource, auth_token)

    return f"MeasureReport/{server_id}"


def upsert_bundle(bundle, facility_guid, reporting_date, base_url, auth_token=None):
    """Persist the self-contained Bundle. Uses deterministic identifier for upsert."""
    bundle_copy = copy.deepcopy(bundle)

    # Generate deterministic identifier from facility_guid + reporting_date
    date_str = reporting_date.strftime("%Y-%m-%d")
    det_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{facility_guid}:{date_str}"))
    bundle_id_system = "urn:ietf:rfc:3986"
    bundle_id_value = f"urn:uuid:{det_uuid}"

    bundle_copy["identifier"] = {
        "system": bundle_id_system,
        "value": bundle_id_value,
    }

    existing = fhir_search(base_url, "Bundle",
                           {"identifier": f"{bundle_id_system}|{bundle_id_value}"},
                           auth_token)
    if existing:
        server_id = existing["id"]
        fhir_update(base_url, "Bundle", server_id, bundle_copy, auth_token)
    else:
        server_id = fhir_create(base_url, "Bundle", bundle_copy, auth_token)

    return f"Bundle/{server_id}"


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
    parser.add_argument("--fhir-server", default=None, metavar="URL",
                        help="FHIR server base URL to persist resources to (e.g. http://localhost:8080/fhir)")
    args = parser.parse_args()

    # --- Set up logging ---
    os.makedirs("log", exist_ok=True)
    log_filename = datetime.now().strftime("convert_%Y%m%d_%H%M%S.log")
    log_format = "%(asctime)s %(levelname)s %(message)s"

    file_handler = logging.FileHandler(os.path.join("log", log_filename))
    file_handler.setFormatter(logging.Formatter(log_format))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))

    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    config = load_config(args.config)
    rows = parse_csv(args.csv_file)

    os.makedirs(args.output_dir, exist_ok=True)

    # Determine FHIR server URL: CLI flag overrides config
    fhir_server_url = args.fhir_server or config.get("server", {}).get("base_url") or None
    if fhir_server_url and not fhir_server_url.startswith(("http://", "https://")):
        logger.warning("Ignoring non-URL server base_url: %s", fhir_server_url)
        fhir_server_url = None
    if fhir_server_url:
        fhir_server_url = fhir_server_url.rstrip("/")
    auth_token = None
    server_cfg = config.get("server", {})
    token_endpoint = server_cfg.get("token_endpoint")
    client_id = server_cfg.get("client_id")
    client_secret = server_cfg.get("client_secret")
    if fhir_server_url and token_endpoint and client_id and client_secret:
        auth_token = fetch_access_token(token_endpoint, client_id, client_secret)

    # Track server refs for reuse across rows (Org/Location/Device are the same for all rows)
    org_ref = None
    loc_ref = None
    dev_ref = None

    for i, row in enumerate(rows):
        bundle, reporting_date = build_bundle(row, config)
        facility_name = sanitize_filename(row.get("facility_name", f"facility_{i}"))
        date_str = reporting_date.strftime("%Y-%m-%d")

        # Create date subdirectory
        date_dir = os.path.join(args.output_dir, date_str)
        os.makedirs(date_dir, exist_ok=True)

        # Write bundle
        bundle_filepath = os.path.join(date_dir, f"{facility_name}.{date_str}.BedCapacity.json")
        with open(bundle_filepath, "w") as f:
            json.dump(bundle, f, indent=2)
        logger.info("Generated %s", bundle_filepath)

        # Write individual resources for debugging
        for entry in bundle["entry"]:
            resource = entry["resource"]
            res_type = resource["resourceType"]
            res_filepath = os.path.join(date_dir, f"{res_type}.json")
            with open(res_filepath, "w") as f:
                json.dump(resource, f, indent=2)
            logger.info("Generated %s", res_filepath)

        # Optionally persist to FHIR server
        if fhir_server_url:
            try:
                # Upsert Org/Location/Device once, reuse for subsequent rows
                if org_ref is None:
                    org_ref = upsert_organization(config, fhir_server_url, auth_token)
                if loc_ref is None:
                    loc_ref = upsert_location(config, org_ref, fhir_server_url, auth_token)
                if dev_ref is None:
                    dev_ref = upsert_device(config, fhir_server_url, auth_token)

                mr_ref = upsert_measure_report(row, config, reporting_date,
                                               org_ref, loc_ref,
                                               fhir_server_url, auth_token)
                facility_guid = row.get("facility_guid", "")
                bundle_ref = upsert_bundle(bundle, facility_guid, reporting_date,
                                           fhir_server_url, auth_token)
                logger.info("Persisted: %s + %s", mr_ref, bundle_ref)
            except urllib.error.HTTPError:
                logger.error("Skipping server persistence for row due to error above")
            except urllib.error.URLError as e:
                logger.error("FHIR server unreachable: %s", e)
                fhir_server_url = None  # Disable for remaining rows

    logger.info("Converted %d row(s) to FHIR Bundles in %s", len(rows), args.output_dir.rstrip("/"))


if __name__ == "__main__":
    main()
