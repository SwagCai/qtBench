"""Public oracle: the target polynomials G_{m,n,k}(q,t) of problem 11.

This public oracle is used only to
regenerate the public polynomial targets; the scored evaluator never loads it.

For all ``m, n >= 1`` and ``k >= 1`` it computes the "Hilbert series"

    G_{m,n,k}(q, t) = < ([m+k]_q / [d]_q) Theta_{e_k} p_{m,n} , h_{1^{n+k}} >,
    d = gcd(m, n),

of the rectangular Delta symmetric function of Iraci, Pagaria, Paolini and Vanden
Wyngaerd (arXiv:2206.00131), whose ``q = 1`` specialisation is conjectured there
to equal the ``area`` enumerator of the standardly labelled rise-decorated
rectangular paths ``LRP(m+k, n+k)^{*k}``.

**Convention.** The source paper reads ``area`` off the exponent of ``t``; qtBench
publishes the known statistic as the exponent of ``q``. ``G_poly`` therefore
returns the *transposed* polynomial ``{(area_exponent, partner_exponent)}``.

Method (all exact, stdlib only). Symmetric functions are held in the power-sum
basis, numerically at a sample point ``(q0, t0)`` with ``Fraction`` arithmetic.
The elliptic Hall operators of Bergeron-Garsia-Sergel-Xin are built from

    Q_{1,0} = D_0 = id - M Delta_{e_1},     Q_{0,1} = -(multiplication by e_1),
    Q_{m,n} = (Q_{c,d} Q_{a,b} - Q_{a,b} Q_{c,d}) / M,

with ``a + c = m``, ``b + d = n`` and ``an - bm = gcd(m, n)``; each ``Q_{m,n}``
is cached as a matrix per input degree. For ``m = ad``, ``n = bd`` and
``gcd(a,b)=1``, Definition 2.6 of the source constructs
``p_{m,n} = F_{a,b}(p_d)`` by expanding ``p_d`` in its prescribed transformed
homogeneous basis and replacing each basis element by a product of
``Q_{lambda_i a,lambda_i b}(1)``. Finally
``Theta_{e_k} F = Pi(e_k[X/M] Pi^{-1} F)`` and
``<P, h_{1^N}> = N! [p_{1^N}] P``, with ``Pi`` and ``Delta_{e_1}`` diagonal on the
modified Macdonald basis ``Ht_mu`` obtained from the Garsia-Haiman-Tesler
two-plethystic triangularity.

The result is bivariately interpolated and then verified at fresh sample points,
which rules out an interpolation degree bound that is too small.
"""
from __future__ import annotations

from collections import Counter
from fractions import Fraction
from functools import lru_cache
from math import factorial, gcd

PROBLEM_ID = 11
PROBLEM_NAME = "lrp_area_qt_rectangular_delta_second_stat"


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
# The lattice split (a, b) + (c, d) of Bergeron-Garsia-Sergel-Xin
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def split(m: int, n: int) -> tuple[int, int, int, int]:
    """``(a, b, c, d)`` with ``a+c = m``, ``b+d = n`` and ``an - bm = gcd(m, n)``.

    The smallest ``a + b`` selects one admissible split deterministically when
    more than one is available.
    """
    g = gcd(m, n)
    best = None
    for a in range(m + 1):
        for b in range(n + 1):
            if a * n - b * m == g:
                if best is None or (a + b) < (best[0] + best[1]):
                    best = (a, b)
    if best is None:
        raise ValueError(f"no admissible split for ({m}, {n})")
    a, b = best
    return a, b, m - a, n - b


# ---------------------------------------------------------------------------
# One evaluation point: Macdonald data and the elliptic Hall operators
# ---------------------------------------------------------------------------

class Point:
    """Symmetric function calculus at a fixed numeric ``(q0, t0)``."""

    def __init__(self, q0: Fraction, t0: Fraction) -> None:
        self.q = q0
        self.t = t0
        self.M = (1 - q0) * (1 - t0)
        self._ht: dict[tuple[int, ...], dict] = {}
        self._q_matrix: dict[tuple[int, int, int], dict] = {}

    # -- Macdonald constants -------------------------------------------------

    def ht(self, mu):
        cached = self._ht.get(mu)
        if cached is not None:
            return cached
        n = sum(mu)
        parts = partitions(n)
        muprime = conjugate(mu)

        def pleth(rho, base):
            v = Fraction(1)
            for part in rho:
                v *= (1 - base ** part)
            return v

        rows = []
        rhs = []
        for lam in parts:
            if not dominates(lam, mu):
                rows.append([pleth(rho, self.q) * character(lam, rho) for rho in parts])
                rhs.append(Fraction(0))
        for lam in parts:
            if not dominates(lam, muprime):
                rows.append([pleth(rho, self.t) * character(lam, rho) for rho in parts])
                rhs.append(Fraction(0))
        rows.append([Fraction(character(tuple([n]), rho)) for rho in parts])
        rhs.append(Fraction(1))
        sol = solve_unique(rows, rhs, len(parts))
        value = {parts[i]: sol[i] for i in range(len(parts))}
        self._ht[mu] = value
        return value

    def Pi(self, mu):
        v = Fraction(1)
        for (i, j) in cells(mu):
            if (i, j) != (0, 0):
                v *= (1 - self.q ** i * self.t ** j)
        return v

    def B(self, mu):
        return sum((self.q ** i * self.t ** j for (i, j) in cells(mu)), Fraction(0))

    def w(self, mu):
        v = Fraction(1)
        for c in cells(mu):
            a = arm(mu, c)
            l = leg(mu, c)
            v *= (self.q ** a - self.t ** (l + 1)) * (self.t ** l - self.q ** (a + 1))
        return v

    def star_norm(self, rho):
        v = Fraction(z_lambda(rho) * eps_lambda(rho))
        for part in rho:
            v *= (1 - self.q ** part) * (1 - self.t ** part)
        return v

    # -- power-sum linear algebra -------------------------------------------

    def ht_coefficients(self, f, deg):
        """``<f, Ht_mu>_* / w_mu`` for every ``mu`` of size ``deg``."""
        out = {}
        for mu in partitions(deg):
            ht = self.ht(mu)
            s = Fraction(0)
            for rho, coeff in f.items():
                value = ht.get(rho)
                if value is not None:
                    s += coeff * value * self.star_norm(rho)
            out[mu] = s / self.w(mu)
        return out

    def from_ht(self, coefficients):
        out: dict[tuple[int, ...], Fraction] = {}
        for mu, coeff in coefficients.items():
            if not coeff:
                continue
            for rho, value in self.ht(mu).items():
                out[rho] = out.get(rho, Fraction(0)) + coeff * value
        return out

    def scale_ht(self, f, deg, weight):
        """Apply the operator diagonal on ``Ht_mu`` with eigenvalue ``weight(mu)``."""
        coefficients = self.ht_coefficients(f, deg)
        return self.from_ht({mu: coeff * weight(mu) for mu, coeff in coefficients.items()})

    def e_star(self, k):
        """``e_k[X/M]`` in the power-sum basis."""
        out = {}
        for lam in partitions(k):
            denom = Fraction(1)
            for part in lam:
                denom *= (1 - self.q ** part) * (1 - self.t ** part)
            out[lam] = Fraction(eps_lambda(lam), z_lambda(lam)) / denom
        return out

    # -- elliptic Hall operators --------------------------------------------

    def q_matrix(self, m, n, deg):
        key = (m, n, deg)
        cached = self._q_matrix.get(key)
        if cached is not None:
            return cached
        matrix = {rho: self._apply_raw(m, n, {rho: Fraction(1)}, deg) for rho in partitions(deg)}
        self._q_matrix[key] = matrix
        return matrix

    def apply_Q(self, m, n, f, deg):
        matrix = self.q_matrix(m, n, deg)
        out: dict[tuple[int, ...], Fraction] = {}
        for rho, coeff in f.items():
            if not coeff:
                continue
            for sigma, value in matrix[rho].items():
                out[sigma] = out.get(sigma, Fraction(0)) + coeff * value
        return out

    def _apply_raw(self, m, n, f, deg):
        if (m, n) == (1, 0):  # D_0 = id - M Delta_{e_1}
            shifted = self.scale_ht(f, deg, self.B)
            out = dict(f)
            for rho, value in shifted.items():
                out[rho] = out.get(rho, Fraction(0)) - self.M * value
            return out
        if (m, n) == (0, 1):  # -(multiplication by e_1 = p_1)
            out = {}
            for rho, coeff in f.items():
                key = tuple(sorted((*rho, 1), reverse=True))
                out[key] = out.get(key, Fraction(0)) - coeff
            return out
        a, b, c, d = split(m, n)
        left = self.apply_Q(c, d, self.apply_Q(a, b, f, deg), deg + b)
        right = self.apply_Q(a, b, self.apply_Q(c, d, f, deg), deg + d)
        out = {}
        for rho in set(left) | set(right):
            value = (left.get(rho, Fraction(0)) - right.get(rho, Fraction(0))) / self.M
            if value:
                out[rho] = value
        return out

    def Q_one(self, m, n):
        """``Q_{m,n}(1)``, an element of ``Lambda^{(n)}``."""
        return self.apply_Q(m, n, {(): Fraction(1)}, 0)


def pmult(f, g):
    out = {}
    for lam, a in f.items():
        for mu, b in g.items():
            key = tuple(sorted(lam + mu, reverse=True))
            out[key] = out.get(key, Fraction(0)) + a * b
    return out


def _scaled_h(r: int, u: Fraction) -> dict[tuple[int, ...], Fraction]:
    """``h_r[(1-u)X/u]`` in the power-sum basis."""
    out = {}
    for rho in partitions(r):
        coeff = Fraction(1, z_lambda(rho))
        for part in rho:
            coeff *= (1 - u ** part) / u ** part
        out[rho] = coeff
    return out


@lru_cache(maxsize=None)
def _p_basis_coefficients(d: int, u: Fraction) -> dict[tuple[int, ...], Fraction]:
    """Coefficients prescribed in Definition 2.6 for ``f = p_d``."""
    parts = partitions(d)
    basis = {}
    for lam in parts:
        value = {(): Fraction(1)}
        for part in lam:
            value = pmult(value, _scaled_h(part, u))
        scale = (u / (u - 1)) ** len(lam)
        basis[lam] = {rho: scale * coeff for rho, coeff in value.items()}
    rows = [[basis[lam].get(rho, Fraction(0)) for lam in parts] for rho in parts]
    rhs = [Fraction(1 if rho == (d,) else 0) for rho in parts]
    coefficients = solve_unique(rows, rhs, len(parts))
    return {lam: coefficients[index] for index, lam in enumerate(parts)}


def p_mn(point: Point, m: int, n: int) -> dict:
    """The general elliptic-Hall symmetric function ``p_{m,n}``."""
    d = gcd(m, n)
    a, b = m // d, n // d
    out: dict[tuple[int, ...], Fraction] = {}
    for lam, coefficient in _p_basis_coefficients(d, point.q * point.t).items():
        term = {(): Fraction(1)}
        degree = 0
        for part in lam:
            term = point.apply_Q(part * a, part * b, term, degree)
            degree += part * b
        # Normalize the operator convention so that d=1 reduces to the
        # already-validated p_{m,n}=Q_{m,n}((-1)^n) formula.
        scale = coefficient * (-1) ** (n + 1)
        for rho, value in term.items():
            out[rho] = out.get(rho, Fraction(0)) + scale * value
    return {rho: value for rho, value in out.items() if value}


def e_mn(point: Point, m: int, n: int) -> dict:
    """``e_{m,n} = p_{m,n} = Q_{m,n}((-1)^n)`` for coprime ``(m, n)``.

    ``Q_{0,1} = -e_1`` contributes one sign per unit of degree, and the rational
    shuffle theorem is stated for the operator applied to the constant
    ``(-1)^n``. When ``gcd(m, n) = 1`` the general ``F_{a,b}`` construction
    collapses to this single term, and ``e_{m,n}`` and ``p_{m,n}`` coincide.
    The published targets use ``p_mn``, which is defined for all ``(m, n)``.
    """
    if gcd(m, n) != 1:
        raise ValueError(f"e_{{{m},{n}}} is only defined for coprime sides; use p_mn")
    sign = (-1) ** n
    return {rho: sign * value for rho, value in point.Q_one(m, n).items()}


def theta(point: Point, k: int, f, deg):
    """``Theta_{e_k} f = Pi( e_k[X/M] Pi^{-1} f )`` for ``f`` of degree ``deg``."""
    if k == 0:
        return f
    inverse = point.scale_ht(f, deg, lambda mu: 1 / point.Pi(mu))
    product = pmult(point.e_star(k), inverse)
    return point.scale_ht(product, deg + k, point.Pi)


def _q_integer(point: Point, j: int) -> Fraction:
    return (1 - point.q ** j) / (1 - point.q)


def dyck_G_at(m: int, n: int, k: int, q0: Fraction, t0: Fraction) -> Fraction:
    """``<Theta_{e_k} e_{m,n}, h_{1^{n+k}}>``: the rectangular Dyck path companion."""
    point = Point(q0, t0)
    target = theta(point, k, e_mn(point, m, n), n)
    N = n + k
    return factorial(N) * target.get(tuple([1] * N), Fraction(0))


def G_at(m: int, n: int, k: int, q0: Fraction, t0: Fraction) -> Fraction:
    """``G_{m,n,k}(q0, t0)`` in the source paper's variables, evaluated exactly."""
    point = Point(q0, t0)
    target = theta(point, k, p_mn(point, m, n), n)
    N = n + k
    hilbert = factorial(N) * target.get(tuple([1] * N), Fraction(0))
    return _q_integer(point, m + k) * hilbert / _q_integer(point, gcd(m, n))


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
            for dd, c in enumerate(num):
                new[dd] += c * (-xs[j])
                new[dd + 1] += c
            num = new
            denom *= (xs[i] - xs[j])
        scale = ys[i] / denom
        for dd in range(len(num)):
            coeffs[dd] += num[dd] * scale
    return coeffs


def _interpolate(evaluate, degbound: int) -> dict[tuple[int, int], int]:
    D = degbound
    primes = _primes(2 * (D + 1) + 2)
    qgrid = [Fraction(p) for p in primes[: D + 1]]
    tgrid = [Fraction(p) for p in primes[D + 1: 2 * (D + 1)]]
    values = [[evaluate(qgrid[a], tgrid[b]) for b in range(D + 1)] for a in range(D + 1)]
    coeffs_t = [_lagrange(tgrid, values[a]) for a in range(D + 1)]
    result: dict[tuple[int, int], int] = {}
    for j in range(D + 1):
        cq = _lagrange(qgrid, [coeffs_t[a][j] for a in range(D + 1)])
        for i in range(D + 1):
            c = cq[i]
            if c != 0:
                if c.denominator != 1:
                    raise ValueError(f"non-integer coefficient {c} at (q^{i}, t^{j})")
                result[(i, j)] = int(c)
    # verify at fresh sample points: an interpolation degree bound that is too
    # small aliases, and the aliased polynomial disagrees off the grid
    extra = primes[2 * (D + 1):]
    for q0, t0 in ((Fraction(extra[0]), Fraction(extra[1])), (Fraction(extra[1]), Fraction(extra[0]))):
        direct = evaluate(q0, t0)
        recovered = sum(
            (Fraction(c) * q0 ** i * t0 ** j for (i, j), c in result.items()), Fraction(0)
        )
        if direct != recovered:
            raise ValueError(f"interpolation failed at (q,t)=({q0},{t0}); raise the degree bound")
    return result


def G_poly(m: int, n: int, k: int, degbound: int | None = None) -> dict[tuple[int, int], int]:
    """Return ``{(area_exponent, partner_exponent): coeff}`` of the qtBench target.

    The source paper's polynomial is ``sum G_{i,j} q^i t^j`` with ``j`` the
    ``area``; the returned dictionary is its transpose, so the first exponent is
    the public ``area`` statistic.
    """
    if degbound is None:
        degbound = max(2, (m + k) * (n + k))
    raw = _interpolate(lambda q0, t0: G_at(m, n, k, q0, t0), degbound)
    return {(j, i): c for (i, j), c in raw.items()}


def dyck_G_poly(m: int, n: int, k: int, degbound: int | None = None) -> dict[tuple[int, int], int]:
    """The same transposed target for the rectangular *Dyck* path companion."""
    if degbound is None:
        degbound = max(2, (m + k) * (n + k))
    raw = _interpolate(lambda q0, t0: dyck_G_at(m, n, k, q0, t0), degbound)
    return {(j, i): c for (i, j), c in raw.items()}
