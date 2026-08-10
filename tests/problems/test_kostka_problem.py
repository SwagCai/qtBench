from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from qtbench.combinatorics import (
    conjugate_partition,
    iter_kostka_standard_tableaux,
    iter_partitions,
    kostka_standard_tableau_count,
    kostka_tableau_size,
)
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_kostka_probes,
    evaluate_kostka_polynomial_checks,
    evaluate_kostka_submission,
    run_resource_gate,
    run_value_audit,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "t_statistic_discovery" / "syt_qt_kostka_macdonald_pair_stat"
PROBLEM_ID = 13
PROBLEM_NAME = "syt_qt_kostka_macdonald_pair_stat"


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def _by_pair():
    return {
        (case["n"], tuple(case["lam"]), tuple(case["mu"])): {
            (i, j): coefficient for i, j, coefficient in case["terms"]
        }
        for case in _polynomials()["cases"]
    }


def test_polynomials_are_positive_and_total_the_number_of_tableaux():
    data = _polynomials()
    assert data["variables"] == ["q", "t"]
    assert data["known_statistics"] == []
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    seen = Counter()
    for case in data["cases"]:
        lam = tuple(case["lam"])
        seen[case["n"]] += 1
        poly = {(i, j): coefficient for i, j, coefficient in case["terms"]}
        assert all(coefficient > 0 for coefficient in poly.values())
        assert all(i >= 0 and j >= 0 for i, j in poly)
        # K~_{lambda mu}(1, 1) = f^lambda
        assert sum(poly.values()) == case["count"] == kostka_standard_tableau_count(lam)
    # one case per ordered pair of partitions of n, up to n = 8
    for n, cases in seen.items():
        assert cases == len(iter_partitions(n)) ** 2


def test_conjugating_mu_swaps_q_and_t():
    table = _by_pair()
    for (n, lam, mu), poly in table.items():
        swapped = table[(n, lam, conjugate_partition(mu))]
        assert poly == {(j, i): coefficient for (i, j), coefficient in swapped.items()}


def test_the_two_extreme_mu_are_the_maj_distribution():
    table = _by_pair()
    for n in range(1, 9):
        for lam in iter_partitions(n):
            maj = Counter(
                tableau.maj() for tableau in iter_kostka_standard_tableaux(lam, (n,))
            )
            row = table[(n, lam, (n,))]
            column = table[(n, lam, tuple([1] * n))]
            assert {i: c for (i, j), c in row.items() if j == 0} == maj
            assert sum(row.values()) == sum(maj.values())
            assert {j: c for (i, j), c in column.items() if i == 0} == maj
            assert sum(column.values()) == sum(maj.values())


def _n_statistic(mu) -> int:
    """``n(mu) = sum_i (i - 1) mu_i``."""
    return sum(index * part for index, part in enumerate(mu))


def test_the_two_extreme_schur_coefficients_are_the_classical_ones():
    # Independent of the generator: <H~_mu, s_(n)> = 1 and
    # <H~_mu, s_(1^n)> = q^{n(mu')} t^{n(mu)} for every mu.
    for case in _polynomials()["cases"]:
        lam = tuple(case["lam"])
        mu = tuple(case["mu"])
        terms = [tuple(term) for term in case["terms"]]
        if lam == (case["n"],):
            assert terms == [(0, 0, 1)]
        if lam == tuple([1] * case["n"]):
            assert terms == [(_n_statistic(conjugate_partition(mu)), _n_statistic(mu), 1)]


def _semistandard_tableaux(lam, mu):
    """Every semistandard Young tableau of shape ``lam`` and content ``mu``."""
    height = len(lam)
    rows = [[0] * part for part in lam]
    out = []

    def place(value, remaining, start_row):
        if value > len(mu):
            out.append(tuple(tuple(row) for row in rows))
            return
        if remaining == 0:
            place(value + 1, mu[value] if value < len(mu) else 0, 0)
            return
        for r in range(start_row, height):
            for c in range(lam[r]):
                if rows[r][c]:
                    continue
                if c and (rows[r][c - 1] == 0 or rows[r][c - 1] > value):
                    continue
                if r and (rows[r - 1][c] == 0 or rows[r - 1][c] >= value):
                    continue
                rows[r][c] = value
                place(value, remaining - 1, r)
                rows[r][c] = 0
                break  # only the leftmost free cell of a row can be filled next

    place(1, mu[0], 0)
    return out


def _standard_subwords(word):
    """Macdonald's decomposition of a word into standard subwords.

    Scanning leftwards and cyclically from the right end, select the first ``1``,
    then the first ``2`` left of it, and so on; the selected letters form one
    standard subword and are removed.
    """
    remaining = list(word)
    out = []
    while remaining:
        chosen: list[int] = []
        index = len(remaining) - 1
        for value in range(1, max(remaining) + 1):
            found = None
            for step in range(len(remaining)):
                probe = (index - step) % len(remaining)
                if remaining[probe] == value and probe not in chosen:
                    found = probe
                    break
            if found is None:
                break
            chosen.append(found)
            index = found
        picked = sorted(chosen)
        out.append([remaining[i] for i in picked])
        remaining = [v for i, v in enumerate(remaining) if i not in set(picked)]
    return out


def _charge(tableau):
    """Lascoux-Schuetzenberger charge of the reading word of ``tableau``.

    The reading word runs along the rows from the bottom row up, left to right.
    On a standard word the index of ``1`` is ``0`` and the index of ``r + 1`` is
    that of ``r``, plus one when ``r + 1`` lies to the right of ``r``.
    """
    word = [value for row in tableau[::-1] for value in row]
    total = 0
    for subword in _standard_subwords(word):
        position = {value: i for i, value in enumerate(subword)}
        index = 0
        for value in range(2, len(subword) + 1):
            if position[value] > position[value - 1]:
                index += 1
            total += index
    return total


def test_q_equals_zero_is_the_kostka_foulkes_cocharge_polynomial():
    """Cross-check the shipped targets against a completely different algorithm.

    ``H~_mu(X; 0, t)`` is the modified Hall-Littlewood polynomial, so
    ``K~_{lambda mu}(0, t) = sum_{S in SSYT(lambda, mu)} t^{cocharge(S)}``. Charge
    on semistandard tableaux shares no code and no combinatorial model with the
    Haglund-Haiman-Loehr ``inv``/``maj`` fillings the generator used, so agreeing
    with it validates the ``q = 0`` slice of every target independently. The
    conjugation symmetry then carries the same check to the ``t = 0`` slice.
    """
    for case in _polynomials()["cases"]:
        if case["n"] > 6:
            continue
        lam = tuple(case["lam"])
        mu = tuple(case["mu"])
        expected = Counter()
        for i, j, coefficient in case["terms"]:
            if i == 0:
                expected[j] += coefficient
        cocharge = Counter(
            _n_statistic(mu) - _charge(tableau)
            for tableau in _semistandard_tableaux(lam, mu)
        )
        assert cocharge == expected, case["case_id"]


def test_q_equals_1_is_the_t_marginal():
    full = {case["case_id"]: case for case in _polynomials()["cases"]}
    marginal = json.loads((PROBLEM / "data" / "q_equals_1.json").read_text())
    assert marginal["variables"] == ["t"]
    for case in marginal["cases"]:
        expected: Counter[int] = Counter()
        for _i, j, coefficient in full[case["case_id"]]["terms"]:
            expected[j] += coefficient
        assert {j: coefficient for j, coefficient in case["terms"]} == dict(expected)
        assert sum(coefficient for _j, coefficient in case["terms"]) == case["count"]


def test_public_instances_are_the_enumerated_fibers():
    data = json.loads((PROBLEM / "data" / "instances.json").read_text())
    assert data["known_statistics"] == []
    for case in data["cases"]:
        lam = tuple(case["lam"])
        mu = tuple(case["mu"])
        expected = [
            tableau.encoding for tableau in iter_kostka_standard_tableaux(lam, mu)
        ]
        assert case["entries"] == expected
        assert case["count"] == len(expected)


def _reference_pair():
    """A rank-assignment witness: proves the target is realizable over the tableaux."""
    mapping: dict[str, tuple[int, int]] = {}
    for case in _polynomials()["cases"]:
        exponents: list[tuple[int, int]] = []
        for i, j, coefficient in case["terms"]:
            exponents.extend([(i, j)] * coefficient)
        encodings = sorted(
            tableau.encoding
            for tableau in iter_kostka_standard_tableaux(
                tuple(case["lam"]), tuple(case["mu"])
            )
        )
        for encoding, value in zip(encodings, exponents, strict=True):
            mapping[encoding] = value

    def pair(tableau):
        return mapping[tableau.encoding]

    return pair


def test_reference_pair_reproduces_the_target_but_maj_alone_does_not():
    result = evaluate_kostka_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_pair(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    # (maj, 0) is the answer at mu = (n) only, so it matches those cases and no more.
    partial = evaluate_kostka_polynomial_checks(
        problem_dir=PROBLEM, statistic=lambda tableau: (tableau.maj(), 0)
    )
    assert not partial["full_qt"]["passed"]
    correct = {
        case["case_id"]
        for case in partial["full_qt"]["case_results"]
        if case["correct"]
    }
    cases = _polynomials()["cases"]
    assert {
        case["case_id"] for case in cases if tuple(case["mu"]) == (case["n"],)
    } <= correct
    assert len(correct) < len(cases)


@pytest.mark.parametrize(
    "value", [0, (0,), (0, 0, 0), [0, 0], (0, -1), (0.0, 0), (True, 0)]
)
def test_the_submitted_value_must_be_a_pair_of_nonnegative_integers(value):
    with pytest.raises((TypeError, ValueError)):
        evaluate_kostka_polynomial_checks(
            problem_dir=PROBLEM, statistic=lambda _tableau: value
        )


def test_constant_pair_short_circuits_at_numerical_end_to_end():
    result = evaluate_kostka_submission(
        source="def statistic(tableau):\n    return (0, 0)\n",
        probes=lambda: adversarial_kostka_probes(96),
        problem_dir=PROBLEM,
        timeout_seconds=2.0,
        numerical_timeout_seconds=120.0,
        max_python_bytes=64_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"
    assert result["value_audit"] is None


def test_non_pair_output_is_rejected():
    # Returning a bare int is rejected during the numerical checks.
    with pytest.raises(ResourceGateError, match="pair of nonnegative integers"):
        evaluate_kostka_submission(
            source="def statistic(tableau):\n    return 0\n",
            probes=lambda: adversarial_kostka_probes(96),
            problem_dir=PROBLEM,
            timeout_seconds=2.0,
            numerical_timeout_seconds=120.0,
            max_python_bytes=64_000_000,
        )


def test_value_audit_wired_for_kostka_standard_tableaux():
    genuine = "def statistic(tableau):\n    return (tableau.maj(), tableau.comaj())\n"
    run_value_audit(
        genuine,
        adversarial_kostka_probes(64),
        value_exponent=8,
        timeout_seconds=5.0,
        size_of=kostka_tableau_size,
    )

    counting = (
        "def statistic(tableau):\n"
        "    total = 1\n"
        "    for _ in range(tableau.n):\n"
        "        total = total + total\n"
        "    return (total % 3, 0)\n"
    )
    with pytest.raises(ResourceGateError, match="magnitude bound|bit integer"):
        run_value_audit(
            counting,
            adversarial_kostka_probes(64),
            value_exponent=8,
            timeout_seconds=5.0,
            size_of=kostka_tableau_size,
        )


def test_resource_gate_accepts_a_polynomial_statistic_on_large_tableaux():
    genuine = "def statistic(tableau):\n    return (tableau.maj(), tableau.comaj())\n"
    probes = adversarial_kostka_probes(256)
    report = run_resource_gate(
        genuine,
        probes,
        timeout_seconds=10.0,
        max_python_bytes=64_000_000,
    )
    assert len(report.results) == len(probes)
    assert all(
        isinstance(result, tuple) and len(result) == 2 for result in report.results
    )


def test_resource_gate_blocks_enumerating_the_fiber():
    # |SYT(lambda)| is exponential, so any submission that walks the fiber of its
    # own object cannot finish on a large probe.
    enumerating = (
        "def statistic(tableau):\n"
        "    total = 0\n"
        "    for i in range(tableau.n):\n"
        "        for j in range(tableau.n):\n"
        "            for k in range(tableau.n):\n"
        "                for l in range(tableau.n):\n"
        "                    total = total + i * j * k * l\n"
        "    return (total % 2, 0)\n"
    )
    with pytest.raises(ResourceGateError, match="seconds|CPU"):
        run_resource_gate(
            enumerating,
            adversarial_kostka_probes(256),
            timeout_seconds=2.0,
            max_python_bytes=64_000_000,
        )
