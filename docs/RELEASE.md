# Candidate qualification and release procedure

The current version is `0.1.0rc1`. P1-6 prepares and tests this candidate; it does not merge the PR stack, create a tag, publish a GitHub Release or upload a package to an index. Those actions require owner approval. Runtime behavior remains bounded by the supplied dossier, scope and `ect-core/0.1` policy.

## What the candidate includes

The first candidate implements admission plus seven operations: `lint`, `profile`, `compare`, `lineage`, `external`, `cases` and `assess`. It includes fourteen synthetic demos, the dossier schema, safe JSON/Markdown reports, the three byte-oriented public functions, and `validate`, `analyze` and `demo` commands. There are no third-party runtime dependencies. The engineering license is Apache-2.0; source papers and private evidence are not bundled.

Qualification covers 64-bit CPython 3.12 and 3.13 on Ubuntu 22.04 x64 and Windows Server 2022 x64. A target is qualified only when that candidate's checks actually pass there. Other platforms remain unqualified. The suite checks software contracts and synthetic cases. No real-data effectiveness pilot, evidence authentication, scientific certification or deployment authorization is claimed.

## Build from an exact clean commit

Maintainers need Git, a supported Python, and the `build` frontend. Install build tooling with `python -m pip install build`. The standard setuptools backend is unchanged. Isolated builds may obtain build dependencies from the configured package index; the installed toolkit and offline installation check do not use network access.

Commit the intended source first. Run `git rev-parse HEAD` and retain its full 40-character SHA independently. Replace the capitalized values below with that SHA and a new output path outside the checkout. The output's parent must already exist.

```sh
python scripts/build_candidate.py --revision SOURCE_COMMIT --output NEW_OUTSIDE_DIRECTORY
```

The script refuses a different HEAD, staged/unstaged changes, nonignored untracked files, inconsistent versions, an already stamped checkout, an existing destination or a destination inside the checkout. Ignored working-tree files cannot contaminate the export because only the named commit is archived. Archive paths, executable flags and file bytes are checked against the committed tree before stamping, so local Git attributes cannot silently omit or substitute source. This small builder supports committed regular files; symlinks and submodules require a separate packaging decision and are refused. It does not modify the repository.

The exported copy receives one static module constant:

```text
BUILD_ID = "ect-0.1.0rc1+git.SOURCE_COMMIT"
```

The script builds an sdist, extracts that sdist into a separate directory without Git metadata, builds its wheel, and verifies the same identity in both artifacts. Source-checkout builds retain `BUILD_ID = "unknown"`. The runtime never invokes Git or reads environment variables to infer identity.

Output layout:

| Path under the new output directory | Purpose |
| --- | --- |
| `source/` | Exact committed export plus the generated static build identity |
| `from-sdist/evaluation_closure_toolkit-0.1.0rc1/` | Source extracted from the built sdist |
| `dist/` | Candidate `.tar.gz` and `.whl` |
| `artifacts.json` | Source revision, version, build ID and actual artifact names, sizes and SHA-256 digests |

`--no-isolation` is available when all required build tooling is already installed. It changes dependency provisioning, not the source-identity rules. A failed build may leave its new output directory for inspection, but no success manifest is issued. Use another new destination after resolving the failure; existing outputs are never replaced.

## Verify the actual artifacts

From the source directory extracted from the sdist, install its wheel with `python -m pip install --no-index --no-deps PATH_TO_WHEEL`, then run:

```sh
python -m unittest discover -s tests -v
python scripts/generate_schema.py --check
python scripts/check_install.py --wheel PATH_TO_WHEEL --expected-build-id ect-0.1.0rc1+git.SOURCE_COMMIT
```

Supply the expected revision from the intended commit, not by trusting whichever identity a wheel happens to report. `check_install.py` creates a fresh virtual environment outside the checkout and verifies that exact expected identity in admission and analysis. It also checks metadata/version, Apache license bytes, schema, zero runtime dependencies, all fourteen demos, both entry points, deterministic reruns, saved-report Markdown parity and the actual README, user-guide and reproducibility examples. Its default identity expectation is `unknown`, for an ordinary source build.

CI runs this process on the exact PR head commit, rather than a synthetic merge commit, in the four named x64 cells. Tests are loaded from the extracted source distribution against the installed candidate. Windows skips the two existing POSIX-only filesystem checks. Successful jobs retain their two distribution files and `artifacts.json` as workflow artifacts for 30 days. These are candidate build artifacts, not a formal release. Download and retain them when needed; workflow retention is finite.

Artifact hashes identify the bytes of each particular build. They do not promise identical wheel/sdist bytes across build tools, timestamps or operating systems. Report determinism and cross-runtime normalized report equality have their separate contract in [REPRODUCIBILITY.md](REPRODUCIBILITY.md). A source label and an artifact manifest are not signed attestations and cannot authenticate the supplied evaluation evidence.

## Owner acceptance and stable publication

Before approving publication, review the exact candidate PR and its four-cell results, the limits in the [user guide](USER_GUIDE.md), and any unresolved failures. A missing platform result remains a blocker for claiming that platform. Tests passing alone do not authorize publication.

After separate authorization:

1. Merge the reviewed PR stack in dependency order. Preserve the accepted contract and source history.
2. Set the stable version to `0.1.0`, update version-specific documentation/CI paths, and commit that final source. A changed or merged revision does not inherit the candidate's exact-source qualification automatically.
3. Rebuild and qualify the final clean commit with this same procedure and all four target cells. Retain the resulting artifacts and their manifest.
4. With owner approval, create the final tag at that qualified commit and publish those exact artifacts with their scope and limitations. Package-index publication requires its own configured workflow and authorization; it is not performed by these scripts.

Do not add capture archives, a replay command, simulation, live collection or adapters as implied release work. Those features remain outside v0.1. A future licensed real-data pilot may support additional empirical claims only to the extent its evidence warrants.
