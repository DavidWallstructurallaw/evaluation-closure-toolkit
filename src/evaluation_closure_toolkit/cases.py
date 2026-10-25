"""Anomaly preservation, revision uptake and objective-bound correction records."""

from .budget import RequestBudget
from .checks import add_premises, check, merge, receipts
from .evidence import evaluate_reviews, fact_reason, known, make_review_index
from .provenance import fact_state, finding, known_reasons, restrict_support, result_shell
from .structural import _assignment, available, unavailable

EVENT_KINDS = frozenset({"process_record", "observation_record", "intervention_record", "execution_record"})
SELECTIONS = {"anomalies": ("anomaly", "anomaly_ids"),
              "revisions": ("revision", "revision_ids"),
              "corrections": ("correction_case", "case_ids")}


def selected_records(records, request, kind, field):
    identities = request.get(field)
    if identities is None:
        identities = [r["id"] for r in records.values()
                      if r["type"] == kind and r["scope_id"] == request["scope_id"]]
    return [records[i] for i in sorted(identities)]


class CaseAudit:
    def __init__(self, dossier, request, budget):
        self.records = {r["id"]: r for r in dossier["records"]}
        self.request, self.budget = request, budget
        self.scope_id = request["scope_id"]
        self.index = make_review_index(self.records)

    def documentary(self, record, fields, evidence_ids=None, *, kinds=EVENT_KINDS,
                    subjects=None, resolved=()):
        result = receipts(self.records, record.get("evidence_ids", []) if evidence_ids is None else evidence_ids,
                          self.scope_id, self.budget, subjects=subjects or [record["id"]],
                          kinds=kinds, resolved=resolved)
        reasons = known_reasons(record, fields)
        reasons |= add_premises(result, self.records, [record["id"]], self.budget)
        restrict_support(result, reasons)
        return result

    def anomaly(self, row):
        identity = known(row, "record")
        preservation = self.documentary(row, ("record", "context", "distinction"),
                                        [identity] if identity else [],
                                        kinds={"document", "observation_record", "execution_record", "process_record"})
        preservation["dependency_ids"] = sorted(set(preservation["dependency_ids"]) | {row["frame_id"]})
        disposition = check(known_reasons(row, ("disposition",)), dependencies=[row["id"]])
        reasons = set()
        if known(row, "disposition") == "recut":
            if not any(self.records[r]["from_frame"] == row["frame_id"]
                       and self.records[r]["scope_id"] == self.scope_id for r in row.get("revision_ids", [])):
                reasons.add("missing_record")
        if known(row, "disposition") == "claim_restricted":
            if not any(known(self.records[c], "objective") == "restrict"
                       and self.records[c]["scope_id"] == self.scope_id for c in row.get("case_ids", [])):
                reasons.add("missing_record")
        restrict_support(disposition, reasons)
        return {"anomaly_id": row["id"], "frame_id": row["frame_id"],
                "disposition": known(row, "disposition") or "unestablished",
                "disposition_state": fact_state(row, "disposition"),
                "revision_ids": sorted(row.get("revision_ids", [])), "case_ids": sorted(row.get("case_ids", [])),
                "preservation": preservation, "disposition_check": disposition}

    def revision(self, row):
        frames = [self.records[row[field]] for field in ("from_frame", "to_frame")]
        documented = self.documentary(row, ("kind", "changed_distinction"), kinds={"document", "process_record", "analysis_record"})
        reasons = set()
        for frame in frames:
            reasons |= known_reasons(frame, ("classes", "task", "context", "horizon", "resolution", "exclusions"))
        reasons |= add_premises(documented, self.records, [f["id"] for f in frames], self.budget)
        for identity in sorted(row.get("anomaly_ids", [])):
            self.budget.charge()
            anomaly = self.records[identity]
            if anomaly["scope_id"] != self.scope_id or anomaly["frame_id"] != row["from_frame"]:
                reasons.add("scope_mismatch")
            detail = self.anomaly(anomaly)
            merge(documented, detail["preservation"], detail["disposition_check"])
            if detail["preservation"]["assessment"] != "supported_under_scope":
                reasons.update(detail["preservation"]["reason_codes"])
        restrict_support(documented, reasons)
        # Names alone are not a new partition. Class-map cardinality and the
        # represented definitions/features distinguish a declared changed cut.
        old = {r["id"]: r["definition"] for r in known(frames[0], "classes") or []}
        new = {r["id"]: r["definition"] for r in known(frames[1], "classes") or []}
        mapping = row.get("class_map", [])
        self.budget.charge(len(mapping) + len(old) + len(new))
        changed = (len(old) != len(new) or sorted(old.values()) != sorted(new.values())
                   or any(known(frames[0], f) != known(frames[1], f)
                          for f in ("task", "context", "horizon", "resolution", "exclusions", "features")))
        complete_map = (bool(mapping) and {r["from_class"] for r in mapping} == set(old)
                        and {r["to_class"] for r in mapping} == set(new))
        cut = ("recut_documented" if known(row, "kind") == "recut" and changed
               and complete_map and documented["assessment"] == "supported_under_scope"
               else "relabel_only" if not changed and old and new else "unestablished")
        incorporated = self.documentary(row, (), row.get("incorporation_evidence_ids", []),
                                       kinds={"process_record", "execution_record", "analysis_record"})
        if documented["assessment"] != "supported_under_scope":
            restrict_support(incorporated, ["prerequisite_unavailable"])
        assignments, assigned_items = [], set()
        for identity in sorted(row.get("new_assignment_ids", [])):
            self.budget.charge()
            assignment = self.records[identity]
            if assignment["item_id"] in assigned_items:
                restrict_support(incorporated, ["unresolved_assignment"])
            assigned_items.add(assignment["item_id"])
            dependencies = set()
            detail, support, contrary = _assignment(assignment["item_id"], identity, frames[1],
                                                   set(new) if known(frames[1], "classes") is not None else None,
                                                   self.records, self.scope_id, self.index, dependencies, self.budget)
            assignments.append(identity)
            merge(incorporated, check(detail["reason_codes"], dependencies=dependencies,
                                     support=support, contrary=contrary))
            if detail["primary_reason"] != "admitted":
                restrict_support(incorporated, ["unresolved_assignment"])
        if not assignments:
            restrict_support(incorporated, ["missing_record"])
        fidelity = evaluate_reviews(self.records, row["id"], "structural_revision", self.scope_id,
                                    required_kinds={"analysis_record"}, required_subjects=[row["id"], *[f["id"] for f in frames]],
                                    review_index=self.index, budget=self.budget)
        if cut != "recut_documented" or incorporated["assessment"] != "supported_under_scope":
            restrict_support(fidelity, ["prerequisite_unavailable"])
        merge(fidelity, documented, incorporated, check(dependencies=[row["id"], *assignments]))
        return {"revision_id": row["id"], "from_frame": row["from_frame"], "to_frame": row["to_frame"],
                "kind": known(row, "kind") or "unestablished", "kind_state": fact_state(row, "kind"),
                "cut_state": cut, "anomaly_ids": sorted(row.get("anomaly_ids", [])), "assignment_ids": assignments,
                "documented": documented, "incorporated": incorporated, "fidelity": fidelity}

    def correction(self, case, publish):
        identity = case["id"]
        row = {"case_id": identity, "claim_id": case["claim_id"],
               "context": known(case, "context") or "unestablished", "context_state": fact_state(case, "context"),
               "objective": known(case, "objective") or "unestablished", "objective_state": fact_state(case, "objective"),
               "route": {}, "authority": {}, "handling": [], "attempts": [], "actions": [], "outcomes": [],
               "capacity": {}, "capacity_extent": "tested_route", "completed": False}
        publish(row)
        route, authority = known(case, "route"), known(case, "authority")
        for field, value in (("route", route), ("authority", authority)):
            row[field] = self.documentary(case, (field, "issue", "context", "objective"),
                                          value["evidence_ids"] if value else [],
                                          kinds={"document", "process_record", "intervention_record"})
        if route and authority and any(route[f] != authority[f] for f in ("actor_id", "target_id")):
            restrict_support(row["authority"], ["scope_mismatch"])
        attempts = {}
        for field, required in (("handling", ("state", "occurred_at")),
                                ("attempts", ("actor_id", "target_id", "occurred_at"))):
            for event in sorted(case.get(field, []), key=lambda r: r["id"]):
                self.budget.charge()
                detail = receipts(self.records, event["evidence_ids"], self.scope_id, self.budget,
                                  subjects=[identity], kinds=EVENT_KINDS)
                restrict_support(detail, known_reasons(event, required))
                event_row = {"event_id": event["id"], "check": detail}
                if field == "handling":
                    event_row["state"] = known(event, "state") or "unestablished"
                else:
                    event_row.update(actor_ids=[known(event, "actor_id")] if known(event, "actor_id") else [],
                                     target_ids=[known(event, "target_id")] if known(event, "target_id") else [])
                    attempts[event["id"]] = (event, detail)
                row[field].append(event_row)
        actions = {}
        for event in sorted(case.get("actions", []), key=lambda r: r["id"]):
            self.budget.charge()
            attempt, attempted = attempts[event["attempt_id"]]
            detail = receipts(self.records, event["evidence_ids"], self.scope_id, self.budget,
                              subjects=[identity], kinds=EVENT_KINDS)
            reasons = known_reasons(event, ("kind", "target_id", "occurred_at", "resulting_state"))
            if attempted["assessment"] != "supported_under_scope":
                reasons.update(attempted["reason_codes"] or ["prerequisite_unavailable"])
            if known(attempt, "target_id") != known(event, "target_id"):
                reasons.add("scope_mismatch")
            start, end = known(attempt, "occurred_at"), known(event, "occurred_at")
            if start and end and start > end:
                reasons.add("scope_mismatch")
            restrict_support(detail, reasons)
            authorization = check(dependencies=[identity, event["id"], attempt["id"]])
            for premise in (detail, row["route"], row["authority"]):
                merge(authorization, premise)
                if premise["assessment"] != "supported_under_scope":
                    restrict_support(authorization, premise["reason_codes"] or ["prerequisite_unavailable"])
            if route and authority:
                if (known(attempt, "actor_id") != authority["actor_id"]
                        or known(event, "target_id") != authority["target_id"]
                        or not start or not end or not authority["start"] <= end < authority["end"]):
                    restrict_support(authorization, ["scope_mismatch"])
            row["actions"].append({"event_id": event["id"], "attempt_id": event["attempt_id"],
                                   "kind": known(event, "kind") or "unestablished",
                                   "target_ids": [known(event, "target_id")] if known(event, "target_id") else [],
                                   "check": detail, "authorization": authorization})
            actions[event["id"]] = (event, detail)
        for event in sorted(case.get("outcomes", []), key=lambda r: r["id"]):
            self.budget.charge()
            action, acted = actions[event["action_id"]]
            review = evaluate_reviews(self.records, identity, "correction_outcome", self.scope_id,
                                      target_event_id=event["id"], extra_contrary=event.get("contrary_ids", []),
                                      required_subjects=[identity], review_index=self.index, budget=self.budget)
            reasons = known_reasons(event, ("criterion", "protocol", "horizon", "assessed_at", "result", "review_id"))
            reasons |= known_reasons(case, ("objective",))
            selected_review = known(event, "review_id")
            if selected_review:
                chosen = next(r for r in review["values"]["reviews"] if r["review_id"] == selected_review)
                if not chosen["selected"] or not chosen["resolved"] and (not chosen["qualified"] or chosen["verdict"] != "supports"):
                    reasons.update(chosen["reason_codes"] or ["prerequisite_unavailable"])
            if acted["assessment"] != "supported_under_scope":
                reasons.update(acted["reason_codes"] or ["prerequisite_unavailable"])
            if known(action, "kind") != known(case, "objective"):
                reasons.add("scope_mismatch")
            time, acted_at = known(event, "assessed_at"), known(action, "occurred_at")
            if time and acted_at and time < acted_at:
                reasons.add("scope_mismatch")
            if known(event, "result") == "unresolved":
                reasons.add("unknown_value")
            evidence = receipts(self.records, event["evidence_ids"], self.scope_id, self.budget,
                                subjects=[identity], kinds=EVENT_KINDS | {"analysis_record"},
                                resolved=review["values"]["resolved_ids"])
            reasons.update(evidence["reason_codes"])
            merge(review, evidence, acted)
            if known(case, "objective") == "repair":
                baseline_id = known(event, "baseline")
                if baseline_id:
                    baseline = receipts(self.records, [baseline_id], self.scope_id, self.budget,
                                        subjects=[identity], kinds=EVENT_KINDS,
                                        resolved=review["values"]["resolved_ids"])
                    reasons.update(baseline["reason_codes"])
                    merge(review, baseline)
                else:
                    reasons.add(fact_reason(event, "baseline"))
            restrict_support(review, reasons)
            row["outcomes"].append({"event_id": event["id"], "action_id": event["action_id"],
                                    "objective": row["objective"], "result": known(event, "result") or "unestablished",
                                    "review": review})
        capacity = evaluate_reviews(self.records, case["claim_id"], "route_operability", self.scope_id,
                                    required_subjects=[identity], required_kinds={"process_record"},
                                    review_index=self.index, budget=self.budget)
        if not any(action["authorization"]["assessment"] == "supported_under_scope" for action in row["actions"]):
            restrict_support(capacity, ["prerequisite_unavailable"])
        row["capacity"], row["completed"] = capacity, True


def cases_request(dossier, request, *, budget=None):
    budget = budget or RequestBudget()
    audit = CaseAudit(dossier, request, budget)
    values = {"anomalies": [], "revisions": [], "corrections": [], "accounting_complete": False,
              "case_target_pairs": [], "pair_counts": {}, "event_counts": {}}
    for stage in ("handling", "attempts", "actions", "outcomes"):
        values["event_counts"][stage] = unavailable("resource_limit")
    for stage in ("attempted", "acted", "authorized", "effective"):
        values["pair_counts"][stage] = unavailable("resource_limit")
    result = result_shell(request, values, [
        "Anomaly preservation, declared revision, incorporation and reviewed fidelity are separate checks.",
        "Handling does not imply an attempt, action or remedy. Outcome reviews qualify their stated objective and effective/ineffective result only.",
        "Unknown authority blocks authorized capacity without erasing a qualified outcome. Drill context is retained and supplies no production resolution.",
        "Pair counts are unique case/target pairs; event counts retain every supplied selected event. Tested routes do not establish sustained capacity.",
    ])
    budget.partial_result, budget.partial_findings = result, []
    try:
        budget.charge(len(audit.records))
        for key, (kind, field) in SELECTIONS.items():
            for record in selected_records(audit.records, request, kind, field):
                budget.charge()
                if key == "corrections":
                    audit.correction(record, values[key].append)
                else:
                    values[key].append(getattr(audit, kind)(record))
        pairs = {}
        for case in values["corrections"]:
            effective_actions = set()
            for outcome in case["outcomes"]:
                budget.charge()
                if outcome["result"] == "effective" and outcome["review"]["assessment"] == "supported_under_scope":
                    effective_actions.add(outcome["action_id"])
            for event in case["attempts"]:
                budget.charge()
                if event["target_ids"] and event["check"]["assessment"] == "supported_under_scope":
                    pairs.setdefault((case["case_id"], event["target_ids"][0]), set()).add("attempted")
            for event in case["actions"]:
                budget.charge()
                if not event["target_ids"]:
                    continue
                states = pairs.setdefault((case["case_id"], event["target_ids"][0]), set())
                if event["check"]["assessment"] == "supported_under_scope":
                    states.add("acted")
                if event["authorization"]["assessment"] == "supported_under_scope":
                    states.add("authorized")
                if event["event_id"] in effective_actions:
                    states.add("effective")
        values["case_target_pairs"] = [{"case_id": case, "target_id": target, "states": sorted(states)}
                                        for (case, target), states in sorted(pairs.items())]
        values["pair_counts"] = {stage: available(sum(stage in states for states in pairs.values()))
                                 for stage in values["pair_counts"]}
        values["event_counts"] = {stage: available(sum(len(c[stage]) for c in values["corrections"]))
                                  for stage in values["event_counts"]}
        values["accounting_complete"] = True
        result["execution"], result["reason_codes"] = "completed", []
    finally:
        # Recursively collect only completed subresults, including an interrupted
        # case's earlier actions/outcomes. Never publish totals for a prefix.
        def collect(value):
            if isinstance(value, dict):
                if "assessment" in value:
                    merge(result, value)
                else:
                    for child in value.values():
                        collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)
        collect(values)
        result["basis"] = [{"kind": "local_deduction", "record_ids": result["dependency_ids"]}]
        findings = [finding(result, family, rule, [r[key] for r in values[section]], result["reason_codes"],
                            "Inspect the separate documentary checks and exact scoped reviews before drawing a dependent conclusion.")
                    for section, key, family, rule in (("anomalies", "anomaly_id", "EC105", "anomaly_accounting"),
                                                       ("revisions", "revision_id", "EC105", "revision_uptake"),
                                                       ("corrections", "case_id", "EC106", "correction_accounting")) if values[section]]
        budget.partial_findings = findings
    return result, findings
