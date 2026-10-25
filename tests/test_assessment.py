"""Literal five-gate acceptance outcomes, including the mandatory P0-3 mutations."""

from copy import deepcopy
import unittest

from evaluation_closure_toolkit import analyze_bytes, render_markdown
from assessment_helpers import supported, revision_demo, evidence, review
from provenance_helpers import fixture, wire, record, known, gap


def gate(values, name):
    return next(r for r in values["conditions"] if r["condition"] == name)


def criterion(values, name):
    return next(r for g in values["conditions"] for r in g["values"]["criteria"] if r["criterion"] == name)


class AssessmentTests(unittest.TestCase):
    def analyze(self, dossier):
        report = analyze_bytes(wire(dossier))
        self.assertEqual(report["admission"], "valid", report.get("diagnostics"))
        self.assertEqual(report["execution"], "completed")
        render_markdown(report)
        return next(r for r in report["results"] if r["operation"] == "assess")["values"]

    def test_all_five_are_satisfiable_with_fourteen_separate_reviews(self):
        d = supported(); values = self.analyze(d)
        self.assertEqual(values["conclusion"], "supported_under_scope")
        self.assertEqual(values["capacity_extent"], "tested_route")
        self.assertEqual(len(values["conditions"]), 5)
        self.assertEqual(sum(len(c["values"]["criteria"]) for c in values["conditions"]), 14)
        self.assertTrue(all(c["assessment"] == "supported_under_scope" for c in values["conditions"]))
        cases = next(p["result"] for p in values["prerequisites"] if p["role"] == "cases")
        self.assertEqual(cases["values"]["corrections"][0]["context"], "drill")
        self.assertEqual(len({record(d, "review-" + r["criterion"])["id"] for c in values["conditions"] for r in c["values"]["criteria"]}), 14)

    def test_removed_use_receipt_blocks_external_presence_and_whole_claim(self):
        d = supported(); record(d, "z-used")["evidence_ids"] = []
        values = self.analyze(d)
        self.assertEqual(gate(values, "external_presence")["assessment"], "unresolved")
        self.assertEqual(values["conclusion"], "unestablished")
        self.assertEqual(gate(values, "tail_retention")["assessment"], "supported_under_scope")

    def test_decisive_scoped_tail_counterexample_defeats_and_retains_other_support(self):
        d = supported()
        d["records"].append(review("tail-defeat", "tail_designation_adequacy", ["receipt-tail_designation_adequacy"],
                                   verdict=known("contradicts"), decisive=known(True), counterexample_ids=["snapshot"]))
        values = self.analyze(d)
        self.assertEqual(gate(values, "tail_retention")["assessment"], "contradicted_under_scope")
        self.assertEqual(values["conclusion"], "defeated_under_scope")
        self.assertEqual(gate(values, "external_presence")["assessment"], "supported_under_scope")
        self.assertIn("review-tail_designation_adequacy", criterion(values, "tail_designation_adequacy")["support_ids"])

    def test_deselected_gate_is_still_output_and_blocks_whole_support(self):
        d = supported(); d["requests"][0]["conditions"] = ["structural_validity", "external_presence", "source_integrity", "corrective_capacity"]
        values = self.analyze(d); tail = gate(values, "tail_retention")
        self.assertEqual(values["conclusion"], "unestablished")
        self.assertEqual((tail["selection"], tail["execution"], tail["assessment"]), ("not_selected", "not_run", "not_assessed"))
        self.assertEqual([r["assessment"] for r in tail["values"]["criteria"]], ["not_assessed"] * 3)

    def test_selecting_no_gates_does_no_prerequisite_work(self):
        d = supported(); d["requests"][0]["conditions"] = []
        values = self.analyze(d)
        self.assertEqual(values["conclusion"], "not_assessed")
        self.assertEqual(values["prerequisites"], [])
        self.assertEqual(len(values["conditions"]), 5)

    def test_each_of_fourteen_reviews_is_required(self):
        base = supported()
        for target in [r for r in base["records"] if r["id"].startswith("review-")]:
            with self.subTest(criterion=target["criterion"]):
                d = deepcopy(base); d["records"].remove(record(d, target["id"]))
                values = self.analyze(d)
                self.assertEqual(values["conclusion"], "unestablished")
                self.assertEqual(criterion(values, target["criterion"])["assessment"], "unresolved")

    def test_independent_prerequisites_do_not_require_separate_requests(self):
        d = supported(); only = self.analyze(d)
        d["requests"].extend([
            {"id": "other-profile", "operation": "profile", "scope_id": "scope", "snapshot_id": "snapshot"},
            {"id": "other-external", "operation": "external", "scope_id": "scope", "cohort_id": "cohort"},
            {"id": "other-cases", "operation": "cases", "scope_id": "scope"}])
        self.assertEqual(self.analyze(d), only)
        report = analyze_bytes(wire(d), request_ids=("assess-main",))
        self.assertEqual(report["results"][0]["values"], only)

    def test_missing_snapshot_or_cohort_selection_is_not_inferred(self):
        for key, gate_name in (("snapshot_id", "tail_retention"), ("cohort_id", "external_presence")):
            d = supported(); del d["requests"][0][key]
            values = self.analyze(d)
            self.assertEqual(gate(values, gate_name)["assessment"], "unresolved")
            self.assertIn("missing_record", gate(values, gate_name)["reason_codes"])
            self.assertEqual(values["conclusion"], "unestablished")

    def test_absent_optional_scope_anchors_cannot_hide_claim_snapshot_mismatch(self):
        d = supported(); scope = record(d, "scope")
        del scope["frame_id"]; del scope["claim_id"]
        other = deepcopy(record(d, "frame")); other["id"] = "other-frame"; d["records"].append(other)
        record(d, "snapshot")["frame_id"] = "other-frame"
        for identity in ("assignment-a", "assignment-b"): record(d, identity)["frame_id"] = "other-frame"
        values = self.analyze(d)
        self.assertEqual(values["conclusion"], "unestablished")
        self.assertIn("scope_mismatch", values["claim_check"]["reason_codes"])
        self.assertEqual(gate(values, "tail_retention")["assessment"], "unresolved")

    def test_currentness_and_required_claim_fields_block_affirmative_conclusion(self):
        for target, field in (("claim", "statement"), ("claim", "intended_use"), ("claim", "horizon"),
                              ("claim", "requirements"), ("claim", "valid_until"), ("scope", "window")):
            with self.subTest(field=field):
                d = supported(); record(d, target)[field] = gap()
                self.assertEqual(self.analyze(d)["conclusion"], "unestablished")
        d = supported(); record(d, "claim")["valid_until"] = known(d["analysis_time"])
        values = self.analyze(d)
        self.assertEqual(values["currentness"], "expired_under_declared_date")
        self.assertEqual(values["conclusion"], "unestablished")
        self.assertTrue(all(g["assessment"] == "unresolved" for g in values["conditions"]))
        self.assertEqual(criterion(values, "tail_designation_adequacy")["assessment"], "supported_under_scope")

    def test_specific_independence_must_qualify_and_known_overlap_blocks_it(self):
        d = supported()
        d["records"].extend([
            {"id": "independence", "type": "independence", "scope_id": "scope", "members": ["item-a", "item-b"],
             "form": "pairwise", "dimension": "acquisition", "method": known("Inspect declared acquisition sources"),
             "unexamined_dimensions": ["model_ancestry"]},
            evidence("independence-receipt", subjects=["item-a", "item-b"]),
            review("independence-review", "independence", ["independence-receipt"], target="independence")])
        values = self.analyze(d)
        self.assertEqual(gate(values, "source_integrity")["assessment"], "unresolved")
        child = next(p["result"] for p in values["prerequisites"] if p["role"] == "independence:independence")
        self.assertEqual(child["values"]["witnesses"][0]["node_id"], "source")
        self.assertEqual(child["values"]["independence_assessments"][0]["review"]["assessment"], "unresolved")

    def test_structured_missing_required_feature_is_a_direct_defeat(self):
        d = supported(); record(d, "claim")["requirements"] = known(["single_turn", "recovery"])
        values = self.analyze(d)
        self.assertEqual(criterion(values, "frame_target_fidelity")["assessment"], "contradicted_under_scope")
        self.assertEqual(values["conclusion"], "defeated_under_scope")

    def test_direct_counterexample_with_disputed_frame_premise_stays_unresolved(self):
        d = supported(); record(d, "claim")["requirements"] = known(["single_turn", "recovery"])
        d["records"].append(evidence("frame-dispute", subjects=["frame"]))
        record(d, "frame")["contrary_ids"] = ["frame-dispute"]
        self.assertEqual(criterion(self.analyze(d), "frame_target_fidelity")["assessment"], "unresolved")
        record(d, "review-frame_target_fidelity")["resolves"] = ["frame-dispute"]
        self.assertEqual(criterion(self.analyze(d), "frame_target_fidelity")["assessment"], "contradicted_under_scope")

    def test_simulation_is_not_execution_validation(self):
        d = supported(); record(d, "receipt-validation_type_fit")["kind"] = known("simulation_record")
        values = self.analyze(d)
        self.assertEqual(criterion(values, "validation_type_fit")["assessment"], "unresolved")
        self.assertEqual(values["conclusion"], "unestablished")

    def test_human_consequence_requirement_needs_its_own_type(self):
        d = supported(); record(d, "claim")["requirements"] = known(["single_turn", "human_consequence"])
        record(d, "frame")["features"] = known(["single_turn", "human_consequence"])
        self.assertEqual(criterion(self.analyze(d), "validation_type_fit")["assessment"], "unresolved")
        d["records"].append(evidence("human", "human_consequence_record", ["claim"]))
        record(d, "review-validation_type_fit")["evidence_ids"].append("human")
        self.assertEqual(self.analyze(d)["conclusion"], "supported_under_scope")

    def test_partial_cohort_needs_explicit_known_member_gate_anchors(self):
        d = supported(); record(d, "cohort")["membership"] = known("partial")
        values = self.analyze(d)
        self.assertEqual(gate(values, "external_presence")["assessment"], "unresolved")
        for name in ("outside_process_contact", "claim_relevance", "recorded_use"):
            record(d, "receipt-" + name)["subject_ids"].remove("cohort")
        values = self.analyze(d)
        self.assertEqual(gate(values, "external_presence")["assessment"], "supported_under_scope")
        external = next(p["result"] for p in values["prerequisites"] if p["role"] == "external")
        self.assertEqual(external["values"]["full_member_count"]["state"], "unavailable")

    def test_carryover_and_missing_separate_qualification_block_presence(self):
        for key, value in (("carryover_ids", ["z"]), ("qualifications", []), ("externality_reviews", [])):
            d = supported(); record(d, "cohort")[key] = value
            self.assertEqual(gate(self.analyze(d), "external_presence")["assessment"], "unresolved")

    def test_gate_review_must_anchor_actual_use_target_and_event(self):
        for target, remove in (("receipt-claim_relevance", "process"), ("receipt-recorded_use", "z-used"),
                               ("receipt-outside_process_contact", "z")):
            d = supported(); record(d, target)["subject_ids"].remove(remove)
            self.assertEqual(gate(self.analyze(d), "external_presence")["assessment"], "unresolved")

    def test_source_origin_inventory_roles_and_limits_are_required(self):
        for target, field in (("receipt-provenance_transformations", "origin_ids"),
                              ("receipt-provenance_transformations", "transformation_ids"),
                              ("receipt-provenance_transformations", "uncertainty"),
                              ("receipt-evaluator_relationships", "uncertainty"), ("role-generation", "role"), ("scope", "dimension")):
            d = supported(); del record(d, target)[field]
            self.assertEqual(gate(self.analyze(d), "source_integrity")["assessment"], "unresolved")

    def test_declared_frontier_can_be_reviewed_without_hidden_ancestry_completeness(self):
        d = supported(); d["records"].append({"id": "frontier", "type": "frontier", "scope_id": "scope", "node_id": "source", "view": "acquisition", "reason": gap()})
        self.assertEqual(gate(self.analyze(d), "source_integrity")["assessment"], "unresolved")
        for criterion_name in ("provenance_transformations", "evaluator_relationships"):
            record(d, "receipt-" + criterion_name)["subject_ids"].append("frontier")
        self.assertEqual(gate(self.analyze(d), "source_integrity")["assessment"], "supported_under_scope")

    def test_tail_coverage_and_result_receipt_are_both_required(self):
        for mutation in ("membership", "assignment", "receipt", "scope"):
            d = supported()
            if mutation == "membership": record(d, "snapshot")["membership"] = known("partial")
            elif mutation == "assignment": record(d, "assignment-b")["decision"] = known("provisional")
            elif mutation == "receipt": record(d, "snapshot")["tail_results"] = known([])
            else: record(d, "tail-receipt")["access"] = known("referenced_only")
            self.assertEqual(gate(self.analyze(d), "tail_retention")["assessment"], "unresolved")

    def test_absent_tail_in_complete_population_is_a_mechanical_defeat(self):
        d = supported(); record(d, "assignment-b")["class_id"] = known("usual")
        values = self.analyze(d)
        self.assertEqual(values["conclusion"], "defeated_under_scope")
        self.assertEqual(criterion(values, "tail_representation")["assessment"], "contradicted_under_scope")

    def test_empty_tail_list_is_only_a_reviewed_bounded_empty_obligation(self):
        d = supported(); record(d, "frame")["tail_designations"] = known([])
        values = self.analyze(d)
        self.assertEqual(gate(values, "tail_retention")["assessment"], "supported_under_scope")
        d["records"].remove(record(d, "review-tail_designation_adequacy"))
        self.assertEqual(gate(self.analyze(d), "tail_retention")["assessment"], "unresolved")

    def test_empty_population_cannot_support_tail_retention(self):
        d = supported(); record(d, "snapshot").update(members=[], assignments=[], tail_results=known([]))
        values = self.analyze(d)
        self.assertEqual(values["conclusion"], "unestablished")
        self.assertEqual(gate(values, "tail_retention")["assessment"], "unresolved")
        self.assertIn("empty_population", gate(values, "tail_retention")["reason_codes"])

    def test_sustained_single_case_no_history_is_unresolved(self):
        d = supported(); record(d, "claim")["capacity_extent"] = known("sustained")
        values = self.analyze(d)
        self.assertEqual(criterion(values, "capacity_extent")["assessment"], "unresolved")
        self.assertEqual(criterion(values, "route_operability")["assessment"], "supported_under_scope")
        self.assertEqual(values["conclusion"], "unestablished")

    def test_sustained_requires_distinct_dated_actions_outcomes_and_history(self):
        d = supported(); record(d, "claim")["capacity_extent"] = known("sustained")
        case = record(d, "case"); action = deepcopy(case["actions"][0]); action.update(id="later-action", occurred_at=known("2026-10-04T01:00:00Z"))
        case["actions"].append(action)
        outcome = deepcopy(case["outcomes"][0]); outcome.update(id="later-outcome", action_id="later-action", assessed_at=known("2026-10-05T00:00:00Z"), review_id=known("later-review"))
        case["outcomes"].append(outcome)
        d["records"].extend([review("later-review", "correction_outcome", ["outcome-receipt"], target="case", target_event_id="later-outcome"),
                             evidence("history", "process_record", ["claim", "case"], occurred_at=known("2026-10-05T00:00:00Z"))])
        record(d, "review-capacity_extent")["evidence_ids"].append("history")
        self.assertEqual(self.analyze(d)["conclusion"], "supported_under_scope")
        record(d, "history")["occurred_at"] = known("2026-10-02T00:00:00Z")
        self.assertEqual(criterion(self.analyze(d), "capacity_extent")["assessment"], "unresolved")

    def test_unknown_authority_blocks_capacity_but_prerequisite_keeps_outcome(self):
        d = supported(); record(d, "case")["authority"] = gap()
        values = self.analyze(d)
        self.assertEqual(gate(values, "corrective_capacity")["assessment"], "unresolved")
        cases = next(p["result"]["values"] for p in values["prerequisites"] if p["role"] == "cases")
        self.assertEqual(cases["corrections"][0]["outcomes"][0]["review"]["assessment"], "supported_under_scope")

    def test_known_anomaly_cannot_be_excluded_to_assert_empty_inventory(self):
        d = revision_demo(); d["requests"] = supported()["requests"]
        d["requests"][0]["anomaly_ids"] = []
        values = self.analyze(d)
        self.assertEqual(criterion(values, "anomaly_accountability")["assessment"], "unresolved")
        self.assertIn("unselected", criterion(values, "anomaly_accountability")["reason_codes"])

    def test_narrow_assess_uses_existing_rule_and_has_no_five_gate_summary(self):
        for name, expected in (("supported-narrow-regression", "supported_under_scope"), ("scope-mismatch", "defeated_under_scope"),
                               ("incomplete-regression", "unestablished")):
            d = fixture(name); d["requests"][0]["operation"] = "assess"
            values = self.analyze(d)
            self.assertEqual(values["conclusion"], expected)
            self.assertEqual(values["conditions"], [])
            self.assertEqual(values["open_evaluation"], "not_applicable")

    def test_unresolved_contrary_and_exact_resolution_do_not_delete_originals(self):
        d = supported()
        d["records"].append(review("opposing", "frame_target_fidelity", ["receipt-frame_target_fidelity"], verdict=known("contradicts")))
        self.assertEqual(self.analyze(d)["conclusion"], "unestablished")
        d["records"].append(review("resolution", "frame_target_fidelity", ["receipt-frame_target_fidelity"], resolves=["opposing"]))
        values = self.analyze(d)
        self.assertEqual(values["conclusion"], "supported_under_scope")
        self.assertIn("opposing", criterion(values, "frame_target_fidelity")["contrary_ids"])


if __name__ == "__main__":
    unittest.main()
