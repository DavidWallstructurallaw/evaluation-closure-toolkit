"""Public selection, rendering, delivery-limit and offline-boundary tests.

Expected shapes and statuses are asserted independently of production schema and
policy helpers. The digest helper implements the published wire specification.
"""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
from importlib.resources import files
import io
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import unittest
from unittest.mock import patch
import urllib.request

from evaluation_closure_toolkit import analyze_bytes, render_markdown, validate_bytes
from evaluation_closure_toolkit.errors import ReportError, RequestError
from evaluation_closure_toolkit.budget import RequestBudget, RunBudget, WorkLimit
import evaluation_closure_toolkit.lint as lint_module


def fixture_bytes(name='supported-narrow-regression'):
    return files('evaluation_closure_toolkit').joinpath('data', name + '.json').read_bytes()


def wire(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8') + b'\n'


def rehash(report):
    payload = {key: value for key, value in report.items() if key != 'result_sha256'}
    report['result_sha256'] = hashlib.sha256(wire(payload)).hexdigest()
    return report


def detailed_json(markdown):
    """Decode the fenced detail without reusing the renderer's helpers."""
    lines = markdown.splitlines()
    starts = [i for i, line in enumerate(lines) if re.fullmatch(r'`{3,}json', line)]
    if len(starts) != 1:
        raise AssertionError('Exactly one complete JSON detail block is required.')
    start = starts[0]
    closing = lines[start][:-4]
    end = lines.index(closing, start + 1)
    return json.loads('\n'.join(lines[start + 1:end]))


class APIReportingTests(unittest.TestCase):
    def test_request_selection_is_exact_sorted_and_retains_unselected_state(self):
        dossier = json.loads(fixture_bytes())
        template = dossier['requests'][0]
        dossier['requests'] = [dict(template, id=name) for name in ('lint-z', 'lint-a', 'lint-mid')]
        report = analyze_bytes(wire(dossier), request_ids=('lint-z', 'lint-a'))
        self.assertEqual(report['selected_request_ids'], ['lint-a', 'lint-z'])
        results = {row['request_id']: row for row in report['results']}
        self.assertEqual(list(results), ['lint-a', 'lint-mid', 'lint-z'])
        for name in ('lint-a', 'lint-z'):
            self.assertEqual(results[name]['selection'], 'selected')
            self.assertEqual(results[name]['execution'], 'completed')
        self.assertEqual(results['lint-mid']['selection'], 'not_selected')
        self.assertEqual(results['lint-mid']['execution'], 'not_run')
        self.assertEqual(results['lint-mid']['assessment'], 'not_assessed')
        self.assertEqual(results['lint-mid']['values'], {})
        self.assertEqual(results['lint-mid']['reason_codes'], ['unselected'])
        self.assertEqual(report['execution'], 'completed')

    def test_more_than_sixteen_requests_require_explicit_bounded_selection(self):
        dossier = json.loads(fixture_bytes())
        template = dossier['requests'][0]
        dossier['requests'] = [dict(template, id=f'lint-{number:02d}') for number in range(17)]
        data = wire(dossier)
        self.assertEqual(validate_bytes(data)['admission'], 'valid')
        with self.assertRaisesRegex(RequestError, '^USAGE_SELECTION_LIMIT$'):
            analyze_bytes(data)
        ids = tuple(row['id'] for row in dossier['requests'])
        with self.assertRaisesRegex(RequestError, '^USAGE_SELECTION_LIMIT$'):
            analyze_bytes(data, request_ids=ids)
        report = analyze_bytes(data, request_ids=ids[:16])
        self.assertEqual(len(report['selected_request_ids']), 16)
        self.assertEqual(report['execution'], 'completed')
        self.assertEqual(sum(row['selection'] == 'selected' for row in report['results']), 16)

    def test_selection_errors_are_documented_request_errors(self):
        data = fixture_bytes()
        cases = [
            ((), 'USAGE_NO_REQUESTS'),
            (('lint-main', 'lint-main'), 'USAGE_DUPLICATE_REQUEST'),
            (('missing-request',), 'USAGE_UNKNOWN_REQUEST'),
            (['lint-main'], 'USAGE_INVALID_REQUEST'),
            ('lint-main', 'USAGE_INVALID_REQUEST'),
            ((1,), 'USAGE_INVALID_REQUEST'),
            ((None,), 'USAGE_INVALID_REQUEST'),
        ]
        for selection, code in cases:
            with self.subTest(selection=selection):
                with self.assertRaisesRegex(RequestError, '^' + code + '$'):
                    analyze_bytes(data, request_ids=selection)
        empty = json.loads(data)
        empty['requests'] = []
        self.assertEqual(validate_bytes(wire(empty))['admission'], 'valid')
        with self.assertRaisesRegex(RequestError, '^USAGE_NO_REQUESTS$'):
            analyze_bytes(wire(empty))

    def test_nonbytes_api_inputs_are_rejected_without_coercion(self):
        for value in ('{}', bytearray(b'{}'), memoryview(b'{}'), {}, None):
            for operation in (validate_bytes, analyze_bytes):
                with self.subTest(type=type(value).__name__, operation=operation.__name__):
                    with self.assertRaisesRegex(TypeError, '^INPUT_BYTES_REQUIRED$'):
                        operation(value)
        report = analyze_bytes(b'{', request_ids=('missing-request',))
        self.assertEqual(report['admission'], 'invalid')
        self.assertEqual(report['execution'], 'not_run')
        self.assertEqual(report['results'], [])

    def test_digest_mismatch_and_non_report_inputs_are_rejected(self):
        for value in ({}, [], 'report', None):
            with self.subTest(value=value):
                with self.assertRaises(ReportError):
                    render_markdown(value)
        report = analyze_bytes(fixture_bytes())
        report['results'][0]['values']['claim_conclusion'] = 'unestablished'
        with self.assertRaises(ReportError):
            render_markdown(report)

    def test_recomputed_digest_cannot_admit_malformed_lint_payload(self):
        # A self-consistent hash is identity, not a report-schema validator.
        base = analyze_bytes(fixture_bytes())
        changes = [
            ('invalid conclusion', lambda values: values.update(claim_conclusion='universally_proven')),
            ('invalid currentness', lambda values: values.update(currentness=True)),
            ('invalid documentary completeness', lambda values: values.update(documentary_completeness='verified')),
            ('missing validation envelope', lambda values: values.update(validation={})),
            ('invalid nested assessment', lambda values: values['validation'].update(assessment='truth')),
            ('invalid nested support IDs', lambda values: values['validation'].update(support_ids='receipt')),
            ('invalid disclosure qualification', lambda values: values['disclosures'][0].update(qualification='truth')),
            ('invalid disclosure reasons', lambda values: values['disclosures'][0].update(reasons='missing_field')),
            ('missing disclosure presence', lambda values: values['disclosures'][0].pop('presence')),
            ('unknown raw body field', lambda values: values.update(evidence_content='PRIVATE_UNEXPECTED_BODY_97')),
        ]
        for label, change in changes:
            with self.subTest(change=label):
                report = deepcopy(base)
                change(report['results'][0]['values'])
                rehash(report)
                with self.assertRaises(ReportError):
                    render_markdown(report)

    def test_recomputed_digest_cannot_admit_inconsistent_envelope(self):
        base = analyze_bytes(fixture_bytes())
        changes = [
            ('invalid assessment time', lambda report: report.update(analysis_time='2026-02-30T00:00:00Z')),
            ('missing selected result', lambda report: report.update(results=[])),
            ('contradictory selection', lambda report: report['results'][0].update(selection='not_selected')),
            ('duplicate result identity', lambda report: report['results'].append(deepcopy(report['results'][0]))),
            ('unexecuted affirmative conclusion', lambda report: report['results'][0].update(execution='not_run')),
        ]
        for label, change in changes:
            with self.subTest(change=label):
                report = deepcopy(base)
                change(report)
                rehash(report)
                with self.assertRaises(ReportError):
                    render_markdown(report)

    def test_recomputed_digest_cannot_admit_malformed_findings(self):
        base = analyze_bytes(fixture_bytes('incomplete-regression'))
        self.assertTrue(base['findings'])
        for key, malformed in (('needed_information', ['missing information']),
                               ('basis', 'a supplied assertion'), ('subject_ids', [True])):
            with self.subTest(field=key):
                report = deepcopy(base)
                report['findings'][0][key] = malformed
                rehash(report)
                with self.assertRaises(ReportError):
                    render_markdown(report)

    def test_report_limit_discards_undeliverable_conclusions_and_their_basis(self):
        data = fixture_bytes()
        self.assertEqual(analyze_bytes(data)['results'][0]['values']['claim_conclusion'],
                         'supported_under_scope')
        with patch('evaluation_closure_toolkit.api.MAX_REPORT_BYTES', 4096):
            report = analyze_bytes(data)
        self.assertEqual(report['admission'], 'valid')
        self.assertEqual(report['execution'], 'partial')
        self.assertEqual(report['resource_summary']['affected_request_ids'], ['lint-main'])
        self.assertEqual(report['resource_summary']['reason_codes'], ['resource_limit'])
        row = report['results'][0]
        self.assertEqual(row['execution'], 'partial')
        self.assertEqual(row['assessment'], 'not_assessed')
        self.assertEqual(row['values'], {})
        self.assertEqual(row['support_ids'], [])
        self.assertEqual(row['basis'], [])
        self.assertIn('resource_limit', row['reason_codes'])
        self.assertEqual(report['findings'][0]['family'], 'EC108')
        self.assertNotIn('supported_under_scope', wire(report).decode())
        self.assertLessEqual(len(wire(report)), 4096)
        self.assertEqual(detailed_json(render_markdown(report)), report)

    def test_finding_limit_also_produces_reason_bearing_partial_report(self):
        with patch('evaluation_closure_toolkit.api.MAX_FINDINGS', 0):
            report = analyze_bytes(fixture_bytes('incomplete-regression'))
        self.assertEqual(report['execution'], 'partial')
        self.assertGreater(report['resource_summary']['generated_finding_count'], 0)
        self.assertEqual(report['results'][0]['values'], {})
        self.assertEqual(report['results'][0]['assessment'], 'not_assessed')
        self.assertIn('resource_limit', report['findings'][0]['reason_codes'])

    def test_run_graph_limit_interrupts_first_request_and_skips_later_work(self):
        dossier = json.loads(fixture_bytes())
        template = dossier['requests'][0]
        dossier['requests'] = [dict(template, id='lint-first'), dict(template, id='lint-later')]
        run = RunBudget(limit=1)
        with patch('evaluation_closure_toolkit.api.RunBudget', return_value=run):
            report = analyze_bytes(wire(dossier))
        self.assertEqual(report['admission'], 'valid')
        self.assertEqual(report['execution'], 'partial')
        self.assertEqual(report['selected_request_ids'], ['lint-first', 'lint-later'])
        first, later = report['results']
        self.assertEqual(first['execution'], 'partial')
        self.assertEqual(later['execution'], 'not_run')
        for row in (first, later):
            self.assertEqual(row['assessment'], 'not_assessed')
            self.assertEqual(row['values'], {})
            self.assertEqual(row['reason_codes'], ['resource_limit'])
        self.assertEqual([(f['family'], f['request_id'], f['reason_codes']) for f in report['findings']],
                         [('EC108', 'lint-first', ['resource_limit']),
                          ('EC108', 'lint-later', ['resource_limit'])])
        self.assertLessEqual(run.used, 1)
        self.assertEqual(detailed_json(render_markdown(report)), report)

    def test_request_graph_limit_does_not_skip_later_request_with_run_capacity(self):
        dossier = json.loads(fixture_bytes())
        template = dossier['requests'][0]
        dossier['requests'] = [dict(template, id='lint-first'), dict(template, id='lint-later')]
        budgets = []

        def limited_request(*, run):
            budget = RequestBudget(run=run, limit=1)
            budgets.append(budget)
            return budget

        with patch('evaluation_closure_toolkit.api.RequestBudget', side_effect=limited_request):
            report = analyze_bytes(wire(dossier))
        self.assertEqual(report['admission'], 'valid')
        self.assertEqual(report['execution'], 'partial')
        self.assertEqual(len(budgets), 2)
        self.assertIs(budgets[0].run, budgets[1].run)
        self.assertEqual(budgets[0].run.used, sum(budget.used for budget in budgets))
        self.assertLess(budgets[0].run.used, budgets[0].run.limit)
        for budget in budgets:
            self.assertLessEqual(budget.used, 1)
        for row in report['results']:
            self.assertEqual(row['execution'], 'partial')
            self.assertEqual(row['assessment'], 'not_assessed')
            self.assertEqual(row['values'], {})
            self.assertEqual(row['reason_codes'], ['resource_limit'])
        self.assertEqual([(f['family'], f['request_id']) for f in report['findings']],
                         [('EC108', 'lint-first'), ('EC108', 'lint-later')])
        self.assertEqual(detailed_json(render_markdown(report)), report)

    def test_partial_lint_retains_completed_prefix_without_aggregate_conclusion(self):
        original = lint_module.evaluate_reviews
        calls = 0

        def interrupt_sixth(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 6:
                raise WorkLimit(run_exhausted=False)
            return original(*args, **kwargs)

        # Overall validation and two full disclosure rows complete. Interrupt
        # the next review through the actual public analysis boundary.
        with patch('evaluation_closure_toolkit.lint.evaluate_reviews', side_effect=interrupt_sixth):
            report = analyze_bytes(fixture_bytes('scope-mismatch'))
        self.assertEqual(calls, 6)
        self.assertEqual(report['admission'], 'valid')
        self.assertEqual(report['execution'], 'partial')
        result = report['results'][0]
        self.assertEqual(result['execution'], 'partial')
        self.assertEqual(result['assessment'], 'not_assessed')
        self.assertIn('resource_limit', result['reason_codes'])
        values = result['values']
        self.assertEqual(values['claim_conclusion'], 'not_assessed')
        self.assertEqual(values['documentary_completeness'], 'not_assessed')
        self.assertEqual([row['id'] for row in values['disclosures']], ['R01', 'R02'])
        for row in values['disclosures']:
            self.assertEqual(row['qualification'], 'supported_under_scope')
            self.assertEqual(row['review']['execution'], 'completed')
        self.assertEqual(values['validation']['assessment'], 'supported_under_scope')
        self.assertEqual(values['validation']['execution'], 'completed')
        self.assertIn('validation-review', values['validation']['support_ids'])
        self.assertEqual(values['scope_mismatches'], [
            {'required_feature': 'long_horizon', 'frame_id': 'frame-v1',
             'reason_codes': ['scope_mismatch']}])
        mismatch = next(f for f in report['findings'] if f['rule'] == 'required_feature_absent')
        self.assertEqual(mismatch['family'], 'EC101')
        self.assertEqual(mismatch['assessment'], 'contradicted_under_scope')
        self.assertTrue(mismatch['basis'])
        self.assertTrue(any(f['family'] == 'EC108' and 'resource_limit' in f['reason_codes']
                            for f in report['findings']))
        self.assertEqual(detailed_json(render_markdown(report)), report)

    def test_bytes_api_does_no_file_network_or_subprocess_work(self):
        data = fixture_bytes()
        forbidden = (
            'builtins.open', 'io.open', 'os.open', 'pathlib.Path.open',
            'pathlib.Path.read_bytes', 'pathlib.Path.read_text',
            'socket.socket', 'socket.create_connection', 'urllib.request.urlopen',
            'subprocess.Popen', 'subprocess.run', 'os.system',
        )
        with ExitStack() as stack:
            probes = [stack.enter_context(patch(name, side_effect=AssertionError(name))) for name in forbidden]
            admission = validate_bytes(data)
            analysis = analyze_bytes(data)
            markdown = render_markdown(analysis)
        self.assertEqual(admission['admission'], 'valid')
        self.assertEqual(analysis['results'][0]['values']['claim_conclusion'], 'supported_under_scope')
        self.assertTrue(markdown)
        for probe in probes:
            probe.assert_not_called()

    def test_unknown_build_identity_is_explicit_in_report_and_markdown(self):
        with patch('evaluation_closure_toolkit.api.BUILD_ID', 'unknown'):
            report = analyze_bytes(fixture_bytes())
        self.assertEqual(report['build_id'], 'unknown')
        self.assertTrue(any('unknown' in text.lower() and 'build' in text.lower()
                            for text in report['limitations']))
        detail = detailed_json(render_markdown(report))
        self.assertEqual(detail['build_id'], 'unknown')
        self.assertEqual(detail['limitations'], report['limitations'])

    def test_normalized_demo_bytes_match_cross_runtime_golden_digests(self):
        # Generated golden hashes verify reproducibility only. They are separate
        # from the independent scientific/semantic expectations in acceptance.
        golden = json.loads(Path(__file__).with_name('data').joinpath(
            'normalized_demo_sha256.json').read_text(encoding='utf-8'))
        excluded = {'tool_version', 'build_id', 'python_implementation',
                    'python_version', 'input_sha256', 'result_sha256'}
        self.assertEqual(set(golden['excluded_fields']), excluded)
        self.assertEqual(set(golden['sha256']), {'incomplete-regression',
                         'supported-narrow-regression', 'scope-mismatch', 'open-claim-lint'})
        for name, expected_digest in golden['sha256'].items():
            with self.subTest(fixture=name):
                report = analyze_bytes(fixture_bytes(name))
                normalized = {key: value for key, value in report.items() if key not in excluded}
                self.assertEqual(hashlib.sha256(wire(normalized)).hexdigest(), expected_digest)

    def test_markdown_complete_detail_is_exact_json_report(self):
        for name in ('incomplete-regression', 'supported-narrow-regression', 'scope-mismatch', 'open-claim-lint'):
            with self.subTest(fixture=name):
                report = analyze_bytes(fixture_bytes(name))
                self.assertEqual(detailed_json(render_markdown(report)), report)
        invalid = validate_bytes(b'{')
        self.assertEqual(detailed_json(render_markdown(invalid)), invalid)


if __name__ == '__main__':
    unittest.main()
