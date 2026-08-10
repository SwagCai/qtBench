"""Public oracle: Jack connection coefficients ``c^lambda_{pi,sigma}(beta)``.

Goulden and Jackson define the coefficients by the power-sum expansion of a Cauchy
sum for the integral-form Jack symmetric functions ``J_theta^{(alpha)}``:

    sum_theta (1 / <J_theta, J_theta>_alpha) J_theta(x) J_theta(y) J_theta(z) t^{|theta|}
        = sum_n t^n sum_{lambda,pi,sigma |- n}
            c^lambda_{pi,sigma} alpha^{-l(lambda)} z_lambda^{-1} p_pi(x) p_sigma(y) p_lambda(z).

Writing ``J_theta = sum_mu theta^theta_mu p_mu`` and ``j_theta = <J_theta, J_theta>_alpha``
this reads off as

    c^lambda_{pi,sigma}
        = alpha^{l(lambda)} z_lambda sum_theta
            theta^theta_pi theta^theta_sigma theta^theta_lambda / j_theta,           (*)

which is what this module computes. The target of problem 16 is that quantity as a
polynomial in ``beta = alpha - 1``.

Everything is exact. For a fixed rational ``alpha`` the Jack polynomials are built
by Gram--Schmidt: the ``p``-basis is orthogonal for the deformed Hall product,
``<p_lambda, p_mu>_alpha = delta_{lambda mu} z_lambda alpha^{l(lambda)}``, and
``P_lambda`` is the unique basis orthogonal for it and unitriangular in the monomial
basis for dominance order, so orthogonalizing the monomials along a linear extension
of dominance produces exactly ``P_lambda``. The integral form is
``J_lambda = c_lambda(alpha) P_lambda`` with
``c_lambda = prod_{s in lambda} (alpha a(s) + l(s) + 1)`` over arms and legs, and
``j_lambda = prod_s (alpha a(s) + l(s) + 1)(alpha a(s) + l(s) + alpha)``.

Since ``c^lambda_{pi,sigma}`` is a polynomial in ``beta`` of degree at most
``d(pi,sigma;lambda) = (n - l(pi)) + (n - l(sigma)) - (n - l(lambda))``
(Dolega--Feray), evaluating (*) at ``beta = 0, 1, ..., 2n + 2`` and solving the
Vandermonde system recovers it exactly; the generator checks the recovered degree
against that bound, so an under-sampled interpolation could not pass unnoticed.

The scored evaluator never imports this module; it only reads the published targets.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
from functools import lru_cache
from itertools import permutations
from math import factorial

PROBLEM_ID = 16
PROBLEM_NAME = "match_jack_connection_q_stat"


# ---------------------------------------------------------------------------
# Partitions
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def partitions_of(n: int) -> tuple[tuple[int, ...], ...]:
    """Every partition of ``n`` as a weakly-decreasing tuple, in a fixed order."""
    out: list[tuple[int, ...]] = []

    def rec(remaining: int, cap: int, prefix: list[int]) -> None:
        if remaining == 0:
            out.append(tuple(prefix))
            return
        for part in range(min(remaining, cap), 0, -1):
            prefix.append(part)
            rec(remaining - part, part, prefix)
            prefix.pop()

    rec(n, n, [])
    return tuple(out)


def z_of(lam: tuple[int, ...]) -> int:
    """``z_lambda = prod_i i^{m_i} m_i!``, the size of a centralizer."""
    value = 1
    for part, multiplicity in Counter(lam).items():
        value *= part ** multiplicity * factorial(multiplicity)
    return value


def dominates(lam: tuple[int, ...], mu: tuple[int, ...]) -> bool:
    """Whether ``lam >= mu`` in dominance order."""
    left = right = 0
    for index in range(max(len(lam), len(mu))):
        left += lam[index] if index < len(lam) else 0
        right += mu[index] if index < len(mu) else 0
        if left < right:
            return False
    return True


def arms_and_legs(lam: tuple[int, ...]) -> list[tuple[int, int]]:
    """``(arm, leg)`` of every cell of ``lam``."""
    columns = [sum(1 for part in lam if part > column) for column in range(lam[0])]
    return [
        (lam[row] - column - 1, columns[column] - row - 1)
        for row in range(len(lam))
        for column in range(lam[row])
    ]


# ---------------------------------------------------------------------------
# The power-sum / monomial transition
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def power_sum_in_monomials(n: int) -> dict:
    """``R[lam][mu]`` with ``p_lam = sum_mu R[lam][mu] m_mu``.

    ``R[lam][mu]`` is the coefficient of the single monomial
    ``x_1^{mu_1} x_2^{mu_2} ...`` in ``prod_i (sum_k x_k^{lam_i})``, i.e. the number
    of ways to assign each part of ``lam`` to a part of ``mu`` so that the parts
    assigned to each slot sum to it.
    """
    parts = partitions_of(n)
    transition: dict = {}
    for lam in parts:
        row: dict = {}
        for mu in parts:
            sums = [0] * len(mu)

            def count(index: int) -> int:
                if index == len(lam):
                    return 1 if all(
                        sums[slot] == mu[slot] for slot in range(len(mu))
                    ) else 0
                total = 0
                for slot in range(len(mu)):
                    if sums[slot] + lam[index] <= mu[slot]:
                        sums[slot] += lam[index]
                        total += count(index + 1)
                        sums[slot] -= lam[index]
                return total

            row[mu] = count(0)
        transition[lam] = row
    return transition


@lru_cache(maxsize=None)
def monomials_in_power_sums(n: int) -> dict:
    """``S[mu][lam]`` with ``m_mu = sum_lam S[mu][lam] p_lam``: the inverse matrix."""
    parts = list(partitions_of(n))
    forward = power_sum_in_monomials(n)
    size = len(parts)
    augmented = [
        [Fraction(forward[parts[row]][parts[column]]) for column in range(size)]
        + [Fraction(int(row == column)) for column in range(size)]
        for row in range(size)
    ]
    for column in range(size):
        pivot = next(row for row in range(column, size) if augmented[row][column])
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(size):
            if row != column and augmented[row][column]:
                factor = augmented[row][column]
                augmented[row] = [
                    x - factor * y for x, y in zip(augmented[row], augmented[column])
                ]
    # p = R m as vectors of basis elements, so m = R^{-1} p and row `mu` of the
    # inverse holds the p-coordinates of m_mu.
    return {
        parts[row]: {
            parts[column]: augmented[row][size + column] for column in range(size)
        }
        for row in range(size)
    }


# ---------------------------------------------------------------------------
# Jack polynomials at a fixed rational alpha
# ---------------------------------------------------------------------------


def jack_power_sum_expansion(n: int, alpha) -> tuple[dict, dict]:
    """``({theta: {mu: theta^theta_mu}}, {theta: j_theta})`` for the integral form.

    The Gram--Schmidt runs in ``p``-coordinates, where the deformed Hall product is
    diagonal, over a linear extension of dominance order.
    """
    alpha = Fraction(alpha)
    parts = partitions_of(n)
    to_power_sums = monomials_in_power_sums(n)

    def product(left: dict, right: dict):
        return sum(
            left.get(lam, 0) * right.get(lam, 0) * z_of(lam) * alpha ** len(lam)
            for lam in parts
        )

    order = sorted(
        parts, key=lambda mu: (sum(1 for nu in parts if dominates(mu, nu)), mu)
    )
    basis: list[tuple[tuple[int, ...], dict]] = []
    for mu in order:
        vector = dict(to_power_sums[mu])
        for _nu, earlier in basis:
            factor = product(vector, earlier) / product(earlier, earlier)
            if factor:
                for key, value in earlier.items():
                    vector[key] = vector.get(key, 0) - factor * value
        basis.append((mu, {key: value for key, value in vector.items() if value}))

    theta: dict = {}
    norms: dict = {}
    for lam, vector in basis:
        lower = upper = Fraction(1)
        for arm, leg in arms_and_legs(lam):
            lower *= alpha * arm + leg + 1
            upper *= alpha * arm + leg + alpha
        theta[lam] = {mu: lower * value for mu, value in vector.items()}
        norms[lam] = lower * upper
    return theta, norms


def connection_coefficients_at(n: int, alpha) -> dict:
    """``{(lambda, pi, sigma): c^lambda_{pi,sigma}(alpha)}`` by formula (*)."""
    theta, norms = jack_power_sum_expansion(n, alpha)
    parts = partitions_of(n)
    out: dict = {}
    for lam in parts:
        prefactor = Fraction(alpha) ** len(lam) * z_of(lam)
        for pi in parts:
            for sigma in parts:
                total = sum(
                    theta[tau].get(pi, 0)
                    * theta[tau].get(sigma, 0)
                    * theta[tau].get(lam, 0)
                    / norms[tau]
                    for tau in parts
                )
                out[(lam, pi, sigma)] = prefactor * total
    return out


# ---------------------------------------------------------------------------
# Interpolation in beta
# ---------------------------------------------------------------------------


def _interpolate(values: list[Fraction]) -> list[Fraction]:
    """Coefficients of the polynomial through ``(0, v_0), (1, v_1), ...``."""
    size = len(values)
    augmented = [
        [Fraction(point) ** degree for degree in range(size)] + [Fraction(values[point])]
        for point in range(size)
    ]
    for column in range(size):
        pivot = next(row for row in range(column, size) if augmented[row][column])
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [value / scale for value in augmented[column]]
        for row in range(size):
            if row != column and augmented[row][column]:
                factor = augmented[row][column]
                augmented[row] = [
                    x - factor * y for x, y in zip(augmented[row], augmented[column])
                ]
    return [augmented[degree][size] for degree in range(size)]


def connection_coefficient_polynomials(n: int) -> dict:
    """``{(lambda, pi, sigma): [c_0, c_1, ...]}``, the coefficients of ``beta^i``.

    Trailing zeros are dropped, so the empty list is the zero polynomial. The
    values are ``Fraction``s; the generator is what insists they are nonnegative
    integers, which is the content of the Matchings-Jack conjecture.
    """
    tables = [connection_coefficients_at(n, 1 + beta) for beta in range(2 * n + 3)]
    out: dict = {}
    for key in tables[0]:
        coefficients = _interpolate([table[key] for table in tables])
        while coefficients and coefficients[-1] == 0:
            coefficients.pop()
        out[key] = coefficients
    return out


def degree_bound(n: int, pi: tuple[int, ...], sigma: tuple[int, ...], lam: tuple[int, ...]) -> int:
    """``d(pi,sigma;lambda)``, the Dolega--Feray upper bound on ``deg_beta``."""
    return (n - len(pi)) + (n - len(sigma)) - (n - len(lam))


# ---------------------------------------------------------------------------
# Independent checks the generator runs against this module
# ---------------------------------------------------------------------------


def class_algebra_structure_constants(n: int) -> dict:
    """``{(lambda, pi, sigma): a}``, the ``beta = 0`` specialization, counted directly.

    At ``alpha = 1`` the Jack Cauchy sum degenerates to the Schur one and formula
    (*) returns the classical class-algebra structure constant: the number of ways
    to write one fixed permutation of cycle type ``lambda`` as a product of a
    permutation of type ``pi`` and one of type ``sigma``. Counted here by brute force
    over ``S_n``, so it shares no code and no theory with the Jack computation.
    """
    letters = tuple(range(n))
    words = list(permutations(letters))

    def cycle_type(word: tuple[int, ...]) -> tuple[int, ...]:
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

    by_type: dict = {}
    for word in words:
        by_type.setdefault(cycle_type(word), []).append(word)

    out: dict = {}
    for lam in partitions_of(n):
        target = by_type[lam][0]
        for pi in partitions_of(n):
            counts: Counter = Counter()
            for word in by_type.get(pi, ()):
                inverse = [0] * n
                for index, image in enumerate(word):
                    inverse[image] = index
                # v = u^{-1} target, so that u v = target
                counts[cycle_type(tuple(target[inverse[i]] for i in range(n)))] += 1
            for sigma in partitions_of(n):
                out[(lam, pi, sigma)] = counts.get(sigma, 0)
    return out


def validate_jack(n: int, alpha) -> None:
    """Check the Jack construction against three facts it was not built from.

    * ``<J_lambda, J_mu>_alpha = delta_{lambda mu} j_lambda`` with ``j_lambda`` the
      hook product. Gram--Schmidt gives orthogonality for free, but the norm pins
      down the integral-form normalization ``c_lambda``.
    * ``J_lambda`` is triangular in the monomial basis for dominance order, with
      leading coefficient ``c_lambda`` on ``m_lambda``.
    * ``J_{(1^n)} = n! e_n = n! m_{(1^n)}``.
    """
    alpha = Fraction(alpha)
    parts = partitions_of(n)
    theta, norms = jack_power_sum_expansion(n, alpha)
    forward = power_sum_in_monomials(n)

    for lam in parts:
        for mu in parts:
            product = sum(
                theta[lam].get(nu, 0) * theta[mu].get(nu, 0) * z_of(nu) * alpha ** len(nu)
                for nu in parts
            )
            expected = norms[lam] if lam == mu else 0
            if product != expected:
                raise ValueError(
                    f"n={n} alpha={alpha}: <J_{lam}, J_{mu}> is {product}, expected {expected}"
                )

    for lam in parts:
        leading = Fraction(1)
        for arm, leg in arms_and_legs(lam):
            leading *= alpha * arm + leg + 1
        in_monomials = {
            mu: sum(theta[lam].get(nu, 0) * forward[nu][mu] for nu in parts)
            for mu in parts
        }
        if in_monomials[lam] != leading:
            raise ValueError(f"n={n}: J_{lam} has leading monomial coefficient {in_monomials[lam]}")
        for mu, value in in_monomials.items():
            if value and not dominates(lam, mu):
                raise ValueError(f"n={n}: J_{lam} is not dominance-triangular (m_{mu})")

    column = tuple([1] * n)
    if any(
        value != (factorial(n) if mu == column else 0)
        for mu, value in {
            mu: sum(theta[column].get(nu, 0) * forward[nu][mu] for nu in parts)
            for mu in parts
        }.items()
    ):
        raise ValueError(f"n={n}: J_(1^n) is not n! e_n")
