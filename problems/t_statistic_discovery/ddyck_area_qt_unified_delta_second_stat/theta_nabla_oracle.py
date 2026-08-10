"""Public oracle: the target polynomials F_{n,k,l}(q,t) of problem 7.

This public oracle is used only to
regenerate the public polynomial targets; the scored evaluator never loads it.

For ``n >= 1`` and ``0 <= k, l`` with ``c := n - k - l >= 1`` it computes the
"Hilbert series"

    F_{n,k,l}(q, t) = < Theta_{e_k} Theta_{e_l} nabla e_{n-k-l} , e_{1^n} >

of the unified-Delta symmetric function of Iraci, Nadeau and Vanden Wyngaerd
(arXiv:2312.03956), whose ``q = 1`` (equivalently, by symmetry, ``t = 1``)
specialisation is conjectured there to equal the ``area`` enumerator of the
standardly labelled doubly decorated Dyck paths ``LD(n)^{*k, •l}``.

Method (all exact, stdlib only): with the operators diagonal on the modified
Macdonald basis Ht_mu -- ``nabla Ht_mu = T_mu Ht_mu`` and ``Pi Ht_mu = Pi_mu
Ht_mu`` -- and ``Theta_f g = Pi( f[X/M] * Pi^{-1} g )``, the nested operators
collapse to

    Theta_{e_k} Theta_{e_l} nabla e_c = Pi( e_k[X/M] * e_l[X/M] * Pi^{-1}(nabla e_c) ).

Writing everything in the power-sum basis and pairing with e_{1^n} via
``< Pi P, e_{1^n} > = n! * [p_{1^n}] Pi P``, this is

    F_{n,k,l} = n! * sum_mu Pi_mu * <Q, Ht_mu>_* / w_mu * [p_{1^n}] Ht_mu,

where ``Q = e_k[X/M] e_l[X/M] Pi^{-1}(nabla e_c)`` and Ht_mu is obtained
numerically from the Garsia-Haiman-Tesler two-plethystic triangularity. Each
F_{n,k,l}(q, t) is a nonnegative-integer, q,t-symmetric polynomial; it is
evaluated at integer sample points with exact ``Fraction`` arithmetic and then
bivariately interpolated (degree bound the maximal ``area``).
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
from functools import lru_cache
from math import factorial

PROBLEM_ID = 7
PROBLEM_NAME = "ddyck_area_qt_unified_delta_second_stat"


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
# Arm / leg / co-arm / co-leg of a partition
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


def T_num(mu, q0, t0):
    """The nabla eigenvalue T_mu = prod_{cells} q^{a'} t^{l'}."""
    v = Fraction(1)
    for (i, j) in cells(mu):
        v *= q0 ** i * t0 ** j
    return v


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
    """e_k[X/M] in the power-sum basis (empty product gives e_0[X/M] = 1)."""
    out = {}
    for lam in partitions(k):
        denom = Fraction(1)
        for part in lam:
            denom *= (1 - q0 ** part) * (1 - t0 ** part)
        out[lam] = Fraction(eps_lambda(lam), z_lambda(lam)) / denom
    return out


def e_power(k):
    """e_k in the power-sum basis: {lam: eps_lam / z_lam}."""
    return {lam: Fraction(eps_lambda(lam), z_lambda(lam)) for lam in partitions(k)}


def pmult(f, g):
    out = {}
    for lam, a in f.items():
        for mu, b in g.items():
            key = tuple(sorted(lam + mu, reverse=True))
            out[key] = out.get(key, Fraction(0)) + a * b
    return out


def star_pair_with_ht(f, ht, q0, t0):
    """<f, Ht_mu>_* given f and Ht_mu both in the power-sum basis."""
    s = Fraction(0)
    for rho, coeff in f.items():
        hv = ht.get(rho)
        if hv is not None:
            s += coeff * hv * star_norm(rho, q0, t0)
    return s


def pi_inverse_nabla_e(c, q0, t0):
    """Pi^{-1}(nabla e_c) in the power-sum basis, as {rho: coeff}."""
    ec = e_power(c)
    out: dict[tuple[int, ...], Fraction] = {}
    for mu in partitions(c):
        ht = ht_numeric(mu, q0, t0)
        coef = (
            T_num(mu, q0, t0)
            * star_pair_with_ht(ec, ht, q0, t0)
            / (w_num(mu, q0, t0) * Pi_num(mu, q0, t0))
        )
        for rho, hv in ht.items():
            out[rho] = out.get(rho, Fraction(0)) + coef * hv
    return out


def F_at(n, k, l, q0, t0):
    """F_{n,k,l}(q0, t0) evaluated exactly at a sample point."""
    c = n - k - l
    if c < 1:
        raise ValueError("require n - k - l >= 1")
    f2 = pi_inverse_nabla_e(c, q0, t0)
    Q = pmult(pmult(e_star_num(k, q0, t0), e_star_num(l, q0, t0)), f2)
    key1n = tuple([1] * n)
    total = Fraction(0)
    for mu in partitions(n):
        ht = ht_numeric(mu, q0, t0)
        si = star_pair_with_ht(Q, ht, q0, t0)
        total += Pi_num(mu, q0, t0) * si * ht.get(key1n, Fraction(0)) / w_num(mu, q0, t0)
    return factorial(n) * total


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


def F_poly(n: int, k: int, l: int, degbound: int | None = None) -> dict[tuple[int, int], int]:
    """Return {(i, j): coeff} of q^i t^j in F_{n,k,l}(q, t).

    ``degbound`` bounds the degree in each variable; the true bidegree is the
    maximal ``area`` over ``LD(n)^{*k, •l}``. When omitted, the safe upper bound
    ``n(n-1)/2`` (the maximal Dyck-path area) is used.
    """
    if degbound is None:
        degbound = max(1, n * (n - 1) // 2)
    D = degbound
    primes = _primes(2 * (D + 1))
    qgrid = [Fraction(p) for p in primes[: D + 1]]
    tgrid = [Fraction(p) for p in primes[D + 1: 2 * (D + 1)]]
    values = [[F_at(n, k, l, qgrid[a], tgrid[b]) for b in range(D + 1)] for a in range(D + 1)]
    coeffs_t = [_lagrange(tgrid, values[a]) for a in range(D + 1)]
    result: dict[tuple[int, int], int] = {}
    for j in range(D + 1):
        cq = _lagrange(qgrid, [coeffs_t[a][j] for a in range(D + 1)])
        for i in range(D + 1):
            c = cq[i]
            if c != 0:
                if c.denominator != 1:
                    raise ValueError(f"non-integer coefficient {c} at (q^{i}, t^{j}) of F_{n},{k},{l}")
                result[(i, j)] = int(c)
    return result
