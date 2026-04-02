# Feature Specification: Constitution v1.2.0 Repo Alignment

**Feature Branch**: `003-constitution-repo-update`  
**Created**: 2026-04-02  
**Status**: Draft  
**Input**: User description: "update the repo based on the updated constitution."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - LLM Agent Runs Validation Before Completing Work (Priority: P1)

An LLM agent (Claude Code, Copilot, etc.) makes a change to `convert.py` that could affect FHIR output. Before considering the work complete, the LLM runs the converter against all test fixtures (excluding `*column-labels-only*` files), extracts the `SAFR_IG_VERSION`, and validates all generated Bundles using `validator_cli.jar`. The LLM reports zero errors before signaling completion.

**Why this priority**: This is the core change in constitution v1.2.0 — elevating local validation from SHOULD to MUST for LLM agents. Without this, LLM-authored changes may silently break FHIR conformance and only be caught later in CI.

**Independent Test**: Can be tested by having an LLM agent make a trivial change to `convert.py` and observing that it runs the full validation pipeline before reporting done.

**Acceptance Scenarios**:

1. **Given** an LLM agent modifies code that could affect FHIR output, **When** the agent finishes its changes, **Then** the agent runs the converter against all test fixtures and validates output Bundles with zero FHIR errors before reporting completion.
2. **Given** `validator_cli.jar` or Java is not available in the environment, **When** the LLM attempts validation, **Then** the LLM informs the user and requests environment setup rather than silently skipping validation.
3. **Given** the LLM runs validation and encounters FHIR errors, **When** reviewing the results, **Then** the LLM fixes the errors and re-validates until zero errors are achieved.

---

### User Story 2 - Developer Instructions Reflect Constitution Requirements (Priority: P2)

A developer (human or LLM) reads the project's guidance files (CLAUDE.md) and finds clear, actionable instructions for the LLM validation workflow — including the exact commands to run, the exclusion pattern for column-labels-only files, and the requirement to extract the IG version from the code.

**Why this priority**: Instructions are the mechanism by which the constitution's LLM validation requirement is enforced. Without them codified in CLAUDE.md, LLM agents won't know to run validation.

**Independent Test**: Can be tested by reading CLAUDE.md and confirming it contains the exact validation pipeline steps from the constitution.

**Acceptance Scenarios**:

1. **Given** CLAUDE.md exists in the repo, **When** a developer reads it, **Then** it contains the four-step LLM validation pipeline (convert, extract IG version, validate, zero-errors check) with exact commands.
2. **Given** an LLM agent is given only CLAUDE.md as project context, **When** it performs development work affecting FHIR output, **Then** it can follow the documented steps without needing to reference the constitution directly.

---

### User Story 3 - CI and LLM Validation Use Identical Pipeline Steps (Priority: P3)

The validation steps documented for LLM agents match the steps in the CI workflow, ensuring parity between local LLM validation and automated CI checks. If CI changes, the LLM instructions should be updated to match (and vice versa).

**Why this priority**: Parity prevents situations where LLM validation passes but CI fails (or vice versa), which would undermine trust in the validation process.

**Independent Test**: Can be tested by comparing the commands in CLAUDE.md against the steps in the CI workflow and confirming they are functionally equivalent.

**Acceptance Scenarios**:

1. **Given** the CI workflow runs the converter with specific flags, **When** reviewing CLAUDE.md, **Then** the same command (with the same flags) is documented for LLM use.
2. **Given** the CI workflow validates with the versioned IG reference, **When** reviewing CLAUDE.md, **Then** the same validator invocation is documented for LLM use.

### Edge Cases

- What happens when new test fixture CSVs are added to `input/`? The validation instructions use a glob pattern, not hardcoded filenames, so new fixtures are automatically included.
- What happens when the `SAFR_IG_VERSION` constant is renamed or moved? The extraction step should reference a stable pattern that matches the current code.
- What if `validator_cli.jar` is missing but Java is available? The LLM should inform the user that the validator needs to be downloaded before proceeding.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: CLAUDE.md MUST include the four-step LLM validation pipeline from constitution section "LLM Development Validation," with exact shell commands.
- **FR-002**: The documented validation commands MUST match the CI workflow steps (same flags, same exclusion patterns, same IG version extraction method).
- **FR-003**: CLAUDE.md MUST instruct LLM agents to NOT skip validation to save time or defer it to CI.
- **FR-004**: CLAUDE.md MUST instruct LLM agents to inform the user if `validator_cli.jar` or Java is unavailable, rather than silently skipping validation.
- **FR-005**: The test fixture exclusion pattern (`*column-labels-only*`) MUST be documented so LLMs skip header-only files when running the converter.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: CLAUDE.md contains all four validation pipeline steps with executable commands that an LLM agent can follow without additional context.
- **SC-002**: The commands documented in CLAUDE.md produce the same validation results as the CI pipeline when run against the same inputs.
- **SC-003**: An LLM agent given only CLAUDE.md as project context can successfully run the validation pipeline end-to-end on the existing test fixtures.

## Assumptions

- `validator_cli.jar` and Java 17+ are expected to be available in the development environment; the constitution requires LLMs to inform the user if not, rather than skipping.
- The CI workflow (`.github/workflows/ci.yml`) is the authoritative reference for the validation pipeline steps.
- CLAUDE.md is the primary mechanism for conveying project instructions to LLM agents (Claude Code reads it automatically).
- No new code or scripts need to be written — the existing converter and CI commands are sufficient; only documentation/instructions need updating.
