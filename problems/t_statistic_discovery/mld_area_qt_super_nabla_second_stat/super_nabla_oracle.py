"""Public oracle: the target polynomials H_{n,k}(q,t) of problem 10.

This public oracle is used only to
regenerate the public polynomial targets; the scored evaluator never loads it.

For ``n, k >= 1`` it computes the "Hilbert series"

    H_{n,k}(q, t) = < nabla_*^k e_n , e_{1^n} tensor ... tensor e_{1^n} >

(``k + 1`` tensor factors) of the super nabla operator of Bergeron, Haglund,
Iraci and Romero (arXiv:2303.00560), whose ``t = 1`` specialisation is proven
there to equal the ``area`` enumerator of the standard multi-labelled ``k^n``
Dyck paths ``LD_{k^n}``.

Method (all exact, stdlib only): ``nabla_*`` is defined by
``nabla_* Ht_mu = Ht_mu tensor Ht_mu``, so iterating and expanding
``e_n = sum_mu (M B_mu Pi_mu / w_mu) Ht_mu`` gives

    nabla_*^k e_n = sum_mu (M B_mu Pi_mu / w_mu) Ht_mu(X_0) ... Ht_mu(X_k),

and pairing each factor with ``e_{1^n} = h_{1^n}`` picks the coefficient of
``x_1 ... x_n``, i.e. ``<Ht_mu, e_{1^n}> = n! [p_{1^n}] Ht_mu``. Hence

    H_{n,k} = sum_mu (M B_mu Pi_mu / w_mu) * (n! [p_{1^n}] Ht_mu)^{k+1},

with Ht_mu obtained numerically from the Garsia-Haiman-Tesler two-plethystic
triangularity. Each H_{n,k}(q, t) is a nonnegative-integer, q,t-symmetric
polynomial; it is evaluated at integer sample points with exact ``Fraction``
arithmetic and then bivariately interpolated (degree bound the maximal ``area``).
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
from functools import lru_cache
from math import factorial

PROBLEM_ID = 10
PROBLEM_NAME = "mld_area_qt_super_nabla_second_stat"


# ---------------------------------------------------------------------------
# Partitions and elementary constants
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Symmetric group characters via Murnaghan-Nakayama
# ---------------------------------------------------------------------------

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
    return sum((-1) ** height * character(newshape, rest) for newshape, height in _border_strips(lam, k))


# ---------------------------------------------------------------------------
# Arm / leg of a partition
# ---------------------------------------------------------------------------

def cells(mu: tuple[int, ...]):
    return [(i, j) for j, part in enumerate(mu) for i in range(part)]


def arm(mu, c):
    i, j = c
    return mu[j] - 1 - i


def leg(mu, c):
    i, j = c
    return sum(1 for jj in range(j + 1, len(mu)) if mu[jj] > i)


# ---------------------------------------------------------------------------
# Exact linear algebra over Q
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Modified Macdonald Ht_mu numerically at (q0, t0), in the power-sum basis
# ---------------------------------------------------------------------------

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
    rows.append([Fraction(character(row_n, rho)) for rho in parts])  # chi^{(n)} = 1
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
    return sum((q0 ** i * t0 ** j for (i, j) in cells(mu)), Fraction(0))


def w_num(mu, q0, t0):
    v = Fraction(1)
    for c in cells(mu):
        a = arm(mu, c)
        l = leg(mu, c)
        v *= (q0 ** a - t0 ** (l + 1)) * (t0 ** l - q0 ** (a + 1))
    return v


def H_at(n: int, k: int, q0, t0):
    """H_{n,k}(q0, t0) evaluated exactly at a sample point."""
    M = (1 - q0) * (1 - t0)
    key1n = tuple([1] * n)
    total = Fraction(0)
    for mu in partitions(n):
        ht = ht_numeric(mu, q0, t0)
        hilbert = factorial(n) * ht.get(key1n, Fraction(0))
        total += M * B_num(mu, q0, t0) * Pi_num(mu, q0, t0) / w_num(mu, q0, t0) * hilbert ** (k + 1)
    return total


# ---------------------------------------------------------------------------
# Bivariate interpolation over an integer grid
# ---------------------------------------------------------------------------

def _primes(count: int) -> list[int]:
    found = []
    candidate = 2
    while len(found) < count:
        if all(candidate % p for p in found if p * p <= candidate):
            found.append(candidate)
        candidate += 1
    return found


def _lagrange(xs, ys):
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


def H_poly(n: int, k: int, degbound: int | None = None) -> dict[tuple[int, int], int]:
    """Return {(i, j): coeff} of q^i t^j in H_{n,k}(q, t).

    ``degbound`` bounds the degree in each variable; the true bidegree is the
    maximal ``area``, ``k * n * (n - 1) / 2``, which is also the default.
    """
    if degbound is None:
        degbound = max(1, k * n * (n - 1) // 2)
    D = degbound
    primes = _primes(2 * (D + 1))
    qgrid = [Fraction(p) for p in primes[: D + 1]]
    tgrid = [Fraction(p) for p in primes[D + 1: 2 * (D + 1)]]
    values = [[H_at(n, k, qgrid[a], tgrid[b]) for b in range(D + 1)] for a in range(D + 1)]
    coeffs_t = [_lagrange(tgrid, values[a]) for a in range(D + 1)]
    result: dict[tuple[int, int], int] = {}
    for j in range(D + 1):
        cq = _lagrange(qgrid, [coeffs_t[a][j] for a in range(D + 1)])
        for i in range(D + 1):
            c = cq[i]
            if c != 0:
                if c.denominator != 1:
                    raise ValueError(f"non-integer coefficient {c} at (q^{i}, t^{j}) of H_{n},{k}")
                result[(i, j)] = int(c)
    return result
