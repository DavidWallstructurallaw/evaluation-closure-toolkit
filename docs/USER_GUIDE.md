# User guide

Evaluation Closure Toolkit inspects a supplied evaluation dossier and shows what its records support within a declared scope. Use it to check claim disclosures, inspect structural coverage, trace recorded shared origins, distinguish external contact from actual use, or examine correction records and a five-condition assessment.

This guide accompanies the `0.1.0rc1` release candidate. See the [README](../README.md) for installation and current qualification status. Candidate preparation does not announce a published stable release. All packaged examples are synthetic. The toolkit runs offline using the Python standard library; it does not execute a model, collect evidence, authenticate receipts or authorize deployment.

## Start with one small dossier

After installation, work in a private ordinary directory. Save the following as `prepare_dossier.py` and run `python prepare_dossier.py`. This copies the installed minimal example without replacing an existing file:

```python
from importlib import resources
from pathlib import Path

data = resources.files("evaluation_closure_toolkit").joinpath(
    "data", "incomplete-regression.json"
).read_bytes()
with Path("my-dossier.json").open("xb") as output:
    output.write(data)
```

Then run:

```sh
python -m evaluation_closure_toolkit validate my-dossier.json
python -m evaluation_closure_toolkit analyze my-dossier.json --request lint-main --output my-report.json
python -m evaluation_closure_toolkit analyze my-dossier.json --request lint-main --format markdown --output my-report.md
```

This example passes admission and finishes analysis. Its finite regression claim remains `unestablished` because required information is missing. Read the Markdown request section and each finding's `needed_information`, then inspect the referenced records in the dossier.

To prepare your own inquiry, keep the original example separately. Set the dossier identity and declared analysis time, replace the synthetic claim with your actual finite claim, and add the records you possess. Retain unknown or withheld information explicitly. Never treat a copied synthetic receipt or review as evidence about your system. Use `supported-narrow-regression` as a more complete schema example; its favorable conclusion applies only to its supplied synthetic records.

Run `validate` after each structural edit. After admission succeeds, run `analyze` to inspect evidence gaps. Choose new output filenames for each run. `demo NAME` analyzes its packaged dossier directly; it does not export an editable dossier. For all seven operations together, try `demo bounded-workflow --format markdown`.

## Choose the question and collect its records

Every request refers to an existing `scope` and its process entity. Build only the records needed for the question you actually want to inspect. Incomplete semantic information can still produce a useful report.

| Operation | Question | Typical records to prepare |
| --- | --- | --- |
| `lint` | What is disclosed, missing, contradictory or expired for this claim? | Claim and scope; represented frame; R01–R10 typed disclosure anchors; evidence and appropriately bound reviews |
| `profile` | Which declared classes are represented in this captured population? | Frame and class roster; immutable item versions; selected assignments; snapshot membership; optional item validity and tail records |
| `compare` | How did two compatible captured populations differ? | Two snapshots and their frames/policies; an explicit pair roster and matching basis for matched mode; revision evidence when using a relabel |
| `lineage` | Which typed recorded paths connect these seeds to shared sources? | At least two seed entities/items; scoped typed relations; known frontiers; any exact member-set/dimension independence assessments and reviews |
| `external` | Was a contribution received, retained, selected or used, and was it qualified for this use? | Contribution entities; external cohort and membership; boundary/window/purpose; separate stage events, member-specific externality and suitability reviews |
| `cases` | What happened to anomalies, revisions and correction attempts? | Anomalies and their retained evidence; revision maps and incorporated assignments; correction cases with linked handling, attempts, actions and reviewed outcomes |
| `assess` | Do the supplied records support this claim's required conditions? | Claim, frame and reviews; for a full open claim, a selected snapshot and cohort plus relevant cases/anomalies/revisions and the fixed criterion witnesses |

The [machine-readable schema](../src/evaluation_closure_toolkit/data/dossier.schema.json) defines record shapes. The [executable specification](phase0/P0-3_Minimal_Executable_Specification.md) explains references and semantics. The [P1-4 interpretation guide](P1-4.md) gives the exact evidence-anchor requirements for all fourteen open-assessment criteria. A generic JSON Schema check cannot replace the toolkit's admission checks.

## Represent facts and gaps faithfully

A dossier has exactly six top-level fields: `schema`, `id`, `analysis_time`, `policy`, `records` and `requests`. Use `ect-dossier/0.1` and `ect-core/0.1`. Objects are closed: additional fields, misspelled enum values and unresolved references fail admission. IDs are case-sensitive, begin with an ASCII letter and contain at most 96 characters from letters, digits, underscore, period, colon and hyphen.

Required structural fields, such as a record's `id` and `type`, use ordinary values. Optional semantic facts use tagged objects. For example, these are alternative values for a claim's `horizon` field, not complete dossiers:

```json
{"state":"known","value":"One isolated turn per captured case."}
```

```json
{"state":"unknown","reason":"The run horizon was not recorded.","evidence_ids":[]}
```

Omitting an optional semantic fact produces a `missing_field` gap. Other tagged states include `withheld`, `disputed`, `absent` and `not_applicable`; they have distinct meanings and require the declared shape. A declared absence applies only to its record's scope. A `not_applicable` label cannot waive a required open-evaluation condition. A known empty list, an unknown list and a missing field are different inputs.

Keep these distinctions during preparation:

- Every referenced record must exist. If a document is unavailable, retain an evidence record with an access gap instead of leaving a dangling evidence ID.
- Evidence fields describe the supplied kind, producer, scope, access and content. A locator remains inert. Merely naming a URL or marking a receipt as an `execution_record` provides no independent authentication.
- Reviews need their exact target, criterion, scope and any member/outcome/disclosure/request binding. Qualified support also needs the appropriate supplied witnesses. Favorable prose or a `supports` label alone cannot fill a missing prerequisite.
- Item versions are immutable identities. An assignment revision is a changed classification record, not another observed item. Snapshot selections determine which assignments are used; the tool does not select a convenient latest record.
- Record contrary premises, unknown ancestry and incomplete membership. They remain visible rather than being converted into clean negatives or independent origins.

Use UTC timestamps such as `2026-10-24T12:00:00Z`. The dossier supplies `analysis_time`; the tool does not substitute the computer's current time. `valid_until` equal to `analysis_time` is expired. Time windows include their start and exclude their end. JSON nulls, floating-point numbers, duplicate keys and a byte-order mark are rejected. Preserve decimal measurements as evidence text where needed; the tool does not parse that prose into measurements.

## Scope and selection

A scope identifies the inquiry's process, and can bind a claim, frame, snapshots, time window and dimension. Exact scope IDs govern matching. A review from a different scope cannot silently qualify this one. Frame or snapshot selections must agree with the applicable claim and scope references.

Requests live inside the dossier. `--request ID` selects an existing request, not an operation name. Repeat the flag for several IDs. Omit it to select all requests. Selection must contain between one and sixteen unique request IDs; a larger dossier can be validated and analyzed in explicit smaller selections. Results retain unselected requests as `not_selected` and `not_run`.

Operation-specific selectors also matter:

- `profile` defaults to the selected population. `confirmed_valid` additionally reports the confirmed-valid subset with its own denominator.
- Descriptive `compare` uses the captured catalogs. Matched comparison requires an explicit fixed pair roster and supporting completeness/basis; it does not infer pairs from similar names.
- `lineage` selects one typed relation view. A disconnected graph or empty witness list cannot establish independence.
- `cases` defaults to all exact-scope records; an explicit empty selector chooses none.
- Open `assess` defaults to all five conditions. Unselected conditions remain visible and block an overall affirmative conclusion. The assessment runs its actual prerequisites directly, so a separate profile or external request need not run first.

## Interpret the assessment

Read admission and execution before reading the conclusion. `valid` means the dossier passed structural/reference checks. `completed` means the requested analysis finished. Inventory and arithmetic results normally have `assessment=not_assessed` while still carrying useful counts and witnesses.

| Claim result | Meaning within the declared scope |
| --- | --- |
| `supported_under_scope` | The required implemented predicates and supplied documentary premises qualify under the fixed policy |
| `defeated_under_scope` | A decisive scoped contradiction defeats the claim; other supported premises remain visible |
| `unestablished` | The available analysis does not establish the claim, including missing, unresolved, expired or unfinished prerequisites |
| `not_assessed` | No claim assessment was performed for that result |

Individual criteria use `contradicted_under_scope` for a contradiction and `unresolved` for an unresolved assessment. Read their reasons and evidence references rather than treating all non-support states as equivalent.

A narrow regression claim keeps its finite scope and can be supported by the corresponding execution-validation evidence and reviews. Complete disclosures for an open claim still leave `lint` at `unestablished` unless a decisive contradiction defeats it. The separate open `assess` operation evaluates five non-compensatory conditions:

| Condition | What the supplied evidence must address |
| --- | --- |
| Structural validity | Frame/target fidelity and accountability for captured anomalies |
| External presence | Qualified outside-process contact, claim relevance and recorded use |
| Source integrity | Captured provenance/transformations, validation-type fit and evaluator relationships |
| Tail retention | Adequate designation, representation and visibility of declared tail results |
| Corrective capacity | Route and authority, route operability and the claimed capacity extent |

All fourteen fixed criteria, required selections, currentness and complete dependent work must qualify for overall support. There is no aggregate score that compensates for a failed condition. The permitted affirmative meaning is: supported under the declared scope, supplied evidence and `ect-core/0.1` policy.

A tested correction drill establishes only the supported `tested_route` extent. A documented restriction outcome retains that objective; it does not become a repair. A sustained-capacity claim needs separate history evidence. Likewise, a supplied assessment of source integrity may retain known shared origins and lineage limits. It does not create a universal independence guarantee.

## Reports, failures and repeat runs

JSON is authoritative. Markdown renders the same report with a reading view and an inert complete-report block. Exact fractions retain their denominators. Finding families such as EC101 or EC108 identify categories, not severity ranks. Inspect `basis`, `support_ids`, `contrary_ids`, `dependency_ids`, reasons and limitations. `needed_information` identifies the rule's information need; it does not promise that adding one record will establish the claim.

| Exit | Action |
| --- | --- |
| `0` | Inspect the report. Admission or analysis completed, even if the claim is unresolved or defeated. |
| `1` | Resolve the I/O, delivery or internal failure before treating the run as successful. |
| `2` | Correct the usage or input admission error; diagnostics use sanitized codes and positions. |
| `3` | Inspect partial/not-run states and resource reasons. Reduce the dossier or selection where appropriate; preserve the original run. |

Input is one explicitly named regular file of at most 10 MiB. The CLI refuses stdin, archives, symlinks/reparse points and nonregular files. Output files require an existing ordinary parent directory and a new name. There is no overwrite flag or automatic directory creation. Work limits are deterministic. The 20 MiB delivery cap covers canonical JSON and expanded Markdown; if either exceeds it, both formats use the same compact partial report with undeliverable basis and conclusions removed together.

Raw evidence bodies and locators are omitted from reports, but supplied identifiers remain. Treat dossiers and reports as private and review them before sharing. The filesystem boundary assumes a user-controlled directory; it does not protect against a concurrent hostile local process replacing path components. The runtime does not read auxiliary evidence files, execute dossier text, access the network or publish reports.

The public API can inspect the same saved dossier:

```python
from pathlib import Path
from evaluation_closure_toolkit import analyze_bytes, render_markdown, validate_bytes

dossier_bytes = Path("my-dossier.json").read_bytes()
admission = validate_bytes(dossier_bytes)
report = analyze_bytes(dossier_bytes, request_ids=("lint-main",))
markdown = render_markdown(report)
print(admission["admission"], report["execution"])
```

File reading in this example is explicit caller code. The byte APIs themselves do not read paths. Invalid input produces a sanitized admission report; selection mistakes raise `RequestError`, non-byte arguments raise `TypeError`, internal failures raise `InternalError`, and invalid or oversized saved reports raise `ReportError` during rendering.

Keep original dossier bytes, selection, artifact/build identity, interpreter identity and contracts for reruns. Reformatting the input changes its digest even when analytical values are equal. Follow the [reproducibility guide](REPRODUCIBILITY.md) to verify exact bytes, result digests and saved-report rendering, or to compare substantive content across qualified runtimes. A digest establishes byte identity, without authenticating the evidence or proving the underlying claims.
