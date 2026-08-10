"""Reference implementations of the two public statistics, chain and dinv.

An object is a pair ``(f, alpha)`` encoded as ``f + "|" + alpha``: ``f`` lists the
values of a parking function of length ``n`` and ``alpha`` the ``a``-vector of a
Dyck path with ``alpha <= beta(f)`` in the Tamari order, where ``beta(f)`` is the
weakly increasing rearrangement of ``f``.

- ``chain`` is ``d(alpha, beta(f))``, the length of the longest Tamari chain from
  ``alpha`` up to the shape. The Tamari lattice is not graded, so this is a
  genuine longest-path computation; the two extremes are closed forms
  (``0`` at the shape, ``area(beta) = binom(n,2) - sum b_i`` at the Tamari
  minimum ``(0, 1, ..., n-1)``).
- ``dinv`` is the parking function inversion statistic: with ``(a_i, b_i)`` the
  lexicographic rearrangement of ``(i, f_i)`` ordered first by value and
  ``c_i = i - b_i``, it counts the pairs ``i < j`` with ``c_i = c_j`` and
  ``a_i < a_j``, or ``c_i - c_j = 1`` and ``a_i > a_j``.

Both statistics are public; the task is to discover the third one. The same
values are exposed as ``pair.chain()`` and ``pair.dinv()`` on the object passed to
a submission.
"""
from __future__ import annotations


def _encoding(pair) -> str:
    if hasattr(pair, "encoding"):
        return pair.encoding
    return pair


def _parse(pair):
    parking_text, alpha_text = _encoding(pair).split("|")
    f = tuple(int(piece) for piece in parking_text.split(","))
    alpha = tuple(int(piece) for piece in alpha_text.split(","))
    return f, alpha


def _primitive_end(alpha, i: int) -> int:
    n = len(alpha)
    k = i
    while k < n and alpha[k] - alpha[i - 1] < (k + 1) - i:
        k += 1
    return k


def _up_covers(alpha):
    out = []
    for i in range(2, len(alpha) + 1):
        if alpha[i - 2] < alpha[i - 1]:
            k = _primitive_end(alpha, i)
            out.append(
                tuple(
                    value - 1 if i <= j <= k else value
                    for j, value in enumerate(alpha, start=1)
                )
            )
    return out


def chain(pair) -> int:
    f, alpha = _parse(pair)
    beta = tuple(sorted(f))
    n = len(f)
    if alpha == beta:
        return 0
    if alpha == tuple(range(n)):
        return n * (n - 1) // 2 - sum(beta)

    memo: dict[tuple[int, ...], int | None] = {}

    def longest(current):
        if current == beta:
            return 0
        if current in memo:
            return memo[current]
        memo[current] = None
        best = None
        for cover in _up_covers(current):
            if any(c < b for c, b in zip(cover, beta)):
                continue
            below = longest(cover)
            if below is not None and (best is None or below + 1 > best):
                best = below + 1
        memo[current] = best
        return best

    value = longest(alpha)
    if value is None:
        raise ValueError(f"alpha is not below beta(f) for {_encoding(pair)!r}")
    return value


def dinv(pair) -> int:
    f, _alpha = _parse(pair)
    pairs = sorted((value, position) for position, value in enumerate(f, start=1))
    a = [position for _value, position in pairs]
    c = [i - value for i, (value, _position) in enumerate(pairs, start=1)]
    n = len(f)
    return sum(
        1
        for i in range(n)
        for j in range(i + 1, n)
        if (c[i] == c[j] and a[i] < a[j]) or (c[i] - c[j] == 1 and a[i] > a[j])
    )
