"""Synthetic supplied premises. Expected judgments are literal test assertions."""

from copy import deepcopy

from provenance_helpers import entity, known, record, gap


def evidence(identity, kind="analysis_record", subjects=(), **kwargs):
    return {"id": identity, "type": "evidence", "scope_id": "scope", "kind": known(kind),
            "producer_id": known("actor"), "access": known("supplied"),
            "content": known("Synthetic receipt for the explicitly anchored finite inquiry."),
            "subject_ids": list(subjects), **kwargs}


def review(identity, criterion, evidence_ids, target="claim", **kwargs):
    return {"id": identity, "type": "review", "target_id": target, "criterion": criterion,
            "scope_id": "scope", "assessor_id": known("actor"), "reviewed_at": known("2026-10-05T12:00:00Z"),
            "method": known("Inspect the supplied typed records and exact subject inventory."),
            "rationale": known("Supports only the declared horizon, objective, boundary and supplied inventory; unexamined history remains unknown."),
            "verdict": known("supports"), "evidence_ids": list(evidence_ids), **kwargs}


def supported():
    records = [entity("process", "process"), entity("actor", "actor"), entity("model", "model"),
               entity("reference"), entity("judge", "model"), entity("source"), entity("z", "contribution")]
    records.extend([
        {"id": "scope", "type": "scope", "process_id": "process", "claim_id": "claim", "frame_id": "frame",
         "snapshot_ids": ["snapshot"], "dimension": known("acquisition"),
         "window": known({"start": "2026-10-01T00:00:00Z", "end": "2026-11-01T00:00:00Z"})},
        {"id": "claim", "type": "claim", "scope_id": "scope", "profile": "open_evaluation",
         "statement": known("Open evaluation of these two finite synthetic items under the supplied five conditions."),
         "intended_use": known("Bounded synthetic evaluation"), "horizon": known("The declared October window"),
         "frame_id": known("frame"), "requirements": known(["single_turn"]), "validation_kind": known("execution"),
         "valid_until": known("2026-11-01T00:00:00Z"), "capacity_extent": known("tested_route")},
        {"id": "frame", "type": "frame", **{f: known("Bounded synthetic " + f) for f in
          ("task", "context", "horizon", "resolution", "exclusions", "validity_rubric", "admission_policy", "selection_policy")},
         "features": known(["single_turn"]), "classes": known([{"id": "usual", "definition": "Usual finite cases"},
                                                                {"id": "rare", "definition": "Rare finite cases"}]),
         "tail_designations": known([{"class_id": "rare", "rationale": "Rare but relevant failure condition",
                                       "severity": "Severe within this finite use", "rarity_basis": "Supplied finite roster"}])},
        {"id": "snapshot", "type": "snapshot", "frame_id": "frame", "members": ["item-a", "item-b"],
         "membership": known("complete"), "selection_policy": known("Two fixed items"),
         "observed_at": known("2026-10-04T00:00:00Z"),
         "assignments": [{"item_id": "item-a", "assignment_id": "assignment-a"}, {"item_id": "item-b", "assignment_id": "assignment-b"}],
         "tail_results": known([{"class_id": "rare", "evidence_ids": ["tail-receipt"]}])},
    ])
    for suffix, class_id in (("a", "usual"), ("b", "rare")):
        records.extend([
            {"id": "item-" + suffix, "type": "item", "logical_id": "item-" + suffix, "version": "v1", "body": known("Toy item " + suffix)},
            {"id": "assignment-" + suffix, "type": "assignment", "item_id": "item-" + suffix, "frame_id": "frame",
             "class_id": known(class_id), "decision": known("admitted"), "basis": known("Supplied class meaning"), "asserted_by": known("actor")},
            {"id": "origin-" + suffix, "type": "relation", "scope_id": "scope", "from_id": "item-" + suffix,
             "to_id": "source", "kind": "acquired_from", "asserted_by": known("actor")},
        ])
    for role, target in (("generation", "model"), ("reference", "reference"), ("judgment", "judge")):
        records.append({"id": "role-" + role, "type": "relation", "scope_id": "scope", "from_id": "process",
                        "to_id": target, "kind": "uses_" + role, "role": known("Declared " + role + " role"), "asserted_by": known("actor")})
    records.append(evidence("tail-receipt", "execution_record", ["snapshot", "item-b"],
                            content=known("The rare-class model failure remains visible in the supplied result.")))
    records.append({"id": "cohort", "type": "external_cohort", "scope_id": "scope", "members": ["z"],
                    "membership": known("complete"), "boundary": known("Outside the declared process"),
                    "checkpoint": known("captured-october"), "purpose": known("Bounded synthetic evaluation"),
                    "externality_reviews": [{"member_id": "z", "review_id": "external-z"}],
                    "qualifications": [{"member_id": "z", "review_id": "qualification-z"}]})
    for name, criterion in (("external-z", "externality"), ("qualification-z", "input_qualification")):
        records.extend([evidence(name + "-receipt", subjects=["cohort", "z"]),
                        review(name, criterion, [name + "-receipt"], target="cohort", member_id="z")])
    for stage in ("received", "used"):
        records.extend([evidence("z-" + stage + "-receipt", "process_record", ["z", "z-" + stage]),
                        {"id": "z-" + stage, "type": "external_event", "scope_id": "scope", "cohort_id": "cohort",
                         "member_id": "z", "stage": stage, "verdict": known("yes"), "occurred_at": known("2026-10-03T00:00:00Z"),
                         "checkpoint": known("captured-october"), "purpose": known("Bounded synthetic evaluation"),
                         "target_id": known("process"), "asserted_by": known("actor"), "evidence_ids": ["z-" + stage + "-receipt"]}])
    case = {"id": "case", "type": "correction_case", "scope_id": "scope", "claim_id": "claim",
            "issue": known("Finite issue"), "context": known("drill"), "objective": known("restrict"),
            "route": known({"actor_id": "actor", "target_id": "process", "procedure": "Invoke bounded restriction", "evidence_ids": ["route-receipt"]}),
            "authority": known({"actor_id": "actor", "target_id": "process", "start": "2026-10-01T00:00:00Z",
                                "end": "2026-11-01T00:00:00Z", "evidence_ids": ["authority-receipt"]}),
            "handling": [{"id": "accepted", "state": known("accepted"), "occurred_at": known("2026-10-02T00:00:00Z"), "evidence_ids": ["handling-receipt"]}],
            "attempts": [{"id": "attempt", "actor_id": known("actor"), "target_id": known("process"),
                          "occurred_at": known("2026-10-03T00:00:00Z"), "evidence_ids": ["attempt-receipt"]}],
            "actions": [{"id": "action", "attempt_id": "attempt", "kind": known("restrict"), "target_id": known("process"),
                         "occurred_at": known("2026-10-03T01:00:00Z"), "resulting_state": known("Restricted for the declared use"), "evidence_ids": ["action-receipt"]}],
            "outcomes": [{"id": "outcome", "action_id": "action", "criterion": known("Restriction applies"),
                          "protocol": known("Inspect the resulting objective state"), "horizon": known("Declared drill observation"),
                          "assessed_at": known("2026-10-04T00:00:00Z"), "result": known("effective"),
                          "review_id": known("outcome-review"), "evidence_ids": ["outcome-receipt"]}]}
    records.append(case)
    for name in ("route", "authority", "handling", "attempt", "action", "outcome"):
        records.append(evidence(name + "-receipt", "process_record", ["case", "process"]))
    records.append(review("outcome-review", "correction_outcome", ["outcome-receipt"], target="case", target_event_id="outcome"))
    criteria = (
        "frame_target_fidelity", "anomaly_accountability", "outside_process_contact", "claim_relevance", "recorded_use",
        "provenance_transformations", "validation_type_fit", "evaluator_relationships", "tail_designation_adequacy",
        "tail_representation", "tail_result_visibility", "route_and_authority", "route_operability", "capacity_extent")
    subjects = ["claim", "scope", "frame", "snapshot", "cohort", "z", "z-used", "process", "case",
                "origin-a", "origin-b", "role-generation", "role-reference", "role-judgment"]
    for criterion in criteria:
        kind = {"validation_type_fit": "execution_record", "tail_result_visibility": "execution_record",
                "recorded_use": "process_record", "route_operability": "process_record"}.get(criterion, "analysis_record")
        receipt = evidence("receipt-" + criterion, kind, subjects)
        if criterion in {"provenance_transformations", "evaluator_relationships"}:
            receipt.update(origin_ids=["source"], transformation_ids=[],
                           uncertainty=known("Generator, reference and judge acquisition is examined; other ancestry/dimensions remain unexamined."))
        records.extend([receipt, review("review-" + criterion, criterion, [receipt["id"]])])
    return {"schema": "ect-dossier/0.1", "id": "demo-supported-open-evaluation", "analysis_time": "2026-10-06T00:00:00Z",
            "policy": "ect-core/0.1", "records": records,
            "requests": [{"id": "assess-main", "operation": "assess", "scope_id": "scope", "claim_id": "claim", "snapshot_id": "snapshot", "cohort_id": "cohort"}]}


def cases_demo():
    dossier = supported()
    dossier["id"] = "demo-correction-cases"
    record(dossier, "case")["authority"] = gap()
    ticket = deepcopy(record(dossier, "case"))
    ticket.update(id="ticket-only", attempts=[], actions=[], outcomes=[])
    ticket["handling"][0]["id"] = "ticket-accepted"
    ticket["handling"][0]["evidence_ids"] = ["ticket-receipt"]
    dossier["records"].extend([ticket, entity("newer-version"), evidence("ticket-receipt", "process_record", ["ticket-only"])])
    dossier["requests"] = [{"id": "cases-main", "operation": "cases", "scope_id": "scope"}]
    return dossier


def revision_demo():
    dossier = supported()
    dossier["id"] = "demo-revision-accountability"
    for suffix, changed in (("recut", True), ("rename", False)):
        frame = deepcopy(record(dossier, "frame"))
        frame["id"] = "frame-" + suffix
        if changed:
            frame["classes"]["value"][1]["definition"] = "Rare cases with newly represented recovery distinction"
        anomaly = {"id": "anomaly-" + suffix, "type": "anomaly", "scope_id": "scope", "frame_id": "frame",
                   "record": known("anomaly-" + suffix + "-receipt"), "context": known("Supplied finite anomaly context"),
                   "distinction": known("Recovery distinctions were examined"), "disposition": known("recut" if changed else "investigated_no_change"),
                   "revision_ids": ["revision-" + suffix]}
        revision = {"id": "revision-" + suffix, "type": "revision", "scope_id": "scope", "from_frame": "frame", "to_frame": frame["id"],
                    "kind": known("recut" if changed else "relabel"), "changed_distinction": known("Supplied represented distinction or label change"),
                    "anomaly_ids": [anomaly["id"]], "class_map": [{"from_class": "usual", "to_class": "usual"}, {"from_class": "rare", "to_class": "rare"}],
                    "evidence_ids": ["revision-" + suffix + "-receipt"], "incorporation_evidence_ids": ["incorporation-" + suffix],
                    "new_assignment_ids": ["assignment-" + suffix]}
        assignment = deepcopy(record(dossier, "assignment-b"))
        assignment.update(id="assignment-" + suffix, frame_id=frame["id"])
        dossier["records"].extend([frame, anomaly, revision, assignment,
            evidence("anomaly-" + suffix + "-receipt", "observation_record", [anomaly["id"]]),
            evidence("revision-" + suffix + "-receipt", "process_record", [revision["id"]]),
            evidence("incorporation-" + suffix, "analysis_record", [revision["id"]]),
            evidence("fidelity-" + suffix + "-receipt", "analysis_record", [revision["id"], "frame", frame["id"]]),
            review("fidelity-" + suffix, "structural_revision", ["fidelity-" + suffix + "-receipt"], target=revision["id"])])
    dossier["requests"] = [{"id": "cases-main", "operation": "cases", "scope_id": "scope", "case_ids": []}]
    return dossier
