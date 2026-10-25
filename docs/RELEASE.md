# Exact-source qualification and release procedure

The current version is `0.1.0`. The owner authorized acceptance, dependency-ordered PR merges, documentation discoverability changes and the stable GitHub Release. P1-6 remains the historical `0.1.0rc1` qualification record; stable artifacts must qualify their own final source commit. Runtime behavior remains bounded by the supplied dossier, scope and `ect-core/0.1` policy. Package-index publication is outside this authorization and workflow.

## What the release includes

The first stable release implements admission plus seven operations: `lint`, `profile`, `compare`, `lineage`, `external`, `cases` and `assess`. It includes fourteen synthetic demos, the dossier schema, safe JSON/Markdown reports, the three byte-oriented public functions, and `validate`, `analyze` and `demo` commands. There are no third-party runtime dependencies. The engineering license is Apache-2.0; source papers and private evidence are not bundled.

Qualification covers 64-bit CPython 3.12 and 3.13 on Ubuntu 22.04 x64 and Windows Server 2022 x64. A target is qualified only when that exact source revision's checks actually pass there. Other platforms remain unqualified. The suite checks software contracts and synthetic cases. No real-data effectiveness pilot, evidence authentication, scientific certification or deployment authorization is claimed.

## Build from an exact clean commit

Maintainers need Git, a supported Python, and the `build` frontend. Install build tooling with `python -m pip install build`. The standard setuptools backend is unchanged. Isolated builds may obtain build dependencies from the configured package index; the installed toolkit and offline installation check do not use network access.

Commit the intended source first. Run `git rev-parse HEAD` and retain its full 40-character SHA independently. Replace the capitalized values below with that SHA and a new output path outside the checkout. The output's parent must already exist.

```sh
python scripts/build_candidate.py --revision SOURCE_COMMIT --output NEW_OUTSIDE_DIRECTORY
```

The script refuses a different HEAD, staged/unstaged changes, nonignored untracked files, inconsistent versions, an already stamped checkout, an existing destination or a destination inside the checkout. Ignored working-tree files cannot contaminate the export because only the named commit is archived. Archive paths, executable flags and file bytes are checked against the committed tree before stamping, so local Git attributes cannot silently omit or substitute source. This small builder supports committed regular files; symlinks and submodules require a separate packaging decision and are refused. It does not modify the repository.

The exported copy receives one static module constant:

```text
BUILD_ID = "ect-0.1.0+git.SOURCE_COMMIT"
```

The script builds an sdist, extracts that sdist into a separate directory without Git metadata, builds its wheel, and verifies the same identity in both artifacts. Source-checkout builds retain `BUILD_ID = "unknown"`. The runtime never invokes Git or reads environment variables to infer identity.

Output layout:

| Path under the new output directory | Purpose |
| --- | --- |
| `source/` | Exact committed export plus the generated static build identity |
| `from-sdist/evaluation_closure_toolkit-0.1.0/` | Source extracted from the built sdist |
| `dist/` | Qualified `.tar.gz` and `.whl` |
| `artifacts.json` | Source revision, version, build ID and actual artifact names, sizes and SHA-256 digests |

`--no-isolation` is available when all required build tooling is already installed. It changes dependency provisioning, not the source-identity rules. A failed build may leave its new output directory for inspection, but no success manifest is issued. Use another new destination after resolving the failure; existing outputs are never replaced.

## Verify the actual artifacts

From the source directory extracted from the sdist, install its wheel with `python -m pip install --no-index --no-deps PATH_TO_WHEEL`, then run:

```sh
python -m unittest discover -s tests -v
python scripts/generate_schema.py --check
python scripts/check_install.py --wheel PATH_TO_WHEEL --expected-build-id ect-0.1.0+git.SOURCE_COMMIT
```

Supply the expected revision from the intended commit, not by trusting whichever identity a wheel happens to report. `check_install.py` creates a fresh virtual environment outside the checkout and verifies that exact expected identity in admission and analysis. It also checks metadata/version, Apache license bytes, schema, zero runtime dependencies, all fourteen demos, both entry points, deterministic reruns, saved-report Markdown parity and the actual README, user-guide and reproducibility examples. Its default identity expectation is `unknown`, for an ordinary source build.

CI runs this process on the exact PR head for pull requests and on the actual merged commit for a push to `main`, in the four named x64 cells. Tests are loaded from the extracted source distribution against the installed package. Windows skips the two existing POSIX-only filesystem checks. Successful jobs retain their two distribution files and `artifacts.json` as workflow artifacts for 30 days. A qualified workflow artifact alone is not a published release. Download and retain it when needed; workflow retention is finite.

Artifact hashes identify the bytes of each particular build. They do not promise identical wheel/sdist bytes across build tools, timestamps or operating systems. Report determinism and cross-runtime normalized report equality have their separate contract in [REPRODUCIBILITY.md](REPRODUCIBILITY.md). A source label and an artifact manifest are not signed attestations and cannot authenticate the supplied evaluation evidence.

## Download verification

Obtain the attached wheel, sdist, `artifacts.json` and `SHA256SUMS` from the [0.1.0 release page](https://github.com/DavidWallstructurallaw/evaluation-closure-toolkit/releases/tag/v0.1.0). Retain the full source SHA from the release's qualification record and verify that tag `v0.1.0` resolves to that same SHA. For each distribution, compare its byte size and SHA-256 with its `artifacts.json` entry. The manifest's version must be `0.1.0`, `source_revision` must equal that independently expected SHA, and `build_id` must be `ect-0.1.0+git.` followed by that SHA. `SHA256SUMS` also includes the manifest's digest; on systems providing `sha256sum`, run `sha256sum -c SHA256SUMS` with all three files in the same directory.

GitHub's automatic source ZIP/tar archives contain the un-stamped committed checkout. They differ from the attached qualified sdist; do not substitute them when verifying the release build identity. A matching unsigned manifest establishes consistency of the downloaded bytes with that manifest, without supplying an independent trust root.

## Owner acceptance and stable publication

Review the exact release PR and its four-cell results, the limits in the [user guide](USER_GUIDE.md), and any unresolved failures. A missing platform result remains a blocker for claiming that platform. Tests passing alone do not authorize publication.

For this authorized `0.1.0` release:

1. Merge the reviewed PR stack in dependency order, preserving the accepted contract and source history. PRs #1 through #6 have been merged in that order.
2. Review the separate stable preparation PR containing version `0.1.0`, current documentation, package metadata and guarded publication. Qualify that PR head in all four target cells.
3. Merge the accepted stable PR with the explicit `[publish-v0.1.0]` marker in its merge commit message. This is the deliberate publication gate. A changed or merged revision does not inherit the candidate's exact-source qualification automatically.
4. The resulting push to `main` rebuilds and qualifies the final clean commit in all four cells. The release job runs only after they all succeed. It consumes the Ubuntu 22.04 / CPython 3.12 artifacts from that same run, without rebuilding them.
5. The publisher checks the exact source revision, stable version, build ID, filenames, sizes and hashes, and requires the expected commit still to be `main` HEAD. It creates a draft GitHub Release targeting that qualified SHA, uploads the two distributions, `artifacts.json` and `SHA256SUMS`, verifies the uploaded hashes and sizes, then publishes. Tag `v0.1.0` must resolve to the exact qualified SHA. The release notes include the source identity and qualification run.

Only the publication job requests repository contents write permission through the standard Actions token. PR verification remains read-only. A conflicting existing tag/release, moved `main`, failed qualification or permission error must stop publication; it does not authorize overwrites, forced tags, branch-protection changes or alternate credentials. Inspect any incomplete draft before retrying. Historical candidate build records remain unchanged. Future releases need their own version, review and publication authorization.

The GitHub Release is the distribution channel for `0.1.0`. PyPI publication requires its own configured workflow and authorization and is not performed here. For the release contents and limits, see [0.1.0 release notes](releases/0.1.0.md).

Do not add capture archives, a replay command, simulation, live collection or adapters as implied release work. Those features remain outside v0.1. A future licensed real-data pilot may support additional empirical claims only to the extent its evidence warrants.
