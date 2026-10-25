# Evaluation Closure Toolkit P0 1 Source Intake

**Inspection date:** 2026-09-30, America/Los_Angeles  
**State:** P0-1 preparation completed; owner review pending  
**Scope:** Source identity, preliminary semantic inheritance, capability-specific gaps  
**Governing handoff:** `Evaluation_Closure_Toolkit_Work_Handoff.md`, revision 0.1

The supplied sources and identifiable predecessor definitions are sufficient to proceed to P0-2. Production implementation remains deferred under the handoff. This intake does not establish a frozen ECT contract, approve a runtime dependency, or accept an upstream candidate branch.

No repository was created or modified. The review inspected documents, representative implementation passages and test bodies. It did not execute predecessor tests or repeat release acceptance.

## 1 Source register

PDF page numbers below count from the first PDF page. Fingerprints in section 8 identify the supplied bytes. Uploaded manuscripts are the current source candidates for this project; this register does not declare every theoretical claim empirically established.

| ID | Supplied manuscript | Identity and use |
|---|---|---|
| EC | Evaluation Closure: Benchmark Inbreeding and the Design of Open AI Evaluation | 16 pages, 362,486 bytes. SHA-256 exactly matches the handoff. Primary authority for the evaluation-specific product boundary. Displayed title omits the colon. |
| UIL | The Universal Inbreeding Law: Closure, Diversity Loss, Correlated Error, and Integrity Decay in Self-Organizing Systems | 20 pages. Supplied filename says v2; no internal version label found. Relevant mathematical core on pp. 6-9; limits on pp. 9 and 15-16. |
| SISD | Structural Inbreeding in Synthetic Data: How Linguistic Abundance Conceals the Collapse of Generative Support | 31 pages. Displayed Version 1.0, August 2026. Exact hash matches StructDet's adopted source. Relevant sections 3, 4, 5-6, 8.6, 9 and 12. |
| QB | The Question Bottleneck in the Age of AI: Structural Fidelity Discrimination and the Reality-Coupled Architecture of Knowledge Production | 33 pages; no internal version label found. Sections 7.3-7.5, 13.6 and 14 support claim typing, provenance and anomaly preservation. |
| SIL | The Source Integrity Layer: Presence × Integrity and the Governance of AI-Native Information Distribution | 18 pages. Exact hash matches the primary source-governance manuscript identified by accepted Source Integrity `SPEC_AUDIT.md` section 2. This closes the handoff's core Source Integrity source-selection gap. |
| ENT | Entropy as a Structural Boundary Condition, Not a Causal Force | 11 pages, supplied filename v2. Background only for this scope. No general entropy detector is inherited. |
| BVL | The Boundary Vacuum Law: Gradient, Boundary Failure, Topological Flow, and Pressure Capture in Social Systems | 29 pages, supplied filename v2. Optional boundary-control context. No social-flow or pressure metric enters the initial product. |

UIL, SISD, QB and SIL are substantive manuscripts with closing material and references. They are not similarly titled editorial reports. The three supplementary manuscripts requested by the handoff are therefore available in concrete versions.

EC sections 2, 6, 7, 9, 10 and 12 support the proposed distinction between reporting completeness, local calculation and external validity. Rendered pages 6-8 and 11 were inspected to check the mathematical notation and the five-condition conjunction.

**Compact missing-source list:** Upstream source maps additionally name *The Heat Death of Language v2* (Source Integrity), *Structural Determinacy* (StructDet), and the *Supplementary Case Registry for the Universal Inbreeding Law Version 2.0* (Recursive Integrity). These were not supplied or read. Accepted engineering specifications are sufficient for the selected inheritance review; obtain an additional manuscript only if a decision needs fresh interpretation beyond those specifications. Recursive Integrity names UIL v2 without a manuscript hash, so exact upstream-to-upload byte correspondence remains unverified. No further paper collection is required for P0-2.

The EC manuscript states CC BY-NC-ND 4.0. This intake grants no new distribution rights. The proposed Apache-2.0 license for original toolkit engineering remains a later owner decision; theory PDFs will not be bundled by default.

## 2 Predecessor status

Repository acceptance, branch integration and public interface availability are recorded separately. Each status is an observation from this intake date.

### Source Integrity Toolkit

Repository: `DavidWallstructurallaw/source-integrity-toolkit`.

Accepted merged baseline: `6dbca96f3314d537beed4ccb6202147bd9248dd9`, incorporating PR #33, P3-W14. `PHASE_0_APPROVAL.md` adopts the eighteen-document specification baseline at `7d2e5fcaff591641b5cefce00e71e88941dd1f95` and supersedes historical proposal headers.

PR #34, P3-W15, remains open and unmerged at `90684996eac568af6129973764fe40f3b666a15f`. Its pending planner distinction between an unselected dependency dimension and no applicable subject must remain candidate behavior.

The accepted definitions and representative private-core behavior are usable as semantic references. The public `audit_bundle` and `audit_file` functions in `src/source_integrity_toolkit/api.py` still raise `NotImplementedError`. A public audit adapter is consequently deferred.

Evidence locations, pinned to the accepted merged baseline:

- [PHASE_0_APPROVAL.md](https://github.com/DavidWallstructurallaw/source-integrity-toolkit/blob/6dbca96f3314d537beed4ccb6202147bd9248dd9/PHASE_0_APPROVAL.md)
- [SPEC_AUDIT.md](https://github.com/DavidWallstructurallaw/source-integrity-toolkit/blob/6dbca96f3314d537beed4ccb6202147bd9248dd9/SPEC_AUDIT.md), section 2; `THEORY_SOURCE_MAP.md`.
- [DEFINITIONS_AND_UNITS.md](https://github.com/DavidWallstructurallaw/source-integrity-toolkit/blob/6dbca96f3314d537beed4ccb6202147bd9248dd9/DEFINITIONS_AND_UNITS.md), sections 6, 8-13 and 20-28.
- [CLAIMS_EVIDENCE_AND_LINEAGE_SPEC.md](https://github.com/DavidWallstructurallaw/source-integrity-toolkit/blob/6dbca96f3314d537beed4ccb6202147bd9248dd9/CLAIMS_EVIDENCE_AND_LINEAGE_SPEC.md), sections 6.9 and 9-11.
- `analysis/process_comparison.py`, `analysis/presence.py` and `analysis/correction_outcomes.py` under `src/source_integrity_toolkit/`, with corresponding `tests/unit/` files.

### Recursive Integrity Toolkit

Repository: `DavidWallstructurallaw/recursive-integrity-toolkit`.

Merged `main` is `cfe1bd0941c1125498ac3d9d9ebf3adafa2c2fcb`, an installable Phase 1 scaffold. Phase 4, Phase 5 and Phase 6A completion records report accepted milestones on stacked, open draft PRs #1-3. The latest such milestone is Phase 6A: tested candidate `157109717079c9db9f02ac65ec1493709f37d8a4`, administrative head `b6389c6c50f2fc61d39580274bd24ed39e09ca45`. Acceptance here is attributed to those records; this intake did not re-audit candidate CI artifacts. The release listing is empty.

Phase 6B head `33ae8af1aaeb99ac118368148a80d563804eeff9` contains its Step 5 completion record. Its schema 1.3 simulation work remains provisional. The accepted 6A branch documents report schema 1.2; that development contract cannot be treated as a released dependency.

`PHASE_0_APPROVAL.md` approves exact specification hashes. Fetched product-spec, definitions and source-map bytes match them, including the handoff's product-spec blob `970f3ad9583aac99f424c9fc9c69cf316652692a`. Historical pending text inside the source map does not reopen approval.

Evidence locations:

- [PHASE_0_APPROVAL.md](https://github.com/DavidWallstructurallaw/recursive-integrity-toolkit/blob/cfe1bd0941c1125498ac3d9d9ebf3adafa2c2fcb/PHASE_0_APPROVAL.md), with `V0.1_PRODUCT_SPEC.md`, `DEFINITIONS_AND_UNITS.md` and `THEORY_SOURCE_MAP.md` at that commit.
- [PHASE_6A_COMPLETION.md](https://github.com/DavidWallstructurallaw/recursive-integrity-toolkit/blob/b6389c6c50f2fc61d39580274bd24ed39e09ca45/PHASE_6A_COMPLETION.md), with `docs/report_schema.md` and `examples/longitudinal/EXPECTED_OUTPUTS.md` at that accepted milestone.
- At the same 6A commit: `tests/unit/test_T1_representation.py`, `test_T3_bounds.py`, `test_T4_ancestry.py`, `test_lineage_bounds_proxy.py` and `test_T1_resampling.py`; relevant implementations under `src/recursive_integrity_toolkit/metrics/` and `lineage/`.

### StructDet

Repository: `DavidWallstructurallaw/structdet-bench`.

Merged main and published v0.1.0 both resolve to `0a9dc88deffd4b14264485b161bea06f027f68f5`. No open PR was returned. `PHASE_1_PLAN.md` section 1.1 records acceptance of the consolidated Phase 0 definitions, superseding historical proposed headers.

The shipped public workflow uses the HERO sorting frame, imported structural assignments and offline comparison/longitudinal reports. Public CLI and report contracts exist. ECT's evaluation-item unit and generic frames require their own specification; an ECT dossier cannot be passed unchanged to the sorting loader. Internal component objects also carry private data and must not become interchange payloads.

`THEORY_SOURCES.md` and the approval record pin both SISD and EC to the exact supplied PDF hashes. Relevant evidence at the accepted release commit:

- [DEFINITIONS_AND_UNITS.md](https://github.com/DavidWallstructurallaw/structdet-bench/blob/0a9dc88deffd4b14264485b161bea06f027f68f5/DEFINITIONS_AND_UNITS.md), sections 3-6; `STRUCTURAL_CLASS_CONTRACT.md`, sections 2, 6-7 and 10-12.
- [METRICS_SPEC.md](https://github.com/DavidWallstructurallaw/structdet-bench/blob/0a9dc88deffd4b14264485b161bea06f027f68f5/METRICS_SPEC.md), sections 3-7, 10, 12 and 14.
- [LONGITUDINAL_FORMAT.md](https://github.com/DavidWallstructurallaw/structdet-bench/blob/0a9dc88deffd4b14264485b161bea06f027f68f5/LONGITUDINAL_FORMAT.md), sections 10, 14.4 and 15.
- `structdet_bench/metrics.py`, `populations.py`, `longitudinal.py` and `recovery.py`, with corresponding `tests/test_*.py` files.

`structdet-code` was not needed for this measurement slice and was not audited.

## 3 Preliminary inheritance matrix

These are proposed treatments for P0-2, with no new public API or enum frozen by this document.

| ECT requirement | Source and candidate treatment | Boundary to preserve |
|---|---|---|
| Supplied assertions, deductions and unavailable information | Reuse Source Integrity distinctions | A graph deduction retains the evidentiary basis of its declared edges. Captured bytes and valid schemas do not authenticate claims. |
| Typed ancestry and shared origin | Adapt Source Integrity witnesses to evaluation roles and versions | A parentless node is a terminal in the supplied graph. It cannot become an independent origin without the required basis. Known paths and unknown frontiers coexist. |
| Scoped independence | Adapt Source Integrity acquisition, method, model ancestry, rubric and organizational dimensions | Pairwise results do not establish setwise independence. Distinct organizations or model names cannot replace inquiry-specific evidence. |
| External presence and use | Adapt Source Integrity and Recursive Integrity definitions | Boundary, time, role, relevant distinction and recorded influence remain explicit. ECT received/retained/qualified/used must not silently copy another tool's stage enum. |
| Recursive reuse | Reuse version and ancestry discipline; define ECT event relationships locally | Snapshot similarity or a graph cycle alone cannot establish a recursive causal evaluation process. |
| Structural-class accounting | Reuse EC/SISD mathematics and StructDet measurement discipline | Supplied assignments require a declared representation. Unresolved assignments remain visible in coverage; they cannot become an invented mechanism class. |
| Longitudinal and tail comparisons | Adapt StructDet frame, population and revision rules | Missing observation, taxonomy change, population attrition and confirmed support loss remain separate. Observed absence cannot establish latent model extinction. |
| Correction evidence | Reuse Source Integrity route, authority, handling and linked-change distinctions; define outcome criteria locally | A qualified linked change does not establish substantive effectiveness, causal benefit or sustained corrective capacity. |
| Structural validity and reopening | Define evaluation-specific contract from EC, with SISD/QB support | An anomaly record, an adjudicated distinction, a frame revision and validated improvement are different claims. |
| Five-condition profile | Local EC contract | Structural validity, external presence, source integrity, tail retention and corrective capacity are non-compensatory and claim-scoped. |
| Cross-tool import | Defer until a needed versioned public contract is verified | No private-module imports, upstream checkout requirement or evidence promotion after import. |

## 4 Small behavioral anchors

These examples identify the meaning to protect during P0-2. They are read or hand-specified examples, with no ECT implementation or passing test claim.

1. **Unknown ancestry:** Source Integrity's `test_vf006_m_and_vf021_p_shared_unknown_is_one_frontier_and_zero_reached_origins` preserves two affected seeds reaching one unknown frontier, with zero reached qualified origins. The unresolved boundary supplies no hidden-origin upper bound.
2. **Independent dimensions:** `test_other_dimension_dependency_does_not_poison_exact_acquisition_comparison` and `test_overlapping_pairs_and_supplied_set_stay_separate_without_transitive_completion` protect dimension scope and prohibit transitive completion of an independence claim.
3. **Externality:** `test_vf029_negative_recent_human_remote_metadata_and_admission_cannot_create_externality` rejects promotion from recent date, human authorship, remote location or admission alone. A supplied assessment for a different system boundary cannot qualify the selected inquiry.
4. **Correction:** `test_vf043_n_acceptance_and_unlinked_later_version_do_not_create_change` preserves the case and handling record while yielding no qualified linked target or case. An independently documented change can also survive a separate authority gap.
5. **Structural accounting:** The handoff's fixed four-class examples give A = `(12,6,4,2)`, 24 classified items, support 4, SCI `25/72`; B = `(24,16,8,0)`, 48 classified items, support 3, SCI `7/18`. The declared required fourth class is absent from B. Incomplete membership, unresolved assignment or a taxonomy split blocks reuse of that loss conclusion.
6. **Recursive Integrity bounds:** Its inspected tests give `N=8, C=3, U=2` a direct-closure interval of `[3/8,5/8]`. A Hero example has direct `[1/2,1/2]` alongside lineage `[0,0]`. These refer to different declared objects. Neither becomes an ECT openness score or an independent-validator count.
7. **StructDet populations:** Its MF-07 example preserves six selected observations, four classified observations with counts `(2,2)` and two valid-classified observations in one class. Conditional SCI is `1/2` and `1` respectively. A missing assignment does not shrink the selected denominator. Missing longitudinal panels cannot disappear from the declared panel mean; a schema recut cannot turn old samples into observed recovery.

P0-2 should add one small counterexample for each adopted local translation. P0-1 does not require a new test harness.

## 5 Source differences requiring explicit treatment

**Five conditions govern this tool.** SISD section 9 describes a four-part Evaluation Closure framework. EC section 7 explicitly adds structural validity to the conjunctive profile. The handoff's primary-source order resolves the product direction: retain all five, including structural validity as its own condition.

**Actor identity and epistemic qualification need separate fields.** SIL p. 16 argues for human judgment in its institutional governance layer. QB sections 8-9 assigns epistemic functions to humans, instruments, AI or hybrids subject to appropriate constraints. P0-2 should keep responsible authority, actor identity, grounding and independence separate, and document which claim needs which review. Neither statement supplies a universal automatic qualification rule based on a human label.

**Correction stages need a local mapping.** Source Integrity distinguishes admission, preservation, selection and influence, and separately distinguishes route, authority, handling and linked change. The handoff proposes ECT-specific external-input and correction sequences. P0-2 must specify their relationships without presuming a mandatory funnel or promoting a recorded change into an effective remedy.

**Optional entropy language must retain its variable.** ENT discusses increasing statistical entropy in some recursive AI examples; SISD distinguishes realization entropy from structural entropy and support. The initial auditor should use explicit structural distributions and concentration. An undifferentiated entropy trend has no authorized diagnostic meaning here. BVL's comparative formulas likewise require domain-specific proxies and add no initial computational obligation.

**Finite-model statements retain their assumptions.** EC's expectations apply to finite multinomial resampling. They do not require every realized path to lose diversity. For an absent class, external reentry has positive probability only when both mixture weight and external class mass are positive; finite sampling does not guarantee recovery. The simulator decision remains for P0-3. No universal external-input percentage or real-system collapse forecast is established.

## 6 Capability-specific blockers

| Capability | P0-1 outcome | Remaining requirement before implementation |
|---|---|---|
| Claim and reporting linter | Primary source available; independent preparation can continue | P0-2/P0-3 must define claim applicability, presence versus qualification, expiry semantics and the initial dossier contract. |
| Structural accounting and compatible comparison | Theory and predecessor discipline available | Define ECT populations, assignment coverage, empty-population results, frame compatibility and revision mappings. |
| Typed evaluator lineage | Stable Source Integrity semantic slice available | Define evaluation-specific relation types, scope, finite witnesses and incomplete traversal results. |
| External-input qualification | Relevant definitions available | Resolve stage mapping, boundary/time units, unknown qualification and recorded-use meaning. |
| Anomaly revision and five-condition assessment | EC provides the primary requirements | Specify supplied adjudication, contrary evidence, local outcome criteria and non-compensatory claim wording. |
| Direct Source Integrity adapter | Deferred | A working, documented and versioned public audit/export contract is absent at the inspected merged baseline. |
| Other predecessor adapters | Deferred unless a concrete workflow needs one | Verify the exact public interchange contract and status separately from semantic acceptance. |
| Optional resampling mode | Mathematical source available | P0-3 scope decision, exact assumptions, method identity and separation from empirical dossier evidence. |

Production implementation also retains the handoff's global prerequisites: an accepted minimal specification, selected runtime/security boundary, a small vertical slice and explicit owner authorization. No capability requires waiting for every predecessor roadmap item.

## 7 Proposed next step

Proceed to **P0-2 Semantic Inheritance Review** after owner review of this intake. Keep it to one compact amendment or companion document:

1. Map the selected Source Integrity, Recursive Integrity and StructDet definitions to ECT units and claims, using the pinned evidence below.
2. Mark each definition reused, adapted, locally defined or deferred, and record the bounded reasons.
3. Resolve the stage, correction-effectiveness, role/authority and population differences identified here with small independently specified examples.
4. Leave the minimal executable specification, simulator choice and runtime matrix for P0-3; leave the readiness decision and implementation authorization for P0-4.

**Stop point:** P0-1 is complete. P0-2 and production implementation have not been started by this document.

## 8 Supplied PDF fingerprints

The numeric prefixes correspond to the project source files supplied with this session.

```text
01 ENT   11 pages  228645 bytes
7e5dbfb7cc270c68d0533b3ba74fbee1e96374004761cb46ffe6a4e56ef5bab4

02 EC    16 pages  362486 bytes
002d2393d05cb2c8b1db0a70e844e3d775e2be2155db7b2ffaadaa8080c8b950

03 BVL   29 pages  492138 bytes
1323813d59152bc2d87ebab90dadce6d7a9232e14b67bb2b50a45e43b5e1e530

04 UIL   20 pages  349251 bytes
b788c18b7a66886b623ea7c35b777643146b38e78b540acedde87cc5e019f2ee

05 SISD  31 pages  721864 bytes
80c193231af343d383544cee924a11fbb063a5c4ccee02d996ea4f904979565a

06 QB    33 pages  527745 bytes
1749b649c01406b6482f9976a4e60a05d899eb9cf86f24ad3128437ca9b80b35

07 SIL   18 pages  250417 bytes
bc233063e153fdcee83ad6e6088764f20dd24e3f4c7ae094b88f35905b52c3b3
```
