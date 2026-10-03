from __future__ import annotations

import importlib.util
import json
from collections import Counter
from itertools import permutations
from pathlib import Path

import pytest

from qtbench.combinatorics import (
    iter_gamma_permutations_for_descents,
)
from qtbench.evaluation import (
    adversarial_gamma_permutations,
    adversarial_qgamma_probes,
    evaluate_qgamma_polynomial_checks,
    evaluate_qgamma_submission,
    run_resource_gate,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "q_statistic_discovery" / "perm_q_eulerian_gamma_q_stat"
PROBLEM_ID = 17
PROBLEM_NAME = "perm_q_eulerian_gamma_q_stat"
PUBLIC_MAX_N = 9
BRUTE_MAX_N = 7

# Table 1 of Han-Jouhet-Zeng: the classical Eulerian gamma-coefficients a_{n,k}.
CLASSICAL_GAMMA = {
    1: [1], 2: [1], 3: [1, 2], 4: [1, 8], 5: [1, 22, 16], 6: [1, 52, 136],
}
# The tangent numbers, which a_{2m+1,m+1}(1) must reproduce.
TANGENT = [1, 2, 16, 272, 7936]


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def _load_oracle():
    spec = importlib.util.spec_from_file_location(
        "qgamma_carlitz_oracle", PROBLEM / "q_eulerian_oracle.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _coefficients(case) -> list[int]:
    terms = {int(degree): int(value) for degree, value in case["terms"]}
    return [terms.get(degree, 0) for degree in range(max(terms) + 1)]


# ---------------------------------------------------------------------------
# An independent rebuild: A_n(t,q) over the whole symmetric group
# ---------------------------------------------------------------------------


def _add(left, right):
    out = [0] * max(len(left), len(right))
    for index, value in enumerate(left):
        out[index] += value
    for index, value in enumerate(right):
        out[index] += value
    while out and out[-1] == 0:
        out.pop()
    return out


def _subtract(left, right):
    return _add(left, [-value for value in right])


def _multiply(left, right):
    if not left or not right:
        return []
    out = [0] * (len(left) + len(right) - 1)
    for i, x in enumerate(left):
        for j, y in enumerate(right):
            out[i + j] += x * y
    while out and out[-1] == 0:
        out.pop()
    return out


def _shift(poly, power):
    return [0] * power + list(poly) if poly else []


def _q_integer(m):
    return [1] * m if m > 0 else []


def _q_eulerian_brute(n):
    """``A_n(t,q) = sum_{sigma in S_n} t^{des sigma} q^{maj sigma}``, by enumeration."""
    out = [[] for _ in range(n)]
    for word in permutations(range(1, n + 1)):
        descents = [i for i in range(1, n) if word[i - 1] > word[i]]
        out[len(descents)] = _add(out[len(descents)], _shift([1], sum(descents)))
    while out and not out[-1]:
        out.pop()
    return out


def _gamma_from_expansion(n):
    """Solve ``A_n(t,q) = sum_k a_{n,k}(q) t^{k-1} (-tq^k;q)_{n+1-2k}`` for the ``a``."""
    remainder = [list(coefficient) for coefficient in _q_eulerian_brute(n)]
    while len(remainder) < n + 1:
        remainder.append([])
    out = {}
    for k in range(1, (n + 1) // 2 + 1):
        basis = [[1]]
        for i in range(n + 1 - 2 * k):
            new = [[] for _ in range(len(basis) + 1)]
            for degree, coefficient in enumerate(basis):
                new[degree] = _add(new[degree], coefficient)
                new[degree + 1] = _add(new[degree + 1], _shift(coefficient, k + i))
            basis = new
        basis = [[]] * (k - 1) + basis
        coefficient = remainder[k - 1]
        if not coefficient:
            continue
        out[k] = list(coefficient)
        for degree, piece in enumerate(basis):
            if degree < len(remainder):
                remainder[degree] = _subtract(remainder[degree], _multiply(coefficient, piece))
    assert not any(remainder), f"n={n}: the expansion left a residue"
    return out


# ---------------------------------------------------------------------------
# The shipped targets
# ---------------------------------------------------------------------------


def test_polynomials_are_positive_and_total_the_fiber():
    data = _polynomials()
    assert data["variables"] == ["q"]
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    seen = set()
    for case in data["cases"]:
        n, k = case["n"], case["k"]
        seen.add((n, k))
        coefficients = _coefficients(case)
        assert all(value > 0 for _degree, value in case["terms"])
        assert sum(coefficients) == case["count"]
        # support: [binom(k,2), binom(k,2) + (k-1)(n-k)]
        low = k * (k - 1) // 2
        assert next(index for index, value in enumerate(coefficients) if value) == low
        assert len(coefficients) - 1 == low + (k - 1) * (n - k)
        # After removing q^low, every a_{n,k}(q) in the public range is palindromic.
        window = coefficients[low:]
        assert window == window[::-1]
    assert seen == {
        (n, k) for n in range(1, PUBLIC_MAX_N + 1) for k in range(1, (n + 1) // 2 + 1)
    }
    assert len(seen) == data["case_count"] == 25


def test_q_equals_1_is_the_classical_gamma_triangle():
    """``a_{n,k}(1)`` against Table 1 of Han-Jouhet-Zeng, transcribed by hand."""
    by_size: dict[int, list[int]] = {}
    for case in _polynomials()["cases"]:
        by_size.setdefault(case["n"], []).append((case["k"], sum(_coefficients(case))))
    for n, expected in CLASSICAL_GAMMA.items():
        assert [value for _k, value in sorted(by_size[n])] == expected


def test_odd_middle_coefficients_are_the_tangent_numbers():
    """``a_{2m+1,m+1}(1) = 1, 2, 16, 272, 7936``: the classical tangent numbers."""
    got = [
        sum(_coefficients(case))
        for case in _polynomials()["cases"]
        if case["n"] % 2 and case["k"] == (case["n"] + 1) // 2
    ]
    assert got == TANGENT


def test_q_equals_1_marginal_is_the_descent_count_and_fiber_size():
    full = {case["case_id"]: case for case in _polynomials()["cases"]}
    marginal = json.loads((PROBLEM / "data" / "q_equals_1.json").read_text())
    assert marginal["variables"] == ["descents"]
    for case in marginal["cases"]:
        n, k = case["n"], case["k"]
        size = sum(1 for _ in iter_gamma_permutations_for_descents(n, k))
        # a_{n,k}(1) = |Gamma_{n,k}|
        assert case["terms"] == [[k - 1, size]]
        assert case["count"] == size == sum(_coefficients(full[case["case_id"]]))


@pytest.mark.parametrize("n", list(range(1, BRUTE_MAX_N + 1)))
def test_expansion_solved_over_the_symmetric_group_reproduces_the_targets(n):
    """Rebuild ``a_{n,k}(q)`` with no recurrence: enumerate ``S_n``, then solve.

    ``A_n(t,q)`` is recomputed as the joint descent/major-index enumerator over the
    whole symmetric group and the expansion is solved triangularly, which shares no
    code with the recurrence the generator used.
    """
    shipped = {
        case["k"]: _coefficients(case) for case in _polynomials()["cases"] if case["n"] == n
    }
    assert _gamma_from_expansion(n) == shipped


@pytest.mark.parametrize("n", list(range(1, BRUTE_MAX_N + 1)))
def test_carlitz_defining_identity_holds(n):
    """``sum_j [j+1]_q^n t^j = A_n(t,q) / (t;q)_{n+1}`` as a truncated power series."""
    eulerian = _q_eulerian_brute(n)
    denominator = [[1]]
    for i in range(n + 1):
        new = [[] for _ in range(len(denominator) + 1)]
        for degree, coefficient in enumerate(denominator):
            new[degree] = _add(new[degree], coefficient)
            new[degree + 1] = _subtract(new[degree + 1], _shift(coefficient, i))
        denominator = new
    order = 6
    powers = []
    for j in range(order + 1):
        power = [1]
        for _ in range(n):
            power = _multiply(power, _q_integer(j + 1))
        powers.append(power)
    for degree in range(order + 1):
        accumulated: list[int] = []
        for offset, coefficient in enumerate(denominator):
            if degree - offset >= 0:
                accumulated = _add(accumulated, _multiply(coefficient, powers[degree - offset]))
        assert accumulated == (eulerian[degree] if degree < len(eulerian) else [])


def test_carlitz_default_order_reaches_the_first_zero_coefficient(monkeypatch):
    oracle = _load_oracle()
    original_power = oracle._power

    def corrupted_power(poly, exponent):
        result = original_power(poly, exponent)
        if len(poly) == 10:  # the t^9 series coefficient [10]_q^9
            result = list(result)
            result[0] += 1
        return result

    monkeypatch.setattr(oracle, "_power", corrupted_power)
    assert oracle.carlitz_identity_residue(9, order=8) is None
    assert oracle.carlitz_identity_residue(9) == 9


def test_instances_are_the_public_objects_of_their_fiber():
    instances = json.loads((PROBLEM / "data" / "instances.json").read_text())
    assert instances["object_family"] == "gamma_permutations"
    assert instances["known_statistics"] == []
    for case in instances["cases"]:
        expected = [
            obj.encoding
            for obj in iter_gamma_permutations_for_descents(case["n"], case["k"])
        ]
        assert case["entries"] == expected
        assert case["count"] == len(expected)


# ---------------------------------------------------------------------------
# The checker adapter
# ---------------------------------------------------------------------------


def _reference_statistic():
    """A statistic witnessing that the target is realizable over the objects.

    Within each fiber, hand out the published exponents to the permutations in
    encoding order. The ``strict=True`` zip also re-checks ``a_{n,k}(1) =
    |Gamma_{n,k}|`` for every fiber.
    """
    mapping: dict[str, int] = {}
    for case in _polynomials()["cases"]:
        exponents: list[int] = []
        for degree, value in case["terms"]:
            exponents.extend([degree] * value)
        encodings = sorted(
            obj.encoding
            for obj in iter_gamma_permutations_for_descents(case["n"], case["k"])
        )
        for encoding, exponent in zip(encodings, exponents, strict=True):
            mapping[encoding] = exponent

    def qgamma(obj):
        return mapping[obj.encoding]

    return qgamma


def _template_statistic():
    source = (ROOT / "examples" / "qgamma_inv_submission.py").read_text()
    namespace: dict = {}
    exec(compile(source, "qgamma_inv_submission.py", "exec"), namespace)
    return namespace["statistic"]


def test_reference_statistic_reproduces_target_but_the_template_does_not():
    result = evaluate_qgamma_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_statistic(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    template = evaluate_qgamma_polynomial_checks(
        problem_dir=PROBLEM, statistic=_template_statistic()
    )
    assert not template["full_qt"]["passed"]
    # the descent marginal, which no statistic can influence, still passes
    assert template["q_equals_1"]["passed"]
    correct = {
        (case["n"], case["k"])
        for case in template["full_qt"]["case_results"]
        if case["correct"]
    }
    # inv is right on the singleton fibers and on Gamma_{3,2}, and nowhere else
    assert correct == {(n, 1) for n in range(1, PUBLIC_MAX_N + 1)} | {(3, 2)}


def test_maj_is_wrong_on_every_nontrivial_fiber():
    """The statistic that grades ``A_n(t,q)`` itself does not grade its gamma part."""
    result = evaluate_qgamma_polynomial_checks(
        problem_dir=PROBLEM, statistic=lambda obj: obj.maj()
    )
    correct = {
        (case["n"], case["k"])
        for case in result["full_qt"]["case_results"]
        if case["correct"]
    }
    assert correct == {(n, 1) for n in range(1, PUBLIC_MAX_N + 1)}


def test_valid_but_wrong_statistic_short_circuits_at_numerical_end_to_end():
    result = evaluate_qgamma_submission(
        source="def statistic(permutation):\n    return 0\n",
        probes=lambda: adversarial_qgamma_probes(96),
        problem_dir=PROBLEM,
        timeout_seconds=2.0,
        numerical_timeout_seconds=120.0,
        max_python_bytes=64_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"


@pytest.mark.parametrize("invalid", [True, 1.0, "1", (0,)])
def test_statistic_must_return_a_nonnegative_int(invalid):
    with pytest.raises(TypeError, match="nonnegative integer"):
        evaluate_qgamma_polynomial_checks(problem_dir=PROBLEM, statistic=lambda _obj: invalid)
    with pytest.raises(ValueError, match="nonnegative integer"):
        evaluate_qgamma_polynomial_checks(problem_dir=PROBLEM, statistic=lambda _obj: -1)


def test_probes_span_a_spread_of_fibers_of_one_size():
    objects = adversarial_gamma_permutations(64, seed=13)
    assert {obj.n for obj in objects} == {64}
    assert sorted({obj.descents + 1 for obj in objects}) == [1, 8, 16, 24, 32]
    odd = adversarial_gamma_permutations(65, seed=13)
    assert all(1 <= obj.descents + 1 <= 33 for obj in odd)




def test_resource_gate_accepts_a_polynomial_statistic_on_large_objects():
    genuine = (ROOT / "examples" / "qgamma_inv_submission.py").read_text()
    probes = adversarial_qgamma_probes(256)
    report = run_resource_gate(
        genuine,
        probes,
        timeout_seconds=5.0,
        max_python_bytes=64_000_000,
    )
    assert len(report.results) == len(probes)


def test_object_totals_match_the_gamma_triangle():
    data = _polynomials()
    assert sum(case["count"] for case in data["cases"]) == 62981
    by_size: Counter[int] = Counter()
    for case in data["cases"]:
        by_size[case["n"]] += case["count"]
    assert [by_size[n] for n in range(1, PUBLIC_MAX_N + 1)] == [
        1, 1, 3, 9, 39, 189, 1107, 7281, 54351
    ]
