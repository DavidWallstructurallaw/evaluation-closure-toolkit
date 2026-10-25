"""Offline source/export/identity checks for the maintainer build script."""

import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile


_SPEC = importlib.util.spec_from_file_location(
    "ect_candidate_builder", Path(__file__).resolve().parents[1] / "scripts" / "build_candidate.py")
builder = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(builder)


@unittest.skipUnless(shutil.which("git"), "Candidate packaging requires Git")
class CandidateBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ect-candidate-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.repository, self.revision = self.make_repository("repository")
        self.output = self.root / "candidate"

    def git(self, repository, *arguments):
        return subprocess.check_output(
            ["git", "-C", str(repository), *arguments], stderr=subprocess.PIPE,
            env=builder._environment()).decode("utf-8").strip()

    def make_repository(self, name, version="0.1.0rc1", embedded_version=None, identity="unknown"):
        repository = self.root / name
        repository.mkdir()
        self.git(repository, "init", "--quiet")
        self.git(repository, "config", "user.name", "Candidate Test")
        self.git(repository, "config", "user.email", "candidate-test@example.invalid")
        self.git(repository, "config", "core.autocrlf", "false")
        package = repository / "src" / "evaluation_closure_toolkit"
        package.mkdir(parents=True)
        (repository / "pyproject.toml").write_text(
            f'[project]\nname = "evaluation-closure-toolkit"\nversion = "{version}"\n',
            encoding="utf-8", newline="\n")
        (package / "__init__.py").write_text(
            f'__version__ = "{embedded_version or version}"\n', encoding="utf-8", newline="\n")
        (package / "_build_info.py").write_text(
            f'BUILD_ID = "{identity}"\n', encoding="utf-8", newline="\n")
        self.git(repository, "add", ".")
        self.git(repository, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Synthetic candidate source")
        return repository, self.git(repository, "rev-parse", "HEAD")

    def fake_build(self, source, dist, kind, no_isolation, *, tamper=None):
        version = builder._source_version(source)
        prefix = f"evaluation_closure_toolkit-{version}"
        if kind == "sdist":
            with tarfile.open(dist / (prefix + ".tar.gz"), "w:gz") as archive:
                for path in sorted(source.rglob("*")):
                    if not path.is_file():
                        continue
                    relative = path.relative_to(source).as_posix()
                    data = path.read_bytes()
                    if tamper == "sdist" and relative.endswith("/_build_info.py"):
                        data = b'BUILD_ID = "unknown"\n'
                    info = tarfile.TarInfo(prefix + "/" + relative)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
        else:
            package = source / "src" / "evaluation_closure_toolkit"
            with zipfile.ZipFile(dist / (prefix + "-py3-none-any.whl"), "w") as archive:
                for name in ("__init__.py", "_build_info.py"):
                    data = (package / name).read_bytes()
                    if tamper == "wheel" and name == "_build_info.py":
                        data = b'BUILD_ID = "unknown"\n'
                    archive.writestr("evaluation_closure_toolkit/" + name, data)
                archive.writestr(prefix + ".dist-info/METADATA",
                                 f"Name: evaluation-closure-toolkit\nVersion: {version}\n")

    def test_clean_commit_is_stamped_only_in_export_and_preserved_through_sdist(self):
        before = (self.repository / builder._IDENTITY_PATH).read_bytes()
        with patch.object(builder, "_build", side_effect=self.fake_build) as build:
            manifest = builder.build_candidate(self.repository, self.revision, self.output, no_isolation=True)
        expected = f"ect-0.1.0rc1+git.{self.revision}"
        self.assertEqual(manifest["build_id"], expected)
        self.assertEqual(manifest["source_revision"], self.revision)
        self.assertEqual(manifest["version"], "0.1.0rc1")
        self.assertEqual((self.repository / builder._IDENTITY_PATH).read_bytes(), before)
        self.assertEqual(self.git(self.repository, "status", "--porcelain=v1"), "")
        self.assertEqual([call.args[2] for call in build.call_args_list], ["sdist", "wheel"])
        self.assertTrue(all(call.args[3] for call in build.call_args_list))
        self.assertEqual(build.call_args_list[1].args[0],
                         self.output / "from-sdist" / "evaluation_closure_toolkit-0.1.0rc1")
        self.assertFalse((build.call_args_list[1].args[0] / ".git").exists())
        self.assertEqual(json.loads((self.output / "artifacts.json").read_bytes()), manifest)
        self.assertEqual(len(manifest["artifacts"]), 2)
        for artifact in manifest["artifacts"]:
            data = (self.output / "dist" / artifact["filename"]).read_bytes()
            self.assertEqual(artifact["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(artifact["size_bytes"], len(data))

    def test_malformed_or_wrong_revision_does_not_create_output(self):
        for revision, reason in (("main", "REVISION_INVALID"), ("A" * 40, "REVISION_INVALID"),
                                 ("a" * 39, "REVISION_INVALID"), ("0" * 40, "HEAD_MISMATCH")):
            with self.subTest(revision=revision):
                with self.assertRaisesRegex(builder.CandidateError, reason):
                    builder.build_candidate(self.repository, revision, self.output)
                self.assertFalse(self.output.exists())

    def test_tracked_staged_and_untracked_changes_block_export(self):
        for change in ("tracked", "staged", "untracked"):
            with self.subTest(change=change):
                repository, revision = self.make_repository("dirty-" + change)
                path = repository / ("unexpected-candidate-file.py" if change == "untracked" else builder._INIT_PATH)
                with path.open("a", encoding="utf-8", newline="\n") as target:
                    target.write("# An uncommitted source change.\n")
                if change == "staged":
                    self.git(repository, "add", ".")
                with self.assertRaisesRegex(builder.CandidateError, "SOURCE_DIRTY"):
                    builder.build_candidate(repository, revision, self.output)
                self.assertFalse(self.output.exists())

    def test_existing_destination_and_checkout_destination_are_refused(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_text("existing artifact", encoding="utf-8")
        with self.assertRaisesRegex(builder.CandidateError, "OUTPUT_EXISTS"):
            builder.build_candidate(self.repository, self.revision, self.output)
        self.assertEqual(marker.read_text(encoding="utf-8"), "existing artifact")
        with self.assertRaisesRegex(builder.CandidateError, "OUTPUT_IN_CHECKOUT"):
            builder.build_candidate(self.repository, self.revision, self.repository / "new-candidate")
        self.assertFalse((self.repository / "new-candidate").exists())

    def test_version_and_source_identity_preconditions_precede_output_creation(self):
        for name, options, reason in (
            ("version-mismatch", {"embedded_version": "0.1.0"}, "VERSION_MISMATCH"),
            ("development-version", {"version": "0.1.0.dev5"}, "VERSION_UNSUPPORTED"),
            ("pre-stamped", {"identity": "ect-0.1.0rc1+git." + "f" * 40}, "SOURCE_BUILD_ID_NOT_UNKNOWN"),
        ):
            with self.subTest(case=name):
                repository, revision = self.make_repository(name, **options)
                with self.assertRaisesRegex(builder.CandidateError, reason):
                    builder.build_candidate(repository, revision, self.output)
                self.assertFalse(self.output.exists())

    def test_sdist_or_wheel_identity_loss_never_produces_success_manifest(self):
        for changed in ("sdist", "wheel"):
            with self.subTest(artifact=changed):
                output = self.root / ("bad-" + changed)
                def fake(*args):
                    return self.fake_build(*args, tamper=changed)
                with patch.object(builder, "_build", side_effect=fake):
                    with self.assertRaisesRegex(builder.CandidateError, "BUILD_ID_MISMATCH"):
                        builder.build_candidate(self.repository, self.revision, output)
                self.assertFalse((output / "artifacts.json").exists())
        self.assertEqual(self.git(self.repository, "status", "--porcelain=v1"), "")

    def test_unsafe_archive_layout_is_rejected_without_extracting(self):
        for name in ("../outside.txt", "source/../outside.txt", "source/..\\outside.txt"):
            with self.subTest(name=name):
                data = io.BytesIO()
                with tarfile.open(fileobj=data, mode="w") as archive:
                    info = tarfile.TarInfo(name)
                    info.size = 1
                    archive.addfile(info, io.BytesIO(b"x"))
                data.seek(0)
                with tarfile.open(fileobj=data) as archive:
                    with self.assertRaisesRegex(builder.CandidateError, "ARCHIVE_LAYOUT_INVALID"):
                        builder._extract(archive, self.root / "extract", "source")
        self.assertFalse((self.root / "outside.txt").exists())

    def test_external_info_attributes_cannot_omit_committed_source(self):
        extra = self.repository / "extra.py"
        extra.write_text("CAPTURED = True\n", encoding="utf-8", newline="\n")
        self.git(self.repository, "add", ".")
        self.git(self.repository, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Captured module")
        revision = self.git(self.repository, "rev-parse", "HEAD")
        (self.repository / ".git" / "info" / "attributes").write_text(
            "extra.py export-ignore\n", encoding="utf-8", newline="\n")
        self.assertEqual(self.git(self.repository, "status", "--porcelain=v1"), "")
        with self.assertRaisesRegex(builder.CandidateError, "ARCHIVE_SOURCE_MISMATCH"):
            builder.build_candidate(self.repository, revision, self.output)
        self.assertFalse(self.output.exists())

    def test_external_global_attributes_cannot_substitute_committed_bytes(self):
        extra = self.repository / "extra.py"
        extra.write_text("REVISION = '$Format:%H$'\n", encoding="utf-8", newline="\n")
        self.git(self.repository, "add", ".")
        self.git(self.repository, "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Literal source bytes")
        revision = self.git(self.repository, "rev-parse", "HEAD")
        attributes = self.root / "global-attributes"
        attributes.write_text("extra.py export-subst\n", encoding="utf-8", newline="\n")
        self.git(self.repository, "config", "core.attributesFile", str(attributes))
        self.assertEqual(self.git(self.repository, "status", "--porcelain=v1"), "")
        with self.assertRaisesRegex(builder.CandidateError, "ARCHIVE_SOURCE_MISMATCH"):
            builder.build_candidate(self.repository, revision, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
