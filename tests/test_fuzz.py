"""Unit tests for count fuzzing in convert.py.

Fuzzing perturbs the base count fields of a normalized row (bed `_occ`/`_cap` and the ED
census fields) so the FHIR output carries realistic-but-fake counts. These tests assert the
realism invariants (non-negative ints, occupied <= capacity, aggregate == sum of fuzzed
parts), determinism under a seed, and the disabled-is-identity guarantee.
"""

import datetime
import os
import sys
import unittest

# Ensure repo root is on the path so we can import the modules under test.
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, REPO_ROOT)

from csv_formats import ALL_BED_AREAS  # noqa: E402
from convert import (  # noqa: E402
    FuzzConfig,
    compute_groups,
    fuzz_record,
)


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


def _count_fields(record):
    """All count-field keys on a normalized row."""
    keys = list(FUZZ_ED_KEYS)
    for area in ALL_BED_AREAS:
        keys += [f"{area}_occ", f"{area}_cap"]
    return [k for k in keys if k in record]


FUZZ_ED_KEYS = ("adult_ed", "peds_ed")


class TestFuzzDisabledIsIdentity(unittest.TestCase):
    """US2: with fuzzing off (the default), output is unchanged."""

    def test_disabled_returns_identical_counts(self):
        record, _ = _make_record()
        out = fuzz_record(record, FuzzConfig(enabled=False))
        for key in _count_fields(record):
            self.assertEqual(out[key], record[key], f"{key} changed while fuzzing disabled")

    def test_default_fuzzconfig_is_disabled(self):
        self.assertFalse(FuzzConfig().enabled)


class TestFuzzInvariants(unittest.TestCase):
    """US1: realism constraints on the fuzzed counts."""

    def setUp(self):
        self.record, self.bed_data = _make_record()
        self.cfg = FuzzConfig(enabled=True, seed=12345)
        self.fuzzed = fuzz_record(self.record, self.cfg)

    def test_all_counts_non_negative_integers(self):
        for key in _count_fields(self.record):
            val = self.fuzzed[key]
            self.assertIsInstance(val, int, f"{key} is not an int")
            self.assertGreaterEqual(val, 0, f"{key} is negative")

    def test_occupied_not_exceeding_capacity_when_source_consistent(self):
        for area, (occ, cap) in self.bed_data.items():
            if occ <= cap:  # source consistent → fuzzed must stay consistent
                self.assertLessEqual(
                    self.fuzzed[f"{area}_occ"], self.fuzzed[f"{area}_cap"],
                    f"{area}: fuzzed occupied exceeds fuzzed capacity",
                )

    def test_aggregates_equal_sum_of_fuzzed_parts(self):
        # compute_groups derives aggregates from the (fuzzed) base fields, so each
        # aggregate must equal the sum of its fuzzed components — no contradictions.
        gm = {g["id"]: g["population"][0]["count"] for g in compute_groups(self.fuzzed)}
        self.assertEqual(
            gm["AllBedsOccupied-bed-capacity-group"],
            sum(self.fuzzed[f"{a}_occ"] for a in ALL_BED_AREAS),
        )
        self.assertEqual(
            gm["AllBedsUnoccupied-bed-capacity-group"],
            sum(max(0, self.fuzzed[f"{a}_cap"] - self.fuzzed[f"{a}_occ"]) for a in ALL_BED_AREAS),
        )
        self.assertEqual(
            gm["AdultTotalOccupied-bed-capacity-group"],
            self.fuzzed["adult_icu_occ"] + self.fuzzed["adult_acute_occ"],
        )
        self.assertEqual(
            gm["TotalEDCensus-bed-capacity-group"],
            self.fuzzed["adult_ed"] + self.fuzzed["peds_ed"],
        )

    def test_counts_are_obfuscated(self):
        # The full set of true counts must not survive intact; most non-zero counts change.
        true = {k: self.record[k] for k in _count_fields(self.record)}
        fuzz = {k: self.fuzzed[k] for k in _count_fields(self.record)}
        self.assertNotEqual(true, fuzz, "fuzzing left every count unchanged")
        changed = sum(1 for k in true if true[k] != fuzz[k] and true[k] > 0)
        nonzero = sum(1 for k in true if true[k] > 0)
        self.assertGreater(changed, nonzero // 2, "fewer than half of non-zero counts changed")


class TestFuzzMagnitudeAndEdgeCases(unittest.TestCase):
    """US1: perturbation stays in a realistic neighborhood; zero/small-count handling."""

    def test_large_counts_within_magnitude(self):
        # A large count perturbed proportionally must stay within +/- magnitude (+1 for
        # rounding). Use a value well above the small-count threshold.
        mag = 0.15
        cfg = FuzzConfig(enabled=True, seed=7, magnitude=mag)
        record = {
            "facility_name": "Big", "reporting_date": datetime.date(2026, 1, 1),
            "adult_acute_occ": 300, "adult_acute_cap": 350, "adult_ed": 180, "peds_ed": 0,
        }
        out = fuzz_record(record, cfg)
        for key, true in (("adult_acute_cap", 350), ("adult_ed", 180)):
            self.assertLessEqual(abs(out[key] - true), round(true * mag) + 1,
                                 f"{key} moved beyond +/-{mag}")

    def test_true_zero_stays_zero(self):
        cfg = FuzzConfig(enabled=True, seed=7)
        record = {
            "facility_name": "Z", "reporting_date": datetime.date(2026, 1, 1),
            "peds_icu_occ": 0, "peds_icu_cap": 0, "adult_ed": 0, "peds_ed": 0,
        }
        out = fuzz_record(record, cfg)
        self.assertEqual(out["peds_icu_occ"], 0)
        self.assertEqual(out["peds_icu_cap"], 0)
        self.assertEqual(out["adult_ed"], 0)

    def test_small_counts_are_changed(self):
        # Small non-zero counts must be obfuscated, not left equal to the truth. Check
        # across several seeds that a small value generally moves.
        moved = 0
        for seed in range(20):
            cfg = FuzzConfig(enabled=True, seed=seed)
            record = {
                "facility_name": "S", "reporting_date": datetime.date(2026, 1, 1),
                "surge_occ": 2, "surge_cap": 3, "adult_ed": 1, "peds_ed": 2,
            }
            out = fuzz_record(record, cfg)
            if out["adult_ed"] != 1 or out["surge_occ"] != 2:
                moved += 1
        self.assertGreater(moved, 15, "small counts were rarely obfuscated")

    def test_only_count_fields_change(self):
        # Non-count fields must be passed through untouched (FR-011).
        record, _ = _make_record()
        out = fuzz_record(record, FuzzConfig(enabled=True, seed=1))
        for key in ("facility_name", "facility_guid", "reporting_date"):
            self.assertEqual(out[key], record[key])


class TestFuzzDeterminism(unittest.TestCase):
    """US3: reproducibility under a seed; order independence."""

    def test_same_seed_same_output(self):
        record, _ = _make_record()
        a = fuzz_record(record, FuzzConfig(enabled=True, seed=999))
        b = fuzz_record(record, FuzzConfig(enabled=True, seed=999))
        self.assertEqual(a, b)

    def test_different_seed_different_output(self):
        record, _ = _make_record()
        a = fuzz_record(record, FuzzConfig(enabled=True, seed=1))
        b = fuzz_record(record, FuzzConfig(enabled=True, seed=2))
        a_counts = {k: a[k] for k in _count_fields(record)}
        b_counts = {k: b[k] for k in _count_fields(record)}
        self.assertNotEqual(a_counts, b_counts)

    def test_row_order_independence(self):
        # A row fuzzed alone reproduces the same counts it gets within a multi-row batch,
        # because the per-row PRNG is keyed by the row's stable identity, not call order.
        cfg = FuzzConfig(enabled=True, seed=555)
        rec_a, _ = _make_record()
        rec_b, _ = _make_record()
        rec_b["facility_name"] = "Other Facility"
        rec_b["facility_guid"] = "other-guid"

        alone = fuzz_record(rec_a, cfg)
        # Process a different row first, then rec_a — order must not matter.
        fuzz_record(rec_b, cfg)
        in_batch = fuzz_record(rec_a, cfg)
        self.assertEqual(alone, in_batch)


if __name__ == "__main__":
    unittest.main()
