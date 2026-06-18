# Quickstart: Relocate test fixtures to test/input → test/output

This is the developer/agent workflow for performing and verifying the relocation.

## 1. Move the fixtures (history-preserving)

```bash
mkdir -p test/input
git mv input/*.csv test/input/
rmdir input            # remove the now-empty directory
```

After this, `test/input/` holds all four fixtures and `input/` no longer exists.

## 2. Ignore generated test output

Add to `.gitignore` (next to the existing `output/` entry):

```text
test/output/
```

## 3. Update CI (`.github/workflows/ci.yml`)

- Convert step: loop `test/input/*.csv` (keep the `*column-labels-only*` exclusion) and pass
  `--output-dir test/output`.
- Validate step: `find test/output -name '*.json'` instead of `find output ...`.
- Update the explanatory comments that mention `input/` / `output/`.

## 4. Update `CLAUDE.md` LLM Validation Pipeline

- Step 1 loop: `for csv in test/input/*.csv` and `--output-dir test/output`.
- Step 3 validator: `java -jar validator_cli.jar $(find test/output -name '*.json') ...`.

## 5. Update `README.md` (only where it names fixture/test paths)

Leave generic production examples (placeholder input filename + default `./output`) as-is.

## 6. Verify — run the four-step validation pipeline over the new paths

```bash
# Step 1: convert every data fixture to test/output
for csv in test/input/*.csv; do
  case "$csv" in *column-labels-only*) continue ;; esac
  echo "Converting: $csv"
  python3 convert.py "$csv" --config config.example.json --output-dir test/output
done

# Step 2: extract IG versions
SAFR_IG_VERSION=$(grep -oP '^SAFR_IG_VERSION\s*=\s*"\K[^"]+' convert.py)
NHSN_SAFR_IG_VERSION=$(grep -oP 'NHSN_SAFR_IG_VERSION\s*=\s*"\K[^"]+' convert.py)

# Step 3: validate everything under test/output
java -jar validator_cli.jar $(find test/output -name '*.json') \
  -version 4.0.1 \
  -ig hl7.fhir.us.safr#$SAFR_IG_VERSION \
  -ig https://safr-ci.nhsnlink.org/package.tgz

# Step 4: zero errors except the two documented known-upstream patterns
```

## 7. Acceptance checks

- `ls test/input/` shows all 4 fixtures; `input/` is gone (SC-001).
- Output appears only under `test/output/`; validator reports zero project-introduced errors
  (SC-002).
- `grep -rn 'input/' .github CLAUDE.md README.md` shows no reference to the old fixture
  directory as the fixture source (SC-005).
- `python3 convert.py <some.csv> --config config.example.json` (no `--output-dir`) writes to
  `./output` (SC-006).
- CI passes on the branch (SC-003).

> If `validator_cli.jar` or Java is unavailable locally, FHIR validation cannot be run — report
> this to the user rather than skipping it (constitution: LLM Development Validation).
