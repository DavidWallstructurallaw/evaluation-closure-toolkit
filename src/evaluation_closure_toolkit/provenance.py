"""Small shared report helpers for typed lineage and external contact."""

from .evidence import fact_reason, known


def result_shell(request, values, limitations):
    return {
        "request_id": request["id"], "operation": request["operation"],
        "scope_id": request["scope_id"], "selection": "selected",
        "applicability": "applicable", "execution": "partial",
        "assessment": "not_assessed", "reason_codes": ["resource_limit"],
        "values": values, "basis": [], "support_ids": [], "contrary_ids": [],
        "dependency_ids": [request["scope_id"]], "limitations": limitations,
    }


def reference_record(record, records, dependencies, contrary, budget):
    """Retain attribution and explicit premise IDs without copying sensitive text."""
    dependencies.add(record["id"])
    for field in ("evidence_ids", "contrary_ids"):
        for identity in record.get(field, []):
            budget.charge()
            dependencies.add(identity)
            if field == "contrary_ids":
                contrary.add(identity)
            for ref in records[identity].get("contrary_ids", []):
                budget.charge()
                dependencies.add(ref)
                contrary.add(ref)
    for field in ("asserted_by", "producer_id", "assessor_id"):
        actor = known(record, field)
        if actor is not None:
            dependencies.add(actor)
    for fact in record.values():
        if isinstance(fact, dict) and "state" in fact:
            for identity in fact.get("evidence_ids", []):
                budget.charge()
                dependencies.add(identity)


def fact_state(record, field):
    return record.get(field, {}).get("state", "missing")


def known_reasons(record, fields):
    return {fact_reason(record, field) for field in fields if known(record, field) is None}


def restrict_support(criterion, reasons):
    """Keep original qualified reviews visible while missing prerequisites block support."""
    if reasons:
        criterion["reason_codes"] = sorted(set(criterion["reason_codes"]) | set(reasons))
        if criterion["assessment"] == "supported_under_scope":
            criterion["assessment"] = "unresolved"


def finding(result, family, rule, subjects, reasons, needed, assessment="not_assessed"):
    return {
        "family": family, "request_id": result["request_id"],
        "scope_id": result["scope_id"], "subject_ids": sorted(set(subjects)),
        "rule": rule, "assessment": assessment, "reason_codes": sorted(set(reasons)),
        "basis": result["basis"], "support_ids": result["support_ids"],
        "contrary_ids": result["contrary_ids"], "limitations": result["limitations"],
        "needed_information": needed,
    }
