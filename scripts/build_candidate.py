"""Build a candidate from one clean, explicitly selected Git commit.

This maintainer-only script exports committed source, stamps only that copy,
builds an sdist, and builds the wheel from its extracted source distribution.
It does not publish artifacts, create tags, modify the checkout or authenticate
the recorded source. Build tooling may download its isolated dependencies.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tomllib
from email.parser import BytesParser
import zipfile


_PACKAGE = "evaluation_closure_toolkit"
_IDENTITY_PATH = f"src/{_PACKAGE}/_build_info.py"
_INIT_PATH = f"src/{_PACKAGE}/__init__.py"
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_VERSION = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:rc(?:0|[1-9][0-9]*))?\Z")


class CandidateError(RuntimeError):
    """A build precondition or artifact identity did not qualify."""


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    # The exported project must not import the caller's checkout or use an
    # alternate Git index/work tree when checking its committed source.
    for name in ("PYTHONPATH", "PYTHONHOME", "GIT_DIR", "GIT_WORK_TREE",
                 "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
                 "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
        environment.pop(name, None)
    return environment


def _git(repository: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(repository), *arguments],
        env=_environment(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if result.returncode:
        raise CandidateError("GIT_COMMAND_FAILED")
    return result.stdout


def _literal_assignment(source: str, name: str) -> str:
    values = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name for target in node.targets):
            values.append(ast.literal_eval(node.value))
    if len(values) != 1 or type(values[0]) is not str:
        raise CandidateError("PACKAGE_LITERAL_INVALID")
    return values[0]


def _version_from_text(project: str, initializer: str) -> str:
    metadata = tomllib.loads(project).get("project", {})
    if metadata.get("name") != "evaluation-closure-toolkit":
        raise CandidateError("PACKAGE_NAME_MISMATCH")
    version = metadata.get("version")
    if type(version) is not str or not _VERSION.fullmatch(version):
        raise CandidateError("VERSION_UNSUPPORTED")
    if _literal_assignment(initializer, "__version__") != version:
        raise CandidateError("VERSION_MISMATCH")
    return version


def _source_version(source: Path) -> str:
    return _version_from_text(
        (source / "pyproject.toml").read_text(encoding="utf-8"),
        (source / _INIT_PATH).read_text(encoding="utf-8"),
    )


def _preflight(repository: Path, revision: str, output: Path) -> tuple[Path, str]:
    if not _REVISION.fullmatch(revision):
        raise CandidateError("REVISION_INVALID")
    actual_root = Path(os.fsdecode(_git(repository, "rev-parse", "--show-toplevel")).strip()).resolve()
    if actual_root != repository:
        raise CandidateError("CHECKOUT_ROOT_MISMATCH")
    if _git(repository, "rev-parse", "HEAD").decode("ascii").strip() != revision:
        raise CandidateError("HEAD_MISMATCH")
    if _git(repository, "status", "--porcelain=v1", "--untracked-files=all").strip():
        raise CandidateError("SOURCE_DIRTY")
    # Check the original path before resolving it, including dangling links.
    if output.exists() or output.is_symlink():
        raise CandidateError("OUTPUT_EXISTS")
    output = output.resolve()
    if output.is_relative_to(repository):
        raise CandidateError("OUTPUT_IN_CHECKOUT")
    if not output.parent.is_dir():
        raise CandidateError("OUTPUT_PARENT_INVALID")
    version = _version_from_text(
        _git(repository, "show", f"{revision}:pyproject.toml").decode("utf-8"),
        _git(repository, "show", f"{revision}:{_INIT_PATH}").decode("utf-8"),
    )
    identity = _literal_assignment(
        _git(repository, "show", f"{revision}:{_IDENTITY_PATH}").decode("utf-8"), "BUILD_ID")
    if identity != "unknown":
        raise CandidateError("SOURCE_BUILD_ID_NOT_UNKNOWN")
    return output, version


def _archive_members(archive: tarfile.TarFile, prefix: str) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    names = [member.name for member in members]
    if (not names or len(names) != len(set(names))
            or any("\\" in name or ".." in PurePosixPath(name).parts
                   or (name != prefix and not name.startswith(prefix + "/")) for name in names)):
        raise CandidateError("ARCHIVE_LAYOUT_INVALID")
    return members


def _verify_export(repository: Path, revision: str, captured: bytes) -> None:
    # Git archive honors attribute sources outside the commit, including
    # .git/info/attributes. Check its actual files against the committed tree so
    # export-ignore/export-subst cannot silently change the recorded source.
    expected = {}
    for entry in _git(repository, "ls-tree", "-rz", "--full-tree", revision).split(b"\0"):
        if not entry:
            continue
        metadata, _, path = entry.partition(b"\t")
        mode, kind, object_id = metadata.split()
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            raise CandidateError("COMMITTED_SOURCE_TYPE_UNSUPPORTED")
        expected["source/" + os.fsdecode(path)] = (mode == b"100755", object_id.decode("ascii"))
    actual = set()
    with tarfile.open(fileobj=io.BytesIO(captured)) as archive:
        for member in _archive_members(archive, "source"):
            if member.isdir():
                continue
            if not member.isfile() or member.name not in expected:
                raise CandidateError("ARCHIVE_SOURCE_MISMATCH")
            stream = archive.extractfile(member)
            if stream is None:
                raise CandidateError("ARCHIVE_SOURCE_MISMATCH")
            data = stream.read()
            object_id = hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()
            if expected[member.name] != (bool(member.mode & 0o111), object_id):
                raise CandidateError("ARCHIVE_SOURCE_MISMATCH")
            actual.add(member.name)
    if actual != set(expected):
        raise CandidateError("ARCHIVE_SOURCE_MISMATCH")


def _extract(archive: tarfile.TarFile, destination: Path, prefix: str) -> None:
    _archive_members(archive, prefix)
    archive.extractall(destination, filter="data")


def _verify_source(source: Path, version: str, build_id: str) -> None:
    if (source / ".git").exists() or _source_version(source) != version:
        raise CandidateError("EXPORTED_SOURCE_INVALID")
    identity = _literal_assignment((source / _IDENTITY_PATH).read_text(encoding="utf-8"), "BUILD_ID")
    if identity != build_id:
        raise CandidateError("BUILD_ID_MISMATCH")


def _build(source: Path, dist: Path, kind: str, no_isolation: bool) -> None:
    command = [sys.executable, "-m", "build", "--" + kind, "--outdir", str(dist)]
    if no_isolation:
        command.append("--no-isolation")
    subprocess.run(command, cwd=source, env=_environment(), stdin=subprocess.DEVNULL, check=True)


def _verify_wheel(wheel: Path, version: str, build_id: str) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise CandidateError("WHEEL_LAYOUT_INVALID")
        identity = _literal_assignment(
            archive.read(f"{_PACKAGE}/_build_info.py").decode("utf-8"), "BUILD_ID")
        if identity != build_id:
            raise CandidateError("BUILD_ID_MISMATCH")
        embedded_version = _literal_assignment(
            archive.read(f"{_PACKAGE}/__init__.py").decode("utf-8"), "__version__")
        metadata = BytesParser().parsebytes(archive.read(f"{_PACKAGE}-{version}.dist-info/METADATA"))
        if embedded_version != version or metadata["Version"] != version:
            raise CandidateError("WHEEL_VERSION_MISMATCH")
        if metadata["Name"] != "evaluation-closure-toolkit":
            raise CandidateError("PACKAGE_NAME_MISMATCH")


def build_candidate(repository: Path, revision: str, output: Path, *, no_isolation: bool = False) -> dict:
    """Build artifacts without mutating or importing the source checkout."""
    repository = repository.resolve()
    output, version = _preflight(repository, revision, output)
    build_id = f"ect-{version}+git.{revision}"
    captured = _git(repository, "archive", "--format=tar", "--prefix=source/", revision)
    _verify_export(repository, revision, captured)
    output.mkdir()  # Exclusive: a concurrent existing destination is never reused.
    with tarfile.open(fileobj=io.BytesIO(captured)) as archive:
        _extract(archive, output, "source")
    source = output / "source"
    if _source_version(source) != version:
        raise CandidateError("VERSION_MISMATCH")
    (source / _IDENTITY_PATH).write_text(
        '"""Build identity stamped into this exported source during candidate packaging."""\n\n'
        + f"BUILD_ID = {build_id!r}\n", encoding="utf-8", newline="\n")
    _verify_source(source, version, build_id)
    dist = output / "dist"
    dist.mkdir()
    _build(source, dist, "sdist", no_isolation)
    prefix = f"{_PACKAGE}-{version}"
    sdist = dist / (prefix + ".tar.gz")
    if set(dist.iterdir()) != {sdist} or not sdist.is_file():
        raise CandidateError("SDIST_ARTIFACT_MISMATCH")
    extracted = output / "from-sdist"
    extracted.mkdir()
    with tarfile.open(sdist) as archive:
        _extract(archive, extracted, prefix)
    wheel_source = extracted / prefix
    _verify_source(wheel_source, version, build_id)
    _build(wheel_source, dist, "wheel", no_isolation)
    wheel = dist / (prefix + "-py3-none-any.whl")
    if set(dist.iterdir()) != {sdist, wheel} or not wheel.is_file():
        raise CandidateError("WHEEL_ARTIFACT_MISMATCH")
    _verify_wheel(wheel, version, build_id)
    manifest = {
        "version": version, "source_revision": revision, "build_id": build_id,
        "artifacts": [{"filename": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                       "size_bytes": path.stat().st_size} for path in (sdist, wheel)],
    }
    with (output / "artifacts.json").open("x", encoding="utf-8", newline="\n") as target:
        target.write(json.dumps(manifest, ensure_ascii=True, sort_keys=True, indent=2) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True, help="Exact clean checkout HEAD, as 40 lowercase hex digits.")
    parser.add_argument("--output", required=True, type=Path, help="New directory outside the checkout; its parent must exist.")
    parser.add_argument("--no-isolation", action="store_true", help="Use already-installed build requirements, without isolated dependency installation.")
    args = parser.parse_args()
    try:
        manifest = build_candidate(Path(__file__).resolve().parents[1], args.revision,
                                   args.output, no_isolation=args.no_isolation)
    except (CandidateError, OSError, ValueError, SyntaxError, KeyError,
            subprocess.CalledProcessError, tarfile.TarError, zipfile.BadZipFile) as error:
        detail = str(error) if isinstance(error, CandidateError) else type(error).__name__
        print(f"build-candidate: {detail}; no successful artifact manifest was created", file=sys.stderr)
        return 1
    print("Candidate build identity: " + manifest["build_id"])
    for artifact in manifest["artifacts"]:
        print(f"{artifact['filename']} SHA-256 {artifact['sha256']}")
    print("Artifact manifest: " + str(args.output.resolve() / "artifacts.json"))
    print("No tag, release or package publication was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
