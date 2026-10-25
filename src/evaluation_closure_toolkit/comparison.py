"""Scoped descriptive and fixed-cohort contrasts over supplied assignments."""

from __future__ import annotations

from fractions import Fraction

from .budget import RequestBudget
from .evidence import evaluate_reviews, fact_reason, known
from .structural import available, build_profile, unavailable, undefined


_SEMANTIC_FIELDS = ("task", "context", "horizon", "resolution", "exclusions")
_POLICY_FIELDS = ("selection_policy", "admission_policy")
_LIMITATIONS = [
    "Distributions and deltas are conditional on the selected attributed assignments; arithmetic does not establish scientific validity, fidelity, model recovery or capability.",
    "Descriptive contrasts retain each side's admitted denominator. Matched contrasts use every member of the fixed complete pair roster without complete-case deletion.",
    "Tail conclusions are restricted to the reported population and captured frames; zero admitted sightings do not alone establish complete-population absence.",
]


def _rational(value: Fraction) -> dict:
    return {"state": "available", "value": {
        "numerator": str(value.numerator), "denominator": str(value.denominator)}}


def _fraction(metric: dict) -> Fraction:
    value = metric["value"]
    if type(value) is int:
        return Fraction(value)
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def _delta(before: dict, after: dict) -> dict:
    if before["state"] == "unavailable" or after["state"] == "unavailable":
        return unavailable("prerequisite_unavailable")
    if before["state"] == "undefined" or after["state"] == "undefined":
        return undefined("empty_admitted_population")
    return _rational(_fraction(after) - _fraction(before))


def _new_result(request: dict) -> dict:
    return {
        "request_id": request["id"], "operation": "compare", "scope_id": request["scope_id"],
        "selection": "selected", "applicability": "applicable", "execution": "partial",
        "assessment": "not_assessed", "reason_codes": ["resource_limit"],
        "values": {
            "before": {}, "after": {}, "mode": request["mode"],
            "catalog_profiles": {"before": [], "after": []},
            "compatibility": {"state": "unavailable", "reason_codes": ["resource_limit"], "field_checks": []},
            "pair_count": unavailable("inapplicable" if request["mode"] == "descriptive" else "resource_limit"),
            "pair_gaps": [], "delta_SCI": unavailable("resource_limit"),
            "delta_D": unavailable("resource_limit"), "tail_changes": [],
            "new_observations": unavailable("resource_limit"),
        },
        "basis": [], "support_ids": [], "contrary_ids": [],
        "dependency_ids": [request["scope_id"]], "limitations": list(_LIMITATIONS),
    }


def _inherit(result: dict, context: dict) -> None:
    for key in ("dependency_ids", "support_ids", "contrary_ids"):
        result[key] = sorted(set(result[key]) | set(context.get(key, [])))


def _review(result: dict, records: dict, target_id: str, criterion: str,
            request: dict, budget: RequestBudget) -> dict:
    kwargs = {"budget": budget}
    if criterion == "matching_basis":
        kwargs["request_id"] = request["id"]
    assessment = evaluate_reviews(records, target_id, criterion, request["scope_id"], **kwargs)
    _inherit(result, assessment)
    result["basis"].extend(assessment["basis"])
    return assessment


def _check(checks: list, field: str, reasons=()) -> None:
    reasons = sorted(set(reasons))
    checks.append({"field": field, "state": "unavailable" if reasons else "compatible",
                   "reason_codes": reasons})


def _compare_fact(before: dict, after: dict, field: str, *, exact: bool,
                  mismatch: str) -> list:
    reasons = []
    for record in (before, after):
        if known(record, field) is None:
            reasons.append(fact_reason(record, field))
    if not reasons and exact and known(before, field) != known(after, field):
        reasons.append(mismatch)
    return sorted(set(reasons))


def _compatibility(result: dict, records: dict, request: dict,
                   before: dict, after: dict, budget: RequestBudget) -> tuple[dict, dict]:
    """Return documentary compatibility and a total authorized class mapping."""
    checks = []
    compatibility = {"state": "unavailable", "reason_codes": [], "field_checks": checks}
    old_frame, new_frame = before["frame"], after["frame"]
    same_frame = old_frame["id"] == new_frame["id"]
    mapping = {}
    frame_reasons = ["disputed"] if before.get("premise_contrary_ids") or after.get("premise_contrary_ids") else []
    semantic_review = False
    if same_frame:
        classes = known(old_frame, "classes")
        if classes is None:
            frame_reasons.append(fact_reason(old_frame, "classes"))
        else:
            mapping = {row["id"]: row["id"] for row in classes}
    else:
        revision = records.get(request.get("revision_id"))
        if revision is None:
            frame_reasons.extend(["incompatible_frame", "missing_record"])
        else:
            result["dependency_ids"] = sorted(set(result["dependency_ids"]) | {revision["id"]})
            review = _review(result, records, revision["id"], "frame_equivalence", request, budget)
            compatibility["frame_equivalence"] = review
            semantic_review = review["assessment"] == "supported_under_scope"
            if known(revision, "kind") != "relabel":
                frame_reasons.append("incompatible_frame")
                if known(revision, "kind") is None:
                    frame_reasons.append(fact_reason(revision, "kind"))
            if not semantic_review:
                frame_reasons.extend(["incompatible_frame", *review["reason_codes"]])
            old_classes, new_classes = known(old_frame, "classes"), known(new_frame, "classes")
            map_reasons = []
            if old_classes is None or new_classes is None:
                map_reasons.append("incompatible_frame")
                for frame in (old_frame, new_frame):
                    if known(frame, "classes") is None:
                        map_reasons.append(fact_reason(frame, "classes"))
            else:
                rows = revision.get("class_map", [])
                budget.charge(len(rows))
                old_ids = {row["id"] for row in old_classes}
                new_ids = {row["id"] for row in new_classes}
                from_ids = [row["from_class"] for row in rows]
                to_ids = [row["to_class"] for row in rows]
                if (set(from_ids) != old_ids or set(to_ids) != new_ids
                        or len(from_ids) != len(set(from_ids)) or len(to_ids) != len(set(to_ids))):
                    map_reasons.append("incompatible_frame")
                else:
                    mapping = dict(zip(from_ids, to_ids))
            _check(checks, "class_map", map_reasons)
            frame_reasons.extend(map_reasons)
            if frame_reasons:
                mapping = {}
    _check(checks, "frame", frame_reasons)
    for field in _SEMANTIC_FIELDS:
        budget.charge()
        reasons = _compare_fact(old_frame, new_frame, field,
                                exact=same_frame or not semantic_review, mismatch="incompatible_frame")
        _check(checks, field, reasons)
    for field in _POLICY_FIELDS:
        budget.charge()
        _check(checks, "frame_" + field,
               _compare_fact(old_frame, new_frame, field, exact=True, mismatch="incompatible_policy"))
    _check(checks, "snapshot_selection_policy", _compare_fact(
        before["snapshot"], after["snapshot"], "selection_policy", exact=True, mismatch="incompatible_policy"))
    if request.get("population", "selected") == "confirmed_valid":
        _check(checks, "validity_rubric", _compare_fact(
            old_frame, new_frame, "validity_rubric", exact=True, mismatch="incompatible_policy"))
    for name, context in (("before", before), ("after", after)):
        membership_reasons = [] if context["membership_complete"] else ["unknown_membership"]
        if known(context["snapshot"], "membership") is None:
            membership_reasons.append(fact_reason(context["snapshot"], "membership"))
        _check(checks, name + "_membership", membership_reasons)
    return compatibility, mapping


def _pair_checks(result: dict, records: dict, request: dict, before: dict,
                 after: dict, compatibility: dict, budget: RequestBudget) -> bool:
    pairs = sorted(request.get("pairs", []), key=lambda p: (p["before_item_id"], p["after_item_id"]))
    complete = known(request, "pair_membership") == "complete"
    membership_reasons = [] if complete else ["incomplete_pairs"]
    if known(request, "pair_membership") is None:
        membership_reasons.append(fact_reason(request, "pair_membership"))
    _check(compatibility["field_checks"], "pair_membership", membership_reasons)
    result["values"]["pair_count"] = available(len(pairs)) if complete else unavailable("incomplete_pairs")
    before_members, after_members = set(before["members"]), set(after["members"])
    identity_matches = True
    pair_dependencies = set(result["dependency_ids"])
    gaps = []
    for pair in pairs:
        budget.charge()
        bid, aid = pair["before_item_id"], pair["after_item_id"]
        pair_dependencies.update((bid, aid))
        reasons = set()
        if bid not in before_members or aid not in after_members:
            reasons.add("missing_record")
        if bid not in before["admitted"] or aid not in after["admitted"]:
            reasons.add("unresolved_assignment")
        if request.get("population", "selected") == "confirmed_valid":
            if before["validity"].get(bid) != "valid" or after["validity"].get(aid) != "valid":
                reasons.add("prerequisite_unavailable")
        same_identity = records[bid]["logical_id"] == records[aid]["logical_id"]
        identity_matches = identity_matches and same_identity
        gaps.append((pair, reasons, same_identity))
    result["dependency_ids"] = sorted(pair_dependencies)
    matching_qualified = identity_matches
    has_matching_reviews = any(record["type"] == "review"
                               and record["target_id"] == request["scope_id"]
                               and record["criterion"] == "matching_basis"
                               and record.get("request_id") == request["id"]
                               for record in records.values())
    if not identity_matches or has_matching_reviews:
        review = _review(result, records, request["scope_id"], "matching_basis", request, budget)
        compatibility["matching_basis"] = review
        active_conflict = any(row["selected"] and not row["resolved"]
                              and (row["verdict"] != "supports" or "disputed" in row["reason_codes"])
                              for row in review["values"]["reviews"])
        matching_qualified = (identity_matches or review["assessment"] == "supported_under_scope") and not active_conflict
        _check(compatibility["field_checks"], "matching_basis", [] if matching_qualified else ["incomplete_pairs", *review["reason_codes"]])
    else:
        _check(compatibility["field_checks"], "matching_basis")
    for pair, reasons, same_identity in gaps:
        if not matching_qualified:
            reasons.add("incomplete_pairs")
        if reasons:
            result["values"]["pair_gaps"].append({
                "before_item_id": pair["before_item_id"], "after_item_id": pair["after_item_id"],
                "reason_codes": sorted(reasons),
            })
    return complete and matching_qualified and not result["values"]["pair_gaps"]


def _tail_status(entry: dict, count: dict, *, distribution_complete: bool) -> str:
    if count["state"] != "available":
        return "unavailable"
    if count["value"] > 0:
        return "present"
    total = entry["N"]
    if distribution_complete and total["state"] == "available" and total["value"] == 0:
        return "absent_in_empty_population"
    if distribution_complete:
        return "absent_in_complete_population"
    return "zero_admitted_sightings"


def _tails(request: dict, before: dict, after: dict, before_context: dict,
           after_context: dict, mapping: dict, budget: RequestBudget) -> list:
    if not before or not after or not mapping:
        return []
    old_tail = {row["class_id"] for row in known(before_context["frame"], "tail_designations") or []}
    new_tail = {row["class_id"] for row in known(after_context["frame"], "tail_designations") or []}
    inverse = {value: key for key, value in mapping.items()}
    ids = old_tail | {inverse[cid] for cid in new_tail if cid in inverse}
    old_counts = {row["class_id"]: row["count"] for row in before["class_counts"]}
    new_counts = {row["class_id"]: row["count"] for row in after["class_counts"]}
    scope = "matched_cohort" if request["mode"] == "matched" else (
        "confirmed_valid_subset" if request.get("population", "selected") == "confirmed_valid" else "selected_catalog")
    rows = []
    for class_id in sorted(ids):
        budget.charge()
        target_id = mapping[class_id]
        old_count = old_counts[class_id]
        new_count = new_counts[target_id]
        old_status = _tail_status(before, old_count, distribution_complete=before_context["distribution_complete"])
        new_status = _tail_status(after, new_count, distribution_complete=after_context["distribution_complete"])
        reasons = []
        if old_status == "unavailable" or new_status == "unavailable":
            change = "unavailable"
            reasons.append("prerequisite_unavailable")
        elif old_status == new_status == "present":
            change = "retained"
        elif old_status == "present" and new_status in {"absent_in_complete_population", "absent_in_empty_population"}:
            if new_status == "absent_in_empty_population":
                reasons.append("absent_in_empty_population")
            complete_before = before_context["distribution_complete"]
            change = "loss" if complete_before else "no_loss_established"
            if not complete_before:
                reasons.append("prerequisite_unavailable")
        else:
            change = "no_loss_established"
            if "zero_admitted_sightings" in (old_status, new_status):
                reasons.append("prerequisite_unavailable")
            if "absent_in_empty_population" in (old_status, new_status):
                reasons.append("absent_in_empty_population")
        rows.append({
            "before_class_id": class_id, "after_class_id": target_id,
            "population": request.get("population", "selected"), "scope": scope,
            "before_count": old_count, "after_count": new_count,
            "before_status": old_status, "after_status": new_status,
            "change": change, "reason_codes": sorted(set(reasons)),
        })
    return rows


def _finding(result: dict, *, family: str, rule: str, reasons: list, subjects: list) -> dict:
    return {
        "family": family, "request_id": result["request_id"], "scope_id": result["scope_id"],
        "subject_ids": sorted(set(subjects)), "rule": rule, "assessment": "not_assessed",
        "reason_codes": sorted(set(reasons)), "basis": list(result["basis"]),
        "support_ids": list(result["support_ids"]), "contrary_ids": list(result["contrary_ids"]),
        "limitations": list(result["limitations"]),
        "needed_information": "Use complete compatible captured populations and qualified exact-scope premises for the requested contrast."
        if family == "EC108" else "Interpret this tail inventory only within the explicitly reported population; fidelity and model capability require separate evidence.",
    }


def compare_request(dossier: dict, request: dict, *, budget=None) -> tuple[dict, list]:
    """Compute catalog or exact-pair metrics without changing population views."""
    if budget is None:
        budget = RequestBudget()
    records = {record["id"]: record for record in dossier["records"]}
    result = _new_result(request)
    budget.partial_result = result
    budget.partial_findings = []
    population = request.get("population", "selected")
    contexts = {}
    for side, snapshot_id in (("before", request["before_id"]), ("after", request["after_id"])):
        selected_entry, selected_context = build_profile(records, snapshot_id, request["scope_id"], budget=budget)
        result["values"]["catalog_profiles"][side].append(selected_entry)
        _inherit(result, selected_context)
        entry, context = selected_entry, selected_context
        if population == "confirmed_valid":
            entry, context = build_profile(records, snapshot_id, request["scope_id"], population=population, budget=budget)
            result["values"]["catalog_profiles"][side].append(entry)
            _inherit(result, context)
        contexts[side] = context
        if request["mode"] == "descriptive":
            result["values"][side] = entry
    before, after = contexts["before"], contexts["after"]
    if (before["membership_complete"] and after["membership_complete"]
            and set(before["members"]) == set(after["members"])):
        result["values"]["new_observations"] = available(0)
    else:
        result["values"]["new_observations"] = unavailable("prerequisite_unavailable")
    compatibility, mapping = _compatibility(result, records, request, before, after, budget)
    pair_ready = True
    if request["mode"] == "matched":
        pair_ready = _pair_checks(result, records, request, before, after, compatibility, budget)
    reasons = {reason for check in compatibility["field_checks"] for reason in check["reason_codes"]}
    if not pair_ready:
        reasons.add("incomplete_pairs")
        reasons.update(reason for row in result["values"]["pair_gaps"] for reason in row["reason_codes"])
    compatibility["field_checks"].sort(key=lambda row: row["field"])
    compatibility["reason_codes"] = sorted(reasons)
    compatibility["state"] = "unavailable" if reasons else "supported"
    compatible = not reasons
    metric_contexts = dict(contexts)
    if request["mode"] == "matched" and compatible:
        for side, endpoint in (("before", "before_item_id"), ("after", "after_item_id")):
            members = tuple(sorted(pair[endpoint] for pair in request.get("pairs", [])))
            entry, context = build_profile(records, request[side + "_id"], request["scope_id"],
                                           population=population, member_ids=members, budget=budget)
            result["values"][side] = entry
            metric_contexts[side] = context
            _inherit(result, context)
    if compatible:
        old, new = result["values"]["before"], result["values"]["after"]
        deltas = {"delta_" + name: _delta(old[name], new[name]) for name in ("SCI", "D")}
    else:
        reason = "unknown_membership" if "unknown_membership" in reasons else (
            "incomplete_pairs" if request["mode"] == "matched" and not pair_ready else (
                "incompatible_frame" if "incompatible_frame" in reasons else (
                    "incompatible_policy" if "incompatible_policy" in reasons else "prerequisite_unavailable")))
        deltas = {"delta_SCI": unavailable(reason), "delta_D": unavailable(reason)}
    # Even incomplete coverage preserves positive presence and zero sightings.
    # Frame/policy incompatibility, however, cannot authorize a cross-frame loss.
    tail_changes = []
    membership_only = all(not row["reason_codes"] or row["field"] in {"before_membership", "after_membership"}
                          for row in compatibility["field_checks"])
    if compatible or (request["mode"] == "descriptive" and membership_only):
        tail_changes = _tails(
            request, result["values"]["before"], result["values"]["after"],
            metric_contexts["before"], metric_contexts["after"], mapping, budget)
    supplied = sorted({request["scope_id"], request["before_id"], request["after_id"],
                       before["frame"]["id"], after["frame"]["id"]})
    result["basis"] = [{"kind": "supplied_assertion", "record_ids": supplied},
                       {"kind": "local_calculation", "record_ids": sorted(set(result["dependency_ids"]))},
                       *result["basis"]]
    result["values"].update(deltas)
    result["values"]["compatibility"] = compatibility
    result["values"]["tail_changes"] = tail_changes
    result["reason_codes"] = sorted(reasons)
    result["execution"] = "completed"
    findings = []
    if reasons:
        findings.append(_finding(result, family="EC108", rule="comparison_prerequisites",
                                 reasons=sorted(reasons), subjects=[request["before_id"], request["after_id"]]))
    if result["values"]["tail_changes"]:
        tail_reasons = sorted({r for row in result["values"]["tail_changes"] for r in row["reason_codes"]})
        findings.append(_finding(result, family="EC104", rule="comparison_tail_inventory", reasons=tail_reasons,
                                 subjects=[request["before_id"], request["after_id"]]))
    return result, findings
