from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from qtbench.combinatorics import (
    iter_zero_rooted_tiered_trees,
    tiered_tree_size,
    zero_rooted_tiered_tree_count,
)
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_ttree_probes,
    evaluate_ttree_polynomial_checks,
    evaluate_ttree_submission,
    run_resource_gate,
    run_value_audit,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "t_statistic_discovery" / "ttree_inv_qt_xi_second_stat"
PROBLEM_ID = 9
PROBLEM_NAME = "ttree_inv_qt_xi_second_stat"


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def test_polynomials_are_symmetric_and_total_the_rtt0_count():
    data = _polynomials()
    assert data["variables"] == ["q", "t"]
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    for case in data["cases"]:
        mu = tuple(case["mu"])
        assert sum(mu) == case["n"]
        assert list(mu) == sorted(mu, reverse=True)
        poly = {(q, t): c for q, t, c in case["terms"]}
        assert all(c > 0 for c in poly.values())
        assert sum(poly.values()) == case["count"]
        assert poly == {(t, q): c for (q, t), c in poly.items()}  # q,t-symmetric
        # realizability: the q-marginal is the inv distribution of RTT_0(mu)
        if case["n"] <= 4:
            assert case["count"] == zero_rooted_tiered_tree_count(mu)
            q_marginal = Counter()
            for (q, _t), c in poly.items():
                q_marginal[q] += c
            model = Counter(tree.inv() for tree in iter_zero_rooted_tiered_trees(mu))
            assert q_marginal == model


def test_known_statistic_matches_public_instances():
    spec = importlib.util.spec_from_file_location("known_ttree", PROBLEM / "known_statistic.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((PROBLEM / "data" / "instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            assert module.statistic(entry["object"]) == entry["inv"]


def _reference_partner():
    """A rank-assignment witness: proves the target is realizable over RTT_0."""
    mapping: dict[str, int] = {}
    for case in _polynomials()["cases"]:
        column = defaultdict(list)
        for q, t, coeff in case["terms"]:
            column[q].extend([t] * coeff)
        for values in column.values():
            values.sort()
        fibers = defaultdict(list)
        for tree in iter_zero_rooted_tiered_trees(tuple(case["mu"])):
            fibers[tree.inv()].append(tree.encoding)
        for inv, encodings in fibers.items():
            for encoding, value in zip(encodings, column[inv], strict=True):
                mapping[encoding] = value

    def partner(tree):
        return mapping[tree.encoding]

    return partner


def test_reference_partner_reproduces_the_target_but_inv_does_not():
    result = evaluate_ttree_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_partner(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    inv_result = evaluate_ttree_polynomial_checks(
        problem_dir=PROBLEM, statistic=lambda tree: tree.inv()
    )
    assert not inv_result["full_qt"]["passed"]


def test_constant_zero_short_circuits_at_numerical_end_to_end():
    result = evaluate_ttree_submission(
        source="def statistic(tree):\n    return 0\n",
        probes=lambda: adversarial_ttree_probes(96),
        problem_dir=PROBLEM,
        timeout_seconds=2.0,
        numerical_timeout_seconds=60.0,
        max_python_bytes=64_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"
    assert result["value_audit"] is None


def test_value_audit_wired_for_tiered_trees():
    # a genuine small-valued statistic passes; a counting cheat is blocked
    genuine = "def statistic(tree):\n    return sum(tree.levels)\n"
    run_value_audit(
        genuine,
        adversarial_ttree_probes(64),
        value_exponent=8,
        timeout_seconds=5.0,
        size_of=tiered_tree_size,
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
            adversarial_ttree_probes(64),
            value_exponent=8,
            timeout_seconds=5.0,
            size_of=tiered_tree_size,
        )


def test_resource_gate_accepts_a_polynomial_statistic_on_large_trees():
    # A genuine, polynomial-time statistic runs within limits on large probes.
    genuine = "def statistic(tree):\n    return tree.inv()\n"
    report = run_resource_gate(
        genuine,
        adversarial_ttree_probes(256),
        timeout_seconds=10.0,
        max_python_bytes=64_000_000,
    )
    assert len(report.results) == len(adversarial_ttree_probes(256))
