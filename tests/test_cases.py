"""Objective-specific case and structural-revision acceptance counterexamples."""

from copy import deepcopy
import unittest

from evaluation_closure_toolkit import analyze_bytes, render_markdown
from evaluation_closure_toolkit.evidence import evaluate_reviews
from assessment_helpers import supported, cases_demo, revision_demo, evidence, review
from provenance_helpers import wire, record, known, gap, entity


class CaseTests(unittest.TestCase):
    def analyze(self, dossier=None):
        dossier = dossier or supported()
        dossier["requests"] = [{"id": "cases-main", "operation": "cases", "scope_id": "scope",
                                **{k: dossier["requests"][0][k] for k in ("case_ids", "anomaly_ids", "revision_ids") if k in dossier["requests"][0]}}]
        report = analyze_bytes(wire(dossier))
        self.assertEqual(report["admission"], "valid", report.get("diagnostics"))
        self.assertEqual(report["execution"], "completed")
        render_markdown(report)
        return report["results"][0]["values"]

    def case(self, dossier):
        return self.analyze(dossier)["corrections"][0]

    def test_ticket_and_newer_version_are_not_action_or_outcome(self):
        value = self.analyze(cases_demo())
        ticket = value["corrections"][1]
        self.assertEqual(ticket["handling"][0]["state"], "accepted")
        self.assertEqual(ticket["handling"][0]["check"]["assessment"], "supported_under_scope")
        self.assertEqual((ticket["attempts"], ticket["actions"], ticket["outcomes"]), ([], [], []))
        self.assertEqual(ticket["capacity"]["assessment"], "unresolved")
        self.assertEqual(value["event_counts"]["handling"], {"state": "available", "value": 2})

    def test_unknown_authority_preserves_effective_restriction(self):
        row = self.case(cases_demo())
        self.assertEqual(row["outcomes"][0]["review"]["assessment"], "supported_under_scope")
        self.assertEqual(row["outcomes"][0]["objective"], "restrict")
        self.assertEqual(row["authority"]["assessment"], "unresolved")
        self.assertEqual(row["actions"][0]["authorization"]["assessment"], "unresolved")
        self.assertEqual(row["capacity"]["assessment"], "unresolved")
        self.assertEqual(row["context"], "drill")

    def test_drill_authorized_attempt_action_and_outcome_are_separate(self):
        row = self.case(supported())
        self.assertEqual(row["capacity"]["assessment"], "supported_under_scope")
        self.assertEqual(row["capacity_extent"], "tested_route")
        self.assertEqual(row["context"], "drill")
        self.assertEqual(row["actions"][0]["authorization"]["assessment"], "supported_under_scope")

    def test_repeat_actions_do_not_multiply_case_target_pairs(self):
        d = supported()
        action = deepcopy(record(d, "case")["actions"][0]); action["id"] = "second-action"
        record(d, "case")["actions"].append(action)
        values = self.analyze(d)
        self.assertEqual(values["event_counts"]["actions"], {"state": "available", "value": 2})
        self.assertEqual(values["pair_counts"]["acted"], {"state": "available", "value": 1})
        self.assertEqual(values["pair_counts"]["authorized"], {"state": "available", "value": 1})
        self.assertEqual(values["pair_counts"]["effective"], {"state": "available", "value": 1})

    def test_authority_actor_target_and_half_open_action_time(self):
        for field, value in (("actor_id", "second-actor"), ("target_id", "model"),
                             ("end", "2026-10-03T01:00:00Z"), ("start", "2026-10-03T02:00:00Z")):
            with self.subTest(field=field):
                d = supported(); d["records"].append(entity("second-actor", "actor"))
                record(d, "case")["authority"]["value"][field] = value
                row = self.case(d)
                self.assertEqual(row["actions"][0]["authorization"]["assessment"], "unresolved")
                self.assertEqual(row["outcomes"][0]["review"]["assessment"], "supported_under_scope")
        d = supported(); record(d, "case")["authority"]["value"]["start"] = "2026-10-03T01:00:00Z"
        self.assertEqual(self.case(d)["actions"][0]["authorization"]["assessment"], "supported_under_scope")

    def test_missing_or_reversed_attempt_action_outcome_times(self):
        for field, key, value in (("attempts", "occurred_at", gap()), ("actions", "occurred_at", gap()),
                                  ("outcomes", "assessed_at", gap()),
                                  ("attempts", "occurred_at", known("2026-10-03T02:00:00Z")),
                                  ("outcomes", "assessed_at", known("2026-10-02T00:00:00Z"))):
            with self.subTest(field=field, value=value):
                d = supported(); record(d, "case")[field][0][key] = value
                self.assertEqual(self.case(d)["outcomes"][0]["review"]["assessment"], "unresolved")

    def test_route_action_target_mismatch_does_not_erase_documented_action(self):
        d = supported(); record(d, "case")["route"]["value"]["target_id"] = "model"
        row = self.case(d)
        self.assertEqual(row["actions"][0]["check"]["assessment"], "supported_under_scope")
        self.assertEqual(row["actions"][0]["authorization"]["assessment"], "unresolved")

    def test_ineffective_outcome_can_coexist_with_operable_route(self):
        d = supported(); record(d, "case")["outcomes"][0]["result"] = known("ineffective")
        values = self.analyze(d); row = values["corrections"][0]
        self.assertEqual(row["outcomes"][0]["result"], "ineffective")
        self.assertEqual(row["outcomes"][0]["review"]["assessment"], "supported_under_scope")
        self.assertEqual(row["capacity"]["assessment"], "supported_under_scope")
        self.assertEqual(values["pair_counts"]["effective"]["value"], 0)

    def test_objective_mismatch_never_upgrades_restriction_to_repair(self):
        d = supported(); record(d, "case")["objective"] = known("repair")
        outcome = self.case(d)["outcomes"][0]["review"]
        self.assertEqual(outcome["assessment"], "unresolved")
        self.assertIn("scope_mismatch", outcome["reason_codes"])

    def test_repair_requires_supplied_baseline_but_restriction_does_not(self):
        d = supported(); case = record(d, "case")
        case["objective"] = known("repair"); case["actions"][0]["kind"] = known("repair")
        self.assertEqual(self.case(d)["outcomes"][0]["review"]["assessment"], "unresolved")
        d["records"].append(evidence("baseline", "execution_record", ["case"]))
        case["outcomes"][0]["baseline"] = known("baseline")
        self.assertEqual(self.case(d)["outcomes"][0]["review"]["assessment"], "supported_under_scope")
        record(d, "baseline")["access"] = known("referenced_only")
        self.assertIn("access_gap", self.case(d)["outcomes"][0]["review"]["reason_codes"])

    def test_no_outcome_upgrade_from_pointer_or_wrong_typed_receipt(self):
        for change in ({"access": known("referenced_only")}, {"kind": known("simulation_record")},
                       {"subject_ids": ["model"]}, {"content": gap("withheld")}, {"producer_id": gap()}):
            d = supported(); record(d, "outcome-receipt").update(change)
            self.assertEqual(self.case(d)["outcomes"][0]["review"]["assessment"], "unresolved")

    def test_outcome_binding_is_required(self):
        d = supported()
        with self.assertRaisesRegex(ValueError, "OUTCOME_BINDING_REQUIRED"):
            evaluate_reviews({r["id"]: r for r in d["records"]}, "case", "correction_outcome", "scope")

    def test_an_unrelated_outcome_review_cannot_defeat_the_selected_outcome(self):
        d = supported(); case = record(d, "case")
        second = deepcopy(case["outcomes"][0]); second.update(id="second-outcome", review_id=known("second-review"))
        case["outcomes"].append(second)
        d["records"].append(review("second-review", "correction_outcome", ["outcome-receipt"], target="case",
                                   target_event_id="second-outcome", verdict=known("contradicts"), decisive=known(True), counterexample_ids=["outcome-receipt"]))
        case["contrary_ids"] = ["second-review"]
        outcomes = self.case(d)["outcomes"]
        self.assertEqual(outcomes[0]["review"]["assessment"], "supported_under_scope")
        self.assertEqual(outcomes[1]["review"]["assessment"], "contradicted_under_scope")

    def test_conflict_and_exact_resolution_retain_history(self):
        d = supported()
        d["records"].append(review("opposing", "correction_outcome", ["outcome-receipt"], target="case",
                                   target_event_id="outcome", verdict=known("contradicts")))
        self.assertEqual(self.case(d)["outcomes"][0]["review"]["assessment"], "unresolved")
        d["records"].append(review("resolved", "correction_outcome", ["outcome-receipt"], target="case",
                                   target_event_id="outcome", resolves=["opposing"]))
        result = self.case(d)["outcomes"][0]["review"]
        self.assertEqual(result["assessment"], "supported_under_scope")
        self.assertEqual(result["values"]["resolved_ids"], ["opposing"])
        self.assertIn("opposing", result["contrary_ids"])

    def test_explicit_outcome_contrary_is_not_hidden_by_favorable_review(self):
        d = supported(); d["records"].append(evidence("contrary", "observation_record", ["case"]))
        record(d, "case")["outcomes"][0]["contrary_ids"] = ["contrary"]
        outcome = self.case(d)["outcomes"][0]["review"]
        self.assertEqual(outcome["assessment"], "unresolved")
        self.assertIn("contrary", outcome["contrary_ids"])

    def test_empty_selectors_mean_none_not_default_all(self):
        d = revision_demo(); d["requests"][0].update(anomaly_ids=[], revision_ids=[], case_ids=[])
        values = self.analyze(d)
        self.assertEqual((values["anomalies"], values["revisions"], values["corrections"]), ([], [], []))

    def test_relabel_and_investigation_do_not_establish_recut_or_fidelity(self):
        values = self.analyze(revision_demo())
        recut, rename = values["revisions"]
        self.assertEqual(recut["cut_state"], "recut_documented")
        self.assertEqual(recut["fidelity"]["assessment"], "supported_under_scope")
        self.assertEqual(rename["documented"]["assessment"], "supported_under_scope")
        self.assertEqual(rename["incorporated"]["assessment"], "supported_under_scope")
        self.assertEqual(rename["cut_state"], "relabel_only")
        self.assertEqual(rename["fidelity"]["assessment"], "unresolved")
        self.assertEqual(values["anomalies"][1]["disposition"], "investigated_no_change")

    def test_declared_recut_with_identical_class_meanings_remains_cosmetic(self):
        d = revision_demo(); record(d, "revision-rename")["kind"] = known("recut")
        row = self.analyze(d)["revisions"][1]
        self.assertEqual(row["cut_state"], "relabel_only")
        self.assertEqual(row["fidelity"]["assessment"], "unresolved")

    def test_missing_original_incorporation_or_assignment_blocks_dependent_improvement(self):
        for mutation in ("original", "incorporation", "assignment", "map"):
            with self.subTest(mutation=mutation):
                d = revision_demo()
                if mutation == "original":
                    record(d, "anomaly-recut-receipt")["access"] = known("referenced_only")
                elif mutation == "incorporation":
                    record(d, "revision-recut")["incorporation_evidence_ids"] = []
                elif mutation == "assignment":
                    record(d, "assignment-recut")["decision"] = known("provisional")
                else:
                    record(d, "revision-recut")["class_map"] = []
                self.assertEqual(self.analyze(d)["revisions"][0]["fidelity"]["assessment"], "unresolved")

    def test_recut_review_cannot_replace_incorporation_with_favorable_text(self):
        d = revision_demo(); record(d, "revision-recut")["new_assignment_ids"] = []
        row = self.analyze(d)["revisions"][0]
        self.assertEqual(row["documented"]["assessment"], "supported_under_scope")
        self.assertEqual(row["incorporated"]["assessment"], "unresolved")
        self.assertEqual(row["fidelity"]["assessment"], "unresolved")

    def test_two_affected_assignments_for_one_item_do_not_select_a_unique_cut(self):
        d = revision_demo(); assignment = deepcopy(record(d, "assignment-recut"))
        assignment.update(id="other-assignment", class_id=known("usual"))
        d["records"].append(assignment)
        record(d, "revision-recut")["new_assignment_ids"].append("other-assignment")
        row = self.analyze(d)["revisions"][0]
        self.assertEqual(row["incorporated"]["assessment"], "unresolved")
        self.assertEqual(row["fidelity"]["assessment"], "unresolved")

    def test_other_case_counterexample_cannot_decisively_defeat_this_outcome(self):
        d = cases_demo()
        d["records"].append(review("bad-counterexample", "correction_outcome", ["outcome-receipt"], target="case",
                                   target_event_id="outcome", verdict=known("contradicts"), decisive=known(True), counterexample_ids=["ticket-only"]))
        self.assertEqual(self.case(d)["outcomes"][0]["review"]["assessment"], "unresolved")


if __name__ == "__main__":
    unittest.main()
