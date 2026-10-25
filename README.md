# Evaluation Closure Toolkit

Inspect a supplied AI evaluation dossier offline, with conclusions tied to its declared scope and evidence.

Use it when an evaluation claim needs an inspectable record of what was tested, what its population covers, where its evidence came from, and whether external input and correction routes were actually documented. Supply one local JSON dossier; receive scoped findings and exact counts in JSON or Markdown. No model service or credentials are required.

**P1-6 release candidate: `0.1.0rc1`.** All seven specified operations are implemented. This branch prepares release qualification and user documentation; it does not publish stable `0.1.0`. See the [user guide](docs/USER_GUIDE.md) for preparing real dossiers and the [release procedure](docs/RELEASE.md) for candidate provenance and acceptance.

## Install and try

Use 64-bit CPython 3.12 or 3.13. The qualification matrix is Ubuntu 22.04 x64 and Windows Server 2022 x64; other systems remain unqualified. From this candidate checkout:

```sh
python -m pip install .
```

A source-checkout install reports `build_id=unknown`. For an already qualified local wheel, use `python -m pip install --no-index --no-deps PATH_TO_WHEEL`; the [release procedure](docs/RELEASE.md) explains how its source revision is embedded and verified. No package-index publication is assumed.

The runtime uses only the Python standard library. Source installation needs setuptools as a build dependency and may access a package index for build tooling. The fourteen demos are synthetic, packaged with the wheel, and require no network, credentials, external model or predecessor toolkit. `demo` analyzes a packaged dossier; it does not export the dossier.

Run the following after installation in a private working directory with fresh output names. These examples are executed from the installed wheel during qualification.

<!-- ect-quickstart:start -->

```sh
evaluation-closure --version
evaluation-closure demo bounded-workflow --format markdown --output demo-report.md
```

For an editable dossier and a public-API example, save this as `quickstart.py` and run it with your installed Python:

```python
from importlib import resources
from pathlib import Path
from evaluation_closure_toolkit import analyze_bytes, render_markdown, validate_bytes

dossier_bytes = resources.files("evaluation_closure_toolkit").joinpath(
    "data", "bounded-workflow.json"
).read_bytes()
with Path("dossier.json").open("xb") as output:
    output.write(dossier_bytes)
admission = validate_bytes(dossier_bytes)
report = analyze_bytes(dossier_bytes, request_ids=("lint-main",))
markdown = render_markdown(report)
print(admission["admission"], report["execution"])
```

```sh
evaluation-closure validate dossier.json
evaluation-closure analyze dossier.json --request lint-main --output report.json
evaluation-closure analyze dossier.json --request lint-main --format markdown --output report.md
```

<!-- ect-quickstart:end -->

Start with `bounded-workflow` for all seven operations in one finite scope. It compares two captured items with three: SCI changes from `1/2` to `5/9` and D from `1/2` to `4/9`. Its open-claim lint has complete disclosures yet remains `unestablished`; separate assessment supports all five conditions under the supplied evidence and policy. Shared lineage remains visible and supplies no automatic independence conclusion. Correction capacity remains a tested drill route. These statements describe the fixture, not a real evaluated system.

| Demo | Expected claim conclusion |
| --- | --- |
| `incomplete-regression` | `unestablished` |
| `supported-narrow-regression` | `supported_under_scope` |
| `scope-mismatch` | `defeated_under_scope` |
| `open-claim-lint` | `unestablished`, even with complete disclosures |

| Structural demo | What it shows |
| --- | --- |
| `growing-catalog` | 24 to 48 items, while observed structural support falls from four classes to three; exact descriptive SCI change `1/24` |
| `matched-cohort` | A separately declared fixed 24-pair cohort gives SCI change `1/12`; its denominator stays distinct from the catalog comparison |
| `recut-comparison` | The same 24 items are reannotated into five classes; direct cross-frame deltas remain unavailable |

| Lineage/contact demo | What it shows |
| --- | --- |
| `shared-lineage` | Two explicit acquisition paths share a source while an unknown frontier remains; a separate rubric view has no captured overlap, without establishing independence |
| `recursive-reuse` | A later generation process uses an earlier output with a finite production/use path and explicit chronology; the graph is acyclic |
| `external-contact` | Three members, three retention events, but only one retained member; documented use survives missing receipt logs and a wrong-scope externality review |

| Correction/assessment demo | What it shows |
| --- | --- |
| `correction-cases` | Effective restriction remains documented with unknown authority; a separate accepted ticket has no linked action or outcome |
| `revision-accountability` | Documented revision, incorporation and reviewed fidelity are separate; cosmetic relabeling cannot support a recut |
| `supported-open-evaluation` | Fourteen distinct reviews and typed witnesses support all five conditions in one finite synthetic scope; corrective extent remains a tested drill route |

## Use your dossier

The [user guide](docs/USER_GUIDE.md) maps each operation to the records it needs, explains unknown/withheld facts, and starts with a smaller incomplete example. Replace synthetic records with your own evidence before making any real-world claim.

Input must be an explicit regular JSON file. Output defaults to stdout; `--output` creates one new file in an existing directory and refuses overwrite. Symlinks, reparse points and nonregular files are refused. Locators and evidence text stay inert. The tool never fetches documents, executes models, launches processes, or publishes reports.

Both byte APIs return a sanitized report for invalid JSON or schema/reference failures. Selection mistakes raise `RequestError`; non-byte arguments raise `TypeError`. Unexpected engine faults raise payload-free `InternalError`. Rendering an invalid current report raises `ReportError`.

| Exit | Meaning |
| --- | --- |
| `0` | Admission or selected analysis completed; evidence gaps and defeated claims can still be present |
| `1` | I/O, delivery or internal failure |
| `2` | Usage or admission error |
| `3` | Valid input with partial selected work |

`lint`, `profile`, `compare`, `lineage`, `external`, `cases` and `assess` all execute. Unknown operations fail admission. Default analysis selects all requests, subject to the 16-request execution limit; explicit selections must be nonempty, unique and exact. Deterministic resource limits produce partial results, an `EC108` finding and exit `3`.

The 20 MiB report-delivery limit applies to both canonical JSON and expanded Markdown. If either would exceed it, analysis returns one compact partial report for both formats, omitting detailed basis and conclusions together. Rendering a separately supplied oversized saved report raises `ReportError` rather than silently changing it.

## What the result establishes

Lint checks ten disclosure rows, structured feature mismatches, documentary review qualification, contrary premises and expiry under the dossier's supplied `analysis_time`. Missing semantic facts remain explicit gaps. A narrow regression claim can be supported only under the declared scope, supplied evidence and `ect-core/0.1` policy. Open-claim lint does not execute the five-condition assessment.

Structural profiles report captured membership, admitted assignments, unresolved cases, class counts and exact SCI/D fractions. A requested confirmed-valid view retains the selected population beside it and uses its own denominator. Unknown membership preserves a labeled known subset while leaving full-population metrics unavailable. Model failure receipts do not remove items from structural coverage.

Descriptive comparisons require compatible known frames and exact policies. Matched comparisons additionally require an explicit complete pair roster with justified endpoints; an unresolved endpoint blocks the requested contrast. Reviewed one-to-one relabels can qualify for comparison, including zero-count classes. A recut retains side-by-side profiles. Tail presence, zero sightings, complete absence and loss are reported separately under the actual population scope.

Lineage requests traverse one exact-scope relation view and retain finite shortest paths, known overlap, explicit unknown frontiers and captured terminals. Terminals and disconnected graphs do not prove independent origins. Independence reviews retain their exact member set, pairwise/setwise form and dimension. Recursive-use witnesses additionally require ordered process/use times; a static cycle supplies no causal history by itself.

External requests count each contribution once per stage, separately from raw event counts. Receipt, retention, selection and use remain independent axes. Externality and suitability for the named use require separate member-bound reviews. Old carryover cannot supply fresh contact. Incomplete cohort membership yields labeled known-subset counts, without an invented population denominator or presence score.

Case requests retain anomaly preservation and disposition, revision documentation/incorporation/fidelity, and separate route, authority, handling, attempt, action and objective-specific outcome checks. Unique case/target counts remain separate from events. A supported restriction result establishes only the supplied restriction objective; a repair requires a baseline. Unknown authority limits capacity while preserving qualified outcome evidence. Drill context stays explicit.

Assessment requests execute their structural, external and case prerequisites directly. Select one `snapshot_id` and `cohort_id` for a full open claim. All five condition rows remain visible, including unselected conditions. Each of the fourteen fixed criteria requires its own scoped review and typed witnesses. Missing evidence or an unselected condition prevents overall support; a decisive scoped counterexample defeats the claim while other evidence remains visible. Expiry also prevents gate support. `tested_route` and `sustained` capacity have separate evidence requirements. No aggregate openness score is computed.

Review receipts use explicit `subject_ids` to bind the supplied judgment to the relevant frame, inventory, member/use target or case. The [P1-4 interpretation guide](docs/P1-4.md) explains these anchors, bounded empty inventories and history receipts. Favorable prose cannot replace a missing fixed criterion. A narrow `assess` request retains the existing finite regression rule, an empty conditions list and `open_evaluation=not_applicable`.

The tool does not authenticate receipts, prove textual assertions or authorize deployment. JSON and Markdown omit raw evidence bodies and locators. Reports contain supplied identifiers and should be treated as private. Markdown includes a scoped reading view with request states, disclosures, criteria, prerequisite status, findings, evidence references, needed information and limitations, followed by the complete inert report object. Finding families identify the kind of issue or observation; they are not severity rankings. Inventory/arithmetic rows remain `not_assessed`.

Input identity hashes the original bytes. Result identity hashes canonical JSON excluding its own digest, with a final newline. Candidate builds embed `ect-VERSION+git.SOURCE_REVISION` from a clean committed export; ordinary source builds remain `unknown`. Retain the actual artifact and check its hash and expected revision. These identities do not supply a signature, authenticate evidence or promise byte-reproducible packaging. Results include interpreter identity, so cross-runtime comparisons use normalized substantive fields.

The [deterministic rerun guide](docs/REPRODUCIBILITY.md) shows how to retain an exact dossier, rerun the existing commands, verify report bytes and digests, and render saved JSON through the public API. Keep original bytes and matching selection/contracts before comparing normalized outputs. Capture archives, a `replay` command and simulation remain outside this release.

The bounded local-file checks assume a user-controlled directory. They do not claim protection against a concurrent hostile process replacing directory components.

## Contract and development

- [Approved executable specification](docs/phase0/P0-3_Minimal_Executable_Specification.md)
- [Readiness decision](docs/phase0/P0-4_Readiness_Decision.md)
- [P1-1 implementation and verification](docs/P1-1.md)
- [P1-2 implementation and verification](docs/P1-2.md)
- [P1-3 implementation and verification](docs/P1-3.md)
- [P1-4 implementation and verification](docs/P1-4.md)
- [P1-5 reporting, workflow and rerun integration](docs/P1-5.md)
- [P1-6 release qualification](docs/P1-6.md)
- [User guide](docs/USER_GUIDE.md)
- [Candidate build and release procedure](docs/RELEASE.md)
- [Deterministic rerun guide](docs/REPRODUCIBILITY.md)
- [Machine-readable dossier schema](src/evaluation_closure_toolkit/data/dossier.schema.json)

The JSON Schema describes closed local shapes. Admission also checks exact byte/token limits, timestamps, typed references, immutable identities and cross-record bindings. A generic JSON Schema validator cannot replace the byte API.

```sh
python -m pip install .
python -m unittest discover -s tests -v
python scripts/generate_schema.py --check
python -m pip install build
python -m build
python scripts/check_install.py --wheel dist/evaluation_closure_toolkit-0.1.0rc1-py3-none-any.whl
```

The commands above check an ordinary source build with unknown identity. The [candidate build procedure](docs/RELEASE.md) additionally requires an exact clean source revision and verifies the stamped artifact. CI qualifies that exact revision in all four selected cells, including tests from the extracted source distribution and fresh offline installation outside the checkout. See the pull request checks for actual results. All examples remain synthetic; no real-data effectiveness pilot is claimed.

License: Apache-2.0.
