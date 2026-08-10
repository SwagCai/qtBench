"""Public oracle: the q-Eulerian gamma coefficients ``a_{n,k}(q)``.

Carlitz's ``q``-Eulerian polynomials ``A_n(t,q)`` are defined by

    sum_{j >= 0} [j + 1]_q^n t^j = A_n(t,q) / (t; q)_{n+1},                      (2.1)

with ``[m]_q = 1 + q + ... + q^{m-1}`` and ``(x; q)_N = (1 - x)(1 - xq) ... (1 - xq^{N-1})``,
and equal the joint descent/major-index enumerator ``sum_{sigma in S_n} t^{des sigma}
q^{maj sigma}``. Han, Jouhet and Zeng (arXiv:1203.6736, Theorem 1) proved the
``q``-analogue of the classical ``gamma``-expansion:

    A_n(t,q) = sum_{k=1}^{floor((n+1)/2)} a_{n,k}(q) t^{k-1} (-t q^k; q)_{n+1-2k}  (2.3)

with ``a_{n,k}(q)`` in ``N[q]``, satisfying

    a_{n,k}(q) = [k]_q a_{n-1,k}(q)
               + (1 + q^{k-1}) q^{k-1} [n + 2 - 2k]_q a_{n-1,k-1}(q),             (2.4)

``a_{1,1}(q) = 1``. Han, Jouhet and Zeng ask for a combinatorial interpretation
of ``a_{n,k}(q)`` without prescribing an object family. Problem 17 is qtBench's
stronger proposal to realize it by a statistic on the Foata--Schuetzenberger
permutations that count ``a_{n,k}(1)``.

Everything here is exact integer arithmetic on coefficient lists. The module offers
the coefficients by two routes -- the recurrence (2.4), and solving the expansion
(2.3) against ``A_n(t,q)`` -- and ``A_n`` itself by two routes -- the recurrence
(2.2), and brute force over ``S_n`` -- plus a direct check of the defining identity
(2.1) as a truncated power series in ``t``. The generator runs all of them against
each other. The scored evaluator never imports this module.
"""
from __future__ import annotations

from itertools import permutations

PROBLEM_ID = 17
PROBLEM_NAME = "perm_q_eulerian_gamma_q_stat"


# ---------------------------------------------------------------------------
# Polynomials in q, as lists of integer coefficients (index = exponent)
# ---------------------------------------------------------------------------


def _trim(poly: list[int]) -> list[int]:
    while poly and poly[-1] == 0:
        poly.pop()
    return poly


def add(left, right) -> list[int]:
    out = [0] * max(len(left), len(right))
    for index, value in enumerate(left):
        out[index] += value
    for index, value in enumerate(right):
        out[index] += value
    return _trim(out)


def subtract(left, right) -> list[int]:
    out = [0] * max(len(left), len(right))
    for index, value in enumerate(left):
        out[index] += value
    for index, value in enumerate(right):
        out[index] -= value
    return _trim(out)


def multiply(left, right) -> list[int]:
    if not left or not right:
        return []
    out = [0] * (len(left) + len(right) - 1)
    for i, x in enumerate(left):
        if x:
            for j, y in enumerate(right):
                out[i + j] += x * y
    return _trim(out)


def shift(poly, power: int) -> list[int]:
    """Multiply by ``q^power``."""
    return [0] * power + list(poly) if poly else []


def q_integer(m: int) -> list[int]:
    """``[m]_q = 1 + q + ... + q^{m-1}``, and the zero polynomial for ``m <= 0``."""
    return [1] * m if m > 0 else []


def at_one(poly) -> int:
    return sum(poly)


# ---------------------------------------------------------------------------
# Carlitz's q-Eulerian polynomials
# ---------------------------------------------------------------------------


def q_eulerian(n: int) -> list[list[int]]:
    """``A_n(t,q)`` as ``[A_{n,0}(q), A_{n,1}(q), ...]`` indexed by the power of ``t``.

    Recurrence (2.2), in the paper's indexing ``A_{n,k}(q) = [k]_q A_{n-1,k}(q) +
    q^{k-1} [n + 1 - k]_q A_{n-1,k-1}(q)`` for ``1 <= k <= n``, where the paper's ``k``
    is one more than the power of ``t``.
    """
    if n < 1:
        raise ValueError("size must be positive")
    row = [[1]]
    for size in range(2, n + 1):
        new = [[] for _ in range(size)]
        for k in range(1, size + 1):
            term = multiply(q_integer(k), row[k - 1]) if k - 1 < len(row) else []
            if 0 <= k - 2 < len(row):
                term = add(term, multiply(shift(q_integer(size + 1 - k), k - 1), row[k - 2]))
            new[k - 1] = term
        row = _trim(new) or [[1]]
    return row


def q_eulerian_brute(n: int) -> list[list[int]]:
    """The same, straight from ``sum_{sigma in S_n} t^{des sigma} q^{maj sigma}``."""
    out: list[list[int]] = [[] for _ in range(n)]
    for word in permutations(range(1, n + 1)):
        descents = [i for i in range(1, n) if word[i - 1] > word[i]]
        out[len(descents)] = add(out[len(descents)], shift([1], sum(descents)))
    return _trim(out)


def carlitz_identity_residue(n: int, order: int | None = None):
    """``None`` if (2.1) holds to ``O(t^{order+1})``, else the first failing degree.

    Multiplies the series ``sum_j [j+1]_q^n t^j`` by ``(t; q)_{n+1}`` and compares
    with ``A_n(t,q)`` coefficientwise -- the definition, with no rearrangement. By
    default it preserves the original eight-degree smoke check and also reaches
    degree ``n``, the first coefficient beyond ``deg_t A_n = n - 1``.
    """
    if order is None:
        order = max(8, n)
    eulerian = q_eulerian(n)
    denominator = [[1]]
    for i in range(n + 1):
        new = [[] for _ in range(len(denominator) + 1)]
        for degree, coefficient in enumerate(denominator):
            new[degree] = add(new[degree], coefficient)
            new[degree + 1] = subtract(new[degree + 1], shift(coefficient, i))
        denominator = new
    powers = [_power(q_integer(j + 1), n) for j in range(order + 1)]
    for degree in range(order + 1):
        accumulated: list[int] = []
        for offset, coefficient in enumerate(denominator):
            if degree - offset >= 0:
                accumulated = add(accumulated, multiply(coefficient, powers[degree - offset]))
        expected = eulerian[degree] if degree < len(eulerian) else []
        if accumulated != expected:
            return degree
    return None


def _power(poly, exponent: int) -> list[int]:
    out = [1]
    for _ in range(exponent):
        out = multiply(out, poly)
    return out


# ---------------------------------------------------------------------------
# The gamma coefficients
# ---------------------------------------------------------------------------


def gamma_coefficients(n: int) -> dict:
    """``{k: a_{n,k}(q)}`` from the recurrence (2.4)."""
    if n < 1:
        raise ValueError("size must be positive")
    rows: dict = {1: {1: [1]}}
    for size in range(2, n + 1):
        previous = rows[size - 1]
        current: dict = {}
        for k in range(1, (size + 1) // 2 + 1):
            term = multiply(q_integer(k), previous.get(k, []))
            lower = previous.get(k - 1, [])
            if lower:
                factor = multiply(
                    add([1], shift([1], k - 1)),                       # 1 + q^{k-1}
                    shift(q_integer(size + 2 - 2 * k), k - 1),         # q^{k-1} [n+2-2k]_q
                )
                term = add(term, multiply(factor, lower))
            if term:
                current[k] = term
        rows[size] = current
    return rows[n]


def gamma_coefficients_from_expansion(n: int) -> dict:
    """``{k: a_{n,k}(q)}`` by solving (2.3) against ``A_n(t,q)``.

    The ``k``-th basis element starts at ``t^{k-1}``, so the system is triangular:
    read ``a_{n,k}`` off the coefficient of ``t^{k-1}`` of what is left, subtract its
    contribution, and continue. If the expansion did not close exactly, the residue
    is nonzero and this raises.
    """
    remainder = [list(coefficient) for coefficient in q_eulerian(n)]
    while len(remainder) < n + 1:
        remainder.append([])
    out: dict = {}
    for k in range(1, (n + 1) // 2 + 1):
        basis = _basis_element(n, k)
        coefficient = remainder[k - 1]
        if not coefficient:
            continue
        out[k] = list(coefficient)
        for degree, piece in enumerate(basis):
            if degree < len(remainder):
                remainder[degree] = subtract(remainder[degree], multiply(coefficient, piece))
    if any(remainder):
        raise ValueError(f"n={n}: the gamma expansion left the residue {remainder}")
    return out


def _basis_element(n: int, k: int) -> list[list[int]]:
    """``t^{k-1} (-t q^k; q)_{n+1-2k}`` as a list of ``q``-polynomials indexed by ``t``."""
    product: list[list[int]] = [[1]]
    for i in range(n + 1 - 2 * k):
        new: list[list[int]] = [[] for _ in range(len(product) + 1)]
        for degree, coefficient in enumerate(product):
            new[degree] = add(new[degree], coefficient)
            new[degree + 1] = add(new[degree + 1], shift(coefficient, k + i))
        product = new
    return [[]] * (k - 1) + product
