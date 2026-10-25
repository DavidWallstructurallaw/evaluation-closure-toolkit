"""Deterministic serialization and an inert, lossless Markdown view."""

from __future__ import annotations

import hashlib
import datetime as dt
import json
import math
import re

from .errors import ReportError

_BASE = {
    "schema", "method", "serialization", "tool_version", "build_id",
    "python_implementation", "python_version", "input_sha256",
    "selected_request_ids", "admission", "execution", "results", "findings",
    "limitations", "result_sha256",
}
_DOSSIER = {"dossier_schema", "dossier_id", "policy", "analysis_time"}
_RESULT = {
    "request_id", "operation", "scope_id", "selection", "applicability",
    "execution", "assessment", "reason_codes", "values", "basis", "support_ids",
    "contrary_ids", "dependency_ids", "limitations",
}
_FINDING = {
    "family", "request_id", "scope_id", "subject_ids", "rule", "assessment",
    "reason_codes", "basis", "support_ids", "contrary_ids", "limitations", "needed_information",
}
_EXECUTION = {"completed", "partial", "not_run", "failed"}
_ASSESSMENT = {"supported_under_scope", "contradicted_under_scope", "unresolved", "not_assessed"}
_OPERATIONS = {"lint", "profile", "compare", "lineage", "external", "cases", "assess"}
_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,95}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_REASONS = set("missing_field missing_record unknown_value withheld disputed explicit_absence scope_mismatch expired access_gap body_unavailable provisional unclassified unresolved_assignment unknown_membership incomplete_pairs incompatible_frame incompatible_policy unsupported_validation_kind unsupported_operation resource_limit unselected inapplicable prerequisite_unavailable empty_population empty_admitted_population no_witness_in_captured_view absent_in_empty_population internal_error".split())
_CRITERION = _RESULT - {"request_id", "operation", "scope_id"}
_DECIMAL_INTEGER = re.compile(r"(?:0|-?[1-9][0-9]{0,31})\Z")
_POSITIVE_INTEGER = re.compile(r"[1-9][0-9]{0,31}\Z")
_PROFILE = {
    "snapshot_id", "frame_id", "population", "K", "N", "A", "U",
    "assignment_coverage", "class_counts", "observed_support", "SCI", "D",
    "member_reasons", "membership_complete", "population_complete",
    "reason_counts", "known_subset", "tails", "count_scope",
}
_VALID_PROFILE = {"V", "validity_coverage", "validity_counts", "validity_members"}
_VALIDITY_STATES = {"valid", "invalid", "unresolved", "missing", "disputed"}
_PRIMARY_REASONS = {
    "admitted", "disputed", "withheld", "body_unavailable", "missing_record",
    "provisional", "unclassified", "unresolved",
}
_COMPATIBILITY_FIELDS = {
    "frame", "task", "context", "horizon", "resolution", "exclusions",
    "frame_selection_policy", "frame_admission_policy", "snapshot_selection_policy",
    "validity_rubric", "before_membership", "after_membership", "pair_membership",
    "matching_basis", "class_map",
}
_TAIL_COMPARISON_STATES = {
    "present", "zero_admitted_sightings", "absent_in_complete_population",
    "absent_in_empty_population", "unavailable",
}


def _require(condition) -> None:
    if not condition:
        raise ReportError("REPORT_INVALID")


def _keys(value, keys) -> None:
    _require(type(value) is dict and set(value) == set(keys))


def _ids(value) -> None:
    _require(_strings(value) and all(_identity(v) for v in value))
    _require(value == sorted(set(value)))


def _reasons(value) -> None:
    _require(_strings(value) and set(value) <= _REASONS and value == sorted(set(value)))


def _basis(value) -> None:
    _require(type(value) is list)
    for entry in value:
        _keys(entry, {"kind", "record_ids"})
        _require(entry["kind"] in {"supplied_assertion", "supplied_review", "local_deduction", "local_calculation", "captured_identity"})
        _ids(entry["record_ids"])


def _number(value, *, integer=False, unit_interval=False, delta=False) -> None:
    """Check an exact numeric wrapper without coercing booleans or decimals."""
    _require(type(value) is dict)
    if value.get("state") in {"undefined", "unavailable"}:
        _keys(value, {"state", "reason"})
        _require(type(value["reason"]) is str and value["reason"] in _REASONS)
        return
    _keys(value, {"state", "value"})
    _require(value["state"] == "available")
    number = value["value"]
    if integer:
        _require(type(number) is int and 0 <= number <= 9_007_199_254_740_991)
        return
    _keys(number, {"numerator", "denominator"})
    numerator, denominator = number["numerator"], number["denominator"]
    _require(type(numerator) is str and _DECIMAL_INTEGER.fullmatch(numerator) is not None)
    _require(type(denominator) is str and _POSITIVE_INTEGER.fullmatch(denominator) is not None)
    n, d = int(numerator), int(denominator)
    _require(math.gcd(n, d) == 1)
    if unit_interval:
        _require(0 <= n <= d)
    if delta:
        _require(-d <= n <= d)


def _common(value) -> None:
    _require(value["selection"] in {"selected", "not_selected"})
    _require(value["applicability"] in {"applicable", "not_applicable", "unresolved"})
    _require(value["execution"] in _EXECUTION and value["assessment"] in _ASSESSMENT)
    _reasons(value["reason_codes"])
    for key in ("support_ids", "contrary_ids", "dependency_ids"):
        _ids(value[key])
    _require(_strings(value["limitations"]))
    _basis(value["basis"])


def _criterion(value) -> None:
    _keys(value, _CRITERION)
    _common(value)
    details = value["values"]
    _keys(details, {"documentary_completeness", "reviews", "decisive_review_ids", "resolved_ids"})
    _require(details["documentary_completeness"] in {"complete", "incomplete"})
    _ids(details["decisive_review_ids"])
    _ids(details["resolved_ids"])
    _require(type(details["reviews"]) is list)
    for review in details["reviews"]:
        _keys(review, {"review_id", "scope_id", "selected", "documentary_completeness", "qualified", "resolved", "verdict", "reason_codes", "support_ids", "contrary_ids", "resolves"})
        _require(_identity(review["review_id"]) and _identity(review["scope_id"]))
        _require(all(type(review[key]) is bool for key in ("selected", "qualified", "resolved")))
        _require(review["documentary_completeness"] in {"complete", "incomplete"})
        _require(review["verdict"] in {"supports", "contradicts", "unresolved"})
        _reasons(review["reason_codes"])
        for key in ("support_ids", "contrary_ids", "resolves"):
            _ids(review[key])
    identifiers = [r["review_id"] for r in details["reviews"]]
    _require(identifiers == sorted(set(identifiers)))


def _lint_values(value, *, partial=False) -> None:
    _keys(value, {"disclosures", "documentary_completeness", "currentness", "scope_mismatches", "validation", "claim_conclusion", "open_evaluation"})
    _require(value["open_evaluation"] in {"not_applicable", "not_assessed"})
    _require(value["documentary_completeness"] in {"complete", "incomplete", "not_assessed"})
    _require(value["currentness"] in {"current_under_declared_date", "expired_under_declared_date", "unestablished"})
    _require(value["claim_conclusion"] in {"supported_under_scope", "defeated_under_scope", "unestablished", "not_assessed"})
    _require(type(value["disclosures"]) is list)
    count = len(value["disclosures"])
    _require(0 <= count <= 10 if partial else count == 10)
    _require([row["id"] for row in value["disclosures"]] == [f"R{i:02}" for i in range(1, count + 1)])
    if partial:
        _require(value["claim_conclusion"] == "not_assessed" and value["documentary_completeness"] == "not_assessed")
    for row in value["disclosures"]:
        _keys(row, {"id", "presence", "well_formed", "linked", "qualification", "applicability", "reasons", "anchor_ids", "review", "applicability_review"})
        _require(row["presence"] in {"missing", "present", "unknown", "withheld", "disputed", "explicit_absence"})
        _require(row["well_formed"] in {"yes", "no", "unresolved"} and row["linked"] in {"yes", "no", "unresolved"})
        _require(row["qualification"] in _ASSESSMENT)
        _require(row["applicability"] in {"applicable", "not_applicable", "unresolved"})
        _reasons(row["reasons"])
        _ids(row["anchor_ids"])
        _criterion(row["review"])
        _criterion(row["applicability_review"])
    _require(type(value["scope_mismatches"]) is list)
    for mismatch in value["scope_mismatches"]:
        _keys(mismatch, {"required_feature", "frame_id", "reason_codes"})
        _require(mismatch["required_feature"] in {"single_turn", "persistent_state", "long_horizon", "recovery", "override", "human_consequence", "field_use"})
        _require(_identity(mismatch["frame_id"]))
        _reasons(mismatch["reason_codes"])
    _criterion(value["validation"])


def _sorted_rows(rows, field: str) -> None:
    _require(type(rows) is list)
    keys = [row[field] for row in rows]
    _require(keys == sorted(set(keys)))


def _member_rows(rows) -> None:
    _require(type(rows) is list)
    for row in rows:
        required = {"item_id", "primary_reason", "reason_codes"}
        optional = {"assignment_id", "class_id", "resolution"}
        _require(type(row) is dict and required <= row.keys() <= required | optional)
        for field in ("item_id", "assignment_id", "class_id"):
            if field in row:
                _require(_identity(row[field]))
        _require(row["primary_reason"] in _PRIMARY_REASONS)
        _reasons(row["reason_codes"])
        if "resolution" in row:
            _criterion(row["resolution"])
    _sorted_rows(rows, "item_id")


def _validity_rows(rows) -> None:
    _require(type(rows) is list)
    for row in rows:
        required = {"item_id", "state", "reason_codes"}
        _require(type(row) is dict and required <= row.keys() <= required | {"validity_id"})
        _require(_identity(row["item_id"]) and row["state"] in _VALIDITY_STATES)
        if "validity_id" in row:
            _require(_identity(row["validity_id"]))
        _reasons(row["reason_codes"])
    _sorted_rows(rows, "item_id")


def _partial_profiles(values, *, partial: bool) -> None:
    if "partial_profiles" not in values:
        return
    _require(partial and type(values["partial_profiles"]) is list and len(values["partial_profiles"]) <= 1)
    for profile in values["partial_profiles"]:
        _keys(profile, {"snapshot_id", "frame_id", "population", "member_reasons", "validity_members", "reason_codes"})
        _require(_identity(profile["snapshot_id"]) and _identity(profile["frame_id"]))
        _require(profile["population"] in {"selected", "confirmed_valid"})
        _require(profile["reason_codes"] == ["resource_limit"])
        _member_rows(profile["member_reasons"])
        _validity_rows(profile["validity_members"])


def _profile(value) -> None:
    _require(type(value) is dict and value.get("population") in {"selected", "confirmed_valid"})
    valid = value["population"] == "confirmed_valid"
    _keys(value, _PROFILE | (_VALID_PROFILE if valid else set()))
    _require(_identity(value["snapshot_id"]) and _identity(value["frame_id"]))
    _require(value["count_scope"] in {"known_roster", "confirmed_valid_subset", "matched_cohort"})
    _require(type(value["membership_complete"]) is bool and type(value["population_complete"]) is bool)
    for field in ("K", "N", "A", "U", "observed_support"):
        _number(value[field], integer=True)
    for field in ("assignment_coverage", "SCI", "D"):
        _number(value[field], unit_interval=True)
    _require(type(value["class_counts"]) is list)
    for row in value["class_counts"]:
        _keys(row, {"class_id", "count"})
        _require(_identity(row["class_id"]))
        _number(row["count"], integer=True)
    _sorted_rows(value["class_counts"], "class_id")
    _member_rows(value["member_reasons"])
    _require(type(value["reason_counts"]) is list)
    for row in value["reason_counts"]:
        _keys(row, {"reason", "count"})
        _require(row["reason"] in _REASONS)
        _number(row["count"], integer=True)
    _sorted_rows(value["reason_counts"], "reason")
    subset = value["known_subset"]
    _keys(subset, {"A", "U", "assignment_coverage", "observed_support", "SCI", "D"})
    for field in ("A", "U", "observed_support"):
        _number(subset[field], integer=True)
    for field in ("assignment_coverage", "SCI", "D"):
        _number(subset[field], unit_interval=True)
    _require(type(value["tails"]) is list)
    for row in value["tails"]:
        _keys(row, {"class_id", "count", "state", "reason_codes", "evidence_ids"})
        _require(_identity(row["class_id"]))
        _require(row["state"] in {"present", "absent", "absent_in_empty_population", "unestablished"})
        _number(row["count"], integer=True)
        _reasons(row["reason_codes"])
        _ids(row["evidence_ids"])
        if row["state"] == "present":
            _require(row["count"]["state"] == "available" and row["count"]["value"] > 0)
        elif row["state"] in {"absent", "absent_in_empty_population"}:
            _require(row["count"] == {"state": "available", "value": 0})
            _require(value["N"]["state"] == "available" and value["N"] == value["A"])
            if row["state"] == "absent_in_empty_population":
                _require(value["N"]["value"] == 0)
    _sorted_rows(value["tails"], "class_id")
    if valid:
        _number(value["V"], integer=True)
        _number(value["validity_coverage"], unit_interval=True)
        _require(type(value["validity_counts"]) is list)
        for row in value["validity_counts"]:
            _keys(row, {"state", "count"})
            _require(row["state"] in _VALIDITY_STATES)
            _number(row["count"], integer=True)
        _sorted_rows(value["validity_counts"], "state")
        _require({row["state"] for row in value["validity_counts"]} == _VALIDITY_STATES)
        _validity_rows(value["validity_members"])


def _profile_list(profiles, *, partial=False) -> None:
    _require(type(profiles) is list and len(profiles) <= 2)
    if not partial:
        _require(bool(profiles))
    for profile in profiles:
        _profile(profile)
    populations = [profile["population"] for profile in profiles]
    _require(populations == ["selected", "confirmed_valid"][:len(profiles)])
    if len(profiles) == 2:
        _require(all(profiles[0][key] == profiles[1][key] for key in ("snapshot_id", "frame_id")))


def _profile_values(value, *, partial=False) -> None:
    _keys(value, {"profiles"} | ({"partial_profiles"} if "partial_profiles" in value else set()))
    _partial_profiles(value, partial=partial)
    _profile_list(value["profiles"], partial=partial)


def _compare_values(value, *, partial=False) -> None:
    _keys(value, {
        "before", "after", "mode", "compatibility", "pair_count", "pair_gaps",
        "delta_SCI", "delta_D", "tail_changes", "catalog_profiles", "new_observations",
    } | ({"partial_profiles"} if "partial_profiles" in value else set()))
    _partial_profiles(value, partial=partial)
    _require(value["mode"] in {"descriptive", "matched"})
    compatibility = value["compatibility"]
    required = {"state", "reason_codes", "field_checks"}
    optional = {"frame_equivalence", "matching_basis"}
    _require(type(compatibility) is dict and required <= compatibility.keys() <= required | optional)
    _require(compatibility["state"] in {"supported", "unavailable"})
    _reasons(compatibility["reason_codes"])
    if compatibility["state"] == "supported":
        _require(not compatibility["reason_codes"])
    _require(type(compatibility["field_checks"]) is list)
    for check in compatibility["field_checks"]:
        _keys(check, {"field", "state", "reason_codes"})
        _require(check["field"] in _COMPATIBILITY_FIELDS)
        _require(check["state"] in {"compatible", "unavailable"})
        _reasons(check["reason_codes"])
        if check["state"] == "compatible":
            _require(not check["reason_codes"])
        if compatibility["state"] == "supported":
            _require(check["state"] == "compatible")
    _sorted_rows(compatibility["field_checks"], "field")
    for field in optional:
        if field in compatibility:
            _criterion(compatibility[field])
    _keys(value["catalog_profiles"], {"before", "after"})
    for side in ("before", "after"):
        profile = value[side]
        if profile == {}:
            _require(compatibility["state"] == "unavailable")
            _require(value["mode"] == "matched" or partial)
        else:
            _profile(profile)
        _profile_list(value["catalog_profiles"][side], partial=partial)
    _number(value["pair_count"], integer=True)
    if value["mode"] == "descriptive":
        _require(value["pair_count"] == {"state": "unavailable", "reason": "inapplicable"})
    _require(type(value["pair_gaps"]) is list)
    for gap in value["pair_gaps"]:
        _keys(gap, {"before_item_id", "after_item_id", "reason_codes"})
        _require(_identity(gap["before_item_id"]) and _identity(gap["after_item_id"]))
        _reasons(gap["reason_codes"])
    pairs = [(gap["before_item_id"], gap["after_item_id"]) for gap in value["pair_gaps"]]
    _require(pairs == sorted(set(pairs)))
    for field in ("delta_SCI", "delta_D"):
        _number(value[field], delta=True)
        if compatibility["state"] == "unavailable":
            _require(value[field]["state"] == "unavailable")
    _number(value["new_observations"], integer=True)
    if value["new_observations"]["state"] == "available":
        _require(value["new_observations"]["value"] == 0)
    _require(type(value["tail_changes"]) is list)
    for tail in value["tail_changes"]:
        _keys(tail, {
            "before_class_id", "after_class_id", "population", "scope", "before_count",
            "after_count", "before_status", "after_status", "change", "reason_codes",
        })
        _require(_identity(tail["before_class_id"]) and _identity(tail["after_class_id"]))
        _require(tail["population"] in {"selected", "confirmed_valid"})
        _require(tail["scope"] in {"selected_catalog", "confirmed_valid_subset", "matched_cohort"})
        for field in ("before_count", "after_count"):
            _number(tail[field], integer=True)
        for field in ("before_status", "after_status"):
            _require(tail[field] in _TAIL_COMPARISON_STATES)
        _require(tail["change"] in {"retained", "loss", "no_loss_established", "unavailable"})
        _reasons(tail["reason_codes"])
        if tail["change"] == "loss":
            _require(compatibility["state"] == "supported")
            _require(tail["before_status"] == "present" and tail["after_status"] in {"absent_in_complete_population", "absent_in_empty_population"})
            _require(tail["before_count"]["state"] == "available" and tail["before_count"]["value"] > 0)
            _require(tail["after_count"] == {"state": "available", "value": 0})
            if tail["after_status"] == "absent_in_empty_population":
                _require(value["after"]["N"] == {"state": "available", "value": 0})
    tails = [(row["before_class_id"], row["after_class_id"]) for row in value["tail_changes"]]
    _require(tails == sorted(set(tails)))
    if partial:
        _require(compatibility["state"] == "unavailable" and "resource_limit" in compatibility["reason_codes"])
        _require(not value["tail_changes"])


def _json_types(value, depth=0) -> None:
    if depth > 40:
        raise ReportError("REPORT_INVALID")
    if type(value) is dict:
        for key, child in value.items():
            if type(key) is not str:
                raise ReportError("REPORT_INVALID")
            _json_types(child, depth + 1)
    elif type(value) is list:
        for child in value:
            _json_types(child, depth + 1)
    elif type(value) not in (str, bool, int):
        raise ReportError("REPORT_INVALID")
    elif type(value) is int and abs(value) > 9_007_199_254_740_991:
        raise ReportError("REPORT_INVALID")


def canonical_json(report: dict) -> bytes:
    """Serialize ect-json/0.1, including the single terminal LF."""
    try:
        _json_types(report)
        return (json.dumps(report, ensure_ascii=True, sort_keys=True,
                           separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    except ReportError:
        raise
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise ReportError("REPORT_INVALID") from None


def _strings(value) -> bool:
    return type(value) is list and all(type(v) is str for v in value)


def _identity(value) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _check_report(report: dict) -> None:
    if type(report) is not dict or not _BASE <= report.keys():
        raise ReportError("REPORT_INVALID")
    if report.keys() - (_BASE | _DOSSIER | {"diagnostics", "resource_summary"}):
        raise ReportError("REPORT_INVALID")
    if (report["schema"] != "ect-report/0.1" or report["serialization"] != "ect-json/0.1"
            or report["method"] != "ect-method/0.1"
            or report["admission"] not in {"valid", "invalid"}
            or report["execution"] not in _EXECUTION):
        raise ReportError("REPORT_INVALID")
    for key in ("input_sha256", "result_sha256"):
        if type(report[key]) is not str or not _HASH.fullmatch(report[key]):
            raise ReportError("REPORT_INVALID")
    for key in ("tool_version", "build_id", "python_implementation", "python_version"):
        if type(report[key]) is not str or not report[key]:
            raise ReportError("REPORT_INVALID")
    if (not _strings(report["selected_request_ids"])
            or not all(_identity(r) for r in report["selected_request_ids"])
            or report["selected_request_ids"] != sorted(set(report["selected_request_ids"]))
            or not _strings(report["limitations"])
            or type(report["results"]) is not list or type(report["findings"]) is not list):
        raise ReportError("REPORT_INVALID")
    if report["admission"] == "valid":
        if (not _DOSSIER <= report.keys() or report["dossier_schema"] != "ect-dossier/0.1"
                or report["policy"] != "ect-core/0.1" or not _identity(report["dossier_id"])
                or type(report["analysis_time"]) is not str):
            raise ReportError("REPORT_INVALID")
        _require(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", report["analysis_time"]) is not None)
        dt.datetime.strptime(report["analysis_time"], "%Y-%m-%dT%H:%M:%SZ")
        _require("diagnostics" not in report)
    elif (report["execution"] != "not_run" or report["results"] or report["findings"]
          or report["selected_request_ids"] or not report.get("diagnostics")):
        raise ReportError("REPORT_INVALID")
    if report["admission"] == "invalid":
        _require(not (_DOSSIER & report.keys()))
        _require(type(report["diagnostics"]) is list)
        for diagnostic in report["diagnostics"]:
            _keys(diagnostic, {"code", "pointer"})
            _require(type(diagnostic["code"]) is str and re.fullmatch(r"INPUT_[A-Z_]+", diagnostic["code"]) is not None)
            _require(type(diagnostic["pointer"]) is str and re.fullmatch(r"(?:/[A-Za-z0-9_]+)*", diagnostic["pointer"]) is not None)
    for result in report["results"]:
        if type(result) is not dict or set(result) != _RESULT:
            raise ReportError("REPORT_INVALID")
        if (not _identity(result["request_id"]) or not _identity(result["scope_id"])
                or result["operation"] not in _OPERATIONS
                or result["selection"] not in {"selected", "not_selected"}
                or result["applicability"] not in {"applicable", "not_applicable", "unresolved"}
                or result["execution"] not in _EXECUTION or result["assessment"] not in _ASSESSMENT
                or type(result["values"]) is not dict or type(result["basis"]) is not list):
            raise ReportError("REPORT_INVALID")
        for key in ("reason_codes", "support_ids", "contrary_ids", "dependency_ids", "limitations"):
            if not _strings(result[key]):
                raise ReportError("REPORT_INVALID")
        _common(result)
        _require((result["selection"] == "selected") == (result["request_id"] in report["selected_request_ids"]))
        if result["operation"] == "lint" and result["execution"] == "completed":
            _lint_values(result["values"])
        elif result["operation"] == "lint" and result["execution"] == "partial" and result["values"]:
            _require(result["assessment"] == "not_assessed" and "resource_limit" in result["reason_codes"])
            _lint_values(result["values"], partial=True)
        elif result["operation"] in {"profile", "compare"} and result["execution"] in {"completed", "partial"} and result["values"]:
            partial = result["execution"] == "partial"
            _require(result["assessment"] == "not_assessed")
            if partial:
                _require("resource_limit" in result["reason_codes"])
            checker = _profile_values if result["operation"] == "profile" else _compare_values
            checker(result["values"], partial=partial)
        else:
            _require(result["values"] == {} and result["execution"] in {"not_run", "partial"})
    request_ids = [r["request_id"] for r in report["results"]]
    _require(request_ids == sorted(set(request_ids)))
    _require(set(report["selected_request_ids"]) <= set(request_ids))
    for finding in report["findings"]:
        if type(finding) is not dict or set(finding) != _FINDING:
            raise ReportError("REPORT_INVALID")
        if (finding["family"] not in {f"EC{i}" for i in range(101, 109)}
                or not _identity(finding["request_id"]) or not _identity(finding["scope_id"])
                or finding["assessment"] not in _ASSESSMENT):
            raise ReportError("REPORT_INVALID")
        for key in ("subject_ids", "reason_codes", "support_ids", "contrary_ids", "limitations"):
            if not _strings(finding[key]):
                raise ReportError("REPORT_INVALID")
        _require(finding["request_id"] in report["selected_request_ids"])
        _require(type(finding["rule"]) is str and re.fullmatch(r"[A-Za-z0-9_]+", finding["rule"]) is not None)
        _require(type(finding["needed_information"]) is str and bool(finding["needed_information"]))
        _basis(finding["basis"])
        _reasons(finding["reason_codes"])
        for key in ("subject_ids", "support_ids", "contrary_ids"):
            _ids(finding[key])
    if "resource_summary" in report:
        summary = report["resource_summary"]
        _keys(summary, {"affected_request_ids", "generated_finding_count", "generated_result_count", "reason_codes"})
        _ids(summary["affected_request_ids"])
        _require(report["execution"] == "partial" and summary["reason_codes"] == ["resource_limit"])
        _require(all(type(summary[k]) is int and summary[k] >= 0 for k in ("generated_finding_count", "generated_result_count")))
    payload = {key: value for key, value in report.items() if key != "result_sha256"}
    if hashlib.sha256(canonical_json(payload)).hexdigest() != report["result_sha256"]:
        raise ReportError("REPORT_INVALID")


def _escape(value: str) -> str:
    # JSON quoting first removes terminal controls; punctuation escaping keeps
    # IDs and generated prose inert in headings, tables and ordinary text.
    value = json.dumps(value, ensure_ascii=True)[1:-1]
    return re.sub(r"([\\`*_{}\[\]()<>#+.!|:\-])", r"\\\1", value)


def _number_text(value: dict) -> str:
    if value["state"] != "available":
        return value["state"] + " (" + value["reason"] + ")"
    number = value["value"]
    if type(number) is int:
        return str(number)
    return number["numerator"] + "/" + number["denominator"]


def _table(lines: list[str], headers: list[str], rows: list[list[str]]) -> None:
    lines.append("| " + " | ".join(_escape(value) for value in headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(_escape(value) for value in row) + " |")
    lines.append("")


def _profile_markdown(lines: list[str], profile: dict, label: str) -> None:
    lines += ["### " + _escape(label), "",
              "Snapshot: " + _escape(profile["snapshot_id"]) + ". Frame: " + _escape(profile["frame_id"]) + ".", "",
              "Population: " + _escape(profile["population"]) + ". Count scope: " + _escape(profile["count_scope"]) + ". "
              "Membership complete: " + str(profile["membership_complete"]).lower() + ". "
              "Population complete: " + str(profile["population_complete"]).lower() + ".", ""]
    metrics = [
        ("K (captured original roster)", "K"), ("N (profile population)", "N"),
        ("A (admitted)", "A"), ("U (non-admitted)", "U"),
        ("Assignment coverage (A/N)", "assignment_coverage"),
        ("Observed support", "observed_support"), ("SCI", "SCI"), ("D", "D"),
    ]
    if profile["population"] == "confirmed_valid":
        metrics += [("V (confirmed-valid subset)", "V"),
                    ("Validity coverage (decided / selected N)", "validity_coverage")]
    _table(lines, ["Metric", "Exact value"], [[label, _number_text(profile[field])] for label, field in metrics])
    if not profile["membership_complete"]:
        lines += ["Known-subset arithmetic uses only the captured roster. Full-population values remain unavailable.", ""]
        subset = profile["known_subset"]
        _table(lines, ["Known-subset metric", "Exact value"],
               [[field, _number_text(subset[field])] for field in ("A", "U", "assignment_coverage", "observed_support", "SCI", "D")])
    if profile["class_counts"]:
        _table(lines, ["Class", "Admitted count"],
               [[row["class_id"], _number_text(row["count"])] for row in profile["class_counts"]])
    if profile["tails"]:
        _table(lines, ["Declared tail", "Admitted count", "Status", "Reasons"],
               [[row["class_id"], _number_text(row["count"]), row["state"], ", ".join(row["reason_codes"])]
                for row in profile["tails"]])


def _structural_markdown(lines: list[str], result: dict) -> None:
    values = result["values"]
    lines += ["## " + _escape(result["operation"] + " " + result["request_id"]), ""]
    if result["execution"] == "partial":
        lines += ["Execution is partial. Completed views are retained; unfinished views and comparisons remain unavailable.", ""]
    if values.get("partial_profiles"):
        lines += ["Completed member and validity decisions from unfinished views are retained in the complete report. These inventories do not establish full-population totals or absence.", ""]
    if result["operation"] == "profile":
        for profile in values["profiles"]:
            _profile_markdown(lines, profile, profile["snapshot_id"] + " / " + profile["population"])
        return
    compatibility = values["compatibility"]
    lines += ["Mode: " + _escape(values["mode"]) + ". Compatibility: " + _escape(compatibility["state"]) + ".", ""]
    _table(lines, ["Comparison metric", "Exact value"], [
        ["Pair count (fixed matched denominator)", _number_text(values["pair_count"])],
        ["Delta SCI (after - before)", _number_text(values["delta_SCI"])],
        ["Delta D (after - before)", _number_text(values["delta_D"])],
        ["New observations from reannotation", _number_text(values["new_observations"])],
    ])
    if compatibility["reason_codes"]:
        lines += ["Compatibility reasons: " + _escape(", ".join(compatibility["reason_codes"])) + ".", ""]
    for side in ("before", "after"):
        if values[side]:
            _profile_markdown(lines, values[side], side.capitalize() + " comparison population")
        else:
            lines += [side.capitalize() + " comparison population: unavailable.", ""]
        for profile in values["catalog_profiles"][side]:
            if profile != values[side]:
                _profile_markdown(lines, profile, side.capitalize() + " catalog / " + profile["population"])
    if values["pair_gaps"]:
        _table(lines, ["Before item", "After item", "Pair gap reasons"],
               [[row["before_item_id"], row["after_item_id"], ", ".join(row["reason_codes"])]
                for row in values["pair_gaps"]])
    if values["tail_changes"]:
        _table(lines, ["Before tail", "After tail", "Scope", "Before", "After", "Change"],
               [[row["before_class_id"], row["after_class_id"], row["scope"],
                 _number_text(row["before_count"]), _number_text(row["after_count"]), row["change"]]
                for row in values["tail_changes"]])


def render_markdown(report: dict) -> str:
    """Render current reports with complete detail, without a second analysis.

    The report digest and current envelope are checked. The digest establishes
    consistency only, never authenticity. All substantive detail is retained in
    an inert JSON code block after the concise reading view.
    """
    try:
        if len(canonical_json(report)) > 20 * 1024 * 1024:
            raise ReportError("REPORT_INVALID")
        _check_report(report)
        lines = ["# Evaluation Closure Toolkit report", "",
                 f"Admission: **{_escape(report['admission'])}**. Execution: **{_escape(report['execution'])}**.", ""]
        if report["admission"] == "valid":
            lines += [f"Dossier: {_escape(report['dossier_id'])}. Declared analysis time: {_escape(report['analysis_time'])}.", ""]
        if report["results"]:
            lines += ["## Requests", "", "| Request | Scope | Operation | Selection | Execution | Conclusion |",
                      "| --- | --- | --- | --- | --- | --- |"]
            for result in report["results"]:
                columns = [result[k] for k in ("request_id", "scope_id", "operation", "selection", "execution")]
                columns.append(result["values"].get("claim_conclusion", result["assessment"]))
                lines.append("| " + " | ".join(_escape(v) for v in columns) + " |")
            lines.append("")
            for result in report["results"]:
                if result["operation"] in {"profile", "compare"} and result["values"]:
                    _structural_markdown(lines, result)
        lines += ["## Limitations", ""]
        lines.extend("- " + _escape(value) for value in report["limitations"])
        lines += ["", "## Complete report", "",
                  "All disclosure rows, review qualifications, contrary premises, findings, scope and identity fields follow. This is the same report as the JSON output.", ""]
        detail = json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False)
        longest = max((len(match.group()) for match in re.finditer(r"`+", detail)), default=0)
        fence = "`" * max(3, longest + 1)
        lines += [fence + "json", detail, fence, ""]
        return "\n".join(lines)
    except ReportError:
        raise
    except Exception:
        raise ReportError("REPORT_INVALID") from None
