from __future__ import annotations

import json
from collections import Counter, defaultdict
from itertools import permutations
from math import comb
from pathlib import Path

import pytest

from qtbench.combinatorics import (
    iter_partitions,
    iter_standard_tableau_rows,
    iter_uig_tableaux_for_vector,
    kostka_standard_tableau_count,
    unit_interval_graph_tableau_count,
    unit_interval_graph_tableau_size,
)
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_llt_probes,
    evaluate_llt_polynomial_checks,
    evaluate_llt_submission,
    run_resource_gate,
    run_value_audit,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "q_statistic_discovery" / "uig_syt_llt_schur_q_stat"
PROBLEM_ID = 14
PROBLEM_NAME = "uig_syt_llt_schur_q_stat"


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def _edge_count(b) -> int:
    return sum(1 for i in range(1, len(b) + 1) for j in range(i + 1, b[i - 1] + 1))


def _by_partition(case) -> dict[tuple[int, ...], dict[int, int]]:
    out: dict[tuple[int, ...], dict[int, int]] = defaultdict(dict)
    for partition, q, coeff in case["terms"]:
        out[tuple(partition)][q] = coeff
    return out


def test_polynomials_are_schur_positive_transpose_symmetric_and_total_the_fiber():
    data = _polynomials()
    assert data["variables"] == ["partition", "q"]
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    seen_n = Counter()
    for case in data["cases"]:
        n = case["n"]
        b = tuple(case["b"])
        seen_n[n] += 1
        num_edges = _edge_count(b)
        by_partition = _by_partition(case)
        for _partition, poly in by_partition.items():
            assert all(coeff > 0 for coeff in poly.values())  # Schur positivity
            assert max(poly) <= num_edges
        for partition, poly in by_partition.items():
            # omega LLT_G(q) = q^{|E|} LLT_G(1/q), coefficientwise
            conjugate = tuple(
                sum(1 for part in partition if part > column) for column in range(partition[0])
            )
            assert by_partition[conjugate] == {num_edges - q: c for q, c in poly.items()}
        # the two extreme shapes pin the ends of the q-range
        assert by_partition[(n,)] == {0: 1}
        assert by_partition[tuple([1] * n)] == {num_edges: 1}
        assert sum(coeff for _p, _q, coeff in case["terms"]) == case["count"]
    # one fiber per Dyck graph (Catalan) at each size, up to n = 7
    for n, graphs in seen_n.items():
        assert graphs == comb(2 * n, n) // (n + 1)


def test_q_equals_1_is_the_shape_distribution():
    full = {c["case_id"]: c for c in _polynomials()["cases"]}
    marginal = json.loads((PROBLEM / "data" / "q_equals_1.json").read_text())
    assert marginal["variables"] == ["partition"]
    for case in marginal["cases"]:
        got = {tuple(partition): coeff for partition, coeff in case["terms"]}
        # c_lambda(1) = f^lambda, since LLT_G(X;1) = p_1^n
        assert got == {
            lam: kostka_standard_tableau_count(lam) for lam in iter_partitions(case["n"])
        }
        expected = defaultdict(int)
        for partition, _q, coeff in full[case["case_id"]]["terms"]:
            expected[tuple(partition)] += coeff
        assert got == dict(expected)
        assert sum(got.values()) == case["count"]


def test_complete_graph_coefficients_are_the_maj_generating_function():
    """Independent check: for ``K_n`` the Schur coefficient is ``sum_T q^maj(T)``.

    This classical evaluation of the unicellular LLT polynomial of the complete
    graph shares no code with the generator, which reads the target off colourings
    and the Kostka matrix.
    """
    for case in _polynomials()["cases"]:
        n = case["n"]
        if tuple(case["b"]) != tuple([n] * n):
            continue
        by_partition = _by_partition(case)
        for lam in iter_partitions(n):
            expected: Counter[int] = Counter()
            for rows in iter_standard_tableau_rows(lam):
                row_of = {value: r for r, row in enumerate(rows) for value in row}
                expected[sum(i for i in range(1, n) if row_of[i + 1] > row_of[i])] += 1
            assert by_partition[lam] == dict(expected)


def test_edgeless_graph_has_no_q_grading():
    for case in _polynomials()["cases"]:
        n = case["n"]
        if tuple(case["b"]) == tuple(range(1, n + 1)):
            assert all(q == 0 for _p, q, _c in case["terms"])


def test_permutation_marginal_matches_the_ascent_distribution():
    """Independent check of the change of basis: ``sum_lambda f^lambda c_lambda(q)``.

    Pairing ``LLT_G`` with ``h_1^n`` reads off the coefficient of
    ``x_1 x_2 ... x_n``, the ``q^{asc}`` distribution over the bijective
    colourings, which is computed here straight from the definition.
    """
    for case in _polynomials()["cases"]:
        n = case["n"]
        if n > 5:
            continue
        b = tuple(case["b"])
        expected: Counter[int] = Counter()
        for colouring in permutations(range(1, n + 1)):
            expected[
                sum(
                    1
                    for u in range(1, n + 1)
                    for v in range(u + 1, b[u - 1] + 1)
                    if colouring[u - 1] < colouring[v - 1]
                )
            ] += 1
        generated: Counter[int] = Counter()
        for partition, q, coeff in case["terms"]:
            generated[q] += coeff * kostka_standard_tableau_count(tuple(partition))
        assert generated == expected


def _reference_statistic():
    """A statistic witnessing that the target is realizable over the objects.

    Within each graph fiber and each shape, hand out the published exponents to
    the tableaux in encoding order. The ``strict=True`` zip also re-checks
    ``c_lambda(1) = f^lambda`` for every graph and shape.
    """
    mapping: dict[str, int] = {}
    for case in _polynomials()["cases"]:
        column = defaultdict(list)
        for partition, q, coeff in case["terms"]:
            column[tuple(partition)].extend([q] * coeff)
        fibers = defaultdict(list)
        for obj in iter_uig_tableaux_for_vector(tuple(case["b"])):
            fibers[obj.shape].append(obj.encoding)
        for shape, encodings in fibers.items():
            encodings.sort()
            for encoding, exponent in zip(encodings, sorted(column[shape]), strict=True):
                mapping[encoding] = exponent

    def lltstat(graph_tableau):
        return mapping[graph_tableau.encoding]

    return lltstat


def test_reference_statistic_reproduces_target_but_maj_does_not():
    result = evaluate_llt_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_statistic(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    # maj is the answer for the complete graph only, so it fails almost everywhere;
    # the shape marginal, which no statistic can influence, still passes.
    maj = evaluate_llt_polynomial_checks(problem_dir=PROBLEM, statistic=lambda obj: obj.maj())
    assert not maj["full_qt"]["passed"]
    assert maj["q_equals_1"]["passed"]


def test_valid_but_wrong_statistic_short_circuits_at_numerical_end_to_end():
    # The constant 0 is a valid exponent but wrong on every graph with an edge,
    # so it fails gracefully at the numerical stage before the value/resource gates.
    result = evaluate_llt_submission(
        source="def statistic(graph_tableau):\n    return 0\n",
        probes=lambda: adversarial_llt_probes(96),
        problem_dir=PROBLEM,
        timeout_seconds=2.0,
        numerical_timeout_seconds=120.0,
        max_python_bytes=64_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"
    assert result["value_audit"] is None


@pytest.mark.parametrize("invalid", [True, 1.0, "1", (0,)])
def test_statistic_must_return_a_nonnegative_int(invalid):
    with pytest.raises(TypeError, match="nonnegative integer"):
        evaluate_llt_polynomial_checks(problem_dir=PROBLEM, statistic=lambda _obj: invalid)
    with pytest.raises(ValueError, match="nonnegative integer"):
        evaluate_llt_polynomial_checks(problem_dir=PROBLEM, statistic=lambda _obj: -1)


def test_value_audit_wired_for_unit_interval_graph_tableaux():
    genuine = "def statistic(graph_tableau):\n    return graph_tableau.maj()\n"
    run_value_audit(
        genuine,
        adversarial_llt_probes(64),
        value_exponent=8,
        timeout_seconds=5.0,
        size_of=unit_interval_graph_tableau_size,
    )

    counting = (
        "def statistic(graph_tableau):\n"
        "    total = 1\n"
        "    for _ in range(graph_tableau.n):\n"
        "        total = total + total\n"
        "    return total\n"
    )
    with pytest.raises(ResourceGateError, match="magnitude bound|bit integer"):
        run_value_audit(
            counting,
            adversarial_llt_probes(64),
            value_exponent=8,
            timeout_seconds=5.0,
            size_of=unit_interval_graph_tableau_size,
        )


def test_resource_gate_accepts_a_polynomial_statistic_on_large_objects():
    genuine = "def statistic(graph_tableau):\n    return graph_tableau.maj()\n"
    probes = adversarial_llt_probes(256)
    report = run_resource_gate(
        genuine,
        probes,
        timeout_seconds=5.0,
        max_python_bytes=64_000_000,
    )
    assert len(report.results) == len(probes)


def test_object_totals_match_catalan_times_involutions():
    assert unit_interval_graph_tableau_count(5) == 42 * 26
