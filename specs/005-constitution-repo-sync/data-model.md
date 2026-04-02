# Data Model: Constitution v1.3.0 Repo Sync

**Branch**: `005-constitution-repo-sync` | **Date**: 2026-04-02

## Entities

### Test Case (unit test context)

Represents a single test scenario for a computation function.

| Field | Description |
|-------|-------------|
| Input | A CSV row dict (or subset), function arguments |
| Expected Output | The computed value or structure |
| Edge Condition | What boundary or error case is being tested |

No persistent data model changes. This feature adds test code and documentation, not data structures.

### CSV Row (existing, tested entity)

The CSV row dict is the primary input to all tested functions. Key columns used by computation functions:

| Column Pattern | Used By |
|----------------|---------|
| `{prefix}_currently_occupied` | `get_occupied_and_unoccupied()` |
| `{prefix}_capacity` | `get_occupied_and_unoccupied()` |
| `previous_day_adult_emergency_department_visits` | `compute_groups()` |
| `previous_day_pediatric_emergency_department_visits` | `compute_groups()` |
| `reporting_date` | `parse_reporting_date()` |

Where `{prefix}` is one of the 8 values in `ALL_BED_PREFIXES`.

### MeasureReport Group (existing, tested entity)

Output of `compute_groups()`. Each group is a dict with:

| Field | Description |
|-------|-------------|
| `id` | `{ConceptName}-bed-capacity-group` |
| `code.coding[0].code` | LOINC code from `LOINC_CODES` dict |
| `population[0].count` | Integer count (occupied, unoccupied, or aggregate) |

Expected: 25 groups total (14 direct + 3 ED + 8 aggregate).

## Validation Rules

- `safe_int()`: Returns 0 for `None`, empty string, whitespace-only string. Returns `int(value)` otherwise. Raises `ValueError` for non-numeric non-empty strings (current behavior — tests should verify this).
- `get_occupied_and_unoccupied()`: Unoccupied = `max(0, capacity - occupied)`. Never negative.
- `compute_groups()`: Always returns exactly 25 groups. Aggregate sums computed from raw CSV via `get_occupied_and_unoccupied()`, not from intermediate group values.
- `parse_reporting_date()`: Accepts `MM/DD/YYYY` format. Returns `datetime.date` object.
