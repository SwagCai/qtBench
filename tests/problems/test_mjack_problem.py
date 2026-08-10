from __future__ import annotations

import json
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

import pytest

from qtbench.combinatorics import (
    canonical_jack_matching,
    iter_jack_matchings_for_partition,
    iter_partitions,
    jack_matching_size,
)
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_jack_matchings,
    adversarial_mjack_probes,
    evaluate_mjack_polynomial_checks,
    evaluate_mjack_submission,
    run_resource_gate,
    run_value_audit,
)
from qtbench.evaluation import admission

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "q_statistic_discovery" / "match_jack_connection_q_stat"
PROBLEM_ID = 16
PROBLEM_NAME = "match_jack_connection_q_stat"
PUBLIC_MAX_N = 6


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def _by_fiber(case) -> dict[tuple[tuple[int, ...], tuple[int, ...]], dict[int, int]]:
    out: dict[tuple[tuple[int, ...], tuple[int, ...]], dict[int, int]] = defaultdict(dict)
    for pi, sigma, q, coefficient in case["terms"]:
        out[(tuple(pi), tuple(sigma))][q] = coefficient
    return out


def _double_factorial(n: int) -> int:
    value = 1
    for size in range(1, 2 * n, 2):
        value *= size
    return value


def _enumerate_case(lam: tuple[int, ...]) -> tuple[Counter, Counter]:
    """``(fiber sizes, bipartite counts)`` keyed by ``(pi, sigma)``."""
    sizes: Counter = Counter()
    bipartite: Counter = Counter()
    for obj in iter_jack_matchings_for_partition(lam):
        key = (obj.epsilon_type(), obj.reference_type())
        sizes[key] += 1
        if obj.is_bipartite:
            bipartite[key] += 1
    return sizes, bipartite


def _class_algebra_constants(n: int) -> dict:
    """``{(lambda, pi, sigma): a}`` counted by brute force in ``S_n``.

    ``a`` is the number of ways to write one fixed permutation of cycle type
    ``lambda`` as a product of a permutation of type ``pi`` and one of type ``sigma``:
    the classical ``beta = 0`` specialization of the connection coefficients, with no
    Jack symmetric function anywhere in sight.
    """

    def cycle_type(word) -> tuple[int, ...]:
        seen = [False] * n
        lengths = []
        for start in range(n):
            if seen[start]:
                continue
            length = 0
            node = start
            while not seen[node]:
                seen[node] = True
                node = word[node]
                length += 1
            lengths.append(length)
        return tuple(sorted(lengths, reverse=True))

    by_type: dict = defaultdict(list)
    for word in permutations(range(n)):
        by_type[cycle_type(word)].append(word)

    out: dict = {}
    for lam in iter_partitions(n):
        target = by_type[lam][0]
        for pi in iter_partitions(n):
            counts: Counter = Counter()
            for word in by_type[pi]:
                inverse = [0] * n
                for index, image in enumerate(word):
                    inverse[image] = index
                counts[cycle_type([target[inverse[i]] for i in range(n)])] += 1
            for sigma in iter_partitions(n):
                out[(lam, pi, sigma)] = counts.get(sigma, 0)
    return out


# ---------------------------------------------------------------------------
# The shipped targets
# ---------------------------------------------------------------------------


def test_polynomials_are_positive_and_total_the_case():
    data = _polynomials()
    assert data["variables"] == ["pi", "sigma", "q"]
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    seen = set()
    for case in data["cases"]:
        n = case["n"]
        lam = tuple(case["lambda"])
        seen.add((n, lam))
        assert all(coefficient > 0 for *_key, coefficient in case["terms"])
        assert sum(coefficient for *_key, coefficient in case["terms"]) == case["count"]
        assert case["count"] == _double_factorial(n)
        for (pi, sigma), poly in _by_fiber(case).items():
            # Dolega-Feray: deg_beta c <= (n - l(pi)) + (n - l(sigma)) - (n - l(lambda))
            assert max(poly) <= (n - len(pi)) + (n - len(sigma)) - (n - len(lam))
    assert seen == {(n, lam) for n in range(1, PUBLIC_MAX_N + 1) for lam in iter_partitions(n)}
    assert len(seen) == data["case_count"] == 29


def test_target_is_symmetric_in_pi_and_sigma():
    """The Cauchy sum is symmetric in ``x`` and ``y``, so ``c^lam_{pi,sigma}`` is too."""
    for case in _polynomials()["cases"]:
        by_fiber = _by_fiber(case)
        for (pi, sigma), poly in by_fiber.items():
            assert by_fiber.get((sigma, pi)) == poly


def test_the_two_sharp_fibers_are_single_bipartite_matchings():
    """``Lambda(d, eps) = (1^n)`` forces ``d = eps``, and likewise for ``delta_lambda``.

    So the fibers indexed by ``(1^n)`` hold exactly one matching, it is bipartite, and
    the coefficient is the constant ``1``.
    """
    for case in _polynomials()["cases"]:
        n = case["n"]
        lam = tuple(case["lambda"])
        column = tuple([1] * n)
        by_fiber = _by_fiber(case)
        assert by_fiber[(column, lam)] == {0: 1}
        assert by_fiber[(lam, column)] == {0: 1}
        assert all(pi != column or sigma == lam for pi, sigma in by_fiber)
        assert all(sigma != column or pi == lam for pi, sigma in by_fiber)
        if lam == column:
            # delta_lambda = eps, so the two cycle types coincide on every object
            assert all(pi == sigma for pi, sigma in by_fiber)


def test_q_equals_1_is_the_table_of_fiber_sizes():
    full = {case["case_id"]: case for case in _polynomials()["cases"]}
    marginal = json.loads((PROBLEM / "data" / "q_equals_1.json").read_text())
    assert marginal["variables"] == ["pi", "sigma"]
    for case in marginal["cases"]:
        lam = tuple(case["lambda"])
        got = {(tuple(pi), tuple(sigma)): coefficient for pi, sigma, coefficient in case["terms"]}
        sizes, _bipartite = _enumerate_case(lam)
        # c^lambda_{pi,sigma}(1) = |G^lambda_{pi,sigma}|
        assert got == {key: value for key, value in sizes.items() if value}
        assert sum(got.values()) == case["count"] == _double_factorial(case["n"])
        expected = defaultdict(int)
        for pi, sigma, _q, coefficient in full[case["case_id"]]["terms"]:
            expected[(tuple(pi), tuple(sigma))] += coefficient
        assert got == dict(expected)


def test_constant_terms_count_the_bipartite_matchings():
    """``c^lambda_{pi,sigma}(0)`` against the enumerated fiber, not against Jack."""
    for case in _polynomials()["cases"]:
        lam = tuple(case["lambda"])
        sizes, bipartite = _enumerate_case(lam)
        by_fiber = _by_fiber(case)
        for key in sizes:
            assert by_fiber.get(key, {}).get(0, 0) == bipartite.get(key, 0)
        assert sum(poly.get(0, 0) for poly in by_fiber.values()) == sum(bipartite.values())


def test_constant_terms_are_the_class_algebra_structure_constants():
    """The same constant terms against a brute-force count of factorizations in ``S_n``.

    At ``beta = 0`` the Jack Cauchy sum degenerates to the Schur one, so the constant
    term is the classical class-algebra structure constant. Counting those in ``S_n``
    shares nothing with the Jack computation that produced the targets, nor with the
    matchings of the previous check.
    """
    for n in range(1, PUBLIC_MAX_N + 1):
        constants = _class_algebra_constants(n)
        for case in _polynomials()["cases"]:
            if case["n"] != n:
                continue
            lam = tuple(case["lambda"])
            by_fiber = _by_fiber(case)
            for pi in iter_partitions(n):
                for sigma in iter_partitions(n):
                    assert by_fiber.get((pi, sigma), {}).get(0, 0) == constants[(lam, pi, sigma)]


def test_instances_are_the_public_objects_of_their_case():
    instances = json.loads((PROBLEM / "data" / "instances.json").read_text())
    assert instances["object_family"] == "jack_matchings"
    assert instances["known_statistics"] == []
    for case in instances["cases"]:
        lam = tuple(case["lambda"])
        expected = [obj.encoding for obj in iter_jack_matchings_for_partition(lam)]
        assert case["entries"] == expected
        assert case["count"] == len(expected) == _double_factorial(case["n"])


# ---------------------------------------------------------------------------
# The checker adapter
# ---------------------------------------------------------------------------


def _reference_statistic():
    """A statistic witnessing that the target is realizable over the objects.

    Within each case and each ``(pi, sigma)`` fiber, hand out the published exponents
    to the matchings in encoding order. The ``strict=True`` zip also re-checks
    ``c^lambda_{pi,sigma}(1) = |G^lambda_{pi,sigma}|`` for every fiber.
    """
    mapping: dict[str, int] = {}
    for case in _polynomials()["cases"]:
        column = defaultdict(list)
        for pi, sigma, q, coefficient in case["terms"]:
            column[(tuple(pi), tuple(sigma))].extend([q] * coefficient)
        fibers = defaultdict(list)
        for obj in iter_jack_matchings_for_partition(tuple(case["lambda"])):
            fibers[(obj.epsilon_type(), obj.reference_type())].append(obj)
        for key, objects in fibers.items():
            bipartite = sorted(
                (obj for obj in objects if obj.is_bipartite), key=lambda obj: obj.encoding
            )
            nonbipartite = sorted(
                (obj for obj in objects if not obj.is_bipartite), key=lambda obj: obj.encoding
            )
            exponents = sorted(column[key])
            assert exponents.count(0) == len(bipartite)
            for obj in bipartite:
                mapping[obj.encoding] = 0
            for obj, exponent in zip(
                nonbipartite, (value for value in exponents if value > 0), strict=True
            ):
                mapping[obj.encoding] = exponent

    def mjack(obj):
        return mapping[obj.encoding]

    return mjack


def _template_statistic():
    source = (ROOT / "examples" / "mjack_within_class_submission.py").read_text()
    namespace: dict = {}
    exec(compile(source, "mjack_within_class_submission.py", "exec"), namespace)
    return namespace["statistic"]


def test_reference_statistic_reproduces_target_but_the_template_does_not():
    result = evaluate_mjack_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_statistic(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    template = evaluate_mjack_polynomial_checks(
        problem_dir=PROBLEM, statistic=_template_statistic()
    )
    assert not template["full_qt"]["passed"]
    # the fiber-size marginal, which no statistic can influence, still passes
    assert template["q_equals_1"]["passed"]
    correct = sum(case["correct"] for case in template["full_qt"]["case_results"])
    assert correct == 3


def test_template_vanishes_exactly_on_the_bipartite_matchings():
    """The one anchor the conjecture states outright, on the shipped template."""
    template = _template_statistic()
    for n in range(1, 5):
        for lam in iter_partitions(n):
            for obj in iter_jack_matchings_for_partition(lam):
                assert (template(obj) == 0) == obj.is_bipartite


def test_distribution_preserving_zero_locus_swap_is_rejected():
    reference = _reference_statistic()
    values = {}
    groups = defaultdict(list)
    for lam in iter_partitions(4):
        for obj in iter_jack_matchings_for_partition(lam):
            values[obj.encoding] = reference(obj)
            groups[(lam, obj.epsilon_type(), obj.reference_type())].append(obj)

    for objects in groups.values():
        bipartite = next((obj for obj in objects if obj.is_bipartite), None)
        nonbipartite = next(
            (obj for obj in objects if not obj.is_bipartite and values[obj.encoding] > 0),
            None,
        )
        if bipartite is not None and nonbipartite is not None:
            values[bipartite.encoding], values[nonbipartite.encoding] = (
                values[nonbipartite.encoding],
                values[bipartite.encoding],
            )
            break
    else:
        raise AssertionError("no mixed Matchings-Jack fiber found")

    result = evaluate_mjack_polynomial_checks(
        problem_dir=PROBLEM,
        statistic=lambda obj: values.get(obj.encoding, reference(obj)),
    )
    assert not result["passed"]
    assert any(
        case["zero_locus_failure"]
        for case in result["full_qt"]["case_results"]
    )


def test_large_probe_zero_locus_is_checked_pointwise():
    objects = adversarial_jack_matchings(64, seed=11)
    calls = [("statistic", (obj,)) for obj in objects]
    valid = admission.ResourceReport(
        0.0, 0, tuple(0 if obj.is_bipartite else 1 for obj in objects)
    )
    admission._validate_mjack_probe_results(valid, calls)

    invalid = admission.ResourceReport(
        0.0, 0, tuple(1 if obj.is_bipartite else 0 for obj in objects)
    )
    with pytest.raises(ResourceGateError, match="zero exactly on bipartite"):
        admission._validate_mjack_probe_results(invalid, calls)


def test_valid_but_wrong_statistic_short_circuits_at_numerical_end_to_end():
    # The constant 0 is a valid exponent but wrong wherever a fiber has a
    # non-bipartite matching, so it fails at the numerical stage before the later
    # gates.
    result = evaluate_mjack_submission(
        source="def statistic(jack_matching):\n    return 0\n",
        probes=lambda: adversarial_mjack_probes(96),
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
        evaluate_mjack_polynomial_checks(problem_dir=PROBLEM, statistic=lambda _obj: invalid)
    with pytest.raises(ValueError, match="nonnegative integer"):
        evaluate_mjack_polynomial_checks(problem_dir=PROBLEM, statistic=lambda _obj: -1)


def test_probes_span_bipartite_and_non_bipartite_objects_of_one_size():
    objects = adversarial_jack_matchings(64, seed=11)
    assert {obj.n for obj in objects} == {64}
    assert any(obj.is_bipartite for obj in objects)
    assert any(not obj.is_bipartite for obj in objects)
    assert len({obj.lam for obj in objects}) > 1
    assert all(sum(obj.lam) == 64 for obj in objects)


def test_value_audit_wired_for_jack_matchings():
    genuine = (
        "def statistic(jack_matching):\n"
        "    return jack_matching.n - len(jack_matching.lam)\n"
    )
    run_value_audit(
        genuine,
        adversarial_mjack_probes(64),
        value_exponent=8,
        timeout_seconds=5.0,
        size_of=jack_matching_size,
    )

    counting = (
        "def statistic(jack_matching):\n"
        "    total = 1\n"
        "    for _ in range(jack_matching.n):\n"
        "        total = total + total\n"
        "    return total\n"
    )
    with pytest.raises(ResourceGateError, match="magnitude bound|bit integer"):
        run_value_audit(
            counting,
            adversarial_mjack_probes(64),
            value_exponent=8,
            timeout_seconds=5.0,
            size_of=jack_matching_size,
        )


def test_resource_gate_accepts_a_polynomial_statistic_on_large_objects():
    genuine = (ROOT / "examples" / "mjack_within_class_submission.py").read_text()
    probes = adversarial_mjack_probes(256)
    report = run_resource_gate(
        genuine,
        probes,
        timeout_seconds=5.0,
        max_python_bytes=64_000_000,
    )
    assert len(report.results) == len(probes)


def test_object_totals_match_partitions_times_matchings():
    data = _polynomials()
    assert sum(case["count"] for case in data["cases"]) == 121537
    fibers = {
        (case["case_id"], tuple(pi), tuple(sigma))
        for case in data["cases"]
        for pi, sigma, _q, _c in case["terms"]
    }
    assert len(fibers) == 1055


def test_canonical_probes_are_the_matchings_the_statistic_must_kill():
    for lam in ((6,), (3, 3), (2, 2, 1, 1), (1,) * 6):
        assert canonical_jack_matching(lam, kind="epsilon").is_bipartite
        assert canonical_jack_matching(lam, kind="reference").is_bipartite
