"""End-to-end tests for the per-facility output layout and the --bundles-mrs-only flag.

Covers spec 009: individual resource files live in output/{date}/{facility}/ (never
loose in the date directory), multi-facility input does not overwrite one facility's
resources with another's, and --bundles-mrs-only restricts local output to the Bundle
and MeasureReport.json.
"""

import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

# Per-run volatile values the converter generates (random UUIDs and a wall-clock timestamp);
# normalized away when comparing FHIR content across runs.
_UUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?")


def _normalized_json_text(path):
    with open(path) as f:
        text = f.read()
    return _TS_RE.sub("<TS>", _UUID_RE.sub("<UUID>", text))

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
CONFIG = os.path.join(REPO_ROOT, "config.example.json")
SINGLE_FACILITY_FIXTURE = os.path.join(REPO_ROOT, "input", "2025.10.21.Test.Facility.BedCapacity.csv")
MULTI_FACILITY_FIXTURE = os.path.join(REPO_ROOT, "input", "census_20260511.FromKC.SubsetObfsctd.csv")

INDIVIDUAL_RESOURCE_NAMES = {"Organization.json", "Device.json", "Location.json", "MeasureReport.json"}
SKIPPED_WHEN_BUNDLES_MRS_ONLY = {"Organization.json", "Device.json", "Location.json"}


def _run_convert(csv_path, output_dir, *extra_args):
    return subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, "convert.py"), csv_path,
         "--config", CONFIG, "--output-dir", output_dir, *extra_args],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )


def _date_dirs(output_dir):
    return sorted(
        os.path.join(output_dir, d) for d in os.listdir(output_dir)
        if os.path.isdir(os.path.join(output_dir, d))
    )


def _facility_dirs(date_dir):
    return sorted(
        os.path.join(date_dir, d) for d in os.listdir(date_dir)
        if os.path.isdir(os.path.join(date_dir, d))
    )


def _bundle_files(date_dir):
    return sorted(glob.glob(os.path.join(date_dir, "*.BedCapacity.json")))


def _loose_json_in_date_dir(date_dir):
    """JSON files sitting directly in the date directory other than the Bundle files."""
    return sorted(
        f for f in glob.glob(os.path.join(date_dir, "*.json"))
        if not f.endswith(".BedCapacity.json")
    )


class TestPerFacilityLayout(unittest.TestCase):
    def test_single_facility_layout(self):
        """Bundle in the date dir; the four individual resources in output/{date}/{facility}/."""
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out")
            result = _run_convert(SINGLE_FACILITY_FIXTURE, out)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            date_dirs = _date_dirs(out)
            self.assertTrue(date_dirs, "expected at least one date directory")
            for date_dir in date_dirs:
                bundles = _bundle_files(date_dir)
                self.assertTrue(bundles, f"expected a Bundle file in {date_dir}")
                self.assertEqual(
                    _loose_json_in_date_dir(date_dir), [],
                    f"individual resources must not be written loose in {date_dir}",
                )
                facility_dirs = _facility_dirs(date_dir)
                self.assertTrue(facility_dirs, f"expected a per-facility subdir in {date_dir}")
                for facility_dir in facility_dirs:
                    present = set(os.listdir(facility_dir))
                    self.assertEqual(
                        present, INDIVIDUAL_RESOURCE_NAMES,
                        f"{facility_dir} should hold exactly the four individual resources",
                    )

    def test_multi_facility_no_overwrite(self):
        """Each facility gets its own subdir; resources are not overwritten across facilities."""
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out")
            result = _run_convert(MULTI_FACILITY_FIXTURE, out)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            max_facilities_in_a_date_dir = 0
            for date_dir in _date_dirs(out):
                self.assertEqual(
                    _loose_json_in_date_dir(date_dir), [],
                    f"individual resources must not be written loose in {date_dir}",
                )
                facility_dirs = _facility_dirs(date_dir)
                self.assertTrue(facility_dirs, f"expected per-facility subdirs in {date_dir}")
                max_facilities_in_a_date_dir = max(max_facilities_in_a_date_dir, len(facility_dirs))

                # Within one date directory, each facility subdir must hold its own complete set of
                # individual resources with a distinct Organization — i.e. nothing was overwritten.
                org_identities = []
                for facility_dir in facility_dirs:
                    self.assertEqual(set(os.listdir(facility_dir)), INDIVIDUAL_RESOURCE_NAMES,
                                     f"{facility_dir} should hold exactly the four individual resources")
                    with open(os.path.join(facility_dir, "Organization.json")) as f:
                        org = json.load(f)
                    org_identities.append(json.dumps(org.get("identifier"), sort_keys=True))
                self.assertEqual(len(org_identities), len(set(org_identities)),
                                 f"facilities in {date_dir} must each have their own Organization")

            # The fixture is multi-facility, so at least one date directory must contain >1 facility
            # subdir — exactly the case that previously caused individual-resource overwrites.
            self.assertGreater(max_facilities_in_a_date_dir, 1,
                               "expected a date directory with multiple facility subdirectories")

    def test_facility_subdir_name_matches_bundle_filename_segment(self):
        """The facility subdir name equals the {facility} segment of that facility's Bundle filename."""
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out")
            result = _run_convert(MULTI_FACILITY_FIXTURE, out)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for date_dir in _date_dirs(out):
                date_str = os.path.basename(date_dir)
                subdir_names = {os.path.basename(d) for d in _facility_dirs(date_dir)}
                bundle_facility_segments = {
                    os.path.basename(b)[: -len(f".{date_str}.BedCapacity.json")]
                    for b in _bundle_files(date_dir)
                }
                self.assertEqual(subdir_names, bundle_facility_segments)


class TestBundlesMrsOnly(unittest.TestCase):
    def test_bundles_mrs_only_skips_org_device_location(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out")
            result = _run_convert(MULTI_FACILITY_FIXTURE, out, "--bundles-mrs-only")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            for date_dir in _date_dirs(out):
                self.assertTrue(_bundle_files(date_dir), f"expected Bundle file(s) in {date_dir}")
                for facility_dir in _facility_dirs(date_dir):
                    self.assertEqual(set(os.listdir(facility_dir)), {"MeasureReport.json"},
                                     f"{facility_dir} should hold only MeasureReport.json")

            for name in SKIPPED_WHEN_BUNDLES_MRS_ONLY:
                hits = glob.glob(os.path.join(out, "**", name), recursive=True)
                self.assertEqual(hits, [], f"{name} should not be written anywhere under {out}")

    def test_default_writes_full_individual_resource_set(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "out")
            result = _run_convert(SINGLE_FACILITY_FIXTURE, out)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for date_dir in _date_dirs(out):
                for facility_dir in _facility_dirs(date_dir):
                    self.assertEqual(set(os.listdir(facility_dir)), INDIVIDUAL_RESOURCE_NAMES)

    def test_help_lists_flag(self):
        result = subprocess.run(
            [sys.executable, os.path.join(REPO_ROOT, "convert.py"), "--help"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--bundles-mrs-only", result.stdout)

    def test_flag_does_not_change_bundle_bytes(self):
        """FR-008a: --bundles-mrs-only must not alter Bundle (or MeasureReport) contents."""
        with tempfile.TemporaryDirectory() as td:
            out_full = os.path.join(td, "full")
            out_only = os.path.join(td, "only")
            r1 = _run_convert(MULTI_FACILITY_FIXTURE, out_full)
            r2 = _run_convert(MULTI_FACILITY_FIXTURE, out_only, "--bundles-mrs-only")
            self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)

            def relative_json(root):
                return sorted(
                    os.path.relpath(p, root)
                    for p in glob.glob(os.path.join(root, "**", "*.json"), recursive=True)
                )

            # Compare modulo the per-run volatile values (random UUIDs and the wall-clock
            # Bundle timestamp) the converter regenerates on every run.
            full_bundles = [p for p in relative_json(out_full) if p.endswith(".BedCapacity.json")]
            only_bundles = [p for p in relative_json(out_only) if p.endswith(".BedCapacity.json")]
            self.assertEqual(full_bundles, only_bundles)
            self.assertTrue(full_bundles)
            for rel in full_bundles:
                self.assertEqual(_normalized_json_text(os.path.join(out_full, rel)),
                                 _normalized_json_text(os.path.join(out_only, rel)),
                                 f"Bundle content differs for {rel}")

            # MeasureReport.json should also match (modulo volatile values) between the two modes.
            full_mrs = [p for p in relative_json(out_full) if os.path.basename(p) == "MeasureReport.json"]
            only_mrs = [p for p in relative_json(out_only) if os.path.basename(p) == "MeasureReport.json"]
            self.assertEqual(full_mrs, only_mrs)
            self.assertTrue(full_mrs)
            for rel in full_mrs:
                self.assertEqual(_normalized_json_text(os.path.join(out_full, rel)),
                                 _normalized_json_text(os.path.join(out_only, rel)),
                                 f"MeasureReport content differs for {rel}")


if __name__ == "__main__":
    unittest.main()
