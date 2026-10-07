"""Exact structural accounting over explicitly selected, attributed records.

Counts describe supplied populations and classification decisions. No item body,
classifier, validity outcome or unselected revision creates a class assignment.
"""

from collections import Counter
from fractions import Fraction

from .budget import RequestBudget
from .evidence import evaluate_reviews, fact_reason, known, make_review_index


PRIMARY_REASONS = (
    "disputed", "withheld", "body_unavailable", "missing_record",
    "provisional", "unclassified", "unresolved",
)
VALIDITY_STATES = ("disputed", "invalid", "missing", "unresolved", "valid")


def available(value: int) -> dict:
    return {"state": "available", "value": value}


def unavailable(reason: str) -> dict:
    return {"state": "unavailable", "reason": reason}


def undefined(reason: str) -> dict:
    return {"state": "undefined", "reason": reason}


def ratio(numerator: int, denominator: int, *, empty_reason="empty_population") -> dict:
    if denominator == 0:
        return undefined(empty_reason)
    number = Fraction(numerator, denominator)
    return {"state": "available", "value": {
        "numerator": str(number.numerator), "denominator": str(number.denominator),
    }}


def _references(record: dict, dependencies: set, budget: RequestBudget) -> None:
    """Retain explicit premises, including gap evidence, without their text."""
    dependencies.add(record["id"])
    for field in ("evidence_ids", "contrary_ids", "contribution_ids"):
        for rid in record.get(field, []):
            budget.charge()
            dependencies.add(rid)
    actor = known(record, "asserted_by")
    if actor is not None:
        budget.charge()
        dependencies.add(actor)
    for value in record.values():
        if isinstance(value, dict) and "state" in value:
            for rid in value.get("evidence_ids", []):
                budget.charge()
                dependencies.add(rid)


def _direct_contrary(record: dict, records: dict, budget: RequestBudget) -> set:
    """Common contrary references and contrary premises on attached evidence."""
    contrary = set()
    for rid in record.get("contrary_ids", []):
        budget.charge()
        contrary.add(rid)
    for eid in record.get("evidence_ids", []):
        budget.charge()
        for rid in records[eid].get("contrary_ids", []):
            budget.charge()
            contrary.add(rid)
    return contrary


def _validity(item_id, validity_id, frame, records, dependencies, budget):
    row = {"item_id": item_id, "state": "missing", "reason_codes": ["missing_record"]}
    if validity_id is None:
        return row, set()
    record = records[validity_id]
    _references(record, dependencies, budget)
    row["validity_id"] = validity_id
    reasons = set()
    for field in ("verdict", "asserted_by", "basis", "rubric"):
        if known(record, field) is None:
            reasons.add(fact_reason(record, field))
    rubric = known(frame, "validity_rubric")
    if rubric is None:
        reasons.add(fact_reason(frame, "validity_rubric"))
    elif known(record, "rubric") is not None and known(record, "rubric") != rubric:
        reasons.add("incompatible_policy")
    if known(record, "verdict") == "unresolved":
        reasons.add("unknown_value")
    contrary = _direct_contrary(record, records, budget)
    if contrary:
        reasons.add("disputed")
    row["reason_codes"] = sorted(reasons)
    row["state"] = ("disputed" if "disputed" in reasons else "unresolved") if reasons else known(record, "verdict")
    return row, contrary


def _assignment(item_id, assignment_id, frame, classes, records, scope_id,
                review_index, dependencies, budget):
    item = records[item_id]
    _references(item, dependencies, budget)
    row = {"item_id": item_id, "primary_reason": "admitted", "reason_codes": []}
    reasons = set()
    categories = set()
    support_ids = set()
    contrary = _direct_contrary(item, records, budget)
    if contrary:
        reasons.add("disputed")
        categories.add("disputed")
    if known(item, "body") is None:
        reasons.update(("body_unavailable", fact_reason(item, "body")))
        categories.add("body_unavailable")
        if fact_reason(item, "body") in {"disputed", "withheld"}:
            categories.add(fact_reason(item, "body"))
    if assignment_id is None:
        reasons.add("missing_record")
        categories.add("missing_record")
    else:
        assignment = records[assignment_id]
        row["assignment_id"] = assignment_id
        _references(assignment, dependencies, budget)
        decision = known(assignment, "decision")
        if decision != "admitted":
            if decision in {"disputed", "withheld", "provisional", "unclassified"}:
                categories.add(decision)
                reasons.add(decision)
            else:
                reason = fact_reason(assignment, "decision")
                reasons.update((reason, "unresolved_assignment"))
                categories.add(reason if reason in {"disputed", "withheld"} else "unresolved")
        for field in ("class_id", "basis", "asserted_by"):
            if known(assignment, field) is None:
                reason = fact_reason(assignment, field)
                reasons.update((reason, "unresolved_assignment"))
                categories.add(reason if reason in {"disputed", "withheld"} else "unresolved")
        if classes is None:
            reason = fact_reason(frame, "classes")
            reasons.update((reason, "unresolved_assignment"))
            categories.add(reason if reason in {"disputed", "withheld"} else "unresolved")
        elif known(assignment, "class_id") not in classes:
            reasons.add("unresolved_assignment")
            categories.add("unresolved")
        assignment_contrary = _direct_contrary(assignment, records, budget)
        candidates = review_index.get((assignment_id, "assignment_resolution"), ())
        if candidates or assignment_contrary:
            resolution = evaluate_reviews(
                records, assignment_id, "assignment_resolution", scope_id,
                review_index=review_index, budget=budget,
            )
            row["resolution"] = resolution
            dependencies.update(resolution["dependency_ids"])
            support_ids.update(resolution["support_ids"])
            contrary.update(resolution["contrary_ids"])
            resolved = set(resolution["values"]["resolved_ids"])
            active_explicit = assignment_contrary - resolved
            # A qualified review of this exact assignment is the only path
            # that can resolve the assignment's explicit opposing premises.
            if assignment_contrary and resolution["assessment"] != "supported_under_scope":
                active_explicit = assignment_contrary
            active_reviews = [review for review in resolution["values"]["reviews"]
                              if review["selected"] and not review["resolved"]]
            opposing_reviews = any(review["verdict"] != "supports"
                                   or "disputed" in review["reason_codes"]
                                   for review in active_reviews)
            if active_explicit or opposing_reviews:
                reasons.add("disputed")
                reasons.update(resolution["reason_codes"])
                categories.add("disputed")
        contrary.update(assignment_contrary)
    if categories:
        row["primary_reason"] = next(value for value in PRIMARY_REASONS if value in categories)
    else:
        row["class_id"] = known(records[assignment_id], "class_id")
        support_ids.add(assignment_id)
    row["reason_codes"] = sorted(reasons)
    return row, support_ids, contrary


def _metrics(counts, admitted, total, *, classes_known):
    if not classes_known:
        support = unavailable("prerequisite_unavailable")
        sci = diversity = unavailable("prerequisite_unavailable")
    else:
        support = available(sum(count > 0 for count in counts.values()))
        sci = ratio(sum(count * count for count in counts.values()), admitted * admitted,
                    empty_reason="empty_admitted_population")
        diversity = ratio(admitted * admitted - sum(count * count for count in counts.values()),
                          admitted * admitted, empty_reason="empty_admitted_population")
    return {
        "A": available(admitted), "U": available(total - admitted),
        "assignment_coverage": ratio(admitted, total), "observed_support": support,
        "SCI": sci, "D": diversity,
    }


def build_profile(records: dict, snapshot_id: str, scope_id: str, *,
                  population="selected", member_ids=None, budget=None) -> tuple[dict, dict]:
    """Return safe accounting and private, source-bearing comparison context.

    An explicit ``member_ids`` fixes the denominator of a justified matched
    cohort. Callers must establish membership, pairing and validity prerequisites
    first; this routine never silently drops one of those named endpoints.
    """
    budget = budget if budget is not None else RequestBudget()
    snapshot = records[snapshot_id]
    frame = records[snapshot["frame_id"]]
    dependencies = {scope_id}
    support_ids = set()
    contrary_ids = set()
    member_rows = []
    validity_rows = []
    # Live lists contain completed rows only. The API can preserve these
    # witnesses if a later edge reservation fails, without inventing partial
    # distribution metrics or repeatedly copying a growing dossier view.
    budget.profile_progress = {
        "snapshot_id": snapshot_id, "frame_id": frame["id"], "population": population,
        "member_reasons": member_rows, "validity_members": validity_rows,
        "dependency_ids": dependencies, "support_ids": support_ids, "contrary_ids": contrary_ids,
    }
    for record in (snapshot, frame):
        _references(record, dependencies, budget)
        contrary_ids.update(_direct_contrary(record, records, budget))
    premise_contrary = set(contrary_ids)
    reasons = {"disputed"} if premise_contrary else set()
    members = tuple(sorted(snapshot["members"]))
    membership_complete = known(snapshot, "membership") == "complete"
    if not membership_complete:
        reasons.add("unknown_membership")
        if known(snapshot, "membership") is None:
            reasons.add(fact_reason(snapshot, "membership"))
    assignments = {row["item_id"]: row["assignment_id"] for row in snapshot.get("assignments", [])}
    validity_ids = {row["item_id"]: row["validity_id"] for row in snapshot.get("validities", [])}
    # One index prevents a per-item scan of every record and review.
    review_index = make_review_index(records)
    class_rows = known(frame, "classes")
    classes = None if class_rows is None else {row["id"] for row in class_rows}
    if classes is None:
        reasons.add(fact_reason(frame, "classes"))
    validity = {}
    if population == "confirmed_valid":
        for item_id in members:
            budget.charge()
            dependencies.add(item_id)
            row, contrary = _validity(item_id, validity_ids.get(item_id), frame, records, dependencies, budget)
            validity_rows.append(row)
            validity[item_id] = row["state"]
            contrary_ids.update(contrary)
            reasons.update(row["reason_codes"])
            if row["state"] in {"valid", "invalid"}:
                support_ids.add(row["validity_id"])
    if member_ids is not None:
        cohort = tuple(sorted(member_ids))
        if len(set(cohort)) != len(cohort) or not set(cohort).issubset(members):
            raise ValueError("invalid_matched_cohort")
        if population == "confirmed_valid" and any(validity[item] != "valid" for item in cohort):
            raise ValueError("invalid_matched_validity")
        count_scope = "matched_cohort"
    elif population == "confirmed_valid":
        cohort = tuple(item for item in members if validity[item] == "valid")
        count_scope = "confirmed_valid_subset"
    else:
        cohort = members
        count_scope = "known_roster"
    count_complete = member_ids is not None or population == "confirmed_valid" or membership_complete
    population_complete = membership_complete and not premise_contrary
    if population == "confirmed_valid":
        population_complete = population_complete and all(state in {"valid", "invalid"} for state in validity.values())
    if member_ids is not None:
        population_complete = not premise_contrary
    counts = {identity: 0 for identity in sorted(classes or ())}
    admitted = {}
    reason_counts = Counter()
    for item_id in cohort:
        budget.charge()
        row, support, contrary = _assignment(
            item_id, assignments.get(item_id), frame, classes, records, scope_id,
            review_index, dependencies, budget,
        )
        member_rows.append(row)
        support_ids.update(support)
        contrary_ids.update(contrary)
        reasons.update(row["reason_codes"])
        reason_counts.update(row["reason_codes"])
        if row["primary_reason"] == "admitted":
            admitted[item_id] = row["class_id"]
            counts[row["class_id"]] += 1
    local = _metrics(counts, len(admitted), len(cohort), classes_known=classes is not None)
    entry = {
        "snapshot_id": snapshot_id, "frame_id": frame["id"], "population": population,
        "count_scope": count_scope, "membership_complete": membership_complete,
        "population_complete": population_complete,
        "K": available(len(members)),
        "N": available(len(cohort)) if count_complete else unavailable("unknown_membership"),
        **local,
        "class_counts": [{"class_id": identity, "count": available(counts[identity])} for identity in sorted(counts)],
        "member_reasons": member_rows,
        "reason_counts": [{"reason": reason, "count": available(count)} for reason, count in sorted(reason_counts.items())],
        "known_subset": dict(local), "tails": [],
    }
    if not count_complete:
        for field in ("assignment_coverage", "SCI", "D"):
            entry[field] = unavailable("unknown_membership")
    if population == "confirmed_valid":
        validity_counts = Counter(validity.values())
        entry.update({
            "V": available(len(cohort)),
            "validity_coverage": ratio(validity_counts["valid"] + validity_counts["invalid"], len(members))
                                 if membership_complete else unavailable("unknown_membership"),
            "validity_counts": [{"state": state, "count": available(validity_counts[state])} for state in VALIDITY_STATES],
            "validity_members": validity_rows,
        })
    tails = known(frame, "tail_designations")
    tail_results = {row["class_id"]: row["evidence_ids"] for row in known(snapshot, "tail_results") or []}
    if tails is None:
        reasons.add(fact_reason(frame, "tail_designations"))
    distribution_complete = count_complete and classes is not None and len(admitted) == len(cohort) and not premise_contrary
    for designation in sorted(tails or (), key=lambda row: row["class_id"]):
        identity = designation["class_id"]
        tail_reasons = set()
        count = counts.get(identity, 0)
        if classes is None:
            state = "unestablished"
            tail_reasons.add("prerequisite_unavailable")
        elif count > 0:
            state = "present"
        elif distribution_complete:
            state = "absent" if cohort else "absent_in_empty_population"
            if not cohort:
                tail_reasons.add("absent_in_empty_population")
        else:
            state = "unestablished"
            if not count_complete:
                tail_reasons.add("unknown_membership")
            if len(admitted) != len(cohort):
                tail_reasons.add("unresolved_assignment")
            if premise_contrary:
                tail_reasons.add("disputed")
        evidence_ids = sorted(tail_results.get(identity, []))
        for eid in evidence_ids:
            budget.charge()
            dependencies.add(eid)
        entry["tails"].append({
            "class_id": identity, "count": available(count) if classes is not None else unavailable("prerequisite_unavailable"),
            "state": state, "reason_codes": sorted(tail_reasons), "evidence_ids": evidence_ids,
        })
    context = {
        "snapshot": snapshot, "frame": frame, "members": members, "cohort_members": cohort,
        "membership_complete": membership_complete, "classes_known": classes is not None,
        "population_complete": population_complete, "distribution_complete": distribution_complete,
        "premise_contrary_ids": sorted(premise_contrary),
        "admitted": admitted, "assignments": assignments, "validity": validity,
        "dependency_ids": sorted(dependencies), "support_ids": sorted(support_ids),
        "contrary_ids": sorted(contrary_ids), "reason_codes": sorted(reasons),
    }
    budget.profile_progress = None
    return entry, context


def _finding(request, entry, context, rule, subjects, reasons, *, state="not_assessed"):
    return {
        "family": "EC104", "request_id": request["id"], "scope_id": request["scope_id"],
        "subject_ids": sorted(set(subjects)), "rule": rule, "assessment": state,
        "reason_codes": sorted(set(reasons)),
        "basis": [{"kind": "local_calculation", "record_ids": context["dependency_ids"]}],
        "support_ids": context["support_ids"], "contrary_ids": context["contrary_ids"],
        "limitations": ["Counts are conditional on the selected supplied assignment and population view."],
        "needed_information": "Inspect the named population and its unresolved member premises before interpreting coverage or absence.",
    }


def profile_request(dossier: dict, request: dict, *, budget=None) -> tuple[dict, list]:
    budget = budget if budget is not None else RequestBudget()
    records = {record["id"]: record for record in dossier["records"]}
    profiles = []
    findings = []
    dependencies = {request["scope_id"], request["snapshot_id"]}
    support_ids = set()
    contrary_ids = set()
    reasons = set()

    def envelope(execution):
        return {
            "request_id": request["id"], "operation": "profile", "scope_id": request["scope_id"],
            "selection": "selected", "applicability": "applicable", "execution": execution,
            "assessment": "not_assessed", "reason_codes": sorted(reasons | ({"resource_limit"} if execution == "partial" else set())),
            "values": {"profiles": list(profiles)},
            "basis": [{"kind": "supplied_assertion", "record_ids": sorted(dependencies)},
                      {"kind": "local_calculation", "record_ids": sorted(dependencies)}],
            "support_ids": sorted(support_ids), "contrary_ids": sorted(contrary_ids),
            "dependency_ids": sorted(dependencies),
            "limitations": [
                "Structural arithmetic is conditional on supplied bodies, selected assignments and declared class meanings.",
                "Known-subset and confirmed-valid counts do not establish the unseen population or model performance.",
                "Tail results retain supplied evidence references without independently evaluating their content.",
            ] + (["Only completed population profiles are retained; the remaining population analysis was not completed."]
                 if execution == "partial" else []),
        }

    budget.partial_result = envelope("partial")
    budget.partial_findings = []
    populations = ("selected", "confirmed_valid") if request.get("population", "selected") == "confirmed_valid" else ("selected",)
    for population in populations:
        entry, context = build_profile(records, request["snapshot_id"], request["scope_id"], population=population, budget=budget)
        profiles.append(entry)
        dependencies.update(context["dependency_ids"])
        support_ids.update(context["support_ids"])
        contrary_ids.update(context["contrary_ids"])
        reasons.update(context["reason_codes"])
        findings.append(_finding(request, entry, context, "structural_distribution_" + population,
                                 [entry["snapshot_id"], entry["frame_id"]], context["reason_codes"]))
        # Group the fixed tail states, retaining every class ID. Repeating an
        # entire population premise list once per zero-count class would grow
        # quadratically with a large declared tail roster.
        tail_groups = {}
        for tail in entry["tails"]:
            tail_groups.setdefault(tail["state"], []).append(tail)
        for state, tails in sorted(tail_groups.items()):
            findings.append(_finding(request, entry, context,
                                     "declared_tail_" + population + "_" + state,
                                     [entry["snapshot_id"], entry["frame_id"], *(tail["class_id"] for tail in tails)],
                                     [reason for tail in tails for reason in tail["reason_codes"]]))
        budget.partial_result = envelope("partial")
        budget.partial_findings = list(findings)
    return envelope("completed"), findings
