"""Unit tests for the computation functions in convert.py / csv_formats.py."""

import datetime
import json
import os
import re
import sys
import unittest

# Ensure repo root is on the path so we can import the modules under test.
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, REPO_ROOT)

from csv_formats import safe_int, ALL_BED_AREAS  # noqa: E402
from convert import (  # noqa: E402
    get_occupied_and_unoccupied,
    parse_reporting_date,
    compute_groups,
    load_config,
    parse_csv,
    build_bundle,
)


# Canonical bed areas excluding "other" (the seven reported individually).
DIRECT_AREAS = [a for a in ALL_BED_AREAS if a != "other"]


class TestSafeInt(unittest.TestCase):
    """safe_int(): string-to-int with safe defaults."""

    def test_empty_string_returns_zero(self):
        self.assertEqual(safe_int(""), 0)

    def test_none_returns_zero(self):
        self.assertEqual(safe_int(None), 0)

    def test_whitespace_returns_zero(self):
        self.assertEqual(safe_int("   "), 0)

    def test_valid_numeric_string(self):
        self.assertEqual(safe_int("42"), 42)

    def test_zero_string(self):
        self.assertEqual(safe_int("0"), 0)

    def test_negative_number(self):
        self.assertEqual(safe_int("-3"), -3)

    def test_non_numeric_string_raises(self):
        with self.assertRaises(ValueError):
            safe_int("abc")


class TestGetOccupiedAndUnoccupied(unittest.TestCase):
    """get_occupied_and_unoccupied(): bed count splitting from a normalized row."""

    def test_normal_split(self):
        record = {"adult_icu_occ": 10, "adult_icu_cap": 25}
        occupied, unoccupied = get_occupied_and_unoccupied(record, "adult_icu")
        self.assertEqual(occupied, 10)
        self.assertEqual(unoccupied, 15)

    def test_unoccupied_clamped_to_zero(self):
        record = {"adult_icu_occ": 30, "adult_icu_cap": 25}
        occupied, unoccupied = get_occupied_and_unoccupied(record, "adult_icu")
        self.assertEqual(occupied, 30)
        self.assertEqual(unoccupied, 0)

    def test_zero_capacity(self):
        record = {"nursery_occ": 0, "nursery_cap": 0}
        occupied, unoccupied = get_occupied_and_unoccupied(record, "nursery")
        self.assertEqual(occupied, 0)
        self.assertEqual(unoccupied, 0)

    def test_missing_keys_default_to_zero(self):
        occupied, unoccupied = get_occupied_and_unoccupied({}, "adult_icu")
        self.assertEqual(occupied, 0)
        self.assertEqual(unoccupied, 0)


class TestParseReportingDate(unittest.TestCase):
    """parse_reporting_date(): MM/DD/YYYY parsing (unchanged behavior)."""

    def test_standard_date(self):
        self.assertEqual(parse_reporting_date("03/15/2026"), datetime.date(2026, 3, 15))

    def test_year_boundary(self):
        self.assertEqual(parse_reporting_date("12/31/2025"), datetime.date(2025, 12, 31))

    def test_new_year(self):
        self.assertEqual(parse_reporting_date("01/01/2026"), datetime.date(2026, 1, 1))

    def test_leap_year_date(self):
        self.assertEqual(parse_reporting_date("02/29/2024"), datetime.date(2024, 2, 29))

    def test_whitespace_stripped(self):
        self.assertEqual(parse_reporting_date("  03/15/2026  "), datetime.date(2026, 3, 15))


def _make_record():
    """Build a complete NormalizedRow with known values; return (record, bed_data)."""
    record = {
        "facility_name": "Test Facility",
        "facility_guid": "test-guid",
        "reporting_date": datetime.date(2026, 3, 15),
        "adult_ed": 50,
        "peds_ed": 10,
    }
    bed_data = {
        "adult_icu": (20, 30),       # (occupied, capacity)
        "peds_icu": (5, 10),
        "adult_acute": (40, 60),
        "peds_acute": (8, 15),
        "neonatal_icu": (3, 8),
        "nursery": (6, 12),
        "surge": (2, 5),
        "other": (4, 10),
    }
    for area, (occ, cap) in bed_data.items():
        record[f"{area}_occ"] = occ
        record[f"{area}_cap"] = cap
    return record, bed_data


class TestComputeGroups(unittest.TestCase):
    """compute_groups(): full MeasureReport group generation from a normalized row."""

    def test_returns_exactly_25_groups(self):
        record, _ = _make_record()
        self.assertEqual(len(compute_groups(record)), 25)

    def test_group_ids_are_unique(self):
        record, _ = _make_record()
        ids = [g["id"] for g in compute_groups(record)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_beds_aggregate(self):
        record, bed_data = _make_record()
        gm = {g["id"]: g["population"][0]["count"] for g in compute_groups(record)}
        expected_occ = sum(occ for occ, _ in bed_data.values())
        expected_unocc = sum(max(0, cap - occ) for occ, cap in bed_data.values())
        self.assertEqual(gm["AllBedsOccupied-bed-capacity-group"], expected_occ)
        self.assertEqual(gm["AllBedsUnoccupied-bed-capacity-group"], expected_unocc)

    def test_adult_total_aggregate(self):
        record, bed_data = _make_record()
        gm = {g["id"]: g["population"][0]["count"] for g in compute_groups(record)}
        icu_occ, icu_cap = bed_data["adult_icu"]
        acute_occ, acute_cap = bed_data["adult_acute"]
        self.assertEqual(gm["AdultTotalOccupied-bed-capacity-group"], icu_occ + acute_occ)
        self.assertEqual(
            gm["AdultTotalUnoccupied-bed-capacity-group"],
            max(0, icu_cap - icu_occ) + max(0, acute_cap - acute_occ),
        )

    def test_peds_total_aggregate(self):
        record, bed_data = _make_record()
        gm = {g["id"]: g["population"][0]["count"] for g in compute_groups(record)}
        icu_occ, icu_cap = bed_data["peds_icu"]
        acute_occ, acute_cap = bed_data["peds_acute"]
        self.assertEqual(gm["PedsTotalOccupied-bed-capacity-group"], icu_occ + acute_occ)
        self.assertEqual(
            gm["PedsTotalUnoccupied-bed-capacity-group"],
            max(0, icu_cap - icu_occ) + max(0, acute_cap - acute_occ),
        )

    def test_specialty_total_aggregate(self):
        record, bed_data = _make_record()
        gm = {g["id"]: g["population"][0]["count"] for g in compute_groups(record)}
        nicu_occ, nicu_cap = bed_data["neonatal_icu"]
        nurs_occ, nurs_cap = bed_data["nursery"]
        self.assertEqual(gm["SpecialtyTotalOccupied-bed-capacity-group"], nicu_occ + nurs_occ)
        self.assertEqual(
            gm["SpecialtyTotalUnoccupied-bed-capacity-group"],
            max(0, nicu_cap - nicu_occ) + max(0, nurs_cap - nurs_occ),
        )

    def test_ed_groups(self):
        record, _ = _make_record()
        gm = {g["id"]: g["population"][0]["count"] for g in compute_groups(record)}
        self.assertEqual(gm["AdultEDCensus-bed-capacity-group"], 50)
        self.assertEqual(gm["PedsEDTotalCensus-bed-capacity-group"], 10)
        self.assertEqual(gm["TotalEDCensus-bed-capacity-group"], 60)

    def test_group_has_loinc_coding(self):
        record, _ = _make_record()
        for group in compute_groups(record):
            coding = group["code"]["coding"][0]
            self.assertEqual(coding["system"], "http://loinc.org")
            self.assertTrue(len(coding["code"]) > 0)

    def test_aggregates_use_raw_values_not_group_counts(self):
        # AllBeds occupied should equal the raw sum even when individual areas would
        # produce different "individual" group counts (here they're the same, but the
        # point is the aggregate is computed from raw _occ/_cap, not re-derived).
        record, bed_data = _make_record()
        gm = {g["id"]: g["population"][0]["count"] for g in compute_groups(record)}
        self.assertEqual(
            gm["AllBedsOccupied-bed-capacity-group"],
            sum(record[f"{a}_occ"] for a in ALL_BED_AREAS),
        )


# --- Regression: original WA Health format output must be unchanged ---

_UUID_RE = re.compile(
    r"urn:uuid:[0-9a-fA-F-]{36}|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


def _scrub(obj):
    """Remove fullUrl keys and replace every UUID with a constant token."""
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items() if k != "fullUrl"}
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, str):
        return _UUID_RE.sub("UUID", obj)
    return obj


def _canonical_bundle(bundle):
    """Strip volatile fields (ids, timestamps, MeasureReport.date) and UUIDs."""
    b = json.loads(json.dumps(bundle))
    b.pop("id", None)
    b.pop("timestamp", None)
    for entry in b.get("entry", []):
        res = entry.get("resource", {})
        res.pop("id", None)
        if res.get("resourceType") == "MeasureReport":
            res.pop("date", None)
    return _scrub(b)


class TestOriginalFormatNoRegression(unittest.TestCase):
    """Converting the original-format fixture must produce the recorded baseline output."""

    def test_original_fixture_matches_baseline(self):
        baseline_path = os.path.join(
            REPO_ROOT, "specs", "008-multi-format-csv-input", "regression-baseline.json"
        )
        with open(baseline_path) as f:
            baseline = {item["file"]: item["bundle"] for item in json.load(f)}

        config = load_config(os.path.join(REPO_ROOT, "config.example.json"))
        fixture = os.path.join(
            REPO_ROOT, "input", "2025.10.21.Test.Facility.BedCapacity.csv"
        )
        descriptor, records = parse_csv(fixture)
        produced = {}
        for record in records:
            bundle, reporting_date, _profile, _unreg = build_bundle(record, config, descriptor)
            fname = f"{record['facility_name'].replace(' ', '_')}.{reporting_date.isoformat()}.BedCapacity.json"
            produced[fname] = _canonical_bundle(bundle)

        self.assertEqual(set(produced), set(baseline))
        for name in baseline:
            self.assertEqual(produced[name], baseline[name], f"regression in {name}")


if __name__ == "__main__":
    unittest.main()
