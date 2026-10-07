"""Independent member-count and evidence-boundary oracles for P0-3 7.2/10.3."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from evaluation_closure_toolkit import analyze_bytes, render_markdown
from evaluation_closure_toolkit.admission import admit
from evaluation_closure_toolkit.budget import RequestBudget, WorkLimit
from evaluation_closure_toolkit.evidence import evaluate_reviews, make_review_index, member_relevant
from provenance_helpers import fixture, known, gap, wire, record, result, member, copy_review, copy_event


class ExternalTests(unittest.TestCase):
    def analyze(self, dossier):
        report = analyze_bytes(wire(dossier))
        self.assertEqual(report["admission"], "valid", report.get("diagnostics"))
        self.assertEqual(report["execution"], "completed")
        render_markdown(report)
        return report

    def test_three_member_retention_counts_are_not_event_counts(self):
        report = self.analyze(fixture("external-contact"))
        value = result(report, "external-main")["values"]
        self.assertEqual(value["known_member_count"], {"state": "available", "value": 3})
        self.assertEqual(value["stage_counts"]["retained"], {
            "yes": {"state": "available", "value": 1}, "no": {"state": "available", "value": 1},
            "unresolved": {"state": "available", "value": 1}, "disputed": {"state": "available", "value": 0}})
        self.assertEqual(value["event_counts"]["retained"], {"state": "available", "value": 3})
        self.assertEqual(len(member(report, "p")["stages"]["retained"]["events"]), 2)

    def test_use_survives_missing_receipt_and_wrong_boundary_review(self):
        row = member(self.analyze(fixture("external-contact")), "q")
        self.assertEqual(row["stages"]["used"]["state"], "yes")
        self.assertEqual(row["stages"]["received"]["state"], "unresolved")
        self.assertEqual(row["externality"]["assessment"], "unresolved")
        self.assertIn("scope_mismatch", row["externality"]["reason_codes"])
        self.assertEqual(row["qualification"]["assessment"], "unresolved")
        self.assertEqual(row["contact_state"], "unresolved")
        self.assertEqual(row["stages"]["selected"]["state"], "no")

    def test_externality_does_not_supply_use_suitability(self):
        d = fixture("external-contact")
        record(d, "cohort")["qualifications"] = []
        row = member(self.analyze(d))
        self.assertEqual(row["externality"]["assessment"], "supported_under_scope")
        self.assertEqual(row["qualification"]["assessment"], "unresolved")
        self.assertEqual(row["stages"]["used"]["state"], "yes")
        self.assertEqual(row["contact_state"], "unresolved")

    def test_positive_contact_is_only_scoped_documentary_contact(self):
        report = self.analyze(fixture("external-contact"))
        self.assertEqual(member(report)["contact_state"], "documented_current_contact")
        self.assertEqual(result(report, "external-main")["assessment"], "not_assessed")
        self.assertNotIn("conclusion", result(report, "external-main")["values"])
        self.assertNotIn("presence_score", str(report))

    def test_carryover_and_old_receipts_do_not_create_fresh_contact(self):
        row = member(self.analyze(fixture("external-contact")), "r")
        self.assertTrue(row["carryover"])
        self.assertEqual(row["stages"]["used"]["state"], "yes")
        self.assertEqual(row["stages"]["received"]["state"], "unresolved")
        self.assertEqual(row["contact_state"], "carryover_only")
        self.assertIn("scope_mismatch", row["stages"]["received"]["events"][0]["reason_codes"])

    def test_later_recording_date_does_not_replace_event_time(self):
        d = fixture("external-contact")
        record(d, "p-received")["recorded_at"] = known("2027-01-01T00:00:00Z")
        self.assertEqual(member(self.analyze(d))["stages"]["received"]["state"], "yes")
        record(d, "p-received")["occurred_at"] = gap()
        self.assertEqual(member(self.analyze(d))["stages"]["received"]["state"], "unresolved")

    def test_half_open_event_window(self):
        for time, expected in (("2026-09-01T00:00:00Z", "yes"), ("2026-10-01T00:00:00Z", "unresolved"),
                               ("2026-08-31T23:59:59Z", "unresolved"), ("2026-09-30T23:59:59Z", "yes")):
            d = fixture("external-contact")
            record(d, "p-received")["occurred_at"] = known(time)
            self.assertEqual(member(self.analyze(d))["stages"]["received"]["state"], expected)

    def test_unknown_scope_window_blocks_time_scoped_qualification(self):
        d = fixture("external-contact")
        record(d, "scope")["window"] = gap()
        row = member(self.analyze(d))
        self.assertEqual(row["stages"]["used"]["state"], "unresolved")
        self.assertEqual(row["externality"]["assessment"], "unresolved")
        self.assertEqual(row["qualification"]["assessment"], "unresolved")

    def test_missing_checkpoint_blocks_event_count_promotion(self):
        for target in ("cohort", "p-used"):
            d = fixture("external-contact")
            del record(d, target)["checkpoint"]
            row = member(self.analyze(d))["stages"]["used"]
            self.assertEqual(row["state"], "unresolved")
            self.assertIn("missing_field", row["reason_codes"])

    def test_distinct_checkpoint_does_not_supply_or_contradict_selected_checkpoint(self):
        d = fixture("external-contact")
        copy_event(d, "other-checkpoint", verdict=known("no"), checkpoint=known("checkpoint-two"))
        row = member(self.analyze(d))["stages"]["used"]
        self.assertEqual(row["state"], "yes")
        self.assertFalse(row["events"][0]["relevant"])
        self.assertFalse(row["events"][0]["qualified"])

    def test_used_and_selected_require_exact_purpose(self):
        for target, stage in (("p-used", "used"), ("p-selected", "selected")):
            d = fixture("external-contact")
            record(d, target)["purpose"] = known("different-use")
            self.assertEqual(member(self.analyze(d))["stages"][stage]["state"], "unresolved")
            del record(d, target)["purpose"]
            self.assertEqual(member(self.analyze(d))["stages"][stage]["state"], "unresolved")

    def test_use_requires_exact_target_but_receipt_does_not(self):
        d = fixture("external-contact")
        for target in ("p-used", "p-received"):
            del record(d, target)["target_id"]
        row = member(self.analyze(d))
        self.assertEqual(row["stages"]["used"]["state"], "unresolved")
        self.assertEqual(row["stages"]["received"]["state"], "yes")

    def test_retention_requires_representation_and_member_review(self):
        for mutation in ("representation", "review", "other-member"):
            d = fixture("external-contact")
            if mutation == "representation":
                for identity in ("p-retained-one", "p-retained-two"):
                    del record(d, identity)["representation"]
            elif mutation == "review":
                d["records"] = [r for r in d["records"] if r["id"] != "retention-p"]
            else:
                record(d, "retention-p")["member_id"] = "q"
            self.assertEqual(member(self.analyze(d))["stages"]["retained"]["state"], "unresolved")

    def test_explicit_no_and_missing_logs_are_distinct(self):
        d = fixture("external-contact")
        record(d, "p-received")["verdict"] = known("no")
        report = self.analyze(d)
        self.assertEqual(member(report)["stages"]["received"]["state"], "no")
        self.assertEqual(member(report, "q")["stages"]["received"]["state"], "unresolved")

    def test_conflicting_events_are_disputed_without_latest_wins(self):
        d = fixture("external-contact")
        copy_event(d, "p-later-no", verdict=known("no"), occurred_at=known("2026-09-25T12:00:00Z"))
        row = member(self.analyze(d))["stages"]["used"]
        self.assertEqual(row["state"], "disputed")
        self.assertEqual(len(row["events"]), 2)

    def test_unqualified_opposing_assertion_still_blocks_support(self):
        d = fixture("external-contact")
        copy_event(d, "p-unsupported-no", verdict=known("no"), evidence_ids=[])
        row = member(self.analyze(d))["stages"]["used"]
        self.assertEqual(row["state"], "disputed")
        self.assertTrue(any(e["qualified"] for e in row["events"]))

    def test_old_opposing_event_does_not_contaminate_current_window(self):
        d = fixture("external-contact")
        copy_event(d, "old-no", verdict=known("no"), occurred_at=known("2026-08-01T00:00:00Z"))
        self.assertEqual(member(self.analyze(d))["stages"]["used"]["state"], "yes")

    def test_evidence_access_kind_body_and_producer_requirements(self):
        mutations = (("access", known("referenced_only")), ("access", known("withheld")),
                     ("kind", known("simulation_record")), ("kind", known("declaration")),
                     ("kind", known("execution_record")), ("producer_id", gap()), ("content", gap("withheld")))
        for key, value in mutations:
            d = fixture("external-contact")
            record(d, "p-used-receipt")[key] = value
            row = member(self.analyze(d))
            self.assertEqual(row["stages"]["used"]["state"], "unresolved", key)
            self.assertEqual(row["stages"]["received"]["state"], "yes")

    def test_event_evidence_must_address_exact_member_or_event(self):
        d = fixture("external-contact")
        record(d, "p-used-receipt")["subject_ids"] = ["q"]
        self.assertEqual(member(self.analyze(d))["stages"]["used"]["state"], "unresolved")
        record(d, "p-used-receipt")["subject_ids"] = ["p-used"]
        self.assertEqual(member(self.analyze(d))["stages"]["used"]["state"], "yes")

    def test_review_support_must_include_exact_member(self):
        d = fixture("external-contact")
        record(d, "external-p-receipt")["subject_ids"] = ["q", "cohort"]
        row = member(self.analyze(d))
        self.assertEqual(row["externality"]["assessment"], "unresolved")
        self.assertEqual(row["qualification"]["assessment"], "supported_under_scope")

    def test_each_named_evidence_record_must_qualify(self):
        d = fixture("external-contact")
        record(d, "p-used")["evidence_ids"].append("q-used-receipt")
        record(d, "q-used-receipt")["access"] = known("referenced_only")
        self.assertEqual(member(self.analyze(d))["stages"]["used"]["state"], "unresolved")

    def test_event_contrary_does_not_delete_witness_and_blocks_positive_state(self):
        d = fixture("external-contact")
        record(d, "p-used-receipt")["contrary_ids"] = ["p-selected-receipt"]
        row = member(self.analyze(d))["stages"]["used"]
        self.assertEqual(row["state"], "disputed")
        self.assertEqual(row["events"][0]["contrary_ids"], ["p-selected-receipt"])

    def test_one_members_opposing_review_never_applies_to_another(self):
        d = fixture("external-contact")
        copy_review(d, "q-opposition", member_id="q", verdict="contradicts", decisive=known(True),
                    counterexample_ids=["q"], evidence_ids=["q-used-receipt"])
        report = self.analyze(d)
        self.assertEqual(member(report)["externality"]["assessment"], "supported_under_scope")
        self.assertEqual(member(report, "q")["externality"]["assessment"], "contradicted_under_scope")
        self.assertNotIn("q-opposition", member(report)["externality"]["dependency_ids"])

    def test_other_members_counterexample_cannot_defeat_current_member(self):
        d = fixture("external-contact")
        for target in ("q", "q-used", "q-used-receipt"):
            mutated = deepcopy(d)
            copy_review(mutated, "p-opposition", verdict="contradicts", decisive=known(True), counterexample_ids=[target])
            row = member(self.analyze(mutated))["externality"]
            self.assertEqual(row["assessment"], "unresolved")
            self.assertEqual(row["values"]["decisive_review_ids"], [])

    def test_target_member_bound_contrary_does_not_contaminate_others(self):
        d = fixture("external-contact")
        record(d, "cohort")["contrary_ids"] = ["q-used-receipt"]
        report = self.analyze(d)
        self.assertEqual(member(report)["externality"]["assessment"], "supported_under_scope")
        self.assertEqual(member(report)["stages"]["used"]["state"], "yes")
        self.assertEqual(member(report, "q")["stages"]["used"]["state"], "disputed")

    def test_wrong_scope_opposition_cannot_defeat_exact_scope(self):
        d = fixture("external-contact")
        copy_review(d, "wrong-opposition", verdict="contradicts", scope_id="scope-other", decisive=known(True), counterexample_ids=["p"])
        row = member(self.analyze(d))["externality"]
        self.assertEqual(row["assessment"], "supported_under_scope")
        wrong = next(r for r in row["values"]["reviews"] if r["review_id"] == "wrong-opposition")
        self.assertFalse(wrong["selected"])
        self.assertFalse(wrong["qualified"])

    def test_qualified_support_cannot_resolve_counterexample_by_recency(self):
        d = fixture("external-contact")
        copy_review(d, "counter-review", verdict="contradicts")
        copy_review(d, "newer-support", reviewed_at=known("2026-10-01T00:00:00Z"))
        row = member(self.analyze(d))["externality"]
        self.assertEqual(row["assessment"], "unresolved")
        self.assertIn("disputed", row["reason_codes"])

    def test_exact_resolution_preserves_historical_contrary(self):
        d = fixture("external-contact")
        copy_review(d, "counter-review", verdict="contradicts")
        copy_review(d, "resolver", resolves=["counter-review"])
        row = member(self.analyze(d))["externality"]
        self.assertEqual(row["assessment"], "supported_under_scope")
        self.assertIn("counter-review", row["values"]["resolved_ids"])
        self.assertIn("counter-review", row["contrary_ids"])

    def test_other_member_resolution_cannot_remove_current_member_conflict(self):
        d = fixture("external-contact")
        copy_review(d, "counter-review", verdict="contradicts")
        copy_review(d, "q-resolver", member_id="q", evidence_ids=["q-used-receipt"], resolves=["counter-review"])
        self.assertEqual(member(self.analyze(d))["externality"]["assessment"], "unresolved")

    def test_resolution_cycle_stays_disputed(self):
        d = fixture("external-contact")
        copy_review(d, "cycle-a", resolves=["cycle-b"])
        copy_review(d, "cycle-b", resolves=["cycle-a"])
        self.assertEqual(member(self.analyze(d))["externality"]["assessment"], "unresolved")

    def test_selected_review_cannot_be_bypassed_by_other_favorable_review(self):
        d = fixture("external-contact")
        del record(d, "external-p")["method"]
        copy_review(d, "unselected-favorable", method=known("Synthetic inspection"))
        self.assertEqual(member(self.analyze(d))["externality"]["assessment"], "unresolved")

    def test_qualified_exact_resolution_may_replace_selected_review(self):
        d = fixture("external-contact")
        record(d, "external-p")["verdict"] = known("unresolved")
        copy_review(d, "selected-replacement", resolves=["external-p"])
        self.assertEqual(member(self.analyze(d))["externality"]["assessment"], "supported_under_scope")

    def test_unknown_cohort_membership_only_has_known_subset_counts(self):
        for fact in (known("partial"), known("unknown"), gap("withheld"), gap("disputed")):
            d = fixture("external-contact")
            record(d, "cohort")["membership"] = fact
            value = result(self.analyze(d), "external-main")["values"]
            self.assertEqual(value["count_scope"], "known_subset")
            self.assertEqual(value["known_member_count"], {"state": "available", "value": 3})
            self.assertEqual(value["full_member_count"], {"state": "unavailable", "reason": "unknown_membership"})
            self.assertEqual(value["stage_counts"]["retained"]["yes"]["value"], 1)

    def test_known_empty_cohort_is_zero_inventory_without_support(self):
        d = fixture("external-contact")
        d["records"] = [r for r in d["records"] if r["type"] not in {"review", "external_event", "evidence"}]
        cohort = record(d, "cohort")
        for field in ("members", "externality_reviews", "qualifications", "carryover_ids"):
            cohort[field] = []
        value = result(self.analyze(d), "external-main")["values"]
        self.assertEqual(value["member_states"], [])
        self.assertEqual(value["known_member_count"]["value"], 0)
        self.assertEqual(value["qualification_counts"]["supported_under_scope"]["value"], 0)

    def test_fresh_human_remote_labels_do_not_qualify_externality(self):
        d = fixture("external-contact")
        record(d, "cohort")["externality_reviews"] = []
        record(d, "p")["label"] = known("verified independent fresh human source")
        record(d, "p-received-receipt")["locator"] = known("https://example.invalid/verified")
        row = member(self.analyze(d))
        self.assertEqual(row["externality"]["assessment"], "unresolved")
        self.assertEqual(row["stages"]["received"]["state"], "yes")

    def test_member_binding_is_required_and_index_does_not_change_outcomes(self):
        d = admit(wire(fixture("external-contact")))
        records = {r["id"]: r for r in d["records"]}
        for criterion in ("externality", "input_qualification", "retention"):
            with self.assertRaisesRegex(ValueError, "MEMBER_BINDING_REQUIRED"):
                evaluate_reviews(records, "cohort", criterion, "scope")
            plain = evaluate_reviews(records, "cohort", criterion, "scope", member_id="p")
            indexed = evaluate_reviews(records, "cohort", criterion, "scope", member_id="p", review_index=make_review_index(records))
            self.assertEqual(plain, indexed)

    def test_partial_accounting_retains_complete_member_without_full_totals(self):
        d = fixture("external-contact")
        found = False
        for limit in range(30, 200):
            with patch("evaluation_closure_toolkit.api.RequestBudget", side_effect=lambda **kw: RequestBudget(limit=limit, **kw)):
                report = analyze_bytes(wire(d))
            value = result(report, "external-main")["values"]
            if report["execution"] == "partial" and value["member_states"] and value["member_states"][0]["completed"]:
                found = True
                self.assertEqual(value["member_states"][0]["contact_state"], "documented_current_contact")
                self.assertFalse(value["accounting_complete"])
                self.assertEqual(value["stage_counts"]["used"]["yes"], {"state": "unavailable", "reason": "resource_limit"})
                render_markdown(report)
                break
        self.assertTrue(found)

    def test_member_evidence_with_cohort_parent_stays_member_specific(self):
        d = fixture("external-contact")
        record(d, "q-used-receipt")["subject_ids"].append("cohort")
        record(d, "cohort")["contrary_ids"] = ["q-used-receipt"]
        report = self.analyze(d)
        self.assertEqual(member(report)["externality"]["assessment"], "supported_under_scope")
        self.assertEqual(member(report)["stages"]["used"]["state"], "yes")
        copy_review(d, "p-wrong-counter", verdict="contradicts", decisive=known(True), counterexample_ids=["q-used-receipt"])
        self.assertEqual(member(self.analyze(d))["externality"]["assessment"], "unresolved")

    def test_input_order_is_inert_for_member_and_event_results(self):
        d = fixture("external-contact")
        expected = result(self.analyze(d), "external-main")
        d["records"].reverse()
        record(d, "cohort")["members"].reverse()
        self.assertEqual(result(self.analyze(d), "external-main"), expected)

    def test_member_subject_scans_are_charged_before_examination(self):
        d = admit(wire(fixture("external-contact")))
        records = {r["id"]: r for r in d["records"]}
        with self.assertRaises(WorkLimit):
            member_relevant(records["q-used-receipt"], "cohort", "p", records, RequestBudget(limit=1))


if __name__ == "__main__":
    unittest.main()
