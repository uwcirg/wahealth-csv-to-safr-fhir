# Research: Constitution v1.2.0 Repo Alignment

**Feature**: 003-constitution-repo-update | **Date**: 2026-04-02

## Research Question 1: What exact commands does the CI pipeline use for FHIR validation?

**Decision**: Use the exact commands from `.github/workflows/ci.yml` (lines 43–65).

**Findings**:
The CI pipeline has four distinct steps:

1. **Convert test fixtures** (excluding column-labels-only files):
   ```bash
   for csv in input/*.BedCapacity.csv; do
     case "$csv" in *column-labels-only*) continue ;; esac
     python3 convert.py "$csv" --config config.example.json --output-dir output
   done
   ```

2. **Extract SAFR IG version** from `convert.py`:
   ```bash
   SAFR_IG_VERSION=$(python3 -c "import re; m=re.search(r\"SAFR_IG_VERSION\s*=\s*['\"]([^'\"]+)['\"]\", open('convert.py').read()); print(m.group(1))")
   ```

3. **Validate FHIR Bundles** with versioned IG:
   ```bash
   java -jar validator_cli.jar output/**/*.json \
     -version 4.0.1 \
     -ig hl7.fhir.us.safr#$SAFR_IG_VERSION
   ```

4. **Zero errors required**; warnings are acceptable.

**Rationale**: These commands are already proven in CI. Using identical commands ensures parity (FR-002, US-3).

**Alternatives considered**: None — the constitution explicitly requires matching CI steps.

## Research Question 2: What is the current state of CLAUDE.md and what needs to change?

**Decision**: CLAUDE.md needs a new "LLM Validation Pipeline" section with the four-step process and behavioral instructions.

**Findings**:
Current CLAUDE.md is auto-generated from feature plans and contains:
- Active Technologies (duplicated entries from features 001 and 002)
- Project Structure (generic `src/` / `tests/` — doesn't match actual repo)
- Commands (garbled format: `cd src [ONLY COMMANDS...]`)
- Code Style (minimal)
- Recent Changes

Missing entirely:
- The four-step LLM validation pipeline (FR-001)
- Instruction not to skip validation (FR-003)
- Instruction to inform user if validator/Java unavailable (FR-004)
- Column-labels-only exclusion pattern (FR-005)

**Rationale**: The auto-generated CLAUDE.md structure has `<!-- MANUAL ADDITIONS START/END -->` markers. The validation pipeline should go in the manual additions section to survive future auto-generation runs.

**Alternatives considered**:
- Replacing the entire CLAUDE.md: Rejected — the auto-generated sections may be updated by speckit commands.
- Adding a separate file: Rejected — CLAUDE.md is what Claude Code reads automatically.

## Research Question 3: Should the existing CLAUDE.md inaccuracies be fixed?

**Decision**: Fix structural inaccuracies in the manual additions section. Leave auto-generated sections to the speckit tooling.

**Findings**:
- Project Structure shows `src/` and `tests/` but actual code is at root (`convert.py`)
- Commands section is garbled
- These are in auto-generated sections managed by speckit

**Rationale**: Fixing auto-generated sections would be overwritten by future speckit runs. The manual additions section is the right place for durable instructions.

**Alternatives considered**: Fixing auto-generated sections — rejected as they'd be overwritten.
