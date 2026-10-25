"""Readable ordering, scoped evidence visibility and saved-report rendering.

The golden fixes only the reading view before run-wide limitations. Literal
expectations below establish its meaning independently of rendered output.
Complete JSON parity remains checked separately, including runtime identity.
"""

from copy import deepcopy
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from evaluation_closure_toolkit import analyze_bytes, render_markdown, validate_bytes
from evaluation_closure_toolkit.cli import DEMOS
from evaluation_closure_toolkit.errors import ReportError


def fixture_bytes(name):
    return files("evaluation_closure_toolkit").joinpath("data", name + ".json").read_bytes()


def wire(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def reading_view(report):
    return render_markdown(report).partition("\n## Limitations\n")[0].rstrip("\n") + "\n"


def complete_report(markdown):
    lines = markdown.splitlines()
    starts = [i for i, line in enumerate(lines) if re.fullmatch(r"`{3,}json", line)]
    if len(starts) != 1:
        raise AssertionError("Expected exactly one authoritative report block")
    start = starts[0]
    end = lines.index(lines[start][:-4], start + 1)
    return json.loads("\n".join(lines[start + 1:end]))


class ReadableReportingTests(unittest.TestCase):
    def test_saved_canonical_reports_render_identically_for_every_demo(self):
        for name in DEMOS:
            with self.subTest(demo=name):
                report = analyze_bytes(fixture_bytes(name))
                before = wire(report)
                markdown = render_markdown(report)
                self.assertEqual(markdown, render_markdown(json.loads(before)))
                self.assertEqual(complete_report(markdown), report)
                self.assertEqual(wire(report), before)

    def test_scope_mismatch_reading_view_has_independent_meaning_and_golden_order(self):
        report = analyze_bytes(fixture_bytes("scope-mismatch"))
        result = report["results"][0]
        self.assertEqual(result["scope_id"], "scope-main")
        self.assertEqual(result["values"]["claim_conclusion"], "defeated_under_scope")
        self.assertEqual(result["values"]["documentary_completeness"], "complete")
        self.assertEqual(result["values"]["validation"]["assessment"], "supported_under_scope")
        self.assertEqual([r["id"] for r in result["values"]["disclosures"]],
                         ["R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09", "R10"])
        self.assertEqual(report["findings"][0]["rule"], "required_feature_absent")
        self.assertEqual(report["findings"][0]["subject_ids"], ["claim-v1", "frame-v1"])
        readable = reading_view(report)
        self.assertIn("Claim conclusion: defeated\\_under\\_scope.", readable)
        self.assertIn("| long\\_horizon | frame\\-v1 | scope\\_mismatch |", readable)
        self.assertIn("Needed information: Provide the required scoped records", readable)
        self.assertIn("| Support IDs | execution\\-receipt, human\\-receipt, validation\\-review |", readable)
        self.assertIn("| Contrary IDs | none recorded |", readable)
        golden = Path(__file__).with_name("data").joinpath("readable_report.md").read_text(encoding="utf-8")
        self.assertEqual(readable, golden)

    def test_assessment_lists_actual_prerequisites_and_all_gate_execution_states(self):
        report = analyze_bytes(fixture_bytes("supported-open-evaluation"))
        readable = reading_view(report)
        self.assertIn("### Actual prerequisites", readable)
        for role, operation in (("structural", "profile"), ("cases", "cases"), ("external", "external")):
            self.assertIn(f"| {role} | {operation} | scope | selected | completed | not\\_assessed |", readable)
        self.assertIn("| frame\\_target\\_fidelity | selected | applicable | completed | supported\\_under\\_scope |", readable)
        self.assertIn("| capacity\\_extent | selected | applicable | completed | supported\\_under\\_scope |", readable)
        self.assertIn("Scoped limitations:", readable)
        self.assertIn("| Dependency IDs |", readable)

    def test_unselected_request_is_visible_without_detailed_or_supported_values(self):
        dossier = json.loads(fixture_bytes("supported-narrow-regression"))
        dossier["requests"].append(dict(dossier["requests"][0], id="lint-unselected"))
        report = analyze_bytes(wire(dossier), request_ids=("lint-main",))
        readable = reading_view(report)
        section = readable.split("## lint lint\\-unselected\n", 1)[1].split("## Findings", 1)[0]
        self.assertIn("| not\\_selected | unresolved | not\\_run | not\\_assessed | unselected |", section)
        self.assertIn("No detailed operation values were delivered.", section)
        self.assertNotIn("supported\\_under\\_scope", section)

    def test_admission_and_delivery_limit_are_explained_without_clean_completion(self):
        invalid = validate_bytes(b"{")
        readable = reading_view(invalid)
        self.assertIn("## Admission diagnostics", readable)
        self.assertIn("INPUT\\_", readable)
        with patch("evaluation_closure_toolkit.api.MAX_REPORT_BYTES", 4096):
            partial = analyze_bytes(fixture_bytes("supported-open-evaluation"))
        readable = reading_view(partial)
        self.assertIn("## Delivery resource limit", readable)
        self.assertIn("Detailed basis and conclusions were omitted together.", readable)
        self.assertIn("resource\\_limit", readable)
        self.assertNotIn("supported\\_under\\_scope", readable)
        self.assertEqual(complete_report(render_markdown(partial)), partial)
        self.assertLessEqual(len(wire(partial)), 4096)
        self.assertLessEqual(len(render_markdown(partial).encode("utf-8")), 4096)

    def test_markdown_expansion_chooses_one_bounded_compact_report_for_both_formats(self):
        data = fixture_bytes("bounded-workflow")
        full = analyze_bytes(data)
        canonical_size = len(wire(full))
        markdown_size = len(render_markdown(full).encode("utf-8"))
        cap = (canonical_size + markdown_size) // 2
        self.assertLess(canonical_size, cap)
        self.assertGreater(markdown_size, cap)
        self.assertEqual(full["execution"], "completed")
        self.assertEqual(next(r for r in full["results"] if r["operation"] == "assess")["values"]["conclusion"],
                         "supported_under_scope")
        with patch("evaluation_closure_toolkit.api.MAX_REPORT_BYTES", cap):
            compact = analyze_bytes(data)
            self.assertEqual(compact, analyze_bytes(data))
        self.assertEqual(compact["execution"], "partial")
        self.assertEqual(compact["resource_summary"]["generated_result_count"], 7)
        self.assertTrue(all(r["values"] == {} and r["assessment"] == "not_assessed"
                            for r in compact["results"]))
        markdown = render_markdown(compact)
        self.assertLessEqual(len(wire(compact)), cap)
        self.assertLessEqual(len(markdown.encode("utf-8")), cap)
        self.assertEqual(complete_report(markdown), compact)
        unsigned = {key: value for key, value in compact.items() if key != "result_sha256"}
        self.assertEqual(compact["result_sha256"], hashlib.sha256(wire(unsigned)).hexdigest())

    def test_public_renderer_rejects_oversize_saved_view_without_changing_report(self):
        report = analyze_bytes(fixture_bytes("supported-narrow-regression"))
        before = wire(report)
        cap = (len(before) + len(render_markdown(report).encode("utf-8"))) // 2
        self.assertLess(len(before), cap)
        with patch("evaluation_closure_toolkit.reporting.MAX_REPORT_BYTES", cap):
            with self.assertRaisesRegex(ReportError, "^REPORT_INVALID$"):
                render_markdown(report)
        self.assertEqual(wire(report), before)

    def test_findings_and_scoped_limits_escape_hostile_text_without_losing_detail(self):
        report = deepcopy(analyze_bytes(fixture_bytes("scope-mismatch")))
        hostile = "<script>https://invalid.example/[click](x)|````\n\x1b[31m"
        report["findings"][0]["needed_information"] = hostile
        report["findings"][0]["limitations"] = [hostile]
        report["results"][0]["limitations"].append(hostile)
        report.pop("result_sha256")
        report["result_sha256"] = hashlib.sha256(wire(report)).hexdigest()
        markdown = render_markdown(report)
        readable = markdown.partition("\n## Complete report\n")[0]
        self.assertNotIn("<script>", readable)
        self.assertNotIn("https://", readable)
        self.assertNotIn("\x1b", markdown)
        self.assertIn(r"\<script\>https\://invalid\.example/\[click\]\(x\)\|\`\`\`\`\\n\\u001b\[31m", readable)
        self.assertIn("`````json\n", markdown)
        self.assertEqual(complete_report(markdown), report)
        self.assertEqual(markdown, render_markdown(json.loads(wire(report))))

    def test_case_accounting_uses_semantic_order_even_after_object_key_sorting(self):
        report = analyze_bytes(fixture_bytes("correction-cases"))
        readable = reading_view(json.loads(wire(report)))
        pairs = readable.split("| Unique case/target pair state | Count |", 1)[1]
        self.assertLess(pairs.index("| attempted |"), pairs.index("| acted |"))
        self.assertLess(pairs.index("| acted |"), pairs.index("| authorized |"))
        self.assertLess(pairs.index("| authorized |"), pairs.index("| effective |"))
        events = readable.split("| Raw event type | Count |", 1)[1]
        self.assertLess(events.index("| handling |"), events.index("| attempts |"))
        self.assertLess(events.index("| attempts |"), events.index("| actions |"))
        self.assertLess(events.index("| actions |"), events.index("| outcomes |"))


if __name__ == "__main__":
    unittest.main()
