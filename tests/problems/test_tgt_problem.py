from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from qtbench.combinatorics import (
    ThresholdSpanningTree,
    is_threshold_spanning_tree,
    is_threshold_up_degrees,
    iter_threshold_graphs,
    iter_threshold_spanning_trees,
    threshold_spanning_tree_count,
    threshold_tree_size,
    threshold_up_degrees,
)
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_tgt_probes,
    evaluate_tgt_polynomial_checks,
    evaluate_tgt_submission,
    run_resource_gate,
    run_value_audit,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "t_statistic_discovery" / "tgt_inv_qt_ehrhart_second_stat"
PROBLEM_ID = 21
PROBLEM_NAME = "tgt_inv_qt_ehrhart_second_stat"


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def test_polynomials_are_symmetric_and_total_the_spanning_tree_count():
    data = _polynomials()
    assert data["variables"] == ["q", "t"]
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    for case in data["cases"]:
        up_degrees = tuple(case["up_degrees"])
        assert len(up_degrees) == case["n"]
        poly = {(q, t): c for q, t, c in case["terms"]}
        # Conjecture 6.1 of arXiv:1610.08370, open in general
        assert all(c > 0 for c in poly.values())
        assert sum(poly.values()) == case["count"]
        assert poly == {(t, q): c for (q, t), c in poly.items()}  # q,t-symmetric
        # realizability: the q-marginal is the inv distribution, Theorem 3.8
        if case["n"] <= 5:
            assert case["count"] == threshold_spanning_tree_count(up_degrees)
            q_marginal = Counter()
            for (q, _t), c in poly.items():
                q_marginal[q] += c
            model = Counter(
                tree.inv() for tree in iter_threshold_spanning_trees(up_degrees)
            )
            assert q_marginal == model


def test_complete_graph_fibers_have_the_diagonal_harmonics_dimension():
    """For K_{n+1} the target is the bigraded Hilbert series of DH_n."""
    cases = {tuple(case["up_degrees"]): case for case in _polynomials()["cases"]}
    for n in range(1, 7):
        complete = threshold_up_degrees(n, range(1, n))
        case = cases[complete]
        assert case["count"] == (n + 1) ** (n - 1)  # Cayley
        assert max(q for q, _t, _c in case["terms"]) == n * (n - 1) // 2


def test_threshold_graph_parametrisation():
    for n in range(1, 8):
        graphs = list(iter_threshold_graphs(n))
        assert len(graphs) == 2 ** max(0, n - 1)
        assert len(set(graphs)) == len(graphs)
        for up_degrees in graphs:
            tree = next(iter_threshold_spanning_trees(up_degrees))
            degrees = tree.degrees
            # labelled by reverse degree sequence
            assert list(degrees) == sorted(degrees, reverse=True)
            # vertex 0 dominates, so the graph is connected and 0 roots every tree
            assert degrees[0] == n
            # the staircase property that characterises threshold graphs
            for i in range(n + 1):
                for j in range(n + 1):
                    if i != j and tree.adjacent(i, j):
                        for a in range(i + 1):
                            for b in range(j + 1):
                                if a != b:
                                    assert tree.adjacent(a, b)


@pytest.mark.parametrize(
    "n,subset",
    [(0, ()), (3, (0,)), (3, (3,)), (3, (1, 1)), (3, (True,))],
)
def test_threshold_graph_parametrisation_rejects_invalid_subsets(n, subset):
    with pytest.raises(ValueError):
        threshold_up_degrees(n, subset)


@pytest.mark.parametrize("value", [None, "3,2,1", (True,), (1.0,)])
def test_threshold_up_degree_predicate_rejects_invalid_types(value):
    assert not is_threshold_up_degrees(value)


def test_deep_threshold_tree_validation_and_inversions():
    n = 2_048
    up_degrees = tuple(range(n, 0, -1))
    parents = (*range(2, n + 1), 0)
    encoding = (
        ",".join(map(str, up_degrees))
        + "|"
        + ",".join(map(str, parents))
    )

    tree = ThresholdSpanningTree(encoding)
    assert tree.inv() == n * (n - 1) // 2

    cyclic_parents = (*parents[:-1], n - 1)
    cyclic_encoding = (
        ",".join(map(str, up_degrees))
        + "|"
        + ",".join(map(str, cyclic_parents))
    )
    assert not is_threshold_spanning_tree(cyclic_encoding)


def test_the_graph_is_part_of_the_object():
    """The same labelled tree spans many graphs, and inv cannot tell them apart.

    Example 6.5 of arXiv:1610.08370 shows the missing statistic must depend on
    the ambient threshold graph, which is why the encoding carries it.
    """
    fibers = defaultdict(set)
    for up_degrees in iter_threshold_graphs(4):
        for tree in iter_threshold_spanning_trees(up_degrees):
            fibers[tree.parents].add(up_degrees)
    shared = {parents: graphs for parents, graphs in fibers.items() if len(graphs) > 1}
    assert shared, "expected labelled trees spanning several threshold graphs"
    parents, graphs = max(shared.items(), key=lambda item: len(item[1]))
    invs = set()
    for up_degrees in graphs:
        encoding = (
            ",".join(str(v) for v in up_degrees) + "|" + ",".join(str(p) for p in parents)
        )
        assert is_threshold_spanning_tree(encoding)
        invs.add(next(
            tree.inv() for tree in iter_threshold_spanning_trees(up_degrees)
            if tree.parents == parents
        ))
    assert len(invs) == 1  # inv does not see the graph, so the partner must


def test_known_statistic_matches_public_instances():
    spec = importlib.util.spec_from_file_location("known_tgt", PROBLEM / "known_statistic.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((PROBLEM / "data" / "instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            assert module.statistic(entry["object"]) == entry["inv"]


def _reference_partner():
    """A rank-assignment witness: proves the target is realizable over the fiber."""
    mapping: dict[str, int] = {}
    for case in _polynomials()["cases"]:
        column = defaultdict(list)
        for q, t, coeff in case["terms"]:
            column[q].extend([t] * coeff)
        for values in column.values():
            values.sort()
        fibers = defaultdict(list)
        for tree in iter_threshold_spanning_trees(tuple(case["up_degrees"])):
            fibers[tree.inv()].append(tree.encoding)
        for inv, encodings in fibers.items():
            for encoding, value in zip(encodings, column[inv], strict=True):
                mapping[encoding] = value

    def partner(tree):
        return mapping[tree.encoding]

    return partner


def test_reference_partner_reproduces_the_target_but_inv_does_not():
    result = evaluate_tgt_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_partner(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    inv_result = evaluate_tgt_polynomial_checks(
        problem_dir=PROBLEM, statistic=lambda tree: tree.inv()
    )
    assert not inv_result["full_qt"]["passed"]


def test_constant_zero_short_circuits_at_numerical_end_to_end():
    result = evaluate_tgt_submission(
        source="def statistic(tree):\n    return 0\n",
        probes=lambda: adversarial_tgt_probes(96),
        problem_dir=PROBLEM,
        timeout_seconds=2.0,
        numerical_timeout_seconds=120.0,
        max_python_bytes=64_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"
    assert result["value_audit"] is None


def test_value_audit_wired_for_threshold_trees():
    # a genuine small-valued statistic passes; a counting cheat is blocked
    genuine = "def statistic(tree):\n    return sum(tree.up_degrees)\n"
    run_value_audit(
        genuine,
        adversarial_tgt_probes(64),
        value_exponent=8,
        timeout_seconds=5.0,
        size_of=threshold_tree_size,
    )

    counting = (
        "def statistic(tree):\n"
        "    total = 1\n"
        "    for _ in range(tree.n):\n"
        "        total = total + total\n"
        "    return total % 3\n"
    )
    with pytest.raises(ResourceGateError, match="magnitude bound|bit integer"):
        run_value_audit(
            counting,
            adversarial_tgt_probes(64),
            value_exponent=8,
            timeout_seconds=5.0,
            size_of=threshold_tree_size,
        )


def test_resource_gate_accepts_a_polynomial_statistic_on_large_objects():
    # A genuine, polynomial-time statistic runs within limits on large probes,
    # including the deep path tree and the dense complete graph.
    genuine = "def statistic(tree):\n    return tree.inv()\n"
    report = run_resource_gate(
        genuine,
        adversarial_tgt_probes(256),
        timeout_seconds=10.0,
        max_python_bytes=64_000_000,
    )
    assert len(report.results) == len(adversarial_tgt_probes(256))
