"""Scoped documentary checks shared by cases and fixed-condition assessment."""

from .evidence import REVIEW_KINDS, fact_reason, known
from .provenance import reference_record


def check(reasons=(), *, dependencies=(), support=(), contrary=(), assessed=True):
    """A documentary subresult uses the same explicit envelope as a review."""
    reasons = set(reasons)
    return {
        "selection": "selected", "applicability": "applicable",
        "execution": "completed" if assessed else "not_run",
        "assessment": ("unresolved" if reasons else "supported_under_scope") if assessed else "not_assessed",
        "reason_codes": sorted(reasons),
        "values": {"documentary_completeness": "incomplete" if reasons or not assessed else "complete",
                   "reviews": [], "decisive_review_ids": [], "resolved_ids": []},
        "basis": [{"kind": "local_deduction", "record_ids": sorted(set(dependencies))}],
        "support_ids": sorted(set(support)), "contrary_ids": sorted(set(contrary)),
        "dependency_ids": sorted(set(dependencies) | set(support) | set(contrary)),
        "limitations": ["This check qualifies the supplied scoped documentary premises; it does not authenticate them."],
    }


def merge(target, *children):
    for key in ("dependency_ids", "support_ids", "contrary_ids", "reason_codes"):
        target[key] = sorted(set(target[key]).union(*(child[key] for child in children)))


def receipts(records, evidence_ids, scope_id, budget, *, subjects=(), kinds=REVIEW_KINDS,
             resolved=(), dated=False):
    """All named receipts must qualify; their subject inventory covers the anchors."""
    reasons, dependencies, contrary, anchors = set(), {scope_id}, set(), set()
    if not evidence_ids:
        reasons.add("missing_record")
    for identity in sorted(evidence_ids):
        budget.charge()
        row = records[identity]
        reference_record(row, records, dependencies, contrary, budget)
        if row["scope_id"] != scope_id:
            reasons.add("scope_mismatch")
        if known(row, "kind") not in kinds:
            reasons.add("prerequisite_unavailable")
        if known(row, "producer_id") is None:
            reasons.add(fact_reason(row, "producer_id"))
        if known(row, "access") != "supplied":
            reasons.add("access_gap")
        if known(row, "content") is None:
            reasons.add("body_unavailable")
        if dated and known(row, "occurred_at") is None:
            reasons.add(fact_reason(row, "occurred_at"))
        budget.charge(len(row.get("subject_ids", [])))
        anchors.update(row.get("subject_ids", []))
    budget.charge(len(subjects))
    if not set(subjects) <= anchors:
        reasons.add("prerequisite_unavailable")
    if contrary - set(resolved):
        reasons.add("disputed")
    return check(reasons, dependencies=dependencies, support=evidence_ids, contrary=contrary)


def add_premises(criterion, records, identities, budget):
    """Bind target prerequisites without erasing retained favorable/contrary reviews."""
    dependencies, contrary = set(criterion["dependency_ids"]), set()
    for identity in sorted(set(identities)):
        budget.charge()
        reference_record(records[identity], records, dependencies, contrary, budget)
    criterion["dependency_ids"] = sorted(dependencies | contrary)
    criterion["contrary_ids"] = sorted(set(criterion["contrary_ids"]) | contrary)
    return {"disputed"} if contrary - set(criterion["values"]["resolved_ids"]) else set()
