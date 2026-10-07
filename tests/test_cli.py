"""CLI contract checks using the installed-data path and public API."""

import contextlib
import io
import json
import tempfile
import unittest
from importlib import resources
from pathlib import Path
from unittest.mock import patch

import evaluation_closure_toolkit as ect
from evaluation_closure_toolkit import cli, fileio


class CommandLineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "dossier.json"
        self.data = resources.files("evaluation_closure_toolkit").joinpath("data", "incomplete-regression.json").read_bytes()
        self.path.write_bytes(self.data)

    def run_cli(self, *args):
        out, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(error):
            try:
                status = cli.main(list(args))
            except SystemExit as exc:
                status = exc.code
        return status, out.getvalue(), error.getvalue()

    def test_incomplete_evidence_completes_with_zero_exit_and_real_report(self):
        status, stdout, stderr = self.run_cli("analyze", str(self.path))
        self.assertEqual((status, stderr), (0, ""))
        report = json.loads(stdout)
        self.assertEqual(report["admission"], "valid")
        self.assertEqual(report["execution"], "completed")
        self.assertTrue(report["findings"])
        self.assertEqual(report["results"][0]["values"]["claim_conclusion"], "unestablished")

    def test_validate_does_not_execute_analysis(self):
        with patch.object(ect, "analyze_bytes", side_effect=AssertionError("analysis forbidden")):
            status, stdout, stderr = self.run_cli("validate", str(self.path))
        self.assertEqual((status, stderr), (0, ""))
        self.assertEqual(json.loads(stdout)["results"], [])

    def test_bad_input_is_exit_two_with_payload_free_report(self):
        self.path.write_bytes(b'{"PRIVATE-RAW-INPUT": invalid}')
        status, stdout, stderr = self.run_cli("validate", str(self.path))
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(stdout)["admission"], "invalid")
        self.assertNotIn("PRIVATE-RAW-INPUT", stdout + stderr)
        self.assertNotIn(str(self.path), stdout + stderr)

    def test_unsupported_selected_operation_emits_exit_three(self):
        dossier = json.loads(self.data)
        dossier["requests"] = [{"id": "cases-one", "operation": "cases", "scope_id": "scope-main"}]
        self.path.write_text(json.dumps(dossier), encoding="utf-8")
        status, stdout, stderr = self.run_cli("analyze", str(self.path))
        self.assertEqual((status, stderr), (3, ""))
        self.assertIn("unsupported_operation", stdout)
        self.assertIn("EC108", stdout)

    def test_unknown_duplicate_and_empty_selections_are_usage_errors(self):
        for arguments, expected in (
            (("--request", "MISSING-PRIVATE-ID"), "USAGE_UNKNOWN_REQUEST"),
            (("--request", "lint-main", "--request", "lint-main"), "USAGE_DUPLICATE_REQUEST"),
        ):
            with self.subTest(arguments=arguments):
                status, stdout, stderr = self.run_cli("analyze", str(self.path), *arguments)
                self.assertEqual((status, stdout), (2, ""))
                self.assertIn(expected, stderr)
                self.assertNotIn("MISSING-PRIVATE-ID", stderr)
        dossier = json.loads(self.data)
        dossier["requests"] = []
        self.path.write_text(json.dumps(dossier), encoding="utf-8")
        status, stdout, stderr = self.run_cli("analyze", str(self.path))
        self.assertEqual((status, stdout), (2, ""))
        self.assertIn("USAGE_NO_REQUESTS", stderr)

    def test_help_version_and_usage_do_not_open_input(self):
        with patch.object(cli, "read_input", side_effect=AssertionError("no file read")):
            for arguments in (("--help",), ("--version",), ("analyze", "--help")):
                with self.subTest(arguments=arguments):
                    status, stdout, stderr = self.run_cli(*arguments)
                    self.assertEqual((status, stderr), (0, ""))
                    self.assertTrue(stdout)
            for arguments in (("replay", "PRIVATE"), ("analyze", "SECRET-PATH", "--force"), ("demo", "../SECRET")):
                with self.subTest(arguments=arguments):
                    status, stdout, stderr = self.run_cli(*arguments)
                    self.assertEqual((status, stdout), (2, ""))
                    self.assertNotIn("SECRET", stderr)
                    self.assertNotIn("PRIVATE", stderr)

    def test_packaged_demos_use_same_api_and_need_no_filesystem_output(self):
        for name in cli.DEMOS:
            with self.subTest(name=name):
                status, stdout, stderr = self.run_cli("demo", name)
                self.assertEqual((status, stderr), (0, ""))
                report = json.loads(stdout)
                self.assertEqual(report["admission"], "valid")
                self.assertEqual(report["execution"], "completed")
        self.assertEqual(list(self.root.iterdir()), [self.path])

    def test_profile_and_compare_selection_has_exact_numeric_cli_results(self):
        data = resources.files("evaluation_closure_toolkit").joinpath("data", "growing-catalog.json").read_bytes()
        self.path.write_bytes(data)
        status, stdout, stderr = self.run_cli(
            "analyze", str(self.path), "--request", "profile-a", "--request", "compare-catalog"
        )
        self.assertEqual((status, stderr), (0, ""))
        report = json.loads(stdout)
        self.assertEqual(report["selected_request_ids"], ["compare-catalog", "profile-a"])
        selected = {r["request_id"]: r for r in report["results"] if r["selection"] == "selected"}
        profile = selected["profile-a"]["values"]["profiles"][0]
        self.assertEqual(profile["N"], {"state": "available", "value": 24})
        self.assertEqual(profile["SCI"], {
            "state": "available", "value": {"numerator": "25", "denominator": "72"}
        })
        comparison = selected["compare-catalog"]["values"]
        self.assertEqual(comparison["delta_SCI"], {
            "state": "available", "value": {"numerator": "1", "denominator": "24"}
        })

    def test_profile_and_compare_markdown_matches_complete_api_report(self):
        for name, expected_tokens in (
            ("growing-catalog", ("profile-a", "compare-catalog", "delta_SCI", "25/72")),
            ("matched-cohort", ("compare-matched", "matched", "pair_count", "1/12")),
            ("recut-comparison", ("compare-catalog", "incompatible_frame")),
        ):
            with self.subTest(name=name):
                data = resources.files("evaluation_closure_toolkit").joinpath("data", f"{name}.json").read_bytes()
                expected = ect.render_markdown(ect.analyze_bytes(data))
                status, stdout, stderr = self.run_cli("demo", name, "--format", "markdown")
                self.assertEqual((status, stdout, stderr), (0, expected, ""))
                for token in expected_tokens:
                    self.assertIn(token, stdout)

    def test_missing_installed_demo_fails_truthfully_without_traceback(self):
        with patch.object(cli.resources, "files", side_effect=FileNotFoundError("SECRET-INSTALL-PATH")):
            status, stdout, stderr = self.run_cli("demo", "incomplete-regression")
        self.assertEqual((status, stdout), (1, ""))
        self.assertIn("IO_DEMO_UNAVAILABLE", stderr)
        self.assertNotIn("SECRET", stderr)

    def test_output_exclusive_and_failure_overrides_success(self):
        output = self.root / "report.json"
        status, stdout, stderr = self.run_cli("analyze", str(self.path), "--output", str(output))
        self.assertEqual((status, stdout, stderr), (0, "", ""))
        original = output.read_bytes()
        status, stdout, stderr = self.run_cli("analyze", str(self.path), "--output", str(output))
        self.assertEqual((status, stdout), (1, ""))
        self.assertEqual(output.read_bytes(), original)
        self.assertNotIn(str(output), stderr)

    def test_in_memory_analysis_precedes_opening_output(self):
        output = self.root / "never-opened.json"
        with patch.object(ect, "analyze_bytes", side_effect=RuntimeError("PRIVATE-PAYLOAD")):
            status, stdout, stderr = self.run_cli("analyze", str(self.path), "--output", str(output))
        self.assertEqual((status, stdout), (1, ""))
        self.assertFalse(output.exists())
        self.assertIn("INTERNAL_ERROR", stderr)
        self.assertNotIn("PRIVATE-PAYLOAD", stderr)

    def test_oversized_file_has_admission_exit_without_a_partial_input_hash(self):
        with patch.object(fileio, "MAX_INPUT_BYTES", 3):
            status, stdout, stderr = self.run_cli("validate", str(self.path))
        self.assertEqual((status, stdout), (2, ""))
        self.assertIn("INPUT_BYTE_LIMIT", stderr)
        self.assertNotIn("sha256", stderr)

    def test_markdown_uses_api_renderer(self):
        expected = ect.render_markdown(ect.analyze_bytes(self.data))
        status, stdout, stderr = self.run_cli("analyze", str(self.path), "--format", "markdown")
        self.assertEqual((status, stdout, stderr), (0, expected, ""))


if __name__ == "__main__":
    unittest.main()
