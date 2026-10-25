"""Verify a built wheel in a fresh offline virtual environment outside the source tree.

Usage: python scripts/check_install.py --wheel dist/evaluation_closure_toolkit-0.1.0.dev1-py3-none-any.whl

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
data = data_root.joinpath("incomplete-regression.json").read_bytes()
assert ect.validate_bytes(data)["admission"] == "valid"
report = ect.analyze_bytes(data)
assert report["execution"] == "completed"
assert report["results"][0]["values"]["claim_conclusion"] == "unestablished"
assert ect.render_markdown(report).strip(), "Markdown renderer returned no report"
Path("dossier.json").write_bytes(data)
print("API, version identity, packaged schema and zero runtime dependencies verified")
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
        expected = {
            "incomplete-regression": "unestablished",
            "supported-narrow-regression": "supported_under_scope",
            "scope-mismatch": "defeated_under_scope",
            "open-claim-lint": "unestablished",
        }
        for name, conclusion in expected.items():
            report = json.loads(_run([str(console), "demo", name], working, environment, f"Packaged demo {name}"))
            assert report["admission"] == "valid" and report["execution"] == "completed"
            assert report["results"][0]["values"]["claim_conclusion"] == conclusion, name
        admitted = json.loads(_run([str(console), "validate", "dossier.json"], working, environment, "Installed validate"))
        assert admitted["admission"] == "valid" and admitted["results"] == []
        analyzed = json.loads(_run([str(console), "analyze", "dossier.json", "--request", "lint-main"], working, environment, "Installed analyze"))
        assert analyzed["results"][0]["values"]["claim_conclusion"] == "unestablished"
        _run([str(console), "analyze", "dossier.json", "--format", "markdown", "--output", "report.md"], working, environment, "Installed Markdown output")
        assert (working / "report.md").read_text(encoding="utf-8").strip()
        print(f"{version.strip()}: fresh offline install, both entry points, four demos, validate/analyze and Markdown output passed")
        print(f"Local verification runtime: {sys.implementation.name} {sys.version.split()[0]} on {sys.platform}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
