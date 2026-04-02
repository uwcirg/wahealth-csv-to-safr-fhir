# wahealth-csv-to-safr-fhir Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-02

## Active Technologies
- Python 3 (stdlib only at runtime) + None at runtime. Dev: `ruff` (linter), `validator_cli.jar` (FHIR validation), `gitleaks` (secret scanning) (002-ig-version-tracking)
- Filesystem — CSV input, JSON output, JSON config (002-ig-version-tracking)
- Python 3 (stdlib only at runtime) + None at runtime. Dev: `ruff`, `validator_cli.jar`, `gitleaks` (003-constitution-repo-update)
- Python 3 (stdlib only) + None at runtime (004-safr-ig-stu1-update)

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
- 005-constitution-repo-sync: Added Python 3 (stdlib only at runtime) + None at runtime. Dev: `ruff` (linter), `validator_cli.jar` (FHIR validation), `gitleaks` (secret scanning)
- 004-safr-ig-stu1-update: Added Python 3 (stdlib only) + None at runtime
- 003-constitution-repo-update: Added Python 3 (stdlib only at runtime) + None at runtime. Dev: `ruff`, `validator_cli.jar`, `gitleaks`


<!-- MANUAL ADDITIONS START -->

## LLM Validation Pipeline

LLM agents **MUST** run the following four-step FHIR validation pipeline before completing any development work that touches `convert.py`, configuration, or FHIR output. This matches the CI pipeline in `.github/workflows/ci.yml` exactly.

### Step 1: Convert test fixtures

Run the converter against all test CSV fixtures, excluding column-labels-only files (which contain headers but no data rows):

```bash
for csv in input/*.BedCapacity.csv; do
  case "$csv" in
    *column-labels-only*) continue ;;
  esac
  echo "Converting: $csv"
  python3 convert.py "$csv" --config config.example.json --output-dir output
done
```

### Step 2: Extract SAFR IG version

Extract the IG version from `convert.py` so the validator uses the correct profile version:

```bash
SAFR_IG_VERSION=$(grep -oP 'SAFR_IG_VERSION\s*=\s*"\K[^"]+' convert.py)
```

### Step 3: Validate FHIR Bundles

Run the FHIR validator against all generated output:

```bash
java -jar validator_cli.jar output/**/*.json \
  -version 4.0.1 \
  -ig hl7.fhir.us.safr#$SAFR_IG_VERSION
```

### Step 4: Zero project-introduced errors required

The validation **MUST** produce zero errors **not attributable to known upstream issues**. Warnings are acceptable.

**Known upstream error patterns to filter** (see `known-validation-issues.md` for full root-cause analysis):

1. `extension-MeasureReport.supplementalData` — DEQM v5.0.0 references an unresolvable R5 cross-version extension, causing slicing evaluation to fail on MeasureReport extensions.
2. `Slice 'Bundle.entry:measurereport': a matching slice is required` — Cascading failure from issue 1; the Bundle slice discriminator cannot validate the MeasureReport profile.

These are the same patterns filtered by CI's `grep -v` in `.github/workflows/ci.yml`. If the validator output contains **only** errors matching these two patterns, validation **passes**. Any error **not** matching these patterns is a project-introduced blocker — fix the issue and re-run the full pipeline from Step 1.

### Behavioral Requirements

- **Do NOT skip validation** to save time or defer to CI. The validation pipeline is mandatory before completing work.
- If `validator_cli.jar` or Java is not available in the local environment, **inform the user immediately** and explain that FHIR validation cannot be performed. Do not silently skip validation.

<!-- MANUAL ADDITIONS END -->
