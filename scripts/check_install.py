"""Verify a built wheel in a fresh offline virtual environment outside the source tree.

Usage: python scripts/check_install.py --wheel dist/evaluation_closure_toolkit-0.1.0rc1-py3-none-any.whl

This development-only script intentionally launches installation and CLI processes.
The installed toolkit runtime does not launch subprocesses or make network calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

_DEMOS = (
    "incomplete-regression", "supported-narrow-regression", "scope-mismatch", "open-claim-lint",
    "growing-catalog", "matched-cohort", "recut-comparison",
    "shared-lineage", "recursive-reuse", "external-contact",
    "correction-cases", "revision-accountability", "supported-open-evaluation",
    "bounded-workflow",
)

_INSTALLED_API_CHECK = r'''
import hashlib
import json
import struct
import sys
from importlib import metadata, resources
from pathlib import Path
import evaluation_closure_toolkit as ect

assert Path(ect.__file__).is_relative_to(Path(sys.prefix)), "Import escaped installed environment"
assert struct.calcsize("P") == 8, "Qualification requires a 64-bit interpreter"
distribution = metadata.distribution("evaluation-closure-toolkit")
assert not distribution.requires, "Runtime dependency unexpectedly added"
assert distribution.version == ect.__version__, "Version identity disagrees"
expected_build_id, expected_license_sha256 = sys.argv[1:]
assert distribution.metadata["License-Expression"] == "Apache-2.0", "License expression differs"
assert distribution.metadata.get_all("License-File") == ["LICENSE"], "License-file metadata differs"
license_files = [entry for entry in distribution.files or ()
                 if str(entry).endswith(".dist-info/licenses/LICENSE")]
assert len(license_files) == 1, "Installed license file missing or ambiguous"
assert hashlib.sha256(distribution.locate_file(license_files[0]).read_bytes()).hexdigest() == expected_license_sha256, "Installed license content differs"
data_root = resources.files("evaluation_closure_toolkit").joinpath("data")
schema = json.loads(data_root.joinpath("dossier.schema.json").read_bytes())
assert schema["type"] == "object", "Packaged dossier schema missing"

def fraction(numerator, denominator):
    return {"state": "available", "value": {"numerator": str(numerator), "denominator": str(denominator)}}

def integer(value):
    return {"state": "available", "value": value}

conclusions = {
    "incomplete-regression": "unestablished",
    "supported-narrow-regression": "supported_under_scope",
    "scope-mismatch": "defeated_under_scope",
    "open-claim-lint": "unestablished",
}
for name in (*conclusions, "growing-catalog", "matched-cohort", "recut-comparison", "shared-lineage", "recursive-reuse", "external-contact", "correction-cases", "revision-accountability", "supported-open-evaluation", "bounded-workflow"):
    data = data_root.joinpath(name + ".json").read_bytes()
    admission = ect.validate_bytes(data)
    assert admission["admission"] == "valid", name
    assert admission["build_id"] == expected_build_id, "Admission build identity differs: " + name
    report = ect.analyze_bytes(data)
    assert report["build_id"] == expected_build_id, "Analysis build identity differs: " + name
    assert report["execution"] == "completed", name
    rows = {row["request_id"]: row for row in report["results"]}
    if name in conclusions:
        assert report["results"][0]["values"]["claim_conclusion"] == conclusions[name], name
    if name in {"growing-catalog", "matched-cohort"}:
        before = rows["profile-a"]["values"]["profiles"][0]
        after = rows["profile-b"]["values"]["profiles"][0]
        assert before["N"] == integer(24) and after["N"] == integer(48), name
        assert before["SCI"] == fraction(25, 72) and before["D"] == fraction(47, 72), name
        assert after["SCI"] == fraction(7, 18) and after["D"] == fraction(11, 18), name
        comparison = rows["compare-catalog"]["values"]
        assert comparison["compatibility"]["state"] == "supported", name
        assert comparison["delta_SCI"] == fraction(1, 24), name
        assert comparison["delta_D"] == fraction(-1, 24), name
    if name == "matched-cohort":
        matched = rows["compare-matched"]["values"]
        assert matched["mode"] == "matched"
        assert matched["compatibility"]["state"] == "supported"
        assert matched["pair_count"] == integer(24)
        assert matched["after"]["SCI"] == fraction(31, 72)
        assert matched["after"]["D"] == fraction(41, 72)
        assert matched["catalog_profiles"]["after"][0]["N"] == integer(48)
        assert matched["delta_SCI"] == fraction(1, 12)
        assert matched["delta_D"] == fraction(-1, 12)
    if name == "recut-comparison":
        recut = rows["compare-catalog"]["values"]
        assert recut["compatibility"]["state"] == "unavailable"
        assert "incompatible_frame" in recut["compatibility"]["reason_codes"]
        assert recut["delta_SCI"]["state"] == "unavailable"
        assert recut["delta_D"]["state"] == "unavailable"
        assert len(recut["after"]["class_counts"]) == 5
        assert recut["after"]["SCI"] == fraction(2, 9)
        assert recut["after"]["D"] == fraction(7, 9)
        assert recut["new_observations"] == integer(0)
    if name == "shared-lineage":
        lineage = rows["lineage-acquisition"]["values"]
        assert lineage["search_complete"]
        assert lineage["witnesses"] == [{"left_seed_id": "x", "right_seed_id": "y", "node_id": "origin",
                                          "left_path": ["edge-x-origin"], "right_path": ["edge-y-origin"]}]
        assert lineage["frontiers"][0]["node_id"] == "unknown-node"
        assert lineage["independence_assessments"][0]["review"]["assessment"] == "unresolved"
        assert rows["lineage-rubric"]["values"]["witnesses"] == []
    if name == "recursive-reuse":
        lineage = rows["lineage-recursive"]["values"]
        assert lineage["cycle_state"] == "no_witness_in_captured_view"
        assert lineage["recursive_witnesses"][0]["state"] == "recorded_recursive_reuse"
        assert lineage["recursive_witnesses"][0]["path"] == ["reuse-output", "produce-a"]
    if name == "external-contact":
        external = rows["external-main"]["values"]
        assert external["known_member_count"] == integer(3)
        assert external["event_counts"]["retained"] == integer(3)
        assert external["stage_counts"]["retained"] == {"yes": integer(1), "no": integer(1), "unresolved": integer(1), "disputed": integer(0)}
        members = {r["member_id"]: r for r in external["member_states"]}
        assert members["p"]["contact_state"] == "documented_current_contact"
        assert members["q"]["stages"]["used"]["state"] == "yes"
        assert members["q"]["stages"]["received"]["state"] == "unresolved"
        assert members["q"]["externality"]["assessment"] == "unresolved"
        assert members["r"]["contact_state"] == "carryover_only"
    if name == "correction-cases":
        cases = rows["cases-main"]["values"]
        assert cases["pair_counts"]["effective"] == integer(1)
        assert cases["pair_counts"]["authorized"] == integer(0)
        assert cases["event_counts"]["handling"] == integer(2)
        first, ticket = cases["corrections"]
        assert first["authority"]["assessment"] == "unresolved"
        assert first["outcomes"][0]["review"]["assessment"] == "supported_under_scope"
        assert first["outcomes"][0]["objective"] == "restrict"
        assert ticket["handling"][0]["check"]["assessment"] == "supported_under_scope"
        assert ticket["actions"] == ticket["outcomes"] == []
    if name == "revision-accountability":
        recut, rename = rows["cases-main"]["values"]["revisions"]
        assert recut["cut_state"] == "recut_documented" and recut["fidelity"]["assessment"] == "supported_under_scope"
        assert rename["cut_state"] == "relabel_only" and rename["incorporated"]["assessment"] == "supported_under_scope"
        assert rename["fidelity"]["assessment"] == "unresolved"
    if name in {"supported-open-evaluation", "bounded-workflow"}:
        assessment = rows["assess-main"]["values"]
        assert assessment["conclusion"] == "supported_under_scope"
        assert assessment["capacity_extent"] == "tested_route"
        assert len(assessment["conditions"]) == 5
        assert all(g["assessment"] == "supported_under_scope" for g in assessment["conditions"])
        assert sum(len(g["values"]["criteria"]) for g in assessment["conditions"]) == 14
        assert {p["role"] for p in assessment["prerequisites"]} == {"structural", "cases", "external"}
    if name == "bounded-workflow":
        assert {r["operation"] for r in rows.values()} == {"lint", "profile", "compare", "lineage", "external", "cases", "assess"}
        assert rows["lint-main"]["values"]["claim_conclusion"] == "unestablished"
        comparison = rows["compare-main"]["values"]
        assert comparison["before"]["SCI"] == fraction(1, 2)
        assert comparison["after"]["SCI"] == fraction(5, 9)
        assert comparison["delta_SCI"] == fraction(1, 18)
        assert comparison["delta_D"] == fraction(-1, 18)
        assert rows["lineage-main"]["values"]["witnesses"]
    markdown = ect.render_markdown(report)
    assert markdown.strip(), name
    assert ect.render_markdown(json.loads(json.dumps(report, sort_keys=True))) == markdown, name
    Path(name + ".json").write_bytes(data)
    Path(name + ".report.json").write_text(json.dumps(report), encoding="utf-8")
    Path(name + ".report.md").write_text(markdown, encoding="utf-8")
assert ect.validate_bytes(b"{")["build_id"] == expected_build_id, "Invalid-input build identity differs"
print("API, fourteen exact demo results, saved-JSON Markdown parity, expected build identity, package version/license/schema and zero runtime dependencies verified")
'''


def _run(command: list[str], cwd: Path, environment: dict[str, str], label: str) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="backslashreplace",
        timeout=60,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"{label} failed with exit {result.returncode}:\n"
            f"{result.stdout[-3000:]}\n{result.stderr[-3000:]}"
        )
    return result.stdout


def _check_documented_rerun(python: Path, working: Path, environment: dict[str, str]) -> None:
    """Execute the actual guide snippets using only the installed distribution."""
    guide = Path(__file__).resolve().parents[1] / "docs" / "REPRODUCIBILITY.md"
    blocks = re.findall(r"```(python|sh)\n(.*?)\n```", guide.read_text(encoding="utf-8"), re.S)
    assert [language for language, _ in blocks] == ["sh", "python", "sh", "sh", "python", "python"]
    for index, (language, code) in enumerate(blocks):
        if language == "sh":
            for line in code.splitlines():
                arguments = shlex.split(line)
                assert arguments and arguments[0] == "python", "Unexpected guide command"
                _run([str(python), *arguments[1:]], working, environment, "Documented CLI command")
        else:
            if index == 5:
                prelude = (
                    "import json\nfrom pathlib import Path\n"
                    "left = json.loads(Path('run-a.json').read_bytes())\n"
                    "right = json.loads(Path('run-b.json').read_bytes())\n"
                )
                _run([str(python), "-c", prelude + code], working, environment, "Documented normalization")
                # A changed input must fail before identity fields are excluded.
                negative = prelude + "right['input_sha256'] = '0' * 64\n"
                negative += "try:\n" + "\n".join("    " + line for line in code.splitlines())
                negative += "\nexcept AssertionError as exc:\n    assert 'input_sha256' in str(exc)\nelse:\n    raise AssertionError('Changed input was normalized away')\n"
                _run([str(python), "-c", negative], working, environment, "Documented input-identity guard")
            else:
                _run([str(python), "-c", code], working, environment, "Documented Python snippet")
    print("Documented installed example, exact digests, saved-report rendering and normalization guard passed")


def _check_user_examples(python: Path, console: Path, root: Path, environment: dict[str, str]) -> None:
    """Run the bounded first-use examples verbatim, outside the source checkout."""
    source = Path(__file__).resolve().parents[1]
    readme = (source / "README.md").read_text(encoding="utf-8")
    start, end = "<!-- ect-quickstart:start -->", "<!-- ect-quickstart:end -->"
    assert readme.count(start) == readme.count(end) == 1, "README quickstart markers missing or repeated"
    assert readme.index(start) < readme.index(end), "README quickstart markers are reversed"
    quickstart = readme.split(start, 1)[1].split(end, 1)[0]
    guide = (source / "docs" / "USER_GUIDE.md").read_text(encoding="utf-8")
    for label, text, expected in (
        ("README", quickstart, ["sh", "python", "sh"]),
        ("USER_GUIDE", guide, ["python", "sh", "python"]),
    ):
        blocks = re.findall(r"```(python|sh)\n(.*?)\n```", text, re.S)
        languages = [language for language, _ in blocks]
        assert languages == expected, f"Unexpected {label} runnable blocks"
        working = root / label.lower()
        working.mkdir()
        for language, code in blocks:
            if language == "python":
                _run([str(python), "-c", code], working, environment, f"{label} Python example")
            else:
                for line in code.splitlines():
                    arguments = shlex.split(line, comments=True)
                    if not arguments:
                        continue
                    assert arguments[0] in {"python", "evaluation-closure"}, f"Unexpected {label} command"
                    # Installation/development commands are deliberately outside
                    # the marked first-use region. The wheel is already installed.
                    if arguments[0] == "python":
                        assert arguments[1:3] == ["-m", "evaluation_closure_toolkit"], f"Unexpected {label} Python command"
                        entry = python
                    else:
                        entry = console
                    _run([str(entry), *arguments[1:]], working, environment, f"{label} CLI example")
        print(f"Actual {label} first-use examples passed against the installed wheel")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path, help="Built local wheel; no index access is used.")
    parser.add_argument("--expected-build-id", default="unknown",
                        help="Independently expected exact report build identity; default checks an unstamped source build.")
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    if not wheel.is_file() or wheel.suffix != ".whl":
        parser.error("--wheel must name a regular .whl file")
    environment = os.environ.copy()
    # Avoid importing the checkout through caller-provided Python configuration.
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    with tempfile.TemporaryDirectory(prefix="ect-installed-") as directory:
        root = Path(directory)
        environment_dir = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment_dir)
        executable_dir = environment_dir / ("Scripts" if os.name == "nt" else "bin")
        python = executable_dir / ("python.exe" if os.name == "nt" else "python")
        console = executable_dir / ("evaluation-closure.exe" if os.name == "nt" else "evaluation-closure")
        working = root / "working"
        working.mkdir()
        _run(
            [str(python), "-m", "pip", "--disable-pip-version-check", "install", "--no-index", "--no-deps", str(wheel)],
            working, environment, "Offline wheel installation",
        )
        license_sha256 = hashlib.sha256((Path(__file__).resolve().parents[1] / "LICENSE").read_bytes()).hexdigest()
        print(_run([str(python), "-c", _INSTALLED_API_CHECK, args.expected_build_id, license_sha256],
                   working, environment, "Installed API/identity/license/schema").strip())
        version = _run([str(console), "--version"], working, environment, "Console entry point")
        module_version = _run([str(python), "-m", "evaluation_closure_toolkit", "--version"], working, environment, "Module entry point")
        assert version == module_version, "Console/module identity disagrees"
        for name in _DEMOS:
            report = json.loads(_run([str(console), "demo", name], working, environment, f"Packaged demo {name}"))
            expected = json.loads((working / f"{name}.report.json").read_text(encoding="utf-8"))
            assert report == expected, f"Console/API result differs for {name}"
            if name in {"growing-catalog", "matched-cohort", "recut-comparison", "shared-lineage", "recursive-reuse", "external-contact", "correction-cases", "revision-accountability", "supported-open-evaluation", "bounded-workflow"}:
                markdown = _run([str(console), "demo", name, "--format", "markdown"], working, environment, f"Packaged Markdown demo {name}")
                assert markdown == (working / f"{name}.report.md").read_text(encoding="utf-8"), name
        admitted = json.loads(_run([str(console), "validate", "incomplete-regression.json"], working, environment, "Installed validate"))
        assert admitted["admission"] == "valid" and admitted["results"] == []
        assert admitted["build_id"] == args.expected_build_id, "CLI admission build identity differs"
        analyzed = json.loads(_run([str(console), "analyze", "incomplete-regression.json", "--request", "lint-main"], working, environment, "Installed analyze"))
        assert analyzed["results"][0]["values"]["claim_conclusion"] == "unestablished"
        structural = json.loads(_run([str(console), "analyze", "growing-catalog.json", "--request", "profile-a", "--request", "compare-catalog"], working, environment, "Installed profile/compare selection"))
        assert structural["selected_request_ids"] == ["compare-catalog", "profile-a"]
        assert structural["execution"] == "completed"
        _run([str(console), "analyze", "incomplete-regression.json", "--format", "markdown", "--output", "report.md"], working, environment, "Installed Markdown output")
        assert (working / "report.md").read_text(encoding="utf-8").strip()
        provenance = json.loads(_run([str(console), "analyze", "shared-lineage.json", "--request", "lineage-acquisition"], working, environment, "Installed lineage selection"))
        assert provenance["selected_request_ids"] == ["lineage-acquisition"]
        assert provenance["execution"] == "completed"
        contact = json.loads(_run([str(console), "analyze", "external-contact.json", "--request", "external-main"], working, environment, "Installed external selection"))
        assert contact["execution"] == "completed"
        cases = json.loads(_run([str(console), "analyze", "correction-cases.json", "--request", "cases-main"], working, environment, "Installed cases selection"))
        assert cases["execution"] == "completed"
        assessment = json.loads(_run([str(console), "analyze", "supported-open-evaluation.json", "--request", "assess-main"], working, environment, "Installed assess selection"))
        assert assessment["results"][0]["values"]["conclusion"] == "supported_under_scope"
        # Exact bytes are checked across both entry points and equivalent explicit
        # selections in opposite input order. No stdout newline translation occurs.
        selection = sorted(json.loads((working / "bounded-workflow.report.json").read_text(encoding="utf-8"))["selected_request_ids"])
        for entry, request_ids, output in (
            ([str(console)], selection, "rerun-a.json"),
            ([str(python), "-m", "evaluation_closure_toolkit"], list(reversed(selection)), "rerun-b.json"),
        ):
            options = [argument for request_id in request_ids for argument in ("--request", request_id)]
            _run(entry + ["analyze", "bounded-workflow.json", *options, "--output", output], working, environment, "Installed deterministic rerun")
        first = (working / "rerun-a.json").read_bytes()
        assert first == (working / "rerun-b.json").read_bytes(), "Same-input rerun bytes differ"
        assert json.loads(first) == json.loads((working / "bounded-workflow.report.json").read_text(encoding="utf-8"))
        _check_documented_rerun(python, working, environment)
        _check_user_examples(python, console, root, environment)
        print(f"{version.strip()}: fresh offline install, both entry points, fourteen demos, validate/analyze, all seven request operations, saved-JSON Markdown parity and deterministic rerun passed")
        print(f"Verified report build identity: {args.expected_build_id}")
        print(f"Local verification runtime: {sys.implementation.name} {sys.version.split()[0]} on {sys.platform}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
