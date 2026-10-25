"""Report grammar, byte parity, inert inputs and interrupted-delivery checks."""

from copy import deepcopy
import hashlib
import json
import re
import unittest
from unittest.mock import patch

from evaluation_closure_toolkit import analyze_bytes, render_markdown
from evaluation_closure_toolkit.budget import RequestBudget, RunBudget
from evaluation_closure_toolkit.errors import ReportError
from provenance_helpers import fixture, wire, known, record, result, member


def resign(report):
    report.pop("result_sha256", None)
    report["result_sha256"] = hashlib.sha256(wire(report)).hexdigest()
    return report


class ProvenanceReportingTests(unittest.TestCase):
    def test_complete_markdown_detail_is_identical_report(self):
        for name in ("shared-lineage", "recursive-reuse", "external-contact"):
            report = analyze_bytes(wire(fixture(name)))
            markdown = render_markdown(report)
            block = re.search(r"```json\n(.*)\n```", markdown, re.S)
            self.assertEqual(json.loads(block.group(1)), report)
            self.assertIn("Full paths, premise IDs", markdown)

    def test_readable_stage_counts_and_paths_have_no_second_rounding_policy(self):
        report = analyze_bytes(wire(fixture("external-contact")))
        markdown = render_markdown(report)
        self.assertIn("| retained | 1 | 1 | 0 | 1 | 3 |", markdown)
        lineage = render_markdown(analyze_bytes(wire(fixture("shared-lineage"))))
        self.assertIn(r"| x, y | origin | edge\-x\-origin | edge\-y\-origin |", lineage)

    def test_same_bytes_and_selected_requests_have_exact_determinism(self):
        for name in ("shared-lineage", "recursive-reuse", "external-contact"):
            data = wire(fixture(name))
            a, b = analyze_bytes(data), analyze_bytes(data)
            self.assertEqual(wire(a), wire(b))
            self.assertEqual(render_markdown(a), render_markdown(b))

    def test_no_evidence_method_role_locator_or_representation_text_leaks(self):
        sentinel = "DO_NOT_EXPORT_<script>file:///private;$(command)"
        for name in ("shared-lineage", "recursive-reuse", "external-contact"):
            d = fixture(name)
            for row in d["records"]:
                for key in ("content", "locator", "representation", "method", "rationale", "role"):
                    if key in row:
                        row[key] = known(sentinel)
            data = wire(d)
            report = analyze_bytes(data)
            self.assertEqual(report["admission"], "valid")
            self.assertNotIn(sentinel, json.dumps(report))
            self.assertNotIn("DO_NOT_EXPORT", render_markdown(report))

    def test_runtime_does_not_open_evidence_locators_or_spawn_processes(self):
        import socket
        import subprocess
        for name in ("shared-lineage", "external-contact"):
            data = wire(fixture(name))
            analyze_bytes(data)  # Resolve lazy module imports outside the guard.
            with patch("builtins.open", side_effect=AssertionError("unexpected file access")), \
                 patch.object(socket, "socket", side_effect=AssertionError("unexpected network")), \
                 patch.object(subprocess, "Popen", side_effect=AssertionError("unexpected child")):
                report = analyze_bytes(data)
                self.assertEqual(report["execution"], "completed")
                render_markdown(report)

    def test_missing_or_unknown_fields_are_rejected_by_renderer(self):
        for name, request in (("shared-lineage", "lineage-acquisition"), ("external-contact", "external-main")):
            report = analyze_bytes(wire(fixture(name)))
            result(report, request)["values"]["fabricated_score"] = 100
            with self.assertRaises(ReportError):
                render_markdown(resign(report))

    def test_disconnected_path_is_rejected(self):
        report = analyze_bytes(wire(fixture("shared-lineage")))
        result(report, "lineage-acquisition")["values"]["witnesses"][0]["left_path"] = ["edge-y-origin"]
        with self.assertRaises(ReportError):
            render_markdown(resign(report))

    def test_unsorted_duplicate_witness_and_false_terminal_rejected(self):
        base = analyze_bytes(wire(fixture("shared-lineage")))
        for mutation in ("duplicate", "terminal"):
            report = deepcopy(base)
            value = result(report, "lineage-acquisition")["values"]
            if mutation == "duplicate":
                value["witnesses"].append(deepcopy(value["witnesses"][0]))
            else:
                value["captured_terminals"] = [{"seed_id": "x", "node_id": "x", "path": []}]
            with self.assertRaises(ReportError):
                render_markdown(resign(report))

    def test_fake_cycle_is_rejected(self):
        report = analyze_bytes(wire(fixture("shared-lineage")))
        value = result(report, "lineage-acquisition")["values"]
        value["cycle_state"] = "present"
        value["cycle_witnesses"] = [{"node_id": "x", "path": ["edge-x-origin"]}]
        with self.assertRaises(ReportError):
            render_markdown(resign(report))

    def test_wrong_recursive_path_order_is_rejected(self):
        report = analyze_bytes(wire(fixture("recursive-reuse")))
        result(report, "lineage-recursive")["values"]["recursive_witnesses"][0]["path"].reverse()
        with self.assertRaises(ReportError):
            render_markdown(resign(report))

    def test_fake_current_contact_with_missing_receipt_is_rejected(self):
        report = analyze_bytes(wire(fixture("external-contact")))
        member(report, "q")["contact_state"] = "documented_current_contact"
        with self.assertRaises(ReportError):
            render_markdown(resign(report))

    def test_member_counts_cannot_be_replaced_by_raw_event_counts(self):
        report = analyze_bytes(wire(fixture("external-contact")))
        result(report, "external-main")["values"]["stage_counts"]["retained"]["yes"]["value"] = 2
        with self.assertRaises(ReportError):
            render_markdown(resign(report))

    def test_numeric_booleans_and_unavailable_zero_placeholder_rejected(self):
        for bad in ({"state": "available", "value": True}, {"state": "unavailable", "reason": "unknown_membership", "value": 0}):
            report = analyze_bytes(wire(fixture("external-contact")))
            result(report, "external-main")["values"]["known_member_count"] = bad
            with self.assertRaises(ReportError):
                render_markdown(resign(report))

    def test_wrong_dimension_applicability_is_rejected(self):
        report = analyze_bytes(wire(fixture("shared-lineage")))
        result(report, "lineage-acquisition")["values"]["independence_assessments"][0]["applies_to_view"] = False
        with self.assertRaises(ReportError):
            render_markdown(resign(report))

    def test_all_early_partial_points_remain_renderable(self):
        for name in ("shared-lineage", "recursive-reuse", "external-contact"):
            data = wire(fixture(name))
            for limit in range(0, 160, 3):
                with self.subTest(name=name, limit=limit):
                    with patch("evaluation_closure_toolkit.api.RequestBudget", side_effect=lambda **kw: RequestBudget(limit=limit, **kw)):
                        report = analyze_bytes(data)
                    render_markdown(report)
                    if report["execution"] == "partial":
                        self.assertTrue(any(f["family"] == "EC108" for f in report["findings"]))

    def test_delivery_limit_drops_conclusion_with_its_undeliverable_basis(self):
        with patch("evaluation_closure_toolkit.api.MAX_REPORT_BYTES", 2000):
            report = analyze_bytes(wire(fixture("external-contact")))
        row = result(report, "external-main")
        self.assertEqual(report["execution"], "partial")
        self.assertEqual(row["values"], {})
        self.assertEqual(row["assessment"], "not_assessed")
        render_markdown(report)

    def test_cases_and_assess_execute_after_the_p1_4_implementation(self):
        d = fixture("incomplete-regression")
        scope, claim = d["requests"][0]["scope_id"], d["requests"][0]["claim_id"]
        d["requests"] = [{"id": "future-cases", "operation": "cases", "scope_id": scope},
                         {"id": "future-assess", "operation": "assess", "scope_id": scope, "claim_id": claim}]
        report = analyze_bytes(wire(d))
        self.assertEqual(report["admission"], "valid")
        self.assertTrue(all(r["execution"] == "completed" and "unsupported_operation" not in r["reason_codes"] for r in report["results"]))
        render_markdown(report)


if __name__ == "__main__":
    unittest.main()
