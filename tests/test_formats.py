"""Unit tests for CSV format detection, parsing, and per-facility identity resolution."""

import csv
import datetime
import os
import subprocess
import sys
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, REPO_ROOT)

from csv_formats import (  # noqa: E402
    SUPPORTED_FORMATS,
    UnrecognizedFormatError,
    detect_format,
    parse_date_flexible,
    parse_rows,
    slugify,
)
from convert import (  # noqa: E402
    UNREGISTERED_ORG_ID_PREFIX,
    NHSN_SYSTEM,
    compute_groups,
    load_config,
    resolve_facility_profile,
)


ORIGINAL_FIXTURE = os.path.join(REPO_ROOT, "input", "2025.10.21.Test.Facility.BedCapacity.csv")
DICT_FIXTURE = os.path.join(REPO_ROOT, "input", "2026.04.30.Test.Facility.WAHealthDict.csv")
KC_FIXTURE = os.path.join(REPO_ROOT, "input", "census_20260511.FromKC.SubsetObfsctd.csv")
CATALOG_FILE = os.path.join(REPO_ROOT, "WA-HEALTH-DataDictionary.Variable Catalog.KC.2026-04-30.csv")
CONFIG = os.path.join(REPO_ROOT, "config.example.json")


def _header(path):
    with open(path, "r", newline="") as f:
        return next(csv.reader(f))


def _read(path):
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        descriptor = detect_format(reader.fieldnames)
        return descriptor, parse_rows(reader, descriptor)


class TestSlugify(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Seaside Medical Center"), "seaside-medical-center")

    def test_punctuation_and_hyphens(self):
        self.assertEqual(slugify("AMC - University Triangle"), "amc-university-triangle")
        self.assertEqual(slugify("Catholic Health St. Ebe Hospital"), "catholic-health-st-ebe-hospital")

    def test_trims_and_collapses(self):
        self.assertEqual(slugify("  --Foo / Bar--  "), "foo-bar")

    def test_empty(self):
        self.assertEqual(slugify(""), "")
        self.assertEqual(slugify(None), "")


class TestParseDateFlexible(unittest.TestCase):
    def test_us_format(self):
        self.assertEqual(parse_date_flexible("03/15/2026", ("%m/%d/%Y",)), datetime.date(2026, 3, 15))

    def test_iso_first_then_us_fallback(self):
        fmts = ("%Y-%m-%d", "%m/%d/%Y")
        self.assertEqual(parse_date_flexible("2026-04-29", fmts), datetime.date(2026, 4, 29))
        self.assertEqual(parse_date_flexible("4/29/2026", fmts), datetime.date(2026, 4, 29))

    def test_whitespace(self):
        self.assertEqual(parse_date_flexible("  2026-04-29 ", ("%Y-%m-%d",)), datetime.date(2026, 4, 29))

    def test_unparseable_raises(self):
        with self.assertRaises(ValueError):
            parse_date_flexible("not a date", ("%Y-%m-%d", "%m/%d/%Y"))


class TestDetectFormat(unittest.TestCase):
    def test_original(self):
        self.assertEqual(detect_format(_header(ORIGINAL_FIXTURE))["id"], "original")

    def test_wahealth_dict(self):
        self.assertEqual(detect_format(_header(DICT_FIXTURE))["id"], "wahealth_dict_2026_04_30")

    def test_kc_mft(self):
        self.assertEqual(detect_format(_header(KC_FIXTURE))["id"], "kc_mft_2026_05_11")

    def test_variable_catalog_is_unrecognized(self):
        # The variable-catalog reference file is documentation, not data.
        with self.assertRaises(UnrecognizedFormatError):
            detect_format(_header(CATALOG_FILE))

    def test_unknown_header_is_unrecognized(self):
        with self.assertRaises(UnrecognizedFormatError):
            detect_format(["foo", "bar", "baz"])


class TestParseRowsOriginal(unittest.TestCase):
    def test_count_and_values(self):
        descriptor, records = _read(ORIGINAL_FIXTURE)
        self.assertEqual(descriptor["id"], "original")
        self.assertEqual(len(records), 2)
        first = records[0]
        self.assertEqual(first["facility_name"], "Pilot Hospital")
        self.assertEqual(first["facility_guid"], "570b2e3f-a5a1-ed11-aad0-001dd80708be")
        self.assertEqual(first["reporting_date"], datetime.date(2025, 10, 20))
        # icu_beds_adult_currently_occupied=4, icu_beds_adult_capacity=3 in row 1
        self.assertEqual(first["adult_icu_occ"], 4)
        self.assertEqual(first["adult_icu_cap"], 3)


class TestParseRowsKcMft(unittest.TestCase):
    def test_nine_rows_across_facilities(self):
        descriptor, records = _read(KC_FIXTURE)
        self.assertEqual(descriptor["id"], "kc_mft_2026_05_11")
        self.assertEqual(descriptor["multi_facility"], True)
        self.assertEqual(len(records), 9)
        names = {r["facility_name"] for r in records}
        self.assertIn("Seaside Medical Center", names)
        self.assertIn("Nordic Issaquah", names)
        # Seaside appears for three distinct reporting dates
        seaside_dates = sorted(r["reporting_date"] for r in records if r["facility_name"] == "Seaside Medical Center")
        self.assertEqual(len(seaside_dates), 3)
        for r in records:
            self.assertIsNone(r["facility_guid"])

    def test_first_row_values(self):
        _descriptor, records = _read(KC_FIXTURE)
        r0 = records[0]
        self.assertEqual(r0["facility_name"], "Catholic Health St. Augustine Hospital")
        self.assertEqual(r0["reporting_date"], datetime.date(2026, 4, 26))
        # "ICU Adult Occupancy"=6, "ICU Adult Capacity"=10
        self.assertEqual(r0["adult_icu_occ"], 6)
        self.assertEqual(r0["adult_icu_cap"], 10)
        # "Acute Adult Occupancy"=102, "Acute Adult Capacity"=120
        self.assertEqual(r0["adult_acute_occ"], 102)
        self.assertEqual(r0["adult_acute_cap"], 120)


class TestParseRowsWaHealthDict(unittest.TestCase):
    def test_values_come_from_area_columns_not_totals(self):
        descriptor, records = _read(DICT_FIXTURE)
        self.assertEqual(descriptor["id"], "wahealth_dict_2026_04_30")
        self.assertEqual(len(records), 2)
        r0 = records[0]
        self.assertEqual(r0["facility_name"], "Pilot Dictionary Hospital")
        self.assertEqual(r0["reporting_date"], datetime.date(2026, 4, 29))
        # adult_acute_occ=40, adult_acute_cap=60 ; adult_icu_occ=20, adult_icu_cap=30
        self.assertEqual(r0["adult_acute_occ"], 40)
        self.assertEqual(r0["adult_icu_occ"], 20)
        # The fixture's all_inpatient_occ/cap are deliberately wrong (777/888);
        # the AllBeds aggregate must be the raw sum of areas, not those totals.
        gm = {g["id"]: g["population"][0]["count"] for g in compute_groups(r0)}
        raw_occ_sum = sum(r0[f"{a}_occ"] for a in
                          ["adult_icu", "peds_icu", "adult_acute", "peds_acute",
                           "neonatal_icu", "nursery", "surge", "other"])
        self.assertEqual(gm["AllBedsOccupied-bed-capacity-group"], raw_occ_sum)
        self.assertNotEqual(gm["AllBedsOccupied-bed-capacity-group"], 777)

    def test_hrd_columns_are_ignored(self):
        # covid_*/flu_*/rsv_* columns exist in the fixture but are not in the
        # descriptor's column map, so they never reach the normalized row.
        descriptor, records = _read(DICT_FIXTURE)
        mapped_cols = set()
        for occ, cap in descriptor["bed_columns"].values():
            mapped_cols.update((occ, cap))
        mapped_cols.update({descriptor["facility_name_col"], descriptor["reporting_date_col"],
                            descriptor["adult_ed_col"], descriptor["peds_ed_col"]})
        self.assertNotIn("covid_hospitalized", mapped_cols)
        self.assertNotIn("flu_hospitalized", mapped_cols)
        self.assertNotIn("rsv_hospitalized", mapped_cols)
        self.assertNotIn("all_inpatient_occ", mapped_cols)
        # And the normalized record has no covid_*/flu_*/rsv_*/all_inpatient_* keys.
        for key in records[0]:
            self.assertFalse(key.startswith(("covid_", "flu_", "rsv_", "all_inpatient_")))


class TestParseRowsErrors(unittest.TestCase):
    def test_missing_required_column_raises(self):
        # Original descriptor expects reporting_date; a header lacking it but with
        # facility_guid won't even be detected as original — so test parse_rows
        # directly with a reader whose fieldnames are missing a mapped column.
        original = next(d for d in SUPPORTED_FORMATS if d["id"] == "original")

        class FakeReader:
            fieldnames = ["facility_guid", "reporting_date", "facility_name"]  # missing bed/ED columns

            def __iter__(self):
                return iter([])

        with self.assertRaises(ValueError):
            parse_rows(FakeReader(), original)

    def test_no_data_rows_raises(self):
        original = next(d for d in SUPPORTED_FORMATS if d["id"] == "original")

        class FakeReader:
            fieldnames = list(_header(ORIGINAL_FIXTURE))

            def __iter__(self):
                return iter([])

        with self.assertRaises(ValueError):
            parse_rows(FakeReader(), original)


class TestResolveFacilityProfile(unittest.TestCase):
    def setUp(self):
        self.config = load_config(CONFIG)
        self.kc_descriptor = next(d for d in SUPPORTED_FORMATS if d["id"] == "kc_mft_2026_05_11")
        self.original_descriptor = next(d for d in SUPPORTED_FORMATS if d["id"] == "original")

    def test_single_facility_uses_top_level_config(self):
        record = {"facility_name": "Whatever"}
        profile, unregistered = resolve_facility_profile(record, self.config, self.original_descriptor)
        self.assertFalse(unregistered)
        self.assertIs(profile["organization"], self.config["organization"])
        self.assertIs(profile["location"], self.config["location"])

    def test_registered_facility_uses_registry_entry(self):
        record = {"facility_name": "Seaside Medical Center"}
        profile, unregistered = resolve_facility_profile(record, self.config, self.kc_descriptor)
        self.assertFalse(unregistered)
        self.assertEqual(profile["organization"]["nhsn_org_id"], "10000001")

    def test_unregistered_facility_gets_sparse_profile(self):
        record = {"facility_name": "Nordic Issaquah"}
        profile, unregistered = resolve_facility_profile(record, self.config, self.kc_descriptor)
        self.assertTrue(unregistered)
        self.assertEqual(profile["organization"], {"name": "Nordic Issaquah"})
        self.assertEqual(profile["location"]["name"], "Nordic Issaquah")

    def test_unregistered_organization_uses_placeholder_nhsn_id(self):
        # Build the resource and check the identifier is NHSN-system with an
        # obviously-synthetic value (so it satisfies the SAFR profile's required slice).
        from convert import build_organization_resource
        record = {"facility_name": "Nordic Issaquah"}
        profile, unregistered = resolve_facility_profile(record, self.config, self.kc_descriptor)
        org = build_organization_resource(profile, unregistered)
        ident = org["identifier"][0]
        self.assertEqual(ident["system"], NHSN_SYSTEM)
        self.assertEqual(ident["value"], f"{UNREGISTERED_ORG_ID_PREFIX}nordic-issaquah")
        self.assertNotIn("nhsn_org_id", profile["organization"])  # config OrgID not used


class TestUnrecognizedInputExits(unittest.TestCase):
    """End-to-end: an unrecognized file exits non-zero, names the formats, writes no output."""

    def _run(self, csv_path, tmp_output):
        return subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "convert.py"), csv_path,
             "--config", CONFIG, "--output-dir", tmp_output],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )

    def test_variable_catalog_file_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out")
            result = self._run(CATALOG_FILE, out)
            self.assertNotEqual(result.returncode, 0)
            combined = result.stdout + result.stderr
            self.assertIn("Unrecognized CSV layout", combined)
            self.assertIn("Original WA Health format", combined)
            self.assertIn("2026-04-30 WA Health dictionary from KC", combined)
            self.assertIn("KC multi-hospital from MFT 2026-05-11", combined)
            self.assertFalse(os.path.exists(out), "output directory must not be created")

    def test_empty_file_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            empty = os.path.join(td, "empty.csv")
            open(empty, "w").close()
            out = os.path.join(td, "out")
            result = self._run(empty, out)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(os.path.exists(out), "output directory must not be created")


if __name__ == "__main__":
    unittest.main()
