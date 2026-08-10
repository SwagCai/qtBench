"""Public oracle: the target polynomials G_mu(q,t) of problem 19.

This public oracle is used only to
regenerate the public polynomial targets; the scored evaluator never loads it.

For a partition ``mu`` with ``n = |mu|`` and ``N = n + 1`` it computes the
"Hilbert series"

    G_mu(q, t) = < Theta_{e_mu} e_1 , e_{1^N} >

of the Theta operator of D'Adderio, Iraci, Le Borgne, Romero and Vanden
Wyngaerd (arXiv:2202.05706). Theorem 4.6 there proves that its ``t = 1``
specialisation is the ``inv`` enumerator of standard rooted tiered trees
``stRTT(mu)``, and the first identity of Problem 6.5 asks for the missing
``t``-statistic.

Method (all exact, stdlib only): since ``Pi^{-1} e_1 = e_1``,

    Theta_{e_mu} e_1 = Pi( e_mu[X/M] * e_1 ),

and ``< Pi P, e_{1^N} > = N! * [p_{1^N}] Pi P``. Writing ``P`` in the power-sum
basis and expanding in the modified Macdonald basis ``Ht_nu`` (obtained
numerically from the Garsia-Haiman-Tesler two-plethystic triangularity),

    G_mu = N! * sum_nu Pi_nu * <P, Ht_nu>_* / w_nu * [p_{1^N}] Ht_nu .

Each target is evaluated at integer sample points with exact ``Fraction``
arithmetic and then bivariately interpolated.
"""
from __future__ import annotations

PROBLEM_ID = 19
PROBLEM_NAME = "rtt_inv_qt_theta_second_stat"


from collections import Counter
from fractions import Fraction
from functools import lru_cache
from math import factorial


@lru_cache(maxsize=None)
def partitions(n: int) -> tuple[tuple[int, ...], ...]:
    if n == 0:
        return ((),)
    out: list[tuple[int, ...]] = []

    def rec(remaining: int, maxpart: int, prefix: list[int]) -> None:
        if remaining == 0:
            out.append(tuple(prefix))
            return
        for p in range(min(remaining, maxpart), 0, -1):
            rec(remaining - p, p, prefix + [p])

    rec(n, n, [])
    return tuple(out)


def z_lambda(lam: tuple[int, ...]) -> int:
    z = 1
    for part, mult in Counter(lam).items():
        z *= (part ** mult) * factorial(mult)
    return z


def eps_lambda(lam: tuple[int, ...]) -> int:
    return (-1) ** (sum(lam) - len(lam))


def conjugate(lam: tuple[int, ...]) -> tuple[int, ...]:
    if not lam:
        return ()
    return tuple(sum(1 for p in lam if p >= i) for i in range(1, lam[0] + 1))


def dominates(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    la = list(a) + [0] * len(b)
    lb = list(b) + [0] * len(a)
    sa = sb = 0
    for i in range(max(len(a), len(b))):
        sa += la[i]
        sb += lb[i]
        if sa < sb:
            return False
    return True


# --------------------------------------------------------------------------
# Symmetric group characters via Murnaghan-Nakayama
# --------------------------------------------------------------------------

def _border_strips(lam: tuple[int, ...], k: int):
    lam = list(lam)
    r = len(lam)
    beta = sorted((lam[i] + (r - 1 - i) for i in range(r)), reverse=True)
    beta_set = set(beta)
    results = []
    for b in list(beta):
        if b - k >= 0 and (b - k) not in beta_set:
            newbeta = sorted((beta_set - {b}) | {b - k}, reverse=True)
            rr = len(newbeta)
            newlam = tuple(newbeta[i] - (rr - 1 - i) for i in range(rr))
            newlam = tuple(p for p in newlam if p > 0)
            height = sum(1 for x in beta_set if b - k < x < b)
            results.append((newlam, height))
    return results


@lru_cache(maxsize=None)
def character(lam: tuple[int, ...], rho: tuple[int, ...]) -> int:
    if sum(lam) == 0:
        return 1
    k = rho[0]
    rest = rho[1:]
    return sum(
        (-1) ** height * character(newshape, rest)
        for newshape, height in _border_strips(lam, k)
    )


# --------------------------------------------------------------------------
# Arm / leg / coarm / coleg
# --------------------------------------------------------------------------

def cells(mu: tuple[int, ...]):
    """Cells ``(coarm, coleg)`` of ``mu`` drawn in French notation."""
    return [(i, j) for j, part in enumerate(mu) for i in range(part)]


def arm(mu, c):
    i, j = c
    return mu[j] - 1 - i


def leg(mu, c):
    i, j = c
    return sum(1 for jj in range(j + 1, len(mu)) if mu[jj] > i)


# --------------------------------------------------------------------------
# Exact linear algebra over Q
# --------------------------------------------------------------------------

def solve_unique(rows, rhs, nvars):
    A = [list(r) + [b] for r, b in zip(rows, rhs)]
    m = len(A)
    pivots: dict[int, int] = {}
    r = 0
    for col in range(nvars):
        piv = next((i for i in range(r, m) if A[i][col] != 0), None)
        if piv is None:
            continue
        A[r], A[piv] = A[piv], A[r]
        inv = A[r][col]
        A[r] = [x / inv for x in A[r]]
        for i in range(m):
            if i != r and A[i][col] != 0:
                f = A[i][col]
                A[i] = [a - f * b for a, b in zip(A[i], A[r])]
        pivots[col] = r
        r += 1
        if r == nvars:
            break
    if len(pivots) != nvars:
        raise ValueError(f"system underdetermined: rank {len(pivots)} < {nvars}")
    sol = [Fraction(0)] * nvars
    for col, row in pivots.items():
        sol[col] = A[row][-1]
    return sol


# --------------------------------------------------------------------------
# Modified Macdonald Ht_nu numerically at (q0, t0), in the power-sum basis
# --------------------------------------------------------------------------

def ht_numeric(mu, q0, t0):
    n = sum(mu)
    parts = partitions(n)
    nv = len(parts)
    muprime = conjugate(mu)
    row_n = tuple([n])

    def pleth(rho, base):
        v = Fraction(1)
        for part in rho:
            v *= (1 - base ** part)
        return v

    rows = []
    rhs = []
    for lam in parts:
        if not dominates(lam, mu):
            rows.append([pleth(rho, q0) * character(lam, rho) for rho in parts])
            rhs.append(Fraction(0))
    for lam in parts:
        if not dominates(lam, muprime):
            rows.append([pleth(rho, t0) * character(lam, rho) for rho in parts])
            rhs.append(Fraction(0))
    rows.append([Fraction(character(row_n, rho)) for rho in parts])
    rhs.append(Fraction(1))

    sol = solve_unique(rows, rhs, nv)
    return {parts[i]: sol[i] for i in range(nv)}


def Pi_num(mu, q0, t0):
    v = Fraction(1)
    for (i, j) in cells(mu):
        if (i, j) == (0, 0):
            continue
        v *= (1 - q0 ** i * t0 ** j)
    return v


def B_num(mu, q0, t0):
    return sum((q0 ** i * t0 ** j for i, j in cells(mu)), Fraction(0))


def m_gamma_at_B(gamma, mu, q0, t0):
    """``m_gamma[B_mu]`` evaluated at the sample point."""
    if not gamma:
        return Fraction(1)
    weights = [q0 ** i * t0 ** j for i, j in cells(mu)]
    order = len(weights)
    ell = len(gamma)
    if ell > order:
        return Fraction(0)
    total = Fraction(0)
    used = [False] * order

    def rec(index: int, acc):
        nonlocal total
        if index == ell:
            total += acc
            return
        for k in range(order):
            if not used[k]:
                used[k] = True
                rec(index + 1, acc * weights[k] ** gamma[index])
                used[k] = False

    rec(0, Fraction(1))
    # Each distinct monomial was produced once for every rearrangement of the
    # equal parts of gamma, so divide by the automorphisms of gamma.
    divisor = 1
    for mult in Counter(gamma).values():
        divisor *= factorial(mult)
    return total / divisor


def w_num(mu, q0, t0):
    v = Fraction(1)
    for c in cells(mu):
        a = arm(mu, c)
        l = leg(mu, c)
        v *= (q0 ** a - t0 ** (l + 1)) * (t0 ** l - q0 ** (a + 1))
    return v


def star_norm(rho, q0, t0):
    v = Fraction(z_lambda(rho) * eps_lambda(rho))
    for part in rho:
        v *= (1 - q0 ** part) * (1 - t0 ** part)
    return v


def e_star_num(k, q0, t0):
    """``e_k[X/M]`` in the power-sum basis."""
    out = {}
    for lam in partitions(k):
        denom = Fraction(1)
        for part in lam:
            denom *= (1 - q0 ** part) * (1 - t0 ** part)
        out[lam] = Fraction(eps_lambda(lam), z_lambda(lam)) / denom
    return out


def s_star_num(lam, q0, t0):
    """``s_lam[X/M]`` in the power-sum basis."""
    n = sum(lam)
    out = {}
    for rho in partitions(n):
        denom = Fraction(1)
        for part in rho:
            denom *= (1 - q0 ** part) * (1 - t0 ** part)
        out[rho] = Fraction(character(lam, rho), z_lambda(rho)) / denom
    return out


def pmult(f, g):
    out = {}
    for lam, a in f.items():
        for mu, b in g.items():
            key = tuple(sorted(lam + mu, reverse=True))
            out[key] = out.get(key, Fraction(0)) + a * b
    return out


def e_star_product(mu, q0, t0):
    """``e_mu[X/M] = prod_i e_{mu_i}[X/M]`` in the power-sum basis."""
    P = {(): Fraction(1)}
    for part in mu:
        P = pmult(P, e_star_num(part, q0, t0))
    return P


def p_expansion(coeffs, N, q0, t0):
    """Expand ``sum_nu coeffs[nu] Ht_nu`` in the power-sum basis."""
    out = {rho: Fraction(0) for rho in partitions(N)}
    for nu, c in coeffs.items():
        if not c:
            continue
        ht = ht_numeric(nu, q0, t0)
        for rho, v in ht.items():
            out[rho] += c * v
    return out


def macdonald_coefficients(P, N, q0, t0):
    """Coefficients ``a_nu`` with ``P = sum_nu a_nu Ht_nu``, for ``P`` in p-basis."""
    out = {}
    for nu in partitions(N):
        ht = ht_numeric(nu, q0, t0)
        acc = Fraction(0)
        for rho, coeff in P.items():
            if rho in ht:
                acc += coeff * ht[rho] * star_norm(rho, q0, t0)
        out[nu] = acc / w_num(nu, q0, t0)
    return out


# --------------------------------------------------------------------------
# p-basis to e-basis transition
# --------------------------------------------------------------------------

@lru_cache(maxsize=None)
def e_in_p(eta: tuple[int, ...]) -> tuple[tuple[tuple[int, ...], Fraction], ...]:
    """``e_eta`` written in the power-sum basis, as exact rationals."""
    acc = {(): Fraction(1)}
    for part in eta:
        piece = {
            rho: Fraction(eps_lambda(rho), z_lambda(rho)) for rho in partitions(part)
        }
        new = {}
        for lam, a in acc.items():
            for rho, b in piece.items():
                key = tuple(sorted(lam + rho, reverse=True))
                new[key] = new.get(key, Fraction(0)) + a * b
        acc = new
    return tuple(sorted(acc.items()))


def e_expansion(P, N):
    """Rewrite ``P`` (a p-basis dict) in the elementary basis."""
    parts = partitions(N)
    index = {rho: i for i, rho in enumerate(parts)}
    columns = []
    for eta in parts:
        column = [Fraction(0)] * len(parts)
        for rho, value in e_in_p(eta):
            column[index[rho]] = value
        columns.append(column)
    rows = [[columns[j][i] for j in range(len(parts))] for i in range(len(parts))]
    rhs = [P.get(rho, Fraction(0)) for rho in parts]
    solution = solve_unique(rows, rhs, len(parts))
    return {parts[j]: solution[j] for j in range(len(parts))}


# --------------------------------------------------------------------------
# Interpolation
# --------------------------------------------------------------------------

def primes(count: int) -> list[int]:
    found: list[int] = []
    candidate = 2
    while len(found) < count:
        if all(candidate % p for p in found if p * p <= candidate):
            found.append(candidate)
        candidate += 1
    return found


def lagrange(xs, ys):
    n = len(xs)
    coeffs = [Fraction(0)] * n
    for i in range(n):
        num = [Fraction(1)]
        denom = Fraction(1)
        for j in range(n):
            if j == i:
                continue
            new = [Fraction(0)] * (len(num) + 1)
            for d, c in enumerate(num):
                new[d] += c * (-xs[j])
                new[d + 1] += c
            num = new
            denom *= (xs[i] - xs[j])
        scale = ys[i] / denom
        for d in range(len(num)):
            coeffs[d] += num[d] * scale
    return coeffs


def interpolate_bivariate(evaluate, degree_bound: int):
    """Interpolate a scalar-valued ``evaluate(q0, t0)`` into ``{(i, j): coeff}``."""
    D = degree_bound
    grid = primes(2 * (D + 1))
    qgrid = [Fraction(p) for p in grid[: D + 1]]
    tgrid = [Fraction(p) for p in grid[D + 1:]]
    values = [[evaluate(qgrid[a], tgrid[b]) for b in range(D + 1)] for a in range(D + 1)]
    coeffs_t = [lagrange(tgrid, values[a]) for a in range(D + 1)]
    result: dict[tuple[int, int], Fraction] = {}
    for j in range(D + 1):
        cq = lagrange(qgrid, [coeffs_t[a][j] for a in range(D + 1)])
        for i in range(D + 1):
            if cq[i]:
                result[(i, j)] = cq[i]
    return result


def evaluate_poly(poly, q0, t0):
    return sum((c * q0 ** i * t0 ** j for (i, j), c in poly.items()), Fraction(0))


def substitute_q_one_plus_u(poly):
    """Rewrite ``f(q, t)`` as a polynomial in ``u = q - 1`` and ``t``."""
    out: dict[tuple[int, int], Fraction] = {}
    max_i = max((i for i, _ in poly), default=0)
    table = [[0] * (max_i + 1) for _ in range(max_i + 1)]
    for i in range(max_i + 1):
        table[i][0] = 1
        for k in range(1, i + 1):
            table[i][k] = table[i - 1][k - 1] + table[i - 1][k]
    for (i, j), c in poly.items():
        for k in range(i + 1):
            key = (k, j)
            out[key] = out.get(key, Fraction(0)) + c * table[i][k]
    return {key: value for key, value in out.items() if value}


def G_poly(mu, degree_bound: int) -> dict[tuple[int, int], int]:
    """Return ``{(i, j): coeff}`` of ``q^i t^j`` in ``G_mu(q, t)``.

    ``degree_bound`` bounds the degree in each variable; the caller passes the
    maximal ``inv`` over ``stRTT(mu)`` plus a margin, and the interpolated
    polynomial is re-checked at sample points outside the grid.
    """
    mu = tuple(int(part) for part in mu)
    N = sum(mu) + 1
    key = tuple([1] * N)
    scale = factorial(N)

    def evaluate(q0, t0):
        base = pmult(e_star_product(mu, q0, t0), {(1,): Fraction(1)})
        a = macdonald_coefficients(base, N, q0, t0)
        total = Fraction(0)
        for nu, value in a.items():
            if not value:
                continue
            ht = ht_numeric(nu, q0, t0)
            total += value * Pi_num(nu, q0, t0) * ht.get(key, Fraction(0))
        return scale * total

    poly = interpolate_bivariate(evaluate, degree_bound)
    for base_q, base_t in ((Fraction(-3), Fraction(-5)), (Fraction(-7), Fraction(-11))):
        if evaluate_poly(poly, base_q, base_t) != evaluate(base_q, base_t):
            raise ValueError(f"interpolation bound {degree_bound} too small for mu={mu}")
    if any(value.denominator != 1 for value in poly.values()):
        raise ValueError(f"non-integer coefficient in G_{mu}")
    return {key: int(value) for key, value in poly.items()}
