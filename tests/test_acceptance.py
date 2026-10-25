"""Independent behavioral expectations for the first installable slice.

These literal conclusions come from P0-3/P0-4. Fixture changes use only
stdlib helpers, without importing the implementation's policy or validators.
"""
from copy import deepcopy
from importlib.resources import files
import hashlib
import json
import unittest

from evaluation_closure_toolkit import analyze_bytes, render_markdown, validate_bytes


def fixture(name):
    return json.loads(files('evaluation_closure_toolkit').joinpath('data', name + '.json').read_bytes())


def encoded(dossier):
    return json.dumps(dossier, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode() + b'\n'


def record(dossier, identifier):
    return next(row for row in dossier['records'] if row['id'] == identifier)


def known(value):
    return {'state': 'known', 'value': value}


def result(report, identifier='lint-main'):
    return next(row for row in report['results'] if row['request_id'] == identifier)


class AcceptanceTests(unittest.TestCase):
    def analyze(self, dossier):
        report = analyze_bytes(encoded(dossier))
        self.assertEqual(report['admission'], 'valid')
        return report, result(report)

    def positive(self):
        return fixture('supported-narrow-regression')

    def test_all_packaged_fixtures_pass_admission(self):
        for name in ('incomplete-regression', 'supported-narrow-regression',
                     'scope-mismatch', 'open-claim-lint'):
            with self.subTest(name=name):
                report = validate_bytes(encoded(fixture(name)))
                self.assertEqual(report['admission'], 'valid', report)

    def test_finite_support_requires_scoped_receipts_and_review(self):
        report, lint = self.analyze(self.positive())
        self.assertEqual(report['execution'], 'completed')
        self.assertEqual(lint['execution'], 'completed')
        self.assertEqual(lint['values']['claim_conclusion'], 'supported_under_scope')
        self.assertEqual(lint['values']['open_evaluation'], 'not_applicable')
        self.assertEqual(lint['values']['currentness'], 'current_under_declared_date')
        self.assertEqual(lint['values']['documentary_completeness'], 'complete')
        self.assertEqual(lint['values']['validation']['assessment'], 'supported_under_scope')
        self.assertEqual({row['id'] for row in lint['values']['disclosures']},
                         {'R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07', 'R08', 'R09', 'R10'})
        self.assertNotIn('conditions', lint['values'])

    def test_incomplete_facts_are_completed_analysis_with_gaps(self):
        report, lint = self.analyze(fixture('incomplete-regression'))
        self.assertEqual(report['execution'], 'completed')
        self.assertEqual(lint['execution'], 'completed')
        self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')
        self.assertEqual(lint['values']['currentness'], 'unestablished')
        self.assertEqual(lint['values']['documentary_completeness'], 'incomplete')
        self.assertTrue({'EC101', 'EC107'} <= {finding['family'] for finding in report['findings']})

    def test_complete_open_disclosures_never_grant_open_support(self):
        _, lint = self.analyze(fixture('open-claim-lint'))
        self.assertEqual(lint['values']['documentary_completeness'], 'complete')
        self.assertEqual(lint['values']['validation']['assessment'], 'supported_under_scope')
        self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')
        self.assertEqual(lint['values']['open_evaluation'], 'not_assessed')
        self.assertNotIn('conditions', lint['values'])
        self.assertNotIn('openness_score', lint['values'])

    def test_disclosure_gap_states_remain_distinct(self):
        for state, presence in (('unknown', 'unknown'), ('withheld', 'withheld'),
                                ('disputed', 'disputed'), ('absent', 'explicit_absence')):
            with self.subTest(state=state):
                dossier = self.positive()
                record(dossier, 'claim-v1')['disclosures']['R04'] = {
                    'state': state, 'reason': 'Synthetic attributed gap.', 'evidence_ids': []}
                _, lint = self.analyze(dossier)
                row = next(r for r in lint['values']['disclosures'] if r['id'] == 'R04')
                self.assertEqual(row['presence'], presence)
                self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')
                self.assertEqual(lint['values']['documentary_completeness'], 'incomplete')

    def test_empty_anchor_list_is_well_formed_but_cannot_discharge_required_row(self):
        dossier = self.positive()
        record(dossier, 'claim-v1')['disclosures']['R04'] = known([])
        _, lint = self.analyze(dossier)
        row = next(r for r in lint['values']['disclosures'] if r['id'] == 'R04')
        self.assertEqual(row['presence'], 'present')
        self.assertEqual(row['well_formed'], 'yes')
        self.assertEqual(row['linked'], 'no')
        self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')

    def test_structured_missing_feature_defeats_finite_claim(self):
        report, lint = self.analyze(fixture('scope-mismatch'))
        self.assertEqual(lint['values']['claim_conclusion'], 'defeated_under_scope')
        self.assertTrue(lint['values']['scope_mismatches'])
        self.assertIn('long_horizon', json.dumps(lint['values']['scope_mismatches']))
        self.assertIn('EC101', {finding['family'] for finding in report['findings']})

    def test_structured_missing_feature_also_survives_open_lint(self):
        dossier = fixture('scope-mismatch')
        record(dossier, 'claim-v1')['profile'] = 'open_evaluation'
        record(dossier, 'validation-review')['criterion'] = 'validation_type_fit'
        _, lint = self.analyze(dossier)
        self.assertEqual(lint['values']['claim_conclusion'], 'defeated_under_scope')

    def test_missing_execution_receipt_body_blocks_support_without_rejection(self):
        dossier = self.positive()
        receipt = record(dossier, 'execution-receipt')
        del receipt['content']
        receipt['access'] = known('referenced_only')
        _, lint = self.analyze(dossier)
        self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')
        self.assertEqual(lint['values']['documentary_completeness'], 'complete')
        self.assertNotEqual(lint['values']['validation']['assessment'], 'supported_under_scope')

    def test_expiry_is_half_open_and_uses_declared_time(self):
        for expiry, expected in (
            ('2026-10-06T20:59:59Z', 'expired_under_declared_date'),
            ('2026-10-06T21:00:00Z', 'expired_under_declared_date'),
            ('2026-10-06T21:00:01Z', 'current_under_declared_date'),
        ):
            with self.subTest(expiry=expiry):
                dossier = self.positive()
                record(dossier, 'claim-v1')['valid_until'] = known(expiry)
                _, lint = self.analyze(dossier)
                self.assertEqual(lint['values']['currentness'], expected)
                self.assertEqual(lint['values']['claim_conclusion'],
                                 'supported_under_scope' if expiry.endswith('01Z') else 'unestablished')

    def test_an_unavailable_extra_support_record_blocks_review(self):
        dossier = self.positive()
        receipt = deepcopy(record(dossier, 'execution-receipt'))
        receipt['id'] = 'unavailable-extra'
        receipt['access'] = known('unavailable')
        receipt.pop('content')
        dossier['records'].append(receipt)
        record(dossier, 'validation-review')['evidence_ids'].append('unavailable-extra')
        _, lint = self.analyze(dossier)
        self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')

    def test_wrong_scope_review_stays_unqualified(self):
        dossier = self.positive()
        dossier['records'].append({'id': 'scope-other', 'type': 'scope', 'process_id': 'process-v1'})
        record(dossier, 'validation-review')['scope_id'] = 'scope-other'
        _, lint = self.analyze(dossier)
        self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')
        self.assertNotEqual(lint['values']['validation']['assessment'], 'supported_under_scope')
        self.assertIn('scope_mismatch', json.dumps(lint))

    def test_wrong_scope_receipt_cannot_support_matching_review(self):
        dossier = self.positive()
        dossier['records'].append({'id': 'scope-other', 'type': 'scope', 'process_id': 'process-v1'})
        record(dossier, 'execution-receipt')['scope_id'] = 'scope-other'
        _, lint = self.analyze(dossier)
        self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')

    def test_incomplete_support_review_is_preserved_without_promotion(self):
        dossier = self.positive()
        record(dossier, 'validation-review').pop('method')
        _, lint = self.analyze(dossier)
        self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')
        self.assertIn('validation-review', json.dumps(lint))
        self.assertNotEqual(lint['values']['validation']['assessment'], 'supported_under_scope')

    def test_active_competing_assertions_block_support(self):
        for verdict, incomplete in (('contradicts', False), ('contradicts', True), ('unresolved', False)):
            with self.subTest(verdict=verdict, incomplete=incomplete):
                dossier = self.positive()
                review = deepcopy(record(dossier, 'validation-review'))
                review.update(id='competing-review', verdict=known(verdict))
                if incomplete:
                    review.pop('method')
                dossier['records'].append(review)
                _, lint = self.analyze(dossier)
                self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')
                self.assertIn('competing-review', json.dumps(lint))

    def test_decisive_scoped_counterexample_defeats_claim(self):
        dossier = self.positive()
        review = deepcopy(record(dossier, 'validation-review'))
        review.update(id='decisive-review', verdict=known('contradicts'),
                      decisive=known(True), counterexample_ids=['item-v1'])
        dossier['records'].append(review)
        _, lint = self.analyze(dossier)
        self.assertEqual(lint['values']['claim_conclusion'], 'defeated_under_scope')
        self.assertIn('decisive-review', json.dumps(lint))

    def test_simulation_or_declaration_label_cannot_supply_execution(self):
        for kind in ('simulation_record', 'declaration', 'analysis_record'):
            with self.subTest(kind=kind):
                dossier = self.positive()
                record(dossier, 'execution-receipt')['kind'] = known(kind)
                _, lint = self.analyze(dossier)
                self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')

    def test_human_consequence_requirement_needs_its_own_typed_receipt(self):
        dossier = self.positive()
        record(dossier, 'human-receipt')['kind'] = known('document')
        _, lint = self.analyze(dossier)
        self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')

    def test_unsupported_narrow_validation_kind_is_completed_scope_limit(self):
        dossier = self.positive()
        record(dossier, 'claim-v1')['validation_kind'] = known('proof')
        report, lint = self.analyze(dossier)
        self.assertEqual(report['execution'], 'completed')
        self.assertEqual(lint['values']['claim_conclusion'], 'unestablished')
        self.assertIn('unsupported_validation_kind', json.dumps(lint))

    def test_case_inventory_is_completed_without_invented_aggregate_assessment(self):
        dossier = self.positive()
        dossier['requests'] = [{'id': 'cases-main', 'operation': 'cases',
                               'scope_id': 'scope-main'}]
        report = analyze_bytes(encoded(dossier))
        self.assertEqual(report['admission'], 'valid')
        profile = result(report, 'cases-main')
        self.assertEqual(profile['execution'], 'completed')
        self.assertEqual(profile['assessment'], 'not_assessed')
        self.assertNotIn('unsupported_operation', profile['reason_codes'])
        self.assertTrue(any(f['family'] == 'EC106' and f['request_id'] == 'cases-main'
                            for f in report['findings']))

    def test_exact_request_selection_does_not_execute_future_request(self):
        dossier = self.positive()
        dossier['requests'].append({'id': 'profile-main', 'operation': 'profile',
                                    'scope_id': 'scope-main', 'snapshot_id': 'snapshot-v1'})
        report = analyze_bytes(encoded(dossier), request_ids=('lint-main',))
        self.assertEqual(report['selected_request_ids'], ['lint-main'])
        self.assertEqual(result(report)['values']['claim_conclusion'], 'supported_under_scope')
        for row in report['results']:
            if row['request_id'] == 'profile-main':
                self.assertEqual(row['selection'], 'not_selected')
                self.assertEqual(row['execution'], 'not_run')

    def test_report_hash_and_identical_bytes_are_reproducible(self):
        data = encoded(self.positive())
        first = analyze_bytes(data)
        self.assertEqual(first, analyze_bytes(data))
        self.assertEqual(first['input_sha256'], hashlib.sha256(data).hexdigest())
        payload = deepcopy(first)
        digest = payload.pop('result_sha256')
        canonical = json.dumps(payload, ensure_ascii=True, sort_keys=True,
                               separators=(',', ':'), allow_nan=False).encode() + b'\n'
        self.assertEqual(digest, hashlib.sha256(canonical).hexdigest())
        self.assertEqual(first['schema'], 'ect-report/0.1')
        self.assertEqual(first['serialization'], 'ect-json/0.1')
        self.assertEqual(first['policy'], 'ect-core/0.1')
        self.assertEqual(first['method'], 'ect-method/0.1')

    def test_reformatting_preserves_scientific_values_but_changes_identity(self):
        dossier = self.positive()
        compact = analyze_bytes(encoded(dossier))
        formatted = analyze_bytes(json.dumps(dossier, indent=2).encode())
        self.assertNotEqual(compact['input_sha256'], formatted['input_sha256'])
        self.assertNotEqual(compact['result_sha256'], formatted['result_sha256'])
        self.assertEqual(result(compact)['values'], result(formatted)['values'])

    def test_markdown_preserves_result_tokens_without_raw_private_bodies(self):
        for name in ('supported-narrow-regression', 'scope-mismatch', 'open-claim-lint'):
            with self.subTest(name=name):
                report, lint = self.analyze(fixture(name))
                markdown = render_markdown(report)
                rendered_tokens = markdown.replace('\\_', '_').replace('\\-', '-')
                self.assertIn(lint['values']['claim_conclusion'], rendered_tokens)
                self.assertIn(lint['values']['currentness'], rendered_tokens)
                self.assertIn('scope-main', rendered_tokens)
                self.assertIn('lint-main', rendered_tokens)
                for row in lint['values']['disclosures']:
                    self.assertIn(row['id'], markdown)
                for body in ('PRIVATE_ITEM_BODY_SENTINEL_73', 'PRIVATE_EXECUTION_RECEIPT_SENTINEL_73',
                             'PRIVATE_HUMAN_RECEIPT_SENTINEL_73', 'PRIVATE_CURRENTNESS_SENTINEL_73',
                             'PRIVATE_LOCATOR_SENTINEL_73', 'https://private.invalid'):
                    self.assertNotIn(body, json.dumps(report))
                    self.assertNotIn(body, markdown)

    def test_input_text_stays_inert_and_unpublished(self):
        dossier = self.positive()
        marker = 'UNTRUSTED_TEXT_SENTINEL_73 $(touch /tmp/ect-must-not-execute) <script>alert(1)</script>'
        record(dossier, 'claim-v1')['statement'] = known(marker)
        report, lint = self.analyze(dossier)
        self.assertEqual(lint['values']['claim_conclusion'], 'supported_under_scope')
        self.assertNotIn(marker, json.dumps(report))
        self.assertNotIn(marker, render_markdown(report))


if __name__ == '__main__':
    unittest.main()
