# Research: Constitution Alignment

**Date**: 2026-04-01  
**Feature**: 001-constitution-alignment

## R1: Python Linter Choice

**Decision**: Use `ruff` as the Python linter.

**Rationale**: Ruff is the modern standard for Python linting — extremely fast, drop-in replacement for flake8/isort/pyupgrade, and available as a dedicated GitHub Action (`chartboost/ruff-action`). It can auto-fix safe violations with `ruff check --fix`. The constitution permits dev/test dependencies.

**Alternatives considered**:
- `flake8` — Mature but slower, requires separate plugins for import sorting. No significant advantage over ruff for this project.
- `pylint` — More opinionated, heavier configuration burden. Overkill for a single-file project.

**Configuration**: Minimal `ruff.toml` at repo root. Start with defaults; adjust line-length if convert.py has existing long lines.

## R2: FHIR Validator in CI

**Decision**: Download `validator_cli.jar` from the official hapifhir/org.hl7.fhir.core GitHub releases and run it with Java 17 in CI.

**Rationale**: This is the authoritative HL7 FHIR Reference Validator. It validates Bundles against the US SAFR IG profiles. Java 17 is the current LTS available in GitHub Actions runners.

**Invocation pattern**:
```bash
java -jar validator_cli.jar output/*.json \
  -version 4.0.1 \
  -ig hl7.fhir.us.safr
```

**Caching**: Use `actions/cache` to cache the JAR and the `~/.fhir/` package cache directory to avoid re-downloading on every run.

**Alternatives considered**:
- HAPI FHIR server validation — requires running a server, much heavier.
- Custom JSON schema validation — would not catch profile-level conformance issues.

## R3: Secret Scanning in CI

**Decision**: Enable GitHub push protection (free for public repos) as the primary mechanism, and add a `gitleaks` GitHub Action step as a belt-and-suspenders check in the CI workflow.

**Rationale**: GitHub's built-in push protection covers 39+ known secret patterns automatically. Gitleaks adds regex-based scanning for custom patterns and works as a CI step that fails the PR check — providing the "reject commits containing likely credentials" behavior required by the constitution.

**Alternatives considered**:
- `trufflehog` — Scans full git history; more false positives, heavier setup.
- `git-secrets` — Requires GPG keys for CI, more complex than needed.
- `detect-secrets` — Viable but less commonly used than gitleaks.

## R4: Test Fixture Organization

**Decision**: Keep test CSV fixtures in `input/` for now. The CI workflow will glob `input/*.csv` to discover fixtures automatically.

**Rationale**: The constitution mentions `input/` as the current location and notes a plan to relocate to `test/`. Since there are only 2 test files and no `test/` directory exists yet, moving files would be premature. The CI workflow can be pointed at any directory later. The column-labels-only CSV should be excluded from validation runs (it has no data rows to convert).

**Alternatives considered**:
- Create `test/fixtures/` now — adds unnecessary churn for 2 files. Can do this when HRD fixtures are added.

## R5: .gitignore Contents

**Decision**: Create `.gitignore` with entries required by the constitution plus standard Python/project entries.

**Rationale**: The constitution explicitly requires `config.json`, `*.secret*`, and `.env`. Additional entries (`__pycache__/`, `log/`, `output/`) are implied by the project structure — generated output and caches should not be committed.

**Entries**:
```
# Secrets and config
config.json
*.secret*
.env

# Python
__pycache__/
*.pyc

# Generated output
output/
log/
```
