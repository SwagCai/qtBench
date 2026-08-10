from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from qtbench.combinatorics import (
    iter_uig_permutations_for_vector,
    unit_interval_graph_permutation_count,
    unit_interval_graph_permutation_size,
)
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_uig_probes,
    evaluate_uig_polynomial_checks,
    evaluate_uig_submission,
    run_resource_gate,
    run_value_audit,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "q_statistic_discovery" / "uig_ginv_shareshian_wachs_q_stat"
PROBLEM_ID = 8
PROBLEM_NAME = "uig_ginv_shareshian_wachs_q_stat"


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def test_polynomials_are_e_positive_palindromic_and_total_the_fiber():
    data = _polynomials()
    assert data["variables"] == ["partition", "q"]
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    seen_n = Counter()
    for case in data["cases"]:
        n = case["n"]
        b = tuple(case["b"])
        seen_n[n] += 1
        num_edges = sum(1 for i in range(1, n + 1) for j in range(i + 1, b[i - 1] + 1))
        by_partition = defaultdict(dict)
        for partition, q, coeff in case["terms"]:
            assert coeff > 0  # e-positivity
            by_partition[tuple(partition)][q] = coeff
        for poly in by_partition.values():
            # reciprocal with ambient exponent |E|:
            # c_lambda(q) = q^{|E|} c_lambda(1/q)
            for q, coeff in poly.items():
                assert poly.get(num_edges - q, 0) == coeff
        assert sum(coeff for _p, _q, coeff in case["terms"]) == case["count"]
    # one fiber per Dyck graph (Catalan) at each size, up to n = 7
    for n, graphs in seen_n.items():
        from math import comb

        assert graphs == comb(2 * n, n) // (n + 1)


def test_q_equals_1_is_the_partition_multiset_marginal():
    full = {c["case_id"]: c for c in _polynomials()["cases"]}
    marginal = json.loads((PROBLEM / "data" / "q_equals_1.json").read_text())
    assert marginal["variables"] == ["partition"]
    for case in marginal["cases"]:
        expected = defaultdict(int)
        for partition, _q, coeff in full[case["case_id"]]["terms"]:
            expected[tuple(partition)] += coeff
        got = {tuple(partition): coeff for partition, coeff in case["terms"]}
        assert got == {p: c for p, c in expected.items() if c}
        assert sum(got.values()) == case["count"]


def test_known_statistic_matches_public_instances():
    spec = importlib.util.spec_from_file_location("known_uig", PROBLEM / "known_statistic.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((PROBLEM / "data" / "instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            assert module.statistic(entry["object"]) == entry["ginv"]


def _reference_theta():
    """A partition-valued witness proving the target is realizable over the objects.

    For each Dyck graph, distribute the permutations of each fixed ``ginv`` value
    among the target partitions according to the published coefficients. The
    ``strict=True`` zip also re-checks the total identity per graph.
    """
    mapping: dict[str, tuple[int, ...]] = {}
    for case in _polynomials()["cases"]:
        column = defaultdict(list)
        for partition, q, coeff in case["terms"]:
            column[q].extend([tuple(partition)] * coeff)
        for values in column.values():
            values.sort()
        fibers = defaultdict(list)
        for obj in iter_uig_permutations_for_vector(tuple(case["b"])):
            fibers[obj.ginv()].append(obj.encoding)
        for ginv_value, encodings in fibers.items():
            encodings.sort()
            for encoding, partition in zip(encodings, column[ginv_value], strict=True):
                mapping[encoding] = partition

    def theta(graph_permutation):
        return mapping[graph_permutation.encoding]

    return theta


def test_reference_theta_reproduces_target_but_a_constant_does_not():
    result = evaluate_uig_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_theta(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    # The constant partition (n) matches only the complete-graph fibers.
    constant = evaluate_uig_polynomial_checks(
        problem_dir=PROBLEM, statistic=lambda obj: (obj.n,)
    )
    assert not constant["full_qt"]["passed"]


def test_valid_but_wrong_statistic_short_circuits_at_numerical_end_to_end():
    # The constant partition (n) is a valid composition but wrong on most graphs,
    # so it fails gracefully at the numerical stage before the value/resource gates.
    result = evaluate_uig_submission(
        source="def statistic(graph_permutation):\n    return (graph_permutation.n,)\n",
        probes=lambda: adversarial_uig_probes(96),
        problem_dir=PROBLEM,
        timeout_seconds=2.0,
        numerical_timeout_seconds=60.0,
        max_python_bytes=64_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"
    assert result["value_audit"] is None


def test_non_composition_output_is_rejected():
    # Returning an int (not a composition of n) is rejected during numerical checks.
    with pytest.raises(ResourceGateError, match="composition"):
        evaluate_uig_submission(
            source="def statistic(graph_permutation):\n    return 0\n",
            probes=lambda: adversarial_uig_probes(96),
            problem_dir=PROBLEM,
            timeout_seconds=2.0,
            numerical_timeout_seconds=60.0,
            max_python_bytes=64_000_000,
        )


@pytest.mark.parametrize("invalid_part", [True, 1.0, "1"])
def test_composition_parts_must_be_exact_integers(invalid_part):
    with pytest.raises(ValueError, match="composition"):
        evaluate_uig_polynomial_checks(
            problem_dir=PROBLEM,
            statistic=lambda _obj: (invalid_part,),
        )


def test_value_audit_wired_for_unit_interval_graph_permutations():
    # A genuine small-valued statistic (a valid composition) passes the audit.
    genuine = (
        "def statistic(graph_permutation):\n"
        "    return tuple(1 for _ in range(graph_permutation.n))\n"
    )
    run_value_audit(
        genuine,
        adversarial_uig_probes(64),
        value_exponent=8,
        timeout_seconds=5.0,
        size_of=unit_interval_graph_permutation_size,
    )

    counting = (
        "def statistic(graph_permutation):\n"
        "    total = 1\n"
        "    for _ in range(graph_permutation.n):\n"
        "        total = total + total\n"
        "    return (total % 3 + 1,) + tuple(1 for _ in range(graph_permutation.n - 1))\n"
    )
    with pytest.raises(ResourceGateError, match="magnitude bound|bit integer"):
        run_value_audit(
            counting,
            adversarial_uig_probes(64),
            value_exponent=8,
            timeout_seconds=5.0,
            size_of=unit_interval_graph_permutation_size,
        )


def test_resource_gate_accepts_a_polynomial_statistic_on_large_objects():
    genuine = (
        "def statistic(graph_permutation):\n"
        "    return (graph_permutation.n,)\n"
    )
    probes = adversarial_uig_probes(256)
    report = run_resource_gate(
        genuine,
        probes,
        timeout_seconds=5.0,
        max_python_bytes=64_000_000,
    )
    assert len(report.results) == len(probes)


def test_object_totals_match_double_factorial():
    assert unit_interval_graph_permutation_count(5) == 945
