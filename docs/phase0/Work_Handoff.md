# Evaluation Closure Toolkit
## Work Handoff: Product Boundary, Semantic Inheritance, and Deferred Implementation

**Document revision:** 0.1  
**Owner:** Xiangyu Guo  
**Intended recipient:** Work engineering session  
**Working project name:** Evaluation Closure Toolkit  
**Candidate repository name:** `evaluation-closure-toolkit`  
**Delivery state:** Preparation handoff. No implementation or release acceptance is claimed.  
**Current execution boundary:** Prepare the design; wait for relevant predecessor semantics and explicit owner authorization before production implementation.

> Build a local, auditable tool for examining whether an evaluation system retains meaningful contact with the reality its capability claims concern.

## 1. Read This First

The owner wants to preserve this project now while completing relevant work in Source Integrity Toolkit and Recursive Integrity Toolkit. Those projects can supply mature definitions for evidence status, lineage, ancestry, independence, external presence, and correction. StructDet supplies related measurement discipline.

Work should begin with source intake and a compact semantic-inheritance review. This handoff does not authorize repository creation, upstream repository changes, production code, dependency extraction, PR merges, package publication, or release creation.

The immediate deliverable is a reviewable design and a capability-specific readiness decision. A future instruction to start implementation must name the approved phase or step.

### 1.1 Decisions already established for this handoff

- The proposed product has its own evaluation-system scope.
- Production implementation is deferred while relevant predecessor semantics mature.
- Tools remain independently installable and runnable.
- Evidence gaps, unresolved ancestry, supplied declarations, and observed artifacts retain distinct meanings.
- Open evaluation has five non-compensatory conditions. There is no universal openness, truth, integrity, or collapse score.
- Verification must protect actual semantic, security, and release failure modes. Administrative machinery must remain small.

### 1.2 Engineering proposals requiring approval

The candidate input model, result states, diagnostic identifiers, CLI, fixtures, module boundaries, and implementation sequence below are proposed translations of the theory. They are not quotations from the paper or existing public APIs.

The handoff's revision number does not establish a software version. The repository name and command names remain provisional until availability and owner preference are checked.

### 1.3 Authority order

Use explicit owner decisions first. For theoretical claims, use the identified primary paper and subsequently confirmed supplementary manuscripts. For inherited engineering definitions, use exact accepted predecessor specifications, relevant implementation, and behavioral tests.

This handoff supplies the proposed bridge between those sources. Earlier conversational examples are design sketches. When they conflict with the paper or accepted definitions, record the conflict and obtain a bounded decision. Do not silently reconcile distinct concepts merely because their names resemble each other.

## 2. Product Purpose and First User Value

### 2.1 Product statement

Evaluation Closure Toolkit accepts a caller-prepared local dossier describing a benchmark or evaluation pipeline, its represented conditions, item ancestry, evaluator relationships, external evidence, retained anomalies, revisions, and correction records.

It produces inspectable findings about the supplied evaluation structure, calculations under an explicit measurement frame, and unresolved requirements for the evaluation claim. Each conclusion identifies its premises and scope.

A useful first user question is:

> My evaluation gained more test items and higher scores. Did it retain meaningful structural coverage, independent corrective input, and a route from detected failures to correction?

### 2.2 Initial users and workflows

The intended users are evaluation researchers, benchmark maintainers, research engineers, and reviewers examining documented evaluation processes.

The first release should support three practical workflows:

1. **Review one evaluation dossier.** Inspect claim scope, structural coverage, generator/reference/judge relationships, external-input records, and correction evidence.
2. **Compare compatible benchmark versions.** Track represented mechanisms, unresolved assignments, declared tail classes, preserved anomalies, and changes in the evaluation frame.
3. **Inspect an openness claim.** Produce a five-condition evidence profile without converting incomplete documentation into a safety or capability certificate.

A small optional mathematical mode can illustrate the paper's finite resampling model. It remains separate from the dossier auditor.

### 2.3 Success at the user level

A first-time user should be able to run a packaged synthetic example without an account or model key, identify the exact evidence behind a finding, and understand which additional information would change the result.

A user with a real dossier should be able to obtain a useful partial report even when ancestry or deployment evidence is incomplete. Unresolved facts are a normal analytical outcome.

## 3. Source Register and Reading Requirements

### 3.1 Primary source available for this handoff

**[EC] Xiangyu Guo (2026), _Evaluation Closure: Benchmark Inbreeding and the Design of Open AI Evaluation_.**

The supplied PDF contains 16 pages. Its displayed title omits the separating colon.

- Supplied filename: `Evaluation Closure Benchmark Inbreeding and the Design of Open AI Evaluation.pdf`
- Size of the inspected file: `362486` bytes.
- SHA-256: `002d2393d05cb2c8b1db0a70e844e3d775e2be2155db7b2ffaadaa8080c8b950`
- Stated manuscript license: Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International.

This identifies the version used for the handoff. A later owner-selected manuscript may supersede it through a documented semantic comparison. A matching hash identifies bytes; it does not establish scientific validity.

References such as `[EC, section 7.3, p. 11]` below point to this PDF. The equations in sections 4.1-4.5 were checked against the displayed pages because text extraction omits mathematical symbols.

### 3.2 Supplementary manuscripts to confirm

The following three works appear in [EC]'s reference list. Their authoritative full versions have not been established for this handoff:

| Manuscript | Candidate contribution | Intake requirement |
|---|---|---|
| _The Universal Inbreeding Law: Closure, Diversity Loss, Correlated Error, and Integrity Decay in Self-Organizing Systems_ | Recursive closure and the limits of the finite mathematical model | Obtain the owner's intended version; map only definitions actually used |
| _Structural Inbreeding in Synthetic Data: How Linguistic Abundance Conceals the Collapse of Generative Support_ | Task-relative structural representation and distinctions among forms of support | Confirm the complete manuscript and its relationship to adopted StructDet definitions |
| _The Question Bottleneck in the Age of AI: Structural Fidelity Discrimination and the Reality-Coupled Architecture of Knowledge Production_ | Structural fidelity, question framing, and reality-coupled correction | Read before assigning it any binding engineering requirement |

Also request the owner's chosen **core Source Integrity theory source**, or the accepted source map identifying that source. Do not select a manuscript as canonical merely because its title mentions source integrity.

Library search surfaced similarly titled research/editorial reports for Structural Inbreeding. These have not been treated as the authoritative manuscript. A title match and an editorial recommendation do not establish a final source version.

The primary paper is sufficient for preliminary product design. Missing supplementary sources block only the claims or inherited definitions that actually require them. They do not justify indefinite collection of unrelated papers.

### 3.3 Engineering sources consulted and their limits

Two predecessor documents were read for boundary and inheritance guidance:

- `DavidWallstructurallaw/source-integrity-toolkit`, `PHASE_3_PLAN.md`, especially sections 2, 2.1, and 3. This plan explicitly separates the private analytical core from later public reporting, serialization, file handling, and release work.
- `DavidWallstructurallaw/recursive-integrity-toolkit`, `V0.1_PRODUCT_SPEC.md`, especially sections 1-5. This specification establishes representation-bound diversity, evidence-bounded closure, assumption-bound simulations, and explicit unavailable conclusions. The returned file blob SHA was `970f3ad9583aac99f424c9fc9c69cf316652692a`.

These reads establish candidate semantic relationships. They do not constitute a current acceptance audit, a code review, or confirmation of compatible public APIs. Work must identify exact accepted source commits before inheriting an operational definition.

**Important sequencing correction:** completion of Source Integrity Phase 3 does not itself supply a public reporting envelope or stable public audit API. The phase's stated deliverable is the private analytical core. Evaluate readiness by the specific definitions and interfaces needed here.

### 3.4 Optional cross-system sources

Structural Safety, Boundary Vacuum Law, Capability-Bandwidth Mismatch, and responsibility-architecture papers may supply later integration context. They do not expand this v0.1 into deployment enforcement, organizational workload modeling, or liability analysis.

### 3.5 Licensing boundary

Proposed default for original engineering content: Apache-2.0, subject to owner confirmation for this repository. Preserve the separate licenses of theory publications and third-party or user evidence. Do not bundle theory PDFs, private dossiers, credentials, or externally owned benchmark data by default.

## 4. What the Tool Will and Will Not Establish

### 4.1 Proposed v0.1 scope

The initial auditor should provide:

- Strict local input validation and explicit missing/unknown states.
- Claim and reporting-completeness checks.
- Structural-class accounting under supplied, versioned assignments.
- Typed evaluation-lineage inspection with finite witnesses.
- Scoped accounting of supplied external-input evidence.
- Compatible version comparison, tail accounting, and anomaly/revision traceability.
- A five-condition openness evidence profile, including correction-path evidence.
- JSON and Markdown reports, packaged demonstrations, and bounded deterministic execution.

The mathematical resampling mode is a proposed additional capability. Phase 0 must decide whether a small standalone implementation has enough value to include in v0.1 or should remain a documented companion workflow using Recursive Integrity Toolkit.

### 4.2 Explicit exclusions

v0.1 does not collect live model outputs, execute benchmarks or candidate code, train models, browse private systems, authenticate institutions, discover hidden training ancestry, or automatically classify arbitrary natural-language tasks into valid structural classes.

It has no embedded LLM judge, telemetry, cloud service, database server, autonomous correction, deployment approval, or runtime policy enforcement.

It does not estimate causal error correlation from shared ancestry alone, infer a number of independent validators from a graph's disconnected components, or forecast real model collapse from a resampling simulation.

Universal semantic deduplication, general benchmark adapters, population-wide deployment-risk estimates, and a shared cross-tool framework remain outside the initial release.

### 4.3 Three different kinds of verification

Keep these distinct throughout the product:

| Kind | What this toolkit can check | Remaining limitation |
|---|---|---|
| Documentary structure | Required fields, typed links, chronology, supplied reviews, and contradictions | A coherent dossier can contain false declarations |
| Local analytical result | Arithmetic, graph consequences, report consistency, and captured artifact identity | The result inherits the validity of its input model and premises |
| External validity | Whether the dossier includes relevant external evidence and its documented qualification | The toolkit cannot independently recreate every reported event or establish that the evaluation represents all of deployment reality |

A software test passing establishes a tested software behavior. A supplied experiment receipt remains supplied evidence. A valid structural mapping requires domain-relevant support beyond schema validity. [EC, sections 2, 6, and 12]

## 5. Semantic Inheritance and Start Gate

### 5.1 Inheritance matrix

| Evaluation Closure requirement | Candidate predecessor | Reuse target | Boundary to preserve |
|---|---|---|---|
| Supplied assertions, deductions, unresolved evidence | Source Integrity | Evidence-state distinctions and their counterexamples | Documentary qualification cannot authenticate an assertion |
| Shared origin, missing ancestry, scoped independence | Source Integrity; Recursive Integrity where relevant | Typed lineage, completeness, and witness semantics | Different IDs, URLs, names, or providers do not establish independence |
| External presence | Source Integrity and Recursive Integrity | Scoped acquisition, grounding, process, and lineage distinctions | Define externality relative to this evaluated process and time window |
| Recursive reuse | Recursive Integrity | Versioned ancestry and recorded process identity | Snapshot overlap does not establish a recursive causal process |
| Structural-class measurement | StructDet-Bench; StructDet Code where relevant | Explicit frame, populations, assignments, concentration, and missing states | Transfer arithmetic only after confirming the unit and denominator |
| Longitudinal comparison | StructDet and relevant Recursive Integrity work | Matched observations, frame compatibility, revisions, and history | Taxonomy change or attrition must not masquerade as structural loss |
| Correction evidence | Source Integrity | Separation of declared route, authority, event, and qualified outcome | A recorded attempt does not establish an effective correction |
| Structural cut and reopening | [EC] is the primary source | Evaluation-specific requirements and anomaly-to-revision links | Creating or renaming labels does not establish improved structural validity |
| Five-condition profile | [EC] is the primary source | Non-compensatory, claim-scoped evaluation | No weighted total or unrestricted certification |
| Consequential deployment boundary | Structural Safety, optional later interface | Evidence exchange only | The evaluation auditor does not become an enforcement engine |

No row implies that a named Python class, function, export schema, or reusable implementation currently exists.

### 5.2 Reuse policy

Prefer semantic reuse and small domain-appropriate implementations. Do not import private predecessor modules or require an upstream checkout at runtime.

A future adapter must consume an explicitly versioned, documented interchange format. It must preserve the originating tool, schema, scope, evidence status, limitations, and unresolved states. Successful import establishes parsing and mapping, with no automatic promotion of evidence.

Do not extract a common package merely to make all repositories share a class name. Accept bounded local implementation where meanings differ. Explain such differences in the inheritance matrix.

### 5.3 Readiness criteria

Production implementation can begin when the owner authorizes it and the following are true for the selected v0.1 scope:

1. The relevant primary and supplementary source versions are identified.
2. The inherited definitions have accepted source locations, behavioral examples, and explicit limits.
3. Any difference among predecessor meanings has an explicit local decision.
4. Input units, populations, unknown states, evidence qualification, and report claims are sufficiently specified to write independent expected outcomes.
5. Planned external dependencies are either unnecessary or available through a verified public contract.
6. A small vertical-slice plan and its acceptance examples are approved.

Do not wait for every predecessor roadmap item or future release. A stable semantic slice can be sufficient. Conversely, a phase number, green badge, or release label alone cannot establish that the required contract exists.

When a predecessor remains unsettled, mark the affected capability `deferred`. Continue independent design work. Implementing a separate local definition requires owner approval and an explicit compatibility note.

## 6. Theory-to-Engineering Map

| Paper location | Theoretical requirement | Proposed executable treatment | Prohibited substitution |
|---|---|---|---|
| Sections 1 and 3, pp. 2-4 | Evaluation and model development can form a coupled recursive lineage | Versioned roles, influence/derivation records, and known ancestry witnesses | Calling every repeated benchmark a demonstrated closed loop |
| Section 2, pp. 3-4 | Measurement, distributional, and structural validity answer different questions | Separate claim requirements and evidence fields | Treating reproducibility as proof of deployment coverage |
| Section 3.1, p. 5 | Surface item abundance can coexist with concentrated structural support | Item counts and supplied structural-class distributions reported separately | Embedding distance or string uniqueness as structural ground truth |
| Section 3.2, p. 5 | Evaluators may share lineage and blind spots | Scoped overlap/exposure findings with provenance | Inferring measured error covariance or independence counts |
| Section 4, pp. 6-8 | Exact finite resampling model with stated assumptions | Optional analytical null results and seeded simulations | Production collapse predictions |
| Sections 4.4-4.5, pp. 7-8 | Distributional and structural reopening are distinct | Separate external-case admission from adjudicated frame revision | New timestamps or new labels as proof of openness |
| Section 6, pp. 9-10 | Validation must match the claim type | Inspect required evidence types and supplied receipts | The auditor becoming a universal proof checker or domain expert |
| Section 7, pp. 10-11 | Five conjunctive conditions | Five evidence profiles and a scoped claim assessment | An aggregate openness score |
| Section 8, p. 12 | Horizon, propagation, recovery, and reflexivity matter | Inspect recorded requirements and histories where supplied | Longer static item lists as long-horizon evidence |
| Sections 9-10, pp. 12-13 | Narrow benchmark claims remain useful and require explicit reporting | Claim-scoped reporting linter | Penalizing a narrow regression test for not certifying an open-world deployment |

## 7. Candidate Input Contract

Use one local JSON dossier for the first vertical slice. Large auxiliary payloads and adapters can be added only when their file boundaries are specified. Every object below is a proposed engineering object.

| Object | Minimum meaning |
|---|---|
| `evaluation` | Evaluation identity, benchmark version, protocol identity, and the selected analysis scope |
| `claims` | Capability assertions with intended use, claim type, horizon, and evidence requirements |
| `frames` | Versioned structural cuts: task, context, resolution, represented conditions, exclusions, and class definitions |
| `items` | Item versions with source references, process role, supplied assignments, and separate validity/test-result records |
| `actors` | Generators, reference producers, classifiers, judges, evaluated models, and responsible reviewers |
| `relations` | Typed, versioned derivation, use, training/exposure, review, and correction links with attributed evidence |
| `evidence` | Supplied materials, knowledge type, transformation history, qualification records, scope, and uncertainty |
| `snapshots` | Explicit populations and item memberships at recorded benchmark versions or checkpoints |
| `external_inputs` | Received, retained, qualified, and actually used input records, scoped to an evaluated process |
| `anomalies` | Preserved cases that do not fit the existing cut, including unresolved and disputed cases |
| `revisions` | Old/new frames, explicit mappings, motivating anomalies, and supplied adjudication |
| `corrections` | Proposed routes, authority records, attempts, action receipts, outcome evidence, and timing where relevant |
| `assessment_policy` | The declared claim requirements, admission rules, tail definitions, and comparison policy |

Separate identifiers from identity evidence. Separate the existence of a record from the truth of its contents.

### 7.1 Known values and missing states

Use explicit reason-bearing states for unavailable information. Missing, unknown, withheld, contradictory, not selected, and unsupported are distinguishable situations. Do not force all these into a single `null` without a reason.

A structurally valid dossier may contain unresolved ancestry or disputed assignments. Syntactic admission and analytical qualification are separate operations.

### 7.2 Structural assignment boundary

For the smallest release, prefer supplied hard assignments under one explicit primary partition. Each counted item has at most one admitted primary class for that calculation. A disputed or unresolved assignment remains visible outside the classified distribution.

Multi-label and probabilistic assignments require their own approved aggregation semantics. Do not average them, choose a convenient winner, or reinterpret them as hard labels automatically.

Preserve the assignment basis, reviewer/producer, class-definition version, and any contrary evidence. A supplied model suggestion cannot automatically become an accepted structural classification.

### 7.3 Typed graph boundary

Keep item derivation, semantic influence, training/exposure, evaluation, and correction relationships distinct. A connection in one relation type does not establish another.

Use versioned events for recorded recursive processes. An ancestry cycle, an evaluator-to-model relationship, and feedback across successive generations have different meanings. Graph-cycle detection alone cannot diagnose evaluation closure.

Unknown edges remain unknown. Completed search can establish the absence of a witness in the supplied graph and scope. It cannot establish the absence of hidden ancestry in the world.

## 8. Capability A: Claim and Reporting Linter

The linter should check whether a dossier supplies the reporting elements listed in [EC, section 10, p. 13]:

1. Capability claim and intended deployment scope.
2. Structural cut and represented/omitted conditions.
3. Item source and transformation lineage.
4. Contamination controls and known benchmark exposure.
5. Evaluator identity, evaluator-model relationships, and judge-bias controls.
6. Structural-class results, including declared rare and high-severity conditions.
7. Long-horizon, recovery, and override evidence where relevant.
8. Live or field evidence relevant to the claimed use.
9. A correction path triggered by failure.
10. The date after which the result should no longer be treated as current.

Report separately whether each requirement is present, well-formed, linked to evidence, and qualified under the selected policy. Presence checking cannot certify adequacy.

A missing timestamp means currentness is unestablished. An expired supplied validity date can be reported as expired. The tool must not invent a universal expiry interval.

For type-appropriate validation, inspect declared evidence requirements and submitted records. A supplied label such as `executed_test` does not establish that execution happened. The v0.1 auditor does not run the test. [EC, section 6, pp. 9-10]

Applicability is claim-scoped. A finite regression-test claim can be useful within its stated conditions. It must not receive an unrestricted open-evaluation certification, and it must not be declared useless for lacking unrelated deployment evidence. [EC, section 9, p. 12]

## 9. Capability B: Structural Distributions and Version Comparison

### 9.1 Populations and denominators

For each calculation, identify the frame/version, included item membership, assignment policy, weighting, and any validity filter.

Report at least:

- Total eligible items.
- Items with admitted primary structural assignments.
- Unresolved/disputed assignments and explicit exclusions.
- Assignment coverage.
- Per-class counts, observed support, concentration, and diversity for the admitted population.

Unknown items remain in the coverage denominator. Do not create an `unknown` mechanism class or distribute unresolved items among known classes.

Correctness and structural assignment are separate. If supplied validity results support a separate valid-only population, label its membership and denominator explicitly. Never silently filter failed or untested items out of the main profile.

### 9.2 Initial arithmetic

For an unweighted, nonempty population of `N` admitted single-class assignments, with counts `n_i`:

```text
p_i = n_i / N
observed_support = count of classes with n_i > 0
SCI = sum_i(p_i^2)
D = 1 - SCI
```

The paper specifies Gini-Simpson structural diversity. `SCI` is the corresponding concentration terminology proposed for alignment with StructDet. These results describe the declared partition and population. [EC, section 3.1, p. 5]

When `N = 0`, proportion-based metrics are unavailable. Report counts and the reason. Avoid representing an empty classified population as either perfect diversity or perfect concentration.

### 9.3 Comparison compatibility

Before numerical comparison, check task scope, frame semantics, assignment policy, population selection, and weighting. A stable class name does not guarantee stable class meaning.

Preserve benchmark version order and item ancestry. Repeated generation, paraphrasing, recursive benchmark reconstruction, and recursive model training retain their actual recorded process types.

Frame splits, merges, and new classes require explicit mappings and separate reporting. Do not bridge a taxonomy change through an unrecorded recoding. Incompatible comparisons produce useful side-by-side inventories and a specific unavailable comparison result.

### 9.4 Tail retention

Define tail conditions and required classes before evaluating their retention. Report rarity, severity, reference membership, representation, and available performance separately. Rarity and severity are not interchangeable.

A class absent from the submitted snapshot is absent from that recorded population. It is not automatically extinct in a model or absent from all future elicitation.

A claimed loss requires adequate snapshot coverage and compatible class semantics. Missing snapshots, incomplete memberships, and unclassified items cannot quietly become confirmed losses. [EC, sections 4.2 and 7.4]

## 10. Capability C: Evaluator Lineage and External Presence

### 10.1 Lineage exposure

Model the separate roles of item generator, reference-answer producer, structural classifier, judge, model selector, and evaluated system.

Where supplied relations support it, report common ancestors, reuse paths, role overlap, and incomplete ancestry frontiers. Include the relationship type, scope, dates/versions, and evidence basis.

A documented shared-lineage path establishes exposure under its premises. It does not numerically establish correlated errors. Estimating error correlation would require outcome data and a separately specified statistical analysis. [EC, section 3.2, p. 5]

Do not infer setwise independence from pairwise labels, assume transitivity of independence, or compute an effective validator count by counting provider names or root nodes. Retain any supplied independence assessment with its stated scope and qualification.

### 10.2 External-input accounting

Externality is relative to a process, lineage, role, and time. Record the distinction between a case being received, retained, qualified as relevant external input under a policy, and actually used to revise evaluation or constrain a decision.

A new timestamp, human author, different vendor, or `external=true` field alone cannot establish independent corrective content. Old real data can become structurally internal after repeated optimization. [EC, section 7.2, p. 10]

Report the supplied and qualified record counts with their actual units and denominators. Preserve unknown qualification and incomplete membership. Do not equate the observed share of records labeled external with the simulation parameter `lambda`.

### 10.3 Closure claims

The auditor should report documented closure-related conditions: recursive reuse paths, ancestry concentration where admissible, missing corrective evidence, and structural coverage changes.

A global claim that an evaluation system is closed requires more than any one of these signals. Keep the overall assessment scoped to the supplied records and chosen policy. High concentration can be functional in a genuinely closed, stable task. [EC, section 12, p. 14]

## 11. Capability D: Anomaly Preservation and Reopening

Distributional reopening introduces fresh reality-bearing cases within the existing represented state space. Structural reopening changes the represented distinctions in response to relevant anomalies. [EC, sections 4.4-4.5, pp. 7-8]

For each supplied anomaly, retain its original record or authorized retained artifact, source, context, current classification status, and review history. An unresolved case must survive as an unresolved case.

For each claimed structural revision, inspect:

- The old and new frame definitions.
- The motivating anomaly references.
- The particular distinction changed.
- The supplied review/adjudication and its scope.
- The mapping between previous and current classes.
- Evidence of incorporation into evaluation, where claimed.

Renaming classes, dividing a category without a meaningful distinction, adding paraphrases, or using a new generator does not by itself establish structural reopening.

A record of revision can be established at a documentary level while the validity of that revision remains unresolved. Report those separately.

**No-new-class finding rule:** zero newly created classes does not establish closure. A suitable stable frame may receive fresh external cases without needing revision. A negative structural-reopening finding requires a relevant obligation, preserved anomaly, unmet claimed response, or other explicit supporting premise.

Original anomaly preservation also respects privacy and rights. Authorized redacted records may carry declared limitations. The product must not force secret raw content into reports to satisfy a preservation checkbox.

## 12. Capability E: Correction and the Five-Condition Profile

### 12.1 Correction evidence

Keep the following separate:

```text
route declared
actor and authority documented
correction attempted
action/change recorded
outcome evidence supplied
outcome qualified under the stated criterion
```

These are proposed engineering distinctions. Source Integrity inheritance review must confirm their precise representation.

A ticket is evidence of a ticket. A rollback record can support a recorded action. Evidence that a remedy addressed the relevant failure requires an additional outcome basis.

Record review/correction timing where it is relevant to the claim. Unknown authority, unknown effectiveness, late intervention, and no recorded route are distinct outcomes. The tool does not execute a correction or independently establish that institutional powers remain exercisable. [EC, section 7.5, p. 11]

### 12.2 Five required conditions

Preserve all five conditions from [EC, section 7, pp. 10-11]:

1. Structural validity.
2. External presence.
3. Source integrity.
4. Tail retention.
5. Corrective capacity.

Do not collapse structural validity into reporting completeness. Do not omit it to create a four-condition profile.

Each condition needs a scoped requirement, supporting and contrary evidence, qualifications, unresolved facts, and a separate execution state. A missing proof of adequacy and an established contradiction must remain distinguishable.

### 12.3 Candidate result dimensions

Avoid a single overloaded `status`. Use separate dimensions, with exact names to be settled in Phase 0:

| Dimension | Candidate values or contents |
|---|---|
| Execution | completed, partial, not selected, unsupported, failed |
| Applicability | applicable, not applicable with rationale, unresolved |
| Assessment | supported under supplied scope, contradicted under supplied scope, unresolved, not assessed |
| Evidence basis | supplied records, local artifact checks, derived results, assumption-bound simulation; retain every material basis |
| Limitations | missing premises, incomplete populations, conflicts, unavailable external validation |

Supporting and contrary evidence may coexist. Preserve both rather than erasing one through summary-state precedence. A decisive contradiction can defeat a scoped requirement without making all other evidence disappear.

### 12.4 Overall claim rule

For an explicit open-evaluation claim, all five conditions are required. A condition cannot be silently marked inapplicable to obtain a pass.

- Any established contradiction to a required condition defeats that scoped claim.
- Any unresolved or unassessed required condition leaves that claim unestablished.
- Support for all five may be reported only as support under the declared scope, supplied evidence, and assessment policy.

No result certifies unrestricted deployment readiness. Narrower claims may have narrower applicable requirements, but they cannot inherit the unrestricted open-evaluation label.

Do not issue an `80% open` score. Strength in one condition cannot compensate for another missing condition. Metadata completion percentages, if later introduced, must remain documentary counts with different labels and no evidentiary promotion.

## 13. Optional Capability F: Finite Resampling Laboratory

This is an isolated mathematical mode. Its inclusion in v0.1 remains a Phase 0 decision.

### 13.1 Exact source model

Let `b_t` be a probability vector over a finite represented state space, and let integer `n >= 1` be a constant sample size. The closed model is:

```text
X_t | b_t ~ Multinomial(n, b_t)
b_(t+1) = X_t / n
D_t = 1 - sum_i(b_ti^2)
E[D_(t+1) | b_t] = (1 - 1/n) D_t
E[D_t] = (1 - 1/n)^t D_0
P(b_(t+1),i = 0 | b_ti) = (1 - b_ti)^n
```

At `t = 0`, return the specified initial state directly, including the `n = 1` case. Under this closed model, a zero-probability state remains absent in later generations. [EC, sections 4.1-4.2, pp. 6-7]

For a fixed external reference `q` on the same space, the paper defines squared error `L_t = ||b_t - q||_2^2` and gives:

```text
E[L_(t+1) | b_t] = L_t + D_t/n
```

This identity is conditional on the stated model. [EC, section 4.3, p. 7]

Distributional reopening uses:

```text
b_(t+1) = R_n((1 - lambda) b_t + lambda r_t)
0 <= lambda <= 1
```

Here `r_t` is a supplied external distribution in the same represented space. The mode cannot certify its real-world independence. Structural reopening requires an explicit change of represented space and an anomaly/revision basis. [EC, sections 4.4-4.5, pp. 7-8]

### 13.2 Required separation and validation

Label analytical expectations, individual simulated paths, and Monte Carlo estimates separately. Expected diversity need not decrease in every sampled trajectory. Do not apply a one-step loss probability as a multi-generation probability without the required derivation.

Record the model assumptions, complete parameters, generator/method identity, seed, trial count, numeric policy, and runtime identity needed for reproducibility. A seed alone is not a cross-version replay contract.

Do not apply the closed-model expectation unchanged to the reopened process. Do not infer a minimum real-world external-input percentage from a chosen `lambda`.

Prefer exact small-case oracles for correctness tests. For `b_0 = (1/2, 1/2)` and `n = 2`, the next-generation count outcomes have probabilities `1/4, 1/2, 1/4`. Their diversity values are `0, 1/2, 0`, so expected diversity is exactly `1/4`.

The simulator must not depend on the auditor's evidence-qualification functions. Its synthetic paths cannot be fed back into an empirical audit as independent deployment evidence.

## 14. Candidate Diagnostics and Forbidden Promotions

Diagnostic IDs are provisional. Freeze them only after the semantic review.

| ID | Candidate finding family | Example evidentiary boundary |
|---|---|---|
| EC101 | Claim or structural-cut disclosure gap | Required scope is missing; the system's actual scope remains unknown |
| EC102 | Shared evaluative lineage or unsupported independence claim | A supplied path shows overlap; actual error correlation remains unmeasured |
| EC103 | External-input qualification or use gap | Received cases lack qualified corrective use within the selected scope |
| EC104 | Structural support/tail change | A declared required class disappears from compatible complete snapshots |
| EC105 | Anomaly preservation or reopening gap | A relevant anomaly lacks the claimed retained record or revision response |
| EC106 | Correction-path, authority, or outcome gap | A claimed effective correction has only a ticket or an attempted action |
| EC107 | Validation-type or currentness gap | A claim lacks the required evidence type, or its declared validity date has passed |
| EC108 | Frame/population comparability or analysis-completion limit | The requested comparison or negative conclusion cannot be completed honestly |

The finding family is separate from evidence strength, severity, and processing status. No universal high/medium/low threshold is authorized.

Every finding should include its claim/frame/snapshot scope, relevant records or paths, rule premises, evidence origin, known conflicts, limitations, and the particular information needed to resolve the gap.

### Mandatory forbidden promotions

The implementation must reject these inference shortcuts:

```text
different identifiers -> independent sources
no discovered common ancestor -> proven independence
shared provider/model family -> measured correlated error
many evaluator components -> many independent checks
human-authored input -> independently grounded correction
new timestamps or new items -> structural reopening
no new class -> demonstrated closure
more classes -> automatically better evaluation
high concentration -> automatically harmful collapse
unclassified cases -> zero contribution without disclosure
missing snapshot -> confirmed support loss
recorded absence -> latent model inability
schema-valid dossier -> authentic evidence
supplied verified label -> independently verified event
correction ticket -> effective correction
five-condition documentation -> unconditional openness certification
simulation result -> observed deployment fact
replay success -> independent confirmation of the original premises
```

## 15. Minimal Hero Fixtures and Independent Expected Results

All initial fixtures must use project-owned synthetic data. They demonstrate software behavior and declared contrasts. They establish no prevalence, market demand, causal model effect, or independent real-world validation.

| Fixture | Purpose | Required outcome |
|---|---|---|
| `shared-lineage` | Different role IDs reuse a documented common ancestry | Preserve the overlap path; reject unsupported independence promotion |
| `unknown-lineage` | Withhold relevant ancestry from the same basic process | Retain known paths; leave missing independence unresolved |
| `growing-catalog` | More items coexist with narrower observed structural support | Report both item expansion and support loss under a compatible frame |
| `anomaly-revision` | Contrast relabeling with a documented anomaly-linked revision | Report revision evidence and validity limits separately; preserve the original anomaly |
| `correction-records` | Compare a declared route, an attempted action, and an outcome-supported record | Distinguish each evidence level without claiming external authentication |
| `narrow-regression` | A finite, accurately scoped regression claim | Preserve its supported narrow value; withhold an unrestricted open-evaluation claim |

An optional seventh example covers the finite resampling laboratory.

### 15.1 Fixed arithmetic for `growing-catalog`

Under the same four-class partition:

```text
Snapshot A: 24 classified items
Class counts: 12, 6, 4, 2
Observed support: 4
SCI = (144 + 36 + 16 + 4) / 576 = 25/72
D = 47/72

Snapshot B: 48 classified items
Class counts: 24, 16, 8, 0
Observed support: 3
SCI = (576 + 256 + 64) / 2304 = 7/18
D = 11/18
```

The fourth class is stipulated to be required in this fixture. Its earlier share is `1/12`; a preregistered rarity threshold can classify it as a tail class. The fixture's declarations establish the expected local interpretation, with no claim about a real benchmark.

Create separate variants for an incomplete snapshot, an unresolved assignment, and a taxonomy split. Those variants must block the unsupported loss/comparison conclusion rather than reuse the base oracle unchanged.

### 15.2 Acceptance tests that matter most

Test population conservation, exact arithmetic, evidence-state preservation, typed graph witnesses, known/unknown ancestry coexistence, incompatible frames, meaningful versus cosmetic revisions, and claim-specific applicability.

Also test that one satisfied condition cannot repair another contradicted condition; that incomplete traversal cannot produce a clean negative result; and that successful import or replay cannot strengthen the evidence class.

Expected outcomes must be specified independently of the function under test. Use fixed tiny graphs, hand-calculated fractions, and explicit documentary contrasts. Do not generate every fixture and every expected result from one production helper.

## 16. Runtime, Reporting, and Packaging

### 16.1 Architecture

Organize the implementation around a few responsibilities: input contracts, typed graph operations, structural accounting, evidence/claim checks, reporting, and the CLI. Keep an optional simulator isolated.

These are responsibilities, not mandatory package counts. Do not create a large empty module tree or placeholder phases before the first useful vertical slice.

### 16.2 Runtime posture

Prefer Python and the standard library for v0.1. Choose supported interpreter and operating-system combinations during Phase 0 and verify them at release. Do not copy another project's compatibility claims without running this product's checks.

Input text, URLs, commands, and credentials remain data. The runtime makes no model calls, network requests, subprocess calls, or environment-variable expansion based on dossier content.

Specify size/depth/count limits, graph-search work limits, and a safe output policy. Reject duplicate JSON keys and non-finite numeric values. Handle integer/floating-point limits explicitly. A resource limit must preserve the difference between established findings and unperformed work.

File-based input must have defined path, link, overwrite, and capture semantics for supported platforms. Reports should include necessary references rather than indiscriminately copying sensitive evidence text. Avoid payload leakage in errors.

### 16.3 Report shape

A report should include:

- Tool/schema/policy identity and captured input identity.
- Selected claims, frames, populations, and comparison scope.
- Separate execution status, available values, and unresolved reasons.
- The five-condition profile where selected.
- Findings with witnesses, premises, and evidence origins.
- Known omissions, remaining questions, and interpretation limits.

JSON and Markdown must represent the same substantive results. Stable ordering and output identity should make comparisons inspectable.

A small run manifest may identify input and method versions. Avoid a second governance system around that manifest.

### 16.4 Replay boundary

A proposed `snapshot`/`replay` workflow may preserve captured inputs, configuration, policy, method version, and output identity. It reproduces the analysis of captured material. It does not independently validate that material.

Byte-identical replay needs an explicit versioned serialization and numeric contract. Unsupported replay versions produce a clear non-result rather than an approximate recreation labeled exact. Packaging should include the runnable fixtures so users do not need a separate checkout just to try the tool.

### 16.5 Candidate CLI

The following is an interface proposal. These commands do not exist yet:

```sh
evaluation-closure demo shared-lineage --output ./first-demo
evaluation-closure validate evaluation.json
evaluation-closure lint evaluation.json --format markdown
evaluation-closure analyze evaluation.json --format markdown
evaluation-closure compare history.json --from baseline --to revision-1
evaluation-closure snapshot evaluation.json --output ./captured-run
evaluation-closure replay ./captured-run
```

If approved separately:

```sh
evaluation-closure simulate resampling.json --output ./simulation-run
```

Define exit semantics before implementation. A valid input, a completed analysis, no detected finding, and an established claim are different statements. Shell success must not be presented as a scientific pass.

## 17. Verification Governance and Complexity Control

Preserve strong semantic, security, and release assurance. Keep governance proportional to the failure modes it protects.

Maintain three distinct layers:

1. **Canonical product regression:** direct tests of the live contracts, calculations, witnesses, evidence rules, and safe I/O.
2. **Release qualification:** source distribution, wheel built from that distribution, clean installation outside the checkout, packaged examples, CLI/API behavior, and the advertised platform matrix.
3. **Historical evidence:** archived records explaining earlier decisions and tests, with no runtime or ordinary-test dependency on replaying the entire project history.

Every proposed new guard, ledger, receipt, signature, or verification stage must name a concrete uncovered failure mode. Prefer extending an existing assertion when it protects that mode adequately.

Do not require full matrix execution for a prose-only edit unless executable examples or a platform-specific claim changed. Conversely, a semantic change requires targeted regression and the affected integration checks even when its code diff is small.

Do not use test counts, module counts, or preserved file counts as substitutes for correctness. Do not make historical byte identity the general definition of a valid improvement. Preserve behavior and evidence meaning while allowing explicit refactoring.

An AI-assisted test suite remains an internal validation instrument. Give high-value examples independent expected results, retain reviewer disagreement, and preserve unexpected external failures as candidates for new tests. [EC, sections 6-7 and 12]

## 18. Work Sequence

### Stage A: Preparation now

**P0-1: Source and authority intake.** Confirm [EC], identify the supplementary versions actually needed, inspect predecessor source maps, and return a compact missing-source list. No repository creation or production implementation.

**P0-2: Semantic inheritance review.** Resolve each selected row in section 5 against exact accepted definitions and behavioral examples. Record what is reused, adapted, locally defined, or deferred. Avoid inventing a universal cross-project ontology.

**P0-3: Minimal executable specification.** Settle the smallest input contract, population rules, evidence states, claim-policy boundary, diagnostics, security limits, and hand-checked hero outcomes. Decide whether the simulator belongs in v0.1. Define a small initial runtime matrix.

**P0-4: Readiness decision.** Return the selected scope, remaining blockers by capability, and a concrete first implementation step. Report either ready for owner approval or deferred with specific missing contracts. Stop for authorization.

These preparation outputs can live in a small design packet. This handoff is the initial packet. Split files only when their maintenance responsibilities justify it.

### Stage B: Implementation after authorization

The proposed sequence below should be refined once P0 is accepted. Each step has a review stop; do not auto-start the next step.

| Step | Coherent delivery | Acceptance focus |
|---|---|---|
| P1-1 | Installable minimal package, strict input admission, and a useful claim-lint vertical slice | Installed CLI/API, inert inputs, explicit documentary limits |
| P1-2 | Structural accounting and compatible snapshot comparison | Exact denominators, unresolved assignments, tail and frame counterexamples |
| P1-3 | Typed evaluation lineage and external-input qualification | Finite witnesses, scoped completeness, no invented independence |
| P1-4 | Anomaly/revision evidence, correction records, and five-condition profiles | Non-compensatory assessment and proper claim applicability |
| P1-5 | Consolidated reports, packaged demos, and approved capture/replay; optional simulator only if included in the accepted scope | JSON/Markdown parity, reproducibility boundaries, independent oracles |
| P1-6 | Release acceptance and user-facing documentation | Wheel from sdist, clean installation, real README runs, supported environments, truthful release claims |

No elaborate private-core-only phase is required by default. Each implementation step should expose a coherent supported behavior while keeping unimplemented capabilities explicit.

A real-data pilot is valuable when appropriately licensed evidence is available. Absence of such a pilot need not block a narrowly described software release, but it blocks empirical effectiveness claims. Never relabel synthetic fixtures as field validation.

### Stage C: Later work, separately authorized

Possible later extensions include adapters for established evaluation exports, richer assignment models, statistically qualified outcome-correlation analysis, broader platform support, and cross-tool interchange. Each needs a specific user case and a separate semantic contract.

Do not schedule a full ecosystem platform as an implied obligation of v0.1.

## 19. Phase 0 Decisions Still Open

Resolve only decisions needed for the chosen first release:

| Decision | Required resolution |
|---|---|
| Source versions | Which full supplementary manuscripts and accepted predecessor revisions govern inherited definitions? |
| Minimal claim policy | Which narrow requirements can v0.1 qualify mechanically, and which require supplied domain review? |
| Input and assignment scope | Single dossier format, primary hard partition, population selection, and supported revision mappings |
| Public result contract | Exact evidence/applicability/execution semantics and permitted overall claim wording |
| Predecessor boundary | Semantic reuse only, or a verified versioned artifact adapter for a selected capability? |
| Simulator | Small standalone mode in v0.1, or companion workflow deferred from implementation? |
| Distribution | Repository/license confirmation, supported runtime matrix, CLI exits, and safe installation/output workflow |

A pending choice should identify its affected capability. Avoid turning unrelated future work into a global blocker.

## 20. Completion Conditions for the Future v0.1

A v0.1 completion claim requires the selected functionality, its negative cases, and installed workflows to work. In particular:

- The product has a coherent first-run path and includes its examples.
- Structural distributions retain their declared classes, membership, and uncertainty.
- Lineage findings carry actual typed witnesses and incomplete frontiers.
- External input, anomaly revision, and correction records retain their different evidentiary meanings.
- The five-condition profile cannot hide an unresolved or contradicted required condition behind a score.
- Narrow regression claims retain their legitimate value.
- Partial execution and unsupported analysis cannot appear as a clean pass.
- Reports state what was calculated, what was supplied, and what remains unverified.
- The source distribution and installed wheel behave as documented in the stated environments.
- No upstream private API, remote model, telemetry, or hidden live data collection is required.
- Public messaging distinguishes software qualification from empirical deployment validation.

Release readiness does not require claiming that every theoretical condition can be established automatically. The useful product boundary includes explicit limits.

## 21. First Instruction to the Receiving Work Session

Use the following as the kickoff instruction:

> Read this handoff and the supplied primary Evaluation Closure paper. Begin P0-1 only. Confirm the authoritative sources available, identify the supplementary manuscripts actually required, and inspect the relevant accepted definitions in Source Integrity Toolkit, Recursive Integrity Toolkit, and StructDet. Return a compact source register, a preliminary inheritance matrix, capability-specific blockers, and the proposed next preparation step. Keep public APIs, private implementation seams, accepted definitions, and unmerged work distinct. Do not create a repository, modify predecessor repositories, write production code, merge PRs, or publish packages. Keep preparation small and stop for owner review.

## 22. Governing Product Rule

**A result is useful only when its structural object, evidence basis, population, assumptions, and limits remain visible.**

This toolkit should make evaluation systems easier to question and correct. Its own successful tests, complete reports, and repeatable outputs must never become a substitute for the independent reality contact described in the paper.
