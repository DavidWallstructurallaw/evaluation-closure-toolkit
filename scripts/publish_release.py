"""Publish the owner-authorized 0.1.0 artifacts after exact-source qualification.

This maintainer-only network client is outside the installed toolkit. It accepts
only the marked main-branch Actions run in this repository, never overwrites a
tag/release/asset, and leaves any newly created failed draft for owner review.
Use --check-only for offline artifact validation without publishing anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener


REPOSITORY = "DavidWallstructurallaw/evaluation-closure-toolkit"
VERSION = "0.1.0"
TAG = "v" + VERSION
MARKER = "[publish-v0.1.0]"
_FILES = ("evaluation_closure_toolkit-0.1.0.tar.gz",
          "evaluation_closure_toolkit-0.1.0-py3-none-any.whl")
_REVISION = re.compile(r"[0-9a-f]{40}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class ReleaseError(RuntimeError):
    """Publication precondition failed; existing remote objects stay untouched."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        # Never forward an authorization header to a redirect target.
        return None


class GitHub:
    def __init__(self, token: str):
        self._token = token
        self._opener = build_opener(_NoRedirect())

    def request(self, method: str, path: str, *, data=None, missing_ok=False):
        url = "https://api.github.com/repos/" + REPOSITORY + path
        raw = None if data is None else json.dumps(data).encode("utf-8")
        return self._request(method, url, raw, "application/json", missing_ok)

    def upload(self, release_id: int, name: str, data: bytes):
        url = (f"https://uploads.github.com/repos/{REPOSITORY}/releases/"
               f"{release_id}/assets?name={quote(name, safe='')}")
        return self._request("POST", url, data, "application/octet-stream", False)

    def _request(self, method, url, data, content_type, missing_ok):
        request = Request(url, data=data, method=method, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + self._token,
            "X-GitHub-Api-Version": "2026-03-10",
            "Content-Type": content_type,
            "User-Agent": "evaluation-closure-toolkit-release/0.1.0",
        })
        try:
            with self._opener.open(request, timeout=45) as response:
                return json.loads(response.read())
        except HTTPError as error:
            if method == "GET" and missing_ok and error.code == 404:
                return None
            # Response bodies and credentials are deliberately never logged.
            raise ReleaseError(f"GITHUB_{method}_HTTP_{error.code}") from None
        except (URLError, TimeoutError):
            raise ReleaseError("GITHUB_TRANSPORT_FAILED") from None


def _read_regular(path: Path, maximum: int) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ReleaseError("ARTIFACT_FILE_INVALID")
    data = path.read_bytes()
    if len(data) > maximum:
        raise ReleaseError("ARTIFACT_FILE_INVALID")
    return data


def load_artifacts(directory: Path, revision: str) -> dict[str, bytes]:
    """Snapshot and verify exactly the two qualified assets and their manifest."""
    if not _REVISION.fullmatch(revision):
        raise ReleaseError("REVISION_INVALID")
    if directory.is_symlink() or (directory / "dist").is_symlink():
        raise ReleaseError("ARTIFACT_DIRECTORY_INVALID")
    manifest_bytes = _read_regular(directory / "artifacts.json", 1024 * 1024)
    manifest = json.loads(manifest_bytes)
    if (type(manifest) is not dict
            or set(manifest) != {"version", "source_revision", "build_id", "artifacts"}
            or manifest.get("version") != VERSION
            or manifest.get("source_revision") != revision
            or manifest.get("build_id") != f"ect-{VERSION}+git.{revision}"):
        raise ReleaseError("MANIFEST_IDENTITY_MISMATCH")
    entries = manifest["artifacts"]
    if type(entries) is not list or len(entries) != 2:
        raise ReleaseError("MANIFEST_ARTIFACTS_INVALID")
    assets = {}
    for entry in entries:
        if (type(entry) is not dict or set(entry) != {"filename", "size_bytes", "sha256"}
                or entry.get("filename") not in _FILES or entry["filename"] in assets
                or type(entry.get("size_bytes")) is not int or entry["size_bytes"] <= 0
                or type(entry.get("sha256")) is not str or not _DIGEST.fullmatch(entry["sha256"])):
            raise ReleaseError("MANIFEST_ARTIFACTS_INVALID")
        name = entry["filename"]
        data = _read_regular(directory / "dist" / name, 64 * 1024 * 1024)
        if len(data) != entry["size_bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ReleaseError("ARTIFACT_HASH_OR_SIZE_MISMATCH")
        assets[name] = data
    if set(assets) != set(_FILES) or set(path.name for path in (directory / "dist").iterdir()) != set(_FILES):
        raise ReleaseError("ARTIFACT_SET_MISMATCH")
    assets["artifacts.json"] = manifest_bytes
    assets["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(assets.items())
    ).encode("ascii")
    return assets


def require_actions_context(environment: dict[str, str], revision: str) -> str:
    expected = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "push",
                "GITHUB_REF": "refs/heads/main", "GITHUB_REPOSITORY": REPOSITORY,
                "GITHUB_SHA": revision}
    if any(environment.get(key) != value for key, value in expected.items()):
        raise ReleaseError("AUTHORIZED_ACTIONS_CONTEXT_REQUIRED")
    run_id = environment.get("GITHUB_RUN_ID", "")
    if not re.fullmatch(r"[1-9][0-9]*", run_id):
        raise ReleaseError("RUN_ID_INVALID")
    event = json.loads(Path(environment["GITHUB_EVENT_PATH"]).read_bytes())
    if (event.get("after") != revision or event.get("ref") != "refs/heads/main"
            or MARKER not in event.get("head_commit", {}).get("message", "")):
        raise ReleaseError("OWNER_PUBLICATION_MARKER_REQUIRED")
    if not environment.get("GITHUB_TOKEN"):
        raise ReleaseError("CONFIGURED_GITHUB_TOKEN_REQUIRED")
    return run_id


def _require_main(api: GitHub, revision: str) -> None:
    if api.request("GET", "").get("default_branch") != "main":
        raise ReleaseError("DEFAULT_BRANCH_CHANGED")
    head = api.request("GET", "/git/ref/heads/main").get("object", {})
    if head.get("type") != "commit" or head.get("sha") != revision:
        raise ReleaseError("MAIN_HEAD_CHANGED")


def _check_tag(api: GitHub, revision: str, *, required=False) -> None:
    tag = api.request("GET", "/git/ref/tags/" + TAG, missing_ok=True)
    if tag is None and not required:
        return
    if tag is None or tag.get("object", {}).get("type") != "commit" or tag["object"].get("sha") != revision:
        raise ReleaseError("TAG_TARGET_MISMATCH")


def _asset_matches(asset: dict, name: str, data: bytes) -> bool:
    return (asset.get("name") == name and asset.get("state") == "uploaded"
            and asset.get("size") == len(data)
            and asset.get("digest") == "sha256:" + hashlib.sha256(data).hexdigest())


def publish(api: GitHub, assets: dict[str, bytes], revision: str, notes: str, run_id: str) -> str:
    """Create a new draft, verify every uploaded asset, then publish once."""
    _require_main(api, revision)
    _check_tag(api, revision)
    # The by-tag endpoint only guarantees published releases. List drafts too.
    for page in range(1, 101):
        releases = api.request("GET", f"/releases?per_page=100&page={page}")
        if any(release.get("tag_name") == TAG for release in releases):
            raise ReleaseError("EXISTING_RELEASE_REQUIRES_OWNER_REVIEW")
        if len(releases) < 100:
            break
    else:
        raise ReleaseError("RELEASE_LIST_LIMIT")
    provenance = (f"\n\n## Qualified source and artifacts\n\n"
                  f"Source commit: `{revision}`\n\n"
                  f"Build identity: `ect-{VERSION}+git.{revision}`\n\n"
                  f"[Four-cell qualification run](https://github.com/{REPOSITORY}/actions/runs/{run_id}). "
                  "Published distribution bytes are the qualified Ubuntu 22.04 / CPython 3.12 artifacts from this run. "
                  "See `artifacts.json` and `SHA256SUMS` for exact sizes and SHA-256 hashes.\n")
    release = api.request("POST", "/releases", data={
        "tag_name": TAG, "target_commitish": revision,
        "name": "Evaluation Closure Toolkit " + VERSION,
        "body": notes.rstrip() + provenance, "draft": True, "prerelease": False,
    })
    release_id = release.get("id")
    if (type(release_id) is not int or release_id <= 0 or release.get("draft") is not True
            or release.get("tag_name") != TAG or release.get("target_commitish") != revision
            or release.get("upload_url") != f"https://uploads.github.com/repos/{REPOSITORY}/releases/{release_id}/assets{{?name,label}}"):
        raise ReleaseError("DRAFT_RESPONSE_INVALID")
    for name, data in sorted(assets.items()):
        if not _asset_matches(api.upload(release_id, name, data), name, data):
            raise ReleaseError("UPLOADED_ASSET_MISMATCH")
    remote_assets = api.request("GET", f"/releases/{release_id}/assets?per_page=100")
    if (len(remote_assets) != len(assets)
            or {asset.get("name") for asset in remote_assets} != set(assets)
            or any(not _asset_matches(asset, asset["name"], assets[asset["name"]]) for asset in remote_assets)):
        raise ReleaseError("REMOTE_ASSET_SET_MISMATCH")
    _require_main(api, revision)
    _check_tag(api, revision)
    result = api.request("PATCH", f"/releases/{release_id}", data={
        "draft": False, "prerelease": False, "make_latest": "true",
    })
    if result.get("draft") is not False or result.get("prerelease") is not False or result.get("tag_name") != TAG:
        raise ReleaseError("PUBLISHED_RELEASE_RESPONSE_INVALID")
    _check_tag(api, revision, required=True)
    return f"https://github.com/{REPOSITORY}/releases/tag/{TAG}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-directory", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--notes", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        assets = load_artifacts(args.artifact_directory, args.revision)
        if args.check_only:
            print("Release artifact identity, names, sizes and SHA-256 hashes verified; no publication.")
            return 0
        if args.notes is None:
            raise ReleaseError("RELEASE_NOTES_REQUIRED")
        notes = args.notes.read_text(encoding="utf-8")
        if not notes.strip():
            raise ReleaseError("RELEASE_NOTES_EMPTY")
        run_id = require_actions_context(os.environ, args.revision)
        url = publish(GitHub(os.environ["GITHUB_TOKEN"]), assets, args.revision, notes, run_id)
    except (ReleaseError, OSError, ValueError, KeyError, TypeError) as error:
        detail = str(error) if isinstance(error, ReleaseError) else type(error).__name__
        print("publish-release: " + detail + "; no existing tag, release or asset was overwritten. "
              "A newly created draft may need owner review before retrying.", file=sys.stderr)
        return 1
    print("Published " + url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
