"""Independent P0-3 section 10.2 oracles for packaged structural examples.

Expected fractions below are literal specification values. No production
algorithm, schema registry, metric helper, or classifier constructs the oracle.
"""
from copy import deepcopy
from importlib.resources import files
import json
import unittest

from evaluation_closure_toolkit import analyze_bytes, render_markdown, validate_bytes


def fixture(name='growing-catalog'):
    return json.loads(files('evaluation_closure_toolkit').joinpath('data', name + '.json').read_bytes())


def known(value):
    return {'state': 'known', 'value': value}


def gap(state='unknown'):
    return {'state': state, 'reason': 'Explicit synthetic test gap.', 'evidence_ids': []}


def encoded(dossier):
    return json.dumps(dossier, sort_keys=True, separators=(',', ':')).encode() + b'\n'


def record(dossier, identifier):
    return next(row for row in dossier['records'] if row['id'] == identifier)


def request(dossier, identifier):
    return next(row for row in dossier['requests'] if row['id'] == identifier)


def result(report, identifier):
    return next(row for row in report['results'] if row['request_id'] == identifier)


def profile(report, identifier='profile-a', population='selected'):
    return next(row for row in result(report, identifier)['values']['profiles']
                if row['population'] == population)


def remove_member(dossier, snapshot_id, item_id):
    snapshot = record(dossier, snapshot_id)
    snapshot['members'].remove(item_id)
    for field in ('assignments', 'validities'):
        snapshot[field] = [row for row in snapshot[field] if row['item_id'] != item_id]


class StructuralAcceptanceTests(unittest.TestCase):
    def analyze(self, dossier):
        report = analyze_bytes(encoded(dossier))
        self.assertEqual(report['admission'], 'valid', report.get('diagnostics'))
        self.assertEqual(report['execution'], 'completed')
        return report

    def assert_count(self, metric, expected):
        self.assertEqual(metric, {'state': 'available', 'value': expected})

    def assert_fraction(self, metric, numerator, denominator):
        self.assertEqual(metric, {'state': 'available', 'value': {
            'numerator': str(numerator), 'denominator': str(denominator)}})

    def counts(self, entry):
        return {row['class_id']: row['count'] for row in entry['class_counts']}

    def tail(self, entry, class_id='class-four'):
        return next(row for row in entry['tails'] if row['class_id'] == class_id)

    def test_packaged_examples_admit_and_execute(self):
        for name in ('growing-catalog', 'matched-cohort', 'recut-comparison'):
            with self.subTest(name=name):
                dossier = fixture(name)
                self.assertEqual(validate_bytes(encoded(dossier))['admission'], 'valid')
                report = self.analyze(dossier)
                self.assertTrue(all(row['assessment'] == 'not_assessed'
                                    for row in report['results']))

    def test_complete_baseline_and_growing_catalog_exact_arithmetic(self):
        report = self.analyze(fixture())
        a, b = profile(report), profile(report, 'profile-b')
        for key, expected in [('K', 24), ('N', 24), ('A', 24), ('U', 0), ('observed_support', 4)]:
            self.assert_count(a[key], expected)
        self.assert_fraction(a['SCI'], 25, 72)
        self.assert_fraction(a['D'], 47, 72)
        self.assert_fraction(a['assignment_coverage'], 1, 1)
        self.assert_count(b['N'], 48)
        self.assert_count(b['observed_support'], 3)
        self.assert_fraction(b['SCI'], 7, 18)
        self.assert_fraction(b['D'], 11, 18)
        for name, expected in [('class-one', 24), ('class-two', 16), ('class-three', 8), ('class-four', 0)]:
            self.assert_count(self.counts(b)[name], expected)
        comparison = result(report, 'compare-catalog')['values']
        self.assert_fraction(comparison['delta_SCI'], 1, 24)
        self.assert_fraction(comparison['delta_D'], -1, 24)
        self.assertEqual(comparison['mode'], 'descriptive')
        self.assertEqual(comparison['pair_count']['state'], 'unavailable')
        fourth = next(row for row in comparison['tail_changes'] if row['before_class_id'] == 'class-four')
        self.assertEqual(fourth['change'], 'loss')
        self.assertEqual(fourth['scope'], 'selected_catalog')

    def test_model_failure_receipts_do_not_remove_structural_items(self):
        dossier = fixture()
        report = self.analyze(dossier)
        before = profile(report)
        self.assert_count(before['A'], 24)
        self.assert_count(self.counts(before)['class-four'], 2)
        self.assertIn('tail-failure-receipt', json.dumps(report))
        record(dossier, 'tail-failure-receipt')['content'] = known('Both scripted answers succeeded instead.')
        after = profile(self.analyze(dossier))
        for field in ('K', 'N', 'A', 'U', 'class_counts', 'SCI', 'D'):
            self.assertEqual(before[field], after[field])

    def test_one_unclassified_member_retains_roster_and_conditional_metrics(self):
        dossier = fixture()
        record(dossier, 'assignment-b-048')['decision'] = known('unclassified')
        report = self.analyze(dossier)
        b = profile(report, 'profile-b')
        self.assert_count(b['N'], 48)
        self.assert_count(b['A'], 47)
        self.assert_count(b['U'], 1)
        self.assert_fraction(b['assignment_coverage'], 47, 48)
        self.assert_fraction(b['SCI'], 881, 2209)
        self.assert_fraction(b['D'], 1328, 2209)
        self.assert_count(self.counts(b)['class-four'], 0)
        self.assertEqual(self.tail(b)['state'], 'unestablished')
        fourth = next(row for row in result(report, 'compare-catalog')['values']['tail_changes']
                      if row['before_class_id'] == 'class-four')
        self.assertNotEqual(fourth['change'], 'loss')

    def test_unknown_membership_preserves_known_subset_without_full_denominator(self):
        dossier = fixture()
        remove_member(dossier, 'snapshot-b', 'item-b-048')
        record(dossier, 'snapshot-b')['membership'] = known('unknown')
        report = self.analyze(dossier)
        b = profile(report, 'profile-b')
        self.assert_count(b['K'], 47)
        for field in ('N', 'assignment_coverage', 'SCI', 'D'):
            self.assertEqual(b[field]['state'], 'unavailable')
        self.assert_fraction(b['known_subset']['SCI'], 881, 2209)
        self.assert_fraction(b['known_subset']['D'], 1328, 2209)
        self.assertEqual(result(report, 'compare-catalog')['values']['delta_SCI']['state'], 'unavailable')
        self.assertEqual(self.tail(b)['state'], 'unestablished')

    def test_item_validity_is_separate_from_the_selected_population(self):
        dossier = fixture()
        for identifier in ('validity-a-023', 'validity-a-024'):
            record(dossier, identifier)['verdict'] = known('invalid')
        request(dossier, 'profile-a')['population'] = 'confirmed_valid'
        report = self.analyze(dossier)
        selected = profile(report)
        confirmed = profile(report, population='confirmed_valid')
        self.assert_count(selected['A'], 24)
        self.assert_fraction(selected['SCI'], 25, 72)
        self.assert_count(confirmed['V'], 22)
        self.assert_count(confirmed['N'], 22)
        self.assert_count(confirmed['K'], 24)
        self.assert_fraction(confirmed['SCI'], 49, 121)
        self.assert_fraction(confirmed['D'], 72, 121)
        self.assert_fraction(confirmed['validity_coverage'], 1, 1)
        self.assertEqual(confirmed['count_scope'], 'confirmed_valid_subset')

    def test_unknown_validity_preserves_conditional_subset_and_original_coverage(self):
        dossier = fixture()
        request(dossier, 'profile-a')['population'] = 'confirmed_valid'
        record(dossier, 'validity-a-001')['verdict'] = gap()
        confirmed = profile(self.analyze(dossier), population='confirmed_valid')
        self.assert_count(confirmed['V'], 23)
        self.assert_fraction(confirmed['validity_coverage'], 23, 24)
        self.assertFalse(confirmed['population_complete'])
        validity = {row['state']: row['count'] for row in confirmed['validity_counts']}
        self.assert_count(validity['unresolved'], 1)

    def test_unqualified_invalid_does_not_inflate_validity_coverage(self):
        dossier = fixture()
        request(dossier, 'profile-a')['population'] = 'confirmed_valid'
        invalid = record(dossier, 'validity-a-001')
        invalid['verdict'] = known('invalid')
        invalid.pop('basis')
        confirmed = profile(self.analyze(dossier), population='confirmed_valid')
        self.assert_fraction(confirmed['validity_coverage'], 23, 24)
        validity = {row['state']: row['count'] for row in confirmed['validity_counts']}
        self.assert_count(validity['invalid'], 0)
        self.assert_count(validity['unresolved'], 1)

    def test_fixed_24_pair_cohort_preserves_separate_48_item_catalog(self):
        report = self.analyze(fixture('matched-cohort'))
        matched = result(report, 'compare-matched')['values']
        catalog = result(report, 'compare-catalog')['values']
        self.assert_count(matched['pair_count'], 24)
        self.assert_count(matched['after']['N'], 24)
        self.assert_fraction(matched['after']['SCI'], 31, 72)
        self.assert_fraction(matched['after']['D'], 41, 72)
        self.assert_fraction(matched['delta_SCI'], 1, 12)
        self.assert_count(catalog['after']['N'], 48)
        self.assert_fraction(catalog['delta_SCI'], 1, 24)

    def test_missing_matched_membership_never_silently_deletes_a_pair(self):
        dossier = fixture('matched-cohort')
        remove_member(dossier, 'snapshot-b', 'item-b-024')
        matched = result(self.analyze(dossier), 'compare-matched')['values']
        self.assertEqual(matched['delta_SCI']['state'], 'unavailable')
        self.assert_count(matched['pair_count'], 24)
        self.assertTrue(any(row['after_item_id'] == 'item-b-024' for row in matched['pair_gaps']))
        self.assertNotEqual(matched.get('after', {}).get('N'), {'state': 'available', 'value': 23})

    def test_missing_matched_assignment_never_silently_deletes_a_pair(self):
        dossier = fixture('matched-cohort')
        snapshot = record(dossier, 'snapshot-b')
        snapshot['assignments'] = [row for row in snapshot['assignments'] if row['item_id'] != 'item-b-024']
        matched = result(self.analyze(dossier), 'compare-matched')['values']
        self.assertEqual(matched['delta_SCI']['state'], 'unavailable')
        self.assert_count(matched['pair_count'], 24)
        self.assertTrue(any(row['after_item_id'] == 'item-b-024' for row in matched['pair_gaps']))

    def test_false_identity_match_and_incomplete_pair_roster_cannot_yield_deltas(self):
        for change in ('logical_identity', 'membership'):
            with self.subTest(change=change):
                dossier = fixture('matched-cohort')
                if change == 'logical_identity':
                    record(dossier, 'item-b-001')['logical_id'] = 'different-observation'
                else:
                    request(dossier, 'compare-matched')['pair_membership'] = known('partial')
                matched = result(self.analyze(dossier), 'compare-matched')['values']
                self.assertEqual(matched['delta_SCI']['state'], 'unavailable')

    def test_confirmed_valid_matching_does_not_drop_invalid_endpoint(self):
        dossier = fixture('matched-cohort')
        request(dossier, 'compare-matched')['population'] = 'confirmed_valid'
        record(dossier, 'validity-b-024')['verdict'] = known('invalid')
        matched = result(self.analyze(dossier), 'compare-matched')['values']
        self.assertEqual(matched['delta_SCI']['state'], 'unavailable')
        self.assert_count(matched['pair_count'], 24)

    def test_duplicate_matched_endpoint_is_an_admission_error(self):
        dossier = fixture('matched-cohort')
        pairs = request(dossier, 'compare-matched')['pairs']
        pairs[1]['after_item_id'] = pairs[0]['after_item_id']
        report = analyze_bytes(encoded(dossier))
        self.assertEqual(report['admission'], 'invalid')
        self.assertEqual(report['results'], [])

    def test_recut_same_items_adds_no_observations_and_blocks_direct_gain(self):
        report = self.analyze(fixture('recut-comparison'))
        recut = profile(report, 'profile-b')
        self.assert_count(recut['N'], 24)
        self.assert_count(recut['observed_support'], 5)
        self.assert_fraction(recut['SCI'], 2, 9)
        self.assert_fraction(recut['D'], 7, 9)
        comparison = result(report, 'compare-catalog')['values']
        self.assert_count(comparison['new_observations'], 0)
        self.assertEqual(comparison['delta_SCI']['state'], 'unavailable')
        self.assertIn('incompatible_frame', comparison['compatibility']['reason_codes'])
        self.assertEqual(result(report, 'compare-catalog')['assessment'], 'not_assessed')

    def relabel(self):
        dossier = fixture()
        old = record(dossier, 'frame-main')
        new = deepcopy(old)
        new['id'] = 'frame-renamed'
        mapping = {row['id']: 'renamed-' + row['id'] for row in old['classes']['value']}
        for row in new['classes']['value']:
            row['id'] = mapping[row['id']]
        for row in new['tail_designations']['value']:
            row['class_id'] = mapping[row['class_id']]
        dossier['records'].append(new)
        record(dossier, 'scope-main').pop('frame_id')
        record(dossier, 'snapshot-b')['frame_id'] = 'frame-renamed'
        for row in dossier['records']:
            if row['type'] in ('assignment', 'validity') and row['item_id'].startswith('item-b-'):
                row['frame_id'] = 'frame-renamed'
                if row['type'] == 'assignment':
                    row['class_id'] = known(mapping[row['class_id']['value']])
        dossier['records'].extend([
            {'id': 'revision-relabel', 'type': 'revision', 'scope_id': 'scope-main',
             'from_frame': 'frame-main', 'to_frame': 'frame-renamed', 'kind': known('relabel'),
             'class_map': [{'from_class': source, 'to_class': target} for source, target in mapping.items()]},
            {'id': 'equivalence-receipt', 'type': 'evidence', 'scope_id': 'scope-main',
             'kind': known('document'), 'producer_id': known('actor-fixture'), 'access': known('supplied'),
             'content': known('Synthetic inspection covers all compatibility fields and exact class meaning.'),
             'subject_ids': ['revision-relabel', 'frame-main', 'frame-renamed']},
            {'id': 'equivalence-review', 'type': 'review', 'target_id': 'revision-relabel',
             'criterion': 'frame_equivalence', 'scope_id': 'scope-main',
             'assessor_id': known('actor-fixture'), 'reviewed_at': known('2026-10-05T12:00:00Z'),
             'method': known('Inspect every compatibility field and class mapping in this synthetic fixture.'),
             'rationale': known('Only class IDs have changed; all supplied meanings are unchanged.'),
             'verdict': known('supports'), 'evidence_ids': ['equivalence-receipt']},
        ])
        request(dossier, 'compare-catalog')['revision_id'] = 'revision-relabel'
        return dossier

    def test_reviewed_total_relabel_preserves_arithmetic_and_review_basis(self):
        report = self.analyze(self.relabel())
        comparison = result(report, 'compare-catalog')
        self.assert_fraction(comparison['values']['delta_SCI'], 1, 24)
        self.assertEqual(comparison['values']['compatibility']['state'], 'supported')
        self.assertIn('equivalence-review', json.dumps(comparison))

    def test_omitting_zero_count_class_from_relabel_blocks_equivalence(self):
        dossier = self.relabel()
        revision = record(dossier, 'revision-relabel')
        revision['class_map'] = [row for row in revision['class_map'] if row['from_class'] != 'class-four']
        comparison = result(self.analyze(dossier), 'compare-catalog')['values']
        self.assertEqual(comparison['compatibility']['state'], 'unavailable')
        self.assertEqual(comparison['delta_SCI']['state'], 'unavailable')

    def test_relabel_without_review_cannot_establish_semantic_equivalence(self):
        dossier = self.relabel()
        dossier['records'] = [row for row in dossier['records'] if row['id'] != 'equivalence-review']
        comparison = result(self.analyze(dossier), 'compare-catalog')['values']
        self.assertEqual(comparison['delta_SCI']['state'], 'unavailable')

    def test_empty_population_is_undefined_without_zero_metric_placeholders(self):
        dossier = fixture()
        snapshot = record(dossier, 'snapshot-b')
        for field in ('members', 'assignments', 'validities'):
            snapshot[field] = []
        b = profile(self.analyze(dossier), 'profile-b')
        for field in ('N', 'A', 'U', 'observed_support'):
            self.assert_count(b[field], 0)
        for field in ('SCI', 'D', 'assignment_coverage'):
            self.assertEqual(b[field]['state'], 'undefined')
            self.assertNotIn('value', b[field])
        self.assertEqual(self.tail(b)['state'], 'absent_in_empty_population')

    def test_zero_admitted_population_cannot_establish_class_absence(self):
        dossier = fixture()
        for row in dossier['records']:
            if row['type'] == 'assignment' and row['item_id'].startswith('item-b-'):
                row['decision'] = known('unclassified')
        b = profile(self.analyze(dossier), 'profile-b')
        self.assert_count(b['N'], 48)
        self.assert_count(b['A'], 0)
        self.assert_count(b['U'], 48)
        self.assert_fraction(b['assignment_coverage'], 0, 1)
        self.assertEqual(b['SCI']['state'], 'undefined')
        self.assertEqual(self.tail(b)['state'], 'unestablished')

    def test_single_class_population_retains_all_zero_class_rows(self):
        dossier = fixture()
        for row in dossier['records']:
            if row['type'] == 'assignment' and row['item_id'].startswith('item-b-'):
                row['class_id'] = known('class-one')
        b = profile(self.analyze(dossier), 'profile-b')
        self.assert_count(b['observed_support'], 1)
        self.assert_fraction(b['SCI'], 1, 1)
        self.assert_fraction(b['D'], 0, 1)
        self.assertEqual(len(b['class_counts']), 4)

    def test_unselected_revision_is_inert_then_explicit_selection_recomputes(self):
        dossier = fixture()
        before = profile(self.analyze(dossier), 'profile-b')
        revision = deepcopy(record(dossier, 'assignment-b-048'))
        revision.update(id='assignment-b-048-corrected', class_id=known('class-four'),
                        supersedes=known('assignment-b-048'))
        dossier['records'].append(revision)
        unselected = profile(self.analyze(dossier), 'profile-b')
        for field in ('K', 'N', 'A', 'SCI', 'D', 'class_counts'):
            self.assertEqual(before[field], unselected[field])
        row = next(row for row in record(dossier, 'snapshot-b')['assignments'] if row['item_id'] == 'item-b-048')
        row['assignment_id'] = 'assignment-b-048-corrected'
        selected = profile(self.analyze(dossier), 'profile-b')
        self.assert_count(selected['N'], 48)
        self.assert_count(self.counts(selected)['class-four'], 1)
        self.assert_fraction(selected['SCI'], 49, 128)
        self.assert_fraction(selected['D'], 79, 128)

    def test_requested_confirmed_valid_comparison_never_falls_back_to_selected(self):
        dossier = fixture()
        request(dossier, 'compare-catalog')['population'] = 'confirmed_valid'
        record(dossier, 'snapshot-b')['validities'] = []
        comparison = result(self.analyze(dossier), 'compare-catalog')['values']
        self.assertEqual(comparison['after']['population'], 'confirmed_valid')
        self.assert_count(comparison['after']['N'], 0)
        self.assertNotEqual(comparison['delta_SCI']['state'], 'available')
        selected = next(row for row in comparison['catalog_profiles']['after'] if row['population'] == 'selected')
        self.assert_count(selected['N'], 48)

    def test_duplicate_or_multiple_logical_versions_cannot_be_deduplicated(self):
        for mutation in ('duplicate', 'second_version'):
            with self.subTest(mutation=mutation):
                dossier = fixture()
                if mutation == 'duplicate':
                    record(dossier, 'snapshot-a')['members'].append('item-a-001')
                else:
                    item = deepcopy(record(dossier, 'item-a-001'))
                    item.update(id='item-a-001-v2', version='v2')
                    dossier['records'].append(item)
                    record(dossier, 'snapshot-a')['members'].append(item['id'])
                report = analyze_bytes(encoded(dossier))
                self.assertEqual(report['admission'], 'invalid')
                self.assertEqual(report['results'], [])

    def test_json_and_markdown_preserve_exact_arithmetic_without_source_bodies(self):
        report = self.analyze(fixture())
        markdown = render_markdown(report)
        for fraction in ('25/72', '47/72', '7/18', '11/18', '1/24'):
            self.assertIn(fraction, markdown)
        self.assertIn('tail-failure-receipt', markdown.replace('\\-', '-'))
        for marker in ('PRIVATE_STRUCTURAL_BODY_91', 'PRIVATE_MODEL_FAILURE_91'):
            self.assertNotIn(marker, json.dumps(report))
            self.assertNotIn(marker, markdown)


if __name__ == '__main__':
    unittest.main()
