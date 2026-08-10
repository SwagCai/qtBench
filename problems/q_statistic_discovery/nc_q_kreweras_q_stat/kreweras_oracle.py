"""Public oracle: the type A q-Kreweras numbers of Reiner and Sommers.

For a partition ``lambda`` of ``n`` and a parameter ``m`` coprime to ``n``, Reiner
and Sommers (arXiv:1605.09172, Theorem 1.5, type ``A_{n-1}``) give

    Krew(lambda; m; q) = q^{m(n - l(lambda)) - c(lambda)} (1 / [m]_q) [ m ; mu(lambda) ]_q,

where ``mu(lambda)`` is the multiplicity vector of ``lambda``, ``c(lambda) =
sum_j lambda'_j lambda'_{j+1}`` is built from the conjugate partition, and

    [ m ; nu ]_q = [m]!_q / ([nu_1]!_q ... [nu_t]!_q [m - |nu|]!_q)

is the q-multinomial. The classical Kreweras refinement of the Catalan number is the
case ``m = n + 1``, which is the target of problem 23:

    Krew_lambda(q) := Krew(lambda; n + 1; q),
    Krew_lambda(1) = #{ pi in NC(n) : type(pi) = lambda },
    sum_{lambda |- n} Krew_lambda(q) = (1 / [n+1]_q) [ 2n ; n ]_q, the q-Catalan number.

The polynomial is what the cyclic sieving phenomenon for noncrossing partitions
refines to; what is missing, and what problem 23 asks for, is a statistic on
``NC(n)`` whose generating function it is.

All arithmetic is exact on integer coefficient lists, and every division is a
polynomial division with a checked zero remainder, so a wrong formula could not
silently produce a plausible answer. The scored evaluator never imports this module.
"""
from __future__ import annotations

from collections import Counter

PROBLEM_ID = 23
PROBLEM_NAME = "nc_q_kreweras_q_stat"


def _trim(poly: list[int]) -> list[int]:
    while poly and poly[-1] == 0:
        poly.pop()
    return poly


def multiply(left, right) -> list[int]:
    if not left or not right:
        return []
    out = [0] * (len(left) + len(right) - 1)
    for i, x in enumerate(left):
        if x:
            for j, y in enumerate(right):
                out[i + j] += x * y
    return _trim(out)


def divide(numerator, denominator) -> list[int]:
    """Exact division of integer polynomials; raises if the remainder is nonzero."""
    numerator = list(numerator)
    if not denominator:
        raise ValueError("division by the zero polynomial")
    quotient = [0] * (len(numerator) - len(denominator) + 1)
    for degree in range(len(quotient) - 1, -1, -1):
        value, remainder = divmod(numerator[degree + len(denominator) - 1], denominator[-1])
        if remainder:
            raise ValueError("q-polynomial division left a remainder")
        quotient[degree] = value
        for offset, coefficient in enumerate(denominator):
            numerator[degree + offset] -= value * coefficient
    if _trim(numerator):
        raise ValueError("q-polynomial division left a remainder")
    return _trim(quotient)


def q_integer(m: int) -> list[int]:
    return [1] * m if m > 0 else []


def q_factorial(m: int) -> list[int]:
    out = [1]
    for value in range(1, m + 1):
        out = multiply(out, q_integer(value))
    return out


def shift(poly, power: int) -> list[int]:
    return [0] * power + list(poly) if poly else []


def conjugate(lam) -> list[int]:
    return [sum(1 for part in lam if part > column) for column in range(lam[0])] if lam else []


def q_multinomial(m: int, nu) -> list[int]:
    """``[ m ; nu ]_q``, and the zero polynomial when ``|nu| > m``."""
    if sum(nu) > m:
        return []
    denominator = q_factorial(m - sum(nu))
    for value in nu:
        denominator = multiply(denominator, q_factorial(value))
    return divide(q_factorial(m), denominator)


def kreweras(lam, n: int, m: int | None = None) -> list[int]:
    """``Krew(lambda; m; q)``; ``m`` defaults to ``n + 1``, the classical case."""
    if sum(lam) != n:
        raise ValueError(f"{lam} is not a partition of {n}")
    if m is None:
        m = n + 1
    multiplicities = Counter(lam)
    nu = [multiplicities.get(part, 0) for part in range(1, n + 1)]
    columns = conjugate(lam)
    charge = sum(
        columns[j] * (columns[j + 1] if j + 1 < len(columns) else 0)
        for j in range(len(columns))
    )
    reduced = divide(q_multinomial(m, nu), q_integer(m))
    return shift(reduced, m * (n - len(lam)) - charge)


def q_catalan(n: int) -> list[int]:
    """``(1 / [n+1]_q) [ 2n ; n ]_q``, the MacMahon q-Catalan number."""
    binomial = divide(q_factorial(2 * n), multiply(q_factorial(n), q_factorial(n)))
    return divide(binomial, q_integer(n + 1))
