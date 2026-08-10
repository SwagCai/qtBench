"""Public oracle: the Shareshian--Wachs chromatic quasisymmetric function.

For a Dyck graph (natural unit interval graph) ``G = ([n], E)`` the target of
problem 8 is the elementary-basis expansion of the chromatic quasisymmetric
function of Shareshian and Wachs,

    chi_G[X; q] = sum_{kappa proper} q^{asc_G(kappa)} x_kappa
                = sum_{lambda |- n} c_lambda(q) e_lambda,

where the sum is over proper colourings ``kappa : [n] -> Z_{>0}`` (adjacent
vertices get different colours), ``x_kappa = prod_v x_{kappa(v)}``, and

    asc_G(kappa) = #{ (i, j) in E : i < j, kappa(i) < kappa(j) }.

``chi_G`` is a genuine symmetric function for these graphs (Shareshian--Wachs),
so the ``e``-expansion exists; the Shareshian--Wachs conjecture is that every
``c_lambda(q)`` lies in ``N[q]``.

This module computes ``c_lambda(q)`` with exact ``Fraction`` arithmetic and no
external CAS: it reads off the monomial coefficients ``[m_mu] chi_G`` directly
from proper colourings of the prescribed content, then changes basis from the
monomial to the elementary basis via the integer transition matrix. The scored
evaluator never imports this module; it only reads the published targets.
"""
from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from itertools import combinations

PROBLEM_ID = 8
PROBLEM_NAME = "uig_ginv_shareshian_wachs_q_stat"

# A q-polynomial is a dict {q_exponent: integer coefficient}.
Poly = dict


# ---------------------------------------------------------------------------
# Partitions and the elementary -> monomial transition
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


@lru_cache(maxsize=None)
def _e_to_m_matrix(n: int) -> dict:
    """``A[lam][mu]`` = integer coefficient of ``m_mu`` in ``e_lam`` (no ``q``)."""
    part_list = partitions_of(n)

    def e_r(r: int) -> dict:
        d: dict = {}
        for combo in combinations(range(n), r):
            exp = [0] * n
            for idx in combo:
                exp[idx] = 1
            d[tuple(exp)] = d.get(tuple(exp), 0) + 1
        return d

    def mul(d1: dict, d2: dict) -> dict:
        out: dict = {}
        for e1, c1 in d1.items():
            for e2, c2 in d2.items():
                key = tuple(a + b for a, b in zip(e1, e2))
                out[key] = out.get(key, 0) + c1 * c2
        return out

    er = {r: e_r(r) for r in range(1, n + 1)}
    matrix: dict = {}
    for lam in part_list:
        prod = {tuple([0] * n): 1}
        for part in lam:
            prod = mul(prod, er[part])
        matrix[lam] = {}
        for mu in part_list:
            rep = tuple(sorted(list(mu) + [0] * (n - len(mu)), reverse=True))
            matrix[lam][mu] = prod.get(rep, 0)
    return matrix


@lru_cache(maxsize=None)
def _e_from_m_solver(n: int) -> dict:
    """``B[lam][mu]`` (Fractions) with ``c = B M`` solving ``A^T c = M`` for ``c``.

    Here ``M_mu = [m_mu] chi_G`` and ``c_lam = [e_lam] chi_G``; ``B = (A^T)^{-1}``.
    """
    part_list = partitions_of(n)
    A = _e_to_m_matrix(n)
    size = len(part_list)
    # (A^T)[mu][lam] augmented with the identity, then Gauss--Jordan.
    aug = [
        [Fraction(A[lam][mu]) for lam in part_list]
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
# chi_G in the monomial basis, via proper colourings
# ---------------------------------------------------------------------------


def _monomial_coeffs(n: int, edges: frozenset[tuple[int, int]]) -> dict:
    """``{mu: poly}`` with ``poly = [m_mu] chi_G[X; q]`` for every ``mu |- n``.

    ``[m_mu] chi_G`` is the coefficient of the representative monomial
    ``x_1^{mu_1} x_2^{mu_2} ...``: the ``q^{asc}``-weighted count of proper
    colourings using colour ``c`` exactly ``mu_c`` times (colours ``1..len(mu)``).
    Enumerated by backtracking over the vertices with a per-colour quota and the
    independence constraint.
    """
    adjacency: list[set[int]] = [set() for _ in range(n + 1)]
    for i, j in edges:
        adjacency[i].add(j)
        adjacency[j].add(i)
    oriented = sorted(edges)

    result: dict = {}
    for mu in partitions_of(n):
        quota = list(mu)
        ncolours = len(mu)
        colour = [0] * (n + 1)
        poly: dict = {}

        def rec(v: int) -> None:
            if v > n:
                asc = 0
                for i, j in oriented:
                    if colour[i] < colour[j]:
                        asc += 1
                poly[asc] = poly.get(asc, 0) + 1
                return
            for c in range(ncolours):
                if quota[c] == 0:
                    continue
                shade = c + 1
                if any(colour[w] == shade for w in adjacency[v]):
                    continue
                colour[v] = shade
                quota[c] -= 1
                rec(v + 1)
                quota[c] += 1
                colour[v] = 0

        rec(1)
        result[mu] = {exp: coeff for exp, coeff in poly.items() if coeff}
    return result


def chi_e_expansion(b: tuple[int, ...]) -> dict:
    """The ``e``-expansion ``{lambda: poly_in_q}`` of ``chi_G`` for graph vector ``b``.

    Zero coefficients are dropped; each returned ``poly`` is a ``{q_exp: int}``
    dict with (conjecturally) nonnegative integer coefficients.
    """
    n = len(b)
    edges = frozenset(
        (i, j) for i in range(1, n + 1) for j in range(i + 1, b[i - 1] + 1)
    )
    part_list = partitions_of(n)
    monomial = _monomial_coeffs(n, edges)
    solver = _e_from_m_solver(n)

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
                    raise ValueError(f"non-integer e-coefficient for {lam} at q^{exp}: {value}")
                value = int(value)
            poly[exp] = value
        if poly:
            expansion[lam] = poly
    return expansion
