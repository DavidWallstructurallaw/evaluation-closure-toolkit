# Evaluation Closure Toolkit P0-3 Minimal Executable Specification

**Date:** 2026-10-06, America/Los_Angeles  
**Revision:** P0-4 clarification of open-claim lint output; table rendering corrected  
**Status:** P0-3 design complete for owner review; implementation has not started  
**Authority:** Work Handoff revision 0.1; P0-1 Source Intake; P0-2 Semantic Inheritance Review  
**Target:** independently installable v0.1 offline auditor  
**Contract identifiers proposed for approval:** `ect-dossier/0.1`, `ect-report/0.1`, `ect-core/0.1`, `ect-method/0.1`, `ect-json/0.1`

This specification fixes the input units, supported analyses, evidence rules, result states, interfaces, limits and independent acceptance examples needed to implement the selected product. Its identifiers are ECT-local. They do not claim compatibility with a predecessor's wire format. The engineering decisions are complete enough for P0-4 readiness review. Repository creation, implementation and publication retain their separate authorization boundary.

## 1. Selected product and bounded decisions

| Decision | Selected v0.1 treatment |
|---|---|
| First user value | Inspect a supplied evaluation dossier; explain its reporting gaps, structural distribution, lineage witnesses, external-input records and claim-scoped five-condition profile. |
| Execution | Python standard library, offline, deterministic functions over one UTF-8 JSON dossier. No model calls, benchmark execution, telemetry, plugins or background service. |
| Claims | Two built-in profiles: `narrow_regression` and `open_evaluation`. The caller selects the profile; arbitrary prose is never classified automatically. |
| Structural units | Immutable evaluation item versions, one selected primary hard assignment per item/frame, unweighted counts, explicitly selected revisions. |
| Comparisons | Descriptive catalogs and separately requested fixed matched cohorts; identical frames or documented total bijective relabeling. Split/merge comparisons need fresh item-level assignments under a common frame. |
| Evidence | Documentary qualification under fixed rules plus attributed domain reviews. Missing data, conflicting reviews, supplied declarations and local calculations remain distinct. |
| Runtime integration | Semantic inheritance only. No predecessor runtime dependency, private imports, format adapters or shared package extraction. |
| Simulation | Deferred from ECT v0.1. RIT remains an optional companion. No `simulate` command or simulation-to-evidence conversion. |
| Reproduction | Retain the dossier and rerun the same request with the same contract/tool identity. Deterministic report bytes and a result digest are specified below. Capture archives and a `replay` command are deferred. |
| Outputs | One authoritative JSON report; Markdown renders the same conclusions, denominators, witnesses and limitations. No scalar openness score. |
| Proposed release matrix | CPython 3.12 and 3.13, each on Ubuntu 22.04 x64 and Windows Server 2022 x64. These are four future qualification targets, not compatibility already demonstrated. |
| Owner decisions reserved for P0-4 | Repository/package/command naming and the proposed Apache-2.0 license for original engineering. Theory PDFs and private evidence are excluded from distribution. |

The working distribution and command are `evaluation-closure-toolkit` and `evaluation-closure`; the import package is `evaluation_closure_toolkit`. Availability and owner acceptance must be checked before repository/package creation. No dependency on a license or name decision prevents completion of this specification.

## 2. Wire conventions and admission

### 2.1 Small top-level dossier

Exactly these keys are supported:

| Key | Type and requirement |
|---|---|
| `schema` | Required literal `ect-dossier/0.1`. |
| `id` | Required ID. |
| `analysis_time` | Required UTC timestamp. Caller-declared logical assessment time used for expiry checks. |
| `policy` | Required literal `ect-core/0.1`. |
| `records` | Required array of the typed records in section 3; an empty array is valid. |
| `requests` | Required array of requests in section 4; an empty array is valid for validation only. |

The report identifies `analysis_time` as supplied, and separately identifies captured input bytes. It does not describe this timestamp as the actual execution time or an evidence cutoff. The auditor evaluates the captured dossier retrospectively. Historical reconstruction of what was known at a past release is unsupported. Later-recorded information about earlier events retains both dates and is never backdated.

IDs match `[A-Za-z][A-Za-z0-9_.:-]{0,95}`. Record IDs are globally unique in the dossier. Item `(logical_id,version)` pairs and entity `(kind,logical_id,version)` triples must also be unique; conflicting aliases for an immutable version are rejected. Request IDs are unique in their own namespace. Nested event IDs are unique within their parent record and are referenced as a two-element pair `[record_id,event_id]`. Class IDs are local to their frame. IDs are case-sensitive and are never Unicode-normalized or inferred from display names.

All objects are closed: unrecognized keys, enum values, record types and schema versions are admission errors. The record tables below exhaust their keys, with the common keys added. Lists of IDs are sets with no duplicate members unless explicitly called an ordered list. References must resolve to the specified record type. An unavailable document is represented by an existing evidence record with an access gap; a dangling evidence ID is an input error.

JSON `null`, floating-point/exponent number tokens, non-finite constants, duplicate keys, a BOM, invalid UTF-8 and unpaired Unicode surrogates are rejected. Input JSON integers are limited to the inclusive range `[-9007199254740991,9007199254740991]`; counts and durations have their additional nonnegative constraints. Booleans are never accepted as integers. Decimal measurements can be preserved as evidence text but are not silently parsed into measurements. A rational is `{ "numerator": "signed decimal integer", "denominator": "positive decimal integer" }`; normalize it to lowest terms, positive denominator and `0/1` for zero. Each integer string has at most 32 digits excluding a minus sign. Rational arithmetic is exact.

Timestamps use `YYYY-MM-DDTHH:MM:SSZ`, valid Gregorian dates, no leap seconds or fractional seconds. Windows are half-open `[start,end)` with `start < end`. `valid_until == analysis_time` means expired. The runtime uses no wall-clock default. Event, acquisition, recording and review times remain distinct.

### 2.2 Required structure and optional semantic facts

In the tables, **R** means a syntactically required ordinary field. **F<T>** means an optional semantic fact with the tagged form below. An omitted F field becomes a result gap `missing_field`; it does not invalidate the dossier. This permits a useful report from incomplete records. Lists not marked R or F default to `[]`; no other defaults apply.

```json
{"state":"known","value":"a value of the declared type"}
```

Alternative fact shapes are `{ "state": "unknown|withheld|disputed|absent|not_applicable", "reason": "nonempty text", "evidence_ids": [] }`, where the `state` is one enum value, not the displayed union string. `evidence_ids` is required, possibly empty. `known` has exactly `state,value`. A `disputed` fact can additionally carry `candidates`, an array of the declared value type, to retain competing statements. Other alternatives have no `value` or `candidates` key.

`absent` is an attributed assertion of absence within the owning record's scope. It is never a computed negative merely because a field is absent. `not_applicable` is an assertion requiring a permitted applicability rule; it cannot waive an open-evaluation condition. Known empty lists, missing fields, unknown values and explicit absence remain different outputs.

Every record has R `id,type`. Records other than `entity`, `scope`, `evidence`, and `review` also accept `asserted_by: F<entity ID>`, `recorded_at: F<timestamp>`, `evidence_ids`, and `contrary_ids` (evidence/review IDs). These are attributed premises, not automatic authentication. Documentary record existence is available even when attribution is missing. Common fields never override a more specific rule below.

Strings used as explanatory text must be nonempty, at most 65,536 UTF-8 bytes. The tool tests structured predicates and references. It does not decide the truth, adequacy or equivalence of free text.

## 3. Typed record contract

The following compact field tables are the normative input grammar. Unspecified fields are unavailable in v0.1. A later machine-readable JSON Schema must encode this grammar without changing its semantics.

### 3.1 Identity, scope, claims and structural populations

| `type` | Additional fields |
|---|---|
| `entity` | R `kind: actor\|process\|model\|artifact\|contribution`; R `logical_id: ID`, `version: ID`; `label: F<text>`, `role: F<text>`, `occurred_at: F<timestamp>`. An entity record identifies one version. Different IDs do not establish independence. |
| `scope` | R `process_id` (process entity); `claim_id` (optional claim ID), `frame_id` (optional frame ID); `snapshot_ids`; `window: F<{start,end}>`; `role: F<text>`; `dimension: F<acquisition\|analytical_method\|model_ancestry\|evaluation_rubric\|organizational_control>`. |
| `claim` | R `scope_id`, `profile: narrow_regression\|open_evaluation`; `statement`, `intended_use`, `horizon` as F<text>; `frame_id: F<frame ID>`; `requirements: F<set of feature codes>`; `validation_kind: F<execution\|proof\|observation\|human_consequence>`; `valid_until: F<timestamp>`; `disclosures` (optional object of R01 through R10, each F<list of record IDs>); `capacity_extent: F<tested_route\|sustained>`. |
| `frame` | `task`, `context`, `horizon`, `resolution`, `exclusions`, `validity_rubric`, `admission_policy`, `selection_policy` as F<text>; `features: F<set of feature codes>`; `classes: F<list of {id,definition}>`; `tail_designations: F<list of {class_id,rationale,severity,rarity_basis}>`. Class definitions/rationale/severity/rarity_basis are text. Class IDs are unique. Empty tail list is permitted but not automatically adequate. |
| `item` | R `logical_id: ID`, `version: ID`; `body: F<text>`; `contribution_ids` (contribution entities). The item's record ID is its immutable item-version reference. |
| `assignment` | R `item_id`, `frame_id`; `class_id: F<class ID>`, `decision: F<admitted\|unclassified\|provisional\|disputed\|withheld>`, `basis: F<text>`, `supersedes: F<assignment ID>`. A superseded record remains present. |
| `validity` | R `item_id`, `frame_id`; `verdict: F<valid\|invalid\|unresolved>`, `rubric: F<text>`, `basis: F<text>`. This is item validity, never model answer success. |
| `snapshot` | R `frame_id`, `members` (item IDs); `membership: F<complete\|partial\|unknown>`; `selection_policy: F<text>`; `assignments` (list of `{item_id,assignment_id}`); `validities` (list of `{item_id,validity_id}`); `excluded` (list of `{item_id,reason}`); `observed_at: F<timestamp>`; `tail_results: F<list of {class_id,evidence_ids}>`. |

Feature codes are `single_turn`, `persistent_state`, `long_horizon`, `recovery`, `override`, `human_consequence`, `field_use`. They are coarse declared dimensions, with domain meaning preserved in the frame and reviews. A complete known `features` list that omits a claim-required feature supplies a structured scope mismatch; missing/unknown lists supply a gap. No implication such as `long_horizon -> recovery` is invented.

A claim-linked scope must point back to that claim; optional scope frame/snapshot references must agree with the request and claim when present. Scope identity is exact: v0.1 does not automatically widen, intersect or treat one scope as equivalent to another. A review for another scope remains visible but cannot qualify the selected inquiry. The time window required for a capability must be known; an unknown window preserves an unresolved result.

Every selected membership is unique. A snapshot selects at most one version of each logical item, and its `excluded` list is disjoint from `members`. Real variants require separate logical identities and supplied lineage. Assignment and validity selection tables have at most one row per selected item, with the referenced item/frame matching the row and snapshot. Conflicting candidate records may exist outside the selection. The runtime never chooses the latest record or treats an assignment revision as a new item.

An assignment counts as admitted only when its selected decision is known `admitted`, class belongs to the known frame roster, basis and asserted_by are known, body is known, and no unresolved explicit contrary reference targets that admission. The basis may be a supplied classification method or human review; the result remains conditional on it. An unresolved contrary admission can be resolved only by a qualified `assignment_resolution` review selecting that exact record. No automatic classifier or content-deduplication step exists. A missing class roster blocks all distribution calculations, while preserving membership counts.

### 3.2 Evidence and scoped reviews

| `type` | Additional fields |
|---|---|
| `evidence` | R `scope_id`; `kind: F<declaration\|document\|execution_record\|observation_record\|human_consequence_record\|intervention_record\|proof_record\|analysis_record\|process_record\|simulation_record>`; `producer_id: F<entity ID>`; `occurred_at`, `recorded_at` as F<timestamp>; `access: F<supplied\|referenced_only\|withheld\|unavailable>`; `content: F<text>`, `locator: F<text>`; `subject_ids`, `origin_ids`, `transformation_ids`, `contrary_ids`; `uncertainty: F<text>`. Locators are inert. |
| `review` | R `target_id` (any record), `criterion: criterion code`, `scope_id`; optional ordinary `member_id` (cohort member), `target_event_id` (nested correction outcome ID), `request_id` (comparison request ID), `disclosure_id` (R01-R10); `disclosure_ids` (R01-R10 list); `assessor_id: F<actor entity ID>`; `reviewed_at: F<timestamp>`, `method: F<text>`, `rationale: F<text>`; `verdict: F<supports\|contradicts\|unresolved>`; `evidence_ids`, `contrary_ids`, `resolves` (review/evidence IDs); `decisive: F<boolean>`; `counterexample_ids` (record IDs). |

Criterion codes are exactly the fourteen gate criteria in section 5.3, plus `claim_validation`, `assignment_resolution`, `frame_equivalence`, `matching_basis`, `independence`, `externality`, `input_qualification`, `retention`, `correction_outcome`, `structural_revision`, and `applicability`. Gate/claim reviews target the claim. The remaining criteria target, respectively: assignment; revision; a comparison's scope record; independence record; external cohort; external cohort; external cohort; correction case; revision; claim. `externality`, `input_qualification` and `retention` require `member_id`; `correction_outcome` requires `target_event_id`; `matching_basis` requires `request_id`; `applicability` requires `disclosure_id`. These linkage keys are forbidden on other criteria. Only `claim_validation` and `validation_type_fit` may carry `disclosure_ids`; they explicitly enumerate the reporting rows examined. All linkage references must resolve and agree with the selected cohort/case/request. Matching-basis qualification binds the exact pair roster in that request, never a pair list inferred from prose.

A review qualifies documentarily only if its target, criterion and exact scope match; its assessor, time, method, rationale and definite verdict are known; its relevant evidence list is nonempty; and its linked evidence records have known producer, scope, supplied content and one of `document`, `execution_record`, `observation_record`, `human_consequence_record`, `intervention_record`, `proof_record`, `analysis_record`, or `process_record`. All evidence the review names as support must have `access=supplied`, known content and matching scope. Section 5.1 and the event/outcome rules impose additional evidence-kind requirements for particular witnesses. Any access gap blocks that review's qualification, without erasing the declaration. `declaration` and `simulation_record` can be retained as context but cannot discharge these review-support requirements. Merely adding an evidence-type label supplies no authentication.

Protected underlying material may remain withheld. A supplied inspection receipt can support the narrower statement that a named assessor reported an inspection, provided it carries the required review basis. It cannot satisfy a predicate requiring the underlying content itself. In v0.1 the gate predicates below accept supplied reviews and scoped receipts as documentary premises, with an explicit protected-evidence limitation, and never label that material independently checked. A pointer alone never qualifies.

The toolkit considers every review matching target/criterion/scope, rather than selecting a convenient latest review. Exact conflict handling is defined in section 5.2. Incomplete and wrong-scope reviews are reported with reasons.

### 3.3 Typed lineage and external contact

| `type` | Additional fields |
|---|---|
| `relation` | R `scope_id`, `from_id`, `to_id` (entity or item IDs), `kind` from the relation table below; `occurred_at: F<timestamp>`, `role: F<text>`. Direction follows the table. |
| `frontier` | R `scope_id`, `node_id` (entity or item), `view: acquisition\|model_ancestry\|evaluation_rubric\|recursive_reuse`; `reason: F<unknown\|withheld\|missing_record\|disputed>`. |
| `independence` | R `scope_id`, `members` (at least two entity/item IDs), `form: pairwise\|setwise`, `dimension` from the five scope dimensions; `unexamined_dimensions` (same enum); `method: F<text>`. Pairwise records have exactly two members. Qualification requires an exact `independence` review; the record is retained without one. |
| `external_cohort` | R `scope_id`, `members` (contribution entities); `membership: F<complete\|partial\|unknown>`, `boundary: F<text>`, `checkpoint: F<text>`, `purpose: F<text>`; `externality_reviews`, `qualifications` (each list of `{member_id,review_id}`); `carryover_ids` (member IDs). |
| `external_event` | R `scope_id`, `cohort_id`, `member_id`, `stage: received\|retained\|selected\|used`; `verdict: F<yes\|no\|unknown>`; `occurred_at: F<timestamp>`, `checkpoint: F<text>`, `purpose: F<text>`, `target_id: F<entity or item ID>`, `representation: F<text>`. Each event is independently attributed through the common fields. |

Each `externality_reviews` row selects a member-specific `externality` review. Each `qualifications` row separately selects `input_qualification`, assessing suitability for the cohort's known purpose and claim scope. Both target that cohort with the identical member_id, and their support evidence includes that member in subject_ids. External origin cannot automatically qualify a contribution for its intended use. Relevant opposing reviews for the same member/criterion are still considered; one member's conflict cannot silently apply to another. Different use purposes require distinct cohorts/scopes. No cohort member can be an unknown fabricated ID; partial membership describes known members of a larger unknown population.

| Relation kind | `from_id -> to_id` meaning | Traversal view |
|---|---|---|
| `derived_from` | derived item/artifact/contribution -> its source | `acquisition` |
| `acquired_from` | contribution/item/artifact -> acquisition source | `acquisition` |
| `trained_on` | model version -> training item/artifact/model source | `model_ancestry` |
| `exposed_to` | model version -> exposure item/artifact | `model_ancestry` |
| `rubric_from`, `reference_from` | rubric/reference contribution or artifact -> its source | `evaluation_rubric` |
| `produced_by` | output item/artifact/contribution -> producing process | `recursive_reuse` |
| `uses_generation`, `uses_training`, `uses_selection`, `uses_reference`, `uses_judgment` | consuming process -> prior artifact/item/contribution/model | `recursive_reuse` |
| `semantic_influence` | affected process or contribution -> influencing contribution | Inventory only |
| `evaluated_by` | evaluated model/item -> judge entity | Inventory only |

Endpoint type constraints in this table are admission rules. A view traverses only its listed edge kinds. Roles remain scoped. There is no mixed-edge generic ancestry view. Common organizational control and shared analytical method are supplied assessments; ownership/citation labels never become acquisition edges.

### 3.4 Anomalies, revisions and corrections

| `type` | Additional fields |
|---|---|
| `anomaly` | R `scope_id`, `frame_id`; `record: F<evidence ID>`, `context: F<text>`, `distinction: F<text>`, `disposition: F<unresolved\|investigated_no_change\|recut\|claim_restricted>`; `revision_ids`, `case_ids`. |
| `revision` | R `scope_id`, `from_frame`, `to_frame`; `kind: F<relabel\|recut>`; `anomaly_ids`; `changed_distinction: F<text>`; `class_map` (list of `{from_class,to_class}`); `incorporation_evidence_ids`; `new_assignment_ids`. Splits/merges may have multiple mapping rows; they do not authorize count projection. |
| `correction_case` | R `scope_id`, `claim_id`; `issue: F<text>`, `context: F<production\|drill>`, `objective: F<repair\|restrict\|replace_evaluator\|withdraw>`; `route: F<{actor_id,target_id,procedure,evidence_ids}>`; `authority: F<{actor_id,target_id,start,end,evidence_ids}>`; `handling`, `attempts`, `actions`, `outcomes` as nested arrays below. |

All nested correction entries require `id` and `evidence_ids`; optional semantic fields use F. A handling entry has `state: F<submitted|accepted|rejected>` and `occurred_at`. An attempt has `actor_id`, `target_id`, `occurred_at` as F. An action has R `attempt_id`; `kind: F<repair|restrict|replace_evaluator|withdraw>`, `target_id`, `occurred_at`, `resulting_state` as F (entity ID, timestamp, text). An outcome has R `action_id`; `criterion`, `protocol`, `horizon` as F<text>, `assessed_at: F<timestamp>`, `baseline: F<evidence ID>`, `result: F<effective|ineffective|unresolved>`, `review_id: F<review ID>`, and `contrary_ids`. Action/attempt IDs resolve within that case. A restriction/removal may describe its resulting state without inventing a replacement artifact.

`route.procedure` is text, other route fields are references. Authority start/end form a half-open window and must cover the actor, action target and action time when authorization is assessed. The runtime does not test whether a declared institution actually grants powers. Unknown authority leaves the outcome assertion visible and prevents a route-authority support conclusion.

A correction-outcome review targets the case and binds the outcome through `target_event_id`; the outcome's `action_id` supplies its exact action. Each outcome's `review_id` must agree with that target. No linkage is parsed from evidence prose. Conflicts are compared within that same case/outcome/scope. All other outcomes remain visible without being treated as contradictions merely because their objectives differ. Route/authority/attempt/action targets are entity, item or claim IDs, with the same target required for a claimed authorized action. Known attempt/action/outcome times must be in order; a reverse order yields a chronology gap, and unknown times cannot establish a time-bounded authority or remedy conclusion. Sustained-capacity support additionally needs the fixed gate review in section 5.3 and a supplied history receipt covering the declared horizon.

## 4. Requests and minimal public interfaces

Every request has R `id,operation,scope_id`. All referenced claims/snapshots/entities must exist. Optional selection lists default to the stated deterministic scope, never to a latest version. Duplicate before or after endpoints in a matched pair roster are admission errors. An endpoint that exists but is outside the selected snapshot is an analytical prerequisite gap, preserving the intended pair.

| `operation` | Additional keys and behavior |
|---|---|
| `lint` | R `claim_id`. Run the ten disclosure checks, structured scope mismatch, claim-validation and expiry checks. |
| `profile` | R `snapshot_id`; `population` optional `selected` (default) or `confirmed_valid`. Always retain the main selected profile when the latter is requested. |
| `compare` | R `before_id,after_id,mode: descriptive\|matched`; `population: selected\|confirmed_valid` defaults selected; optional `revision_id`; `pairs` defaults empty list of `{before_item_id,after_item_id,basis}` with text basis; `pair_membership: F<complete\|partial\|unknown>`. Matched mode requires the pair list and declared membership to establish completeness. |
| `lineage` | R `seed_ids` (two or more entity/item IDs), `view: acquisition\|model_ancestry\|evaluation_rubric\|recursive_reuse`; `independence_ids` defaults all records with exact scope and exact seed-member set. |
| `external` | R `cohort_id`. Compute separate receipt, retention, selection, use and qualification summaries. |
| `cases` | `anomaly_ids`, `revision_ids`, `case_ids` default to all of that type with exact scope. An explicitly empty list selects none. |
| `assess` | R `claim_id`; `conditions` defaults all five condition IDs; `snapshot_id`, `cohort_id` optional; `case_ids`, `anomaly_ids`, `revision_ids` default to all exact-scope records. For open claims all five appear in output even when unselected. |

Condition IDs are `structural_validity`, `external_presence`, `source_integrity`, `tail_retention`, `corrective_capacity`. `assess` evaluates its required structural/external/case prerequisites directly under the same rules; success does not depend on separate requests being run first. A scope's snapshot list must include any selected snapshot, and its frame must agree when known. A narrow claim's `assess` result reports claim validation and justified applicability; it never receives an open-evaluation summary.

The first release has only three command families:

```sh
evaluation-closure validate dossier.json
evaluation-closure analyze dossier.json --request lint-main --format markdown
evaluation-closure analyze dossier.json --format json --output report.json
evaluation-closure demo growing-catalog --format markdown
```

`validate` checks complete syntactic/reference admission and emits an admission report. `analyze` runs all requests when `--request` is omitted; repeatable `--request ID` selects exact requests with no duplicates. Selecting more than 16, including by default from a larger valid dossier, is `USAGE_SELECTION_LIMIT`, exit 2; the dossier can still pass validate. An explicit selection of at most 16 is required to analyze it. Selecting zero is `USAGE_NO_REQUESTS`, exit 2; the bytes API raises RequestError for either selection error. `--format` is `json` by default or `markdown`. `--output` is one explicit new file, otherwise stdout. `demo NAME` loads an installed synthetic fixture and analyzes its packaged requests through the same byte API, without writing a dossier or creating a directory. Unknown names/flags/requests are usage errors. `--help` and `--version` perform no dossier analysis. There are no aliases for deferred commands.

Public Python interface, proposed signatures:

```python
validate_bytes(data: bytes) -> dict
analyze_bytes(data: bytes, *, request_ids: tuple[str, ...] | None = None) -> dict
render_markdown(report: dict) -> str
```

The byte functions share the strict decoder and never mutate caller data or read paths. `validate_bytes` returns the admission envelope even for invalid input. `analyze_bytes` likewise returns an admission-error envelope rather than executing on invalid data. Unknown requested IDs raise a documented `RequestError`; resource-limited valid analyses return partial results. `render_markdown` accepts only the current generated report schema and raises `ReportError` for invalid reports. Unexpected implementation errors propagate as `InternalError` at the public boundary and exit 1 at the CLI, with no stack trace by default. No public mutable domain-object framework is required.

## 5. Fixed claim policy and evidence aggregation

### 5.1 Reporting, validation type and currentness

For each disclosure emit separate `presence`, `well_formed`, `linked`, and `qualification` results. A supplied list of IDs can establish presence/linking without establishing adequacy. Applicable missing disclosures are gaps. Empty lists do not establish completeness except when a qualified applicability review establishes the permitted empty scope.

| ID | Required disclosure | Open claim | Narrow regression |
|---|---|---|---|
| R01 | Claim, intended use, horizon and excluded scope | Required | Required |
| R02 | Frame, represented and omitted conditions | Required | Required |
| R03 | Item origin and transformation lineage | Required | Required within the finite test scope |
| R04 | Exposure/contamination controls | Required | Required as a declaration; adequacy scoped to the claim |
| R05 | Evaluator identity, relationships, bias controls | Required | Required for the declared evaluator |
| R06 | Structural profile, rare/severe designations and results | Required | Required where structural-coverage claims are made; otherwise explicit applicability review |
| R07 | Persistent state, horizon, recovery, override | Required for declared corresponding features | Required only for selected corresponding features |
| R08 | Field/human-consequence evidence | Required for `field_use` or `human_consequence`; external contact still separately required | Required only for those selected features |
| R09 | Failure-triggered correction route | Required | Document route or a qualified finite-scope applicability rationale |
| R10 | Validity date and currentness limits | Required | Required |

A disclosure maps to fixed typed anchors: R01 claim fields, R02 frame, R03 item/relation/evidence, R04 evidence/review, R05 entities/relations/reviews, R06 snapshot/frame/evidence, R07 and R08 evidence/review, R09 correction cases, R10 `valid_until` plus a disclosure explanation record. Merely referencing the claim itself does not discharge every row. R01/R02/R10 require their corresponding known fields as well as documentary links. R07 relevance is determined from the structured claim requirements; if requirements are unknown, applicability is unresolved. R06 on a narrow claim is applicable when its disclosure is a known nonempty list of structural anchors; otherwise a qualified row-specific applicability review is required for exclusion. Prose is not mined for claims.

Per disclosure, presence is `present|missing|unknown|withheld|disputed|explicit_absence`; well_formed is `yes|no|unresolved`; linked is `yes|no|unresolved`; qualification uses the criterion assessment enum. Known correctly typed nonempty anchors establish presence/well-formed/linking, including references whose underlying evidence remains unavailable. Qualification additionally requires a qualified supporting claim_validation review for narrow claims, or validation_type_fit review for open claims, whose disclosure_ids includes that exact row and whose scope matches. Its typed anchor requirements must also be satisfied and all relevant contrary records examined. An empty supplied list is well-formed but unlinked. Permitted not-applicable rows retain the assertion in applicability, with assessment not_assessed, and need a qualified applicability review with the exact disclosure_id. That review's `supports` verdict supports exclusion only for rows the table permits; it cannot waive required rows or five gates. Missing/unknown requirements cannot be waived through prose.

`narrow_regression` requires known finite intended scope/frame, no open-evaluation summary, a declared execution-validation basis, and a qualified `claim_validation` review supported by supplied execution receipts. Other validation kinds are retained with `unsupported_validation_kind`: lint completes with an unresolved validation conclusion and exit 0, because the checker has successfully identified its scientific-scope limit. This differs from an unimplemented operation, which is not_run and exit 3. A broader proof/observation claim profile can be added later. `open_evaluation` requires a known validation kind and type-appropriate supplied evidence: execution_record, proof_record, observation_record, or human_consequence_record respectively, with a qualified `validation_type_fit` review. Claims with `human_consequence` require human_consequence_record evidence even when another main validation kind is selected. Evidence type is an attributed premise, never proof of actual execution.

Currentness is `current_under_declared_date`, `expired_under_declared_date`, or `unestablished`. Expiry qualifies only the supplied date, no universal shelf life is invented. Both built-in profiles assess current support at `analysis_time`; an expired date prevents that affirmative conclusion. Earlier scoped results remain available. Missing expiry does not prove ineffectiveness or closure.

For narrow regression, `values.claim_conclusion` is `defeated_under_scope` when a decisive structured mismatch or qualifying counterexample defeats its finite claim. Otherwise it is `supported_under_scope` only when the required known fields, applicable R01-R10 disclosures, type-appropriate claim_validation review and currentness checks all qualify, with no unresolved contrary premise and completed execution. Otherwise completed or partial analysis gives `unestablished`; unperformed analysis gives `not_assessed`. A narrower claim never acquires the five-condition conclusion through this rule.

For an open-evaluation claim, `lint` never executes the five-condition assessment and cannot emit `supported_under_scope` as claim_conclusion. A decisive scoped contradiction gives `defeated_under_scope`; otherwise performed lint gives `unestablished`, even when all disclosures are complete. Unperformed lint gives `not_assessed`. Affirmative five-condition support is available only through the separately implemented `assess` operation. This rule applies in P1-1 and remains in force after assess is implemented.

### 5.2 Review conflicts and aggregation

Each criterion returns documentary completeness separately from semantic assessment. A `supports` label with complete fields cannot discharge the special witness requirements in section 5.3.

For one target/criterion/scope:

1. Retain every matching declaration, supporting/contrary reference and qualification gap, grouped by exact target/criterion/scope and any member/outcome/disclosure/request binding.
2. Apply qualified explicit resolutions before aggregating active verdicts. A resolving review has the same binding, known rationale and qualifying evidence, and names the exact review/evidence IDs in resolves. A resolution cannot resolve itself or its own supporting evidence. Evaluate the acyclic resolution dependency graph from unchallenged leaves; any cycle, conflicting resolution or unresolved premise leaves the affected records active and disputed. Resolved records remain in output as historical contrary basis. A mere general favorable review does not resolve a concrete counterexample.
3. An active documentary-qualified contradicts review is decisive under supplied scope only when decisive=true, counterexample_ids is nonempty, and the reviewed counterexample addresses the exact criterion/scope. Its premise must have no unresolved explicit dispute. That substantive judgment remains attributed. Fixed local counterexamples include a required feature absent from a known complete feature set or a required class absent from a complete selected population. A prose review cannot override unchanged arithmetic or unchanged structured features; correcting those requires selecting corrected records.
4. Any active decisive contradiction gives contradicted_under_scope. Preserve known support and partial execution. Otherwise active contrary/unresolved reviews, unresolved contrary references or unsupported competing assertions block support with disputed.
5. If all required typed witnesses are present, at least one support review qualifies where required, all material contrary records are resolved, and the requested review set was completely examined, return supported_under_scope.
6. Otherwise return unresolved; a criterion not selected or never executed is not_assessed.

All scoped support remains conditional on supplied premises and domain judgments. Record ordering, recency and assessor identity do not break ties. A supplied authority label does not independently authenticate that authority. The runtime cannot adjudicate arbitrary text disputes.

### 5.3 Five non-waivable condition predicates

Each row lists all required criterion codes. For `open_evaluation`, every row is applicable. Gate-level support requires all of its criteria supported, complete evaluation of relevant opposing records, and currentness established. A qualified decisive contradiction defeats the scoped gate. Otherwise an unresolved/unassessed criterion prevents support. The same supplied review may not silently substitute for another criterion; separate review records may reference the same evidence and retain that common basis.

| Gate and criterion codes | Required typed witnesses plus supplied judgment |
|---|---|
| Structural validity: `frame_target_fidelity`, `anomaly_accountability` | Known frame task/context/horizon/resolution/exclusions/class definitions and claim requirements; no unresolved structured scope mismatch. Exact claim-scoped fidelity review connecting the frame to the target. All known relevant anomalies retain original or authorized redacted evidence, disposition and contrary records. Accountability review explicitly covers the captured anomaly inventory, including a declared empty inventory; missing anomaly records never prove no real anomalies. |
| External presence: `outside_process_contact`, `claim_relevance`, `recorded_use` | Nonempty selected contribution cohort with a known boundary, purpose and time window. At least one member has separate qualifying externality and input_qualification reviews, a within-window contact/receipt event and a within-window relevant use event with matching purpose and exact target. Gate reviews establish boundary/contact interpretation and relevance to the claim. Receipt/use are independent facts; neither is inferred from the other. Carried-over ancestry alone cannot satisfy current-window contact. |
| Source integrity: `provenance_transformations`, `validation_type_fit`, `evaluator_relationships` | Scoped origin/transformation inventory and epistemic evidence types, qualified claim-type validation records, and a supplied review of evaluator roles and selected dependency dimensions. Reviews must address relevant ancestry gaps and contrary records, and state unexamined dimensions. No universal complete-hidden-ancestry proof or automatic independence requirement is imposed. A supplied specific independence claim must separately qualify for its exact members and dimension. |
| Tail retention: `tail_designation_adequacy`, `tail_representation`, `tail_result_visibility` | Known task-relevant tail list with rationale, separate severity/rarity basis and qualified adequacy review; complete selected roster and admitted assignments; each designated class has at least one admitted item and a supplied scoped result receipt (including model failures). Reviews qualify relevance and interpretation. Empty designations require an explicit qualified adequacy review explaining why no tail obligation exists in this finite target; representation/visibility then return supported only for that bounded empty obligation, never universal absence of tails. An empty selected population cannot support retention. |
| Corrective capacity: `route_and_authority`, `route_operability`, `capacity_extent` | Declared route with relevant actor/target authority, at least one documented linked attempt and action under that authority, and a scoped operability review. A drill can support a tested route but remains labeled drill. `capacity_extent=tested_route` supports only that bounded capacity; `sustained` additionally requires a supplied dated history receipt, outcome records and a review explicitly covering the declared horizon and objectives. One successful action cannot independently satisfy sustained capacity. |

The gate schema has **fourteen** criterion codes: 2 + 3 + 3 + 3 + 3. Every listed criterion needs its exact scoped review as well as the typed witnesses, except the mechanical counterexamples which can defeat a criterion directly. A material evidence-access gap, unknown event time, incomplete relevant cohort, unresolved contrary record or unfinished required check leaves its dependent criterion unresolved. Partial external-cohort membership does not erase a known positive contact/use witness, but the gate review must explicitly limit its claim to those members; broader complete-cohort assertions remain unresolved.

`assess` scope includes exactly one selected snapshot and one external cohort when these are required. Unknown/no selection gives a named gap. Source-integrity and structural-validity reviews may support bounded judgments while retaining known limitations, provided those limitations do not contradict the selected requirement. The report shows those limits beside the conclusion; it cannot suppress an unresolved required criterion through a general favorable review.

### 5.4 Overall claim rule

For open-evaluation output retain exactly five condition entries:

Affirmative overall support additionally requires known claim statement, intended_use, horizon, frame_id, requirements and validation_kind; a known required scope window; and consistent selected claim/frame/snapshot/cohort references. Missing semantic facts remain valid input and leave the claim unestablished. Reviews attached to an otherwise unnamed or unscoped claim cannot manufacture these prerequisites. A decisive independent counterexample may still defeat the scoped portion actually established by its premises.

- Any condition with a decisive scoped contradiction gives overall `defeated_under_scope`.
- Otherwise all five supported, currentness established and all required execution completed gives `supported_under_scope`.
- Otherwise at least one condition assessed gives `unestablished`.
- If none were assessed, give `not_assessed`.

The permitted affirmative wording is: **“Supported under the declared scope, supplied evidence and ect-core/0.1 policy.”** List the actual scope and limitations immediately with it. No `pass`, certification, 80% openness, truth score, independent-validator estimate, or deployment authorization is produced. A narrow regression result uses the same scoped-evidence wording for its finite claim and carries `open_evaluation: not_applicable`.

## 6. Structural algorithms and comparison contract

### 6.1 Selected and confirmed-valid populations

Let K be the count of explicitly supplied selected members. Only known `membership=complete` establishes N=K as a supplied premise. A reported total or an incomplete roster cannot establish full N. With known N, each member enters admitted A or non-admitted U exactly once: `N=A+U`. Emit per-item reasons and reason counts; multiple reasons may overlap, so reason totals are not represented as a second partition. Primary reason precedence is `disputed`, `withheld`, `body_unavailable`, `missing_record`, `provisional`, `unclassified`, `unresolved`. A member with a known body but unknown class remains unresolved, not a structural class called unknown.

For admitted class counts c_i with A>0:

`SCI = sum(c_i*c_i)/(A*A)`; `D = 1-SCI`; `observed_support = count(c_i>0)`; `assignment_coverage = A/N` for known N>0.

Every declared class appears, including zero counts. These metrics are conditional on admitted assignments. Unknown full membership gives a labeled known-subset profile over K, with full N, full coverage and full-snapshot distribution unavailable. No guessed denominator or hidden mass is supplied.

For a known empty roster: N=A=U=0, support=0, SCI/D/coverage are `undefined`. For N>0,A=0: coverage=0, admitted support=0, SCI/D undefined; absence of a class in the full population remains unestablished. A nonempty single-class population has SCI=1,D=0. No unavailable/undefined metric contains a numeric zero placeholder.

`confirmed_valid` selects only members with a selected known `valid` validity record, known asserted_by/basis and an exactly matching declared rubric. The same attribution/basis/rubric/no-unresolved-contrary rule qualifies a known `invalid` decision for validity coverage. Unqualified invalid declarations stay unresolved and cannot inflate that coverage. Invalid, unresolved, missing and disputed validity states are counted separately on the original roster. Emit validity coverage (qualified decided valid or invalid divided by known N), confirmed-valid size V, and structural assignment coverage within V. Preserve the selected-population profile alongside it. Unknown validity blocks a statement that all truly valid items are enumerated; it does not change the arithmetic of the named confirmed-valid subset. Any explicit unresolved contrary reference blocks admission of the validity decision. No model outcome field filters item membership.

### 6.2 Descriptive and matched comparisons

Direct descriptive comparison requires known compatible frame, task/context/horizon/resolution/exclusions, selection policy and admission policy, the same population view and validity rubric where applicable, and complete selected rosters. Policies must match exact strings; no synonym inference occurs. Different item counts are allowed. Incomplete assignments permit a labeled admitted-subset metric delta, explicitly conditional on each side's different admitted denominator; full-population absence/loss remains blocked. Unknown full membership produces side-by-side known-subset inventories with the primary full-snapshot delta unavailable. No automatic switch to a different requested population.

Matched mode additionally requires known complete fixed pairs, each endpoint used once on its side, a nonempty matching basis per pair, and either identical logical identity across versions or a qualified matching-basis review covering the exact roster. All endpoints must belong to their selected snapshots and have admitted assignments on both sides under the common frame. A pair endpoint can be present in the dossier yet missing from a snapshot; that makes the matched request unavailable, preserving the planned pair. Dangling IDs are admission errors. Unknown counterparts must be represented as an incomplete pair roster, never fabricated IDs.

Let P be the fixed complete pair count. Primary matched metrics use P on both sides, with no silent complete-case deletion. A missing assignment, missing membership or unjustified pair blocks the requested contrast. With `population=confirmed_valid`, every endpoint must independently satisfy the confirmed-valid admission rule; invalid or unresolved validity blocks the requested fixed-cohort contrast, with no endpoint deletion. An empty complete pair roster yields support 0 and undefined SCI/D/deltas. Full-catalog metrics, if requested separately, retain their own denominators. Equal counts never establish matching.

Across different frame IDs, direct contrast requires a selected revision of kind `relabel`, a total one-to-one class map covering all classes including zero-count tails, and qualified `frame_equivalence` review covering all compatibility fields. A syntactic bijection alone establishes no semantic equivalence. A recut/split/merge yields side-by-side profiles and `incompatible_frame` for direct deltas. It can be compared only through separate snapshots selecting item-level assignments under a common frame. Reannotation adds zero items; support gains under a recut do not establish improved fidelity, new observations or model recovery.

### 6.3 Tail findings and revisions

Tail designation is supplied before the evaluated retention assertion and names the exact class/frame/rationale. v0.1 does not infer a universal rarity cutoff. Severity, rarity, representation and model performance remain separate.

A positive admitted count establishes presence in that admitted population despite incomplete coverage elsewhere. A zero count means zero admitted sightings. Complete-snapshot absence requires known complete membership, A=N and compatible meaning. An empty known selected population can yield `absent_in_empty_population`, which cannot support retention or model incapacity. A loss requires positive baseline presence, complete membership/assignments on both sides and zero target count. A missing snapshot cannot become a zero. Confirmed-valid subset absence never stands for whole-snapshot absence.

Revision inspection returns three independent conclusions: revision documented; revision incorporated; improvement in fidelity supported under supplied review. Original anomaly evidence, changed distinction, old/new frames, adjudication and incorporation are required for the respective positive claims. Renaming alone has no recut witness. Investigated-no-change and fresh cases entering a stable adequate frame remain valid recorded outcomes. No-new-class count alone produces no closure finding.

Every result carries its dependency IDs. Selecting a corrected assignment/review recomputes affected results on rerun. There is no mutable cache or historical migration engine; old records remain addressable. A correction does not invalidate unrelated claims by proximity.

## 7. Lineage, external events and correction algorithms

### 7.1 Bounded typed graph analysis

Build only the exact-scope selected view; preserve each relation's declaration basis. Traverse seed and adjacency IDs in lexicographic order with iterative breadth-first search and a visited set. Retain the lexicographically first shortest witness path per reached node per seed. Cycles terminate safely and appear as a graph property only. A common reached node supplies an overlap witness with both paths. Parentless nodes are captured terminals, never automatically qualified origins.

Report frontier records and nodes with no supplied continuation separately. A completed search can state `no_witness_in_captured_view`. It cannot state independence or absence of hidden ancestry. Missing/withheld ancestry can coexist with a known shared witness. No hidden-root bound, independent-validator count or error covariance follows.

For recursive reuse, an admissible witness is a later process B using an earlier output artifact/item X, with X `produced_by` process A and known A-before-B timestamps (from entity occurrence times and use event times). The use kind must name generation, training, selection, reference or judgment. A supplied version order without relevant times remains an unresolved chronology in this v0.1 rule. Such an acyclic path can show recorded recursive reuse; a static cycle alone cannot. All roles/process versions remain visible.

Independence assessment output preserves each exact member set, form, dimension, reviewer method, unexamined dimensions, support and contrary evidence. An acquisition assessment cannot answer model ancestry. a/b and b/c assessments do not produce a/c or a/b/c. Distinct providers and no overlap path do not qualify an independence review.

### 7.2 External cohort accounting

For each known member and each stage, collect exact-scope/checkpoint qualifying event records. A qualifying event has a known yes/no verdict, actual event time inside the scope window, known attribution and supplied scoped process_record, observation_record or intervention_record evidence. `used` additionally requires known purpose and exact target; `retained` requires known representation and a matching qualified retention review with that exact member_id. `selected=no` means excluded for that stated use. `received=no` needs an explicit scoped record; missing logs stay unknown.

For each event axis, output member states `yes`, `no`, `disputed`, `unresolved`, counts in each state and independent raw event count. Conflicting yes/no events at the same checkpoint remain disputed in v0.1; event-level adjudication is deferred. Multiple events describing one member do not multiply member counts. Stages are not assumed monotone. Documented use can survive missing receipt logs or missing use qualification; it does not then establish qualified current-window contact for the stronger gate.

Externality and use qualification are two additional separate axes. Each yields supported_under_scope, contradicted_under_scope or unresolved through its own member-bound review, with all supporting/contrary basis retained. Missing qualification never deletes a documented event. Carryover identifies older grounding and cannot create a new receipt/contact. Unknown full cohort membership gives known-subset counts only. No cross-cohort ratio, presence score, causal effect estimate or simulation lambda is computed.

### 7.3 Cases and outcomes

Output route, authority, handling, attempt, action, objective-specific outcome, and claimed capacity extent separately. A ticket's acceptance does not supply an attempt. A newer version without an exact case-linked action supplies no remedy witness. Count unique case/target pairs separately from events.

Outcome support requires a known objective, linked action, resulting state, criterion/protocol/horizon/assessment time, supplied evidence and a qualified correction-outcome review. Comparative repair/improvement requires a baseline receipt; restriction/withdrawal can use an objective-specific state check. An effective restriction never becomes capability repair. Ineffective attempts remain visible without implying no functioning route. Drill evidence never establishes a resolved production incident. Unknown authority limits the capacity/authorization result while leaving the outcome evidence intact.

## 8. Public result contract, diagnostics and deterministic rendering

### 8.1 Report envelope and independent result dimensions

Every successful admission report includes `schema`, `dossier_schema`, `dossier_id`, `policy`, `method`, `serialization`, `tool_version`, `build_id`, `python_implementation`, `python_version`, `analysis_time`, `input_sha256`, `selected_request_ids`, `admission`, `execution`, `results`, `findings`, `limitations`, and `result_sha256`. Serialization is ect-json/0.1. Build identity is a package-embedded immutable source revision plus release/build label; development builds with unknown identity explicitly carry unknown and make no exact same-build reproduction claim. No raw input bytes, evidence content, locators, machine hostname, absolute file path, wall-clock time or environment variables enter the report. Engine versions are runtime identity, not an external-evidence grade.

`admission` is `valid|invalid`. Invalid-input envelopes identify the byte hash when available, report schema/tool identity and sanitized diagnostics; unavailable dossier fields are omitted with reasons, and results stay empty. Execution is `completed|partial|not_run|failed`. Admission-invalid analysis is `not_run`. A supported request family unavailable in an intermediate implementation step must return `not_run` with `unsupported_operation`, never an empty success.

Each request result has `request_id`, `operation`, `scope_id`, `selection`, `applicability`, `execution`, `assessment`, `reason_codes`, `values`, `basis`, `support_ids`, `contrary_ids`, `dependency_ids`, `limitations`. Nested criteria use the same status dimensions where relevant:

| Dimension | Allowed values |
|---|---|
| `selection` | `selected`, `not_selected` |
| `applicability` | `applicable`, `not_applicable`, `unresolved` |
| `execution` | `completed`, `partial`, `not_run`, `failed` |
| `assessment` | `supported_under_scope`, `contradicted_under_scope`, `unresolved`, `not_assessed` |
| Overall open-claim `conclusion` | `supported_under_scope`, `defeated_under_scope`, `unestablished`, `not_assessed` |
| Numeric value state | `{state:available,value:<integer or rational>}`, or `{state:undefined\|unavailable,reason:<code>}` |
| Basis kind | `supplied_assertion`, `supplied_review`, `local_deduction`, `local_calculation`, `captured_identity` |

Pure arithmetic/inventory outputs set assessment `not_assessed`, applicability applicable and preserve numeric values separately. They do not receive an invented epistemic verdict. Documentary completeness is `complete|incomplete|not_assessed` under `values`. `basis` entries hold kind plus exact record IDs, JSON pointers or finite paths; every derived finding keeps reconstructible premise references. Multiple bases are allowed. A report hash is captured identity only.

The stable operation payloads under `values` are:

| Operation | Required payload keys and meaning |
|---|---|
| lint | `disclosures` (ten rows with id, presence, well_formed, linked, qualification, applicability and reasons), `documentary_completeness`, `currentness`, `scope_mismatches`, `validation`, `claim_conclusion`. Mismatches identify exact required feature and frame; no mismatch is invented from missing text. |
| profile | `profiles`, with one selected entry and, when requested, one confirmed_valid entry. Each has snapshot_id, frame_id, population, K, N, A, U, assignment_coverage, class_counts, observed_support, SCI, D and member_reasons. Class counts are sorted class_id/count rows. Confirmed-valid entries additionally contain V, validity_coverage and validity_counts, while K retains original known roster size. N/A/U for that entry refer to its captured confirmed-valid subset, with N=V and assignment_coverage=A/V when V>0. Validity_coverage uses (qualified valid + qualified invalid)/selected-profile.N, never V as its denominator. Full valid-population claims remain unavailable when original membership or validity is unresolved. |
| compare | `before`, `after` (profile entries), `mode`, `compatibility`, `pair_count`, `pair_gaps`, `delta_SCI`, `delta_D`, `tail_changes`. Pair count is unavailable/inapplicable for descriptive mode. Compatibility is supported or unavailable with reasons. No matched delta occupies a descriptive slot or vice versa. |
| lineage | `view`, `seed_ids`, `witnesses`, `frontiers`, `captured_terminals`, `search_complete`, `independence_assessments`, `recursive_witnesses`. Paths list the actual relation IDs in traversal order. No empty witnesses array supplies independence. |
| external | `cohort_id`, `membership`, `known_member_count`, `member_states`, `stage_counts`, `event_counts`, `externality_counts`, `qualification_counts`, `carryover_ids`. Every count retains its cohort/checkpoint/purpose scope. |
| cases | `anomalies`, `revisions`, `corrections`, each sorted by ID. Anomalies retain preservation/disposition results; revisions have documented/incorporated/fidelity results; corrections have route/authority/handling/attempt/action/outcome/capacity results and event IDs. Each assessed subresult uses the common criterion envelope. |
| assess | `claim_id`, `currentness`, `conditions`, `conclusion`, `capacity_extent`, `prerequisites`. Open claims have exactly five condition rows, each with its fixed criteria and common envelope. Narrow claims have conditions empty and an explicit open_evaluation not_applicable result; their conclusion follows the narrow rule. Prerequisites reference the actual structural/external/case result bodies used. |

All counts, fractions and deltas use the numeric value wrapper. Inventories use arrays, with incompleteness represented in the enclosing execution/coverage state, never by pretending an empty inventory is complete. Per-member reasons include exact selected record IDs. Disclosure `not_applicable` assertions retain presence present with applicability evaluated separately. `documentary_completeness=complete` means every required row has a known well-formed linked declaration or a qualified permitted exclusion; it does not require successful scientific qualification. This permits a completely disclosed but unsupported claim.

Minimum reason-code vocabulary is: `missing_field`, `missing_record`, `unknown_value`, `withheld`, `disputed`, `explicit_absence`, `scope_mismatch`, `expired`, `access_gap`, `body_unavailable`, `provisional`, `unclassified`, `unresolved_assignment`, `unknown_membership`, `incomplete_pairs`, `incompatible_frame`, `incompatible_policy`, `unsupported_validation_kind`, `unsupported_operation`, `resource_limit`, `unselected`, `inapplicable`, `prerequisite_unavailable`, `empty_population`, `empty_admitted_population`, `no_witness_in_captured_view`, `absent_in_empty_population`, `internal_error`. Admission/usage codes have the separate `INPUT_*`/`USAGE_*` namespace. Additions to public codes require an explicit contract revision, not silent drift.

### 8.2 Finding families

| Stable family | Meaning |
|---|---|
| EC101 | Claim/cut disclosure gap or explicit scope mismatch |
| EC102 | Typed shared lineage, scoped independence gap or contradictory assessment |
| EC103 | External-contact/qualification/use gap |
| EC104 | Structural distribution, declared tail presence/absence/loss |
| EC105 | Anomaly preservation, recut or incorporation gap |
| EC106 | Route, authority, attempt, action, outcome or capacity gap |
| EC107 | Claim-validation type or currentness gap |
| EC108 | Comparison incompatibility, incomplete analysis or unsupported operation |

A finding contains `family`, `request_id`, `scope_id`, `subject_ids`, `rule`, `assessment`, `reason_codes`, `basis`, `support_ids`, `contrary_ids`, `limitations` and `needed_information` (rule-generated text). Family is unrelated to severity or evidence strength. Findings are sorted by request ID, family, rule, subject IDs and reason codes. No universal risk ranking is provided. Rule-generated prose uses IDs and safe counts, with referenced sensitive text kept in the original dossier.

### 8.3 Identity, ordering and Markdown parity

Canonical JSON is UTF-8, `ensure_ascii=True`, `sort_keys=True`, separators `(',', ':')`, no indentation, one final LF, no floats. Arrays that represent sets are sorted by ID; semantic ordered pairs/windows/path edges retain order. Requests/results sort by request ID. All returned rationals are reduced decimal-string pairs. Hash exact original input bytes as `input_sha256`.

`result_sha256` hashes the canonical report with only its own `result_sha256` field removed, including the final LF. There is no self-referential hash. Same input bytes, request selection, tool build, interpreter identity and contract versions must produce identical report bytes. Reformatting input changes input/report identity even if values remain equivalent. The four supported runtime cells must agree on normalized substantive results after excluding tool/interpreter identity and digests; they are not promised identical full bytes. Different method/schema versions require explicit comparison, never automatic exact-replay claims.

Markdown uses the same result object. It renders every substantive finding/criterion, selection/execution state, numerator/denominator, scope, contrary basis and limitation. Evidence bodies and locators are omitted in both formats. Numeric display uses integers and exact `numerator/denominator` fractions, avoiding a second rounding policy. Escape all inserted identifiers/text for Markdown and terminal controls; do not produce active HTML or automatic links from dossier strings. JSON/Markdown parity is checked by fixture assertions over the shared result content, with one golden rendering example to protect readable ordering.

## 9. Input, resource, filesystem and exit boundaries

### 9.1 Fixed resource profile

These fixed limits apply before or during analysis, with no dossier-controlled override:

| Limit | v0.1 bound |
|---|---|
| Input bytes | 10 MiB |
| JSON container depth | 32 |
| Total JSON values, including keys | 250,000 |
| One decoded string | 65,536 UTF-8 bytes |
| Total records | 30,000 |
| Graph nodes / relation records | 10,000 / 20,000 |
| Membership rows across snapshots | 50,000 |
| Requests in dossier / selected in a run | 64 / 16 |
| Graph edge examinations | 1,000,000 per request and 2,000,000 per run |
| Retained finite path edges and finding entries | 100,000 path-edge references and 10,000 findings per run |
| Serialized report | 20 MiB |

Structural admission limits reject the whole dossier before analysis with an input diagnostic. A bounded pre-scan enforces depth/value/string/number-token limits before recursive JSON construction. It respects quoted strings and escapes; no regex-only JSON parsing is allowed. The actual strict decoder still validates JSON and duplicate keys. Implementation may use an iterative scanner plus the standard-library decoder, with independent malformed-token fixtures.

Work budgets count each examined adjacency edge, including repeats across seeds, in the deterministic traversal order. At a work/witness/finding limit, preserve completed positive witnesses and results, mark the affected request and run partial, retain frontier/reason data, and block clean-negative or affirmative all-gate conclusions that depend on unfinished work. Stop scheduling later requests after the per-run limit; emit `not_run/resource_limit` placeholders. Do not silently truncate results. If a final report would exceed 20 MiB, emit a compact partial envelope listing affected request IDs and `resource_limit`; retain no false complete conclusion. This exceptional envelope explains that detailed witnesses could not be delivered and preserves their existence/count where established.

No wall-clock timeout is used as a semantic cutoff; deterministic work counters govern partial results. Interruptions may abort execution with a failure result but cannot create clean negatives. No cache, unbounded path enumeration or recursive graph walk is needed.

### 9.2 File and content safety

The CLI reads one explicitly named regular file. It rejects symbolic-link/reparse-point inputs, named pipes, devices and input paths traversing symbolic-link/reparse-point components. Input is opened once, its descriptor verified as a regular file, read within the byte limit and hashed from those exact bytes. No dossier path, URI, command, environment syntax or credential is executed or dereferenced. No auxiliary evidence files are opened. Standard input, archives and directory traversal are outside this release.

Output to stdout is the default. File output requires an existing ordinary parent directory, rejects symlink/reparse-point path components and uses exclusive creation of a new regular file. Existing files, directories, links and an input/output identity collision are refused. There is no `--force`. Validate/analyze completes in memory before opening output. A failed write removes only the newly created incomplete file owned by this invocation; it never replaces an existing file. No automatic directory creation is required.

Use handle-based checks and no-follow facilities where supported. The supported threat boundary is untrusted dossier content in a user-controlled local directory. The tool does not claim protection against a concurrent hostile local process replacing directory components, including a same-user process; document that residual host-level boundary without weakening the explicit link checks. Errors use rule codes, IDs and positions, not source lines, evidence bodies, absolute paths, secrets or raw OS exception text. Output may still contain user-supplied identifiers, so reports are private by default and are never automatically published.

### 9.3 Exit meanings

| Exit | Meaning |
|---|---|
| 0 | Requested admission/analysis completed and output succeeded. Unresolved or defeated scientific claims may be present. |
| 1 | Internal or output/input I/O failure; no success claim. |
| 2 | CLI usage error, invalid dossier syntax/schema/references, or admission resource-limit rejection. |
| 3 | Valid input, but selected work is partial or unsupported. A reason-bearing report is emitted when output succeeds. |

Exit 1 overrides 3 when report delivery fails. Missing evidence in a well-formed dossier is an ordinary completed analytical result and exit 0. No `--fail-on-finding` option is included initially. Shell success never represents openness or truth. `validate` returning 0 means input admission only.

## 10. Independent acceptance packet

All fixtures are project-owned synthetic declarations. Expected outcomes below are specified before implementation and must remain independent of production calculation helpers. They establish software behavior, with no field-validation claim.

### 10.1 Complete minimal input for the first slice

The following is one complete valid dossier. The missing semantic fields are intentional and must generate useful gaps rather than input rejection.

```json
{
  "schema": "ect-dossier/0.1",
  "id": "demo-incomplete-regression",
  "analysis_time": "2026-10-06T21:00:00Z",
  "policy": "ect-core/0.1",
  "records": [
    {"id":"process-v1","type":"entity","kind":"process","logical_id":"process","version":"v1"},
    {"id":"scope-main","type":"scope","process_id":"process-v1","claim_id":"claim-v1"},
    {
      "id":"claim-v1","type":"claim","scope_id":"scope-main","profile":"narrow_regression",
      "statement":{"state":"known","value":"The declared finite regression cases passed in run 1."},
      "intended_use":{"state":"known","value":"Regression tracking for the named single-turn cases only."},
      "horizon":{"state":"known","value":"One isolated turn per case."},
      "requirements":{"state":"known","value":["single_turn"]},
      "validation_kind":{"state":"known","value":"execution"}
    }
  ],
  "requests": [{"id":"lint-main","operation":"lint","scope_id":"scope-main","claim_id":"claim-v1"}]
}
```

Expected invariants: admission valid; lint execution completed; finite claim unestablished; currentness unestablished; EC101 gaps for missing frame/disclosures; EC107 missing execution-validation basis and expiry; no five-condition pass and no claim of actual execution. No model/network/file dereference occurs. CLI exit 0 after successful delivery. Replacing the known statement with a string containing shell syntax or a URL changes captured identity and preserves inert treatment.

### 10.2 Structural and comparison oracles

Use complete frame F with four classes and a declared required fourth class. All base items have known bodies and admitted attributed assignments. Exact expected values:

| Fixture or mutation | Required outcome |
|---|---|
| A counts `(12,6,4,2)`, N=24 | A=24,U=0, support 4; SCI 25/72, D 47/72, coverage 1. |
| B counts `(24,16,8,0)`, N=48 | Support 3; SCI 7/18, D 11/18; descriptive delta SCI +1/24; fourth-class absence/loss within complete compatible catalogs. No matching inferred. |
| B one third-class item unresolved | N=48,A=47,U=1; coverage 47/48; SCI 881/2209,D 1328/2209; zero fourth sightings retained, complete absence/loss unresolved. |
| Only those 47 members, roster unknown | K=47 known-subset metrics; full N/coverage/metrics/delta/absence unavailable. |
| Model fails two fourth-class A cases | Structural A unchanged; failure receipts remain visible. |
| Separate validities mark those two invalid | Confirmed-valid V=22, SCI 49/121,D 72/121; selected A remains 24. |
| One selected validity unknown | Retain unknown-validity count and conditional confirmed-valid profile; no claim of complete valid population. |
| Complete 24 justified pairs end `(12,10,2,0)` | Matched end SCI 31/72,D 41/72; delta +1/12. Full-catalog delta remains +1/24 in its separate request. |
| One pair endpoint lacks snapshot membership | Requested matched contrast unavailable; no silent 23-pair result. |
| Two pairs reuse one target endpoint | Admission rejects duplicate matched endpoint. |
| Same 24 reannotated into `(6,6,6,4,2)` | Support 5,SCI 2/9,D 7/9; new observations 0; direct cross-frame gain unavailable. |
| Complete reviewed one-to-one relabel | Same numerical comparison after mapping, attributed equivalence basis retained. Omit a zero-count class from mapping: compatibility unavailable. |
| Known N=0 | Support 0; SCI/D/coverage undefined. Required class may be absent in empty population, no supported retention. |
| Known N=48,A=0 | U=48, coverage 0, support 0; SCI/D undefined, full class absence unestablished. |
| All 48 in one class | Support 1, SCI 1,D 0. |
| Add unselected assignment revision | Counts and metrics unchanged. Select it explicitly: item count unchanged, dependent metrics recomputed. |
| Duplicate member or logical item version in a snapshot | Admission error, no silent deduplication. |

### 10.3 Evidence and five-condition oracles

| Fixture | Required outcome |
|---|---|
| Shared acquisition paths x->o and y->o; x also reaches unknown frontier u | Both overlap paths and u survive; conditional declaration-based overlap, no hidden-root or independence count. |
| a/b and b/c acquisition reviews; shared analytical method | Exact reviews and separate method relation remain. No a/c/setwise/model-ancestry conclusion. |
| Search stops after a known overlap | Preserve overlap; execution partial and EC108 resource limit; no clean negative from unfinished branches. |
| Use event with missing receipt log and wrong-boundary externality review | Use can remain documented; receipt/qualified external contact unresolved. A qualified externality review with no input_qualification review still leaves suitability for the use unresolved. |
| Three members, two retention events for p, explicit nonretention q, missing r | Member counts yes=1,no=1,unresolved=1; raw event count 3. No two-member count for p. |
| Old grounded carryover, no within-window acquisition | Preserve ancestry; no new contact or independent root. |
| Ticket accepted; newer version has no linked action | Handling documented; attempt/action/outcome unestablished, actual absence of action not inferred. |
| Linked effective restriction; capability repair untested | Support restriction criterion under supplied review; repair unestablished. Unknown authority variant preserves outcome and blocks authority/capacity support. |
| Fully disclosed single-turn frame, claim requires recovery/persistent state | Documentary completeness may be complete; structured scope mismatch defeats the corresponding scope claim. Narrower supported use remains available. |
| Revision with only renamed labels | Revision record preserved, structural recut/improved fidelity unsupported. Investigated-no-change never automatically means closure. |
| `verified` word, human producer, new provider, fresh timestamp | No automatic evidence upgrade, externality, independence or reopening. |
| Protected evidence pointer only | Declaration retained; access gap. Supplied inspection receipt qualifies only its documented inspection statement under the relevant fixed rule. |
| Qualified support plus unresolved contrary review | Criterion disputed/unresolved. Adding an exact qualified resolution preserves both originals; support remains conditional on the resolution. |

**Satisfiable all-five fixture:** one bounded open-evaluation claim C, one complete frame F representing all of C's required features, complete current snapshot S with two classes and at least one item in each, one designated tail class with supplied result receipt, and a current declared validity date. Supply fourteen distinct exact-scope gate reviews with appropriate evidence. Supply the separate claim-type execution-validation receipt, anomaly-accountability review covering a declared known inventory, and source-integrity review explicitly covering generator/reference/judge roles and known lineage limits. Use one nonempty external cohort with member z, exact boundary/window/purpose, separate member-specific externality and input_qualification reviews, known within-window receipt and relevant use with supplied receipts. Supply one authorized case/drill with route, attempt, linked action and operability evidence; set the capacity extent to `tested_route`. All support and contrary inventories are completely examined; no unresolved required premise remains.

Expected: all five `supported_under_scope`; overall supported only for C's finite stated scope, supplied evidence and fixed policy; corrective extent remains tested route, with drill context retained if used. These stipulations do not independently establish real-world truth. Three mutations are mandatory: remove one required external-use receipt -> external presence unresolved and overall unestablished; supply a decisive exact-scope tail contradiction -> overall defeated while other support remains visible; deselect tail retention -> that gate not assessed and overall unestablished. No 80% result appears. A sustained-capacity variant with one case and no history stays unresolved.

**Narrow positive fixture:** a finite single-turn claim with explicit exclusions, current date, scoped frame, required disclosures or permitted applicability reviews, supplied execution receipt and qualified claim_validation review. Expected finite scoped support; no open-evaluation summary. Remove the execution receipt and retain all metadata: documentary completeness can remain, but claim support becomes unresolved.

### 10.4 Security and delivery oracles

Test only distinct contract risks: duplicate keys at nested depth; NaN/infinity/floats; excessive nesting/string/bytes/records; malformed references and wrong types; Unicode/control characters; graph cycles and work limits; deterministic request order; inert locators/shell-looking evidence; no auxiliary reads/network/process launch; exclusive-output refusal; symlink/reparse-point and nonregular-file rejection; safe partial-write cleanup; no raw evidence leakage in errors/reports; JSON/Markdown semantic parity; same-build exact report digest; missing packaged fixture after installation. Expected error categories and exits follow sections 8-9.

No exhaustive historical ledger replay, repeated predecessor CI or test-count target is required. A targeted semantic change gets its direct counterexample plus affected integration check. Release qualification verifies sdist, wheel built from that sdist, installation outside the checkout, packaged demos and documented CLI/API on the four selected runtime cells.

## 11. First implementation slice and P0-4 handoff

### 11.1 Concrete P1-1 candidate

After P0-4 approval and explicit P1-1 authorization, deliver an installable package with the strict dossier decoder, closed record/reference validation, inert fixed policy, the useful `lint` request, JSON/Markdown output and `validate/analyze/demo` entry points. Ship incomplete-regression, supported-narrow-regression and explicit-scope-mismatch fixtures. Other admitted operation requests return `not_run/unsupported_operation`, exit 3; they never receive placeholder support. Build only the modules needed for this slice.

P1-1 acceptance requires:

1. A clean installation outside the checkout runs the packaged lint examples without an account, API key or predecessor repository.
2. The complete minimal input above produces its independently specified gaps; the positive narrow fixture supports only its stated finite claim.
3. Metadata completion cannot substitute for execution evidence; missing expiry and scope mismatch remain distinguishable.
4. Invalid syntax/references fail admission, while missing semantic facts yield a useful report.
5. Inert-input, output-safety, no-leakage, deterministic serialization and unsupported-operation cases behave as specified.
6. JSON and Markdown preserve the same evidence basis and limits. Passing package tests is described as software verification only.

The accepted staged sequence remains P1-1 lint; P1-2 structural accounting/comparison; P1-3 lineage/external contact; P1-4 anomaly/correction/five conditions; P1-5 consolidated reports/demos and deterministic rerun documentation; P1-6 release acceptance. P1-5 now excludes capture archives and simulation, consistent with section 1. This is a scope clarification, not authorization to start any implementation step.

### 11.2 Remaining readiness work

P0-4 should check this selected scope against the six handoff readiness conditions, resolve repository/name/license choices, and present the bounded P1-1 authorization decision. No predecessor API or missing manuscript blocks the selected independent implementation. Any release platform unavailable during later verification must narrow the advertised matrix or remain an explicit release blocker; it cannot be marked tested by design intent.

No production code, repository, upstream edit, package build or ECT test execution is claimed by P0-3. Validation of this deliverable consists of contract review, independent arithmetic checks, embedded JSON syntax/reference review and targeted consistency review. P0-4 has not been started.

## 12. Source pins and traceability

P0-2 remains the authority for accepted predecessor meanings. This step does not repeat a release-history audit or substitute newer unreviewed work.

| Source | Retained identity | Used here |
|---|---|---|
| Evaluation Closure primary PDF | SHA-256 `002d2393d05cb2c8b1db0a70e844e3d775e2be2155db7b2ffaadaa8080c8b950` | Five conditions, structural cut, claim-appropriate validation, reporting and finite-model limits. |
| Source Integrity Toolkit | `2413a29b839b7e1de8f76a449762f031de19d52b` | Attributed assertions, dependency dimensions, evidence gaps, external presence and correction separation. |
| Recursive Integrity Toolkit | `24f46ac375dafe4ee5c407d9b4b08dc4c77914ee`, released v0.1.0 / report schema 1.3 as recorded in P0-2 | Versioned reuse, carryover, unknown frontiers, simulation/reproduction boundaries. |
| StructDet-Bench | `0a9dc88deffd4b14264485b161bea06f027f68f5` | Population conservation, SCI/D, assignment coverage, frame and comparison discipline. |
| Supplementary manuscripts | Exact seven-file identity register in P0-1, reconfirmed in P0-2 | Bounded theory context. No additional metric or runtime dependency. |

Traceability: P0-2 D1 maps to sections 2-4; D2 to 5 and 8; D3 to 3.3 and 7.1; D4 to 5.3 and 7.2; D5-D6 to 6; D7-D8 to 3.4, 5.3 and 7.3; D9 to 5.3-5.4; D10 to 1 and 8-9. The eighteen P0-2 boundary examples are retained or refined in section 10. Its simulation example remains a companion-theory boundary, with no ECT simulator implementation obligation.
