"""Five fixed evidence gates over finite supplied scope, without scalar scores."""

from .budget import RequestBudget, WorkLimit
from .cases import cases_request
from .checks import add_premises, check, merge, receipts
from .evidence import evaluate_reviews, fact_reason, known, make_review_index
from .external import external_request
from .lineage import lineage_request
from .lint import VALIDATION_KINDS, lint_claim
from .provenance import finding, known_reasons, restrict_support, result_shell
from .structural import profile_request

GATES = {
    "structural_validity": ("frame_target_fidelity", "anomaly_accountability"),
    "external_presence": ("outside_process_contact", "claim_relevance", "recorded_use"),
    "source_integrity": ("provenance_transformations", "validation_type_fit", "evaluator_relationships"),
    "tail_retention": ("tail_designation_adequacy", "tail_representation", "tail_result_visibility"),
    "corrective_capacity": ("route_and_authority", "route_operability", "capacity_extent"),
}
FAMILIES = {"structural_validity": "EC102", "external_presence": "EC103", "source_integrity": "EC107",
            "tail_retention": "EC104", "corrective_capacity": "EC106"}


def _pending(selected):
    result = check(["resource_limit" if selected else "unselected"], assessed=False)
    result["selection"] = "selected" if selected else "not_selected"
    return result


class Assessment:
    def __init__(self, dossier, request, budget):
        self.dossier, self.request, self.budget = dossier, request, budget
        self.records = {r["id"]: r for r in dossier["records"]}
        self.index = make_review_index(self.records)
        self.claim = self.records[request["claim_id"]]
        self.scope = self.records[request["scope_id"]]
        self.frame = self.records.get(known(self.claim, "frame_id"), {})
        self.findings = []
        narrow = self.claim["profile"] == "narrow_regression"
        selected = set(request.get("conditions", GATES)) if not narrow else set()
        values = {"claim_id": self.claim["id"], "currentness": "unestablished", "conditions": [],
                  "conclusion": "not_assessed", "capacity_extent": known(self.claim, "capacity_extent") or "unestablished",
                  "open_evaluation": "not_applicable" if narrow else "not_assessed", "prerequisites": [],
                  "claim_check": _pending(True)}
        if not narrow:
            for gate, criteria in GATES.items():
                row = _pending(gate in selected)
                row["values"] = {"criteria": [{"criterion": name, **_pending(gate in selected)} for name in criteria]}
                values["conditions"].append({"condition": gate, **row})
        self.result = result_shell(request, values, [
            "Supported under the declared scope, supplied evidence and ect-core/0.1 policy.",
            "Every selected fixed criterion requires its own scoped review and typed documentary witnesses; unselected conditions remain not assessed.",
            "Captured anomaly, source, tail and case inventories are bounded supplied views. Review rationale attests their adequacy; text is not independently interpreted or authenticated.",
            "Tested corrective routes retain drill/production context. Sustained capacity requires additional dated history and objective/horizon review.",
        ])
        self.values = values
        budget.partial_result, budget.partial_findings = self.result, self.findings
        self.cache = {}

    def prerequisite(self, key, operation, function, **selection):
        if key in self.cache:
            return self.cache[key]
        request = {"id": self.request["id"], "operation": operation, "scope_id": self.scope["id"], **selection}
        parent = self.result
        child = None
        self.budget.partial_result, self.budget.partial_findings = None, []
        try:
            child, findings = function(self.dossier, request, budget=self.budget)
            self.findings.extend(findings)
            return child
        except WorkLimit:
            child = self.budget.partial_result
            if child is not None:
                progress = self.budget.profile_progress
                if progress and (progress["member_reasons"] or progress["validity_members"]):
                    child["values"]["partial_profiles"] = [{k: progress[k] for k in (
                        "snapshot_id", "frame_id", "population", "member_reasons", "validity_members")}
                        | {"reason_codes": ["resource_limit"]}]
                    for field in ("dependency_ids", "support_ids", "contrary_ids"):
                        child[field] = sorted(set(child[field]) | set(progress[field]))
                self.findings.extend(self.budget.partial_findings)
            raise
        finally:
            if child is not None:
                self.values["prerequisites"].append({"role": key, "result": child})
                self.cache[key] = child
                merge(parent, child)
            self.budget.profile_progress = None
            self.budget.partial_result, self.budget.partial_findings = parent, self.findings

    def profile(self):
        snapshot_id = self.request.get("snapshot_id")
        if snapshot_id is None:
            return None
        result = self.prerequisite("structural", "profile", profile_request, snapshot_id=snapshot_id)
        return result["values"]["profiles"][0]

    def cases(self):
        selection = {k: self.request[k] for k in ("case_ids", "anomaly_ids", "revision_ids") if k in self.request}
        return self.prerequisite("cases", "cases", cases_request, **selection)["values"]

    def review(self, criterion, *, subjects=(), groups=(), kinds=("analysis_record",), forbidden=()):
        return evaluate_reviews(self.records, self.claim["id"], criterion, self.scope["id"],
                                required_kinds=kinds, required_subjects=[self.claim["id"], *subjects],
                                subject_groups=groups, forbidden_subjects=forbidden,
                                review_index=self.index, budget=self.budget)

    def finish_criterion(self, review, reasons, identities=(), children=()):
        reasons = set(reasons) | add_premises(review, self.records, identities, self.budget)
        for child in children:
            merge(review, child)
            if child["assessment"] != "supported_under_scope":
                reasons.update(child["reason_codes"] or ["prerequisite_unavailable"])
        restrict_support(review, reasons)
        return review

    def structural(self, criterion):
        profile = self.profile()
        reasons = known_reasons(self.frame, ("task", "context", "horizon", "resolution", "exclusions", "classes", "features"))
        reasons |= known_reasons(self.claim, ("frame_id", "requirements"))
        frame_ids = [self.frame["id"]] if self.frame else []
        if profile is None:
            reasons.add("missing_record")
        elif profile["frame_id"] != self.frame.get("id"):
            reasons.add("scope_mismatch")
        if criterion == "frame_target_fidelity":
            result = self.review(criterion, subjects=frame_ids)
            required, features = known(self.claim, "requirements"), known(self.frame, "features")
            mismatch = required is not None and features is not None and bool(set(required) - set(features))
            premise_reasons = add_premises(result, self.records, [self.claim["id"], *frame_ids], self.budget)
            result = self.finish_criterion(result, reasons | premise_reasons)
            # This direct counterexample is independent of favorable review text.
            if mismatch and not premise_reasons:
                result["assessment"] = "contradicted_under_scope"
                result["reason_codes"] = sorted(set(result["reason_codes"]) | {"scope_mismatch"})
                result["basis"].append({"kind": "local_deduction", "record_ids": sorted([self.claim["id"], *frame_ids])})
            return result
        cases = self.cases()
        self.budget.charge(len(self.records))
        inventory = sorted(r["id"] for r in self.records.values() if r["type"] == "anomaly"
                           and r["scope_id"] == self.scope["id"])
        selected = {r["anomaly_id"]: r for r in cases["anomalies"]}
        if not set(inventory) <= set(selected):
            reasons.add("unselected")
        result = self.review(criterion, subjects=[*frame_ids, *inventory])
        children = [selected[i][k] for i in inventory if i in selected for k in ("preservation", "disposition_check")]
        return self.finish_criterion(result, reasons, [*frame_ids, *inventory], children)

    def external(self, criterion):
        cohort_id = self.request.get("cohort_id")
        if cohort_id is None:
            return self.finish_criterion(self.review(criterion), ["missing_record"])
        external = self.prerequisite("external", "external", external_request, cohort_id=cohort_id)["values"]
        cohort = self.records[cohort_id]
        reasons = known_reasons(cohort, ("boundary", "purpose")) | known_reasons(self.scope, ("window",))
        contacts = [m for m in external["member_states"] if m["contact_state"] == "documented_current_contact"]
        if not contacts:
            reasons.add("prerequisite_unavailable" if cohort["members"] else "empty_population")
        groups = []
        for member in contacts:
            self.budget.charge()
            used = [e for e in member["stages"]["used"]["events"] if e["qualified"] and e["verdict"] == "yes"]
            if criterion == "outside_process_contact":
                groups.append([member["member_id"]])
            else:
                for event in used:
                    self.budget.charge()
                    groups.append([member["member_id"], *event["target_ids"],
                                   *([event["event_id"]] if criterion == "recorded_use" else [])])
        # Explicit member anchors describe a bounded known subset. A receipt
        # claiming the whole cohort cannot upgrade incomplete membership.
        partial = external["count_scope"] == "known_subset"
        result = self.review(criterion, subjects=[] if partial else [cohort_id], groups=groups,
                             kinds={"process_record"} if criterion == "recorded_use" else {"analysis_record"},
                             forbidden=[cohort_id] if partial else [])
        identities = [cohort_id, *(m["member_id"] for m in contacts)]
        return self.finish_criterion(result, reasons, identities)

    def source(self, criterion):
        profile = self.profile()
        reasons = set() if profile else {"missing_record"}
        scope_id = self.scope["id"]
        snapshot_id = self.request.get("snapshot_id")
        self.budget.charge(len(self.records))
        relations = [r for r in self.records.values() if r["type"] == "relation" and r["scope_id"] == scope_id]
        frontiers = [r for r in self.records.values() if r["type"] == "frontier" and r["scope_id"] == scope_id]
        validation_kind = known(self.claim, "validation_kind")
        kinds = {VALIDATION_KINDS[validation_kind]} if validation_kind in VALIDATION_KINDS else set()
        if "human_consequence" in (known(self.claim, "requirements") or []):
            kinds.add("human_consequence_record")
        if criterion == "validation_type_fit":
            if validation_kind is None:
                reasons.add(fact_reason(self.claim, "validation_kind"))
            result = self.review(criterion, kinds=kinds)
            return self.finish_criterion(result, reasons, [self.claim["id"]])
        identities = [r["id"] for r in relations + frontiers]
        if criterion == "provenance_transformations":
            result = self.review(criterion, subjects=[*([snapshot_id] if snapshot_id else []), *identities])
            # The receipt explicitly inventories origins and transformations,
            # including a declared empty transformation list and known limits.
            qualified_receipts = [self.records[e] for r in result["values"]["reviews"]
                                  if r["qualified"] and r["verdict"] == "supports"
                                  for e in r["support_ids"]]
            inventory = [r for r in qualified_receipts if known(r, "kind") == "analysis_record"
                         and r.get("origin_ids") and "transformation_ids" in r and known(r, "uncertainty") is not None]
            if not inventory:
                reasons.add("prerequisite_unavailable")
            for evidence in inventory:
                self.budget.charge(len(evidence["origin_ids"]) + len(evidence["transformation_ids"]))
                identities.extend(evidence["origin_ids"] + evidence["transformation_ids"])
        else:
            roles = {r["kind"] for r in relations}
            if not {"uses_generation", "uses_reference", "uses_judgment"} <= roles:
                reasons.add("missing_record")
            reasons |= known_reasons(self.scope, ("dimension",))
            for relation in relations:
                self.budget.charge()
                if relation["kind"] in {"uses_generation", "uses_reference", "uses_judgment"}:
                    reasons |= known_reasons(relation, ("role", "asserted_by"))
            result = self.review(criterion, subjects=[self.scope["id"], *identities])
            if not any(known(self.records[e], "uncertainty") is not None
                       for r in result["values"]["reviews"] if r["qualified"] and r["verdict"] == "supports"
                       for e in r["support_ids"]):
                reasons.add("prerequisite_unavailable")
            # Independence is optional. When declared, reuse exact member and
            # dimension assessment, including known overlap and contrary paths.
            for independence in sorted(self.records.values(), key=lambda r: r["id"]):
                self.budget.charge()
                if independence["type"] != "independence" or independence["scope_id"] != scope_id:
                    continue
                view = {"acquisition": "acquisition", "model_ancestry": "model_ancestry",
                        "evaluation_rubric": "evaluation_rubric"}.get(independence["dimension"], "acquisition")
                child = self.prerequisite("independence:" + independence["id"], "lineage", lineage_request,
                                          seed_ids=independence["members"], view=view, independence_ids=[independence["id"]])
                detail = child["values"]["independence_assessments"][0]["review"]
                merge(result, detail)
                if detail["assessment"] != "supported_under_scope":
                    reasons.update(detail["reason_codes"] or ["prerequisite_unavailable"])
        return self.finish_criterion(result, reasons, identities)

    def tail(self, criterion):
        profile = self.profile()
        reasons = known_reasons(self.frame, ("tail_designations",))
        frame_ids = [self.frame["id"]] if self.frame else []
        snapshot_ids = [self.request["snapshot_id"]] if "snapshot_id" in self.request else []
        result = self.review(criterion, subjects=[*frame_ids, *snapshot_ids],
                             kinds={"execution_record"} if criterion == "tail_result_visibility" else {"analysis_record"})
        if profile is None:
            reasons.add("missing_record")
        elif profile["frame_id"] != self.frame.get("id"):
            reasons.add("scope_mismatch")
        elif criterion != "tail_designation_adequacy":
            if not profile["population_complete"]:
                reasons.add("unknown_membership")
            if profile["K"]["value"] == 0:
                reasons.add("empty_population")
            if profile["A"]["value"] != profile["K"]["value"]:
                reasons.add("unresolved_assignment")
            if any(t["state"] != "present" for t in profile["tails"]):
                reasons.add("prerequisite_unavailable")
            if criterion == "tail_result_visibility":
                for tail in profile["tails"]:
                    self.budget.charge()
                    receipt = receipts(self.records, tail["evidence_ids"], self.scope["id"], self.budget,
                                       subjects=snapshot_ids, kinds={"execution_record", "observation_record", "human_consequence_record"},
                                       resolved=result["values"]["resolved_ids"])
                    merge(result, receipt)
                    reasons.update(receipt["reason_codes"])
        result = self.finish_criterion(result, reasons, [*frame_ids, *snapshot_ids])
        if (criterion == "tail_representation" and profile and profile["frame_id"] == self.frame.get("id")
                and any(t["state"] == "absent" for t in profile["tails"])):
            result["assessment"] = "contradicted_under_scope"
            result["basis"].append({"kind": "local_calculation", "record_ids": sorted([*frame_ids, *snapshot_ids])})
        return result

    def corrective(self, criterion):
        cases = [r for r in self.cases()["corrections"] if r["claim_id"] == self.claim["id"]]
        eligible = [r for r in cases if r["completed"] and r["capacity"]["assessment"] == "supported_under_scope"]
        # Each capacity witness is one coherent case, route, actor, target and
        # authorized action. Different incomplete cases cannot be combined.
        if criterion == "route_and_authority":
            eligible = [r for r in cases if r["completed"] and any(
                a["authorization"]["assessment"] == "supported_under_scope" for a in r["actions"])]
        reasons = set() if eligible else {"prerequisite_unavailable"}
        groups = [[r["case_id"]] for r in eligible]
        result = self.review(criterion, groups=groups,
                             kinds={"process_record"} if criterion == "route_operability" else {"analysis_record"})
        identities = [r["case_id"] for r in cases]
        if criterion == "capacity_extent":
            extent = known(self.claim, "capacity_extent")
            if extent is None:
                reasons.add(fact_reason(self.claim, "capacity_extent"))
            elif extent == "sustained":
                history_actions = []
                for case in eligible:
                    source_case = self.records[case["case_id"]]
                    actions = {a["id"]: a for a in source_case.get("actions", [])}
                    for outcome in case["outcomes"]:
                        self.budget.charge()
                        if outcome["review"]["assessment"] == "supported_under_scope":
                            history_actions.append((case["case_id"], outcome["action_id"], known(actions[outcome["action_id"]], "occurred_at")))
                times = {time for _, _, time in history_actions if time}
                if len(times) < 2:
                    reasons.add("prerequisite_unavailable")
                event_receipts = {e for c in cases for field in ("attempts", "actions", "outcomes")
                                  for event in self.records[c["case_id"]].get(field, []) for e in event["evidence_ids"]}
                histories = []
                for review in result["values"]["reviews"]:
                    if not review["qualified"] or review["verdict"] != "supports":
                        continue
                    for identity in review["support_ids"]:
                        self.budget.charge()
                        evidence = self.records[identity]
                        if (identity not in event_receipts and known(evidence, "kind") == "process_record"
                                and known(evidence, "occurred_at") is not None
                                and (not times or known(evidence, "occurred_at") >= max(times))):
                            histories.append(identity)
                history = receipts(self.records, sorted(set(histories)), self.scope["id"], self.budget,
                                   subjects=[self.claim["id"], *sorted({c for c, _, _ in history_actions})],
                                   kinds={"process_record"}, dated=True, resolved=result["values"]["resolved_ids"])
                merge(result, history)
                reasons.update(history["reason_codes"])
        return self.finish_criterion(result, reasons, identities)

    def refresh(self):
        values, result = self.values, self.result
        for row in values["conditions"]:
            criteria = row["values"]["criteria"]
            if row["selection"] == "not_selected":
                continue
            row["reason_codes"] = []
            merge(row, *criteria)
            states = {c["assessment"] for c in criteria}
            row["execution"] = "completed" if all(c["execution"] == "completed" for c in criteria) else "partial"
            row["assessment"] = ("contradicted_under_scope" if "contradicted_under_scope" in states else
                                 "supported_under_scope" if states == {"supported_under_scope"} else
                                 "not_assessed" if states == {"not_assessed"} else "unresolved")
            if row["assessment"] == "supported_under_scope" and values["currentness"] != "current_under_declared_date":
                row["assessment"] = "unresolved"
                row["reason_codes"] = sorted(set(row["reason_codes"]) | {
                    "expired" if values["currentness"] == "expired_under_declared_date" else "prerequisite_unavailable"})
        states = {c["assessment"] for c in values["conditions"]}
        if "contradicted_under_scope" in states:
            values["conclusion"] = "defeated_under_scope"
        elif (states == {"supported_under_scope"} and values["claim_check"]["assessment"] == "supported_under_scope"
              and values["currentness"] == "current_under_declared_date" and result["execution"] == "completed"):
            values["conclusion"] = "supported_under_scope"
        elif states - {"not_assessed"}:
            values["conclusion"] = "unestablished"
        else:
            values["conclusion"] = "not_assessed"
        values["open_evaluation"] = values["conclusion"]
        result["assessment"] = {"defeated_under_scope": "contradicted_under_scope", "unestablished": "unresolved"}.get(values["conclusion"], values["conclusion"])
        merge(result, values["claim_check"], *values["conditions"])
        result["basis"] = [{"kind": "local_deduction", "record_ids": result["dependency_ids"]}]

    def run(self):
        claim = self.claim
        try:
            self.budget.charge(len(self.records))
            if claim["profile"] == "narrow_regression":
                lint = self.prerequisite("narrow", "lint", lint_claim, claim_id=claim["id"])
                self.values["currentness"] = lint["values"]["currentness"]
                self.values["conclusion"] = lint["values"]["claim_conclusion"]
                self.values["claim_check"] = lint["values"]["validation"]
                self.result["execution"], self.result["assessment"] = "completed", lint["assessment"]
                self.result["reason_codes"] = lint["reason_codes"]
                return self.result, self.findings
            gaps = known_reasons(claim, ("statement", "intended_use", "horizon", "frame_id", "requirements", "validation_kind"))
            gaps |= known_reasons(self.scope, ("window",))
            snapshot_id = self.request.get("snapshot_id")
            if snapshot_id and known(claim, "frame_id") is not None and self.records[snapshot_id]["frame_id"] != known(claim, "frame_id"):
                gaps.add("scope_mismatch")
            expiry = known(claim, "valid_until")
            if expiry is None:
                gaps.add(fact_reason(claim, "valid_until"))
            elif expiry <= self.dossier["analysis_time"]:
                self.values["currentness"] = "expired_under_declared_date"
                gaps.add("expired")
            else:
                self.values["currentness"] = "current_under_declared_date"
            self.values["claim_check"] = check(gaps, dependencies=[claim["id"], self.scope["id"]])
            for condition in self.values["conditions"]:
                if condition["selection"] == "not_selected":
                    continue
                method = {"structural_validity": self.structural, "external_presence": self.external,
                          "source_integrity": self.source, "tail_retention": self.tail, "corrective_capacity": self.corrective}[condition["condition"]]
                for index, row in enumerate(condition["values"]["criteria"]):
                    self.budget.charge()
                    detail = method(row["criterion"])
                    condition["values"]["criteria"][index] = {"criterion": row["criterion"], **detail}
                    self.refresh()
                    self.findings.append(finding(self.result, FAMILIES[condition["condition"]], row["criterion"],
                                                 [claim["id"]], detail["reason_codes"],
                                                 "Inspect this fixed criterion's supplied witnesses, exact scoped reviews and remaining premises.", detail["assessment"]))
            self.result["execution"], self.result["reason_codes"] = "completed", []
        finally:
            if claim["profile"] != "narrow_regression":
                self.refresh()
            self.budget.partial_result, self.budget.partial_findings = self.result, self.findings
        return self.result, self.findings


def assess_request(dossier, request, *, budget=None):
    return Assessment(dossier, request, budget or RequestBudget()).run()
