"""Independent arithmetic and evidence counterexamples for structural views."""

import copy
import json
import unittest

from evaluation_closure_toolkit.admission import admit
from evaluation_closure_toolkit.budget import RequestBudget, WorkLimit
from evaluation_closure_toolkit.structural import build_profile, profile_request


def fact(value):
    return {"state": "known", "value": value}


def gap(state="unknown"):
    return {"state": state, "reason": "Private explanatory material.", "evidence_ids": []}


def count(value):
    return {"state": "available", "value": value}


def fraction(numerator, denominator):
    return {"state": "available", "value": {"numerator": str(numerator), "denominator": str(denominator)}}


def fixture(class_sizes=(12, 6, 4, 2)):
    """Input construction only; no implementation-derived expected numbers."""
    records = [
        {"id": "actor", "type": "entity", "kind": "actor", "logical_id": "actor", "version": "v1"},
        {"id": "process", "type": "entity", "kind": "process", "logical_id": "process", "version": "v1"},
        {"id": "scope", "type": "scope", "process_id": "process", "frame_id": "frame", "snapshot_ids": ["snapshot"]},
        {"id": "frame", "type": "frame", "classes": fact([
            {"id": "class-" + str(i + 1), "definition": "Private class definition."}
            for i in range(len(class_sizes))
        ]), "validity_rubric": fact("fixed-rubric"), "tail_designations": fact([
            {"class_id": "class-" + str(len(class_sizes)), "rationale": "Supplied designation.",
             "severity": "Severe.", "rarity_basis": "Declared rare."}
        ])},
    ]
    snapshot = {"id": "snapshot", "type": "snapshot", "frame_id": "frame", "members": [],
                "membership": fact("complete"), "assignments": [], "validities": []}
    number = 0
    for class_number, size in enumerate(class_sizes, start=1):
        for _ in range(size):
            number += 1
            item_id = "item-" + str(number).zfill(3)
            assignment_id = "assignment-" + str(number).zfill(3)
            validity_id = "validity-" + str(number).zfill(3)
            snapshot["members"].append(item_id)
            snapshot["assignments"].append({"item_id": item_id, "assignment_id": assignment_id})
            snapshot["validities"].append({"item_id": item_id, "validity_id": validity_id})
            records.extend([
                {"id": item_id, "type": "item", "logical_id": item_id, "version": "v1", "body": fact("private-body-918")},
                {"id": assignment_id, "type": "assignment", "item_id": item_id, "frame_id": "frame",
                 "class_id": fact("class-" + str(class_number)), "decision": fact("admitted"),
                 "basis": fact("private-classification-basis-918"), "asserted_by": fact("actor")},
                {"id": validity_id, "type": "validity", "item_id": item_id, "frame_id": "frame",
                 "verdict": fact("valid"), "basis": fact("Private validity basis."),
                 "rubric": fact("fixed-rubric"), "asserted_by": fact("actor")},
            ])
    records.append(snapshot)
    return {"schema": "ect-dossier/0.1", "id": "structural-test", "analysis_time": "2026-10-06T00:00:00Z",
            "policy": "ect-core/0.1", "records": records,
            "requests": [{"id": "profile", "operation": "profile", "scope_id": "scope", "snapshot_id": "snapshot"}]}


def index(dossier):
    return {record["id"]: record for record in dossier["records"]}


def add_evidence(dossier, identity="evidence", scope="scope"):
    record = {"id": identity, "type": "evidence", "scope_id": scope,
              "kind": fact("document"), "producer_id": fact("actor"),
              "access": fact("supplied"), "content": fact("private-evidence-918")}
    dossier["records"].append(record)
    return record


def add_review(dossier, identity="review", verdict="supports", scope="scope"):
    record = {"id": identity, "type": "review", "target_id": "assignment-001",
              "criterion": "assignment_resolution", "scope_id": scope,
              "assessor_id": fact("actor"), "reviewed_at": fact("2026-10-05T00:00:00Z"),
              "method": fact("Inspection."), "rationale": fact("Private reviewed reason."),
              "verdict": fact(verdict), "evidence_ids": ["evidence"]}
    dossier["records"].append(record)
    return record


class StructuralTests(unittest.TestCase):
    def result(self, dossier):
        admitted = admit(json.dumps(dossier).encode())
        return profile_request(admitted, admitted["requests"][0])

    def profile(self, dossier):
        return self.result(dossier)[0]["values"]["profiles"][0]

    def test_catalog_a_exact_independent_oracle(self):
        dossier = fixture()
        result, findings = self.result(dossier)
        value = result["values"]["profiles"][0]
        self.assertEqual(value["N"], count(24))
        self.assertEqual(value["A"], count(24))
        self.assertEqual(value["U"], count(0))
        self.assertEqual(value["observed_support"], count(4))
        self.assertEqual(value["SCI"], fraction(25, 72))
        self.assertEqual(value["D"], fraction(47, 72))
        self.assertEqual(value["assignment_coverage"], fraction(1, 1))
        self.assertEqual([row["count"] for row in value["class_counts"]], [count(12), count(6), count(4), count(2)])
        self.assertEqual(value["tails"][0]["state"], "present")
        self.assertEqual(result["assessment"], "not_assessed")
        self.assertTrue(all(row["assessment"] == "not_assessed" for row in findings))
        self.assertNotIn("private-", json.dumps((result, findings)))

    def test_catalog_b_and_incomplete_assignment(self):
        dossier = fixture((24, 16, 8, 0))
        value = self.profile(dossier)
        self.assertEqual(value["observed_support"], count(3))
        self.assertEqual(value["SCI"], fraction(7, 18))
        self.assertEqual(value["D"], fraction(11, 18))
        self.assertEqual(value["tails"][0]["state"], "absent")
        index(dossier)["assignment-048"]["class_id"] = gap()
        value = self.profile(dossier)
        self.assertEqual(value["N"], count(48))
        self.assertEqual(value["A"], count(47))
        self.assertEqual(value["U"], count(1))
        self.assertEqual(value["assignment_coverage"], fraction(47, 48))
        self.assertEqual(value["SCI"], fraction(881, 2209))
        self.assertEqual(value["D"], fraction(1328, 2209))
        self.assertEqual(value["tails"][0]["count"], count(0))
        self.assertEqual(value["tails"][0]["state"], "unestablished")
        self.assertEqual(len(value["class_counts"]), 4)

    def test_unknown_membership_retains_only_known_subset_distribution(self):
        dossier = fixture((24, 16, 7, 0))
        index(dossier)["snapshot"]["membership"] = fact("unknown")
        value = self.profile(dossier)
        self.assertEqual(value["K"], count(47))
        self.assertEqual(value["count_scope"], "known_roster")
        self.assertEqual(value["N"], {"state": "unavailable", "reason": "unknown_membership"})
        for field in ("SCI", "D", "assignment_coverage"):
            self.assertEqual(value[field], {"state": "unavailable", "reason": "unknown_membership"})
        self.assertEqual(value["known_subset"]["SCI"], fraction(881, 2209))
        self.assertEqual(value["known_subset"]["D"], fraction(1328, 2209))
        self.assertEqual(value["tails"][0]["state"], "unestablished")
        # Positive presence has a witness even when membership is incomplete.
        index(dossier)["frame"]["tail_designations"]["value"][0]["class_id"] = "class-3"
        self.assertEqual(self.profile(dossier)["tails"][0]["state"], "present")

    def test_empty_nonadmitted_and_single_class_are_distinct(self):
        empty = self.profile(fixture((0, 0, 0, 0)))
        for field in ("N", "A", "U", "observed_support"):
            self.assertEqual(empty[field], count(0))
        for field in ("SCI", "D", "assignment_coverage"):
            self.assertEqual(empty[field]["state"], "undefined")
            self.assertNotIn("value", empty[field])
        self.assertEqual(empty["tails"][0]["state"], "absent_in_empty_population")
        dossier = fixture((48, 0, 0, 0))
        single = self.profile(dossier)
        self.assertEqual(single["observed_support"], count(1))
        self.assertEqual(single["SCI"], fraction(1, 1))
        self.assertEqual(single["D"], fraction(0, 1))
        for record in dossier["records"]:
            if record["type"] == "assignment":
                record["decision"] = fact("unclassified")
        value = self.profile(dossier)
        self.assertEqual(value["U"], count(48))
        self.assertEqual(value["assignment_coverage"], fraction(0, 1))
        self.assertEqual(value["observed_support"], count(0))
        self.assertEqual(value["SCI"]["state"], "undefined")
        self.assertEqual(value["tails"][0]["state"], "unestablished")

    def test_missing_frame_roster_preserves_membership_not_distribution(self):
        dossier = fixture()
        del index(dossier)["frame"]["classes"]
        value = self.profile(dossier)
        self.assertEqual(value["K"], count(24))
        self.assertEqual(value["N"], count(24))
        self.assertEqual(value["class_counts"], [])
        for key in ("observed_support", "SCI", "D"):
            self.assertEqual(value[key]["state"], "unavailable")
        self.assertEqual(value["tails"][0]["state"], "unestablished")

    def test_primary_reason_precedence_and_overlapping_counts(self):
        dossier = fixture((1, 0, 0, 0))
        records = index(dossier)
        records["item-001"]["body"] = gap("withheld")
        records["assignment-001"]["decision"] = fact("disputed")
        value = self.profile(dossier)
        row = value["member_reasons"][0]
        self.assertEqual(row["primary_reason"], "disputed")
        self.assertTrue({"disputed", "withheld", "body_unavailable"} <= set(row["reason_codes"]))
        self.assertEqual(value["U"], count(1))
        self.assertGreater(sum(row["count"]["value"] for row in value["reason_counts"]), 1)
        del records["assignment-001"]["decision"]
        self.assertEqual(self.profile(dossier)["member_reasons"][0]["primary_reason"], "withheld")
        records["item-001"]["body"] = gap()
        records["snapshot"]["assignments"] = []
        self.assertEqual(self.profile(dossier)["member_reasons"][0]["primary_reason"], "body_unavailable")

    def test_class_roster_fact_gap_preserves_reason_precedence(self):
        for state in ("withheld", "disputed"):
            with self.subTest(state=state):
                dossier = fixture((1, 0, 0, 0))
                index(dossier)["frame"]["classes"] = gap(state)
                value = self.profile(dossier)
                self.assertEqual(value["member_reasons"][0]["primary_reason"], state)

    def test_confirmed_valid_has_independent_denominators(self):
        dossier = fixture()
        dossier["requests"][0]["population"] = "confirmed_valid"
        for identity in ("validity-023", "validity-024"):
            index(dossier)[identity]["verdict"] = fact("invalid")
        selected, valid = self.result(dossier)[0]["values"]["profiles"]
        self.assertEqual(selected["A"], count(24))
        self.assertEqual(selected["SCI"], fraction(25, 72))
        self.assertEqual(valid["K"], count(24))
        self.assertEqual(valid["V"], count(22))
        self.assertEqual(valid["N"], count(22))
        self.assertEqual(valid["SCI"], fraction(49, 121))
        self.assertEqual(valid["D"], fraction(72, 121))
        self.assertEqual(valid["validity_coverage"], fraction(1, 1))
        self.assertEqual(valid["assignment_coverage"], fraction(1, 1))
        self.assertEqual(valid["count_scope"], "confirmed_valid_subset")
        self.assertEqual(valid["tails"][0]["state"], "absent")
        self.assertEqual(selected["tails"][0]["state"], "present")

    def test_validity_qualification_and_separate_gap_states(self):
        dossier = fixture((5, 0, 0, 0))
        dossier["requests"][0]["population"] = "confirmed_valid"
        records = index(dossier)
        records["validity-001"]["verdict"] = fact("invalid")
        del records["validity-001"]["basis"]
        records["validity-002"]["verdict"] = gap("disputed")
        records["snapshot"]["validities"] = [row for row in records["snapshot"]["validities"] if row["item_id"] != "item-003"]
        records["validity-004"]["verdict"] = fact("invalid")
        value = self.result(dossier)[0]["values"]["profiles"][1]
        self.assertEqual(value["V"], count(1))
        self.assertEqual(value["validity_coverage"], fraction(2, 5))
        self.assertEqual({row["state"]: row["count"] for row in value["validity_counts"]},
                         {"valid": count(1), "invalid": count(1), "unresolved": count(1), "missing": count(1), "disputed": count(1)})
        self.assertFalse(value["population_complete"])
        records["validity-005"]["rubric"] = fact("other-rubric")
        value = self.result(dossier)[0]["values"]["profiles"][1]
        self.assertEqual(value["V"], count(0))
        self.assertEqual(value["validity_coverage"], fraction(1, 5))

    def test_unknown_validity_and_membership_keep_subset_arithmetic(self):
        dossier = fixture()
        dossier["requests"][0]["population"] = "confirmed_valid"
        records = index(dossier)
        records["validity-024"]["verdict"] = gap()
        value = self.result(dossier)[0]["values"]["profiles"][1]
        self.assertEqual(value["V"], count(23))
        self.assertEqual(value["SCI"], fraction(197, 529))
        self.assertEqual(value["validity_coverage"], fraction(23, 24))
        self.assertFalse(value["population_complete"])
        records["snapshot"]["membership"] = fact("partial")
        value = self.result(dossier)[0]["values"]["profiles"][1]
        self.assertEqual(value["N"], count(23))
        self.assertEqual(value["SCI"], fraction(197, 529))
        self.assertEqual(value["validity_coverage"]["state"], "unavailable")
        self.assertFalse(value["population_complete"])

    def test_explicit_validity_contrary_cannot_inflate_coverage(self):
        dossier = fixture((1, 0, 0, 0))
        dossier["requests"][0]["population"] = "confirmed_valid"
        add_evidence(dossier, "contrary")
        index(dossier)["validity-001"]["contrary_ids"] = ["contrary"]
        value = self.result(dossier)[0]["values"]["profiles"][1]
        self.assertEqual(value["V"], count(0))
        self.assertEqual(value["validity_coverage"], fraction(0, 1))
        self.assertEqual(value["validity_members"][0]["state"], "disputed")

    def test_selected_assignment_revision_changes_count_not_item_number(self):
        dossier = fixture()
        before = self.profile(dossier)
        replacement = copy.deepcopy(index(dossier)["assignment-024"])
        replacement.update(id="replacement", class_id=fact("class-1"), supersedes=fact("assignment-024"))
        dossier["records"].append(replacement)
        self.assertEqual(self.profile(dossier), before)
        index(dossier)["snapshot"]["assignments"][-1]["assignment_id"] = "replacement"
        after = self.profile(dossier)
        self.assertEqual(after["N"], count(24))
        self.assertEqual(after["SCI"], fraction(37, 96))
        self.assertEqual(after["class_counts"][-1]["count"], count(1))

    def test_model_failure_receipts_do_not_filter_population(self):
        dossier = fixture()
        add_evidence(dossier, "failure-receipt")
        index(dossier)["snapshot"]["tail_results"] = fact([{"class_id": "class-4", "evidence_ids": ["failure-receipt"]}])
        value = self.profile(dossier)
        self.assertEqual(value["A"], count(24))
        self.assertEqual(value["SCI"], fraction(25, 72))
        self.assertEqual(value["tails"][0]["evidence_ids"], ["failure-receipt"])

    def test_explicit_assignment_contrary_needs_exact_qualified_resolution(self):
        dossier = fixture((1, 0, 0, 0))
        add_evidence(dossier, "contrary")
        add_evidence(dossier)
        index(dossier)["assignment-001"]["contrary_ids"] = ["contrary"]
        self.assertEqual(self.profile(dossier)["A"], count(0))
        review = add_review(dossier)
        self.assertEqual(self.profile(dossier)["A"], count(0))
        review["resolves"] = ["contrary"]
        value = self.profile(dossier)
        self.assertEqual(value["A"], count(1))
        self.assertTrue(value["member_reasons"][0]["resolution"]["values"]["reviews"][0]["qualified"])
        del review["rationale"]
        self.assertEqual(self.profile(dossier)["A"], count(0))

    def test_unlisted_opposing_review_is_still_considered(self):
        dossier = fixture((1, 0, 0, 0))
        add_evidence(dossier)
        contrary = add_review(dossier, verdict="contradicts")
        self.assertEqual(self.profile(dossier)["A"], count(0))
        support = add_review(dossier, identity="support")
        self.assertEqual(self.profile(dossier)["A"], count(0))
        support["resolves"] = [contrary["id"]]
        self.assertEqual(self.profile(dossier)["A"], count(1))

    def test_wrong_scope_assignment_resolution_cannot_clear_contrary(self):
        dossier = fixture((1, 0, 0, 0))
        dossier["records"].append({"id": "other-scope", "type": "scope", "process_id": "process"})
        add_evidence(dossier, "contrary")
        add_evidence(dossier, scope="other-scope")
        review = add_review(dossier, scope="other-scope")
        review["resolves"] = ["contrary"]
        index(dossier)["assignment-001"]["contrary_ids"] = ["contrary"]
        value = self.profile(dossier)
        self.assertEqual(value["A"], count(0))
        resolution = value["member_reasons"][0]["resolution"]
        self.assertIn("scope_mismatch", resolution["reason_codes"])
        self.assertFalse(resolution["values"]["reviews"][0]["selected"])

    def test_disputed_snapshot_and_frame_cannot_establish_absence(self):
        for identity in ("snapshot", "frame"):
            with self.subTest(identity=identity):
                dossier = fixture((1, 0, 0, 0))
                add_evidence(dossier, "contrary")
                index(dossier)[identity]["contrary_ids"] = ["contrary"]
                result = self.result(dossier)[0]
                value = result["values"]["profiles"][0]
                self.assertEqual(value["A"], count(1))
                self.assertEqual(value["tails"][0]["state"], "unestablished")
                self.assertIn("contrary", result["contrary_ids"])
                self.assertFalse(value["population_complete"])

    def test_fixed_cohort_keeps_its_named_denominator(self):
        dossier = fixture()
        records = index(dossier)
        value, context = build_profile(records, "snapshot", "scope", member_ids=("item-001", "item-024"))
        self.assertEqual(value["N"], count(2))
        self.assertEqual(value["K"], count(24))
        self.assertEqual(value["SCI"], fraction(1, 2))
        self.assertEqual(value["count_scope"], "matched_cohort")
        self.assertEqual(context["cohort_members"], ("item-001", "item-024"))
        with self.assertRaises(ValueError):
            build_profile(records, "snapshot", "scope", member_ids=("item-001", "item-001"))

    def test_budget_retains_completed_selected_profile(self):
        dossier = fixture((1, 0, 0, 0))
        records = index(dossier)
        probe = RequestBudget()
        build_profile(records, "snapshot", "scope", budget=probe)
        dossier["requests"][0]["population"] = "confirmed_valid"
        budget = RequestBudget(limit=probe.used)
        with self.assertRaises(WorkLimit):
            profile_request(dossier, dossier["requests"][0], budget=budget)
        self.assertEqual(budget.partial_result["execution"], "partial")
        self.assertEqual(len(budget.partial_result["values"]["profiles"]), 1)
        self.assertEqual(budget.partial_result["values"]["profiles"][0]["N"], count(1))
        self.assertIn("resource_limit", budget.partial_result["reason_codes"])

    def test_budget_progress_contains_only_completed_member_witnesses(self):
        dossier = fixture((2, 0, 0, 0))
        records = index(dossier)
        for population, row_key in (("selected", "member_reasons"),
                                    ("confirmed_valid", "validity_members")):
            with self.subTest(population=population):
                budget = RequestBudget(limit=2)
                with self.assertRaises(WorkLimit):
                    build_profile(records, "snapshot", "scope", population=population, budget=budget)
                progress = budget.profile_progress
                self.assertEqual([row["item_id"] for row in progress[row_key]], ["item-001"])
                self.assertNotIn("SCI", progress)
                self.assertNotIn("N", progress)

    def test_tail_findings_group_states_without_dropping_class_inventory(self):
        dossier = fixture((1, 0, 0, 0))
        records = index(dossier)
        designation = records["frame"]["tail_designations"]["value"][0]
        records["frame"]["tail_designations"] = fact([
            dict(designation, class_id="class-" + str(number)) for number in range(1, 5)
        ])
        result, findings = self.result(dossier)
        self.assertEqual(len(result["values"]["profiles"][0]["tails"]), 4)
        self.assertEqual(len(findings), 3)
        absent = next(row for row in findings if row["rule"].endswith("_absent"))
        self.assertTrue({"class-2", "class-3", "class-4"} <= set(absent["subject_ids"]))


if __name__ == "__main__":
    unittest.main()
