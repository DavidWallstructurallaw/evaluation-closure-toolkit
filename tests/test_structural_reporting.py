"""Independent report-grammar and exact readable structural rendering checks."""
from copy import deepcopy
import hashlib
from importlib.resources import files
import json
import re
import unittest
from unittest.mock import patch

from evaluation_closure_toolkit import analyze_bytes, render_markdown
from evaluation_closure_toolkit.budget import WorkLimit
from evaluation_closure_toolkit.errors import ReportError
import evaluation_closure_toolkit.structural as structural_module


def count(value):
    return {'state': 'available', 'value': value}


def ratio(numerator, denominator=1):
    return {'state': 'available', 'value': {'numerator': str(numerator), 'denominator': str(denominator)}}


def unavailable(reason='prerequisite_unavailable'):
    return {'state': 'unavailable', 'reason': reason}


def profile(snapshot='snapshot-before', *, concentrated=False):
    sci, diversity = (ratio(1), ratio(0)) if concentrated else (ratio(5, 9), ratio(4, 9))
    counts = (6, 0) if concentrated else (4, 2)
    return {
        'snapshot_id': snapshot, 'frame_id': 'frame-one', 'population': 'selected',
        'K': count(6), 'N': count(6), 'A': count(6), 'U': count(0),
        'assignment_coverage': ratio(1), 'class_counts': [
            {'class_id': 'class-a', 'count': count(counts[0])},
            {'class_id': 'class-b', 'count': count(counts[1])}],
        'observed_support': count(1 if concentrated else 2), 'SCI': sci, 'D': diversity,
        'member_reasons': [
            {'item_id': f'item-{i}', 'assignment_id': f'assignment-{i}',
             'class_id': 'class-a' if concentrated or i < 4 else 'class-b',
             'primary_reason': 'admitted', 'reason_codes': []} for i in range(6)],
        'membership_complete': True, 'population_complete': True, 'reason_counts': [],
        'known_subset': {'A': count(6), 'U': count(0), 'assignment_coverage': ratio(1),
                         'observed_support': count(1 if concentrated else 2), 'SCI': sci, 'D': diversity},
        'tails': [{'class_id': 'class-b', 'count': count(counts[1]),
                   'state': 'absent' if concentrated else 'present',
                   'reason_codes': [], 'evidence_ids': []}],
        'count_scope': 'known_roster',
    }


def confirmed_profile():
    value = profile()
    value.update(population='confirmed_valid', count_scope='confirmed_valid_subset',
                 V=count(6), validity_coverage=ratio(1),
                 validity_counts=[{'state': state, 'count': count(6 if state == 'valid' else 0)}
                                  for state in ('disputed', 'invalid', 'missing', 'unresolved', 'valid')],
                 validity_members=[{'item_id': f'item-{i}', 'validity_id': f'validity-{i}',
                                    'state': 'valid', 'reason_codes': []} for i in range(6)])
    return value


def compare_values():
    before, after = profile(), profile('snapshot-after', concentrated=True)
    return {
        'before': before, 'after': after, 'mode': 'descriptive',
        'compatibility': {'state': 'supported', 'reason_codes': [], 'field_checks': [
            {'field': 'frame', 'state': 'compatible', 'reason_codes': []}]},
        'pair_count': unavailable('inapplicable'), 'pair_gaps': [],
        'delta_SCI': ratio(4, 9), 'delta_D': ratio(-4, 9),
        'catalog_profiles': {'before': [deepcopy(before)], 'after': [deepcopy(after)]},
        'new_observations': unavailable(),
        'tail_changes': [{'before_class_id': 'class-b', 'after_class_id': 'class-b',
                          'population': 'selected', 'scope': 'selected_catalog',
                          'before_count': count(2), 'after_count': count(0),
                          'before_status': 'present', 'after_status': 'absent_in_complete_population',
                          'change': 'loss', 'reason_codes': []}],
    }


def rehash(report):
    payload = {key: value for key, value in report.items() if key != 'result_sha256'}
    wire = (json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    report['result_sha256'] = hashlib.sha256(wire).hexdigest()
    return report


def report_for(operation='profile', values=None, *, partial=False):
    if values is None:
        values = {'profiles': [profile(), confirmed_profile()]} if operation == 'profile' else compare_values()
    return rehash({
        'schema': 'ect-report/0.1', 'dossier_schema': 'ect-dossier/0.1', 'dossier_id': 'dossier-test',
        'policy': 'ect-core/0.1', 'method': 'ect-method/0.1', 'serialization': 'ect-json/0.1',
        'tool_version': '0.1.0.dev2', 'build_id': 'unknown', 'python_implementation': 'CPython',
        'python_version': '3.12.0', 'analysis_time': '2026-10-07T00:00:00Z', 'input_sha256': '0' * 64,
        'selected_request_ids': ['request-one'], 'admission': 'valid',
        'execution': 'partial' if partial else 'completed',
        'results': [{'request_id': 'request-one', 'operation': operation, 'scope_id': 'scope-main',
                     'selection': 'selected', 'applicability': 'applicable',
                     'execution': 'partial' if partial else 'completed', 'assessment': 'not_assessed',
                     'reason_codes': ['resource_limit'] if partial else [], 'values': values,
                     'basis': [{'kind': 'local_calculation', 'record_ids': ['snapshot-before']}],
                     'support_ids': [], 'contrary_ids': [], 'dependency_ids': ['frame-one', 'snapshot-before'],
                     'limitations': []}],
        'findings': [], 'limitations': ['Synthetic report grammar fixture.'],
    })


def full_detail(markdown):
    match = re.search(r'^(`{3,})json\n(.*?)\n\1$', markdown, re.M | re.S)
    if match is None:
        raise AssertionError('Complete inert JSON detail missing')
    return json.loads(match.group(2))


class StructuralReportingTests(unittest.TestCase):
    def test_exact_fraction_profile_reading_view_and_complete_detail(self):
        report = report_for()
        markdown = render_markdown(report)
        self.assertEqual(full_detail(markdown), report)
        self.assertIn('| SCI | 5/9 |\n| D | 4/9 |', markdown)
        self.assertIn('| Assignment coverage \\(A/N\\) | 1/1 |', markdown)
        self.assertIn('| class\\-a | 4 |\n| class\\-b | 2 |', markdown)
        self.assertNotIn('0.555', markdown)
        self.assertLess(markdown.index('snapshot\\-before / selected'), markdown.index('snapshot\\-before / confirmed\\_valid'))

    def test_compare_reading_view_preserves_mode_denominators_and_scoped_tail_loss(self):
        report = report_for('compare')
        markdown = render_markdown(report)
        self.assertEqual(full_detail(markdown), report)
        self.assertIn('Mode: descriptive. Compatibility: supported.', markdown)
        self.assertIn('| Delta SCI \\(after \\- before\\) | 4/9 |', markdown)
        self.assertIn('| Delta D \\(after \\- before\\) | \\-4/9 |', markdown)
        self.assertIn('selected\\_catalog | 2 | 0 | loss', markdown)
        self.assertIn('unavailable \\(inapplicable\\)', markdown)

    def test_invalid_nested_profile_shapes_are_rejected_after_rehash(self):
        changes = [
            lambda value: value.update(raw_body='PRIVATE_RAW_BODY'),
            lambda value: value.update(membership_complete=1),
            lambda value: value.update(count_scope='entire_universe'),
            lambda value: value['class_counts'][0].update(count=count(True)),
            lambda value: value['class_counts'].append(deepcopy(value['class_counts'][0])),
            lambda value: value['member_reasons'][0].update(primary_reason='certain'),
            lambda value: value['member_reasons'][0].update(reason_codes=['invented']),
            lambda value: value['member_reasons'][0].update(assignment_id='<script>'),
            lambda value: value['known_subset'].update(raw_content='PRIVATE_RAW_BODY'),
            lambda value: value['tails'][0].update(state='universal_absence'),
            lambda value: value['tails'][0].update(state='absent'),
            lambda value: value['tails'][0].update(count=count(0)),
            lambda value: value['tails'][0].update(evidence_ids=['z', 'a']),
            lambda value: value['reason_counts'].append({'reason': 'invented', 'count': count(1)}),
        ]
        for change in changes:
            report = report_for()
            change(report['results'][0]['values']['profiles'][0])
            with self.subTest(change=changes.index(change)), self.assertRaises(ReportError):
                render_markdown(rehash(report))

    def test_confirmed_valid_nested_shapes_remain_closed(self):
        changes = [
            lambda value: value['validity_members'][0].update(state='inferred_valid'),
            lambda value: value['validity_members'][0].update(validity_id=True),
            lambda value: value['validity_counts'][0].update(count=count(-1)),
            lambda value: value['validity_counts'].pop(),
            lambda value: value['validity_coverage'].update(value=True),
            lambda value: value.pop('V'),
        ]
        for change in changes:
            report = report_for()
            change(report['results'][0]['values']['profiles'][1])
            with self.subTest(change=changes.index(change)), self.assertRaises(ReportError):
                render_markdown(rehash(report))

    def test_exact_numeric_wrappers_reject_noncanonical_or_fabricated_values(self):
        malformed = [
            ratio(2, 4), ratio(0, 2), ratio('-0', 1), ratio('01', 2), ratio(1, '02'),
            ratio(1, 0), ratio(1, -1), ratio(2, 1), ratio(-1, 2), ratio('1e0', 2),
            ratio('1' * 33, 1), {'state': 'available', 'value': True},
            {'state': 'available', 'value': 0.5},
            {'state': 'unavailable', 'reason': 'unknown_membership', 'value': 0},
            {'state': 'undefined'}, {'state': 'undefined', 'reason': 'invented'},
        ]
        for number in malformed:
            report = report_for()
            report['results'][0]['values']['profiles'][0]['SCI'] = number
            with self.subTest(number=number), self.assertRaises(ReportError):
                render_markdown(rehash(report))

    def test_invalid_comparison_nested_payloads_are_rejected_after_rehash(self):
        changes = [
            lambda value: value.update(mode='complete_cases'),
            lambda value: value['compatibility'].update(state='proven'),
            lambda value: value['compatibility']['field_checks'][0].update(field='raw_policy_text'),
            lambda value: value['compatibility']['field_checks'][0].update(state='different'),
            lambda value: value.update(pair_gaps=[{'before_item_id': 'item-1', 'after_item_id': 'item-2', 'reason_codes': [], 'raw': 'secret'}]),
            lambda value: value['tail_changes'][0].update(change='model_incapable'),
            lambda value: value['tail_changes'][0].update(scope='whole_world'),
            lambda value: value['tail_changes'][0].update(after_count=count(False)),
            lambda value: value['tail_changes'][0].update(after_count=count(1)),
            lambda value: value['tail_changes'][0].update(after_status='zero_admitted_sightings'),
            lambda value: value['tail_changes'][0].update(after_status='absent_in_empty_population'),
            lambda value: value['catalog_profiles']['after'][0]['class_counts'][0].update(count=count(-1)),
            lambda value: value.update(new_observations=count(1)),
            lambda value: value.update(delta_D=ratio(-5, 4)),
            lambda value: value['compatibility'].update(frame_equivalence={'assessment': 'supported_under_scope'}),
        ]
        for change in changes:
            report = report_for('compare')
            change(report['results'][0]['values'])
            with self.subTest(change=changes.index(change)), self.assertRaises(ReportError):
                render_markdown(rehash(report))

    def test_partial_profile_retains_completed_view_without_inventing_second_view(self):
        report = report_for(values={'profiles': [profile()]}, partial=True)
        markdown = render_markdown(report)
        self.assertEqual(full_detail(markdown), report)
        self.assertIn('Execution is partial.', markdown)
        self.assertNotIn('confirmed\\_valid', markdown)
        bad = report_for(values={'profiles': []})
        with self.assertRaises(ReportError):
            render_markdown(bad)

    def test_partial_compare_retains_catalog_but_blocks_requested_delta(self):
        values = compare_values()
        values.update(before={}, after={}, pair_gaps=[], tail_changes=[],
                      delta_SCI=unavailable('resource_limit'), delta_D=unavailable('resource_limit'),
                      compatibility={'state': 'unavailable', 'reason_codes': ['resource_limit'], 'field_checks': []},
                      catalog_profiles={'before': [profile()], 'after': []})
        report = report_for('compare', values, partial=True)
        markdown = render_markdown(report)
        self.assertEqual(full_detail(markdown), report)
        self.assertIn('Before comparison population: unavailable.', markdown)
        self.assertIn('Before catalog / selected', markdown)
        self.assertIn('| SCI | 5/9 |', markdown)
        values['delta_SCI'] = ratio(0)
        with self.assertRaises(ReportError):
            render_markdown(rehash(report))

    def test_arithmetic_results_cannot_acquire_epistemic_support_verdict(self):
        for operation in ('profile', 'compare'):
            report = report_for(operation)
            report['results'][0]['assessment'] = 'supported_under_scope'
            with self.subTest(operation=operation), self.assertRaises(ReportError):
                render_markdown(rehash(report))

    def test_unfinished_profile_retains_only_closed_completed_member_inventories(self):
        progress = {
            'snapshot_id': 'snapshot-before', 'frame_id': 'frame-one',
            'population': 'confirmed_valid', 'member_reasons': profile()['member_reasons'][:1],
            'validity_members': confirmed_profile()['validity_members'][:2],
            'reason_codes': ['resource_limit'],
        }
        values = {'profiles': [profile()], 'partial_profiles': [progress]}
        report = report_for(values=values, partial=True)
        self.assertEqual(full_detail(render_markdown(report)), report)
        self.assertIn('Completed member and validity decisions from unfinished views', render_markdown(report))
        changes = [
            lambda row: row.update(N=count(1)),
            lambda row: row.update(SCI=ratio(1)),
            lambda row: row.update(reason_codes=[]),
            lambda row: row.update(member_reasons=True),
            lambda row: row['member_reasons'][0].update(raw_body='PRIVATE_BODY'),
            lambda row: row['member_reasons'][0].update(class_id=False),
            lambda row: row['validity_members'][0].update(state='inferred_valid'),
        ]
        for change in changes:
            invalid = deepcopy(report)
            change(invalid['results'][0]['values']['partial_profiles'][0])
            with self.subTest(change=changes.index(change)), self.assertRaises(ReportError):
                render_markdown(rehash(invalid))
        completed = report_for(values=deepcopy(values))
        with self.assertRaises(ReportError):
            render_markdown(completed)

    def test_partial_comparison_accepts_unfinished_member_inventory_without_metrics(self):
        values = compare_values()
        values.update(before={}, after={}, pair_gaps=[], tail_changes=[],
                      delta_SCI=unavailable('resource_limit'), delta_D=unavailable('resource_limit'),
                      compatibility={'state': 'unavailable', 'reason_codes': ['resource_limit'], 'field_checks': []},
                      catalog_profiles={'before': [profile()], 'after': []},
                      partial_profiles=[{'snapshot_id': 'snapshot-after', 'frame_id': 'frame-one',
                                         'population': 'selected', 'member_reasons': profile()['member_reasons'][:1],
                                         'validity_members': [], 'reason_codes': ['resource_limit']}])
        report = report_for('compare', values, partial=True)
        self.assertEqual(full_detail(render_markdown(report)), report)
        report['results'][0]['values']['partial_profiles'][0]['validity_members'] = {'item_id': 'item-one'}
        with self.assertRaises(ReportError):
            render_markdown(rehash(report))

    def test_public_interrupted_profile_preserves_completed_positive_member(self):
        original = structural_module._assignment
        calls = 0

        def stop_before_second_member(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise WorkLimit(run_exhausted=False)
            return original(*args, **kwargs)

        data = files('evaluation_closure_toolkit').joinpath('data', 'growing-catalog.json').read_bytes()
        with patch('evaluation_closure_toolkit.structural._assignment', side_effect=stop_before_second_member):
            report = analyze_bytes(data, request_ids=('profile-a',))
        result = next(row for row in report['results'] if row['request_id'] == 'profile-a')
        self.assertEqual(result['execution'], 'partial')
        self.assertEqual(result['values']['profiles'], [])
        progress, = result['values']['partial_profiles']
        self.assertEqual(progress['snapshot_id'], 'snapshot-a')
        self.assertEqual(progress['reason_codes'], ['resource_limit'])
        member, = progress['member_reasons']
        self.assertEqual(member['primary_reason'], 'admitted')
        self.assertIn('class_id', member)
        self.assertFalse({'N', 'A', 'SCI', 'D', 'tails'} & progress.keys())
        self.assertEqual(full_detail(render_markdown(report)), report)

    def test_complete_empty_target_loss_renders_with_its_empty_population_scope(self):
        data = json.loads(files('evaluation_closure_toolkit').joinpath('data', 'growing-catalog.json').read_bytes())
        after = next(record for record in data['records'] if record['id'] == 'snapshot-b')
        after.update(members=[], assignments=[], validities=[])
        report = analyze_bytes(json.dumps(data).encode(), request_ids=('compare-catalog',))
        result = next(row for row in report['results'] if row['request_id'] == 'compare-catalog')
        changes = result['values']['tail_changes']
        self.assertTrue(changes)
        self.assertTrue(all(row['change'] == 'loss' and row['after_status'] == 'absent_in_empty_population'
                            for row in changes))
        self.assertEqual(full_detail(render_markdown(report)), report)


if __name__ == '__main__':
    unittest.main()
