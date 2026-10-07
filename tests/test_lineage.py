"""Literal typed-path, scope, chronology and independence expectations."""

from copy import deepcopy
import json
import itertools
import random
import unittest
from unittest.mock import patch

from evaluation_closure_toolkit import analyze_bytes, render_markdown
from evaluation_closure_toolkit.budget import RequestBudget, RunBudget
from provenance_helpers import fixture, known, gap, wire, record, result, entity, relation, copy_review


class LineageTests(unittest.TestCase):
    def analyze(self, dossier, request="lineage-acquisition"):
        report = analyze_bytes(wire(dossier), request_ids=(request,))
        self.assertEqual(report["admission"], "valid", report.get("diagnostics"))
        self.assertEqual(report["execution"], "completed")
        render_markdown(report)
        return result(report, request)["values"]

    def test_shared_witness_and_unknown_frontier_coexist(self):
        value = self.analyze(fixture("shared-lineage"))
        self.assertEqual(value["witnesses"], [{"left_seed_id": "x", "right_seed_id": "y", "node_id": "origin",
                                               "left_path": ["edge-x-origin"], "right_path": ["edge-y-origin"]}])
        self.assertEqual(value["frontiers"], [{"frontier_id": "unknown-frontier", "seed_id": "x", "node_id": "unknown-node",
                                              "path": ["edge-x-unknown"], "reason": "unknown", "reason_state": "known"}])
        self.assertEqual([(r["seed_id"], r["node_id"]) for r in value["captured_terminals"]],
                         [("x", "origin"), ("x", "unknown-node"), ("y", "origin")])
        self.assertNotIn("independent_validator_count", value)
        self.assertNotIn("hidden_root_count", value)
        self.assertTrue(value["search_complete"])

    def test_no_mixed_edge_traversal_or_independence_from_no_overlap(self):
        value = self.analyze(fixture("shared-lineage"), "lineage-rubric")
        self.assertEqual(value["witnesses"], [])
        self.assertEqual(value["relations"], [])
        self.assertEqual(value["frontiers"], [])
        self.assertEqual(value["independence_assessments"], [])
        self.assertEqual(value["captured_terminals"], [{"seed_id": "x", "node_id": "x", "path": []}, {"seed_id": "y", "node_id": "y", "path": []}])

    def test_first_lexicographic_shortest_relation_path(self):
        d = fixture("shared-lineage")
        d["records"] += [entity("middle"), relation("a-longer-first", "x", "middle"),
                          relation("b-from-middle", "middle", "origin"), relation("a-direct", "x", "origin")]
        value = self.analyze(d)
        origin = next(r for r in value["witnesses"] if r["node_id"] == "origin")
        self.assertEqual(origin["left_path"], ["a-direct"])

    def test_equal_length_paths_use_relation_ids_not_input_order(self):
        d = fixture("shared-lineage")
        d["records"] = [r for r in d["records"] if r["id"] != "edge-x-origin"]
        d["records"] += [entity("m-a"), entity("m-b"), relation("z-start", "x", "m-a"),
                          relation("a-start", "x", "m-b"), relation("a-end", "m-a", "origin"), relation("z-end", "m-b", "origin")]
        value = self.analyze(d)
        self.assertEqual(value["witnesses"][0]["left_path"], ["a-start", "z-end"])
        d["records"].reverse()
        d["requests"][0]["seed_ids"].reverse()
        self.assertEqual(self.analyze(d), value)

    def test_cycle_is_a_graph_property_and_terminates(self):
        d = fixture("shared-lineage")
        d["records"].append(relation("origin-back", "origin", "x"))
        value = self.analyze(d)
        self.assertEqual(value["cycle_state"], "present")
        self.assertEqual(value["cycle_witnesses"], [{"node_id": "origin", "path": ["origin-back", "edge-x-origin"]}])
        self.assertEqual(value["recursive_witnesses"], [])

    def test_self_loop_and_seed_as_common_reached_node(self):
        d = fixture("shared-lineage")
        d["records"] += [relation("self", "x", "x"), relation("y-to-x", "y", "x")]
        value = self.analyze(d)
        witness = next(r for r in value["witnesses"] if r["node_id"] == "x")
        self.assertEqual(witness["left_path"], [])
        self.assertEqual(witness["right_path"], ["y-to-x"])
        self.assertEqual(value["cycle_state"], "present")

    def test_wrong_scope_relations_and_frontiers_inert(self):
        d = fixture("shared-lineage")
        d["records"].append({"id": "elsewhere", "type": "scope", "process_id": "evaluation"})
        record(d, "edge-y-origin")["scope_id"] = "elsewhere"
        record(d, "unknown-frontier")["scope_id"] = "elsewhere"
        value = self.analyze(d)
        self.assertEqual(value["witnesses"], [])
        self.assertEqual(value["frontiers"], [])

    def test_frontier_fact_states_preserve_distinctions(self):
        for state in ("unknown", "withheld", "disputed", "absent", "not_applicable"):
            d = fixture("shared-lineage")
            record(d, "unknown-frontier")["reason"] = gap(state)
            row = self.analyze(d)["frontiers"][0]
            self.assertEqual(row["reason_state"], state)
            self.assertEqual(row["reason"], "unresolved")
        d = fixture("shared-lineage")
        del record(d, "unknown-frontier")["reason"]
        self.assertEqual(self.analyze(d)["frontiers"][0]["reason_state"], "missing")

    def test_relation_attribution_gap_retains_conditional_path(self):
        d = fixture("shared-lineage")
        del record(d, "edge-x-origin")["asserted_by"]
        value = self.analyze(d)
        self.assertEqual(len(value["witnesses"]), 1)
        self.assertEqual(next(r for r in value["relations"] if r["relation_id"] == "edge-x-origin")["attribution_state"], "missing")

    def test_independence_support_cannot_erase_shared_path(self):
        value = self.analyze(fixture("shared-lineage"))
        independence = value["independence_assessments"][0]
        self.assertEqual(independence["review"]["assessment"], "unresolved")
        self.assertIn("disputed", independence["review"]["reason_codes"])
        self.assertIn("independence-review", independence["review"]["support_ids"])
        self.assertTrue(independence["applies_to_view"])

    def test_qualified_independence_is_exact_and_documentary(self):
        d = fixture("shared-lineage")
        d["records"] = [r for r in d["records"] if r["id"] != "edge-y-origin"]
        row = self.analyze(d)["independence_assessments"][0]
        self.assertEqual(row["review"]["assessment"], "supported_under_scope")
        self.assertEqual(row["members"], ["x", "y"])
        self.assertEqual(row["form"], "pairwise")
        self.assertEqual(row["dimension"], "acquisition")
        self.assertEqual([r["record_id"] for r in row["method_references"]], ["independence-review", "independence-xy"])

    def test_independence_review_missing_or_record_method_missing(self):
        for field in ("review", "method"):
            d = fixture("shared-lineage")
            d["records"] = [r for r in d["records"] if r["id"] != "edge-y-origin"]
            if field == "review":
                d["records"] = [r for r in d["records"] if r["id"] != "independence-review"]
            else:
                del record(d, "independence-xy")["method"]
            self.assertEqual(self.analyze(d)["independence_assessments"][0]["review"]["assessment"], "unresolved")

    def test_dimension_is_not_promoted_to_other_views(self):
        d = fixture("shared-lineage")
        record(d, "independence-xy")["dimension"] = "analytical_method"
        record(d, "independence-xy")["unexamined_dimensions"].remove("analytical_method")
        row = self.analyze(d)["independence_assessments"][0]
        self.assertFalse(row["applies_to_view"])
        self.assertEqual(row["dimension"], "analytical_method")

    def test_unexamined_dimension_blocks_affirmative_review(self):
        d = fixture("shared-lineage")
        d["records"] = [r for r in d["records"] if r["id"] != "edge-y-origin"]
        record(d, "independence-xy")["unexamined_dimensions"].append("acquisition")
        self.assertEqual(self.analyze(d)["independence_assessments"][0]["review"]["assessment"], "unresolved")

    def test_no_pairwise_transitivity_or_setwise_synthesis(self):
        d = fixture("shared-lineage")
        d["records"] = [r for r in d["records"] if r["type"] != "relation"]
        d["records"].append(entity("z"))
        second = deepcopy(record(d, "independence-xy"))
        second.update(id="independence-yz", members=["y", "z"])
        d["records"].append(second)
        copy_review(d, "independence-yz-review", template="independence-review", target_id="independence-yz")
        for seeds in (["x", "z"], ["x", "y", "z"]):
            d["requests"][0]["seed_ids"] = seeds
            self.assertEqual(self.analyze(d)["independence_assessments"], [])

    def test_explicit_empty_independence_selection(self):
        d = fixture("shared-lineage")
        d["requests"][0]["independence_ids"] = []
        self.assertEqual(self.analyze(d)["independence_assessments"], [])

    def test_independence_requires_known_window_and_consistent_scope_dimension(self):
        for field, value in (("window", gap()), ("dimension", known("model_ancestry"))):
            d = fixture("shared-lineage")
            d["records"] = [r for r in d["records"] if r["id"] != "edge-y-origin"]
            record(d, "scope")[field] = value
            self.assertEqual(self.analyze(d)["independence_assessments"][0]["review"]["assessment"], "unresolved")

    def test_recursive_acyclic_witness_has_actual_role_and_path(self):
        value = self.analyze(fixture("recursive-reuse"), "lineage-recursive")
        self.assertEqual(value["cycle_state"], "no_witness_in_captured_view")
        self.assertEqual(value["recursive_witnesses"], [{"earlier_process_id": "generation-a", "later_process_id": "generation-b",
            "artifact_id": "earlier-output", "use_kind": "uses_generation", "path": ["reuse-output", "produce-a"],
            "state": "recorded_recursive_reuse", "reason_codes": [], "contrary_ids": []}])

    def test_each_recursive_role_is_preserved(self):
        for role in ("uses_generation", "uses_training", "uses_selection", "uses_reference", "uses_judgment"):
            d = fixture("recursive-reuse")
            record(d, "reuse-output")["kind"] = role
            self.assertEqual(self.analyze(d, "lineage-recursive")["recursive_witnesses"][0]["use_kind"], role)

    def test_version_order_alone_cannot_supply_chronology(self):
        for identity in ("generation-a", "generation-b", "reuse-output"):
            d = fixture("recursive-reuse")
            del record(d, identity)["occurred_at"]
            row = self.analyze(d, "lineage-recursive")["recursive_witnesses"][0]
            self.assertEqual(row["state"], "unresolved")
            self.assertIn("missing_field", row["reason_codes"])

    def test_reversed_equal_and_before_process_use_times_do_not_qualify(self):
        for identity, time in (("generation-a", "2026-09-20T10:00:00Z"), ("reuse-output", "2026-09-19T10:00:00Z"),
                               ("earlier-output", "2026-09-30T10:00:00Z"), ("produce-a", "2026-09-01T10:00:00Z")):
            d = fixture("recursive-reuse")
            record(d, identity)["occurred_at"] = known(time)
            self.assertEqual(self.analyze(d, "lineage-recursive")["recursive_witnesses"][0]["state"], "unresolved")

    def test_static_cycle_with_missing_times_does_not_become_recursive_evidence(self):
        d = fixture("recursive-reuse")
        record(d, "produce-a")["to_id"] = "generation-b"
        del record(d, "generation-b")["occurred_at"]
        value = self.analyze(d, "lineage-recursive")
        self.assertEqual(value["cycle_state"], "present")
        self.assertTrue(all(r["state"] == "unresolved" for r in value["recursive_witnesses"]))

    def test_inventory_only_edges_do_not_create_acquisition_paths(self):
        d = fixture("shared-lineage")
        d["records"] = [r for r in d["records"] if r["type"] != "relation"]
        d["records"] += [relation("x-evaluated", "x", "assessor", "evaluated_by")]
        # Artifact endpoints are intentionally rejected by admission for evaluated_by.
        report = analyze_bytes(wire(d))
        self.assertEqual(report["admission"], "invalid")
        d["records"] = [r for r in d["records"] if r["id"] != "x-evaluated"]
        self.assertEqual(self.analyze(d)["witnesses"], [])

    def test_limits_preserve_completed_overlap_and_never_clean_negative(self):
        d = fixture("shared-lineage")
        seen = False
        for limit in range(24, 150):
            with patch("evaluation_closure_toolkit.api.RequestBudget", side_effect=lambda **kw: RequestBudget(limit=limit, **kw)):
                report = analyze_bytes(wire(d), request_ids=("lineage-acquisition",))
            row = result(report, "lineage-acquisition")
            if row["execution"] == "partial" and row["values"]["witnesses"]:
                seen = True
                self.assertFalse(row["values"]["search_complete"])
                self.assertTrue(any(f["family"] == "EC108" for f in report["findings"]))
                self.assertFalse(any(f["rule"] == "typed_overlap_search" for f in report["findings"]))
                render_markdown(report)
                break
        self.assertTrue(seen, "A retained finite witness must survive a later work limit")

    def test_runwide_path_budget_stops_later_requests(self):
        d = fixture("shared-lineage")
        with patch("evaluation_closure_toolkit.api.RunBudget", side_effect=lambda: RunBudget(path_limit=1)):
            report = analyze_bytes(wire(d))
        self.assertEqual(report["execution"], "partial")
        self.assertEqual(result(report, "lineage-rubric")["execution"], "not_run")
        render_markdown(report)

    def test_long_chain_does_not_use_recursive_python_traversal(self):
        d = fixture("shared-lineage")
        d["requests"] = [d["requests"][0]]
        d["requests"][0]["independence_ids"] = []
        d["records"] = [r for r in d["records"] if r["type"] not in {"relation", "frontier"}]
        previous = "x"
        for i in range(1100):
            identity = f"chain-{i:04}"
            d["records"] += [entity(identity), relation(f"edge-{i:04}", previous, identity)]
            previous = identity
        value = self.analyze(d)
        terminal = next(r for r in value["captured_terminals"] if r["seed_id"] == "x")
        self.assertEqual(len(terminal["path"]), 1100)

    def test_model_and_rubric_views_keep_distinct_typed_edges(self):
        d = fixture("shared-lineage")
        d["records"] += [entity("model-a", "model"), entity("model-b", "model"),
                          relation("train-a", "model-a", "origin", "trained_on"),
                          relation("expose-b", "model-b", "origin", "exposed_to"),
                          relation("rubric-x", "x", "unknown-node", "rubric_from"),
                          relation("reference-y", "y", "unknown-node", "reference_from")]
        d["requests"][0].update(seed_ids=["model-a", "model-b"], view="model_ancestry")
        value = self.analyze(d)
        self.assertEqual(value["witnesses"], [{"left_seed_id": "model-a", "right_seed_id": "model-b", "node_id": "origin", "left_path": ["train-a"], "right_path": ["expose-b"]}])
        rubric = self.analyze(d, "lineage-rubric")
        self.assertEqual(rubric["witnesses"][0]["node_id"], "unknown-node")
        self.assertEqual(rubric["frontiers"], [])

    def test_exhaustive_simple_path_oracle_on_small_cyclic_graphs(self):
        rng = random.Random(1703)
        nodes, seeds = ["x", "y", "origin", "unknown-node", "z"], ["x", "y", "z"]
        for scenario in range(20):
            d = fixture("shared-lineage")
            d["records"] = [r for r in d["records"] if r["type"] not in {"relation", "frontier", "review", "independence", "evidence"}]
            d["records"].append(entity("z"))
            d["requests"][0]["seed_ids"] = seeds[:]
            edges = []
            for i, (source, target) in enumerate(itertools.product(nodes, repeat=2)):
                if rng.random() < 0.24:
                    edges.append((f"edge-{i:02}", source, target))
            d["records"] += [relation(identity, source, target) for identity, source, target in edges]
            shortest = {}
            for seed in seeds:
                paths = {seed: [()]}
                def enumerate_paths(node, visited, path):
                    for identity, source, target in edges:
                        if source == node and target not in visited:
                            extended = (*path, identity)
                            paths.setdefault(target, []).append(extended)
                            enumerate_paths(target, visited | {target}, extended)
                enumerate_paths(seed, {seed}, ())
                shortest[seed] = {node: min(options, key=lambda p: (len(p), p)) for node, options in paths.items()}
            expected = []
            for left, right in itertools.combinations(seeds, 2):
                for node in sorted(shortest[left].keys() & shortest[right].keys()):
                    expected.append({"left_seed_id": left, "right_seed_id": right, "node_id": node,
                                     "left_path": list(shortest[left][node]), "right_path": list(shortest[right][node])})
            self.assertEqual(self.analyze(d)["witnesses"], expected, scenario)


if __name__ == "__main__":
    unittest.main()
