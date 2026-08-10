from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from fractions import Fraction
from itertools import combinations, combinations_with_replacement, permutations
from math import comb
from pathlib import Path

import pytest

from qtbench.combinatorics import (
    involution_count,
    involution_size,
    iter_involutions_with_fixed_points,
)
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_involution_probes,
    adversarial_involutions,
    evaluate_involution_polynomial_checks,
    evaluate_involution_submission,
    run_resource_gate,
    run_value_audit,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "q_statistic_discovery" / "inv_orbit_harmonics_hilbert_q_stat"
PROBLEM_ID = 15
PROBLEM_NAME = "inv_orbit_harmonics_hilbert_q_stat"


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def _load_problem_module(filename: str, name: str):
    spec = importlib.util.spec_from_file_location(name, PROBLEM / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _series(case) -> list[int]:
    """The case's Hilbert series as a dense coefficient list."""
    coefficients = {int(degree): int(coeff) for degree, coeff in case["terms"]}
    return [coefficients.get(degree, 0) for degree in range(max(coefficients) + 1)]


def test_float64_modular_elimination_enforces_its_exactness_threshold():
    oracle = _load_problem_module("orbit_harmonics_oracle.py", "orbit_harmonics_threshold")
    limit = oracle.float64_modular_point_limit()

    assert limit == 32768
    for prime in oracle.PRIMES:
        assert limit * (prime - 1) ** 2 < oracle.FLOAT64_EXACT_INTEGER_LIMIT
    assert any(
        (limit + 1) * (prime - 1) ** 2 >= oracle.FLOAT64_EXACT_INTEGER_LIMIT
        for prime in oracle.PRIMES
    )

    oracle._ModularBasis(limit, oracle.PRIMES[0])
    with pytest.raises(ValueError, match="supports at most 32768 points"):
        oracle._ModularBasis(limit + 1, oracle.PRIMES[0])


def test_generator_preflight_rejects_the_first_unsafe_public_loci():
    oracle = _load_problem_module("orbit_harmonics_oracle.py", "orbit_harmonics_preflight")
    generator = _load_problem_module("generate_data.py", "involution_generator_preflight")

    generator._validate_float64_preflight(oracle, public_max_n=11, permutation_max_n=7)
    with pytest.raises(ValueError, match=r"M_\{12,2\}.*62370.*32768"):
        generator._validate_float64_preflight(oracle, public_max_n=12, permutation_max_n=7)
    with pytest.raises(ValueError, match=r"S_8.*40320.*32768"):
        generator._validate_float64_preflight(oracle, public_max_n=11, permutation_max_n=8)


def test_exact_certificate_covers_and_matches_every_public_target():
    polynomial_path = PROBLEM / "data" / "polynomials.json"
    certificate = json.loads(
        (PROBLEM / "data" / "exact_certificate.json").read_text()
    )
    targets = {case["case_id"]: case for case in _polynomials()["cases"]}

    assert certificate["schema_version"] == "0.1"
    assert certificate["problem_id"] == PROBLEM_ID
    assert certificate["problem_name"] == PROBLEM_NAME
    assert certificate["method"] == "proof-enabled sparse row echelon form over QQ"
    assert certificate["sage_version"].startswith("SageMath version ")
    assert certificate["polynomials_sha256"] == hashlib.sha256(
        polynomial_path.read_bytes()
    ).hexdigest()
    assert certificate["case_count"] == len(certificate["cases"]) == len(targets)
    assert {case["case_id"] for case in certificate["cases"]} == set(targets)
    for certified in certificate["cases"]:
        target = targets[certified["case_id"]]
        assert certified["point_count"] == target["count"]
        assert certified["hilbert_series"] == _series(target)
        ranks = certified["cumulative_ranks"]
        assert [ranks[0], *[b - a for a, b in zip(ranks, ranks[1:])]] == _series(
            target
        )


def _longest_decreasing(word) -> int:
    piles: list[int] = []
    for value in word:
        low, high = 0, len(piles)
        while low < high:
            middle = (low + high) // 2
            if piles[middle] < value:
                high = middle
            else:
                low = middle + 1
        if low == len(piles):
            piles.append(value)
        else:
            piles[low] = value
    return len(piles)


# ---------------------------------------------------------------------------
# An independent rebuild of the definition: the degree filtration of C[X]
# ---------------------------------------------------------------------------


def _rank_filtration(points, monomials_of_degree, max_degree: int) -> list[int]:
    """``[dim V_0, dim V_1 - dim V_0, ...]`` by exact Gaussian elimination over Q.

    ``monomials_of_degree(d)`` yields, for each monomial of degree exactly ``d``, its
    vector of values on ``points``. No reduction of the spanning set and no modular
    arithmetic: this is the definition, spelled out, and it shares no code with the
    public oracle that produced the shipped targets.
    """
    basis: list[list[Fraction]] = []
    pivots: list[int] = []
    series: list[int] = []
    for degree in range(max_degree + 1):
        before = len(pivots)
        for values in monomials_of_degree(degree):
            row = [Fraction(value) for value in values]
            for pivot, earlier in zip(pivots, basis):
                if row[pivot]:
                    factor = row[pivot]
                    row = [x - factor * y for x, y in zip(row, earlier)]
            pivot = next((index for index, value in enumerate(row) if value), None)
            if pivot is None:
                continue
            inverse = 1 / row[pivot]
            row = [value * inverse for value in row]
            basis = [
                [x - earlier[pivot] * y for x, y in zip(earlier, row)]
                if earlier[pivot]
                else earlier
                for earlier in basis
            ]
            basis.append(row)
            pivots.append(pivot)
        series.append(len(pivots) - before)
        if len(pivots) == len(points):
            return series
    raise AssertionError("the spanning set does not span the function space")


def _partial_permutation_filtration(points, n: int) -> list[int]:
    """The filtration spanned by the squarefree monomials: partial permutations."""

    def monomials(degree: int):
        for rows in combinations(range(1, n + 1), degree):
            for columns in permutations(range(1, n + 1), degree):
                cells = tuple(zip(rows, columns))
                yield [
                    1 if all(point[i - 1] == j for i, j in cells) else 0
                    for point in points
                ]

    return _rank_filtration(points, monomials, n)


def _every_monomial_filtration(points, n: int) -> list[int]:
    """The filtration spanned by *every* monomial in the ``n^2`` matrix variables."""
    cells = [(i, j) for i in range(1, n + 1) for j in range(1, n + 1)]

    def monomials(degree: int):
        for multiset in combinations_with_replacement(cells, degree):
            values = []
            for point in points:
                product = 1
                for i, j in multiset:
                    product *= 1 if point[i - 1] == j else 0
                values.append(product)
            yield values

    return _rank_filtration(points, monomials, n)


def _fiber_points(n: int, a: int):
    return [obj.images for obj in iter_involutions_with_fixed_points(n, a)]


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
        n, a = case["n"], case["a"]
        seen.add((n, a))
        series = _series(case)
        assert all(coefficient > 0 for _degree, coefficient in case["terms"])
        assert series[0] == 1  # the degree-0 piece is the constants
        assert sum(series) == case["count"] == involution_count(n, a)
        # top degree (n - a)/2, one less on the fixed-point-free fiber
        expected_top = max((n - a) // 2 - (1 if a == 0 else 0), 0)
        assert len(series) - 1 == expected_top
    assert seen == {(n, a) for n in range(1, 11) for a in range(n % 2, n + 1, 2)}
    assert len(seen) == data["case_count"] == 35


def test_q_equals_1_is_the_fixed_point_distribution():
    full = {case["case_id"]: case for case in _polynomials()["cases"]}
    marginal = json.loads((PROBLEM / "data" / "q_equals_1.json").read_text())
    assert marginal["variables"] == ["fixed_points"]
    for case in marginal["cases"]:
        # H_{n,a}(1) = |M_{n,a}|: every object of the fiber has fix(pi) = a.
        assert case["terms"] == [[case["a"], involution_count(case["n"], case["a"])]]
        assert sum(coefficient for _a, coefficient in case["terms"]) == case["count"]
        assert case["count"] == full[case["case_id"]]["count"]


def test_instances_are_the_public_objects_of_their_fiber():
    instances = json.loads((PROBLEM / "data" / "instances.json").read_text())
    assert instances["object_family"] == "involutions"
    assert instances["known_statistics"] == []
    total = 0
    for case in instances["cases"]:
        expected = [obj.encoding for obj in iter_involutions_with_fixed_points(case["n"], case["a"])]
        assert case["entries"] == expected
        assert case["count"] == len(expected)
        total += case["count"]
    assert total == sum(
        involution_count(n, a) for n in range(1, 10) for a in range(n % 2, n + 1, 2)
    )


def test_fixed_point_free_fibers_are_the_lds_generating_function():
    """Liu--Ma--Rhoades--Zhu, recomputed from the enumerated fiber.

    ``H_{n,0}(q) = sum_pi q^{(n - lds(pi))/2}`` is the one solved instance, and it
    shares no code with the linear algebra that produced the targets.
    """
    for case in _polynomials()["cases"]:
        if case["a"]:
            continue
        n = case["n"]
        expected: Counter[int] = Counter()
        for obj in iter_involutions_with_fixed_points(n, 0):
            length = _longest_decreasing(obj.images)
            assert (n - length) % 2 == 0
            expected[(n - length) // 2] += 1
        assert _series(case) == [expected[degree] for degree in range(max(expected) + 1)]


def test_degenerate_fibers_have_their_closed_forms():
    for case in _polynomials()["cases"]:
        n, a = case["n"], case["a"]
        if a == n:
            assert _series(case) == [1]  # the fiber is the identity alone
        if a == n - 2:
            # x_{ij} restricted to the transposition locus is the indicator of (i j),
            # so V_1 is everything.
            assert _series(case) == [1, comb(n, 2) - 1][: len(_series(case))]


def test_regularities_of_the_public_table():
    """Two patterns the shipped table satisfies; neither is claimed as a theorem."""
    series = {(case["n"], case["a"]): _series(case) for case in _polynomials()["cases"]}
    for n in range(4, 11, 2):
        assert series[(n, 0)] == series[(n - 1, 1)]
    pairs = [(n, a) for (n, a) in series if a >= 3 and (n, a + 2) in series]
    assert len(pairs) == 12
    for n, a in pairs:
        assert series[(n, a + 2)] == series[(n, a)][:-1]


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5])
def test_orbit_harmonics_definition_reproduces_the_shipped_series(n):
    """Rebuild ``dim V_d - dim V_{d-1}`` over Q from unreduced monomials."""
    shipped = {(case["n"], case["a"]): _series(case) for case in _polynomials()["cases"]}
    for a in range(n % 2, n + 1, 2):
        points = _fiber_points(n, a)
        assert _partial_permutation_filtration(points, n) == shipped[(n, a)]


@pytest.mark.parametrize("n", [1, 2, 3])
def test_every_monomial_gives_the_same_filtration(n):
    """The same check with no reduction of the spanning set at all."""
    shipped = {(case["n"], case["a"]): _series(case) for case in _polynomials()["cases"]}
    for a in range(n % 2, n + 1, 2):
        points = _fiber_points(n, a)
        assert _every_monomial_filtration(points, n) == shipped[(n, a)]


@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_the_same_filtration_answers_the_permutation_matrix_locus(n):
    """Rhoades: the *full* permutation matrix locus gives ``sum_w q^{n - lis(w)}``.

    A published answer for a locus this problem never uses, so it validates the
    rebuilt filtration itself rather than the involution targets.
    """
    words = list(permutations(range(1, n + 1)))
    expected: Counter[int] = Counter()
    for word in words:
        expected[n - _longest_decreasing([-value for value in word])] += 1
    assert _partial_permutation_filtration(words, n) == [
        expected[degree] for degree in range(max(expected) + 1)
    ]


# ---------------------------------------------------------------------------
# The checker adapter
# ---------------------------------------------------------------------------


def _reference_statistic():
    """A statistic witnessing that the target is realizable over the objects.

    Within each fiber, hand out the published exponents to the involutions in
    encoding order. The ``strict=True`` zip also re-checks ``H_{n,a}(1) = |M_{n,a}|``
    for every fiber.
    """
    mapping: dict[str, int] = {}
    for case in _polynomials()["cases"]:
        exponents: list[int] = []
        for degree, coefficient in case["terms"]:
            exponents.extend([degree] * coefficient)
        encodings = sorted(
            obj.encoding for obj in iter_involutions_with_fixed_points(case["n"], case["a"])
        )
        for encoding, exponent in zip(encodings, exponents, strict=True):
            mapping[encoding] = exponent

    def istat(obj):
        return mapping[obj.encoding]

    return istat


def _template_statistic():
    source = (ROOT / "examples" / "involution_moved_lds_submission.py").read_text()
    namespace: dict = {}
    exec(compile(source, "involution_moved_lds_submission.py", "exec"), namespace)
    return namespace["statistic"]


def test_reference_statistic_reproduces_target_but_the_template_does_not():
    result = evaluate_involution_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_statistic(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    template = evaluate_involution_polynomial_checks(
        problem_dir=PROBLEM, statistic=_template_statistic()
    )
    assert not template["full_qt"]["passed"]
    # the fixed-point marginal, which no statistic can influence, still passes
    assert template["q_equals_1"]["passed"]


def test_template_is_right_on_the_solved_fibers_only():
    template = _template_statistic()
    correct = {
        (case["n"], case["a"])
        for case in evaluate_involution_polynomial_checks(
            problem_dir=PROBLEM, statistic=template
        )["full_qt"]["case_results"]
        if case["correct"]
    }
    # problem.md claims exactly this: right on a = 0 and a = n, wrong in between
    solved = {(n, a) for n in range(1, 11) for a in (0, n) if (n - a) % 2 == 0}
    assert correct == solved
    assert (4, 2) not in correct  # the transposition fiber is not answered


def test_valid_but_wrong_statistic_short_circuits_at_numerical_end_to_end():
    # The constant 0 is a valid exponent but wrong on every fiber with more than one
    # object, so it fails gracefully at the numerical stage before the later gates.
    result = evaluate_involution_submission(
        source="def statistic(involution):\n    return 0\n",
        probes=lambda: adversarial_involution_probes(96),
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
        evaluate_involution_polynomial_checks(
            problem_dir=PROBLEM, statistic=lambda _obj: invalid
        )
    with pytest.raises(ValueError, match="nonnegative integer"):
        evaluate_involution_polynomial_checks(problem_dir=PROBLEM, statistic=lambda _obj: -1)


def test_probes_cover_a_spread_of_fibers_of_one_size():
    objects = adversarial_involutions(64, seed=7)
    assert {obj.n for obj in objects} == {64}
    assert {obj.fix for obj in objects} == {0, 16, 32, 48, 64}
    assert all(obj.encoding == obj.to_jsonable() for obj in objects)
    odd = adversarial_involutions(65, seed=7)
    assert all(obj.fix % 2 == 1 for obj in odd)


def test_value_audit_wired_for_involutions():
    genuine = "def statistic(involution):\n    return involution.fix\n"
    run_value_audit(
        genuine,
        adversarial_involution_probes(64),
        value_exponent=8,
        timeout_seconds=5.0,
        size_of=involution_size,
    )

    counting = (
        "def statistic(involution):\n"
        "    total = 1\n"
        "    for _ in range(involution.n):\n"
        "        total = total + total\n"
        "    return total\n"
    )
    with pytest.raises(ResourceGateError, match="magnitude bound|bit integer"):
        run_value_audit(
            counting,
            adversarial_involution_probes(64),
            value_exponent=8,
            timeout_seconds=5.0,
            size_of=involution_size,
        )


def test_resource_gate_accepts_a_polynomial_statistic_on_large_objects():
    genuine = "def statistic(involution):\n    return len(involution.rsk_shape)\n"
    probes = adversarial_involution_probes(256)
    report = run_resource_gate(
        genuine,
        probes,
        timeout_seconds=5.0,
        max_python_bytes=64_000_000,
    )
    assert len(report.results) == len(probes)


def test_object_totals_match_the_involution_numbers():
    assert [
        sum(involution_count(n, a) for a in range(n % 2, n + 1, 2)) for n in range(1, 11)
    ] == [1, 2, 4, 10, 26, 76, 232, 764, 2620, 9496]


def test_the_public_range_holds_every_fiber_of_its_sizes():
    results = evaluate_involution_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_statistic()
    )["full_qt"]["case_results"]
    assert sum(case["count"] for case in results) == 13231
    assert {(case["n"], case["a"]) for case in results} == {
        (n, a) for n in range(1, 11) for a in range(n % 2, n + 1, 2)
    }
