"""Public oracle: the promotion cyclic sieving polynomial C_lambda(q).

Schuetzenberger promotion ``d`` acts on ``SYT(lambda)``. Let ``Z/N`` act through it,
with ``N = rc`` for a rectangle ``lambda = c^r`` and ``N = k(k+1)`` for a staircase
``sc_k``. Grouping the tableaux into ``<d>``-orbits, the least-degree cyclic sieving
polynomial is

    C_lambda(q) = sum_{orbits O} (1 + q^{N/|O|} + ... + q^{(|O|-1)N/|O|}),

which is the polynomial Pon--Wang call ``p_{a,X}`` (arXiv:1003.2728, Section 1). By
construction it satisfies ``C_lambda(1) = |SYT(lambda)|`` and the cyclic sieving
evaluations ``C_lambda(zeta^d) = #Fix(d^d)`` at every ``N``-th root of unity; both
are checked here rather than assumed.

The target of problem 22 is ``C_lambda(q)``. Finding a statistic whose generating
function it is, for staircases, is Problem 1.1 of Pon--Wang; on rectangles the
answer is Rhoades' theorem, and the oracle checks that too.

Everything is exact: promotion is computed by jeu de taquin on integer grids, the
orbits by following the permutation, and the root-of-unity evaluations with exact
integer arithmetic in the cyclotomic quotient ``Z[q]/(q^N - 1)`` rather than
floating point. The scored evaluator never imports this module.
"""
from __future__ import annotations

PROBLEM_ID = 22
PROBLEM_NAME = "syt_promotion_csp_q_stat"


def promotion(rows) -> tuple[tuple[int, ...], ...]:
    """Schuetzenberger promotion: delete ``1``, slide southeast, fill, shift down."""
    shape = [len(row) for row in rows]
    cells = sum(shape)
    grid = [list(row) for row in rows]
    i = j = 0
    grid[0][0] = 0
    while True:
        right = grid[i][j + 1] if j + 1 < shape[i] else None
        below = grid[i + 1][j] if i + 1 < len(shape) and j < shape[i + 1] else None
        if right is None and below is None:
            break
        if below is None or (right is not None and right < below):
            grid[i][j], grid[i][j + 1] = right, 0
            j += 1
        else:
            grid[i][j], grid[i + 1][j] = below, 0
            i += 1
    grid[i][j] = cells + 1
    return tuple(tuple(value - 1 for value in row) for row in grid)


def orbit_sizes(tableaux) -> list[int]:
    """Sizes of the promotion orbits on the given list of tableaux (as row tuples)."""
    index = {rows: position for position, rows in enumerate(tableaux)}
    image = [index[promotion(rows)] for rows in tableaux]
    seen = [False] * len(tableaux)
    sizes: list[int] = []
    for start in range(len(tableaux)):
        if seen[start]:
            continue
        size = 0
        node = start
        while not seen[node]:
            seen[node] = True
            node = image[node]
            size += 1
        sizes.append(size)
    return sizes


def sieving_polynomial(tableaux, modulus: int) -> list[int]:
    """``C_lambda(q)`` as a coefficient list of length at most ``modulus``."""
    coefficients = [0] * modulus
    for size in orbit_sizes(tableaux):
        if modulus % size:
            raise ValueError(f"orbit of size {size} does not divide the modulus {modulus}")
        for step in range(size):
            coefficients[step * modulus // size] += 1
    while coefficients and coefficients[-1] == 0:
        coefficients.pop()
    return coefficients


def fixed_point_counts(tableaux, modulus: int) -> list[int]:
    """``#Fix(d^e)`` for ``e = 0, ..., modulus - 1``, computed from the orbits."""
    counts = [0] * modulus
    for size in orbit_sizes(tableaux):
        for exponent in range(modulus):
            if exponent % size == 0:
                counts[exponent] += size
    return counts


def _cyclotomic(order: int) -> list[int]:
    """The ``order``-th cyclotomic polynomial, by dividing out the smaller ones."""
    numerator = [-1] + [0] * (order - 1) + [1]          # x^order - 1
    for divisor in range(1, order):
        if order % divisor:
            continue
        numerator = _divide(numerator, _cyclotomic(divisor))
    return numerator


def _divide(numerator: list[int], denominator: list[int]) -> list[int]:
    """Exact division of monic integer polynomials."""
    numerator = list(numerator)
    quotient = [0] * (len(numerator) - len(denominator) + 1)
    for degree in range(len(quotient) - 1, -1, -1):
        factor = numerator[degree + len(denominator) - 1]
        quotient[degree] = factor
        for offset, value in enumerate(denominator):
            numerator[degree + offset] -= factor * value
    if any(numerator):
        raise ValueError("polynomial division left a remainder")
    return quotient


def check_cyclic_sieving(coefficients: list[int], modulus: int, tableaux) -> None:
    """``C_lambda(zeta^e) = #Fix(d^e)`` for every ``e``, checked exactly.

    Evaluating at ``zeta^e``, of multiplicative order ``d = N / gcd(N, e)``, folds the
    exponents modulo ``d``; the value is the integer ``#Fix(d^e)`` exactly when the
    folded polynomial minus that integer is divisible by the ``d``-th cyclotomic
    polynomial. That is an integer polynomial division, so no floating point enters.
    """
    from math import gcd

    expected = fixed_point_counts(tableaux, modulus)
    for exponent in range(modulus):
        order = modulus // gcd(modulus, exponent)
        folded = [0] * order
        for degree, value in enumerate(coefficients):
            folded[degree % order] += value
        folded[0] -= expected[exponent]
        if order == 1:
            if any(folded):
                raise ValueError(f"cyclic sieving fails at e={exponent}")
            continue
        remainder = list(folded)
        cyclotomic = _cyclotomic(order)
        for degree in range(len(remainder) - 1, len(cyclotomic) - 2, -1):
            factor = remainder[degree]
            if not factor:
                continue
            for offset, value in enumerate(cyclotomic):
                remainder[degree - len(cyclotomic) + 1 + offset] -= factor * value
        if any(remainder):
            raise ValueError(
                f"cyclic sieving fails at e={exponent}: residue {remainder}"
            )


def check_promotion(tableaux, modulus: int) -> None:
    """Promotion is a permutation of ``SYT(lambda)`` and ``d^N`` is the identity."""
    images = [promotion(rows) for rows in tableaux]
    known = set(tableaux)
    if any(image not in known for image in images):
        raise ValueError("promotion left the tableau set")
    if len(set(images)) != len(tableaux):
        raise ValueError("promotion is not injective")
    for size in orbit_sizes(tableaux):
        if modulus % size:
            raise ValueError(f"d^{modulus} is not the identity: orbit of size {size}")
