"""Fixed, claim-scoped disclosure lint for the first implementation slice."""

import json

from .evidence import evaluate_reviews, fact_reason, known
from .budget import RequestBudget, WorkLimit


ROWS = tuple(f"R{number:02d}" for number in range(1, 11))
ANCHORS = {
    "R01": {"claim"}, "R02": {"frame"},
    "R03": {"item", "relation", "evidence"}, "R04": {"evidence", "review"},
    "R05": {"entity", "relation", "review"},
    "R06": {"snapshot", "frame", "evidence"},
    "R07": {"evidence", "review"}, "R08": {"evidence", "review"},
    "R09": {"correction_case"}, "R10": {"evidence", "review"},
}
VALIDATION_KINDS = {
    "execution": "execution_record", "proof": "proof_record",
    "observation": "observation_record", "human_consequence": "human_consequence_record",
}


def _finding(request: dict, subject_ids, rule: str, reasons, *, family="EC101",
             assessment="unresolved", support_ids=(), contrary_ids=(), basis=()) -> dict:
    return {
        "family": family, "request_id": request["id"], "scope_id": request["scope_id"],
        "subject_ids": sorted(set(subject_ids)), "rule": rule,
        "assessment": assessment, "reason_codes": sorted(set(reasons)),
        "basis": list(basis), "support_ids": sorted(set(support_ids)),
        "contrary_ids": sorted(set(contrary_ids)), "limitations": [],
        "needed_information": "Provide the required scoped records and qualified review, retaining contrary premises.",
    }


def _presence(claim: dict, row: str) -> tuple:
    fact = claim.get("disclosures", {}).get(row)
    if fact is None:
        return "missing", "unresolved", "unresolved", [], {"missing_field"}
    state = fact["state"]
    if state == "known":
        ids = fact["value"]
        return "present", "yes", "yes" if ids else "no", ids, set() if ids else {"missing_record"}
    if state == "not_applicable":
        return "present", "yes", "no", [], {"inapplicable"}
    presence = {"absent": "explicit_absence"}.get(state, state)
    return presence, "unresolved", "unresolved", [], {fact_reason({row: fact}, row)}


def _row_permitted_exclusion(row: str, claim: dict, requirements, anchors: list):
    if row in {"R07", "R08"}:
        if requirements is None:
            return None
        selected = ({"persistent_state", "long_horizon", "recovery", "override"}
                    if row == "R07" else {"field_use", "human_consequence"})
        return not (set(requirements) & selected)
    if claim["profile"] == "narrow_regression":
        return row in {"R06", "R09"} and not anchors
    return False


def _anchor_reasons(row: str, anchor_ids: list, claim: dict, frame: dict,
                    records: dict) -> set:
    reasons = set()
    if not anchor_ids:
        return {"missing_record"}
    if any(records[rid]["type"] not in ANCHORS[row] for rid in anchor_ids):
        reasons.add("prerequisite_unavailable")
    if row == "R01":
        if claim["id"] not in anchor_ids:
            reasons.add("scope_mismatch")
        for field in ("statement", "intended_use", "horizon"):
            if known(claim, field) is None:
                reasons.add(fact_reason(claim, field))
        if known(frame, "exclusions") is None:
            reasons.add(fact_reason(frame, "exclusions"))
    elif row == "R02":
        if frame.get("id") not in anchor_ids:
            reasons.add("scope_mismatch")
        for field in ("task", "context", "horizon", "resolution", "exclusions", "features"):
            if known(frame, field) is None:
                reasons.add(fact_reason(frame, field))
    elif row == "R10" and known(claim, "valid_until") is None:
        reasons.add(fact_reason(claim, "valid_until"))
    # Scope-bearing anchors cannot qualify a different inquiry. An entity/item
    # has no intrinsic scope; its use remains conditional on the scoped review.
    for rid in anchor_ids:
        record = records[rid]
        if "scope_id" in record and record["scope_id"] != claim["scope_id"]:
            reasons.add("scope_mismatch")
        if row in {"R02", "R06"}:
            if record["type"] == "frame" and record["id"] != frame.get("id"):
                reasons.add("scope_mismatch")
            if record["type"] == "snapshot" and record["frame_id"] != frame.get("id"):
                reasons.add("scope_mismatch")
    return reasons


def lint_claim(dossier: dict, request: dict, *, budget=None) -> tuple[dict, list[dict]]:
    """Lint an admitted claim without I/O, mutation, or five-gate analysis."""
    if budget is None:
        budget = RequestBudget()
    records = {record["id"]: record for record in dossier["records"]}
    claim = records[request["claim_id"]]
    scope_id = request["scope_id"]
    scope = records[scope_id]
    frame_id = known(claim, "frame_id")
    frame = records.get(frame_id, {})
    requirements = known(claim, "requirements")
    features = known(frame, "features")
    criterion = "claim_validation" if claim["profile"] == "narrow_regression" else "validation_type_fit"
    validation_kind = known(claim, "validation_kind")
    required_kinds = set()
    if validation_kind in VALIDATION_KINDS:
        required_kinds.add(VALIDATION_KINDS[validation_kind])
    if requirements is not None and "human_consequence" in requirements:
        required_kinds.add("human_consequence_record")
    validation = evaluate_reviews(records, claim["id"], criterion, scope_id,
                                  required_kinds=required_kinds, budget=budget)
    validation_reasons = set(validation["reason_codes"])
    if validation_kind is None:
        validation_reasons.add(fact_reason(claim, "validation_kind"))
    unsupported_kind = claim["profile"] == "narrow_regression" and validation_kind not in {None, "execution"}
    if unsupported_kind:
        validation_reasons.add("unsupported_validation_kind")
    if validation_kind is None or unsupported_kind:
        # Evidence of some other kind does not discharge this finite profile.
        validation["assessment"] = "unresolved"
    validation["reason_codes"] = sorted(validation_reasons)
    findings = []
    dependencies = {claim["id"], scope_id}
    dependencies.update(validation["dependency_ids"])
    support_ids = set(validation["support_ids"])
    contrary_ids = set(validation["contrary_ids"])
    claim_field_gaps = set()
    for field in ("statement", "intended_use", "horizon", "frame_id", "requirements", "validation_kind"):
        if known(claim, field) is None:
            claim_field_gaps.add(fact_reason(claim, field))
    if frame_id is not None:
        dependencies.add(frame_id)
    if claim_field_gaps:
        findings.append(_finding(request, [claim["id"]], "claim_required_fields", claim_field_gaps,
                                 basis=[{"kind": "supplied_assertion", "record_ids": [claim["id"]]}]))
    mismatches = []
    if requirements is not None and features is not None:
        for feature in sorted(set(requirements) - set(features)):
            mismatches.append({"required_feature": feature, "frame_id": frame_id,
                               "reason_codes": ["scope_mismatch"]})
        if mismatches:
            findings.append(_finding(request, [claim["id"], frame_id], "required_feature_absent",
                                     ["scope_mismatch"], assessment="contradicted_under_scope",
                                     basis=[{"kind": "local_deduction", "record_ids": [claim["id"], frame_id]}]))
    elif frame_id is not None:
        claim_field_gaps.add("prerequisite_unavailable")
        findings.append(_finding(request, [claim["id"], frame_id], "feature_scope_unavailable",
                                 ["prerequisite_unavailable"]))
    # Currentness is the supplied logical date only, never the host clock.
    expiry = known(claim, "valid_until")
    currentness = "unestablished"
    currentness_reasons = set()
    if expiry is None:
        currentness_reasons.add(fact_reason(claim, "valid_until"))
    elif expiry <= dossier["analysis_time"]:
        currentness = "expired_under_declared_date"
        currentness_reasons.add("expired")
    else:
        currentness = "current_under_declared_date"
    if currentness_reasons:
        findings.append(_finding(request, [claim["id"]], "claim_currentness", currentness_reasons,
                                 family="EC107", basis=[{"kind": "local_deduction", "record_ids": [claim["id"]]}]))
    if validation["assessment"] != "supported_under_scope":
        findings.append(_finding(request, [claim["id"]], "claim_validation", validation_reasons,
                                 family="EC107", assessment=validation["assessment"],
                                 support_ids=validation["support_ids"], contrary_ids=validation["contrary_ids"],
                                 basis=validation["basis"]))
    disclosures = []
    # Bound accumulated nested review output before all ten rows are retained.
    # The API also enforces the final serialized-report bound across requests.
    output_size = len(json.dumps(validation, ensure_ascii=True, separators=(",", ":")))
    documentary_complete = True
    all_rows_supported = True
    decisive = validation["assessment"] == "contradicted_under_scope" or bool(mismatches)
    all_reasons = set(claim_field_gaps) | currentness_reasons | validation_reasons
    if mismatches:
        all_reasons.add("scope_mismatch")
    for row_id in ROWS:
        presence, well_formed, linked, anchor_ids, reasons = _presence(claim, row_id)
        dependencies.update(anchor_ids)
        permitted = _row_permitted_exclusion(row_id, claim, requirements, anchor_ids)
        applicability = "unresolved" if permitted is None else "applicable"
        applicability_review = evaluate_reviews(records, claim["id"], "applicability", scope_id,
                                               applicability_row=row_id, budget=budget)
        row_review = evaluate_reviews(records, claim["id"], criterion, scope_id,
                                      required_kinds=required_kinds, disclosure_id=row_id, budget=budget)
        anchor_contrary = {cid for rid in anchor_ids for cid in records[rid].get("contrary_ids", [])}
        unresolved_anchor_contrary = anchor_contrary - set(row_review["values"]["resolved_ids"])
        contrary_ids.update(anchor_contrary)
        dependencies.update(anchor_contrary)
        review = row_review
        exclusion_supported = permitted is True and applicability_review["assessment"] == "supported_under_scope"
        if exclusion_supported:
            applicability = "not_applicable"
            presence = "present"
            qualification = "not_assessed"
            reasons = {"inapplicable"}
            review = applicability_review
            # The exclusion is a linked supplied declaration in its own right.
            well_formed, linked = "yes", "yes"
        else:
            anchor_reasons = _anchor_reasons(row_id, anchor_ids, claim, frame, records)
            reasons.update(anchor_reasons)
            if row_id in {"R01", "R02", "R10"} and anchor_ids and anchor_reasons & {
                "missing_field", "unknown_value", "withheld", "disputed", "explicit_absence", "inapplicable"
            }:
                well_formed = "unresolved"
            if anchor_ids and anchor_reasons:
                # Linked IDs remain links even if fields are scientifically
                # incomplete; incorrectly typed anchors cannot discharge them.
                if any(records[rid]["type"] not in ANCHORS[row_id] for rid in anchor_ids):
                    linked = "no"
            qualification = row_review["assessment"]
            if unresolved_anchor_contrary:
                reasons.add("disputed")
            if (anchor_reasons or unresolved_anchor_contrary or permitted is None or validation_kind is None or unsupported_kind) and qualification == "supported_under_scope":
                qualification = "unresolved"
            if validation_kind is None or unsupported_kind:
                qualification = "unresolved"
            reasons.update(row_review["reason_codes"])
            if permitted is None:
                reasons.add("prerequisite_unavailable")
            if permitted is True and not anchor_ids:
                reasons.update(applicability_review["reason_codes"])
            if presence == "present" and claim.get("disclosures", {}).get(row_id, {}).get("state") == "not_applicable":
                reasons.add("inapplicable")
            if not (presence == "present" and well_formed == "yes" and linked == "yes"):
                documentary_complete = False
            if qualification != "supported_under_scope":
                all_rows_supported = False
            if qualification == "contradicted_under_scope":
                decisive = True
        dependencies.update(review["dependency_ids"])
        support_ids.update(review["support_ids"])
        contrary_ids.update(review["contrary_ids"])
        # Applicability declarations are retained even when exclusion is not
        # allowed, so a claimed waiver can never silently erase an obligation.
        dependencies.update(applicability_review["dependency_ids"])
        contrary_ids.update(applicability_review["contrary_ids"])
        result_row = {
            "id": row_id, "presence": presence, "well_formed": well_formed,
            "linked": linked, "qualification": qualification,
            "applicability": applicability, "reasons": sorted(reasons),
            "anchor_ids": sorted(anchor_ids), "review": review,
            "applicability_review": applicability_review,
        }
        output_size += len(json.dumps(result_row, ensure_ascii=True, separators=(",", ":")))
        if output_size > 20 * 1024 * 1024:
            raise WorkLimit(run_exhausted=False)
        disclosures.append(result_row)
        if qualification not in {"supported_under_scope", "not_assessed"}:
            all_reasons.update(reasons)
            findings.append(_finding(request, [claim["id"], *anchor_ids], f"disclosure_{row_id}", reasons,
                                     assessment=qualification, support_ids=review["support_ids"],
                                     contrary_ids=review["contrary_ids"], basis=review["basis"]))
    # A known scope window is necessary for a time-bounded capability claim.
    window_gap = known(scope, "window") is None
    if window_gap:
        all_reasons.add(fact_reason(scope, "window"))
        findings.append(_finding(request, [scope_id, claim["id"]], "claim_scope_window",
                                 [fact_reason(scope, "window")]))
    if decisive:
        conclusion, assessment = "defeated_under_scope", "contradicted_under_scope"
    elif (claim["profile"] == "narrow_regression" and all_rows_supported
          and not claim_field_gaps and not window_gap
          and validation["assessment"] == "supported_under_scope"
          and currentness == "current_under_declared_date"):
        conclusion, assessment = "supported_under_scope", "supported_under_scope"
    else:
        conclusion, assessment = "unestablished", "unresolved"
    limitations = [
        "Conclusions are conditional on the supplied finite scope, evidence and attributed reviews.",
        "Evidence content, execution, assessor authority and protected underlying material were not independently authenticated.",
        "Currentness uses the caller-declared analysis time and validity date.",
    ]
    if claim["profile"] == "open_evaluation":
        limitations.append("Open-claim lint does not execute or support the five-condition assessment.")
    result = {
        "request_id": request["id"], "operation": "lint", "scope_id": scope_id,
        "selection": "selected", "applicability": "applicable", "execution": "completed",
        "assessment": assessment, "reason_codes": sorted(all_reasons),
        "values": {"disclosures": disclosures,
                   "documentary_completeness": "complete" if documentary_complete else "incomplete",
                   "currentness": currentness, "scope_mismatches": mismatches,
                   "validation": validation, "claim_conclusion": conclusion,
                   "open_evaluation": "not_applicable" if claim["profile"] == "narrow_regression" else "not_assessed"},
        "basis": [{"kind": "supplied_assertion", "record_ids": sorted({claim["id"], scope_id})},
                  {"kind": "local_deduction", "record_ids": sorted(dependencies)}],
        "support_ids": sorted(support_ids), "contrary_ids": sorted(contrary_ids),
        "dependency_ids": sorted(dependencies), "limitations": limitations,
    }
    findings.sort(key=lambda item: (item["request_id"], item["family"], item["rule"],
                                   item["subject_ids"], item["reason_codes"]))
    return result, findings
