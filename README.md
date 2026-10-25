# Evaluation Closure Toolkit

Inspect a supplied AI evaluation dossier offline, with conclusions tied to its declared scope and evidence.

**Development stage: P1-3, version `0.1.0.dev3`.** This slice implements strict dossier admission, claim lint, structural accounting, compatible snapshot comparison, typed lineage and member-scoped external contact. Correction analysis and five-condition assessment remain subsequent stages.

## Install and try

Use CPython 3.12 or 3.13. From a checkout:

```sh
python -m pip install .
evaluation-closure demo incomplete-regression
evaluation-closure demo supported-narrow-regression --format markdown
evaluation-closure demo scope-mismatch
evaluation-closure demo open-claim-lint
evaluation-closure demo growing-catalog --format markdown
evaluation-closure demo matched-cohort
evaluation-closure demo recut-comparison
evaluation-closure demo shared-lineage --format markdown
evaluation-closure demo recursive-reuse
evaluation-closure demo external-contact --format markdown
```

The runtime uses only the Python standard library. Installation needs setuptools as a build dependency. The ten demos are synthetic, packaged with the wheel, and require no network, credentials, external model or predecessor toolkit.

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

## Use your dossier

```sh
evaluation-closure validate dossier.json
evaluation-closure analyze dossier.json --request lint-main
evaluation-closure analyze dossier.json --format markdown --output new-report.md
```

Input must be an explicit regular JSON file. Output defaults to stdout; `--output` creates one new file in an existing directory and refuses overwrite. Symlinks, reparse points and nonregular files are refused. Locators and evidence text stay inert. The tool never fetches documents, executes models, launches processes, or publishes reports.

```python
from evaluation_closure_toolkit import analyze_bytes, validate_bytes, render_markdown

admission = validate_bytes(dossier_bytes)
report = analyze_bytes(dossier_bytes, request_ids=("lint-main",))
markdown = render_markdown(report)
```

Both byte APIs return a sanitized report for invalid JSON or schema/reference failures. Selection mistakes raise `RequestError`; non-byte arguments raise `TypeError`. Unexpected engine faults raise payload-free `InternalError`. Rendering an invalid current report raises `ReportError`.

| Exit | Meaning |
| --- | --- |
| `0` | Admission or selected analysis completed; evidence gaps and defeated claims can still be present |
| `1` | I/O, delivery or internal failure |
| `2` | Usage or admission error |
| `3` | Valid input with partial or unsupported selected work |

All seven request grammars are admitted. `lint`, `profile`, `compare`, `lineage` and `external` execute in P1-3. `cases` and `assess` remain deferred. A selected deferred operation returns `not_run`, `unsupported_operation`, an `EC108` finding and exit `3`. Unknown operations fail admission. Default analysis selects all requests, subject to the 16-request execution limit; explicit selections must be nonempty, unique and exact.

## What the result establishes

Lint checks ten disclosure rows, structured feature mismatches, documentary review qualification, contrary premises and expiry under the dossier's supplied `analysis_time`. Missing semantic facts remain explicit gaps. A narrow regression claim can be supported only under the declared scope, supplied evidence and `ect-core/0.1` policy. Open-claim lint does not execute the five-condition assessment.

Structural profiles report captured membership, admitted assignments, unresolved cases, class counts and exact SCI/D fractions. A requested confirmed-valid view retains the selected population beside it and uses its own denominator. Unknown membership preserves a labeled known subset while leaving full-population metrics unavailable. Model failure receipts do not remove items from structural coverage.

Descriptive comparisons require compatible known frames and exact policies. Matched comparisons additionally require an explicit complete pair roster with justified endpoints; an unresolved endpoint blocks the requested contrast. Reviewed one-to-one relabels can qualify for comparison, including zero-count classes. A recut retains side-by-side profiles. Tail presence, zero sightings, complete absence and loss are reported separately under the actual population scope.

Lineage requests traverse one exact-scope relation view and retain finite shortest paths, known overlap, explicit unknown frontiers and captured terminals. Terminals and disconnected graphs do not prove independent origins. Independence reviews retain their exact member set, pairwise/setwise form and dimension. Recursive-use witnesses additionally require ordered process/use times; a static cycle supplies no causal history by itself.

External requests count each contribution once per stage, separately from raw event counts. Receipt, retention, selection and use remain independent axes. Externality and suitability for the named use require separate member-bound reviews. Old carryover cannot supply fresh contact. Incomplete cohort membership yields labeled known-subset counts, without an invented population denominator or presence score.

The tool does not authenticate receipts, prove textual assertions or authorize deployment. JSON and Markdown omit raw evidence bodies and locators. Reports contain supplied identifiers and should be treated as private. Markdown includes a concise reading view and the complete inert report object, preserving every finding and premise.

Input identity hashes the original bytes. Result identity hashes canonical JSON excluding its own digest, with a final newline. The development `build_id` is explicitly `unknown`; no immutable source-build provenance claim is made. Results include interpreter identity, so cross-runtime comparisons use normalized substantive fields.

The bounded local-file checks assume a user-controlled directory. They do not claim protection against a concurrent hostile process replacing directory components.

## Contract and development

- [Approved executable specification](docs/phase0/P0-3_Minimal_Executable_Specification.md)
- [Readiness decision](docs/phase0/P0-4_Readiness_Decision.md)
- [P1-1 implementation and verification](docs/P1-1.md)
- [P1-2 implementation and verification](docs/P1-2.md)
- [P1-3 implementation and verification](docs/P1-3.md)
- [Machine-readable dossier schema](src/evaluation_closure_toolkit/data/dossier.schema.json)

The JSON Schema describes closed local shapes. Admission also checks exact byte/token limits, timestamps, typed references, immutable identities and cross-record bindings. A generic JSON Schema validator cannot replace the byte API.

```sh
python -m pip install .
python -m unittest discover -s tests -v
python scripts/generate_schema.py --check
python -m pip install build
python -m build
python scripts/check_install.py --wheel dist/evaluation_closure_toolkit-0.1.0.dev3-py3-none-any.whl
```

CI targets CPython 3.12/3.13 on Ubuntu 22.04 and Windows Server 2022. The workflow builds a wheel through its source distribution, runs the behavioral suite and performs a fresh installed-package check. See the pull request checks for actual target results.

License: Apache-2.0.
