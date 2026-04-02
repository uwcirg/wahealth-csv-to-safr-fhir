# Quickstart: Constitution Alignment

**Date**: 2026-04-01  
**Feature**: 001-constitution-alignment

## What This Feature Changes

This feature brings the repository into compliance with its constitution by adding:

1. **`.gitignore`** — prevents secrets and generated files from being committed
2. **GitHub Actions CI pipeline** — automated lint, FHIR validation, and secret scanning on every PR
3. **`config.example.json` updates** — obvious placeholder values for server credentials
4. **Lint configuration** — `ruff.toml` for consistent Python style

## Files to Create

| File | Purpose |
| ---- | ------- |
| `.gitignore` | Exclude secrets, caches, generated output |
| `.github/workflows/ci.yml` | CI pipeline (lint + FHIR validate + secret scan) |
| `ruff.toml` | Linter configuration |

## Files to Modify

| File | Change |
| ---- | ------ |
| `config.example.json` | Replace empty strings with `YOUR_*` placeholders in server section |

## How to Verify Locally

```bash
# 1. Check .gitignore works
echo "test" > config.json
git status  # config.json should NOT appear

# 2. Run linter
pip install ruff
ruff check convert.py

# 3. Run converter against test fixture
python3 convert.py input/2025.10.21.Test.Facility.BedCapacity.csv --config config.example.json

# 4. Validate output (requires Java 17+)
java -jar validator_cli.jar output/**/*.json -version 4.0.1 -ig hl7.fhir.us.safr
```

## CI Pipeline Overview

The GitHub Actions workflow runs on all PRs to `main`:

1. **Lint** — `ruff check convert.py` (fast, ~1 second)
2. **FHIR Validate** — Run converter, then validate output Bundles with HL7 FHIR Reference Validator (slower, ~2-5 minutes with caching)
3. **Secret Scan** — `gitleaks` checks for committed credentials
