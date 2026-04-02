# Feature Specification: Constitution Alignment

**Feature Branch**: `001-constitution-alignment`  
**Created**: 2026-04-01  
**Status**: Draft  
**Input**: User description: "update the repo based on the newly-written constitution."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Secrets Are Protected from Accidental Commit (Priority: P1)

A developer working on the converter clones the repo and creates their `config.json` with real OAuth credentials. When they run `git add .` and `git commit`, the `.gitignore` file prevents `config.json`, `.env`, and `*.secret*` files from being staged. The developer never has to worry about accidentally pushing secrets to the remote.

**Why this priority**: Secret leakage could grant unauthorized access to state health data systems. This is a security requirement with immediate risk — the repo currently has no `.gitignore` at all.

**Independent Test**: Create a `config.json` and `.env` file in the repo root, run `git status`, and confirm neither appears as an untracked file.

**Acceptance Scenarios**:

1. **Given** a freshly cloned repo with a new `config.json` containing credentials, **When** a developer runs `git status`, **Then** `config.json` does not appear in the untracked files list.
2. **Given** a repo with files named `token.secret` and `.env`, **When** a developer runs `git add .`, **Then** neither file is staged for commit.
3. **Given** the `.gitignore` file, **When** reviewed, **Then** it includes at minimum: `config.json`, `*.secret*`, `.env`, `__pycache__/`, `log/`, and `output/`.

---

### User Story 2 - CI Pipeline Catches Regressions Before Merge (Priority: P1)

A developer opens a pull request with a change to `convert.py`. GitHub Actions automatically runs linting and FHIR validation against test CSV inputs. If the change introduces a lint error or produces a non-conformant FHIR Bundle, the PR check fails and the developer is notified before merge.

**Why this priority**: With AI-assisted development and a small team, CI is the safety net that catches regressions before they reach hospital workstations. The constitution makes this a mandatory requirement for all PRs.

**Independent Test**: Push a branch with a deliberate lint error and confirm the CI check fails. Push a clean branch and confirm all checks pass.

**Acceptance Scenarios**:

1. **Given** a pull request to the `main` branch, **When** CI runs, **Then** a Python linting check executes and reports pass/fail.
2. **Given** a pull request to the `main` branch, **When** CI runs, **Then** the converter runs against all test CSV inputs in the `input/` directory and the output Bundles are validated with the HL7 FHIR Reference Validator (`validator_cli.jar`). Zero errors required; warnings are acceptable.
3. **Given** a pull request that introduces a lint violation, **When** CI runs, **Then** the PR is marked as failing and the developer sees the specific violation.

---

### User Story 3 - Config Example Uses Obvious Placeholders (Priority: P2)

A hospital data manager copies `config.example.json` to `config.json`. The server credential fields contain obvious placeholder values like `YOUR_CLIENT_ID` and `YOUR_CLIENT_SECRET` that would clearly fail authentication if accidentally used unchanged — making it immediately obvious that real values must be substituted.

**Why this priority**: The constitution requires that `config.example.json` use obvious placeholder values to prevent accidental use of example credentials. The current file uses empty strings for server fields, which could silently fail or be ambiguous.

**Independent Test**: Read `config.example.json` and verify all credential fields contain `YOUR_*` placeholder strings.

**Acceptance Scenarios**:

1. **Given** the `config.example.json` file, **When** reviewed, **Then** `client_id` contains `YOUR_CLIENT_ID`, `client_secret` contains `YOUR_CLIENT_SECRET`, and `token_endpoint` contains `YOUR_TOKEN_ENDPOINT`.
2. **Given** a user who copies `config.example.json` without editing server fields, **When** they attempt to use the converter with `--fhir-server`, **Then** authentication fails clearly rather than proceeding with empty credentials.

---

### User Story 4 - Test Fixtures Are Organized for CI and Development (Priority: P2)

A developer adding HRD surveillance support needs to add test CSV files. The test fixture directory is clearly identified, and the CI pipeline automatically discovers and runs against all fixtures in that directory.

**Why this priority**: The constitution requires test CSV fixtures for each measure domain and plans to relocate test fixtures to a `test/` directory. Organized fixtures support both CI automation and developer workflows.

**Independent Test**: Place a CSV file in the designated test fixture directory and confirm CI picks it up automatically on the next run.

**Acceptance Scenarios**:

1. **Given** the repository structure, **When** a developer looks for test data, **Then** there is a clearly designated directory containing canonical test CSV files.
2. **Given** a new test CSV added to the fixtures directory, **When** CI runs, **Then** the converter runs against the new file and validates the output.

---

### Edge Cases

- What happens when CI runs but the HL7 FHIR Validator JAR is unavailable or fails to download?
- What happens when a developer has already committed `config.json` before the `.gitignore` is added (i.e., it's already tracked)?
- What happens when a lint rule conflicts with existing code style in `convert.py`?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Repository MUST contain a `.gitignore` file that excludes `config.json`, `*.secret*`, `.env`, `__pycache__/`, `log/`, and `output/` from version control.
- **FR-002**: `config.example.json` MUST use obvious placeholder values (`YOUR_CLIENT_ID`, `YOUR_CLIENT_SECRET`, `YOUR_TOKEN_ENDPOINT`) for all server credential fields instead of empty strings.
- **FR-003**: Repository MUST contain a GitHub Actions workflow that runs on all pull requests to the `main` branch.
- **FR-004**: The CI workflow MUST include a Python linting step using a standard linter with consistent style rules.
- **FR-005**: The CI workflow MUST include a FHIR validation step that runs the converter against all test CSV inputs and validates output Bundles with the HL7 FHIR Reference Validator. Zero errors required; warnings are acceptable.
- **FR-006**: The CI workflow MUST include a secret scanning step to reject commits containing likely credentials.
- **FR-007**: Test CSV fixture files MUST be organized in a clearly designated directory that CI automatically discovers.
- **FR-008**: The `config.example.json` MUST stay current with all supported configuration fields.

### Key Entities

- **`.gitignore`**: File controlling which paths are excluded from version control. Central to secret protection.
- **GitHub Actions Workflow**: CI pipeline configuration defining lint, validation, and secret scanning jobs.
- **Test Fixtures**: Canonical CSV input files used for regression testing and FHIR validation.
- **`config.example.json`**: Template configuration file distributed with the repo; the only config file that should be committed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: No secrets (`config.json`, `.env`, `*.secret*`) can be accidentally committed to the repository after `.gitignore` is in place.
- **SC-002**: 100% of pull requests to `main` are automatically checked by CI before merge is permitted.
- **SC-003**: Every test CSV fixture produces a FHIR Bundle that passes the HL7 FHIR Reference Validator with zero errors.
- **SC-004**: All credential placeholder values in `config.example.json` are visually obvious non-functional values (e.g., `YOUR_*` pattern).
- **SC-005**: A new contributor can clone the repo, run the converter against test fixtures, and validate output locally by following documented steps.

## Assumptions

- GitHub Actions is the CI platform (the repo is hosted on GitHub).
- The HL7 FHIR Reference Validator JAR can be downloaded in CI (requires Java runtime in the CI environment).
- A standard Python linter is installable as a dev dependency without violating the zero-dependency runtime principle (dev/test dependencies are explicitly permitted by the constitution).
- The existing `input/` directory contains canonical test CSV files that can serve as the initial test fixture set; relocation to `test/` can be deferred if the team prefers to keep the current structure.
- The existing `convert.py` code may require minor lint fixes to pass the chosen linter's rules, but no functional changes are needed.
