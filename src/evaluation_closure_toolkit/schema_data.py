"""Closed ect-dossier/0.1 shape grammar, shared with schema generation.

Descriptors are data, never executable dossier instructions. Cross-record rules
are enforced in admission.py in addition to these local shapes.
"""


def enum(*values):
    return ("enum", values)


def ref(*types):
    return ("ref", types)


def entity(*kinds):
    return ("entity", kinds)


def fact(value):
    return ("fact", value)


def array(value, minimum=0, unique=False):
    return ("array", value, minimum, unique)


def obj(required, optional=None):
    return ("object", required, optional or {})


ID = ("id",)
TEXT = ("text",)
TIME = ("time",)
BOOL = ("boolean",)
ANY_REF = ref()
NODE = ref("entity", "item")
TARGET = ref("entity", "item", "claim")
EV = ref("evidence")
CONTRARY = ref("evidence", "review")
DIMENSION = enum("acquisition", "analytical_method", "model_ancestry", "evaluation_rubric", "organizational_control")
VIEW = enum("acquisition", "model_ancestry", "evaluation_rubric", "recursive_reuse")
FEATURE = enum("single_turn", "persistent_state", "long_horizon", "recovery", "override", "human_consequence", "field_use")
CONDITION = enum("structural_validity", "external_presence", "source_integrity", "tail_retention", "corrective_capacity")
DISCLOSURE = enum(*(f"R{i:02}" for i in range(1, 11)))
GATE_CRITERIA = (
    "frame_target_fidelity", "anomaly_accountability", "outside_process_contact", "claim_relevance", "recorded_use",
    "provenance_transformations", "validation_type_fit", "evaluator_relationships", "tail_designation_adequacy",
    "tail_representation", "tail_result_visibility", "route_and_authority", "route_operability", "capacity_extent",
)
CRITERIA = GATE_CRITERIA + (
    "claim_validation", "assignment_resolution", "frame_equivalence", "matching_basis", "independence",
    "externality", "input_qualification", "retention", "correction_outcome", "structural_revision", "applicability",
)
RELATIONS = (
    "derived_from", "acquired_from", "trained_on", "exposed_to", "rubric_from", "reference_from", "produced_by",
    "uses_generation", "uses_training", "uses_selection", "uses_reference", "uses_judgment", "semantic_influence", "evaluated_by",
)


def ids(value=ANY_REF, minimum=0):
    return array(value, minimum, unique=True)


WINDOW = obj({"start": TIME, "end": TIME})
COMMON = {
    "asserted_by": fact(entity()), "recorded_at": fact(TIME),
    "evidence_ids": ids(EV), "contrary_ids": ids(CONTRARY),
}
ROUTE = obj({"actor_id": entity("actor"), "target_id": TARGET, "procedure": TEXT, "evidence_ids": ids(EV)})
AUTHORITY = obj({"actor_id": entity("actor"), "target_id": TARGET, "start": TIME, "end": TIME, "evidence_ids": ids(EV)})
NESTED_BASE = {"id": ID, "evidence_ids": ids(EV)}
HANDLING = obj(NESTED_BASE, {"state": fact(enum("submitted", "accepted", "rejected")), "occurred_at": fact(TIME)})
ATTEMPT = obj(NESTED_BASE, {"actor_id": fact(entity("actor")), "target_id": fact(TARGET), "occurred_at": fact(TIME)})
ACTION = obj({**NESTED_BASE, "attempt_id": ID}, {
    "kind": fact(enum("repair", "restrict", "replace_evaluator", "withdraw")), "target_id": fact(TARGET),
    "occurred_at": fact(TIME), "resulting_state": fact(TEXT),
})
OUTCOME = obj({**NESTED_BASE, "action_id": ID}, {
    "criterion": fact(TEXT), "protocol": fact(TEXT), "horizon": fact(TEXT), "assessed_at": fact(TIME),
    "baseline": fact(EV), "result": fact(enum("effective", "ineffective", "unresolved")),
    "review_id": fact(ref("review")), "contrary_ids": ids(CONTRARY),
})

# Each value is (required fields, optional fields), before common record keys.
RECORD_FIELDS = {
    "entity": ({"kind": enum("actor", "process", "model", "artifact", "contribution"), "logical_id": ID, "version": ID},
               {"label": fact(TEXT), "role": fact(TEXT), "occurred_at": fact(TIME)}),
    "scope": ({"process_id": entity("process")}, {
        "claim_id": ref("claim"), "frame_id": ref("frame"), "snapshot_ids": ids(ref("snapshot")),
        "window": fact(WINDOW), "role": fact(TEXT), "dimension": fact(DIMENSION),
    }),
    "claim": ({"scope_id": ref("scope"), "profile": enum("narrow_regression", "open_evaluation")}, {
        "statement": fact(TEXT), "intended_use": fact(TEXT), "horizon": fact(TEXT), "frame_id": fact(ref("frame")),
        "requirements": fact(ids(FEATURE)), "validation_kind": fact(enum("execution", "proof", "observation", "human_consequence")),
        "valid_until": fact(TIME), "disclosures": obj({}, {f"R{i:02}": fact(ids()) for i in range(1, 11)}),
        "capacity_extent": fact(enum("tested_route", "sustained")),
    }),
    "frame": ({}, {
        **{key: fact(TEXT) for key in ("task", "context", "horizon", "resolution", "exclusions", "validity_rubric", "admission_policy", "selection_policy")},
        "features": fact(ids(FEATURE)), "classes": fact(array(obj({"id": ID, "definition": TEXT}))),
        "tail_designations": fact(array(obj({"class_id": ID, "rationale": TEXT, "severity": TEXT, "rarity_basis": TEXT}))),
    }),
    "item": ({"logical_id": ID, "version": ID}, {"body": fact(TEXT), "contribution_ids": ids(entity("contribution"))}),
    "assignment": ({"item_id": ref("item"), "frame_id": ref("frame")}, {
        "class_id": fact(ID), "decision": fact(enum("admitted", "unclassified", "provisional", "disputed", "withheld")),
        "basis": fact(TEXT), "supersedes": fact(ref("assignment")),
    }),
    "validity": ({"item_id": ref("item"), "frame_id": ref("frame")}, {
        "verdict": fact(enum("valid", "invalid", "unresolved")), "rubric": fact(TEXT), "basis": fact(TEXT),
    }),
    "snapshot": ({"frame_id": ref("frame"), "members": ids(ref("item"))}, {
        "membership": fact(enum("complete", "partial", "unknown")), "selection_policy": fact(TEXT),
        "assignments": array(obj({"item_id": ref("item"), "assignment_id": ref("assignment")})),
        "validities": array(obj({"item_id": ref("item"), "validity_id": ref("validity")})),
        "excluded": array(obj({"item_id": ref("item"), "reason": TEXT})), "observed_at": fact(TIME),
        "tail_results": fact(array(obj({"class_id": ID, "evidence_ids": ids(EV)}))),
    }),
    "evidence": ({"scope_id": ref("scope")}, {
        "kind": fact(enum("declaration", "document", "execution_record", "observation_record", "human_consequence_record", "intervention_record", "proof_record", "analysis_record", "process_record", "simulation_record")),
        "producer_id": fact(entity()), "occurred_at": fact(TIME), "recorded_at": fact(TIME),
        "access": fact(enum("supplied", "referenced_only", "withheld", "unavailable")), "content": fact(TEXT), "locator": fact(TEXT),
        "subject_ids": ids(), "origin_ids": ids(), "transformation_ids": ids(), "contrary_ids": ids(CONTRARY), "uncertainty": fact(TEXT),
    }),
    "review": ({"target_id": ANY_REF, "criterion": enum(*CRITERIA), "scope_id": ref("scope")}, {
        "member_id": entity("contribution"), "target_event_id": ID, "request_id": ID, "disclosure_id": DISCLOSURE,
        "disclosure_ids": ids(DISCLOSURE), "assessor_id": fact(entity("actor")), "reviewed_at": fact(TIME),
        "method": fact(TEXT), "rationale": fact(TEXT), "verdict": fact(enum("supports", "contradicts", "unresolved")),
        "evidence_ids": ids(EV), "contrary_ids": ids(CONTRARY), "resolves": ids(CONTRARY),
        "decisive": fact(BOOL), "counterexample_ids": ids(),
    }),
    "relation": ({"scope_id": ref("scope"), "from_id": NODE, "to_id": NODE, "kind": enum(*RELATIONS)},
                 {"occurred_at": fact(TIME), "role": fact(TEXT)}),
    "frontier": ({"scope_id": ref("scope"), "node_id": NODE, "view": VIEW}, {"reason": fact(enum("unknown", "withheld", "missing_record", "disputed"))}),
    "independence": ({"scope_id": ref("scope"), "members": ids(NODE, 2), "form": enum("pairwise", "setwise"), "dimension": DIMENSION},
                     {"unexamined_dimensions": ids(DIMENSION), "method": fact(TEXT)}),
    "external_cohort": ({"scope_id": ref("scope"), "members": ids(entity("contribution"))}, {
        "membership": fact(enum("complete", "partial", "unknown")), "boundary": fact(TEXT), "checkpoint": fact(TEXT), "purpose": fact(TEXT),
        "externality_reviews": array(obj({"member_id": entity("contribution"), "review_id": ref("review")})),
        "qualifications": array(obj({"member_id": entity("contribution"), "review_id": ref("review")})), "carryover_ids": ids(entity("contribution")),
    }),
    "external_event": ({"scope_id": ref("scope"), "cohort_id": ref("external_cohort"), "member_id": entity("contribution"), "stage": enum("received", "retained", "selected", "used")}, {
        "verdict": fact(enum("yes", "no", "unknown")), "occurred_at": fact(TIME), "checkpoint": fact(TEXT),
        "purpose": fact(TEXT), "target_id": fact(NODE), "representation": fact(TEXT),
    }),
    "anomaly": ({"scope_id": ref("scope"), "frame_id": ref("frame")}, {
        "record": fact(EV), "context": fact(TEXT), "distinction": fact(TEXT),
        "disposition": fact(enum("unresolved", "investigated_no_change", "recut", "claim_restricted")),
        "revision_ids": ids(ref("revision")), "case_ids": ids(ref("correction_case")),
    }),
    "revision": ({"scope_id": ref("scope"), "from_frame": ref("frame"), "to_frame": ref("frame")}, {
        "kind": fact(enum("relabel", "recut")), "anomaly_ids": ids(ref("anomaly")), "changed_distinction": fact(TEXT),
        "class_map": array(obj({"from_class": ID, "to_class": ID})), "incorporation_evidence_ids": ids(EV),
        "new_assignment_ids": ids(ref("assignment")),
    }),
    "correction_case": ({"scope_id": ref("scope"), "claim_id": ref("claim")}, {
        "issue": fact(TEXT), "context": fact(enum("production", "drill")), "objective": fact(enum("repair", "restrict", "replace_evaluator", "withdraw")),
        "route": fact(ROUTE), "authority": fact(AUTHORITY), "handling": array(HANDLING), "attempts": array(ATTEMPT),
        "actions": array(ACTION), "outcomes": array(OUTCOME),
    }),
}

POPULATION = enum("selected", "confirmed_valid")
CASE_SELECTIONS = {"case_ids": ids(ref("correction_case")), "anomaly_ids": ids(ref("anomaly")), "revision_ids": ids(ref("revision"))}
REQUEST_FIELDS = {
    "lint": ({"claim_id": ref("claim")}, {}),
    "profile": ({"snapshot_id": ref("snapshot")}, {"population": POPULATION}),
    "compare": ({"before_id": ref("snapshot"), "after_id": ref("snapshot"), "mode": enum("descriptive", "matched")}, {
        "population": POPULATION, "revision_id": ref("revision"),
        "pairs": array(obj({"before_item_id": ref("item"), "after_item_id": ref("item"), "basis": TEXT})),
        "pair_membership": fact(enum("complete", "partial", "unknown")),
    }),
    "lineage": ({"seed_ids": ids(NODE, 2), "view": VIEW}, {"independence_ids": ids(ref("independence"))}),
    "external": ({"cohort_id": ref("external_cohort")}, {}),
    "cases": ({}, CASE_SELECTIONS),
    "assess": ({"claim_id": ref("claim")}, {"conditions": ids(CONDITION), "snapshot_id": ref("snapshot"), "cohort_id": ref("external_cohort"), **CASE_SELECTIONS}),
}
