# Known FHIR Validation Issues

Errors reported by the HL7 FHIR Validator (`validator_cli.jar`) that originate in
upstream IG dependencies, not in this project's converter output.  These same
errors reproduce when validating the **published example Bundle** shipped inside
`hl7.fhir.us.safr#1.0.0`
(`Bundle-HospitalBedCapacityReportBundle.json`).

CI filters these errors so the build stays green while they remain unresolved
upstream.  Each entry below is written to be actionable for the responsible
working group.

---

## 1. Unresolvable R5 cross-version extension in DEQM v5.0.0

| Field | Value |
|-------|-------|
| **Validator message** | `Slicing cannot be evaluated: Unable to resolve profile CanonicalType[http://hl7.org/fhir/5.0/StructureDefinition/extension-MeasureReport.supplementalData]` |
| **Affected resource** | Any `MeasureReport` declaring profile `indv-measurereport-deqm` from DEQM v5.0.0 |
| **Root cause** | The DEQM v5.0.0 `indv-measurereport-deqm` profile slices `MeasureReport.extension` using a discriminator that references the R5 cross-version extension `http://hl7.org/fhir/5.0/StructureDefinition/extension-MeasureReport.supplementalData`. The FHIR validator cannot resolve this StructureDefinition when validating R4 resources, causing all extension slicing evaluation to fail. |
| **Responsible package** | `hl7.fhir.us.davinci-deqm#5.0.0` |
| **Responsible working group** | Da Vinci Clinical Data Exchange (CDex) / Clinical Quality Information (CQI) |
| **Impact** | 2 errors per MeasureReport (one per extension: `extension-measureScoring` and `extension-dataLocation`) |
| **Workaround** | None available at the validator or consumer level. Requires either (a) DEQM to update slicing discriminators to avoid R5 cross-version references, or (b) the FHIR validator to ship R5 cross-version extension definitions when validating R4 content against IGs that reference them. |

---

## 2. Bundle measurereport slice not matched (cascading from issue 1)

| Field | Value |
|-------|-------|
| **Validator message** | `Slice 'Bundle.entry:measurereport': a matching slice is required, but not found (from http://hl7.org/fhir/us/safr/StructureDefinition/us-safr-measurereport-bundle\|1.0.0)` |
| **Affected resource** | Any `Bundle` declaring profile `us-safr-measurereport-bundle` |
| **Root cause** | The `us-safr-measurereport-bundle` profile defines a required slice `Bundle.entry:measurereport` with discriminator `resource.conformsTo('http://hl7.org/fhir/us/davinci-deqm/StructureDefinition/indv-measurereport-deqm')`. To evaluate this discriminator, the validator must fully validate the MeasureReport against the DEQM profile. Because issue 1 prevents that validation from completing, the slice match fails and the validator reports the required slice as missing. |
| **Responsible package** | `hl7.fhir.us.davinci-deqm#5.0.0` (root cause); `hl7.fhir.us.safr#1.0.0` (defines the slice) |
| **Responsible working group** | SAFR / Da Vinci |
| **Impact** | 1 error per Bundle |
| **Workaround** | None. This error will resolve automatically when issue 1 is fixed. |

---

## Reproduction steps

To confirm these errors exist in the IG's own example (not just this project):

```bash
# Download the validator
curl -L -o validator_cli.jar \
  https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar

# Validate the IG's published example Bundle
java -jar validator_cli.jar \
  ~/.fhir/packages/hl7.fhir.us.safr#1.0.0/package/example/Bundle-HospitalBedCapacityReportBundle.json \
  -version 4.0.1 \
  -ig hl7.fhir.us.safr#1.0.0
```

Expected result: 6 errors, all matching issues 1 and 2 above.

## Status update (2026-04-23)

Both issues above are **resolved when the CDC NHSN SAFR Content IG
(`gov.cdc.nhsn.safr`) is included in validation**. The Content IG
transitively depends on `hl7.fhir.uv.xver-r5.r4#0.1.0`, which
provides the R5 cross-version extension definitions that the DEQM
profile's slicing discriminator requires. With this package loaded,
the validator can resolve the `extension-MeasureReport.supplementalData`
StructureDefinition, and both issues 1 and 2 no longer reproduce.

As of feature `006-content-ig-integration`, the CI pipeline and LLM
validation instructions include the Content IG via
`-ig https://safr-ci.nhsnlink.org/package.tgz`. The `grep -v` filters
for these errors remain in CI as a safety net in case the Content IG
URL is temporarily unavailable, but under normal operation these errors
should not appear.

The issues still reproduce when validating with **only** the base IG
(`-ig hl7.fhir.us.safr#1.0.0`) without the Content IG. The entries
above are retained for reference until the upstream DEQM package
itself resolves the issue.

## Environment tested

- FHIR Validator: v6.9.4
- Java: OpenJDK 17
- IG packages: `hl7.fhir.us.safr#1.0.0`, `hl7.fhir.us.davinci-deqm#5.0.0`
- Date: 2026-04-02
- Re-tested with Content IG: 2026-04-23 (0 errors when Content IG
  included via `https://safr-ci.nhsnlink.org/package.tgz`)
