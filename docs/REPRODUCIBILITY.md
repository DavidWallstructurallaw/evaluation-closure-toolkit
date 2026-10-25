# Deterministic reruns and saved reports

P1-5 uses the existing `validate`, `analyze` and `demo` commands and the public
byte-oriented API. A rerun means keeping the original dossier and executing the
same selection again. There is no capture-archive format or `replay` command.
Simulation, benchmark execution and external evidence collection remain outside
ECT v0.1.

## What to retain

Keep these together in a private, user-controlled working directory:

- The **exact original dossier bytes**, including whitespace and final newline.
- The selected request IDs, or the fact that all dossier requests were selected.
  Reports record the normalized selection in `selected_request_ids`.
- The authoritative JSON report, including its input and result digests.
- The installed wheel and its SHA-256, plus the source commit/build record when
  available. Retain the actual artifact; a version string alone does not identify
  an immutable build.
- Python implementation/version and operating system, together with the report's
  tool and contract identities: `tool_version`, `build_id`, `dossier_schema`,
  `schema`, `method`, `serialization` and `policy`.

Development version `0.1.0.dev5` reports `build_id: "unknown"`. Repeated local
bytes can demonstrate deterministic execution in a controlled environment, but
that field cannot establish immutable same-build provenance. Release build
qualification remains P1-6 work. The dossier's `analysis_time` is supplied input,
not a captured execution timestamp or an independently verified evidence cutoff.

The guarantees assume the same original bytes, request selection, tool build,
interpreter identity and contract versions. Changing whitespace in the dossier
changes `input_sha256` and report identity, even if the analytical values agree.
Request argument order is normalized; duplicate IDs are rejected. A changed set
of selected requests is a different run.

## Run the complete installed example

Use the interpreter in which this development package is installed, outside the
source checkout. The commands below use `python`; substitute that interpreter's
explicit path if necessary. Start in an existing ordinary directory with none
of the example output filenames already present.

`demo` analyzes a packaged synthetic dossier. It does not export the dossier:

```sh
python -m evaluation_closure_toolkit demo bounded-workflow --format markdown --output demo.report.md
```

To retain the original bytes, save the following as `prepare_example.py` and run
`python prepare_example.py`. This explicit caller-side copy uses exclusive
creation, so an existing `dossier.json` is not replaced:

```python
from importlib import resources
from pathlib import Path

data = resources.files("evaluation_closure_toolkit").joinpath(
    "data", "bounded-workflow.json"
).read_bytes()
with Path("dossier.json").open("xb") as output:
    output.write(data)
```

Then run:

```sh
python -m evaluation_closure_toolkit validate dossier.json --output admission.json
python -m evaluation_closure_toolkit analyze dossier.json --output run-a.json
python -m evaluation_closure_toolkit analyze dossier.json --output run-b.json
python -m evaluation_closure_toolkit analyze dossier.json --format markdown --output run-cli.md
```

The example contains `lint-main`, `profile-main`, `compare-main`, `lineage-main`,
`external-main`, `cases-main` and `assess-main`. Omitting `--request` selects all
seven. To rerun only a known subset, repeat the exact selection on both runs:

```sh
python -m evaluation_closure_toolkit analyze dossier.json --request lint-main --request assess-main --output selected.json
```

Unselected requests remain explicit `not_selected` / `not_run` rows. They are
not completed analyses. Complete open-claim disclosures in this synthetic
example leave the lint conclusion `unestablished`; the separate assessment uses
the actual fixed five-condition prerequisites. Supported assessment remains
conditional on the supplied, finite evidence and scope. Structural fractions,
lineage overlap and a correction drill do not establish universal openness or
independence.

## Compare bytes, check digests and render saved JSON

Save this as `check_rerun.py` and run `python check_rerun.py` after the commands
above. It uses only Python's standard library and the public `render_markdown`
API. No analysis is rerun when rendering the saved JSON.

```python
import hashlib
import json
from pathlib import Path

from evaluation_closure_toolkit import render_markdown


def canonical(value):
    return (json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ) + "\n").encode("utf-8")


first = Path("run-a.json").read_bytes()
second = Path("run-b.json").read_bytes()
assert first == second, "Same-environment report bytes differ"
report = json.loads(first)
assert first == canonical(report), "Saved report is not canonical JSON"
assert report["input_sha256"] == hashlib.sha256(
    Path("dossier.json").read_bytes()
).hexdigest(), "Dossier bytes differ from the analyzed input"
unsigned = {key: value for key, value in report.items() if key != "result_sha256"}
assert report["result_sha256"] == hashlib.sha256(canonical(unsigned)).hexdigest(), (
    "Result digest mismatch"
)

markdown = render_markdown(report).encode("utf-8")
assert markdown == Path("run-cli.md").read_bytes(), "Saved/CLI rendering differs"
with Path("run-saved.md").open("xb") as output:
    output.write(markdown)
print("Exact rerun, input/result digests and saved-report rendering agree")
```

Canonical report JSON is UTF-8 with ASCII escapes, sorted object keys, compact
separators, no indentation and exactly one terminal LF. The report grammar
permits neither floats nor nulls. `result_sha256` covers that canonical report
after removing only its own field, including the terminal LF. The helper above
reproduces this serialization for valid reports; it is not a general report
validator. `render_markdown` validates the report shape and digest before
rendering. A self-consistent digest alone does not validate a report's semantics.

The JSON report is authoritative. Markdown preserves its substantive results,
states, exact integers/fractions, evidence references and limitations; its full
inert report block provides the same content. It does not introduce rounded
scores. Both outputs omit raw evidence bodies and locators. They still contain
user-supplied IDs and should be treated as private. Digests identify captured
bytes; they do not authenticate evidence, establish textual truth or provide
scientific validation.

## Comparing supported runtime cells

The selected qualification cells are CPython 3.12 and 3.13 on Ubuntu 22.04 x64
and Windows Server 2022 x64. Different interpreter identities change complete
report bytes and `result_sha256`. Cross-runtime checks therefore compare
normalized substantive report content, rather than promising identical full
reports. Successful tests qualify the software behavior examined.

Before normalization, verify that both reports came from the retained artifact
or otherwise independently established same build, and compare the exact
input digest, selection and contracts. For example, given two valid decoded
reports `left` and `right`:

```python
same_run_fields = (
    "input_sha256", "selected_request_ids", "dossier_schema", "schema",
    "method", "serialization", "policy", "tool_version", "build_id",
)
for field in same_run_fields:
    assert left[field] == right[field], f"Different run identity: {field}"

excluded = {
    "tool_version", "build_id", "python_implementation", "python_version",
    "input_sha256", "result_sha256",
}
left_content = {key: value for key, value in left.items() if key not in excluded}
right_content = {key: value for key, value in right.items() if key not in excluded}
assert left_content == right_content, "Substantive reports differ"
```

Validate each saved report and its digest before this comparison. Equality of
two `unknown` build IDs is not independent evidence of same-build provenance.
The input-digest check happens **before** exclusion so changed input cannot be
silently normalized away. The comparison preserves all results, findings,
scopes, evidence references, states and limitations, including report order.
Different method/schema versions require an explicit comparison of changed
contracts. They must not be described as an automatic exact rerun. Changes to
tool builds or inputs likewise require separate qualification and explanation.

## Failures and partial work

| Exit | Interpretation |
|---|---|
| 0 | The requested operation and delivery completed. Claims can still be unresolved or defeated; `validate` checks admission only. |
| 1 | I/O, delivery or internal failure. Do not treat an output as a successful run. |
| 2 | Usage or input-admission failure, including admission resource limits. |
| 3 | Admitted input with selected work partial or not run. Inspect the reason-bearing report. |

Delivery failure takes precedence over partial-work exit 3. Deterministic
resource limits preserve completed witnesses where deliverable, mark unfinished
work and block conclusions that depend on it. A compact delivery-limit report
does not imply absence of evidence. Inspect `execution`, each result's
selection/execution state, reasons and limitations before comparing outcomes.

The CLI accepts one explicitly named regular input file, not stdin, a directory
or archive. It refuses symlink/reparse-point paths and creates new output files
exclusively in an existing ordinary parent directory. There is no `--force` or
automatic directory creation. Choose fresh output names for another run; do not
erase prior evidence merely to make an example succeed. The snippets assume a
user-controlled directory, not protection against a concurrent hostile local
process replacing path components. The installed runtime does not dereference
dossier locators, read auxiliary evidence files, launch commands or use network
access.
