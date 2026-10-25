"""One installed-data workflow; finite expectations are independent literals."""

from copy import deepcopy
from importlib.resources import files
import json
import unittest

from evaluation_closure_toolkit import analyze_bytes, render_markdown
from provenance_helpers import record, wire


REQUEST_IDS = (
    "assess-main", "cases-main", "compare-main", "external-main",
    "lineage-main", "lint-main", "profile-main",
)


def available(value):
    return {"state": "available", "value": value}


def rational(numerator, denominator):
    return available({"numerator": str(numerator), "denominator": str(denominator)})


class BoundedWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = files("evaluation_closure_toolkit").joinpath(
            "data", "bounded-workflow.json").read_bytes()
        cls.dossier = json.loads(cls.raw)
        cls.report = analyze_bytes(cls.raw)
        cls.results = {row["operation"]: row for row in cls.report["results"]}

    def test_all_seven_operations_keep_their_distinct_conclusions(self):
        self.assertEqual(self.report["admission"], "valid")
        self.assertEqual(self.report["execution"], "completed")
        self.assertEqual(self.report["selected_request_ids"], list(REQUEST_IDS))
        self.assertEqual(set(self.results), {
            "lint", "profile", "compare", "lineage", "external", "cases", "assess"})
        self.assertTrue(all(r["scope_id"] == "scope" for r in self.results.values()))
        self.assertTrue(all(r["execution"] == "completed" for r in self.results.values()))
        for operation in ("profile", "compare", "lineage", "external", "cases"):
            self.assertEqual(self.results[operation]["assessment"], "not_assessed")

        lint = self.results["lint"]["values"]
        self.assertEqual(lint["documentary_completeness"], "complete")
        self.assertEqual(lint["claim_conclusion"], "unestablished")
        self.assertEqual(lint["open_evaluation"], "not_assessed")
        self.assertEqual(lint["currentness"], "current_under_declared_date")
        rows = {r["id"]: r for r in lint["disclosures"]}
        self.assertEqual(set(rows), {f"R{i:02d}" for i in range(1, 11)})
        for row_id, row in rows.items():
            self.assertEqual((row["presence"], row["well_formed"], row["linked"]),
                             ("present", "yes", "yes"))
            if row_id in {"R07", "R08"}:
                self.assertEqual((row["applicability"], row["qualification"]),
                                 ("not_applicable", "not_assessed"))
            else:
                self.assertEqual(row["qualification"], "supported_under_scope")

        assessment = self.results["assess"]["values"]
        self.assertEqual(assessment["conclusion"], "supported_under_scope")
        self.assertEqual(assessment["capacity_extent"], "tested_route")
        self.assertEqual([g["condition"] for g in assessment["conditions"]], [
            "structural_validity", "external_presence", "source_integrity",
            "tail_retention", "corrective_capacity"])
        self.assertEqual(sum(len(g["values"]["criteria"]) for g in assessment["conditions"]), 14)
        self.assertTrue(all(g["assessment"] == "supported_under_scope"
                            for g in assessment["conditions"]))
        # The shared report object still renders after the seven results combine.
        self.assertIn("supported_under_scope", render_markdown(self.report))

    def test_catalog_growth_keeps_exact_denominators_and_tail_failure_visibility(self):
        profile = self.results["profile"]["values"]["profiles"][0]
        for name, count in (("K", 3), ("N", 3), ("A", 3), ("U", 0), ("observed_support", 2)):
            self.assertEqual(profile[name], available(count))
        self.assertEqual(profile["assignment_coverage"], rational(1, 1))
        self.assertEqual(profile["SCI"], rational(5, 9))
        self.assertEqual(profile["D"], rational(4, 9))
        self.assertEqual(profile["class_counts"], [
            {"class_id": "rare", "count": available(1)},
            {"class_id": "usual", "count": available(2)}])
        self.assertEqual(profile["tails"][0]["state"], "present")
        self.assertEqual(profile["tails"][0]["evidence_ids"], ["tail-receipt"])
        self.assertIn("model failure", record(self.dossier, "tail-receipt")["content"]["value"])

        comparison = self.results["compare"]["values"]
        self.assertEqual(comparison["mode"], "descriptive")
        self.assertEqual(comparison["compatibility"]["state"], "supported")
        self.assertEqual(comparison["before"]["N"], available(2))
        self.assertEqual(comparison["before"]["SCI"], rational(1, 2))
        self.assertEqual(comparison["after"], profile)
        self.assertEqual(comparison["delta_SCI"], rational(1, 18))
        self.assertEqual(comparison["delta_D"], rational(-1, 18))

    def test_shared_source_is_visible_without_an_invented_independence_claim(self):
        lineage = self.results["lineage"]["values"]
        self.assertEqual(lineage["view"], "acquisition")
        self.assertTrue(lineage["search_complete"])
        self.assertEqual(lineage["witnesses"], [{
            "left_seed_id": "item-a", "right_seed_id": "item-b", "node_id": "source",
            "left_path": ["origin-a"], "right_path": ["origin-b"]}])
        self.assertEqual(lineage["independence_assessments"], [])
        self.assertEqual(lineage["recursive_witnesses"], [])
        source_gate = next(g for g in self.results["assess"]["values"]["conditions"]
                           if g["condition"] == "source_integrity")
        self.assertEqual(source_gate["assessment"], "supported_under_scope")
        self.assertIn("origin-c", record(self.dossier, "receipt-provenance_transformations")["subject_ids"])
        self.assertIn("unexamined", record(self.dossier, "receipt-provenance_transformations")["uncertainty"]["value"])

    def test_contact_axes_and_restriction_drill_are_not_promoted_to_stronger_claims(self):
        external = self.results["external"]["values"]
        self.assertEqual(external["full_member_count"], available(1))
        member = external["member_states"][0]
        self.assertEqual(member["member_id"], "z")
        self.assertEqual(member["contact_state"], "documented_current_contact")
        self.assertEqual({k: v["state"] for k, v in member["stages"].items()}, {
            "received": "yes", "retained": "unresolved",
            "selected": "unresolved", "used": "yes"})
        self.assertEqual(external["event_counts"], {
            "received": available(1), "retained": available(0),
            "selected": available(0), "used": available(1)})
        cases = self.results["cases"]["values"]
        self.assertEqual(cases["anomalies"], [])
        self.assertEqual(cases["revisions"], [])
        case = cases["corrections"][0]
        self.assertEqual((case["context"], case["objective"], case["capacity_extent"]),
                         ("drill", "restrict", "tested_route"))
        outcome = case["outcomes"][0]
        self.assertEqual((outcome["objective"], outcome["result"]), ("restrict", "effective"))
        self.assertEqual(outcome["review"]["assessment"], "supported_under_scope")
        self.assertEqual(cases["pair_counts"], {
            "attempted": available(1), "acted": available(1),
            "authorized": available(1), "effective": available(1)})

    def test_actual_prerequisites_match_standalone_results_and_selection_is_independent(self):
        assessment = self.results["assess"]["values"]
        prerequisites = {p["role"]: p["result"] for p in assessment["prerequisites"]}
        self.assertEqual(set(prerequisites), {"structural", "cases", "external"})
        for role, operation in (("structural", "profile"), ("cases", "cases"), ("external", "external")):
            self.assertEqual(prerequisites[role]["values"], self.results[operation]["values"])
        alone = analyze_bytes(self.raw, request_ids=("assess-main",))
        self.assertEqual(alone["results"][0]["values"], assessment)
        reversed_selection = analyze_bytes(self.raw, request_ids=tuple(reversed(REQUEST_IDS)))
        self.assertEqual(reversed_selection, self.report)

    def test_changed_use_receipt_recomputes_dependent_results_and_preserves_unrelated_values(self):
        dossier = deepcopy(self.dossier)
        record(dossier, "z-used")["evidence_ids"] = []
        changed = analyze_bytes(wire(dossier))
        self.assertEqual(changed["execution"], "completed")
        results = {r["operation"]: r for r in changed["results"]}
        self.assertEqual(results["assess"]["values"]["conclusion"], "unestablished")
        gates = {g["condition"]: g for g in results["assess"]["values"]["conditions"]}
        self.assertEqual(gates["external_presence"]["assessment"], "unresolved")
        self.assertEqual(gates["tail_retention"]["assessment"], "supported_under_scope")
        stages = results["external"]["values"]["member_states"][0]["stages"]
        self.assertEqual(stages["received"]["state"], "yes")
        self.assertEqual(stages["used"]["state"], "unresolved")
        for operation in ("profile", "compare", "lineage", "cases", "lint"):
            self.assertEqual(results[operation]["values"], self.results[operation]["values"])
        self.assertNotEqual(changed["input_sha256"], self.report["input_sha256"])


if __name__ == "__main__":
    unittest.main()
