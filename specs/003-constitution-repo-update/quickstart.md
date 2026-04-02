# Quickstart: Constitution v1.2.0 Repo Alignment

**Feature**: 003-constitution-repo-update | **Date**: 2026-04-02

## What This Feature Does

Adds LLM validation pipeline instructions to CLAUDE.md so that LLM agents (Claude Code, Copilot, etc.) know to run FHIR validation before completing development work. This codifies the constitution v1.2.0 requirement that LLM agents MUST run the same validation as CI.

## Prerequisites

- None for implementation (documentation-only change)
- For the documented pipeline to work, the environment needs:
  - Python 3
  - Java 17+
  - `validator_cli.jar` (downloaded from [HAPI FHIR releases](https://github.com/hapifhir/org.hl7.fhir.core/releases/latest))

## Implementation Steps

1. Edit `CLAUDE.md` — add the LLM validation pipeline between the manual additions markers
2. Verify the documented commands match `.github/workflows/ci.yml`
3. Test by reading CLAUDE.md and confirming an LLM can follow the steps

## Verification

```bash
# Confirm CLAUDE.md contains the validation pipeline
grep -q "LLM Validation Pipeline" CLAUDE.md && echo "PASS: Section exists"

# Confirm key commands are present
grep -q "validator_cli.jar" CLAUDE.md && echo "PASS: Validator command documented"
grep -q "column-labels-only" CLAUDE.md && echo "PASS: Exclusion pattern documented"
grep -q "SAFR_IG_VERSION" CLAUDE.md && echo "PASS: IG version extraction documented"
```
