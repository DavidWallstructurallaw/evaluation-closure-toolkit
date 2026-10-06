"""Independent closed-grammar and hostile-token admission examples."""

import copy
import json
import unittest

from evaluation_closure_toolkit.admission import admit
from evaluation_closure_toolkit.errors import AdmissionError
from evaluation_closure_toolkit.schema_data import RECORD_FIELDS, REQUEST_FIELDS


def known(value):
    return {"state": "known", "value": value}


def base():
    return {
        "schema": "ect-dossier/0.1", "id": "dossier", "analysis_time": "2026-10-06T21:00:00Z",
        "policy": "ect-core/0.1", "records": [
            {"type": "entity", "id": "process", "kind": "process", "logical_id": "process", "version": "v1"},
            {"type": "scope", "id": "scope", "process_id": "process", "claim_id": "claim"},
            {"type": "claim", "id": "claim", "scope_id": "scope", "profile": "narrow_regression"},
        ],
        "requests": [{"id": "lint", "operation": "lint", "scope_id": "scope", "claim_id": "claim"}],
    }


def packet():
    """Explicit independent example with every record and request variant."""
    dossier = base()
    dossier["records"][1]["snapshot_ids"] = ["snapshot"]
    dossier["records"] += [
        {"id": "actor", "type": "entity", "kind": "actor", "logical_id": "actor", "version": "v1"},
        {"id": "model", "type": "entity", "kind": "model", "logical_id": "model", "version": "v1"},
        {"id": "artifact", "type": "entity", "kind": "artifact", "logical_id": "artifact", "version": "v1"},
        {"id": "input", "type": "entity", "kind": "contribution", "logical_id": "input", "version": "v1"},
        {"id": "frame", "type": "frame", "classes": known([{"id": "C", "definition": "Finite class"}]),
         "tail_designations": known([{"class_id": "C", "rationale": "Selected", "severity": "High", "rarity_basis": "Declared"}])},
        {"id": "item", "type": "item", "logical_id": "item", "version": "v1", "contribution_ids": ["input"]},
        {"id": "assignment", "type": "assignment", "item_id": "item", "frame_id": "frame", "class_id": known("C")},
        {"id": "validity", "type": "validity", "item_id": "item", "frame_id": "frame"},
        {"id": "snapshot", "type": "snapshot", "frame_id": "frame", "members": ["item"],
         "assignments": [{"item_id": "item", "assignment_id": "assignment"}],
         "validities": [{"item_id": "item", "validity_id": "validity"}],
         "tail_results": known([{"class_id": "C", "evidence_ids": ["receipt"]}])},
        {"id": "receipt", "type": "evidence", "scope_id": "scope", "subject_ids": ["input"]},
        {"id": "review", "type": "review", "scope_id": "scope", "target_id": "claim", "criterion": "claim_validation", "disclosure_ids": ["R01"]},
        {"id": "relation", "type": "relation", "scope_id": "scope", "from_id": "item", "to_id": "input", "kind": "derived_from"},
        {"id": "frontier", "type": "frontier", "scope_id": "scope", "node_id": "input", "view": "acquisition"},
        {"id": "independence", "type": "independence", "scope_id": "scope", "members": ["item", "input"], "form": "pairwise", "dimension": "acquisition"},
        {"id": "cohort", "type": "external_cohort", "scope_id": "scope", "members": ["input"],
         "externality_reviews": [{"member_id": "input", "review_id": "externality"}],
         "qualifications": [{"member_id": "input", "review_id": "qualification"}], "carryover_ids": ["input"]},
        {"id": "externality", "type": "review", "scope_id": "scope", "target_id": "cohort", "criterion": "externality", "member_id": "input", "evidence_ids": ["receipt"]},
        {"id": "qualification", "type": "review", "scope_id": "scope", "target_id": "cohort", "criterion": "input_qualification", "member_id": "input"},
        {"id": "event", "type": "external_event", "scope_id": "scope", "cohort_id": "cohort", "member_id": "input", "stage": "used"},
        {"id": "anomaly", "type": "anomaly", "scope_id": "scope", "frame_id": "frame", "revision_ids": ["revision"], "case_ids": ["case"]},
        {"id": "revision", "type": "revision", "scope_id": "scope", "from_frame": "frame", "to_frame": "frame", "anomaly_ids": ["anomaly"],
         "class_map": [{"from_class": "C", "to_class": "C"}], "new_assignment_ids": ["assignment"]},
        {"id": "case", "type": "correction_case", "scope_id": "scope", "claim_id": "claim",
         "handling": [{"id": "ticket", "evidence_ids": []}], "attempts": [{"id": "attempt", "evidence_ids": []}],
         "actions": [{"id": "action", "attempt_id": "attempt", "evidence_ids": []}],
         "outcomes": [{"id": "outcome", "action_id": "action", "evidence_ids": [], "review_id": known("outcome-review")}],
         "route": known({"actor_id": "actor", "target_id": "claim", "procedure": "Restrict scope", "evidence_ids": []}),
         "authority": known({"actor_id": "actor", "target_id": "claim", "start": "2026-01-01T00:00:00Z", "end": "2027-01-01T00:00:00Z", "evidence_ids": []})},
        {"id": "outcome-review", "type": "review", "target_id": "case", "criterion": "correction_outcome", "scope_id": "scope", "target_event_id": "outcome"},
        {"id": "match-review", "type": "review", "target_id": "scope", "criterion": "matching_basis", "scope_id": "scope", "request_id": "compare"},
        {"id": "applicability", "type": "review", "target_id": "claim", "criterion": "applicability", "scope_id": "scope", "disclosure_id": "R06"},
    ]
    dossier["requests"] += [
        {"id": "profile", "operation": "profile", "scope_id": "scope", "snapshot_id": "snapshot"},
        {"id": "compare", "operation": "compare", "scope_id": "scope", "before_id": "snapshot", "after_id": "snapshot", "mode": "matched",
         "revision_id": "revision", "pairs": [{"before_item_id": "item", "after_item_id": "item", "basis": "Declared same item"}]},
        {"id": "lineage", "operation": "lineage", "scope_id": "scope", "seed_ids": ["item", "input"], "view": "acquisition", "independence_ids": ["independence"]},
        {"id": "external", "operation": "external", "scope_id": "scope", "cohort_id": "cohort"},
        {"id": "cases", "operation": "cases", "scope_id": "scope", "case_ids": ["case"], "anomaly_ids": ["anomaly"], "revision_ids": ["revision"]},
        {"id": "assess", "operation": "assess", "scope_id": "scope", "claim_id": "claim", "snapshot_id": "snapshot", "cohort_id": "cohort"},
    ]
    return dossier


def by_id(dossier, identity):
    return next(record for record in dossier["records"] if record["id"] == identity)


class AdmissionTests(unittest.TestCase):
    def parse(self, dossier):
        return admit(json.dumps(dossier, ensure_ascii=True).encode())

    def rejects(self, dossier, code=None):
        with self.assertRaises(AdmissionError) as context:
            self.parse(dossier)
        if code:
            self.assertEqual(context.exception.code, code)
        return context.exception

    def test_minimal_and_empty_are_valid(self):
        self.assertEqual(self.parse(base()), base())
        data = base()
        data["records"] = []
        data["requests"] = []
        self.assertEqual(self.parse(data), data)

    def test_every_record_and_operation_admitted(self):
        data = packet()
        self.assertEqual({row["type"] for row in data["records"]}, set(RECORD_FIELDS))
        self.assertEqual({row["operation"] for row in data["requests"]}, set(REQUEST_FIELDS))
        self.assertEqual(self.parse(data), data)

    def test_every_record_is_closed(self):
        for position, row in enumerate(packet()["records"]):
            with self.subTest(record_type=row["type"]):
                data = packet()
                data["records"][position]["confidential-password"] = "secret"
                error = self.rejects(data, "INPUT_UNKNOWN_KEY")
                self.assertEqual(error.pointer, f"/records/{position}")
                self.assertNotIn("confidential", str(error))

    def test_every_request_is_closed(self):
        for position, row in enumerate(packet()["requests"]):
            with self.subTest(operation=row["operation"]):
                data = packet()
                data["requests"][position]["extra"] = True
                self.rejects(data, "INPUT_UNKNOWN_KEY")

    def test_fact_variants_and_disputed_candidates(self):
        for state in ("unknown", "withheld", "disputed", "absent", "not_applicable"):
            data = base()
            by_id(data, "claim")["statement"] = {"state": state, "reason": "Intentionally incomplete", "evidence_ids": []}
            self.parse(data)
        data = base()
        by_id(data, "claim")["statement"] = {"state": "disputed", "reason": "Two accounts", "evidence_ids": [], "candidates": ["a", "b"]}
        self.parse(data)
        by_id(data, "claim")["statement"]["state"] = "unknown"
        self.rejects(data, "INPUT_UNKNOWN_KEY")

    def test_fact_wrong_shape(self):
        for invalid in ({"state": "known"}, {"state": "known", "value": "text", "reason": "extra"}, {"state": "absent", "reason": "gap"}, "text"):
            data = base()
            by_id(data, "claim")["statement"] = invalid
            self.rejects(data)

    def test_nonempty_text_is_syntactic_not_prose_adequacy(self):
        data = base()
        by_id(data, "claim")["statement"] = known(" ")
        self.parse(data)
        by_id(data, "claim")["statement"] = known("")
        self.rejects(data, "INPUT_TEXT")

    def test_common_fields_are_not_added_to_identity_or_review(self):
        data = packet()
        for identity in ("actor", "scope", "receipt", "review"):
            candidate = copy.deepcopy(data)
            by_id(candidate, identity)["asserted_by"] = known("actor")
            self.rejects(candidate, "INPUT_UNKNOWN_KEY")

    def test_missing_and_wrong_reference_types(self):
        for identity in ("missing", "claim"):
            data = base()
            by_id(data, "scope")["process_id"] = identity
            self.rejects(data)
        data = packet()
        by_id(data, "review")["assessor_id"] = known("process")
        self.rejects(data, "INPUT_REFERENCE_TYPE")

    def test_immutable_versions_and_case_sensitive_identity(self):
        data = packet()
        row = copy.deepcopy(by_id(data, "item"))
        row["id"] = "item-alias"
        data["records"].append(row)
        self.rejects(data, "INPUT_IMMUTABLE_IDENTITY")
        row["logical_id"] = "Item"
        self.parse(data)

    def test_duplicate_ids_members_and_class_ids(self):
        data = packet()
        data["records"].append(copy.deepcopy(data["records"][0]))
        self.rejects(data, "INPUT_DUPLICATE_ID")
        data = packet()
        by_id(data, "snapshot")["members"].append("item")
        self.rejects(data, "INPUT_DUPLICATE_MEMBER")
        data = packet()
        by_id(data, "frame")["classes"]["value"].append({"id": "C", "definition": "Other meaning"})
        self.rejects(data, "INPUT_DUPLICATE_MEMBER")

    def test_snapshot_exclusion_and_immutable_version_selection(self):
        data = packet()
        by_id(data, "snapshot")["excluded"] = [{"item_id": "item", "reason": "Excluded"}]
        self.rejects(data, "INPUT_REFERENCE_BINDING")
        data = packet()
        data["records"].append({"id": "item-v2", "type": "item", "logical_id": "item", "version": "v2"})
        by_id(data, "snapshot")["members"].append("item-v2")
        self.rejects(data, "INPUT_IMMUTABLE_IDENTITY")

    def test_known_class_roster_reference_and_missing_roster(self):
        data = packet()
        by_id(data, "assignment")["class_id"] = known("missing-class")
        self.rejects(data, "INPUT_CLASS_REFERENCE")
        del by_id(data, "frame")["classes"]
        self.parse(data)

    def test_relation_endpoint_types(self):
        data = packet()
        relation = by_id(data, "relation")
        relation.update(kind="trained_on", from_id="model", to_id="item")
        self.parse(data)
        relation["from_id"] = "process"
        self.rejects(data, "INPUT_RELATION_ENDPOINT")
        relation.update(kind="evaluated_by", from_id="model", to_id="item")
        self.rejects(data, "INPUT_RELATION_ENDPOINT")

    def test_review_linkage_required_and_forbidden(self):
        data = packet()
        del by_id(data, "externality")["member_id"]
        self.rejects(data)
        data = packet()
        by_id(data, "review")["member_id"] = "input"
        self.rejects(data, "INPUT_REFERENCE_BINDING")
        data = packet()
        by_id(data, "outcome-review")["target_event_id"] = "ticket"
        self.rejects(data, "INPUT_REFERENCE_BINDING")

    def test_wrong_scope_review_is_retained(self):
        data = packet()
        data["records"].append({"id": "other-scope", "type": "scope", "process_id": "process"})
        by_id(data, "review")["scope_id"] = "other-scope"
        self.parse(data)

    def test_correction_local_links_and_nested_id_collision(self):
        data = packet()
        by_id(data, "case")["actions"][0]["attempt_id"] = "absent"
        self.rejects(data, "INPUT_REFERENCE")
        data = packet()
        by_id(data, "case")["handling"][0]["id"] = "attempt"
        self.rejects(data, "INPUT_DUPLICATE_ID")

    def test_reverse_correction_chronology_is_an_analytical_gap(self):
        data = packet()
        case = by_id(data, "case")
        case["attempts"][0]["occurred_at"] = known("2026-10-07T00:00:00Z")
        case["actions"][0]["occurred_at"] = known("2026-10-06T00:00:00Z")
        self.parse(data)

    def test_matched_roster_duplicates_but_missing_membership_valid(self):
        data = packet()
        request = next(x for x in data["requests"] if x["id"] == "compare")
        request["pairs"].append(copy.deepcopy(request["pairs"][0]))
        self.rejects(data, "INPUT_DUPLICATE_MEMBER")
        request["pairs"].pop()
        data["records"].append({"id": "outside", "type": "item", "logical_id": "outside", "version": "v1"})
        request["pairs"][0]["after_item_id"] = "outside"
        self.parse(data)

    def test_windows_and_gregorian_timestamps(self):
        for timestamp in ("2026-02-29T00:00:00Z", "2026-01-01T24:00:00Z", "2026-01-01T00:00:60Z", "0000-01-01T00:00:00Z", "2026-01-01T00:00:00+00:00"):
            data = base()
            data["analysis_time"] = timestamp
            self.rejects(data, "INPUT_TIMESTAMP")
        data = base()
        by_id(data, "scope")["window"] = known({"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:00:00Z"})
        self.rejects(data, "INPUT_WINDOW")

    def test_boolean_not_text_or_id(self):
        data = base()
        by_id(data, "claim")["statement"] = known(True)
        self.rejects(data, "INPUT_TEXT")
        data["id"] = True
        self.rejects(data, "INPUT_ID")

    def test_null_float_exponents_large_integer_and_duplicate_keys(self):
        for raw in (b'null', b'0.0', b'1e0', b'NaN', b'Infinity', b'-Infinity', b'9007199254740992', b'-9007199254740992', b'1' * 100_000, b'{"a":1,"a":2}'):
            with self.subTest(raw=raw[:25]), self.assertRaises(AdmissionError):
                admit(raw)

    def test_integer_bounds_are_lexically_valid_but_not_dossier_objects(self):
        for raw in (b'9007199254740991', b'-9007199254740991', b'-0'):
            with self.assertRaises(AdmissionError) as context:
                admit(raw)
            self.assertEqual(context.exception.code, "INPUT_TYPE")

    def test_quoted_syntax_and_escaped_unicode_are_inert(self):
        data = base()
        text = '"null":null, [true] \\u0000 ${SECRET} $(touch /tmp/no) https://example.invalid 😀'
        by_id(data, "claim")["statement"] = known(text)
        self.assertEqual(self.parse(data), data)

    def test_utf8_bom_surrogates_and_malformed_tokens(self):
        for raw in (b'\xef\xbb\xbf{}', b'\xff', b'"\\ud800"', b'"\\udc00"', b'"\\uZZZZ"', b'"\\x41"', b'"unterminated', b'[[}]', b'{"x":01}', b'{"x":}', b'truefalse'):
            with self.subTest(raw=raw), self.assertRaises(AdmissionError):
                admit(raw)

    def test_string_byte_limit(self):
        data = base()
        by_id(data, "claim")["statement"] = known("é" * 32768)
        self.parse(data)
        by_id(data, "claim")["statement"] = known("é" * 32769)
        self.rejects(data, "INPUT_STRING_LIMIT")

    def test_byte_depth_and_value_limits(self):
        for raw, expected in ((b" " * (10 * 1024 * 1024 + 1), "INPUT_BYTE_LIMIT"), (b"[" * 33 + b"]" * 33, "INPUT_DEPTH_LIMIT"), (b"[" + b",".join([b"0"] * 250000) + b"]", "INPUT_VALUE_LIMIT")):
            with self.assertRaises(AdmissionError) as context:
                admit(raw)
            self.assertEqual(context.exception.code, expected)

    def test_request_admission_limit_independent_of_selection_limit(self):
        data = base()
        data["requests"] = [{"id": f"r{i}", "operation": "lint", "scope_id": "scope", "claim_id": "claim"} for i in range(64)]
        self.parse(data)
        data["requests"].append({"id": "extra", "operation": "lint", "scope_id": "scope", "claim_id": "claim"})
        self.rejects(data, "INPUT_REQUEST_LIMIT")


if __name__ == "__main__":
    unittest.main()
