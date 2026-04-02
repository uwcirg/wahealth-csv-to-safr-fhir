# Data Model: Constitution v1.2.0 Repo Alignment

**Feature**: 003-constitution-repo-update | **Date**: 2026-04-02

## Overview

This feature is documentation-only. There are no new data entities, database schemas, or data transformations. The "data model" for this feature is the structure of the CLAUDE.md additions.

## Entity: CLAUDE.md LLM Validation Section

**Location**: Between `<!-- MANUAL ADDITIONS START -->` and `<!-- MANUAL ADDITIONS END -->` markers in `CLAUDE.md`

**Fields/Content**:

| Content Block | Required | Source |
|---------------|----------|--------|
| Section header ("LLM Validation Pipeline") | Yes | Constitution §Validation-Driven Testing |
| Step 1: Convert command with exclusion pattern | Yes | CI workflow lines 43–53 |
| Step 2: IG version extraction command | Yes | CI workflow lines 54–58 |
| Step 3: Validator invocation command | Yes | CI workflow lines 63–65 |
| Step 4: Zero-errors requirement | Yes | Constitution §LLM Development Validation |
| "Do not skip" instruction | Yes | FR-003 |
| "Inform user if unavailable" instruction | Yes | FR-004 |

**Validation Rules**:
- Commands must be identical to CI workflow (FR-002)
- Exclusion pattern must be `*column-labels-only*` (FR-005)
- Must be self-contained — an LLM with only CLAUDE.md should be able to execute the full pipeline (SC-003)
