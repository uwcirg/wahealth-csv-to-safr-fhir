# Research: Support multiple hospital CSV input formats

Feeds Phase 1 of `plan.md`. Each item: **Decision / Rationale / Alternatives considered**.

---

## R1 — Identifier on a sparsely-populated Organization

**Decision**: For a multi-facility row whose facility has no config entry, the
synthesized `Organization` carries
`identifier = [{ "system": "urn:wahealth:csv-to-safr:unregistered-facility", "value": <slugified facility name> }]`.
The config's NHSN OrgID is never reused for an unregistered facility. A WARNING is
logged once per such facility. The system URI is exposed as a module constant
(`UNREGISTERED_FACILITY_SYSTEM`).

**Rationale**: Matches the `/speckit.clarify` decision (Session 2026-05-11, Q/A).
A non-empty, deterministic identifier keeps the resource structurally conformant
(the constitution requires zero validator errors) and stable across runs (so the
FHIR-server upsert key is reproducible). A distinct "unregistered" system URI makes
the placeholder nature unmistakable to anyone inspecting the data.

**Open risk → confirm during implementation**: whether
`hl7.fhir.us.safr/StructureDefinition/us-safr-submitting-organization` constrains
`Organization.identifier` to a *required slice on the NHSN system*
(`https://www.cdc.gov/nhsn/OrgID`) rather than merely `1..*`. If it does, a
placeholder under a different system fails the slice. **Contingency**: keep the
placeholder *under the NHSN system URI* with an obviously-synthetic value
(`UNREGISTERED-<slug>`) — still honors "don't use the config's OrgID", still
deterministic, still validates. The implementer runs the FHIR validator
(per CLAUDE.md / constitution) and picks the variant that validates; the spec
(FR-008/FR-008a) is satisfied either way.

**Alternatives considered**:
- *Omit the identifier* — likely a validation error (min cardinality), violates the zero-errors rule. Rejected (was option B in clarify).
- *Single shared fallback OrgID in config* — conformant but assigns the same wrong identity to every unregistered hospital; obscures the problem. Rejected (option C).
- *Abort / skip the row* — contradicts the user directive and the constitution's "process every row, emit one Bundle per row". Rejected.

---

## R2 — A sparsely-populated Location

**Decision**: The synthesized `Location` for an unregistered facility:
`identifier = [{ "system": UNREGISTERED_FACILITY_SYSTEM, "value": "<slug>:location" }]`,
`name` = the CSV `Facility` value, `description` = the same, no `address`,
`managingOrganization.reference` = the row's Organization ref; `status` = `active`,
`mode` = `instance`, `type` = HOSP, `physicalType` = `bu` — identical to the
configured path. Same risk/contingency note as R1 applies to whether
`qicore-location` requires an identifier slice on a particular system (it does not,
in current understanding — `Location.identifier` is `0..*` there); if a problem
surfaces, the placeholder value pattern is adjusted, not the design.

**Rationale**: Mirrors R1 for consistency; reuses the existing
`build_location_resource` shape so only the identifier/name/address fields differ.

**Alternatives considered**: deriving address/phone from the CSV — the MFT format
carries only a person `Contact` name (not a phone) and no address, so there is
nothing to populate; left absent rather than guessed.

---

## R3 — Reporting-date parsing per format

**Decision**:
- Original format: `%m/%d/%Y` only (unchanged — `parse_reporting_date` stays for back-compat; the original parser calls it).
- Dictionary & MFT formats: try ISO `%Y-%m-%d` first, then `%m/%d/%Y` as a fallback; raise (loud) if neither matches.
- MFT `Created On` (`YYYY-MM-DD HH:MM:SS.fffffff`) and the dictionary `created_on`: **not parsed** — not consumed by this feature.
- Provide one `parse_date_flexible(s, formats)` helper used by the new parsers; keep `parse_reporting_date` as a thin wrapper for the original path so its existing unit tests are untouched.

**Rationale**: The MFT sample uses ISO; the dictionary catalog only says "Date", so
ISO is the assumed convention with a US-format safety net (cheap, no downside).
`MeasureReport.period` and output filenames remain `YYYY-MM-DD` (derived from the
normalized `datetime.date`), so output is unchanged.

**Alternatives considered**: `datetime.fromisoformat` only — too strict given the
catalog's ambiguity; a full dateutil-style parser — would add a dependency
(forbidden). Rejected.

---

## R4 — Format-detection signatures

**Decision**: `detect_format(header: list[str]) -> str`, evaluated in order:

| Format id | Required header columns (subset test) |
|---|---|
| `original` | `facility_guid` **and** `reporting_date` |
| `wahealth_dict_2026_04_30` | `facility` **and** `reportingday` |
| `kc_mft_2026_05_11` | `Facility` **and** `Reporting Date` |

No match → raise `UnrecognizedFormatError`, whose handler logs an error naming the
three supported formats and exits non-zero **before any output directory or file is
created**. The variable-catalog file's header is `Section, Variable Name, Data
Type, Description, Notes` → matches nothing → rejected (it is documentation).
Detection is purely on column *names* (membership), so column order and trailing
empty columns (the catalog file has many) don't matter.

**Rationale**: Each signature is a two-column pair unique to its format
(`facility_guid` exists only in the original; `reportingday` as one token only in
the dictionary; Title-Case `Reporting Date` only in MFT). Ambiguity is
impossible with these pairs, so "most-specific wins" degenerates to a simple
ordered check. Failing loud before touching the filesystem satisfies FR-006 and
SC-004.

**Alternatives considered**: hashing the full header — brittle against added
columns; sniffing the first data row — unnecessary and slower. Rejected.

---

## R5 — Normalized row model & `compute_groups` refactor

**Decision**: Parsers emit a plain `dict` ("NormalizedRow") with canonical keys:
`facility_name: str`, `facility_guid: str | None`, `reporting_date: datetime.date`,
and for each canonical bed area `A ∈ {adult_icu, peds_icu, adult_acute, peds_acute,
neonatal_icu, nursery, surge, other}` the integer keys `f"{A}_occ"` and
`f"{A}_cap"`, plus `adult_ed: int` and `peds_ed: int`. All ints already passed
through `safe_int` with logging; unoccupied is still computed (and clamped ≥ 0) in
`get_occupied_and_unoccupied`, which is re-signed to `(record, area) ->
(occupied, unoccupied)`. `BED_MAPPINGS` is re-keyed by canonical area; `ALL_BED_PREFIXES`
becomes `ALL_BED_AREAS` (the 8 canonical names). `compute_groups(record)` reads
the canonical keys; the 25-group output and the group IDs/LOINC codes are
unchanged.

**Rationale**: A neutral internal vocabulary keeps `compute_groups` and Bundle
assembly free of any format's column names (FR-005). A dict (vs a dataclass) keeps
the change small and the stdlib-only constraint trivially satisfied.

**Regression guard**: `tests/test_compute.py` is updated to build NormalizedRows
(the existing value-based assertions carry over); a new test converts the existing
original-format fixture end-to-end and asserts the group counts match a recorded
baseline (FR-002 / SC-002).

**Alternatives considered**: keeping the original format's column names *as* the
internal model (parsers for formats 2/3 translate into them) — less code churn but
leaks one format's vocabulary into the core and reads poorly. Rejected.

---

## R6 — `facilities` registry in `config.json`

**Decision**: New **optional** top-level key:

```jsonc
"facilities": {
  "Seaside Medical Center": {
    "organization": { "nhsn_org_id": "…", "name": "…", "phone": "…", "address": { … } },
    "location":     { "identifier_system": "…", "identifier_value": "…", "name": "…", "description": "…" }
  }
  // … one entry per known facility name (must match the CSV `Facility` value exactly)
}
```

`load_config` still requires `organization`, `location`, `software`. When
`facilities` is present, each entry is validated to contain `organization` and
`location` (clear error otherwise). `resolve_facility_profile(record, config,
format_id)`:
- single-facility formats (`original`, `wahealth_dict_2026_04_30`) → `{organization: config["organization"], location: config["location"]}`, `unregistered=False` (exactly today's behavior; the CSV facility name still affects only the filename);
- `kc_mft_2026_05_11` → `config["facilities"].get(name)` if present (`unregistered=False`), else a synthesized sparse profile (`unregistered=True`) + one WARNING.

**Rationale**: Backward compatible (existing configs untouched). Keyed by facility
name because that is the only join key the MFT file offers. The top-level block is
deliberately *not* a fallback for an unregistered facility in a multi-hospital file
— it describes one specific hospital, so borrowing its address/phone for a
different facility would be wrong data (this is the `/speckit.clarify` decision
extended to all identity fields, not just the OrgID).

**Edge — single-facility format with multiple distinct facility names in its
rows**: keep today's behavior (all rows use the top-level config; only the filename
varies); optionally log a WARNING if >1 distinct name is seen. Not a hard
requirement.

**Alternatives considered**: a separate `facilities.json` file — extra moving
part; CLI flag per facility — unusable at scale. Rejected.

---

## R7 — Keep in `convert.py` or extract a module?

**Decision**: Implement detection + the three parsers + the column-map tables in
`convert.py`. If, after implementation, `convert.py` exceeds ~1000 lines, extract
`csv_formats.py` containing exactly: `detect_format`, `UnrecognizedFormatError`,
the per-format column maps, the per-format parser functions, and
`parse_date_flexible`. `convert.py` keeps everything else (FHIR resource builders,
upsert, `main`). No other split.

**Rationale**: The constitution's Single-File Simplicity rule permits a split only
when *both* a clear boundary exists *and* the file exceeds ~1000 lines. The
detection/parser layer is a clean boundary; whether the threshold is crossed is a
post-implementation fact (`convert.py` is ~825 lines now; the addition is
~150–250). Deferring the decision avoids both premature modularization and an
over-long file.

**Alternatives considered**: split unconditionally now — premature per the
constitution; never split — risks an unwieldy file. Rejected in favor of the
threshold rule.

---

## R8 — CI / LLM-validation conversion loop

**Decision**: In `.github/workflows/ci.yml` change the fixture loop from
`for csv in input/*.BedCapacity.csv` to `for csv in input/*.csv`, keeping the
`case "$csv" in *column-labels-only*) continue ;; esac` skip. Mirror the same
change in `CLAUDE.md`'s documented four-step pipeline. The constitution's
"LLM Development Validation" wording already says "all test fixtures in `input/`
(excluding `*column-labels-only*` files)", so no constitution edit is needed.
`config.example.json` will register *some* of the census fixture's facilities and
leave *others* unregistered, so CI exercises both the registry path and the
sparse-resource path — and both must produce zero project-introduced validator
errors.

**Rationale**: The two new fixtures (`census_20260511.FromKC.SubsetObfsctd.csv`,
`2026.04.30.Test.Facility.WAHealthDict.csv`) don't match `*.BedCapacity.csv`;
broadening the glob is simpler and more future-proof than renaming fixtures, and it
keeps the constitution's "all fixtures in `input/`" intent.

**Alternatives considered**: rename every fixture to `*.BedCapacity.csv` — loses
the descriptive names and the format hint in the filename. Rejected.

---

## R9 — FHIR-server upsert with multiple facilities

**Decision**: `main()` currently upserts Organization/Location/Device once and
reuses the refs for all rows. Change to: cache `org_ref` and `loc_ref` in dicts
keyed by facility name (compute the key from the resolved profile / facility name);
Device stays a single upsert. `upsert_organization` / `upsert_location` take a
resolved `profile` (+ `unregistered` flag) instead of the whole `config`; for an
unregistered facility the search identifier is
`UNREGISTERED_FACILITY_SYSTEM|<slug>`. `upsert_bundle`'s deterministic UUID uses
`facility_guid` when present, else `slugify(facility_name)` (FR-007). FHIR-server
persistence is not in the P1 user story but follows for free from the same
`resolve_facility_profile`; it must keep working (FR-005) and is covered by code
review rather than a live integration test.

**Rationale**: A single shared Org/Location ref is incorrect once a file spans
hospitals; per-facility caching is the minimal correct change and still avoids
redundant upserts within a run.

**Alternatives considered**: disable `--fhir-server` for multi-facility files —
contradicts FR-005's "identical regardless of format". Rejected.
