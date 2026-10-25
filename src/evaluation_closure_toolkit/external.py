"""Member-bound external contact, separate from externality and use suitability."""

from collections import defaultdict

from .budget import RequestBudget
from .evidence import evaluate_reviews, fact_reason, known, make_review_index, member_relevant
from .provenance import (
    fact_state, finding, known_reasons, reference_record, restrict_support, result_shell,
)
from .structural import available, unavailable

STAGES = ("received", "retained", "selected", "used")
STATES = ("yes", "no", "disputed", "unresolved")
QUALIFICATIONS = ("supported_under_scope", "contradicted_under_scope", "unresolved")
EVENT_KINDS = frozenset({"process_record", "observation_record", "intervention_record"})


def _review(records, cohort, member, criterion, scope, index, selections, budget):
    result = evaluate_reviews(records, cohort["id"], criterion, scope["id"],
                              member_id=member, review_index=index, budget=budget)
    fields = ("boundary",) if criterion == "externality" else ("purpose",)
    reasons = known_reasons(cohort, fields)
    reasons |= known_reasons(scope, ("window",))
    if criterion != "retention":
        field = "externality_reviews" if criterion == "externality" else "qualifications"
        chosen = selections[field].get(member)
        if chosen is None:
            reasons.add("missing_record")
        else:
            row = next(r for r in result["values"]["reviews"] if r["review_id"] == chosen)
            # An explicitly selected review can be replaced only by an exact,
            # qualified resolution, never by a convenient unrelated support row.
            if not row["selected"]:
                reasons.add("scope_mismatch")
            elif not row["resolved"] and (not row["qualified"] or row["verdict"] != "supports"):
                reasons.update(row["reason_codes"] or ["prerequisite_unavailable"])
    restrict_support(result, reasons)
    return result


def _event(event, cohort, scope, records, retention, dependencies, contrary, budget):
    local_contrary = set()
    reference_record(event, records, dependencies, local_contrary, budget)
    reasons = known_reasons(event, ("asserted_by", "verdict", "occurred_at", "checkpoint"))
    reasons |= known_reasons(cohort, ("checkpoint",))
    reasons |= known_reasons(scope, ("window",))
    verdict = known(event, "verdict")
    if verdict == "unknown":
        reasons.add("unknown_value")
    window, time = known(scope, "window"), known(event, "occurred_at")
    relevant = True
    if window is not None and time is not None and not window["start"] <= time < window["end"]:
        reasons.add("scope_mismatch")
        relevant = False
    checkpoint = known(event, "checkpoint")
    if checkpoint is not None and known(cohort, "checkpoint") is not None and checkpoint != known(cohort, "checkpoint"):
        reasons.add("scope_mismatch")
        relevant = False
    if event["stage"] in {"used", "selected"}:
        reasons |= known_reasons(event, ("purpose",)) | known_reasons(cohort, ("purpose",))
        if known(event, "purpose") is not None and known(cohort, "purpose") is not None and known(event, "purpose") != known(cohort, "purpose"):
            reasons.add("scope_mismatch")
            relevant = False
    if event["stage"] == "used":
        reasons |= known_reasons(event, ("target_id",))
        if known(event, "target_id") is not None:
            dependencies.add(known(event, "target_id"))
    if event["stage"] == "retained":
        reasons |= known_reasons(event, ("representation",))
        if retention["assessment"] != "supported_under_scope":
            reasons.update(retention["reason_codes"] or ["prerequisite_unavailable"])
    evidence_ids = event.get("evidence_ids", [])
    if not evidence_ids:
        reasons.add("missing_record")
    member_seen = False
    for identity in evidence_ids:
        budget.charge()
        evidence = records[identity]
        if evidence["scope_id"] != scope["id"]:
            reasons.add("scope_mismatch")
        if known(evidence, "kind") not in EVENT_KINDS:
            reasons.add("prerequisite_unavailable")
        if known(evidence, "access") != "supplied":
            reasons.add("access_gap")
        if known(evidence, "content") is None:
            reasons.add("body_unavailable")
        if known(evidence, "producer_id") is None:
            reasons.add(fact_reason(evidence, "producer_id"))
        else:
            dependencies.add(known(evidence, "producer_id"))
        for subject in evidence.get("subject_ids", []):
            budget.charge()
            if subject in {event["member_id"], event["id"]}:
                member_seen = True
    if not member_seen:
        reasons.add("prerequisite_unavailable")
    if local_contrary:
        reasons.add("disputed")
    contrary.update(local_contrary)
    return {
        "event_id": event["id"], "verdict": verdict or "unresolved",
        "qualified": not reasons, "relevant": relevant,
        "reason_codes": sorted(reasons), "support_ids": sorted(evidence_ids),
        "contrary_ids": sorted(local_contrary),
        "target_ids": [known(event, "target_id")] if known(event, "target_id") is not None else [],
        "time_state": fact_state(event, "occurred_at"),
        "checkpoint_state": fact_state(event, "checkpoint"),
        "purpose_state": fact_state(event, "purpose"),
        "representation_state": fact_state(event, "representation"),
    }


def _stage(rows, common_reasons):
    verdicts = {row["verdict"] for row in rows if row["qualified"]}
    asserted = {row["verdict"] for row in rows if row["relevant"] and row["verdict"] in {"yes", "no"}}
    disputed = len(asserted) > 1 or any("disputed" in row["reason_codes"] for row in rows if row["relevant"])
    reasons = set(common_reasons)
    if disputed or "disputed" in reasons:
        state = "disputed"
        reasons.add("disputed")
    elif len(verdicts) == 1 and not reasons:
        state = next(iter(verdicts))
    else:
        state = "unresolved"
        for row in rows:
            reasons.update(row["reason_codes"])
        if not rows:
            reasons.add("missing_record")
    return {"state": state, "reason_codes": sorted(reasons), "events": rows}


def external_request(dossier, request, *, budget=None):
    budget = budget or RequestBudget()
    records = {r["id"]: r for r in dossier["records"]}
    cohort, scope = records[request["cohort_id"]], records[request["scope_id"]]
    members = sorted(cohort["members"])
    complete = known(cohort, "membership") == "complete"
    values = {
        "cohort_id": cohort["id"],
        "membership": known(cohort, "membership") or fact_state(cohort, "membership"),
        "membership_state": fact_state(cohort, "membership"),
        "known_member_count": available(len(members)), "member_states": [],
        "count_scope": "complete_cohort" if complete else "known_subset",
        "full_member_count": available(len(members)) if complete else unavailable("unknown_membership"),
        "stage_counts": {stage: {state: unavailable("resource_limit") for state in STATES} for stage in STAGES},
        "event_counts": {stage: unavailable("resource_limit") for stage in STAGES},
        "externality_counts": {state: unavailable("resource_limit") for state in QUALIFICATIONS},
        "qualification_counts": {state: unavailable("resource_limit") for state in QUALIFICATIONS},
        "carryover_ids": sorted(cohort.get("carryover_ids", [])),
        "checkpoint_state": fact_state(cohort, "checkpoint"),
        "purpose_state": fact_state(cohort, "purpose"),
        "boundary_state": fact_state(cohort, "boundary"),
        "window_state": fact_state(scope, "window"),
        "accounting_complete": False,
    }
    result = result_shell(request, values, [
        "Counts describe unique captured contribution members at the referenced cohort checkpoint, purpose and half-open scope window; raw event counts are separate.",
        "Receipt, retention, selection and use are independent axes. No missing stage is inferred from another stage.",
        "Externality and suitability for the named use require separate member-bound documentary reviews; no provider, human or freshness heuristic is used.",
        "Carryover records preserve earlier grounding and cannot supply new current-window contact. No presence score, causal effect or simulation mixing weight is computed.",
        "Event, checkpoint, purpose and representation facts remain referenced in the dossier. Qualification does not authenticate their content or establish open evaluation.",
    ])
    budget.partial_result = result
    dependencies, contrary, support = {scope["id"], cohort["id"], *members}, set(), set()
    index = make_review_index(records)
    selections = {field: {r["member_id"]: r["review_id"] for r in cohort.get(field, [])}
                  for field in ("externality_reviews", "qualifications")}
    events = defaultdict(list)
    try:
        reference_record(cohort, records, dependencies, contrary, budget)
        for record in sorted(records.values(), key=lambda r: r["id"]):
            budget.charge()
            if record["type"] == "external_event" and record["cohort_id"] == cohort["id"]:
                events[(record["member_id"], record["stage"])].append(record)
        for member in members:
            budget.charge()
            row = {"member_id": member, "stages": {}, "externality": {}, "qualification": {},
                   "retention_review": {}, "carryover": member in values["carryover_ids"],
                   "contact_state": "unresolved", "completed": False}
            values["member_states"].append(row)
            common = set()
            cohort_contrary = set(cohort.get("contrary_ids", []))
            for eid in cohort.get("evidence_ids", []):
                budget.charge()
                cohort_contrary.update(records[eid].get("contrary_ids", []))
            for rid in sorted(cohort_contrary):
                budget.charge()
                if member_relevant(records[rid], cohort["id"], member, records, budget):
                    common.add("disputed")
            for stage in STAGES:
                if stage == "retained":
                    row["retention_review"] = _review(records, cohort, member, "retention", scope, index, selections, budget)
                    criterion = row["retention_review"]
                    dependencies.update(criterion["dependency_ids"])
                    support.update(criterion["support_ids"])
                    contrary.update(criterion["contrary_ids"])
                stage_rows = []
                # Publish completed event decisions even if the next event hits a limit.
                row["stages"][stage] = {"state": "unresolved", "reason_codes": ["resource_limit"], "events": stage_rows}
                for event in events.get((member, stage), ()):
                    budget.charge()
                    detail = _event(event, cohort, scope, records, row["retention_review"], dependencies, contrary, budget)
                    stage_rows.append(detail)
                    if detail["qualified"]:
                        support.update([event["id"], *detail["support_ids"]])
                row["stages"][stage] = _stage(stage_rows, common)
            for name, criterion_name in (("externality", "externality"), ("qualification", "input_qualification")):
                criterion = _review(records, cohort, member, criterion_name, scope, index, selections, budget)
                row[name] = criterion
                dependencies.update(criterion["dependency_ids"])
                support.update(criterion["support_ids"])
                contrary.update(criterion["contrary_ids"])
            if row["carryover"]:
                row["contact_state"] = "carryover_only"
            elif (all(row["stages"][stage]["state"] == "yes" for stage in ("received", "used"))
                  and all(row[axis]["assessment"] == "supported_under_scope" for axis in ("externality", "qualification"))):
                row["contact_state"] = "documented_current_contact"
            row["completed"] = True
        for stage in STAGES:
            values["stage_counts"][stage] = {state: available(sum(r["stages"][stage]["state"] == state for r in values["member_states"])) for state in STATES}
            values["event_counts"][stage] = available(sum(len(events[(m, stage)]) for m in members))
        for axis, key in (("externality", "externality_counts"), ("qualification", "qualification_counts")):
            values[key] = {state: available(sum(r[axis]["assessment"] == state for r in values["member_states"])) for state in QUALIFICATIONS}
        values["accounting_complete"] = True
        result["execution"], result["reason_codes"] = "completed", [] if complete else ["unknown_membership"]
    finally:
        result["dependency_ids"] = sorted(dependencies)
        result["support_ids"], result["contrary_ids"] = sorted(support), sorted(contrary)
        result["basis"] = [{"kind": "supplied_assertion", "record_ids": sorted(dependencies)}]
        if support:
            result["basis"].append({"kind": "supplied_review", "record_ids": sorted(rid for rid in support if records[rid]["type"] == "review")})
        reasons = set(result["reason_codes"])
        for row in values["member_states"]:
            for stage in row["stages"].values():
                reasons.update(stage["reason_codes"])
            for name in ("externality", "qualification", "retention_review"):
                reasons.update(row[name].get("reason_codes", []))
        findings = [finding(result, "EC103", "external_contact_accounting", [cohort["id"]], reasons,
                            "Inspect each member's separate stage and qualification decisions; missing logs remain unresolved.")]
        budget.partial_findings = findings
    return result, findings
