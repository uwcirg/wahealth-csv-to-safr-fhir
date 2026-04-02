# wahealth-csv-to-safr-fhir Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-02

## Active Technologies
- Python 3 (stdlib only at runtime) + None at runtime. Dev: `ruff` (linter), `validator_cli.jar` (FHIR validation), `gitleaks` (secret scanning) (002-ig-version-tracking)
- Filesystem — CSV input, JSON output, JSON config (002-ig-version-tracking)

- Python 3 (stdlib only for runtime; dev tools use pip) + None at runtime. Dev: `ruff` (linter), `validator_cli.jar` (FHIR validation), `gitleaks` (secret scanning) (001-constitution-alignment)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3 (stdlib only for runtime; dev tools use pip): Follow standard conventions

## Recent Changes
- 002-ig-version-tracking: Added Python 3 (stdlib only at runtime) + None at runtime. Dev: `ruff` (linter), `validator_cli.jar` (FHIR validation), `gitleaks` (secret scanning)

- 001-constitution-alignment: Added Python 3 (stdlib only for runtime; dev tools use pip) + None at runtime. Dev: `ruff` (linter), `validator_cli.jar` (FHIR validation), `gitleaks` (secret scanning)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
