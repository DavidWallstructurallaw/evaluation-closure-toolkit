"""Bounded exact-scope graph views and documentary independence assessments.

Every path is conditional on supplied relation declarations. Graph terminals,
cycles and disconnected components never establish hidden origins or independence.
"""

from collections import defaultdict, deque

from .budget import RequestBudget
from .evidence import evaluate_reviews, known, make_review_index
from .provenance import (
    fact_state, finding, known_reasons, reference_record, restrict_support, result_shell,
)

VIEWS = {
    "acquisition": frozenset({"derived_from", "acquired_from"}),
    "model_ancestry": frozenset({"trained_on", "exposed_to"}),
    "evaluation_rubric": frozenset({"rubric_from", "reference_from"}),
    "recursive_reuse": frozenset({"produced_by", "uses_generation", "uses_training",
                                "uses_selection", "uses_reference", "uses_judgment"}),
}


def _path(parents, node, budget):
    path = []
    while parents[node] is not None:
        budget.charge()
        node, edge = parents[node]
        path.append(edge)
    return path[::-1]


def _cycle(adjacency, reached, budget):
    """Return one finite directed cycle, using iterative DFS over reached nodes."""
    color = {}
    for root in sorted(reached):
        if color.get(root):
            continue
        color[root] = 1
        stack = [(root, iter(adjacency.get(root, ())))]
        positions = {root: 0}
        edge_stack = []
        while stack:
            node, edges = stack[-1]
            edge = next(edges, None)
            if edge is None:
                color[node] = 2
                positions.pop(node)
                stack.pop()
                if edge_stack:
                    edge_stack.pop()
                continue
            budget.charge()
            target = edge["to_id"]
            if color.get(target) == 1:
                path = edge_stack[positions[target]:] + [edge["id"]]
                budget.retain_paths(len(path))
                return {"node_id": target, "path": path}
            if not color.get(target):
                color[target] = 1
                positions[target] = len(stack)
                stack.append((target, iter(adjacency.get(target, ()))))
                edge_stack.append(edge["id"])
    return None


def _recursive(adjacency, reached, records, values, dependencies, contrary, budget):
    for later_id in sorted(reached):
        later = records[later_id]
        if later.get("kind") != "process":
            continue
        for use in adjacency.get(later_id, ()):
            budget.charge()
            if not use["kind"].startswith("uses_"):
                continue
            artifact = records[use["to_id"]]
            for production in adjacency.get(artifact["id"], ()):
                budget.charge()
                if production["kind"] != "produced_by":
                    continue
                earlier = records[production["to_id"]]
                reasons = known_reasons(earlier, ("occurred_at",))
                reasons |= known_reasons(later, ("occurred_at",))
                reasons |= known_reasons(use, ("occurred_at",))
                a, b, used = (known(row, "occurred_at") for row in (earlier, later, use))
                if a is not None and b is not None and used is not None:
                    if not a < b <= used:
                        reasons.add("prerequisite_unavailable")
                    for record in (artifact, production):
                        time = known(record, "occurred_at")
                        if fact_state(record, "occurred_at") == "disputed":
                            reasons.add("disputed")
                        if time is not None and not a <= time <= used:
                            reasons.add("prerequisite_unavailable")
                local_contrary = set()
                for record in (earlier, later, artifact, use, production):
                    reference_record(record, records, dependencies, local_contrary, budget)
                contrary.update(local_contrary)
                if local_contrary:
                    reasons.add("disputed")
                budget.retain_paths(2)
                values["recursive_witnesses"].append({
                    "earlier_process_id": earlier["id"], "later_process_id": later_id,
                    "artifact_id": artifact["id"], "use_kind": use["kind"],
                    "path": [use["id"], production["id"]],
                    "state": "recorded_recursive_reuse" if not reasons else "unresolved",
                    "reason_codes": sorted(reasons),
                    "contrary_ids": sorted(local_contrary),
                })


def lineage_request(dossier, request, *, budget=None):
    budget = budget or RequestBudget()
    records = {r["id"]: r for r in dossier["records"]}
    scope_id, view = request["scope_id"], request["view"]
    seeds = sorted(request["seed_ids"])
    values = {
        "view": view, "seed_ids": seeds, "witnesses": [], "frontiers": [],
        "captured_terminals": [], "search_complete": False,
        "independence_assessments": [], "recursive_witnesses": [],
        "relations": [], "cycle_state": "unresolved", "cycle_witnesses": [],
    }
    result = result_shell(request, values, [
        "Paths and overlap are deductions conditional on supplied typed relations in the exact captured scope.",
        "Captured terminals and no discovered overlap do not establish origins, independence, hidden-root bounds or error covariance.",
        "Pairwise assessments are not transitive or joint-set assessments; qualifications remain dimension-specific and documentary.",
        "A static cycle alone supplies no recursive-use chronology. Process occurrence times are treated as the start of the named process event.",
        "Sensitive role and method text remains in the referenced dossier records; it is not copied into the report.",
    ])
    budget.partial_result = result
    dependencies, contrary, support = {scope_id, *seeds}, set(), set()
    adjacency, frontiers = defaultdict(list), defaultdict(list)
    review_index = make_review_index(records)
    try:
        for record in sorted(records.values(), key=lambda r: r["id"]):
            budget.charge()
            if record.get("scope_id") != scope_id:
                continue
            if record["type"] == "relation" and record["kind"] in VIEWS[view]:
                local_contrary = set()
                reference_record(record, records, dependencies, local_contrary, budget)
                dependencies.update((record["from_id"], record["to_id"]))
                contrary.update(local_contrary)
                adjacency[record["from_id"]].append(record)
                values["relations"].append({
                    "relation_id": record["id"], "from_id": record["from_id"],
                    "to_id": record["to_id"], "kind": record["kind"],
                    "attribution_state": fact_state(record, "asserted_by"),
                    "role_state": fact_state(record, "role"),
                    "support_ids": sorted(record.get("evidence_ids", [])),
                    "contrary_ids": sorted(local_contrary),
                })
            elif record["type"] == "frontier" and record["view"] == view:
                frontiers[record["node_id"]].append(record)
        # Breadth-first traversal with edge-ID-sorted adjacency gives the first
        # lexicographic shortest relation path. Parent links avoid O(depth^2) storage.
        parents_by_seed, reached_by = {}, defaultdict(list)
        reached = set()
        for seed in seeds:
            parents = {seed: None}
            parents_by_seed[seed] = parents
            queue = deque([seed])
            while queue:
                budget.charge()
                node = queue.popleft()
                reached.add(node)
                dependencies.add(node)
                for other in reached_by[node]:
                    budget.charge()
                    left = _path(parents_by_seed[other], node, budget)
                    right = _path(parents, node, budget)
                    budget.retain_paths(len(left) + len(right))
                    values["witnesses"].append({
                        "left_seed_id": other, "right_seed_id": seed, "node_id": node,
                        "left_path": left, "right_path": right,
                    })
                reached_by[node].append(seed)
                for frontier in frontiers.get(node, ()):
                    reference_record(frontier, records, dependencies, contrary, budget)
                    path = _path(parents, node, budget)
                    budget.retain_paths(len(path))
                    reason = known(frontier, "reason")
                    values["frontiers"].append({
                        "frontier_id": frontier["id"], "seed_id": seed,
                        "node_id": node, "path": path,
                        "reason": reason or "unresolved",
                        "reason_state": fact_state(frontier, "reason"),
                    })
                if not adjacency.get(node):
                    path = _path(parents, node, budget)
                    budget.retain_paths(len(path))
                    values["captured_terminals"].append({"seed_id": seed, "node_id": node, "path": path})
                for edge in adjacency.get(node, ()):
                    budget.charge()
                    target = edge["to_id"]
                    if target not in parents:
                        parents[target] = (node, edge["id"])
                        queue.append(target)
        cycle = _cycle(adjacency, reached, budget)
        if cycle:
            values["cycle_witnesses"].append(cycle)
        values["cycle_state"] = "present" if cycle else "no_witness_in_captured_view"
        if view == "recursive_reuse":
            _recursive(adjacency, reached, records, values, dependencies, contrary, budget)
        selected = request.get("independence_ids")
        if selected is None:
            selected = [r["id"] for r in records.values() if r["type"] == "independence"
                        and r["scope_id"] == scope_id and set(r["members"]) == set(seeds)]
        for identity in sorted(selected):
            budget.charge()
            record = records[identity]
            reference_record(record, records, dependencies, contrary, budget)
            criterion = evaluate_reviews(records, identity, "independence", scope_id,
                                         review_index=review_index, budget=budget)
            reasons = known_reasons(record, ("method",))
            reasons |= known_reasons(records[scope_id], ("window",))
            dimension = record["dimension"]
            scoped_dimension = known(records[scope_id], "dimension")
            if scoped_dimension is not None and scoped_dimension != dimension:
                reasons.add("scope_mismatch")
            if dimension in record.get("unexamined_dimensions", []):
                reasons.add("prerequisite_unavailable")
            applies = dimension == view
            if applies and values["witnesses"]:
                reasons.add("disputed")
                overlap_edges = set()
                for witness in values["witnesses"]:
                    for edge_id in (*witness["left_path"], *witness["right_path"]):
                        budget.charge()
                        overlap_edges.add(edge_id)
                criterion["dependency_ids"] = sorted(set(criterion["dependency_ids"]) | overlap_edges)
                criterion["contrary_ids"] = sorted(set(criterion["contrary_ids"]) | overlap_edges)
                criterion["basis"].append({"kind": "local_deduction", "record_ids": sorted(overlap_edges)})
            restrict_support(criterion, reasons)
            dependencies.update(criterion["dependency_ids"])
            contrary.update(criterion["contrary_ids"])
            support.update(criterion["support_ids"])
            methods = [{"record_id": identity, "field": "method", "state": fact_state(record, "method")}]
            for review in criterion["values"]["reviews"]:
                methods.append({"record_id": review["review_id"], "field": "method",
                                "state": fact_state(records[review["review_id"]], "method")})
            values["independence_assessments"].append({
                "independence_id": identity, "members": sorted(record["members"]),
                "form": record["form"], "dimension": dimension,
                "unexamined_dimensions": sorted(record.get("unexamined_dimensions", [])),
                "applies_to_view": applies, "method_references": sorted(methods, key=lambda r: r["record_id"]),
                "review": criterion,
            })
        values["search_complete"] = True
        result["execution"] = "completed"
        result["reason_codes"] = []
    finally:
        values["witnesses"].sort(key=lambda r: (r["left_seed_id"], r["right_seed_id"], r["node_id"]))
        values["frontiers"].sort(key=lambda r: (r["seed_id"], r["frontier_id"]))
        values["captured_terminals"].sort(key=lambda r: (r["seed_id"], r["node_id"]))
        values["recursive_witnesses"].sort(key=lambda r: (r["later_process_id"], r["path"]))
        result["dependency_ids"] = sorted(dependencies)
        result["support_ids"], result["contrary_ids"] = sorted(support), sorted(contrary)
        result["basis"] = [{"kind": "supplied_assertion", "record_ids": sorted(dependencies)}]
        if values["witnesses"] or values["recursive_witnesses"] or values["cycle_witnesses"]:
            result["basis"].append({"kind": "local_deduction", "record_ids": sorted(r["relation_id"] for r in values["relations"])})
        findings = []
        if values["witnesses"]:
            findings.append(finding(result, "EC102", "typed_shared_lineage", seeds, [],
                                    "Inspect the finite paths and their supplied relation premises; no independent-validator count follows."))
        elif values["search_complete"]:
            findings.append(finding(result, "EC102", "typed_overlap_search", seeds,
                                    ["no_witness_in_captured_view"], "No overlap was found in this captured view; hidden ancestry remains unexamined."))
        if values["frontiers"]:
            findings.append(finding(result, "EC102", "unresolved_ancestry_frontier", seeds,
                                    ["prerequisite_unavailable"], "Supply the missing ancestry in this exact view; preserve already known overlap."))
        if values["independence_assessments"]:
            findings.append(finding(result, "EC102", "scoped_independence_inventory", seeds, [],
                                    "Use only the exact member set, form and dimension covered by each supplied assessment."))
        if values["recursive_witnesses"]:
            findings.append(finding(result, "EC102", "recursive_use_inventory", seeds, [],
                                    "Inspect the use/production path and chronology status; a graph cycle supplies no causal process by itself."))
        budget.partial_findings = findings
    return result, findings
