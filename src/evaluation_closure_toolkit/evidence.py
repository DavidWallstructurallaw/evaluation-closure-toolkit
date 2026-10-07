"""Documentary review qualification over admitted, inert dossier records.

These routines check supplied premises. They do not authenticate evidence or
decide the truth of text, and never read locators or return evidence bodies.
"""

from collections import defaultdict, deque

from .budget import RequestBudget


REVIEW_KINDS = frozenset({
    "document", "execution_record", "observation_record",
    "human_consequence_record", "intervention_record", "proof_record",
    "analysis_record", "process_record",
})


def known(record: dict, key: str):
    """Return an admitted known fact's value; None denotes a semantic gap."""
    fact = record.get(key, {})
    return fact.get("value") if fact.get("state") == "known" else None


def fact_reason(record: dict, key: str) -> str:
    fact = record.get(key)
    if fact is None:
        return "missing_field"
    return {
        "unknown": "unknown_value", "withheld": "withheld",
        "disputed": "disputed", "absent": "explicit_absence",
        "not_applicable": "inapplicable",
    }.get(fact["state"], "prerequisite_unavailable")


def _binding(review: dict) -> tuple:
    return tuple(review.get(key) for key in (
        "target_id", "criterion", "scope_id", "member_id",
        "target_event_id", "request_id", "disclosure_id",
    ))


def _refs_into(target: set, references, budget: RequestBudget) -> None:
    """Examine each reference before adding it, including repeated edges."""
    for reference in references:
        budget.charge()
        target.add(reference)


def _qualification(review: dict, records: dict, scope_id: str,
                   required_kinds: frozenset, budget: RequestBudget) -> set:
    reasons = set()
    if review["scope_id"] != scope_id:
        reasons.add("scope_mismatch")
    for field in ("assessor_id", "reviewed_at", "method", "rationale", "verdict"):
        if known(review, field) is None:
            reasons.add(fact_reason(review, field))
    if known(review, "verdict") == "unresolved":
        reasons.add("unknown_value")
    evidence_ids = review.get("evidence_ids", [])
    if not evidence_ids:
        reasons.add("prerequisite_unavailable")
    kinds = set()
    for evidence_id in evidence_ids:
        budget.charge()
        evidence = records[evidence_id]
        kind = known(evidence, "kind")
        if evidence["scope_id"] != scope_id:
            reasons.add("scope_mismatch")
        if kind not in REVIEW_KINDS:
            reasons.add("prerequisite_unavailable")
        else:
            kinds.add(kind)
        if known(evidence, "producer_id") is None:
            reasons.add(fact_reason(evidence, "producer_id"))
        if known(evidence, "access") != "supplied":
            reasons.add("access_gap")
        if known(evidence, "content") is None:
            reasons.add("body_unavailable")
    if not required_kinds.issubset(kinds):
        reasons.add("prerequisite_unavailable")
    return reasons


def _counterexample_in_scope(counterexample_id: str, review: dict,
                            records: dict, budget: RequestBudget) -> bool:
    record = records[counterexample_id]
    if "scope_id" in record:
        return record["scope_id"] == review["scope_id"]
    if record["id"] == review["target_id"]:
        return True
    target = records[review["target_id"]]
    if record["type"] == "frame" and known(target, "frame_id") == record["id"]:
        return True
    for evidence_id in review.get("evidence_ids", []):
        budget.charge()
        for subject_id in records[evidence_id].get("subject_ids", []):
            budget.charge()
            if subject_id == counterexample_id:
                return True
    return False


def make_review_index(records: dict) -> dict:
    """Index all supplied declarations once; qualifications remain request-local."""
    index = defaultdict(list)
    for record in records.values():
        if record["type"] == "review":
            index[(record["target_id"], record["criterion"])].append(record)
    return {key: sorted(value, key=lambda r: r["id"]) for key, value in index.items()}


def evaluate_reviews(records: dict, target_id: str, criterion: str,
                     scope_id: str, *, required_kinds=(), disclosure_id=None,
                     applicability_row=None, request_id=None, review_index=None,
                     budget=None) -> dict:
    """Assess every relevant declaration, retaining conflicts and resolutions.

    ``records`` is indexed by ID. Disclosures filter claim-review coverage;
    applicability_row instead binds a row-specific applicability review.
    Matching-basis reviews are bound to an exact comparison request. An optional
    index must contain all declarations, including wrong-scope and contrary ones.
    """
    if budget is None:
        budget = RequestBudget()
    if criterion == "matching_basis" and request_id is None:
        raise ValueError("MATCHING_REQUEST_REQUIRED")
    pool = records.values() if review_index is None else review_index.get((target_id, criterion), ())
    candidates = sorted((r for r in pool
                         if r["type"] == "review" and r["target_id"] == target_id
                         and r["criterion"] == criterion
                         and (request_id is None or r.get("request_id") == request_id)
                         and (disclosure_id is None or disclosure_id in r.get("disclosure_ids", []))
                         and (applicability_row is None or r.get("disclosure_id") == applicability_row)),
                        key=lambda r: r["id"])
    selected = {r["id"]: r for r in candidates if r["scope_id"] == scope_id}
    required_kinds = frozenset(required_kinds)
    gaps = {r["id"]: _qualification(r, records, scope_id, required_kinds, budget)
            for r in candidates}
    qualified = {rid for rid in selected if not gaps[rid]}
    # Resolution edges run from adjudicator to the exact challenged record.
    # Invalid links cannot remove a premise. A cycle has no effective winner.
    edges = defaultdict(set)
    dependencies = defaultdict(set)
    resolvers = defaultdict(set)
    for rid in sorted(qualified):
        review = selected[rid]
        support = set()
        _refs_into(support, review.get("evidence_ids", []), budget)
        for ref in review.get("resolves", []):
            budget.charge()
            record = records[ref]
            valid = ref != rid and ref not in support
            if record["type"] == "review":
                valid = valid and _binding(record) == _binding(review)
                if disclosure_id is not None:
                    valid = valid and disclosure_id in record.get("disclosure_ids", [])
            else:
                valid = valid and record.get("scope_id") == scope_id
            if not valid:
                gaps[rid].add("disputed")
                continue
            edges[rid].add(ref)
            resolvers[ref].add(rid)
    conflicting = set()
    for refs in resolvers.values():
        verdicts = set()
        for rid in sorted(refs):
            budget.charge()
            verdicts.add(known(selected[rid], "verdict"))
        if len(verdicts) > 1:
            conflicting.update(refs)
    for rid in conflicting:
        gaps[rid].add("disputed")
    # A reviewer is evaluated after resolvers of its record, supporting
    # evidence or explicitly contrary premises. This avoids order-based wins.
    for rid, review in selected.items():
        inputs = {rid}
        for key in ("evidence_ids", "contrary_ids", "counterexample_ids"):
            _refs_into(inputs, review.get(key, []), budget)
        for eid in review.get("evidence_ids", []):
            budget.charge()
            _refs_into(inputs, records[eid].get("contrary_ids", []), budget)
        for cid in review.get("counterexample_ids", []):
            budget.charge()
            _refs_into(inputs, records[cid].get("contrary_ids", []), budget)
        for ref in sorted(inputs):
            budget.charge()
            for resolver in sorted(resolvers.get(ref, ())):
                # This fanout can be quadratic in the small supplied graph.
                # Charge before allocating each derived dependency edge.
                budget.charge()
                dependencies[rid].add(resolver)
    outgoing = defaultdict(set)
    degree = {}
    for rid in selected:
        degree[rid] = len(dependencies[rid])
        for dep in sorted(dependencies[rid]):
            budget.charge()
            outgoing[dep].add(rid)
    queue = deque(sorted(rid for rid in selected if degree[rid] == 0))
    removed = set()
    examined = set()
    active_qualified = set()
    unresolved_refs = {}
    while queue:
        rid = queue.popleft()
        examined.add(rid)
        review = selected[rid]
        refs = set()
        _refs_into(refs, review.get("contrary_ids", []), budget)
        for eid in review.get("evidence_ids", []):
            budget.charge()
            _refs_into(refs, records[eid].get("contrary_ids", []), budget)
            if eid in removed:
                refs.add(eid)
        pending = (refs - removed) | (set(review.get("evidence_ids", [])) & removed)
        unresolved_refs[rid] = pending
        if rid not in removed and not gaps[rid] and not pending:
            active_qualified.add(rid)
            _refs_into(removed, sorted(edges[rid]), budget)
        for dependent in sorted(outgoing[rid]):
            budget.charge()
            degree[dependent] -= 1
            if degree[dependent] == 0:
                queue.append(dependent)
    cyclic = set(selected) - examined
    for rid in cyclic:
        gaps[rid].add("disputed")
    active_qualified -= removed
    active = set(selected) - removed
    contrary = set()
    _refs_into(contrary, records[target_id].get("contrary_ids", []), budget)
    for review in candidates:
        _refs_into(contrary, review.get("contrary_ids", []), budget)
        for eid in review.get("evidence_ids", []):
            budget.charge()
            _refs_into(contrary, records[eid].get("contrary_ids", []), budget)
        if known(review, "verdict") in {"contradicts", "unresolved"}:
            contrary.add(review["id"])
    decisive = set()
    for rid in sorted(active_qualified):
        review = selected[rid]
        counterexamples = review.get("counterexample_ids", [])
        if (known(review, "verdict") == "contradicts"
                and known(review, "decisive") is True and counterexamples):
            all_active = True
            for cid in counterexamples:
                budget.charge()
                opposing = set()
                _refs_into(opposing, records[cid].get("contrary_ids", []), budget)
                if (cid in removed or opposing - removed
                        or not _counterexample_in_scope(cid, review, records, budget)):
                    all_active = False
                    break
            if all_active:
                decisive.add(rid)
    supports = {rid for rid in active_qualified
                if known(selected[rid], "verdict") == "supports"}
    disputed = bool(cyclic or (set(records[target_id].get("contrary_ids", [])) - removed))
    for rid in active:
        review = selected[rid]
        if (known(review, "verdict") != "supports"
                or review.get("verdict", {}).get("state") == "disputed"
                or unresolved_refs.get(rid) or "disputed" in gaps[rid]):
            disputed = True
    if decisive:
        assessment = "contradicted_under_scope"
    elif disputed:
        assessment = "unresolved"
    elif supports:
        assessment = "supported_under_scope"
    else:
        assessment = "unresolved"
    reasons = set()
    if assessment != "supported_under_scope":
        reasons.update(reason for rid in active for reason in gaps[rid])
        if disputed:
            reasons.add("disputed")
        if not active:
            reasons.add("missing_record")
        if not reasons and not decisive:
            reasons.add("prerequisite_unavailable")
    if not selected and candidates:
        reasons.add("scope_mismatch")
    support_ids = set(supports)
    for rid in sorted(supports):
        _refs_into(support_ids, selected[rid].get("evidence_ids", []), budget)
    dependencies_ids = {target_id, scope_id}
    for review in candidates:
        dependencies_ids.add(review["id"])
        for key in ("evidence_ids", "contrary_ids", "resolves", "counterexample_ids"):
            _refs_into(dependencies_ids, review.get(key, []), budget)
    declarations = []
    for review in candidates:
        rid = review["id"]
        row_reasons = set(gaps[rid])
        if unresolved_refs.get(rid):
            row_reasons.add("disputed")
        declarations.append({
            "review_id": rid, "scope_id": review["scope_id"],
            "selected": rid in selected,
            "documentary_completeness": "complete" if not gaps[rid] else "incomplete",
            "qualified": rid in active_qualified,
            "resolved": rid in removed,
            "verdict": known(review, "verdict") or "unresolved",
            "reason_codes": sorted(row_reasons),
            "support_ids": sorted(review.get("evidence_ids", [])),
            "contrary_ids": sorted(review.get("contrary_ids", [])),
            "resolves": sorted(review.get("resolves", [])),
        })
    return {
        "selection": "selected", "applicability": "applicable",
        "execution": "completed", "assessment": assessment,
        "reason_codes": sorted(reasons),
        "values": {"documentary_completeness": "complete" if active_qualified else "incomplete",
                   "reviews": declarations, "decisive_review_ids": sorted(decisive),
                   "resolved_ids": sorted(removed)},
        "basis": [{"kind": "supplied_review", "record_ids": sorted(r["id"] for r in candidates)}]
                 if candidates else [],
        "support_ids": sorted(support_ids), "contrary_ids": sorted(contrary),
        "dependency_ids": sorted(dependencies_ids),
        "limitations": ["Qualification is conditional on supplied reviews and evidence; authentication and textual truth were not established."],
    }
