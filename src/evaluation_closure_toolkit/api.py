"""Byte-only public boundaries. No paths, clocks, network or subprocesses."""

from __future__ import annotations

import hashlib
import platform

from . import __version__
from .admission import admit
from .budget import RequestBudget, RunBudget, WorkLimit
from .errors import AdmissionError, InternalError, RequestError
from .lint import lint_claim
from .reporting import canonical_json

BUILD_ID = "unknown"
MAX_REPORT_BYTES = 20 * 1024 * 1024
MAX_FINDINGS = 10_000
_LIMITATIONS = [
    "Development build identity is unknown; exact same-build provenance is not established.",
    "Analysis time is supplied by the dossier; it is not a captured execution time or historical evidence cutoff.",
    "Conclusions are conditional on supplied records, declared scope and ect-core/0.1; evidence authenticity and textual truth are not independently verified.",
    "P1-2 executes claim lint, structural profiles and compatible comparisons. Open-evaluation five-condition assessment is unavailable.",
]


def _base(data: bytes) -> dict:
    return {
        "schema": "ect-report/0.1", "method": "ect-method/0.1",
        "serialization": "ect-json/0.1", "tool_version": __version__,
        "build_id": BUILD_ID,
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "input_sha256": hashlib.sha256(data).hexdigest(),
        "selected_request_ids": [], "admission": "invalid",
        "execution": "not_run", "results": [], "findings": [],
        "limitations": list(_LIMITATIONS),
    }


def _admission(data: bytes) -> tuple[dict | None, dict]:
    if type(data) is not bytes:
        # Hash only captured bytes. Other Python objects are not wire inputs.
        raise TypeError("INPUT_BYTES_REQUIRED")
    report = _base(data)
    try:
        dossier = admit(data)
    except AdmissionError as exc:
        report["diagnostics"] = [{"code": exc.code, "pointer": exc.pointer}]
        report["limitations"].append("Dossier identity, policy and analysis time are unavailable because admission failed.")
        return None, report
    report.update({
        "dossier_schema": dossier["schema"], "dossier_id": dossier["id"],
        "policy": dossier["policy"], "analysis_time": dossier["analysis_time"],
        "admission": "valid", "execution": "completed",
    })
    return dossier, report


def _placeholder(request: dict, *, selected: bool, reason: str) -> dict:
    return {
        "request_id": request["id"], "operation": request["operation"],
        "scope_id": request["scope_id"],
        "selection": "selected" if selected else "not_selected",
        "applicability": "unresolved", "execution": "not_run",
        "assessment": "not_assessed", "reason_codes": [reason], "values": {},
        "basis": [], "support_ids": [], "contrary_ids": [],
        "dependency_ids": [], "limitations": [],
    }


def _finding(result: dict, reason: str) -> dict:
    return {
        "family": "EC108", "request_id": result["request_id"],
        "scope_id": result["scope_id"], "subject_ids": [],
        "rule": reason, "assessment": "not_assessed", "reason_codes": [reason],
        "basis": [], "support_ids": [], "contrary_ids": [], "limitations": [],
        "needed_information": "This request requires an implementation of the selected operation."
        if reason == "unsupported_operation" else "Detailed results exceed the deterministic delivery limit; use a smaller dossier or selection.",
    }


def _finish(report: dict, *, resource_limited: bool = False) -> dict:
    report["findings"].sort(key=lambda f: (
        f["request_id"], f["family"], f["rule"], f["subject_ids"], f["reason_codes"]))
    if resource_limited or len(report["findings"]) > MAX_FINDINGS or len(canonical_json(report)) + 100 > MAX_REPORT_BYTES:
        # Delivery must never retain a complete conclusion after its basis is dropped.
        old_results = report["results"]
        report["execution"] = "partial"
        report["resource_summary"] = {
            "affected_request_ids": sorted(r["request_id"] for r in old_results if r["selection"] == "selected"),
            "generated_finding_count": len(report["findings"]),
            "generated_result_count": len(old_results),
            "reason_codes": ["resource_limit"],
        }
        report["results"] = [
            _placeholder({"id": r["request_id"], "operation": r["operation"], "scope_id": r["scope_id"]},
                         selected=r["selection"] == "selected",
                         reason="resource_limit" if r["selection"] == "selected" else "unselected")
            for r in old_results
        ]
        for result in report["results"]:
            if result["selection"] == "selected":
                result["execution"] = "partial"
        report["findings"] = [_finding(r, "resource_limit") for r in report["results"] if r["selection"] == "selected"]
        report["limitations"].append("Detailed results could not be delivered within the report or finding limit. All affected conclusions are unassessed.")
    report["result_sha256"] = hashlib.sha256(canonical_json(report)).hexdigest()
    return report


def validate_bytes(data: bytes) -> dict:
    """Return admission metadata, including a sanitized invalid-input envelope.

    A non-bytes Python argument raises TypeError. No dossier request executes.
    """
    try:
        _, report = _admission(data)
        return _finish(report)
    except TypeError:
        if type(data) is not bytes:
            raise TypeError("INPUT_BYTES_REQUIRED") from None
        raise InternalError("INTERNAL_ERROR") from None
    except Exception:
        raise InternalError("INTERNAL_ERROR") from None


def _select(dossier: dict, request_ids: tuple[str, ...] | None) -> list[str]:
    available = {r["id"] for r in dossier["requests"]}
    if request_ids is None:
        selected = sorted(available)
    else:
        if type(request_ids) is not tuple or any(type(r) is not str for r in request_ids):
            raise RequestError("USAGE_INVALID_REQUEST")
        if len(request_ids) != len(set(request_ids)):
            raise RequestError("USAGE_DUPLICATE_REQUEST")
        if set(request_ids) - available:
            raise RequestError("USAGE_UNKNOWN_REQUEST")
        selected = sorted(request_ids)
    if not selected:
        raise RequestError("USAGE_NO_REQUESTS")
    if len(selected) > 16:
        raise RequestError("USAGE_SELECTION_LIMIT")
    return selected


def analyze_bytes(data: bytes, *, request_ids: tuple[str, ...] | None = None) -> dict:
    """Analyze exact captured bytes. Selection errors raise RequestError.

    Valid requests for deferred operations return not_run/unsupported_operation.
    Missing semantic evidence is a completed analysis, never an admission error.
    """
    try:
        dossier, report = _admission(data)
        if dossier is None:
            return _finish(report)
        selected = _select(dossier, request_ids)
        report["selected_request_ids"] = selected
        run_budget = RunBudget()
        run_exhausted = False
        delivery_limited = False
        delivery_bytes = len(canonical_json(report)) + 100
        for request in sorted(dossier["requests"], key=lambda r: r["id"]):
            if request["id"] not in selected:
                result = _placeholder(request, selected=False, reason="unselected")
                findings = []
            elif delivery_limited or run_exhausted or run_budget.used >= run_budget.limit:
                result = _placeholder(request, selected=True, reason="resource_limit")
                result["limitations"].append("Later work was not scheduled after a run work or report-delivery limit was reached.")
                findings = [_finding(result, "resource_limit")]
            elif request["operation"] in {"lint", "profile", "compare"}:
                budget = RequestBudget(run=run_budget)
                try:
                    if request["operation"] == "lint":
                        result, findings = lint_claim(dossier, request, budget=budget)
                    elif request["operation"] == "profile":
                        from .structural import profile_request
                        result, findings = profile_request(dossier, request, budget=budget)
                    else:
                        from .comparison import compare_request
                        result, findings = compare_request(dossier, request, budget=budget)
                except WorkLimit as exc:
                    run_exhausted = exc.run_exhausted
                    result = budget.partial_result or _placeholder(request, selected=True, reason="resource_limit")
                    result["execution"] = "partial"
                    progress = budget.profile_progress
                    if progress and (progress["member_reasons"] or progress["validity_members"]):
                        # Preserve completed member witnesses without treating
                        # an interrupted population scan as a full distribution.
                        result["values"]["partial_profiles"] = [{
                            key: progress[key] for key in (
                                "snapshot_id", "frame_id", "population", "member_reasons", "validity_members")
                        } | {"reason_codes": ["resource_limit"]}]
                        for key in ("dependency_ids", "support_ids", "contrary_ids"):
                            result[key] = sorted(set(result[key]) | set(progress[key]))
                        result["basis"].append({"kind": "supplied_assertion",
                                                "record_ids": sorted(progress["dependency_ids"])})
                    result["limitations"].append(
                        f"Selected work stopped at a deterministic resource limit after {budget.used} request work units and {run_budget.used} run work units. Only completed intermediate results are retained."
                    )
                    findings = [*budget.partial_findings, _finding(result, "resource_limit")]
            else:
                result = _placeholder(request, selected=True, reason="unsupported_operation")
                findings = [_finding(result, "unsupported_operation")]
            report["results"].append(result)
            report["findings"].extend(findings)
            if not delivery_limited:
                delivery_bytes += len(canonical_json(result)) + len(canonical_json(findings))
                delivery_limited = delivery_bytes > MAX_REPORT_BYTES or len(report["findings"]) > MAX_FINDINGS
            if result["selection"] == "selected" and result["execution"] != "completed":
                report["execution"] = "partial"
        return _finish(report, resource_limited=delivery_limited)
    except RequestError:
        raise
    except TypeError:
        if type(data) is not bytes:
            raise TypeError("INPUT_BYTES_REQUIRED") from None
        raise InternalError("INTERNAL_ERROR") from None
    except Exception:
        raise InternalError("INTERNAL_ERROR") from None
