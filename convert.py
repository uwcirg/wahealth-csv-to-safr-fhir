#!/usr/bin/env python3
"""Convert hospital bed capacity CSV to FHIR R4 SAFR Bed Capacity MeasureReport Bundles.

Usage:
    python3 convert.py input.csv [--config config.json] [--output-dir ./output] [--fhir-server URL]

Before first use, copy config.example.json to config.json and fill in your
hospital's NHSN Org ID, name, address, phone, and location details.

The input CSV layout is auto-detected from its header row. Three layouts are
supported (see csv_formats.SUPPORTED_FORMATS): the original WA Health format, the
"2026-04-30 WA Health dictionary from KC" schema, and the multi-facility
"KC multi-hospital from MFT 2026-05-11" format. An unrecognized header is a hard
error — the converter exits without writing any output.

Outputs one JSON Bundle per data row to the output directory, named:
    {facility_name}.{reporting_date}.BedCapacity.json
For a multi-facility input file, every (facility, reporting date) row produces
its own Bundle. When a facility named in a multi-facility file has no entry in
config.json's optional `facilities` registry, a sparsely-populated Organization
and Location are emitted with a deterministic placeholder identifier (and a
WARNING is logged).

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
import random
import re
import sys
import uuid
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone

from csv_formats import (
    ALL_BED_AREAS,
    UnrecognizedFormatError,
    detect_format,
    parse_date_flexible,
    parse_rows,
    slugify,
    supported_formats_summary,
)

logger = logging.getLogger(__name__)


# --- Constants ---

SAFR_IG_VERSION = "1.0.0"
# CDC NHSN SAFR Content IG (gov.cdc.nhsn.safr) — independently versioned
# from the base HL7 IG (hl7.fhir.us.safr) tracked by SAFR_IG_VERSION above.
NHSN_SAFR_IG_VERSION = "1.0.0"

for _name, _ver in [("SAFR_IG_VERSION", SAFR_IG_VERSION),
                     ("NHSN_SAFR_IG_VERSION", NHSN_SAFR_IG_VERSION)]:
    if not re.match(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$", _ver):
        print(f"ERROR: {_name} is invalid: '{_ver}'. "
              "Expected semver format (e.g., '1.0.0' or '1.0.0-ballot').",
              file=sys.stderr)
        sys.exit(1)

BUNDLE_PROFILE = "http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-measurereport-bundle"
MEASUREREPORT_PROFILE = "http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/indv-measurereport-deqm"
ORG_PROFILE = "http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-submitting-organization"
QICORE_ORG_PROFILE = "http://hl7.org/fhir/us/qicore/StructureDefinition/qicore-organization"
LOCATION_PROFILE = "http://hl7.org/fhir/us/qicore/StructureDefinition/qicore-location"
DEVICE_PROFILE = "http://hl7.org/fhir/uv/crmi/StructureDefinition/crmi-softwaresystemdevice|1.0.0"

BED_CODE_SYSTEM = "http://loinc.org"
MEASURE_POP_SYSTEM = "http://terminology.hl7.org/CodeSystem/measure-population"
MEASURE_SCORING_SYSTEM = "http://terminology.hl7.org/CodeSystem/measure-scoring"
IMPROVEMENT_SYSTEM = "http://terminology.hl7.org/CodeSystem/measure-improvement-notation"
ORG_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/organization-type"
ROLE_CODE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-RoleCode"
PHYSICAL_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/location-physical-type"
SOFTWARE_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/software-system-type-codes"
NHSN_SYSTEM = "https://www.cdc.gov/nhsn/OrgID"

# Placeholder identity for facilities that appear in a multi-facility input file
# but have no entry in config.json's `facilities` registry. The Organization's
# NHSN OrgID identifier must use the real NHSN system URI (the SAFR submitting-
# organization profile requires a slice on it), so the placeholder is encoded in
# the *value*: "UNREGISTERED-<slugified facility name>" — deterministic, stable,
# and obviously not a real OrgID. The config's NHSN OrgID is never used here.
# The placeholder Location identifier uses a project-specific scheme (qicore-
# location does not constrain the identifier system).
UNREGISTERED_ORG_ID_PREFIX = "UNREGISTERED-"
UNREGISTERED_FACILITY_SYSTEM = "urn:wahealth:csv-to-safr:unregistered-facility"

MEASURE_URL = f"http://www.cdc.gov/nhsn/fhirportal/safr/ig/Measure/BedCapacityMeasure|{NHSN_SAFR_IG_VERSION}"

MEASURE_SCORING_EXT = "http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/extension-measureScoring"
DATA_LOCATION_EXT = "http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/extension-dataLocation"

# LOINC codes for bed capacity concepts (STU 1)
LOINC_CODES = {
    "AllBedsOccupied": "112579-8",
    "AllBedsUnoccupied": "112578-0",
    "AdultTotalOccupied": "112577-2",
    "AdultTotalUnoccupied": "112576-4",
    "AdultICUOccupied": "112575-6",
    "AdultICUUnoccupied": "112574-9",
    "AdultNonICUOccupied": "112572-3",
    "AdultNonICUUnoccupied": "112571-5",
    "PedsTotalOccupied": "112564-0",
    "PedsTotalUnoccupied": "112563-2",
    "PedsICUOccupied": "112562-4",
    "PedsICUUnoccupied": "112561-6",
    "PedsNonICUOccupied": "112559-0",
    "PedsNonICUUnoccupied": "112558-2",
    "SpecialtyTotalOccupied": "112551-7",
    "SpecialtyTotalUnoccupied": "112550-9",
    "NICUTotalOccupied": "112545-9",
    "NICUTotalUnoccupied": "112544-2",
    "NurseryOccupied": "112535-0",
    "NurseryUnoccupied": "112534-3",
    "SurgeActiveTotalOccupied": "112525-1",
    "SurgeActiveTotalUnoccupied": "112524-4",
    "AdultEDCensus": "112512-9",
    "PedsEDTotalCensus": "112510-3",
    "TotalEDCensus": "112508-7",
}

# Direct bed-area mappings: (canonical_area, occupied_code, occupied_display, unoccupied_code, unoccupied_display)
BED_MAPPINGS = [
    ("adult_icu", "AdultICUOccupied", "Adult ICU Census", "AdultICUUnoccupied", "Adult ICU Unoccupied"),
    ("peds_icu", "PedsICUOccupied", "Peds ICU Census", "PedsICUUnoccupied", "Peds ICU Unoccupied"),
    ("adult_acute", "AdultNonICUOccupied", "Adult Non-ICU Census", "AdultNonICUUnoccupied", "Adult Non-ICU Unoccupied"),
    ("peds_acute", "PedsNonICUOccupied", "Peds Non-ICU Census", "PedsNonICUUnoccupied", "Peds Non-ICU Unoccupied"),
    ("neonatal_icu", "NICUTotalOccupied", "NICU Total Census", "NICUTotalUnoccupied", "NICU Total Unoccupied"),
    ("nursery", "NurseryOccupied", "Nursery Census", "NurseryUnoccupied", "Nursery Unoccupied"),
    ("surge", "SurgeActiveTotalOccupied", "Surge Total Active Census", "SurgeActiveTotalUnoccupied", "Surge Total Active Unoccupied"),
]


# --- Count fuzzing ---
#
# Opt-in obfuscation that replaces the real bed/ED counts with realistic-but-fake
# values during FHIR generation, so output can be shared or demoed without exposing a
# facility's true operational numbers. Input is consumed exactly as normal; only the
# base count fields of the already-normalized row are perturbed (see fuzz_record).
# Unoccupied beds and all aggregates are derived from those base fields downstream by
# compute_groups, so perturbing the base values keeps every derived count internally
# consistent and preserves occupied <= capacity. Fuzzing is OFF by default.

FUZZ_DEFAULT_MAGNITUDE = 0.15        # +/-15% proportional perturbation
FUZZ_DEFAULT_SMALL_FLOOR = 2         # absolute jitter bound for very small counts
# Counts at or below this threshold get a bounded *absolute* jitter instead of a
# proportional one, so a true value like 2 is actually obfuscated rather than left
# unchanged by a percentage that rounds back to itself.
FUZZ_SMALL_COUNT_THRESHOLD = 5
FUZZ_ED_FIELDS = ("adult_ed", "peds_ed")


class FuzzConfig:
    """Runtime parameters for count fuzzing. Inert (a no-op) when `enabled` is False."""

    def __init__(self, enabled=False, seed=None, magnitude=FUZZ_DEFAULT_MAGNITUDE,
                 small_count_floor=FUZZ_DEFAULT_SMALL_FLOOR):
        self.enabled = enabled
        self.seed = seed
        self.magnitude = magnitude
        self.small_count_floor = small_count_floor


def load_config(path):
    """Read and validate config.json."""
    with open(path, "r") as f:
        config = json.load(f)
    for section in ("organization", "location", "software"):
        if section not in config:
            logger.error("config.json missing '%s' section.", section)
            sys.exit(1)
    facilities = config.get("facilities")
    if facilities is not None:
        if not isinstance(facilities, dict):
            logger.error("config.json 'facilities' must be an object keyed by facility name.")
            sys.exit(1)
        for fac_name, entry in facilities.items():
            if not isinstance(entry, dict) or not entry.get("organization") or not entry.get("location"):
                logger.error(
                    "config.json 'facilities.%s' must contain non-empty 'organization' and 'location' objects.",
                    fac_name,
                )
                sys.exit(1)
    return config


def parse_reporting_date(date_str):
    """Parse an MM/DD/YYYY date string and return a date object."""
    return parse_date_flexible(date_str, ("%m/%d/%Y",))


def parse_csv(path):
    """Detect the input format from the header and return (descriptor, [NormalizedRow])."""
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        try:
            descriptor = detect_format(reader.fieldnames)
        except UnrecognizedFormatError:
            logger.error(
                "Unrecognized CSV layout. Header columns: %s. Supported formats: %s.",
                reader.fieldnames, supported_formats_summary(),
            )
            sys.exit(1)
        logger.info("Detected input format: %s", descriptor["display_name"])
        try:
            records = parse_rows(reader, descriptor)
        except ValueError as e:
            logger.error("Could not parse CSV: %s", e)
            sys.exit(1)
    logger.info("Parsed %d data row(s)", len(records))
    return descriptor, records


def get_occupied_and_unoccupied(record, area):
    """Return (occupied, unoccupied) for a canonical bed area. Unoccupied is clamped to >= 0."""
    occupied = record.get(f"{area}_occ", 0)
    capacity = record.get(f"{area}_cap", 0)
    unoccupied = max(0, capacity - occupied)
    return occupied, unoccupied


def make_uuid():
    """Generate a urn:uuid: identifier."""
    return f"urn:uuid:{uuid.uuid4()}"


def stable_facility_key(record):
    """A deterministic per-facility key: the GUID if the format has one, else the slugified name."""
    return record.get("facility_guid") or slugify(record.get("facility_name", ""))


def build_group(concept_name, display, count):
    """Create one MeasureReport group entry."""
    loinc_code = LOINC_CODES[concept_name]
    return {
        "id": f"{concept_name}-bed-capacity-group",
        "code": {
            "coding": [{
                "system": BED_CODE_SYSTEM,
                "code": loinc_code,
            }]
        },
        "population": [{
            "id": f"{concept_name}-initial-population",
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


def _fuzz_count(value, rng, magnitude, small_count_floor):
    """Perturb a single non-negative count, returning a non-negative int.

    A true zero stays zero (an empty unit must still look empty). Small counts get a
    bounded absolute jitter so they are genuinely obfuscated rather than rounded back to
    the truth; larger counts get a proportional jitter within +/- magnitude. See
    research.md D2.
    """
    if value <= 0:
        return 0
    if value <= FUZZ_SMALL_COUNT_THRESHOLD:
        delta = rng.randint(-small_count_floor, small_count_floor)
        if delta == 0:
            delta = 1  # ensure the value actually changes
        return max(0, value + delta)
    factor = rng.uniform(1 - magnitude, 1 + magnitude)
    return max(0, round(value * factor))


def fuzz_record(record, fuzz_config):
    """Return `record` with its count fields perturbed per `fuzz_config`.

    When fuzzing is disabled this returns the record unchanged (identity), so the
    default code path is byte-for-byte what it was before this feature.

    Only the base count fields are altered: each bed area's `_occ`/`_cap` and the ED
    census fields. Unoccupied beds and all aggregates are derived from these downstream
    by compute_groups, so perturbing the base values keeps every derived count
    internally consistent (aggregate == sum of fuzzed parts) and preserves
    occupied <= capacity. Non-count fields are passed through untouched.
    """
    if not fuzz_config.enabled:
        return record

    fuzzed = copy.deepcopy(record)
    # Per-row PRNG keyed by the run seed plus the row's stable identity, so the same
    # input + seed reproduces identical counts regardless of row order (research.md D3).
    rng = random.Random(
        f"{fuzz_config.seed}|{stable_facility_key(record)}|{record.get('reporting_date')}"
    )
    mag = fuzz_config.magnitude
    floor = fuzz_config.small_count_floor

    for area in ALL_BED_AREAS:
        occ_key, cap_key = f"{area}_occ", f"{area}_cap"
        has_occ, has_cap = occ_key in record, cap_key in record
        if not (has_occ or has_cap):
            continue
        source_occ = record.get(occ_key, 0)
        source_cap = record.get(cap_key, 0)
        new_cap = _fuzz_count(source_cap, rng, mag, floor)
        new_occ = _fuzz_count(source_occ, rng, mag, floor)
        # Preserve occupied <= capacity only when the source row was itself consistent;
        # a source that already reported occ > cap is a real data-quality signal we do
        # not invent away (constitution: Data Integrity).
        if source_occ <= source_cap:
            new_occ = min(new_occ, new_cap)
        if has_occ:
            fuzzed[occ_key] = new_occ
        if has_cap:
            fuzzed[cap_key] = new_cap

    for ed_key in FUZZ_ED_FIELDS:
        if ed_key in record:
            fuzzed[ed_key] = _fuzz_count(record.get(ed_key, 0), rng, mag, floor)

    return fuzzed


def compute_groups(record):
    """Build all MeasureReport groups from a normalized row."""
    groups = []

    # Direct mappings (7 bed areas -> occupied + unoccupied pairs)
    for area, occ_code, occ_display, unocc_code, unocc_display in BED_MAPPINGS:
        occupied, unoccupied = get_occupied_and_unoccupied(record, area)
        groups.append(build_group(occ_code, occ_display, occupied))
        groups.append(build_group(unocc_code, unocc_display, unoccupied))

    # ED mappings
    adult_ed = record.get("adult_ed", 0)
    peds_ed = record.get("peds_ed", 0)
    total_ed = adult_ed + peds_ed

    groups.append(build_group("AdultEDCensus", "Adult ED Total Census", adult_ed))
    groups.append(build_group("PedsEDTotalCensus", "Peds ED Total Census", peds_ed))
    groups.append(build_group("TotalEDCensus", "Total ED Census", total_ed))

    # Computed aggregates

    # AllBeds (all 8 areas including other_inpatient)
    all_occ = 0
    all_unocc = 0
    for area in ALL_BED_AREAS:
        occ, unocc = get_occupied_and_unoccupied(record, area)
        all_occ += occ
        all_unocc += unocc
    groups.append(build_group("AllBedsOccupied", "All Beds Census", all_occ))
    groups.append(build_group("AllBedsUnoccupied", "All Beds Unoccupied", all_unocc))

    # AdultTotal (adult_icu + adult_acute)
    icu_adult_occ, icu_adult_unocc = get_occupied_and_unoccupied(record, "adult_icu")
    acute_adult_occ, acute_adult_unocc = get_occupied_and_unoccupied(record, "adult_acute")
    groups.append(build_group("AdultTotalOccupied", "Adult Total Census", icu_adult_occ + acute_adult_occ))
    groups.append(build_group("AdultTotalUnoccupied", "Adult Total Unoccupied", icu_adult_unocc + acute_adult_unocc))

    # PedsTotal (peds_icu + peds_acute)
    icu_peds_occ, icu_peds_unocc = get_occupied_and_unoccupied(record, "peds_icu")
    acute_peds_occ, acute_peds_unocc = get_occupied_and_unoccupied(record, "peds_acute")
    groups.append(build_group("PedsTotalOccupied", "Peds Total Census", icu_peds_occ + acute_peds_occ))
    groups.append(build_group("PedsTotalUnoccupied", "Peds Total Unoccupied", icu_peds_unocc + acute_peds_unocc))

    # SpecialtyTotal (neonatal + nursery)
    nicu_occ, nicu_unocc = get_occupied_and_unoccupied(record, "neonatal_icu")
    nursery_occ, nursery_unocc = get_occupied_and_unoccupied(record, "nursery")
    groups.append(build_group("SpecialtyTotalOccupied", "Specialty Total Census", nicu_occ + nursery_occ))
    groups.append(build_group("SpecialtyTotalUnoccupied", "Specialty Total Unoccupied", nicu_unocc + nursery_unocc))

    return groups


def resolve_facility_profile(record, config, descriptor):
    """Return (profile, unregistered) for a row.

    `profile` is a dict with `organization` and `location` sub-dicts in the shape
    the resource builders consume. For single-facility formats it is the top-level
    config. For a multi-facility format it is the matching `facilities` entry, or
    — when the facility is not in the registry — a sparse profile built from the
    CSV row alone, with `unregistered=True` (the resource builders then emit a
    placeholder identifier). The top-level config is never a partial fallback for
    an unregistered facility.
    """
    if not descriptor["multi_facility"]:
        return {"organization": config["organization"], "location": config["location"]}, False

    name = record["facility_name"]
    entry = config.get("facilities", {}).get(name)
    if entry:
        return entry, False

    logger.warning(
        "Facility %r not in config 'facilities' registry; emitting sparsely-populated "
        "Organization/Location with a placeholder NHSN OrgID (%s|%s%s)",
        name, NHSN_SYSTEM, UNREGISTERED_ORG_ID_PREFIX, slugify(name),
    )
    profile = {
        "organization": {"name": name},
        "location": {"name": name, "description": name},
    }
    return profile, True


def build_organization_resource(profile, unregistered=False):
    """Build the bare Organization FHIR resource (no fullUrl or id)."""
    org_cfg = profile["organization"]
    addr = org_cfg.get("address", {})

    if unregistered:
        identifier = [{
            "system": NHSN_SYSTEM,
            "value": f"{UNREGISTERED_ORG_ID_PREFIX}{slugify(org_cfg.get('name', ''))}",
        }]
    else:
        identifier = [{
            "system": NHSN_SYSTEM,
            "value": org_cfg["nhsn_org_id"],
        }]

    resource = {
        "resourceType": "Organization",
        "meta": {
            "profile": [ORG_PROFILE, QICORE_ORG_PROFILE]
        },
        "identifier": identifier,
        "active": True,
        "type": [{
            "coding": [{
                "system": ORG_TYPE_SYSTEM,
                "code": "prov",
                "display": "Healthcare Provider",
            }]
        }],
        "name": org_cfg["name"],
    }
    phone = org_cfg.get("phone", "")
    if not unregistered or phone:
        resource["telecom"] = [{
            "system": "phone",
            "value": phone,
            "use": "work",
        }]
    if not unregistered or addr:
        resource["address"] = [{
            "line": addr.get("line", []),
            "city": addr.get("city", ""),
            "state": addr.get("state", ""),
            "postalCode": addr.get("postalCode", ""),
            "country": addr.get("country", "USA"),
        }]
    return resource


def build_organization_entry(profile, org_uuid, unregistered=False):
    """Build the Organization Bundle entry with fullUrl and id."""
    resource = build_organization_resource(profile, unregistered)
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


def build_location_resource(profile, org_ref, unregistered=False):
    """Build the bare Location FHIR resource (no fullUrl or id).

    Args:
        profile: Facility profile dict (`organization` + `location`).
        org_ref: Organization reference string (urn:uuid:... or Organization/...).
        unregistered: When True, emit a placeholder identifier instead of the
            configured location identifier and omit a missing address.
    """
    loc_cfg = profile["location"]
    addr = profile["organization"].get("address", {})

    if unregistered:
        identifier = [{
            "system": UNREGISTERED_FACILITY_SYSTEM,
            "value": f"{slugify(loc_cfg.get('name', ''))}:location",
        }]
    else:
        identifier = [{
            "system": loc_cfg.get("identifier_system", ""),
            "value": loc_cfg.get("identifier_value", ""),
        }]

    resource = {
        "resourceType": "Location",
        "meta": {
            "profile": [LOCATION_PROFILE]
        },
        "identifier": identifier,
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
    }
    if not unregistered or addr:
        resource["address"] = {
            "line": addr.get("line", []),
            "city": addr.get("city", ""),
            "state": addr.get("state", ""),
            "postalCode": addr.get("postalCode", ""),
            "country": addr.get("country", "USA"),
        }
    resource["physicalType"] = {
        "coding": [{
            "system": PHYSICAL_TYPE_SYSTEM,
            "version": "2.0.1",
            "code": "bu",
            "display": "Building",
        }]
    }
    resource["managingOrganization"] = {
        "reference": org_ref,
    }
    return resource


def build_location_entry(profile, loc_uuid, org_uuid, unregistered=False):
    """Build the Location Bundle entry with fullUrl and id."""
    resource = build_location_resource(profile, org_uuid, unregistered)
    resource["id"] = loc_uuid.split(":")[-1]
    return {
        "fullUrl": loc_uuid,
        "resource": resource,
    }


def build_measure_report_resource(record, profile, reporting_date, org_ref, loc_ref):
    """Build the bare MeasureReport FHIR resource (no fullUrl or id).

    Args:
        record: NormalizedRow dict.
        profile: Facility profile dict (`organization` + `location`).
        reporting_date: date object for the reporting period.
        org_ref: Organization reference string (urn:uuid:... or Organization/...).
        loc_ref: Location reference string (urn:uuid:... or Location/...).
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    date_str = reporting_date.strftime("%Y-%m-%d")
    loc_display = profile["location"].get("name", "")
    org_display = profile["organization"].get("name", "")

    groups = compute_groups(record)

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


def build_measure_report_entry(record, profile, reporting_date, mr_uuid, org_uuid, loc_uuid):
    """Build the MeasureReport Bundle entry with fullUrl and id."""
    resource = build_measure_report_resource(record, profile, reporting_date, org_uuid, loc_uuid)
    resource["id"] = mr_uuid.split(":")[-1]
    return {
        "fullUrl": mr_uuid,
        "resource": resource,
    }


def build_bundle(record, config, descriptor):
    """Assemble the full FHIR Bundle for one normalized row.

    Returns (bundle, reporting_date, profile, unregistered).
    """
    reporting_date = record["reporting_date"]
    profile, unregistered = resolve_facility_profile(record, config, descriptor)

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
            build_organization_entry(profile, org_uuid, unregistered),
            build_device_entry(config, device_uuid),
            build_measure_report_entry(record, profile, reporting_date, mr_uuid, org_uuid, loc_uuid),
            build_location_entry(profile, loc_uuid, org_uuid, unregistered),
        ],
    }

    return bundle, reporting_date, profile, unregistered


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

def upsert_organization(profile, unregistered, base_url, auth_token=None):
    """Search by the Organization's identifier; create or update. Returns server reference."""
    resource = build_organization_resource(profile, unregistered)
    if unregistered:
        ident = f"{NHSN_SYSTEM}|{UNREGISTERED_ORG_ID_PREFIX}{slugify(profile['organization'].get('name', ''))}"
    else:
        ident = f"{NHSN_SYSTEM}|{profile['organization']['nhsn_org_id']}"

    existing = fhir_search(base_url, "Organization", {"identifier": ident}, auth_token)
    if existing:
        server_id = existing["id"]
        fhir_update(base_url, "Organization", server_id, resource, auth_token)
    else:
        server_id = fhir_create(base_url, "Organization", resource, auth_token)

    return f"Organization/{server_id}"


def upsert_location(profile, unregistered, org_server_ref, base_url, auth_token=None):
    """Search by the Location's identifier; create or update with org reference. Returns server reference."""
    resource = build_location_resource(profile, org_server_ref, unregistered)
    loc_cfg = profile["location"]
    if unregistered:
        ident = f"{UNREGISTERED_FACILITY_SYSTEM}|{slugify(loc_cfg.get('name', ''))}:location"
    else:
        ident = f"{loc_cfg.get('identifier_system', '')}|{loc_cfg.get('identifier_value', '')}"

    existing = fhir_search(base_url, "Location", {"identifier": ident}, auth_token)
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


def upsert_measure_report(record, profile, reporting_date, org_server_ref, loc_server_ref,
                          base_url, auth_token=None):
    """Search by measure+subject+date; create or update with server refs. Returns server reference."""
    resource = build_measure_report_resource(record, profile, reporting_date,
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


def upsert_bundle(bundle, facility_key, reporting_date, base_url, auth_token=None):
    """Persist the self-contained Bundle. Uses a deterministic identifier for upsert."""
    bundle_copy = copy.deepcopy(bundle)

    # Generate deterministic identifier from a stable facility key + reporting_date
    date_str = reporting_date.strftime("%Y-%m-%d")
    det_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{facility_key}:{date_str}"))
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
    parser.add_argument("--bundles-mrs-only", action="store_true",
                        help="Write only the Bundle and MeasureReport.json for each facility locally; "
                             "skip the rarely-changing Organization.json, Device.json, and Location.json "
                             "files. Does not change what is persisted to a --fhir-server.")
    parser.add_argument("--fuzz", action="store_true",
                        help="Obfuscate counts: replace the real bed/ED counts with realistic but FAKE "
                             "values during FHIR generation. Off by default. Output is NOT real data; "
                             "a warning is logged whenever this is active.")
    parser.add_argument("--fuzz-seed", type=int, default=None, metavar="N",
                        help="Integer seed for reproducible fuzzing (e.g. 42). Any value works; omit for "
                             "a random, non-reproducible run. Only used with --fuzz.")
    parser.add_argument("--fuzz-magnitude", type=float, default=FUZZ_DEFAULT_MAGNITUDE, metavar="M",
                        help="Max proportional perturbation per count, range (0,1] "
                             "(default %(default)s = +/-15%%; suggested 0.05-0.25). Only used with --fuzz.")
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

    # --- Count fuzzing setup ---
    if args.fuzz and not (0 < args.fuzz_magnitude <= 1):
        logger.error("--fuzz-magnitude must be within (0, 1]; got %s", args.fuzz_magnitude)
        sys.exit(1)

    fuzz_seed = args.fuzz_seed
    if args.fuzz and fuzz_seed is None:
        # No fixed seed given: derive a random, non-reproducible one so each run differs.
        fuzz_seed = int.from_bytes(os.urandom(8), "big")
    fuzz_config = FuzzConfig(enabled=args.fuzz, seed=fuzz_seed, magnitude=args.fuzz_magnitude)

    if fuzz_config.enabled:
        logger.warning(
            "COUNT FUZZING ENABLED — output counts are obfuscated and NOT real; do not "
            "submit as authentic data. magnitude=%s (+/-%.0f%%), seed=%s",
            fuzz_config.magnitude, fuzz_config.magnitude * 100,
            "random (not reproducible)" if args.fuzz_seed is None else fuzz_config.seed,
        )
    elif args.fuzz_seed is not None or args.fuzz_magnitude != FUZZ_DEFAULT_MAGNITUDE:
        logger.info("--fuzz-seed/--fuzz-magnitude ignored because --fuzz was not set")

    config = load_config(args.config)
    # Detect format and parse rows *before* creating any output — an unrecognized
    # layout exits here without writing anything.
    descriptor, records = parse_csv(args.csv_file)

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

    # Server refs are cached per facility (a multi-facility file has many); the
    # Device is the same for all rows in a run.
    org_refs = {}
    loc_refs = {}
    dev_ref = None

    for i, record in enumerate(records):
        # Obfuscate counts if requested (no-op when fuzzing is disabled). Applied here so
        # both the local files and any --fhir-server persistence below use the same values.
        record = fuzz_record(record, fuzz_config)
        bundle, reporting_date, profile, unregistered = build_bundle(record, config, descriptor)
        facility_name = sanitize_filename(record.get("facility_name") or f"facility_{i}")
        date_str = reporting_date.strftime("%Y-%m-%d")

        # Create the date subdirectory (holds Bundle files) and the per-facility
        # subdirectory (holds that facility's individual resources). Individual
        # resources are never written loose in the date directory, so processing a
        # multi-facility (or multi-row) input file never overwrites one facility's
        # resources with another's.
        date_dir = os.path.join(args.output_dir, date_str)
        os.makedirs(date_dir, exist_ok=True)
        facility_dir = os.path.join(date_dir, facility_name)
        os.makedirs(facility_dir, exist_ok=True)

        # Write bundle
        bundle_filepath = os.path.join(date_dir, f"{facility_name}.{date_str}.BedCapacity.json")
        with open(bundle_filepath, "w") as f:
            json.dump(bundle, f, indent=2)
        logger.info("Generated %s", bundle_filepath)

        # Write individual resources into the per-facility subdirectory (useful for
        # debugging). With --bundles-mrs-only, only the MeasureReport is written; the
        # rarely-changing Organization/Device/Location files are skipped.
        for entry in bundle["entry"]:
            resource = entry["resource"]
            res_type = resource["resourceType"]
            if args.bundles_mrs_only and res_type != "MeasureReport":
                continue
            res_filepath = os.path.join(facility_dir, f"{res_type}.json")
            with open(res_filepath, "w") as f:
                json.dump(resource, f, indent=2)
            logger.info("Generated %s", res_filepath)

        # Optionally persist to FHIR server
        if fhir_server_url:
            try:
                fac = record.get("facility_name") or f"facility_{i}"
                if fac not in org_refs:
                    org_refs[fac] = upsert_organization(profile, unregistered, fhir_server_url, auth_token)
                if fac not in loc_refs:
                    loc_refs[fac] = upsert_location(profile, unregistered, org_refs[fac], fhir_server_url, auth_token)
                if dev_ref is None:
                    dev_ref = upsert_device(config, fhir_server_url, auth_token)

                mr_ref = upsert_measure_report(record, profile, reporting_date,
                                               org_refs[fac], loc_refs[fac],
                                               fhir_server_url, auth_token)
                bundle_ref = upsert_bundle(bundle, stable_facility_key(record), reporting_date,
                                           fhir_server_url, auth_token)
                logger.info("Persisted: %s + %s", mr_ref, bundle_ref)
            except urllib.error.HTTPError:
                logger.error("Skipping server persistence for row due to error above")
            except urllib.error.URLError as e:
                logger.error("FHIR server unreachable: %s", e)
                fhir_server_url = None  # Disable for remaining rows

    logger.info("Converted %d row(s) to FHIR Bundles in %s", len(records), args.output_dir.rstrip("/"))


if __name__ == "__main__":
    main()
