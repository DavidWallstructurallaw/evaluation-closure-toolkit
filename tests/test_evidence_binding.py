"""Exact comparison binding and index parity, without scientific text inference."""

from copy import deepcopy
from importlib.resources import files
import json
import unittest

from evaluation_closure_toolkit.admission import admit
from evaluation_closure_toolkit.evidence import evaluate_reviews, make_review_index


class ReviewBindingTests(unittest.TestCase):
    def setUp(self):
        dossier = json.loads(files("evaluation_closure_toolkit").joinpath(
            "data", "supported-narrow-regression.json").read_bytes())
        template = next(r for r in dossier["records"] if r["id"] == "validation-review")
        for identifier, verdict in (("compare-a", "supports"), ("compare-b", "contradicts")):
            review = deepcopy(template)
            review.update(id="review-" + identifier, target_id="scope-main",
                          criterion="matching_basis", request_id=identifier,
                          verdict={"state": "known", "value": verdict})
            review.pop("disclosure_ids")
            if verdict == "contradicts":
                review.update(decisive={"state": "known", "value": True},
                              counterexample_ids=["scope-main"])
            dossier["records"].append(review)
        dossier["requests"] = [{"id": name, "operation": "compare", "scope_id": "scope-main",
                                 "before_id": "snapshot-v1", "after_id": "snapshot-v1",
                                 "mode": "matched"} for name in ("compare-a", "compare-b")]
        admitted = admit(json.dumps(dossier).encode())
        self.records = {r["id"]: r for r in admitted["records"]}

    def test_other_request_cannot_supply_or_defeat_matching_basis(self):
        for identifier, expected in (("compare-a", "supported_under_scope"),
                                     ("compare-b", "contradicted_under_scope")):
            with self.subTest(identifier=identifier):
                result = evaluate_reviews(self.records, "scope-main", "matching_basis",
                                          "scope-main", request_id=identifier)
                self.assertEqual(result["assessment"], expected)
                self.assertEqual([r["review_id"] for r in result["values"]["reviews"]],
                                 ["review-" + identifier])
        missing = evaluate_reviews(self.records, "scope-main", "matching_basis", "scope-main",
                                   request_id="not-a-selected-request")
        self.assertEqual(missing["assessment"], "unresolved")
        self.assertEqual(missing["values"]["reviews"], [])

    def test_index_preserves_wrong_scope_and_opposing_declarations(self):
        wrong = deepcopy(self.records["review-compare-a"])
        wrong.update(id="wrong-scope-review", scope_id="scope-other")
        self.records[wrong["id"]] = wrong
        plain = evaluate_reviews(self.records, "scope-main", "matching_basis", "scope-main",
                                 request_id="compare-a")
        indexed = evaluate_reviews(self.records, "scope-main", "matching_basis", "scope-main",
                                   request_id="compare-a", review_index=make_review_index(self.records))
        self.assertEqual(indexed, plain)
        declaration = next(r for r in indexed["values"]["reviews"] if r["review_id"] == wrong["id"])
        self.assertFalse(declaration["selected"])
        self.assertFalse(declaration["qualified"])
        self.assertIn("scope_mismatch", declaration["reason_codes"])

    def test_matching_basis_cannot_be_requested_without_binding(self):
        with self.assertRaisesRegex(ValueError, "^MATCHING_REQUEST_REQUIRED$"):
            evaluate_reviews(self.records, "scope-main", "matching_basis", "scope-main")


if __name__ == "__main__":
    unittest.main()
