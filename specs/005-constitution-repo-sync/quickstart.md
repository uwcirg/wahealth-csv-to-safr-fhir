# Quickstart: Constitution v1.3.0 Repo Sync

**Branch**: `005-constitution-repo-sync` | **Date**: 2026-04-02

## What This Feature Does

Brings the repository into full alignment with constitution v1.3.0 by:
1. Adding unit tests for computation functions (constitution: Validation-Driven Testing)
2. Updating CLAUDE.md with known-issue filtering guidance (constitution v1.3.0: LLM filtering parity)
3. Improving CI IG version logging and adding a unit test job (constitution: CI Pipeline)

## Files Changed

| File | Change |
|------|--------|
| `tests/test_compute.py` | **New** — Unit tests for `safe_int`, `get_occupied_and_unoccupied`, `parse_reporting_date`, `compute_groups` |
| `CLAUDE.md` | **Modified** — Add known-issue filtering patterns to Step 4 of LLM Validation Pipeline |
| `.github/workflows/ci.yml` | **Modified** — Add `unit-test` job, improve IG version logging |

## How to Run Unit Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## How to Verify CLAUDE.md Changes

Read the updated Step 4 in CLAUDE.md and confirm it references `known-validation-issues.md` and includes the specific error patterns that should be filtered (matching the CI's `grep -v` patterns).

## How to Verify CI Changes

Push the branch and check the GitHub Actions run. Verify:
- A new "Unit Tests" job appears and passes
- The "FHIR Validation" job logs the IG version prominently before and after validation
