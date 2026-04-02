# Research: Constitution v1.3.0 Repo Sync

**Branch**: `005-constitution-repo-sync` | **Date**: 2026-04-02

## R1: Unit Test Strategy for Single-File Converter

**Decision**: Use Python's built-in `unittest` module with tests in a `tests/` directory at the repo root. Import functions directly from `convert.py` in the repo root.

**Rationale**: 
- The constitution mandates zero runtime dependencies and prefers stdlib where sufficient. `unittest` is stdlib and fully adequate for testing pure computation functions.
- `convert.py` lives at the repo root (not in `src/`), so `tests/` at the repo root with `sys.path` manipulation or running via `python -m pytest` / `python -m unittest discover` handles imports cleanly.
- The constitution allows dev dependencies (pytest, etc.) but they aren't needed — `unittest` covers assertion, test discovery, and logging verification.

**Alternatives considered**:
- **pytest**: More ergonomic, but adds a dev dependency for no functional gain given the small number of test functions. Could be adopted later if test suite grows significantly.
- **doctest**: Too limited for testing edge cases like negative clamping and aggregate sums across multiple prefixes.

## R2: Importing from convert.py

**Decision**: Import `convert.py` functions directly. The module-level `SAFR_IG_VERSION` validation and `sys.exit(1)` on invalid version won't fire because the version is valid. The `if __name__ == "__main__"` guard protects `main()` from running on import.

**Rationale**: `convert.py` is designed as both a script and an importable module. Functions like `safe_int()`, `get_occupied_and_unoccupied()`, `parse_reporting_date()`, and `compute_groups()` are all module-level functions with no side effects. The only module-level side effect is the version regex check, which passes for the current `"1.0.0"` value.

**Alternatives considered**:
- **Extracting functions to a library module**: Constitution says extract only when file exceeds ~1000 lines. At ~819 lines, premature.
- **subprocess-based testing**: Would test the CLI but not individual functions. Not appropriate for unit tests on computation logic.

## R3: CLAUDE.md Known-Issue Filtering Update

**Decision**: Add a Step 4 subsection to the CLAUDE.md LLM Validation Pipeline that explicitly describes how to filter known upstream errors, referencing `known-validation-issues.md` and listing the specific error patterns to match (same as CI's `grep -v` patterns).

**Rationale**: Constitution v1.3.0 added: "LLM agents performing local validation SHOULD apply the same known-issue filtering as CI." The current CLAUDE.md Step 4 mentions known issues conceptually but doesn't provide the actual error patterns. An LLM agent needs the specific strings to match against validator output.

**Alternatives considered**:
- **Pointing LLM to CI yml**: Workable but indirect. LLM agents should have filtering guidance in their primary instruction file.
- **Embedding patterns in CLAUDE.md**: Slightly redundant with `known-validation-issues.md`, but necessary for LLM agents to act without reading multiple files. Reference the source file for maintenance.

## R4: CI IG Version Logging

**Decision**: The CI already logs the IG version (`echo "Validating against SAFR IG version:$SAFR_IG_VERSION"`). Add a space after the colon and include the version in the validation summary (pass/fail message). Minimal change.

**Rationale**: The constitution requires CI output to "record which version of the SAFR IG was used for validation." This is already done but could be clearer — include the version in both the pre-validation and post-validation log lines.

**Alternatives considered**:
- **GitHub Actions step summary**: Would add the version to the PR checks summary tab. Nice to have but not required by the constitution.
- **Artifact output**: Overkill for a version string that's already in the logs.

## R5: CI Unit Test Integration

**Decision**: Add a new `unit-test` job to `.github/workflows/ci.yml` that runs `python -m unittest discover -s tests -p "test_*.py"`. No additional dependencies needed.

**Rationale**: FR-007 requires unit tests to run as part of CI. A separate job keeps the test/lint/validate separation clear. Using `python -m unittest discover` is stdlib-only and matches the zero-dependency approach.

**Alternatives considered**:
- **Running tests in the existing lint job**: Mixes concerns. Separate jobs give clearer failure signals.
- **pytest in CI**: Would require `pip install pytest`. Unnecessary when `unittest` suffices.
