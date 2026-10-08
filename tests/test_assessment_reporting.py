"""Finite-budget retention, report invariants and inert JSON/Markdown parity."""

from copy import deepcopy
import hashlib
import json
import re
import socket
import subprocess
import unittest
from unittest.mock import patch

from evaluation_closure_toolkit import analyze_bytes, render_markdown
from evaluation_closure_toolkit.assessment import Assessment
from evaluation_closure_toolkit.budget import RequestBudget, RunBudget, WorkLimit
from evaluation_closure_toolkit.errors import ReportError
from evaluation_closure_toolkit import structural
from assessment_helpers import supported, cases_demo, revision_demo, review
from provenance_helpers import wire, record, known, gap, fixture


def resign(report):
    report.pop("result_sha256", None)
    report["result_sha256"] = hashlib.sha256(wire(report)).hexdigest()
    return report


class AssessmentReportingTests(unittest.TestCase):
    def test_exact_report_and_markdown_parity_for_all_new_demos(self):
        for name in ("supported-open-evaluation", "correction-cases", "revision-accountability"):
            data = wire(fixture(name))
            report = analyze_bytes(data)
            self.assertEqual(report, analyze_bytes(data))
            md = render_markdown(report)
            self.assertEqual(json.loads(re.search(r"```json\n(.*)\n```", md, re.S).group(1)), report)
            self.assertNotIn("openness_score", md)
            self.assertNotIn("80%", md)

    def test_private_text_and_locators_stay_inert_and_unexported(self):
        marker = "PRIVATE_TEXT_<script>$(touch /tmp/no);file:///secret"
        for build in (supported, cases_demo, revision_demo):
            d = build()
            for r in d["records"]:
                for key in ("content", "locator", "rationale", "method", "issue", "changed_distinction", "context", "uncertainty"):
                    if key in r and r["type"] != "correction_case": r[key] = known(marker)
            data = wire(d); analyze_bytes(data); render_markdown(analyze_bytes(data))
            with patch("builtins.open", side_effect=AssertionError("file read")), \
                 patch.object(socket, "socket", side_effect=AssertionError("network")), \
                 patch.object(subprocess, "Popen", side_effect=AssertionError("process")):
                report = analyze_bytes(data)
                self.assertEqual(report["admission"], "valid")
                self.assertNotIn("PRIVATE_TEXT", json.dumps(report))
                self.assertNotIn("PRIVATE_TEXT", render_markdown(report))

    def test_missing_case_facts_have_no_nulls_or_internal_error(self):
        d = supported(); case = record(d, "case")
        for field in ("actor_id", "target_id", "occurred_at"): case["attempts"][0][field] = gap()
        case["actions"][0]["target_id"] = gap()
        report = analyze_bytes(wire(d))
        self.assertEqual(report["execution"], "completed")
        self.assertNotIn(":null", wire(report).decode())
        render_markdown(report)

    def test_partial_budget_preserves_parent_and_actual_prerequisites(self):
        for build, limits in ((supported, (1, 100, 150, 300, 400, 700)), (cases_demo, (1, 85, 100, 150))):
            for limit in limits:
                with self.subTest(build=build.__name__, limit=limit):
                    with patch("evaluation_closure_toolkit.api.RequestBudget", side_effect=lambda **kw: RequestBudget(limit=limit, **kw)):
                        report = analyze_bytes(wire(build()))
                    self.assertEqual(report["execution"], "partial")
                    result = report["results"][0]
                    self.assertEqual(result["operation"], "assess" if build == supported else "cases")
                    self.assertIn("resource_limit", result["reason_codes"])
                    self.assertNotEqual(result["assessment"], "supported_under_scope")
                    render_markdown(report)

    def test_nested_profile_keeps_completed_member_when_next_assignment_hits_limit(self):
        original = structural._assignment
        def interrupted(item_id, *args, **kwargs):
            if item_id == "item-b":
                raise WorkLimit(run_exhausted=False)
            return original(item_id, *args, **kwargs)
        with patch.object(structural, "_assignment", side_effect=interrupted):
            report = analyze_bytes(wire(supported()))
        values = report["results"][0]["values"]
        self.assertNotIn("partial_profiles", values)
        partial = values["prerequisites"][0]["result"]
        self.assertEqual(partial["operation"], "profile")
        self.assertEqual(partial["values"]["partial_profiles"][0]["member_reasons"][0]["item_id"], "item-a")
        render_markdown(report)

    def test_completed_decisive_defeat_survives_later_work_limit(self):
        d = supported(); d["records"].append(review("defeat", "frame_target_fidelity", ["receipt-frame_target_fidelity"],
                                                    verdict=known("contradicts"), decisive=known(True), counterexample_ids=["snapshot"]))
        def stop(self, criterion):
            raise WorkLimit(run_exhausted=False)
        with patch.object(Assessment, "external", stop):
            report = analyze_bytes(wire(d))
        result = report["results"][0]
        self.assertEqual(result["execution"], "partial")
        self.assertEqual(result["values"]["conclusion"], "defeated_under_scope")
        self.assertEqual(result["values"]["conditions"][0]["assessment"], "contradicted_under_scope")
        render_markdown(report)

    def test_run_budget_is_shared_across_nested_and_later_requests(self):
        d = supported(); d["requests"].append({"id": "later", "operation": "cases", "scope_id": "scope"})
        with patch("evaluation_closure_toolkit.api.RunBudget", side_effect=lambda: RunBudget(limit=300)):
            report = analyze_bytes(wire(d))
        self.assertEqual(report["results"][0]["execution"], "partial")
        self.assertEqual(report["results"][1]["execution"], "not_run")
        self.assertEqual(report["results"][1]["reason_codes"], ["resource_limit"])
        render_markdown(report)

    def test_undeliverable_basis_and_conclusion_are_dropped_together(self):
        with patch("evaluation_closure_toolkit.api.MAX_REPORT_BYTES", 4096):
            report = analyze_bytes(wire(supported()))
        self.assertEqual(report["results"][0]["values"], {})
        self.assertEqual(report["results"][0]["assessment"], "not_assessed")
        render_markdown(report)

    def test_renderer_rejects_forged_gates_even_with_recomputed_digest(self):
        base = analyze_bytes(wire(supported()))
        mutations = [
            lambda v: v.update(conclusion="certified"),
            lambda v: v.update(conditions=v["conditions"][:-1]),
            lambda v: v["conditions"][0]["values"]["criteria"].pop(),
            lambda v: v["conditions"][0].update(assessment="unresolved"),
            lambda v: v["conditions"][0]["values"]["criteria"][0].update(assessment="unresolved"),
            lambda v: v.update(prerequisites=[*v["prerequisites"], v["prerequisites"][0]]),
            lambda v: v.update(currentness="expired_under_declared_date"),
            lambda v: v.update(openness_score=100),
        ]
        for mutation in mutations:
            report = deepcopy(base); mutation(report["results"][0]["values"])
            with self.assertRaises(ReportError): render_markdown(resign(report))

    def test_renderer_rejects_forged_capacity_counts_or_recut(self):
        for build, mutation in (
            (cases_demo, lambda v: v["pair_counts"]["effective"].update(value=2)),
            (cases_demo, lambda v: v["event_counts"]["actions"].update(value=2)),
            (cases_demo, lambda v: v["corrections"][0]["capacity"].update(assessment="supported_under_scope")),
            (cases_demo, lambda v: v["corrections"][0]["outcomes"][0].update(action_id="missing")),
            (revision_demo, lambda v: v["revisions"][1]["fidelity"].update(assessment="supported_under_scope")),
        ):
            report = analyze_bytes(wire(build())); mutation(report["results"][0]["values"])
            with self.assertRaises(ReportError): render_markdown(resign(report))

    def test_record_permutation_does_not_change_analytical_result(self):
        d = supported(); first = analyze_bytes(wire(d))
        d["records"].reverse(); second = analyze_bytes(wire(d))
        self.assertEqual(first["results"], second["results"])
        self.assertEqual(first["findings"], second["findings"])


if __name__ == "__main__":
    unittest.main()
