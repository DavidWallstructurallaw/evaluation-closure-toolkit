"""Independent counterexamples for claim-review qualification and conflicts."""

import copy
import json
import unittest
from pathlib import Path

from evaluation_closure_toolkit.lint import lint_claim
from evaluation_closure_toolkit.evidence import evaluate_reviews
from evaluation_closure_toolkit.budget import RequestBudget, RunBudget, WorkLimit


DATA = Path(__file__).resolve().parents[1] / "src" / "evaluation_closure_toolkit" / "data"


def known(value):
    return {"state": "known", "value": value}


class LintQualificationTests(unittest.TestCase):
    def setUp(self):
        self.dossier = json.loads((DATA / "supported-narrow-regression.json").read_text())
        self.records = {record["id"]: record for record in self.dossier["records"]}
        self.review = next(record for record in self.dossier["records"] if record["type"] == "review")
        self.claim = next(record for record in self.dossier["records"] if record["type"] == "claim")
        self.receipt = next(record for record in self.dossier["records"] if record["type"] == "evidence"
                            and record["kind"] == known("execution_record"))

    def lint(self):
        return lint_claim(self.dossier, self.dossier["requests"][0])[0]

    def add_review(self, identity, verdict="contradicts"):
        review = copy.deepcopy(self.review)
        review["id"] = identity
        review["verdict"] = known(verdict)
        self.dossier["records"].append(review)
        return review

    def test_positive_and_sensitive_text_do_not_leak(self):
        self.receipt["content"] = known("secret-material-123 $(do-not-run) https://private.invalid/")
        self.receipt["locator"] = known("/secret/never-read")
        result = self.lint()
        self.assertEqual(result["values"]["claim_conclusion"], "supported_under_scope")
        self.assertNotIn("secret", json.dumps(result))

    def test_receipt_fields_are_substantive_prerequisites(self):
        for key in ("kind", "producer_id", "content", "access"):
            with self.subTest(key=key):
                original = self.receipt.pop(key)
                result = self.lint()
                self.assertEqual(result["values"]["claim_conclusion"], "unestablished")
                self.assertEqual(result["values"]["documentary_completeness"], "complete")
                self.receipt[key] = original

    def test_unsupported_validation_kind_stays_analytical_gap(self):
        self.claim["validation_kind"] = known("proof")
        self.receipt["kind"] = known("proof_record")
        result = self.lint()
        self.assertEqual(result["execution"], "completed")
        self.assertEqual(result["values"]["claim_conclusion"], "unestablished")
        self.assertIn("unsupported_validation_kind", result["values"]["validation"]["reason_codes"])

    def test_unsupported_kind_cannot_supply_decisive_validation(self):
        self.claim["validation_kind"] = known("proof")
        self.receipt["kind"] = known("proof_record")
        contrary = self.add_review("opposing-proof")
        contrary["decisive"] = known(True)
        contrary["counterexample_ids"] = [self.claim["id"]]
        result = self.lint()
        self.assertEqual(result["values"]["validation"]["assessment"], "unresolved")
        self.assertEqual(result["values"]["claim_conclusion"], "unestablished")
        self.assertIn("opposing-proof", result["contrary_ids"])
        self.claim["requirements"]["value"].append("recovery")
        self.assertEqual(self.lint()["values"]["claim_conclusion"], "defeated_under_scope")

    def test_unknown_opposing_verdict_prevents_cherry_picking(self):
        contrary = self.add_review("opposing")
        contrary["verdict"] = {"state": "unknown", "reason": "pending", "evidence_ids": []}
        result = self.lint()
        self.assertEqual(result["values"]["claim_conclusion"], "unestablished")
        self.assertIn("disputed", result["values"]["validation"]["reason_codes"])

    def test_incomplete_contradiction_cannot_be_erased_by_support(self):
        contrary = self.add_review("opposing")
        del contrary["method"]
        result = self.lint()
        self.assertEqual(result["values"]["claim_conclusion"], "unestablished")
        self.assertIn("opposing", result["contrary_ids"])
        self.assertIn(self.review["id"], result["support_ids"])

    def test_exact_resolution_preserves_historical_contrary(self):
        self.add_review("opposing")
        resolver = self.add_review("resolution", "supports")
        resolver["resolves"] = ["opposing"]
        result = self.lint()
        self.assertEqual(result["values"]["claim_conclusion"], "supported_under_scope")
        validation = result["values"]["validation"]
        self.assertIn("opposing", validation["contrary_ids"])
        self.assertIn("opposing", validation["values"]["resolved_ids"])

    def test_resolution_cycle_has_no_winner(self):
        first = self.add_review("opposing")
        second = self.add_review("resolution", "supports")
        first["resolves"] = ["resolution"]
        second["resolves"] = ["opposing"]
        result = self.lint()
        self.assertEqual(result["values"]["claim_conclusion"], "unestablished")
        self.assertEqual(result["values"]["validation"]["values"]["resolved_ids"], [])

    def test_resolving_own_support_is_ineffective(self):
        self.receipt["contrary_ids"] = [self.receipt["id"]]
        self.review["resolves"] = [self.receipt["id"]]
        self.assertEqual(self.lint()["values"]["claim_conclusion"], "unestablished")

    def test_decisive_requires_counterexample_in_exact_scope(self):
        contrary = self.add_review("decisive")
        contrary["decisive"] = known(True)
        contrary["counterexample_ids"] = [self.claim["id"]]
        self.assertEqual(self.lint()["values"]["claim_conclusion"], "defeated_under_scope")
        del contrary["counterexample_ids"]
        self.assertEqual(self.lint()["values"]["claim_conclusion"], "unestablished")

    def test_resolved_counterexample_cannot_remain_decisive(self):
        counterexample = next(r for r in self.dossier["records"] if r["type"] == "evidence"
                              and r["id"] not in self.review["evidence_ids"])
        contrary = self.add_review("decisive-review")
        contrary["decisive"] = known(True)
        contrary["counterexample_ids"] = [counterexample["id"]]
        resolver = self.add_review("resolver", "supports")
        resolver["resolves"] = [counterexample["id"]]
        result = self.lint()
        validation = result["values"]["validation"]
        self.assertIn(counterexample["id"], validation["values"]["resolved_ids"])
        self.assertEqual(validation["values"]["decisive_review_ids"], [])
        self.assertEqual(result["values"]["claim_conclusion"], "unestablished")

    def test_explicit_wrong_scope_cannot_be_widened_by_subject_ids(self):
        scope = copy.deepcopy(self.records[self.review["scope_id"]])
        scope["id"] = "scope-other"
        scope.pop("claim_id", None)
        counterexample = copy.deepcopy(self.receipt)
        counterexample["id"] = "other-counterexample"
        counterexample["scope_id"] = "scope-other"
        self.dossier["records"].extend([scope, counterexample])
        self.receipt.setdefault("subject_ids", []).append(counterexample["id"])
        contrary = self.add_review("decisive-review")
        contrary["decisive"] = known(True)
        contrary["counterexample_ids"] = [counterexample["id"]]
        result = self.lint()
        self.assertEqual(result["values"]["validation"]["values"]["decisive_review_ids"], [])
        self.assertEqual(result["values"]["claim_conclusion"], "unestablished")

    def test_expiry_boundary_is_supplied_time(self):
        self.claim["valid_until"] = known(self.dossier["analysis_time"])
        result = self.lint()
        self.assertEqual(result["values"]["currentness"], "expired_under_declared_date")
        self.assertEqual(result["values"]["claim_conclusion"], "unestablished")

    def test_unknown_features_never_manufacture_counterexample(self):
        frame = self.records[self.claim["frame_id"]["value"]]
        frame.pop("features")
        result = self.lint()
        self.assertEqual(result["values"]["scope_mismatches"], [])
        self.assertEqual(result["values"]["claim_conclusion"], "unestablished")

    def test_disclosed_anchor_contrary_cannot_be_ignored(self):
        item = next(r for r in self.dossier["records"] if r["type"] == "item")
        item["contrary_ids"] = [self.receipt["id"]]
        result = self.lint()
        self.assertEqual(result["values"]["claim_conclusion"], "unestablished")
        row = next(r for r in result["values"]["disclosures"] if r["id"] == "R03")
        self.assertIn("disputed", row["reasons"])
        self.assertIn(self.receipt["id"], result["contrary_ids"])

    def test_input_order_cannot_choose_a_review(self):
        self.add_review("opposing")
        result = self.lint()
        self.dossier["records"].reverse()
        self.assertEqual(result, self.lint())

    def test_supported_lint_does_not_mutate_input(self):
        before = copy.deepcopy(self.dossier)
        self.lint()
        self.assertEqual(before, self.dossier)

    def test_resolution_fanout_charged_before_materialization(self):
        premise = next(r for r in self.dossier["records"] if r["type"] == "evidence"
                       and r["id"] not in self.review["evidence_ids"])
        for number in range(20):
            resolver = self.add_review(f"resolver-{number:02d}", "supports")
            resolver["resolves"] = [premise["id"]]
            resolver["contrary_ids"] = [premise["id"]]
        records = {r["id"]: r for r in self.dossier["records"]}
        budget = RequestBudget(limit=200)
        with self.assertRaises(WorkLimit) as caught:
            evaluate_reviews(records, self.claim["id"], "claim_validation", self.review["scope_id"],
                             required_kinds={"execution_record"}, budget=budget)
        self.assertEqual(budget.used, 200)
        self.assertEqual(budget.run.used, 200)
        self.assertFalse(caught.exception.run_exhausted)

    def test_run_budget_accumulates_across_requests(self):
        run = RunBudget(limit=5)
        first = RequestBudget(run=run, limit=4)
        first.charge(3)
        second = RequestBudget(run=run, limit=4)
        second.charge(2)
        with self.assertRaises(WorkLimit) as caught:
            second.charge()
        self.assertTrue(caught.exception.run_exhausted)
        self.assertEqual((first.used, second.used, run.used), (3, 2, 5))

    def test_lint_shares_budget_across_disclosure_rows(self):
        ample = RequestBudget()
        lint_claim(self.dossier, self.dossier["requests"][0], budget=ample)
        restricted = RequestBudget(limit=ample.used - 1)
        with self.assertRaises(WorkLimit):
            lint_claim(self.dossier, self.dossier["requests"][0], budget=restricted)
        self.assertEqual(restricted.used, restricted.limit)

    def test_partial_lint_retains_completed_witnesses_without_claim_support(self):
        class StopAfterTwoRows(RequestBudget):
            def charge(inner, n=1):
                if inner.partial_result and len(inner.partial_result["values"]["disclosures"]) >= 2:
                    raise WorkLimit(run_exhausted=False)
                super().charge(n)

        self.claim["requirements"]["value"].append("recovery")
        budget = StopAfterTwoRows()
        with self.assertRaises(WorkLimit):
            lint_claim(self.dossier, self.dossier["requests"][0], budget=budget)
        partial = budget.partial_result
        self.assertEqual(partial["execution"], "partial")
        self.assertEqual(partial["assessment"], "not_assessed")
        self.assertEqual(partial["values"]["claim_conclusion"], "not_assessed")
        self.assertEqual(partial["values"]["documentary_completeness"], "not_assessed")
        self.assertEqual([row["id"] for row in partial["values"]["disclosures"]], ["R01", "R02"])
        self.assertEqual(partial["values"]["validation"]["assessment"], "supported_under_scope")
        self.assertIn(self.review["id"], partial["support_ids"])
        self.assertEqual(partial["values"]["scope_mismatches"][0]["required_feature"], "recovery")
        self.assertTrue(any(f["rule"] == "required_feature_absent" for f in budget.partial_findings))


if __name__ == "__main__":
    unittest.main()
