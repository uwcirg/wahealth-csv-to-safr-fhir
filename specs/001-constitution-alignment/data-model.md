# Data Model: Constitution Alignment

**Date**: 2026-04-01  
**Feature**: 001-constitution-alignment

## Overview

This feature introduces no new runtime data entities. It adds repository infrastructure files (configuration, CI, gitignore) that govern the development workflow rather than the converter's data model.

## Entities

### `.gitignore` (New File)

- **Purpose**: Exclude secrets, generated output, and caches from version control.
- **Format**: Standard git ignore syntax.
- **Key patterns**: `config.json`, `*.secret*`, `.env`, `__pycache__/`, `output/`, `log/`.
- **Relationships**: Protects `config.json` (which contains OAuth credentials for FHIR server access).

### GitHub Actions Workflow (New File)

- **Purpose**: CI pipeline definition.
- **Format**: YAML workflow file at `.github/workflows/ci.yml`.
- **Key components**:
  - **Lint job**: Runs `ruff check` against Python source.
  - **FHIR validation job**: Runs converter against test CSVs, validates output with `validator_cli.jar`.
  - **Secret scan job**: Runs `gitleaks` to detect committed credentials.
- **Triggers**: Pull requests to `main`, pushes to `main`.
- **Relationships**: Depends on test fixtures in `input/`, depends on `convert.py` being runnable, depends on `config.example.json` for converter config.

### `config.example.json` (Existing File — Modified)

- **Purpose**: Template configuration distributed with repo.
- **Changes**: Replace empty-string server credential fields with obvious `YOUR_*` placeholders.
- **Fields modified**: `server.base_url`, `server.token_endpoint`, `server.client_id`, `server.client_secret`.

### Test Fixtures (Existing Files — No Change)

- **Location**: `input/` directory.
- **Current files**: `2025.10.21.Test.Facility.BedCapacity.csv` (canonical test input), `2025.10.21.Test.Facility.BedCapacity.column-labels-only.csv` (headers only, excluded from CI validation runs).
- **CI discovery**: Glob `input/*.BedCapacity.csv` (excludes column-labels-only variant).
