# Quickstart: Per-Facility Output Layout and Bundles-MRs-Only Mode

## Try it

Full output (default), per-facility subdirectories:

```bash
python3 convert.py input/<some-fixture>.csv --config config.example.json --output-dir output
ls output/*/                 # Bundle files + one subdir per facility
ls output/*/*/               # Organization.json Device.json Location.json MeasureReport.json
```

Bundles + MeasureReports only:

```bash
python3 convert.py input/<some-fixture>.csv --config config.example.json --output-dir output --bundles-mrs-only
ls output/*/*/               # only MeasureReport.json
python3 convert.py --help    # shows --bundles-mrs-only
```

Multi-facility input (the case this feature fixes):

```bash
python3 convert.py input/<multi-facility-fixture>.csv --config config.example.json --output-dir output
# Each facility now has its own output/<date>/<facility>/ — no overwrite.
```

## Verify

1. **Layout** — `output/<date>/` contains only `*.BedCapacity.json` Bundle files; every
   individual resource is under `output/<date>/<facility>/`.
2. **Isolation** — for a multi-facility file, every facility's subdirectory holds that facility's
   own `Organization.json` etc. (compare `id` / identifier values).
3. **Flag** — with `--bundles-mrs-only`, `find output -name 'Organization.json' -o -name
   'Device.json' -o -name 'Location.json'` returns nothing; `MeasureReport.json` and the Bundle
   are present.
4. **Tests** — `cd` to repo root, run `pytest` (incl. the new `tests/test_output_layout.py`) and
   `ruff check .`.
5. **FHIR validation** — run the four-step pipeline in `CLAUDE.md` against the new-layout output,
   passing the validator `$(find output -name '*.json')` (the `output/**/*.json` glob misses the
   new 3-level per-facility files without `shopt -s globstar`); expect zero project-introduced
   errors (only the two known upstream patterns may appear).
6. **Docs** — README "Output" section and options table describe the subdirectory layout and
   `--bundles-mrs-only`; constitution's pending README follow-up TODO is cleared.

## Rollback

Revert the `convert.py` write-loop / `argparse` change and the README edits; delete
`tests/test_output_layout.py`. No data migration — output is regenerated each run.
