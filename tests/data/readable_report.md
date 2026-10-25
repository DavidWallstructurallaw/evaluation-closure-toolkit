# Evaluation Closure Toolkit report

Admission: **valid**. Execution: **completed**.

Dossier: demo\-scope\-mismatch. Declared analysis time: 2026\-10\-06T21\:00\:00Z.

## Requests

| Request | Scope | Operation | Selection | Execution | Conclusion |
| --- | --- | --- | --- | --- | --- |
| lint\-main | scope\-main | lint | selected | completed | defeated\_under\_scope |

## lint lint\-main

Scope: scope\-main.

| Selection | Applicability | Execution | Assessment | Reasons |
| --- | --- | --- | --- | --- |
| selected | applicable | completed | contradicted\_under\_scope | scope\_mismatch |

Claim conclusion: defeated\_under\_scope. Documentary completeness: complete.

Currentness: current\_under\_declared\_date. Open evaluation: not\_applicable.

Documentary completeness describes declarations, not scientific support. Open-claim lint does not perform the five-condition assessment.

| Disclosure | Presence | Well formed | Linked | Applicability | Qualification | Anchors | Reasons |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R01 | present | yes | yes | applicable | supported\_under\_scope | claim\-v1 |  |
| R02 | present | yes | yes | applicable | supported\_under\_scope | frame\-v1 |  |
| R03 | present | yes | yes | applicable | supported\_under\_scope | item\-v1, origin\-relation |  |
| R04 | present | yes | yes | applicable | supported\_under\_scope | execution\-receipt |  |
| R05 | present | yes | yes | applicable | supported\_under\_scope | evaluator\-v1 |  |
| R06 | present | yes | yes | applicable | supported\_under\_scope | snapshot\-v1 |  |
| R07 | present | yes | yes | applicable | supported\_under\_scope | execution\-receipt |  |
| R08 | present | yes | yes | applicable | supported\_under\_scope | human\-receipt |  |
| R09 | present | yes | yes | applicable | supported\_under\_scope | correction\-v1 |  |
| R10 | present | yes | yes | applicable | supported\_under\_scope | currentness\-explanation |  |

| Validation selection | Applicability | Execution | Assessment | Reasons |
| --- | --- | --- | --- | --- |
| selected | applicable | completed | supported\_under\_scope |  |

| Required feature | Conflicting frame | Reasons |
| --- | --- | --- |
| long\_horizon | frame\-v1 | scope\_mismatch |

| Premises | Captured IDs |
| --- | --- |
| Support IDs | execution\-receipt, human\-receipt, validation\-review |
| Contrary IDs | none recorded |
| Dependency IDs | claim\-v1, correction\-v1, currentness\-explanation, evaluator\-v1, execution\-receipt, frame\-v1, human\-receipt, item\-v1, origin\-relation, scope\-main, snapshot\-v1, validation\-review |

Scoped limitations:

- Conclusions are conditional on the supplied finite scope, evidence and attributed reviews\.
- Evidence content, execution, assessor authority and protected underlying material were not independently authenticated\.
- Currentness uses the caller\-declared analysis time and validity date\.

## Findings

Families identify rule categories, not severity or a universal risk ranking. Empty contrary-ID arrays do not establish that no contrary evidence exists.

### EC101 / required\_feature\_absent

Request: lint\-main. Scope: scope\-main.

Subjects: claim\-v1, frame\-v1.

Assessment: contradicted\_under\_scope. Reasons: scope\_mismatch.

| Basis kind | Record IDs |
| --- | --- |
| local\_deduction | claim\-v1, frame\-v1 |

| Premises | Captured IDs |
| --- | --- |
| Support IDs | none recorded |
| Contrary IDs | none recorded |

Needed information: Provide the required scoped records and qualified review, retaining contrary premises\.
