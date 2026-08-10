"""Public oracle: the Schur expansion of the unicellular LLT polynomial.

For a Dyck graph (natural unit interval graph) ``G = ([n], E)`` the target of
problem 14 is the Schur-basis expansion of the unicellular LLT polynomial

    LLT_G(X; q) = sum_{kappa : [n] -> Z_{>0}} q^{asc_G(kappa)} x_kappa
                = sum_{lambda |- n} c_lambda^G(q) s_lambda(X),

where the sum is over *all* colourings ``kappa`` (unlike the chromatic
quasisymmetric function there is no properness condition),
``x_kappa = prod_v x_{kappa(v)}``, and

    asc_G(kappa) = #{ (i, j) in E : i < j, kappa(i) < kappa(j) }.

``LLT_G`` is symmetric and Schur positive (Grojnowski--Haiman), so the expansion
exists with ``c_lambda^G(q) in N[q]``; at ``q = 1`` it degenerates to ``p_1^n``,
so ``c_lambda^G(1) = f^lambda``. What is open is a combinatorial rule for
``c_lambda^G(q)`` in general.

This module computes ``c_lambda^G(q)`` with exact arithmetic and no external
CAS: it reads off the monomial coefficients ``[m_mu] LLT_G`` directly from
colourings of the prescribed content, then changes basis from the monomial to
the Schur basis against the Kostka matrix. The scored evaluator never imports
this module; it only reads the published targets.
"""
from __future__ import annotations

from fractions import Fraction
from functools import lru_cache

PROBLEM_ID = 14
PROBLEM_NAME = "uig_syt_llt_schur_q_stat"

# A q-polynomial is a dict {q_exponent: integer coefficient}.
Poly = dict


# ---------------------------------------------------------------------------
# Partitions and the Schur -> monomial (Kostka) transition
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


def _horizontal_strips(lam: tuple[int, ...], size: int):
    """Yield every ``nu`` with ``lam / nu`` a horizontal strip of ``size`` cells."""
    rows = len(lam)

    def rec(i: int, remaining: int, prefix: list[int]):
        if i == rows:
            if remaining == 0:
                yield tuple(part for part in prefix if part)
            return
        floor = lam[i + 1] if i + 1 < rows else 0
        for nu_i in range(max(floor, lam[i] - remaining), lam[i] + 1):
            prefix.append(nu_i)
            yield from rec(i + 1, remaining - (lam[i] - nu_i), prefix)
            prefix.pop()

    yield from rec(0, size, [])


@lru_cache(maxsize=None)
def kostka_number(lam: tuple[int, ...], mu: tuple[int, ...]) -> int:
    """``K_{lambda mu}``: the number of semistandard tableaux of shape ``lam``, content ``mu``.

    Peeling off the largest entry: it occupies a horizontal strip of ``mu[-1]``
    cells, and what is left is a semistandard tableau of the smaller content.
    """
    if not mu:
        return 1 if not lam else 0
    return sum(
        kostka_number(nu, mu[:-1]) for nu in _horizontal_strips(lam, mu[-1])
    )


@lru_cache(maxsize=None)
def _s_from_m_solver(n: int) -> dict:
    """``B[lam][mu]`` (Fractions) with ``c = B M`` solving ``K^T c = M`` for ``c``.

    Here ``M_mu = [m_mu] LLT_G`` and ``c_lam = [s_lam] LLT_G``; since
    ``s_lam = sum_mu K_{lam mu} m_mu``, the coefficients solve ``K^T c = M``, so
    ``B = (K^T)^{-1}``.
    """
    part_list = partitions_of(n)
    size = len(part_list)
    # (K^T)[mu][lam] augmented with the identity, then Gauss--Jordan.
    aug = [
        [Fraction(kostka_number(lam, mu)) for lam in part_list]
        + [Fraction(1) if i == j else Fraction(0) for j in range(size)]
        for i, mu in enumerate(part_list)
    ]
    for col in range(size):
        pivot = next(r for r in range(col, size) if aug[r][col] != 0)
        aug[col], aug[pivot] = aug[pivot], aug[col]
        inv_pivot = aug[col][col]
        aug[col] = [value / inv_pivot for value in aug[col]]
        for r in range(size):
            if r != col and aug[r][col] != 0:
                factor = aug[r][col]
                aug[r] = [x - factor * y for x, y in zip(aug[r], aug[col])]
    inverse = [row[size:] for row in aug]
    return {
        lam: {mu: inverse[i][j] for j, mu in enumerate(part_list)}
        for i, lam in enumerate(part_list)
    }


# ---------------------------------------------------------------------------
# LLT_G in the monomial basis, via colourings
# ---------------------------------------------------------------------------


def _monomial_coeffs(b: tuple[int, ...]) -> dict:
    """``{mu: poly}`` with ``poly = [m_mu] LLT_G[X; q]`` for every ``mu |- n``.

    ``[m_mu] LLT_G`` is the coefficient of the representative monomial
    ``x_1^{mu_1} x_2^{mu_2} ...``: the ``q^{asc}``-weighted count of colourings
    using colour ``c`` exactly ``mu_c`` times (colours ``1..len(mu)``). Vertices
    are coloured in increasing order, so every left neighbour of ``v`` -- the
    vertices ``u < v`` with ``b_u >= v`` -- is already coloured and the ascents
    contributed by ``v`` can be counted on the spot.
    """
    n = len(b)
    left = [
        tuple(u for u in range(1, v) if b[u - 1] >= v)
        for v in range(n + 1)
    ]

    result: dict = {}
    for mu in partitions_of(n):
        quota = list(mu)
        ncolours = len(mu)
        colour = [0] * (n + 1)
        poly: dict = {}

        def rec(v: int, ascents: int) -> None:
            if v > n:
                poly[ascents] = poly.get(ascents, 0) + 1
                return
            neighbours = left[v]
            for c in range(ncolours):
                if quota[c] == 0:
                    continue
                shade = c + 1
                added = sum(1 for u in neighbours if colour[u] < shade)
                colour[v] = shade
                quota[c] -= 1
                rec(v + 1, ascents + added)
                quota[c] += 1
                colour[v] = 0

        rec(1, 0)
        result[mu] = {exp: coeff for exp, coeff in poly.items() if coeff}
    return result


def llt_schur_expansion(b: tuple[int, ...]) -> dict:
    """The Schur expansion ``{lambda: poly_in_q}`` of ``LLT_G`` for graph vector ``b``.

    Zero coefficients are dropped; each returned ``poly`` is a ``{q_exp: int}``
    dict with nonnegative integer coefficients (Schur positivity).
    """
    n = len(b)
    part_list = partitions_of(n)
    monomial = _monomial_coeffs(b)
    solver = _s_from_m_solver(n)

    expansion: dict = {}
    for lam in part_list:
        accumulator: dict = {}
        for mu in part_list:
            coefficient = solver[lam][mu]
            if coefficient == 0:
                continue
            for exp, value in monomial[mu].items():
                accumulator[exp] = accumulator.get(exp, Fraction(0)) + coefficient * value
        poly: dict = {}
        for exp, value in accumulator.items():
            if value == 0:
                continue
            if isinstance(value, Fraction):
                if value.denominator != 1:
                    raise ValueError(f"non-integer Schur coefficient for {lam} at q^{exp}: {value}")
                value = int(value)
            poly[exp] = value
        if poly:
            expansion[lam] = poly
    return expansion
