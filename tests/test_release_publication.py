"""Offline publication validation and fail-closed API sequencing checks."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


_SPEC = importlib.util.spec_from_file_location(
    "ect_release_publisher", Path(__file__).resolve().parents[1] / "scripts" / "publish_release.py")
publisher = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(publisher)
REVISION = "a" * 40


class FakeGitHub:
    def __init__(self):
        self.calls = []
        self.assets = []
        self.releases = []
        self.tag = None
        self.main = REVISION
        self.main_reads = 0
        self.move_before_publish = False
        self.bad_upload = False
        self.extra_asset = False
        self.draft = None

    def request(self, method, path, *, data=None, missing_ok=False):
        self.calls.append((method, path, copy.deepcopy(data)))
        if method == "GET" and path == "":
            return {"default_branch": "main"}
        if method == "GET" and path == "/git/ref/heads/main":
            self.main_reads += 1
            head = "b" * 40 if self.move_before_publish and self.main_reads > 1 else self.main
            return {"object": {"type": "commit", "sha": head}}
        if method == "GET" and path == "/git/ref/tags/v0.1.0":
            return self.tag
        if method == "GET" and path == "/releases?per_page=100&page=1":
            return self.releases
        if method == "POST" and path == "/releases":
            self.draft = dict(data, id=11, upload_url=(
                f"https://uploads.github.com/repos/{publisher.REPOSITORY}/releases/11/assets{{?name,label}}"))
            return self.draft
        if method == "GET" and path == "/releases/11/assets?per_page=100":
            return self.assets + ([dict(self.assets[0])] if self.extra_asset else [])
        if method == "PATCH" and path == "/releases/11":
            self.tag = {"object": {"type": "commit", "sha": REVISION}}
            return {"draft": False, "prerelease": False, "tag_name": publisher.TAG}
        raise AssertionError((method, path, data))

    def upload(self, release_id, name, data):
        self.calls.append(("UPLOAD", name, None))
        asset = {"name": name, "state": "uploaded", "size": len(data),
                 "digest": "sha256:" + hashlib.sha256(data).hexdigest()}
        if self.bad_upload:
            asset["digest"] = "sha256:" + "0" * 64
        self.assets.append(asset)
        return asset


class ReleasePublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="ect-release-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "dist").mkdir()
        self.manifest = {"version": "0.1.0", "source_revision": REVISION,
                         "build_id": f"ect-0.1.0+git.{REVISION}", "artifacts": []}
        for index, name in enumerate(publisher._FILES):
            data = f"synthetic artifact {index}".encode()
            (self.root / "dist" / name).write_bytes(data)
            self.manifest["artifacts"].append({"filename": name, "size_bytes": len(data),
                                               "sha256": hashlib.sha256(data).hexdigest()})
        self.write_manifest()

    def write_manifest(self):
        (self.root / "artifacts.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def assets(self):
        return publisher.load_artifacts(self.root, REVISION)

    def assert_no_publication(self, api):
        self.assertFalse(any(call[0] == "PATCH" for call in api.calls))

    def test_offline_asset_snapshot_and_checksums(self):
        assets = self.assets()
        self.assertEqual(set(assets), {*publisher._FILES, "artifacts.json", "SHA256SUMS"})
        for line in assets["SHA256SUMS"].decode().splitlines():
            digest, name = line.split("  ")
            self.assertEqual(digest, hashlib.sha256(assets[name]).hexdigest())
        self.assertEqual(assets["artifacts.json"], (self.root / "artifacts.json").read_bytes())

    def test_manifest_identity_changes_are_refused(self):
        original = copy.deepcopy(self.manifest)
        for field, value in (("version", "0.1.0rc1"), ("source_revision", "b" * 40),
                             ("build_id", "unknown")):
            with self.subTest(field=field):
                self.manifest = dict(original, **{field: value})
                self.write_manifest()
                with self.assertRaisesRegex(publisher.ReleaseError, "MANIFEST_IDENTITY_MISMATCH"):
                    self.assets()
        with self.assertRaisesRegex(publisher.ReleaseError, "REVISION_INVALID"):
            publisher.load_artifacts(self.root, "main")

    def test_artifact_tampering_and_unexpected_files_are_refused(self):
        path = self.root / "dist" / publisher._FILES[0]
        original = path.read_bytes()
        path.write_bytes(original + b"tampered")
        with self.assertRaisesRegex(publisher.ReleaseError, "ARTIFACT_HASH_OR_SIZE_MISMATCH"):
            self.assets()
        path.write_bytes(original)
        (self.root / "dist" / "unexpected.txt").write_bytes(b"extra")
        with self.assertRaisesRegex(publisher.ReleaseError, "ARTIFACT_SET_MISMATCH"):
            self.assets()

    def test_duplicate_path_escape_and_invalid_manifest_entries_are_refused(self):
        original = copy.deepcopy(self.manifest)
        for key, value in (("filename", "../private.txt"), ("filename", publisher._FILES[1]),
                           ("size_bytes", True), ("size_bytes", 0), ("sha256", "bad")):
            with self.subTest(key=key, value=value):
                self.manifest = copy.deepcopy(original)
                self.manifest["artifacts"][0][key] = value
                self.write_manifest()
                with self.assertRaises(publisher.ReleaseError):
                    self.assets()

    def test_nonregular_artifacts_and_symlink_metadata_are_refused(self):
        with patch.object(Path, "is_symlink", return_value=True):
            with self.assertRaisesRegex(publisher.ReleaseError, "ARTIFACT_DIRECTORY_INVALID"):
                self.assets()
        with self.assertRaisesRegex(publisher.ReleaseError, "ARTIFACT_FILE_INVALID"):
            publisher._read_regular(self.root / "dist", 100)

    def test_only_authorized_exact_main_actions_context_can_publish(self):
        event_path = self.root / "event.json"
        event = {"after": REVISION, "ref": "refs/heads/main",
                 "head_commit": {"message": "Release " + publisher.MARKER}}
        event_path.write_text(json.dumps(event), encoding="utf-8")
        context = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "push",
                   "GITHUB_REF": "refs/heads/main", "GITHUB_REPOSITORY": publisher.REPOSITORY,
                   "GITHUB_SHA": REVISION, "GITHUB_RUN_ID": "12345",
                   "GITHUB_EVENT_PATH": str(event_path), "GITHUB_TOKEN": "synthetic-test-token"}
        self.assertEqual(publisher.require_actions_context(context, REVISION), "12345")
        for key in ("GITHUB_EVENT_NAME", "GITHUB_REF", "GITHUB_REPOSITORY", "GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_TOKEN"):
            with self.subTest(key=key), self.assertRaises(publisher.ReleaseError):
                publisher.require_actions_context(dict(context, **{key: ""}), REVISION)
        event["head_commit"]["message"] = "Ordinary main update"
        event_path.write_text(json.dumps(event), encoding="utf-8")
        with self.assertRaisesRegex(publisher.ReleaseError, "OWNER_PUBLICATION_MARKER_REQUIRED"):
            publisher.require_actions_context(context, REVISION)

    def test_new_release_is_draft_until_all_four_assets_verified(self):
        api = FakeGitHub()
        url = publisher.publish(api, self.assets(), REVISION, "Scoped release notes.", "12345")
        self.assertEqual(url, f"https://github.com/{publisher.REPOSITORY}/releases/tag/v0.1.0")
        create = next(call for call in api.calls if call[:2] == ("POST", "/releases"))
        self.assertTrue(create[2]["draft"])
        self.assertFalse(create[2]["prerelease"])
        self.assertEqual(create[2]["target_commitish"], REVISION)
        self.assertIn("actions/runs/12345", create[2]["body"])
        self.assertEqual(len([call for call in api.calls if call[0] == "UPLOAD"]), 4)
        publish_index = next(index for index, call in enumerate(api.calls) if call[0] == "PATCH")
        self.assertTrue(all(index < publish_index for index, call in enumerate(api.calls) if call[0] == "UPLOAD"))
        self.assertEqual(api.main_reads, 2)

    def test_existing_draft_or_published_release_is_never_modified(self):
        for draft in (True, False):
            with self.subTest(draft=draft):
                api = FakeGitHub()
                api.releases = [{"tag_name": publisher.TAG, "draft": draft}]
                with self.assertRaisesRegex(publisher.ReleaseError, "EXISTING_RELEASE_REQUIRES_OWNER_REVIEW"):
                    publisher.publish(api, self.assets(), REVISION, "Notes", "12345")
                self.assertTrue(all(call[0] == "GET" for call in api.calls))

    def test_mismatched_tag_or_moved_main_blocks_before_writes(self):
        for condition in ("tag", "main"):
            with self.subTest(condition=condition):
                api = FakeGitHub()
                if condition == "tag":
                    api.tag = {"object": {"type": "commit", "sha": "b" * 40}}
                else:
                    api.main = "b" * 40
                with self.assertRaises(publisher.ReleaseError):
                    publisher.publish(api, self.assets(), REVISION, "Notes", "12345")
                self.assertTrue(all(call[0] == "GET" for call in api.calls))

    def test_upload_or_asset_set_failure_leaves_new_draft_unpublished(self):
        for option in ("bad_upload", "extra_asset", "move_before_publish"):
            with self.subTest(option=option):
                api = FakeGitHub()
                setattr(api, option, True)
                with self.assertRaises(publisher.ReleaseError):
                    publisher.publish(api, self.assets(), REVISION, "Notes", "12345")
                self.assertIsNotNone(api.draft)
                self.assert_no_publication(api)
                self.assertFalse(any(call[0] == "DELETE" for call in api.calls))

    def test_permission_failures_and_redirects_are_not_retried_or_exposed(self):
        api = publisher.GitHub("synthetic-secret-never-log")
        for code in (302, 403, 404):
            with self.subTest(code=code), patch.object(api._opener, "open", side_effect=HTTPError(
                    "https://api.github.com/example", code, "private response", {}, None)) as request:
                with self.assertRaisesRegex(publisher.ReleaseError, f"GITHUB_POST_HTTP_{code}") as result:
                    api.request("POST", "/releases", data={})
                self.assertNotIn("private", str(result.exception))
                self.assertNotIn("synthetic-secret", str(result.exception))
                self.assertEqual(request.call_count, 1)
        self.assertIsNone(publisher._NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.invalid"))


if __name__ == "__main__":
    unittest.main()
