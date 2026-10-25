"""Literal comparison counterexamples, independent of the implementation."""

import copy
import json
from pathlib import Path
import unittest

from evaluation_closure_toolkit.admission import admit
from evaluation_closure_toolkit.budget import RequestBudget, WorkLimit
from evaluation_closure_toolkit.comparison import compare_request
from evaluation_closure_toolkit.structural import build_profile


DATA = Path(__file__).resolve().parents[1] / "src" / "evaluation_closure_toolkit" / "data"


def known(value):
    return {"state": "known", "value": value}


def fraction(numerator, denominator):
    return {"state": "available", "value": {"numerator": str(numerator), "denominator": str(denominator)}}


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.dossier = json.loads((DATA / "matched-cohort.json").read_text())
        self.records = {r["id"]: r for r in self.dossier["records"]}
        self.requests = {r["id"]: r for r in self.dossier["requests"]}

    def compare(self, request_id="compare-catalog", **kwargs):
        admit(json.dumps(self.dossier).encode())
        return compare_request(self.dossier, self.requests[request_id], **kwargs)[0]

    def add_review(self, *, criterion="matching_basis", target="scope-main", request="compare-matched"):
        evidence = {
            "id": "comparison-receipt", "type": "evidence", "scope_id": "scope-main",
            "kind": known("document"), "producer_id": known("actor-fixture"),
            "access": known("supplied"), "content": known("PRIVATE_COMPARISON_RECEIPT"),
        }
        review = {
            "id": "comparison-review", "type": "review", "target_id": target,
            "scope_id": "scope-main", "criterion": criterion,
            "assessor_id": known("actor-fixture"), "reviewed_at": known("2026-10-05T12:00:00Z"),
            "method": known("Exact roster and compatibility-field examination"),
            "rationale": known("Supplied scope-limited premise"), "verdict": known("supports"),
            "evidence_ids": [evidence["id"]],
        }
        if criterion == "matching_basis":
            review["request_id"] = request
        self.dossier["records"].extend([evidence, review])
        self.records.update({evidence["id"]: evidence, review["id"]: review})
        return review

    def relabel(self):
        old = self.records["frame-main"]
        frame = copy.deepcopy(old)
        frame["id"] = "frame-renamed"
        mapping = {row["id"]: "renamed-" + row["id"] for row in frame["classes"]["value"]}
        for row in frame["classes"]["value"]:
            row["id"] = mapping[row["id"]]
        for row in frame["tail_designations"]["value"]:
            row["class_id"] = mapping[row["class_id"]]
        self.dossier["records"].append(frame)
        self.records[frame["id"]] = frame
        self.records["scope-main"].pop("frame_id")
        snapshot = self.records["snapshot-b"]
        snapshot["frame_id"] = frame["id"]
        for selection in snapshot["assignments"]:
            assignment = self.records[selection["assignment_id"]]
            assignment["frame_id"] = frame["id"]
            assignment["class_id"] = known(mapping[assignment["class_id"]["value"]])
        for selection in snapshot["validities"]:
            self.records[selection["validity_id"]]["frame_id"] = frame["id"]
        revision = {
            "id": "revision-renamed", "type": "revision", "scope_id": "scope-main",
            "from_frame": "frame-main", "to_frame": frame["id"], "kind": known("relabel"),
            "class_map": [{"from_class": source, "to_class": target} for source, target in mapping.items()],
        }
        self.dossier["records"].append(revision)
        self.records[revision["id"]] = revision
        for request in self.requests.values():
            if request["operation"] == "compare":
                request["revision_id"] = revision["id"]
        return revision

    def test_catalog_and_matched_deltas_are_distinct_literal_oracles(self):
        catalog = self.compare()["values"]
        matched_result = self.compare("compare-matched")
        matched = matched_result["values"]
        self.assertEqual(catalog["delta_SCI"], fraction(1, 24))
        self.assertEqual(catalog["delta_D"], fraction(-1, 24))
        self.assertEqual(matched["delta_SCI"], fraction(1, 12))
        self.assertEqual(matched["after"]["SCI"], fraction(31, 72))
        self.assertEqual(matched["pair_count"], {"state": "available", "value": 24})
        self.assertEqual(matched["after"]["N"], {"state": "available", "value": 24})
        self.assertEqual(matched["catalog_profiles"]["after"][0]["N"], {"state": "available", "value": 48})
        self.assertEqual(matched_result["assessment"], "not_assessed")
        self.assertEqual(matched["tail_changes"][0]["scope"], "matched_cohort")
        self.assertEqual(catalog["tail_changes"][0]["scope"], "selected_catalog")
        self.assertEqual(matched["tail_changes"][0]["change"], "loss")

    def test_incomplete_assignment_allows_conditional_delta_but_blocks_tail_loss(self):
        self.records["assignment-b-024"]["decision"] = known("unclassified")
        value = self.compare()["values"]
        self.assertEqual(value["after"]["SCI"], fraction(881, 2209))
        self.assertEqual(value["after"]["assignment_coverage"], fraction(47, 48))
        self.assertEqual(value["delta_SCI"], fraction(8207, 159048))
        self.assertEqual(value["tail_changes"][0]["after_status"], "zero_admitted_sightings")
        self.assertEqual(value["tail_changes"][0]["change"], "no_loss_established")

    def test_incomplete_baseline_blocks_loss_even_with_positive_tail(self):
        self.records["assignment-a-001"].pop("basis")
        value = self.compare()["values"]
        self.assertEqual(value["tail_changes"][0]["before_status"], "present")
        self.assertEqual(value["tail_changes"][0]["after_status"], "absent_in_complete_population")
        self.assertEqual(value["tail_changes"][0]["change"], "no_loss_established")

    def test_unknown_membership_keeps_inventory_without_primary_delta_or_loss(self):
        self.records["snapshot-b"]["membership"] = known("unknown")
        value = self.compare()["values"]
        self.assertEqual(value["delta_SCI"], {"state": "unavailable", "reason": "unknown_membership"})
        self.assertEqual(value["after"]["SCI"]["state"], "unavailable")
        self.assertEqual(value["after"]["known_subset"]["SCI"], fraction(7, 18))
        self.assertEqual(value["tail_changes"][0]["after_status"], "zero_admitted_sightings")
        self.assertEqual(value["tail_changes"][0]["change"], "no_loss_established")

    def test_missing_pair_endpoint_is_preserved_and_never_deleted(self):
        snapshot = self.records["snapshot-b"]
        snapshot["members"].remove("item-b-024")
        for field in ("assignments", "validities"):
            snapshot[field] = [row for row in snapshot[field] if row["item_id"] != "item-b-024"]
        value = self.compare("compare-matched")["values"]
        self.assertEqual(value["pair_count"], {"state": "available", "value": 24})
        self.assertEqual(value["after"], {})
        self.assertEqual(value["pair_gaps"][0]["after_item_id"], "item-b-024")
        self.assertEqual(value["delta_SCI"]["state"], "unavailable")
        self.assertEqual(value["catalog_profiles"]["after"][0]["K"], {"state": "available", "value": 47})

    def test_nonadmitted_pair_blocks_entire_contrast(self):
        self.records["assignment-b-024"]["decision"] = known("provisional")
        value = self.compare("compare-matched")["values"]
        self.assertEqual(value["pair_count"], {"state": "available", "value": 24})
        self.assertEqual(value["delta_SCI"]["state"], "unavailable")
        self.assertIn("unresolved_assignment", value["pair_gaps"][0]["reason_codes"])

    def test_invalid_fixed_pair_cannot_be_removed_for_confirmed_valid_view(self):
        self.requests["compare-matched"]["population"] = "confirmed_valid"
        self.records["validity-b-024"]["verdict"] = known("invalid")
        value = self.compare("compare-matched")["values"]
        self.assertEqual(value["pair_count"], {"state": "available", "value": 24})
        self.assertEqual(value["delta_SCI"]["state"], "unavailable")
        self.assertEqual(len(value["catalog_profiles"]["after"]), 2)
        self.assertEqual(value["catalog_profiles"]["after"][0]["N"]["value"], 48)
        self.assertEqual(value["catalog_profiles"]["after"][1]["V"]["value"], 47)
        self.assertIn("prerequisite_unavailable", value["pair_gaps"][0]["reason_codes"])

    def test_incomplete_pair_roster_never_invents_fixed_denominator(self):
        self.requests["compare-matched"]["pair_membership"] = known("partial")
        value = self.compare("compare-matched")["values"]
        self.assertEqual(value["pair_count"], {"state": "unavailable", "reason": "incomplete_pairs"})
        self.assertEqual(value["delta_SCI"]["state"], "unavailable")

    def test_pair_fact_gaps_remain_distinguishable(self):
        request = self.requests["compare-matched"]
        request.pop("pair_membership")
        self.assertIn("missing_field", self.compare("compare-matched")["reason_codes"])
        for state, reason in (("unknown", "unknown_value"), ("withheld", "withheld"),
                              ("disputed", "disputed"), ("absent", "explicit_absence")):
            with self.subTest(state=state):
                request["pair_membership"] = {"state": state, "reason": "Protected premise", "evidence_ids": []}
                result = self.compare("compare-matched")
                self.assertIn(reason, result["reason_codes"])
                self.assertIn("incomplete_pairs", result["reason_codes"])

    def test_complete_empty_pairs_have_zero_support_and_undefined_delta(self):
        self.requests["compare-matched"]["pairs"] = []
        value = self.compare("compare-matched")["values"]
        self.assertEqual(value["pair_count"], {"state": "available", "value": 0})
        self.assertEqual(value["before"]["N"], {"state": "available", "value": 0})
        self.assertEqual(value["after"]["observed_support"], {"state": "available", "value": 0})
        self.assertEqual(value["delta_SCI"]["state"], "undefined")
        self.assertEqual(value["tail_changes"][0]["after_status"], "absent_in_empty_population")
        self.assertNotEqual(value["tail_changes"][0]["change"], "loss")

    def test_complete_empty_target_can_show_scoped_loss_without_numeric_delta(self):
        for field in ("members", "assignments", "validities"):
            self.records["snapshot-b"][field] = []
        result = self.compare()
        value = result["values"]
        self.assertEqual(value["delta_SCI"]["state"], "undefined")
        self.assertEqual(value["tail_changes"][0]["change"], "loss")
        self.assertEqual(value["tail_changes"][0]["after_status"], "absent_in_empty_population")
        self.assertIn("absent_in_empty_population", value["tail_changes"][0]["reason_codes"])
        self.assertEqual(result["assessment"], "not_assessed")

    def test_matching_basis_binds_exact_request(self):
        self.records["item-b-001"]["logical_id"] = "changed-identity"
        review = self.add_review(request="compare-catalog")
        value = self.compare("compare-matched")["values"]
        self.assertEqual(value["delta_SCI"]["state"], "unavailable")
        self.assertEqual(value["compatibility"]["matching_basis"]["values"]["reviews"], [])
        review["request_id"] = "compare-matched"
        result = self.compare("compare-matched")
        self.assertEqual(result["values"]["delta_SCI"], fraction(1, 12))
        self.assertIn("comparison-review", result["support_ids"])
        self.assertNotIn("PRIVATE_COMPARISON_RECEIPT", json.dumps(result))

    def test_bijection_requires_qualified_review_including_zero_class(self):
        revision = self.relabel()
        self.assertEqual(self.compare()["values"]["delta_SCI"]["state"], "unavailable")
        self.add_review(criterion="frame_equivalence", target=revision["id"])
        self.assertEqual(self.compare()["values"]["delta_SCI"], fraction(1, 24))
        revision["class_map"] = [row for row in revision["class_map"] if row["from_class"] != "class-four"]
        value = self.compare()["values"]
        self.assertEqual(value["delta_SCI"]["state"], "unavailable")
        self.assertIn("incompatible_frame", value["compatibility"]["reason_codes"])

    def test_review_can_support_semantic_relabel_but_cannot_change_exact_policy(self):
        revision = self.relabel()
        self.add_review(criterion="frame_equivalence", target=revision["id"])
        self.records["frame-renamed"]["task"] = known("Different wording examined by the exact revision review")
        self.assertEqual(self.compare()["values"]["delta_SCI"], fraction(1, 24))
        self.records["frame-renamed"]["admission_policy"] = known("A differently worded admission policy")
        value = self.compare()["values"]
        self.assertEqual(value["delta_SCI"]["state"], "unavailable")
        self.assertIn("incompatible_policy", value["compatibility"]["reason_codes"])

    def test_access_gap_or_revision_contrary_prevents_relabel_promotion(self):
        revision = self.relabel()
        self.add_review(criterion="frame_equivalence", target=revision["id"])
        self.records["comparison-receipt"]["access"] = known("referenced_only")
        self.assertEqual(self.compare()["values"]["delta_SCI"]["state"], "unavailable")
        self.records["comparison-receipt"]["access"] = known("supplied")
        revision["contrary_ids"] = ["comparison-receipt"]
        value = self.compare()["values"]
        self.assertEqual(value["delta_SCI"]["state"], "unavailable")
        self.assertIn("disputed", value["compatibility"]["reason_codes"])

    def test_recuts_preserve_profiles_and_zero_new_observations_without_direct_gain(self):
        dossier = json.loads((DATA / "recut-comparison.json").read_text())
        request = next(r for r in dossier["requests"] if r["operation"] == "compare")
        value = compare_request(dossier, request)[0]["values"]
        self.assertEqual(value["new_observations"], {"state": "available", "value": 0})
        self.assertEqual(value["after"]["SCI"], fraction(2, 9))
        self.assertEqual(value["delta_SCI"], {"state": "unavailable", "reason": "incompatible_frame"})
        self.assertEqual(value["tail_changes"], [])

    def test_snapshot_or_frame_contrary_blocks_compatibility_and_tail_loss(self):
        for identity in ("snapshot-b", "frame-main"):
            with self.subTest(identity=identity):
                self.records[identity]["contrary_ids"] = ["tail-failure-receipt"]
                result = self.compare()
                self.assertEqual(result["values"]["delta_SCI"]["state"], "unavailable")
                self.assertEqual(result["values"]["compatibility"]["state"], "unavailable")
                self.assertIn("disputed", result["reason_codes"])
                self.assertIn("tail-failure-receipt", result["contrary_ids"])
                self.assertEqual(result["values"]["tail_changes"], [])
                self.assertEqual(result["values"]["after"]["SCI"], fraction(7, 18))
                del self.records[identity]["contrary_ids"]

    def test_identical_item_identity_retains_exact_matching_contradiction(self):
        review = self.add_review()
        review["verdict"] = known("contradicts")
        result = self.compare("compare-matched")
        self.assertEqual(result["values"]["delta_SCI"]["state"], "unavailable")
        self.assertIn("comparison-review", result["contrary_ids"])
        self.assertEqual(len(result["values"]["pair_gaps"]), 24)
        review["verdict"] = known("supports")
        review.pop("method")
        # Incomplete supporting prose cannot erase the independent identity premise.
        self.assertEqual(self.compare("compare-matched")["values"]["delta_SCI"], fraction(1, 12))

    def test_work_limit_retains_completed_catalog_without_comparison_claim(self):
        budget = RequestBudget()
        build_profile(self.records, "snapshot-a", "scope-main", budget=budget)
        stopped = RequestBudget(limit=budget.used)
        with self.assertRaises(WorkLimit):
            self.compare(budget=stopped)
        partial = stopped.partial_result
        self.assertEqual(partial["execution"], "partial")
        self.assertEqual(partial["values"]["catalog_profiles"]["before"][0]["SCI"], fraction(25, 72))
        self.assertEqual(partial["values"]["delta_SCI"]["state"], "unavailable")
        self.assertEqual(partial["assessment"], "not_assessed")

    def test_dossier_record_order_does_not_change_comparison(self):
        expected = self.compare("compare-matched")
        self.dossier["records"].reverse()
        self.requests["compare-matched"]["pairs"].reverse()
        self.assertEqual(self.compare("compare-matched"), expected)


if __name__ == "__main__":
    unittest.main()
