"""CSV input-format detection and normalization for convert.py.

Each descriptor in ``SUPPORTED_FORMATS`` maps one hospital CSV layout onto the
single *normalized row model* that ``convert.py``'s FHIR generation consumes, so
the conformance-critical code path never branches on which layout a row came
from. Detection is by header-column membership. Adding a new layout is a
data-only change here. See
``specs/008-multi-format-csv-input/contracts/input-formats.md``.

A NormalizedRow is a plain dict with: ``facility_name`` (str),
``facility_guid`` (str|None), ``reporting_date`` (datetime.date),
``{area}_occ`` / ``{area}_cap`` ints for each canonical bed area in
``ALL_BED_AREAS``, and ``adult_ed`` / ``peds_ed`` ints.

Stdlib only — no runtime dependencies.
"""

import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# Canonical bed-area names used throughout the converter. All eight participate
# in the AllBeds aggregate; the first seven are also reported individually.
ALL_BED_AREAS = [
    "adult_icu",
    "peds_icu",
    "adult_acute",
    "peds_acute",
    "neonatal_icu",
    "nursery",
    "surge",
    "other",
]


# --- Supported input formats ---
#
# A file is in format F if every column in F["detect_columns"] appears in its
# header row. The generic parser (parse_rows) and everything downstream are
# format-agnostic.

SUPPORTED_FORMATS = [
    {
        "id": "original",
        "display_name": "Original WA Health format",
        "detect_columns": ("facility_guid", "reporting_date"),
        "multi_facility": False,
        "has_guid": True,
        "date_formats": ("%m/%d/%Y",),
        "facility_name_col": "facility_name",
        "facility_guid_col": "facility_guid",
        "reporting_date_col": "reporting_date",
        "adult_ed_col": "previous_day_adult_emergency_department_visits",
        "peds_ed_col": "previous_day_pediatric_emergency_department_visits",
        "bed_columns": {
            "adult_icu": ("icu_beds_adult_currently_occupied", "icu_beds_adult_capacity"),
            "peds_icu": ("icu_beds_pediatric_currently_occupied", "icu_beds_pediatric_capacity"),
            "adult_acute": ("acute_beds_adult_currently_occupied", "acute_beds_adult_capacity"),
            "peds_acute": ("acute_beds_pediatric_currently_occupied", "acute_beds_pediatric_capacity"),
            "neonatal_icu": ("neonatal_icu_beds_currently_occupied", "neonatal_icu_beds_capacity"),
            "nursery": ("nursery_beds_currently_occupied", "nursery_beds_capacity"),
            "surge": ("beds_in_overflow_surge_expansion_areas_currently_occupied", "beds_in_overflow_surge_expansion_areas_capacity"),
            "other": ("beds_in_other_inpatient_areas_currently_occupied", "beds_in_other_inpatient_areas_capacity"),
        },
    },
    {
        "id": "wahealth_dict_2026_04_30",
        "display_name": "2026-04-30 WA Health dictionary from KC",
        "detect_columns": ("facility", "reportingday"),
        "multi_facility": False,
        "has_guid": False,
        "date_formats": ("%Y-%m-%d", "%m/%d/%Y"),
        "facility_name_col": "facility",
        "facility_guid_col": None,
        "reporting_date_col": "reportingday",
        "adult_ed_col": "prevd_adult_ed",
        "peds_ed_col": "prevd_ped_ed",
        "bed_columns": {
            "adult_icu": ("adult_icu_occ", "adult_icu_cap"),
            "peds_icu": ("ped_icu_occ", "ped_icu_cap"),
            "adult_acute": ("adult_acute_occ", "adult_acute_cap"),
            "peds_acute": ("ped_acute_occ", "ped_acute_cap"),
            "neonatal_icu": ("neon_icu_occ", "neon_icu_cap"),
            "nursery": ("nursery_occ", "nursery_cap"),
            "surge": ("surge_occ", "surge_cap"),
            "other": ("other_occ", "other_cap"),
        },
        # Precomputed all-inpatient total carried by this format only. The
        # per-area columns above are authoritative; this total is never used as a
        # data source, but parse_rows reconciles it against the computed sum and
        # warns on mismatch. (occ_col, cap_col)
        "total_columns": ("all_inpatient_occ", "all_inpatient_cap"),
    },
    {
        "id": "kc_mft_2026_05_11",
        "display_name": "KC multi-hospital from MFT 2026-05-11",
        "detect_columns": ("Facility", "Reporting Date"),
        "multi_facility": True,
        "has_guid": False,
        "date_formats": ("%Y-%m-%d", "%m/%d/%Y"),
        "facility_name_col": "Facility",
        "facility_guid_col": None,
        "reporting_date_col": "Reporting Date",
        "adult_ed_col": "Previous Day Adult ED Visits",
        "peds_ed_col": "Previous Day Pediatric ED Visits",
        "bed_columns": {
            "adult_icu": ("ICU Adult Occupancy", "ICU Adult Capacity"),
            "peds_icu": ("ICU Pediatric Occupancy", "ICU Pediatric Capacity"),
            "adult_acute": ("Acute Adult Occupancy", "Acute Adult Capacity"),
            "peds_acute": ("Acute Pediatric Occupancy", "Acute Pediatric Capacity"),
            "neonatal_icu": ("Neonatal ICU Beds Currently in Use", "Neonatal ICU Beds Capacity"),
            "nursery": ("Nursery Current Occupancy", "Nursery Staffed Bed Capacity"),
            "surge": ("Surge Beds Currently in Use", "Surge Beds Capacity"),
            "other": ("Adult Other Inpatient Beds Currently in Use", "Adult Other Inpatient Beds Capacity"),
        },
    },
]


class UnrecognizedFormatError(Exception):
    """Raised when a CSV header matches none of the supported input formats."""


def slugify(name):
    """Lowercase, collapse runs of non-alphanumerics to '-', strip leading/trailing '-'.

    Used for placeholder identifier values and for the stable facility key when a
    format carries no GUID. Distinct from convert.sanitize_filename.
    """
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def supported_formats_summary():
    """Human-readable list of supported format display names."""
    return "; ".join(d["display_name"] for d in SUPPORTED_FORMATS)


def detect_format(header):
    """Return the descriptor for the first supported format matching `header`.

    Raises UnrecognizedFormatError if none match.
    """
    cols = set(header or [])
    for descriptor in SUPPORTED_FORMATS:
        if all(c in cols for c in descriptor["detect_columns"]):
            return descriptor
    raise UnrecognizedFormatError(
        f"CSV header columns {sorted(cols)} match no supported format"
    )


def safe_int(value):
    """Parse a string to int, defaulting to 0 for empty/missing values."""
    if value is None or value.strip() == "":
        return 0
    return int(value)


def parse_date_flexible(value, formats):
    """Parse a date string against each strptime pattern in order; return a date.

    Raises ValueError naming the patterns if none match.
    """
    s = (value or "").strip()
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"could not parse date {value!r}; tried format(s): {', '.join(formats)}"
    )


def _required_source_columns(descriptor):
    """All CSV column names this descriptor reads."""
    cols = [
        descriptor["facility_name_col"],
        descriptor["reporting_date_col"],
        descriptor["adult_ed_col"],
        descriptor["peds_ed_col"],
    ]
    if descriptor["has_guid"]:
        cols.append(descriptor["facility_guid_col"])
    for occ_col, cap_col in descriptor["bed_columns"].values():
        cols.append(occ_col)
        cols.append(cap_col)
    return cols


def _reconcile_totals(record, raw, descriptor):
    """Warn when a format's precomputed all-inpatient total disagrees with the
    sum of the per-area columns.

    The per-area values are authoritative and the aggregate is always derived
    from them; this check only surfaces an inconsistency in the source data. It
    is a no-op for formats without a ``total_columns`` entry and is skipped when
    the source leaves the total blank.
    """
    total_cols = descriptor.get("total_columns")
    if not total_cols:
        return
    occ_col, cap_col = total_cols
    for source_col, area_suffix, label in (
        (occ_col, "_occ", "occupied"),
        (cap_col, "_cap", "capacity"),
    ):
        raw_value = raw.get(source_col)
        if raw_value is None or raw_value.strip() == "":
            continue  # source omitted the total — nothing to reconcile
        source_total = int(raw_value)
        computed = sum(record[f"{area}{area_suffix}"] for area in descriptor["bed_columns"])
        if source_total != computed:
            logger.warning(
                "Source %s total (%s=%d) disagrees with the sum of per-area "
                "columns (%d) for facility %r on %s; using the per-area sum.",
                label,
                source_col,
                source_total,
                computed,
                record["facility_name"],
                record["reporting_date"].isoformat(),
            )


def parse_rows(reader, descriptor):
    """Map a csv.DictReader over a known format to a list of NormalizedRow dicts.

    Raises ValueError if a required column is absent from the header, if a date
    cannot be parsed, or if there are no data rows.
    """
    fieldnames = reader.fieldnames or []
    missing = [c for c in _required_source_columns(descriptor) if c not in fieldnames]
    if missing:
        raise ValueError(
            f"format {descriptor['display_name']!r} expects column(s) {missing} "
            "which are missing from the CSV header"
        )

    records = []
    for raw in reader:
        record = {
            "facility_name": (raw.get(descriptor["facility_name_col"]) or "").strip(),
            "facility_guid": (
                (raw.get(descriptor["facility_guid_col"]) or "").strip()
                if descriptor["has_guid"] else None
            ),
            "reporting_date": parse_date_flexible(
                raw.get(descriptor["reporting_date_col"]), descriptor["date_formats"]
            ),
            "adult_ed": safe_int(raw.get(descriptor["adult_ed_col"])),
            "peds_ed": safe_int(raw.get(descriptor["peds_ed_col"])),
        }
        for area, (occ_col, cap_col) in descriptor["bed_columns"].items():
            record[f"{area}_occ"] = safe_int(raw.get(occ_col))
            record[f"{area}_cap"] = safe_int(raw.get(cap_col))
        _reconcile_totals(record, raw, descriptor)
        records.append(record)

    if not records:
        raise ValueError("CSV file contains no data rows")
    return records
