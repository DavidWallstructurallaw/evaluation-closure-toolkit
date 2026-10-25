"""Artifact contract checks without a third-party runtime schema dependency."""
import json
from pathlib import Path
import re
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "src/evaluation_closure_toolkit/data/dossier.schema.json"
GENERATOR = ROOT / "scripts/generate_schema.py"


class PackagedSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_bytes())
        cls.definitions = cls.schema["$defs"]

    def resolve(self, shape):
        return self.definitions[shape["$ref"].removeprefix("#/$defs/")]

    def test_packaged_artifact_matches_current_grammar(self):
        generate = runpy.run_path(str(GENERATOR))["schema_bytes"]
        self.assertEqual(SCHEMA_PATH.read_bytes(), generate())

    def test_dossier_is_closed_and_has_validation_only_empty_request_form(self):
        self.assertEqual(self.schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(set(self.schema["required"]), {"schema", "id", "analysis_time", "policy", "records", "requests"})
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(self.schema["properties"]["requests"].get("minItems", 0), 0)
        self.assertEqual(self.schema["properties"]["requests"]["maxItems"], 64)
        self.assertEqual(self.schema["properties"]["records"]["maxItems"], 30000)

    def test_every_record_and_request_family_is_present_and_closed(self):
        records = {
            "entity", "scope", "claim", "frame", "item", "assignment", "validity", "snapshot", "evidence",
            "review", "relation", "frontier", "independence", "external_cohort", "external_event", "anomaly",
            "revision", "correction_case",
        }
        requests = {"lint", "profile", "compare", "lineage", "external", "cases", "assess"}
        for group, names, required, discriminator in (
            ("record", records, {"id", "type"}, "type"),
            ("request", requests, {"id", "operation", "scope_id"}, "operation"),
        ):
            alternatives = [self.resolve(shape) for shape in self.definitions[group]["oneOf"]]
            self.assertEqual({shape["properties"][discriminator]["enum"][0] for shape in alternatives}, names)
            for shape in alternatives:
                self.assertFalse(shape["additionalProperties"])
                self.assertTrue(required <= set(shape["required"]))

    def test_missing_claim_facts_are_permitted_but_known_null_is_not_a_text(self):
        claim = self.definitions["record_claim"]
        self.assertEqual(set(claim["required"]), {"id", "type", "scope_id", "profile"})
        fact = self.resolve(claim["properties"]["statement"])
        known, gap, disputed = fact["oneOf"]
        self.assertEqual(known["properties"]["state"], {"const": "known"})
        self.assertEqual(set(known["required"]), {"state", "value"})
        self.assertEqual(self.resolve(known["properties"]["value"])["type"], "string")
        self.assertEqual(set(gap["required"]), {"state", "reason", "evidence_ids"})
        self.assertNotIn("value", gap["properties"])
        self.assertNotIn("candidates", gap["properties"])
        self.assertEqual(disputed["properties"]["state"], {"const": "disputed"})
        self.assertEqual(disputed["properties"]["candidates"]["items"], known["properties"]["value"])
        for shape in fact["oneOf"]:
            self.assertFalse(shape["additionalProperties"])

    def test_common_fields_do_not_expand_protected_record_shapes(self):
        for name in ("entity", "scope", "evidence", "review"):
            self.assertNotIn("asserted_by", self.definitions["record_" + name]["properties"])
        for name in ("claim", "frame", "snapshot", "relation", "correction_case"):
            shape = self.definitions["record_" + name]
            self.assertIn("asserted_by", shape["properties"])
            self.assertNotIn("asserted_by", shape["required"])

    def test_id_sets_and_pairwise_membership_bounds(self):
        independence = self.definitions["record_independence"]
        self.assertTrue(independence["properties"]["members"]["uniqueItems"])
        self.assertEqual(independence["properties"]["members"]["minItems"], 2)
        self.assertEqual(independence["allOf"], [{
            "if": {"properties": {"form": {"const": "pairwise"}}},
            "then": {"properties": {"members": {"maxItems": 2}}},
        }])

    def test_criterion_specific_review_bindings(self):
        conditions = self.definitions["record_review"]["allOf"]
        expected = {
            "member_id": {"externality", "input_qualification", "retention"},
            "target_event_id": {"correction_outcome"},
            "request_id": {"matching_basis"},
            "disclosure_id": {"applicability"},
        }
        for condition in conditions[:-1]:
            key = condition["then"]["required"][0]
            self.assertEqual(set(condition["if"]["properties"]["criterion"]["enum"]), expected.pop(key))
            self.assertEqual(condition["else"], {"properties": {key: False}})
        self.assertFalse(expected)
        self.assertEqual(set(conditions[-1]["if"]["properties"]["criterion"]["enum"]), {"claim_validation", "validation_type_fit"})
        self.assertEqual(conditions[-1]["else"], {"properties": {"disclosure_ids": False}})

    def test_identifier_and_timestamp_patterns_reject_trailing_controls(self):
        identifier = re.compile(self.definitions["id"]["pattern"])
        for candidate in ("A", "scope-main", "a.b:1_2"):
            self.assertIsNotNone(identifier.search(candidate))
        for candidate in ("a\n", "a\r", "1a", " a", "a/../b"):
            self.assertIsNone(identifier.search(candidate))
        timestamp = re.compile(self.definitions["timestamp"]["pattern"])
        self.assertIsNotNone(timestamp.search("2026-10-06T00:00:00Z"))
        for candidate in ("2026-10-06T00:00:00Z\n", "2026-10-06T00:00:60Z", "2026-10-06T00:00:00+00:00", "0000-10-06T00:00:00Z"):
            self.assertIsNone(timestamp.search(candidate))

    def test_all_schema_references_are_packaged_and_resolvable(self):
        pending = [self.schema]
        while pending:
            value = pending.pop()
            if isinstance(value, dict):
                if "$ref" in value:
                    self.assertTrue(value["$ref"].startswith("#/$defs/"))
                    self.assertIn(value["$ref"][len("#/$defs/"):], self.definitions)
                pending.extend(value.values())
            elif isinstance(value, list):
                pending.extend(value)


if __name__ == "__main__":
    unittest.main()
