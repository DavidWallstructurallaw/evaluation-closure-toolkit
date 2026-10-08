"""Closed cases/assessment report shapes and locally checkable invariants."""

from .assessment import GATES
from .reporting import (
    _CRITERION, _RESULT, _common, _criterion, _external_values, _identity, _ids,
    _keys, _lineage_values, _lint_values, _number, _profile_values, _require, _sorted_rows,
)

FACT_STATES = {"known", "unknown", "withheld", "disputed", "absent", "not_applicable", "missing"}


def _optional_criterion(value, partial):
    if value == {}:
        _require(partial)
    else:
        _criterion(value)


def cases_values(value, *, partial=False):
    _keys(value, {"anomalies", "revisions", "corrections", "accounting_complete", "case_target_pairs", "pair_counts", "event_counts"})
    _require(type(value["accounting_complete"]) is bool and value["accounting_complete"] == (not partial))
    for field, identity in (("anomalies", "anomaly_id"), ("revisions", "revision_id"), ("corrections", "case_id")):
        _sorted_rows(value[field], identity)
    for row in value["anomalies"]:
        _keys(row, {"anomaly_id", "frame_id", "disposition", "disposition_state", "revision_ids", "case_ids", "preservation", "disposition_check"})
        _require(_identity(row["frame_id"]) and row["disposition_state"] in FACT_STATES)
        _require(row["disposition"] in {"unresolved", "investigated_no_change", "recut", "claim_restricted", "unestablished"})
        for key in ("revision_ids", "case_ids"):
            _ids(row[key])
        for key in ("preservation", "disposition_check"):
            _criterion(row[key])
    for row in value["revisions"]:
        _keys(row, {"revision_id", "from_frame", "to_frame", "kind", "kind_state", "cut_state", "anomaly_ids", "assignment_ids", "documented", "incorporated", "fidelity"})
        _require(all(_identity(row[k]) for k in ("from_frame", "to_frame")))
        _require(row["kind"] in {"recut", "relabel", "unestablished"} and row["kind_state"] in FACT_STATES)
        _require(row["cut_state"] in {"recut_documented", "relabel_only", "unestablished"})
        for key in ("anomaly_ids", "assignment_ids"):
            _ids(row[key])
        for key in ("documented", "incorporated", "fidelity"):
            _criterion(row[key])
        if row["fidelity"]["assessment"] == "supported_under_scope":
            _require(row["cut_state"] == "recut_documented" and all(row[k]["assessment"] == "supported_under_scope" for k in ("documented", "incorporated")))
        if row["incorporated"]["assessment"] == "supported_under_scope":
            _require(bool(row["assignment_ids"]))
    derived_pairs = {}
    for row in value["corrections"]:
        _keys(row, {"case_id", "claim_id", "context", "context_state", "objective", "objective_state", "route", "authority", "handling", "attempts", "actions", "outcomes", "capacity", "capacity_extent", "completed"})
        _require(_identity(row["claim_id"]) and type(row["completed"]) is bool)
        _require(partial or row["completed"])
        _require(row["context"] in {"production", "drill", "unestablished"})
        _require(row["objective"] in {"repair", "restrict", "replace_evaluator", "withdraw", "unestablished"})
        _require(row["context_state"] in FACT_STATES and row["objective_state"] in FACT_STATES)
        _require(row["capacity_extent"] == "tested_route")
        for key in ("route", "authority", "capacity"):
            _optional_criterion(row[key], partial and not row["completed"])
        nested = []
        for key in ("handling", "attempts", "actions", "outcomes"):
            _sorted_rows(row[key], "event_id")
            nested.extend(r["event_id"] for r in row[key])
        _require(len(nested) == len(set(nested)))
        for event in row["handling"]:
            _keys(event, {"event_id", "check", "state"})
            _criterion(event["check"])
            _require(event["state"] in {"submitted", "accepted", "rejected", "unestablished"})
        for event in row["attempts"]:
            _keys(event, {"event_id", "check", "actor_ids", "target_ids"})
            _criterion(event["check"])
            for key in ("actor_ids", "target_ids"):
                _ids(event[key])
                _require(len(event[key]) <= 1)
            if event["check"]["assessment"] == "supported_under_scope":
                _require(bool(event["actor_ids"]) and bool(event["target_ids"]))
                derived_pairs.setdefault((row["case_id"], event["target_ids"][0]), set()).add("attempted")
        attempts = {e["event_id"]: e for e in row["attempts"]}
        actions = {e["event_id"]: e for e in row["actions"]}
        for event in row["actions"]:
            _keys(event, {"event_id", "attempt_id", "kind", "target_ids", "check", "authorization"})
            _require(event["attempt_id"] in attempts)
            _require(event["kind"] in {"repair", "restrict", "replace_evaluator", "withdraw", "unestablished"})
            _ids(event["target_ids"])
            _require(len(event["target_ids"]) <= 1)
            _criterion(event["check"])
            _criterion(event["authorization"])
            if event["target_ids"]:
                states = derived_pairs.setdefault((row["case_id"], event["target_ids"][0]), set())
                if event["check"]["assessment"] == "supported_under_scope":
                    states.add("acted")
                if event["authorization"]["assessment"] == "supported_under_scope":
                    _require(event["check"]["assessment"] == "supported_under_scope")
                    _require(all(row[k]["assessment"] == "supported_under_scope" for k in ("route", "authority")))
                    states.add("authorized")
        for event in row["outcomes"]:
            _keys(event, {"event_id", "action_id", "objective", "result", "review"})
            _require(event["action_id"] in actions and event["objective"] == row["objective"])
            _require(event["result"] in {"effective", "ineffective", "unresolved", "unestablished"})
            _criterion(event["review"])
            if event["review"]["assessment"] == "supported_under_scope":
                action = actions[event["action_id"]]
                _require(action["check"]["assessment"] == "supported_under_scope" and event["result"] in {"effective", "ineffective"})
                _require(action["kind"] == row["objective"])
                if event["result"] == "effective":
                    derived_pairs.setdefault((row["case_id"], action["target_ids"][0]), set()).add("effective")
        if row["capacity"] and row["capacity"]["assessment"] == "supported_under_scope":
            _require(any(e["authorization"]["assessment"] == "supported_under_scope" for e in row["actions"]))
    _keys(value["event_counts"], {"handling", "attempts", "actions", "outcomes"})
    _keys(value["pair_counts"], {"attempted", "acted", "authorized", "effective"})
    for key in ("pair_counts", "event_counts"):
        for number in value[key].values():
            _number(number, integer=True)
            _require(number["state"] == ("unavailable" if partial else "available"))
    if partial:
        _require(value["case_target_pairs"] == [])
    else:
        expected_pairs = [{"case_id": c, "target_id": t, "states": sorted(states)} for (c, t), states in sorted(derived_pairs.items())]
        _require(value["case_target_pairs"] == expected_pairs)
        for stage, number in value["pair_counts"].items():
            _require(number["value"] == sum(stage in s for s in derived_pairs.values()))
        for stage, number in value["event_counts"].items():
            _require(number["value"] == sum(len(c[stage]) for c in value["corrections"]))


def assess_values(value, *, partial=False):
    _keys(value, {"claim_id", "currentness", "conditions", "conclusion", "capacity_extent", "open_evaluation", "prerequisites", "claim_check"})
    _require(_identity(value["claim_id"]))
    _require(value["currentness"] in {"current_under_declared_date", "expired_under_declared_date", "unestablished"})
    _require(value["conclusion"] in {"supported_under_scope", "defeated_under_scope", "unestablished", "not_assessed"})
    _require(value["capacity_extent"] in {"tested_route", "sustained", "unestablished"})
    _criterion(value["claim_check"])
    _require(type(value["prerequisites"]) is list)
    roles = []
    for prerequisite in value["prerequisites"]:
        _keys(prerequisite, {"role", "result"})
        role, child = prerequisite["role"], prerequisite["result"]
        _require(type(role) is str)
        roles.append(role)
        _keys(child, _RESULT)
        _common(child)
        _require(_identity(child["request_id"]) and _identity(child["scope_id"]) and child["selection"] == "selected")
        _require(child["execution"] in {"completed", "partial"})
        child_partial = child["execution"] == "partial"
        _require(not child_partial or partial)
        if role.startswith("independence:"):
            _require(_identity(role.split(":", 1)[1]) and child["operation"] == "lineage")
            _lineage_values(child["values"], partial=child_partial)
        else:
            mapping = {"structural": ("profile", _profile_values), "external": ("external", _external_values),
                       "cases": ("cases", cases_values), "narrow": ("lint", _lint_values)}
            _require(role in mapping and child["operation"] == mapping[role][0])
            mapping[role][1](child["values"], partial=child_partial)
    _require(len(roles) == len(set(roles)))
    _require(type(value["conditions"]) is list)
    if value["open_evaluation"] == "not_applicable":
        _require(value["conditions"] == [])
        if not partial:
            _require(roles == ["narrow"])
            _require(value["conclusion"] == value["prerequisites"][0]["result"]["values"]["claim_conclusion"])
        return
    _require(value["open_evaluation"] == value["conclusion"])
    _require([r["condition"] for r in value["conditions"]] == list(GATES))
    for gate in value["conditions"]:
        _keys(gate, _CRITERION | {"condition"})
        _common(gate)
        _keys(gate["values"], {"criteria"})
        criteria = gate["values"]["criteria"]
        _require(type(criteria) is list and [r["criterion"] for r in criteria] == list(GATES[gate["condition"]]))
        for row in criteria:
            _criterion({k: v for k, v in row.items() if k != "criterion"})
        if gate["selection"] == "not_selected":
            _require(gate["assessment"] == "not_assessed" and gate["execution"] == "not_run")
            _require(all(r["selection"] == "not_selected" and r["assessment"] == "not_assessed" and r["execution"] == "not_run" for r in criteria))
        else:
            _require(all(r["selection"] == "selected" for r in criteria))
            _require(partial or all(r["execution"] == "completed" for r in criteria))
            states = {r["assessment"] for r in criteria}
            expected = ("contradicted_under_scope" if "contradicted_under_scope" in states else
                        "supported_under_scope" if states == {"supported_under_scope"} else
                        "not_assessed" if states == {"not_assessed"} else "unresolved")
            if expected == "supported_under_scope" and value["currentness"] != "current_under_declared_date":
                expected = "unresolved"
            _require(gate["assessment"] == expected)
    states = {r["assessment"] for r in value["conditions"]}
    expected = ("defeated_under_scope" if "contradicted_under_scope" in states else
                "supported_under_scope" if states == {"supported_under_scope"} and not partial
                and value["claim_check"]["assessment"] == "supported_under_scope"
                and value["currentness"] == "current_under_declared_date" else
                "unestablished" if states - {"not_assessed"} else "not_assessed")
    _require(value["conclusion"] == expected)
