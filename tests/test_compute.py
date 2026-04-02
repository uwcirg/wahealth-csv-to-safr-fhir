"""Unit tests for computation functions in convert.py."""

import datetime
import sys
import os
import unittest

# Ensure repo root is on the path so we can import convert.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from convert import (
    safe_int,
    get_occupied_and_unoccupied,
    parse_reporting_date,
    compute_groups,
    ALL_BED_PREFIXES,
)


class TestSafeInt(unittest.TestCase):
    """Tests for safe_int(): string-to-int with safe defaults."""

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
    """Tests for get_occupied_and_unoccupied(): bed count splitting."""

    def test_normal_split(self):
        row = {
            "icu_beds_adult_currently_occupied": "10",
            "icu_beds_adult_capacity": "25",
        }
        occupied, unoccupied = get_occupied_and_unoccupied(row, "icu_beds_adult")
        self.assertEqual(occupied, 10)
        self.assertEqual(unoccupied, 15)

    def test_unoccupied_clamped_to_zero(self):
        row = {
            "icu_beds_adult_currently_occupied": "30",
            "icu_beds_adult_capacity": "25",
        }
        occupied, unoccupied = get_occupied_and_unoccupied(row, "icu_beds_adult")
        self.assertEqual(occupied, 30)
        self.assertEqual(unoccupied, 0)

    def test_zero_capacity(self):
        row = {
            "nursery_beds_currently_occupied": "0",
            "nursery_beds_capacity": "0",
        }
        occupied, unoccupied = get_occupied_and_unoccupied(row, "nursery_beds")
        self.assertEqual(occupied, 0)
        self.assertEqual(unoccupied, 0)

    def test_missing_columns_default_to_zero(self):
        occupied, unoccupied = get_occupied_and_unoccupied({}, "icu_beds_adult")
        self.assertEqual(occupied, 0)
        self.assertEqual(unoccupied, 0)


class TestParseReportingDate(unittest.TestCase):
    """Tests for parse_reporting_date(): MM/DD/YYYY parsing."""

    def test_standard_date(self):
        result = parse_reporting_date("03/15/2026")
        self.assertEqual(result, datetime.date(2026, 3, 15))

    def test_year_boundary(self):
        result = parse_reporting_date("12/31/2025")
        self.assertEqual(result, datetime.date(2025, 12, 31))

    def test_new_year(self):
        result = parse_reporting_date("01/01/2026")
        self.assertEqual(result, datetime.date(2026, 1, 1))

    def test_leap_year_date(self):
        result = parse_reporting_date("02/29/2024")
        self.assertEqual(result, datetime.date(2024, 2, 29))

    def test_whitespace_stripped(self):
        result = parse_reporting_date("  03/15/2026  ")
        self.assertEqual(result, datetime.date(2026, 3, 15))


class TestComputeGroups(unittest.TestCase):
    """Tests for compute_groups(): full MeasureReport group generation."""

    def _make_row(self):
        """Build a complete CSV row dict with known values."""
        row = {
            "reporting_date": "03/15/2026",
            "previous_day_adult_emergency_department_visits": "50",
            "previous_day_pediatric_emergency_department_visits": "10",
        }
        # Set known values for all 8 bed prefixes
        bed_data = {
            "icu_beds_adult": (20, 30),        # occupied, capacity
            "icu_beds_pediatric": (5, 10),
            "acute_beds_adult": (40, 60),
            "acute_beds_pediatric": (8, 15),
            "neonatal_icu_beds": (3, 8),
            "nursery_beds": (6, 12),
            "beds_in_overflow_surge_expansion_areas": (2, 5),
            "beds_in_other_inpatient_areas": (4, 10),
        }
        for prefix, (occupied, capacity) in bed_data.items():
            row[f"{prefix}_currently_occupied"] = str(occupied)
            row[f"{prefix}_capacity"] = str(capacity)
        return row, bed_data

    def test_returns_exactly_25_groups(self):
        row, _ = self._make_row()
        groups = compute_groups(row)
        self.assertEqual(len(groups), 25)

    def test_group_ids_are_unique(self):
        row, _ = self._make_row()
        groups = compute_groups(row)
        ids = [g["id"] for g in groups]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_beds_aggregate(self):
        row, bed_data = self._make_row()
        groups = compute_groups(row)
        group_map = {g["id"]: g["population"][0]["count"] for g in groups}

        # AllBeds = sum of all 8 prefixes
        expected_occ = sum(occ for occ, _ in bed_data.values())
        expected_unocc = sum(
            max(0, cap - occ) for occ, cap in bed_data.values()
        )
        self.assertEqual(group_map["AllBedsOccupied-bed-capacity-group"], expected_occ)
        self.assertEqual(group_map["AllBedsUnoccupied-bed-capacity-group"], expected_unocc)

    def test_adult_total_aggregate(self):
        row, bed_data = self._make_row()
        groups = compute_groups(row)
        group_map = {g["id"]: g["population"][0]["count"] for g in groups}

        # AdultTotal = icu_adult + acute_adult
        icu_occ, icu_cap = bed_data["icu_beds_adult"]
        acute_occ, acute_cap = bed_data["acute_beds_adult"]
        self.assertEqual(
            group_map["AdultTotalOccupied-bed-capacity-group"],
            icu_occ + acute_occ,
        )
        self.assertEqual(
            group_map["AdultTotalUnoccupied-bed-capacity-group"],
            max(0, icu_cap - icu_occ) + max(0, acute_cap - acute_occ),
        )

    def test_peds_total_aggregate(self):
        row, bed_data = self._make_row()
        groups = compute_groups(row)
        group_map = {g["id"]: g["population"][0]["count"] for g in groups}

        icu_occ, icu_cap = bed_data["icu_beds_pediatric"]
        acute_occ, acute_cap = bed_data["acute_beds_pediatric"]
        self.assertEqual(
            group_map["PedsTotalOccupied-bed-capacity-group"],
            icu_occ + acute_occ,
        )
        self.assertEqual(
            group_map["PedsTotalUnoccupied-bed-capacity-group"],
            max(0, icu_cap - icu_occ) + max(0, acute_cap - acute_occ),
        )

    def test_specialty_total_aggregate(self):
        row, bed_data = self._make_row()
        groups = compute_groups(row)
        group_map = {g["id"]: g["population"][0]["count"] for g in groups}

        nicu_occ, nicu_cap = bed_data["neonatal_icu_beds"]
        nursery_occ, nursery_cap = bed_data["nursery_beds"]
        self.assertEqual(
            group_map["SpecialtyTotalOccupied-bed-capacity-group"],
            nicu_occ + nursery_occ,
        )
        self.assertEqual(
            group_map["SpecialtyTotalUnoccupied-bed-capacity-group"],
            max(0, nicu_cap - nicu_occ) + max(0, nursery_cap - nursery_occ),
        )

    def test_ed_groups(self):
        row, _ = self._make_row()
        groups = compute_groups(row)
        group_map = {g["id"]: g["population"][0]["count"] for g in groups}

        self.assertEqual(group_map["AdultEDCensus-bed-capacity-group"], 50)
        self.assertEqual(group_map["PedsEDTotalCensus-bed-capacity-group"], 10)
        self.assertEqual(group_map["TotalEDCensus-bed-capacity-group"], 60)

    def test_group_has_loinc_coding(self):
        row, _ = self._make_row()
        groups = compute_groups(row)
        for group in groups:
            coding = group["code"]["coding"][0]
            self.assertEqual(coding["system"], "http://loinc.org")
            self.assertTrue(len(coding["code"]) > 0)


if __name__ == "__main__":
    unittest.main()
