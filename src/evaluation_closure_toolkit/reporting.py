"""Deterministic serialization and an inert, lossless Markdown view."""

from __future__ import annotations

import hashlib
import datetime as dt
import json
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
