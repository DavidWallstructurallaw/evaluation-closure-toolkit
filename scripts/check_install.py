"""Verify a built wheel in a fresh offline virtual environment outside the source tree.

Usage: python scripts/check_install.py --wheel dist/evaluation_closure_toolkit-0.1.0.dev3-py3-none-any.whl

This development-only script intentionally launches installation and CLI processes.
The installed toolkit runtime does not launch subprocesses or make network calls.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

_DEMOS = (
    "incomplete-regression", "supported-narrow-regression", "scope-mismatch", "open-claim-lint",
    "growing-catalog", "matched-cohort", "recut-comparison",
    "shared-lineage", "recursive-reuse", "external-contact",
)

_INSTALLED_API_CHECK = r'''
import json
import sys
from importlib import metadata, resources
from pathlib import Path
import evaluation_closure_toolkit as ect

assert Path(ect.__file__).is_relative_to(Path(sys.prefix)), "Import escaped installed environment"
distribution = metadata.distribution("evaluation-closure-toolkit")
assert not distribution.requires, "Runtime dependency unexpectedly added"
assert distribution.version == ect.__version__, "Version identity disagrees"
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
for name in (*conclusions, "growing-catalog", "matched-cohort", "recut-comparison", "shared-lineage", "recursive-reuse", "external-contact"):
    data = data_root.joinpath(name + ".json").read_bytes()
    assert ect.validate_bytes(data)["admission"] == "valid", name
    report = ect.analyze_bytes(data)
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
    markdown = ect.render_markdown(report)
    assert markdown.strip(), name
    Path(name + ".json").write_bytes(data)
    Path(name + ".report.json").write_text(json.dumps(report), encoding="utf-8")
    Path(name + ".report.md").write_text(markdown, encoding="utf-8")
print("API, ten exact demo results, version identity, packaged schema and zero runtime dependencies verified")
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path, help="Built local wheel; no index access is used.")
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
        print(_run([str(python), "-c", _INSTALLED_API_CHECK], working, environment, "Installed API/schema").strip())
        version = _run([str(console), "--version"], working, environment, "Console entry point")
        module_version = _run([str(python), "-m", "evaluation_closure_toolkit", "--version"], working, environment, "Module entry point")
        assert version == module_version, "Console/module identity disagrees"
        for name in _DEMOS:
            report = json.loads(_run([str(console), "demo", name], working, environment, f"Packaged demo {name}"))
            expected = json.loads((working / f"{name}.report.json").read_text(encoding="utf-8"))
            assert report == expected, f"Console/API result differs for {name}"
            if name in {"growing-catalog", "matched-cohort", "recut-comparison", "shared-lineage", "recursive-reuse", "external-contact"}:
                markdown = _run([str(console), "demo", name, "--format", "markdown"], working, environment, f"Packaged Markdown demo {name}")
                assert markdown == (working / f"{name}.report.md").read_text(encoding="utf-8"), name
        admitted = json.loads(_run([str(console), "validate", "incomplete-regression.json"], working, environment, "Installed validate"))
        assert admitted["admission"] == "valid" and admitted["results"] == []
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
        print(f"{version.strip()}: fresh offline install, both entry points, ten demos, validate/analyze, profile/compare/lineage/external selection and Markdown output passed")
        print(f"Local verification runtime: {sys.implementation.name} {sys.version.split()[0]} on {sys.platform}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
