"""Permutations with no double descent and no final descent, for the q-Eulerian task.

Carlitz's ``q``-Eulerian polynomial ``A_n(t,q) = sum_{sigma in S_n} t^{des sigma}
q^{maj sigma}`` expands, by a theorem of Han, Jouhet and Zeng, in the basis
``t^{k-1} (-t q^k; q)_{n+1-2k}`` with coefficients ``a_{n,k}(q)`` in ``N[q]``. At
``q = 1`` these are the classical Eulerian ``gamma``-coefficients, and those are
counted by

    Gamma_{n,k} = { sigma in S_n : des(sigma) = k - 1, sigma has no double descent
                                   and no final descent },

the Foata--Schuetzenberger set. The discovery task is a statistic on ``Gamma_{n,k}``
whose generating function is ``a_{n,k}(q)``.

An object of this family is one such permutation; the fiber it is graded in is
``(n, k) = (sigma.n, sigma.descents + 1)``, read off the object. The canonical
encoding is one-line notation, the comma-separated values ``sigma(1), ..., sigma(n)``,
so ::

    2,1,4,3,5

is ``sigma = 21435`` in ``Gamma_{5,3}``: descents at ``1`` and ``3``, no two of them
adjacent and none of them final.

Equivalently the descent set of an object is a subset of ``{1, ..., n - 2}`` with no
two consecutive elements, which is why ``k - 1`` never exceeds ``floor((n - 1) / 2)``.

No statistic on this family is public. The classical Mahonian statistics are exposed
because they are the natural first guesses, not because they are graded variables of
the target.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Iterator

GammaPermutationWord = str


def _parse(encoding: str) -> tuple[int, ...]:
    return tuple(int(piece) for piece in encoding.split(","))


def _encode(values) -> str:
    return ",".join(str(value) for value in values)


def is_gamma_permutation(encoding: str) -> bool:
    """Whether ``encoding`` is a permutation with no double descent and no final descent."""
    if not isinstance(encoding, str) or not encoding:
        return False
    try:
        values = _parse(encoding)
    except ValueError:
        return False
    n = len(values)
    if sorted(values) != list(range(1, n + 1)):
        return False
    if n > 1 and values[n - 2] > values[n - 1]:
        return False
    return not any(
        values[i - 1] > values[i] > values[i + 1] for i in range(1, n - 1)
    )


@dataclass(frozen=True, init=False)
class GammaPermutation:
    """A permutation of ``[n]`` with no double descent and no final descent.

    Encoded in one-line notation. Public benchmark code exposes the word, its
    descent set, and the classical Mahonian statistics; the graded statistic of the
    target belongs to the discovery task.
    """

    encoding: str
    values: tuple[int, ...]
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_gamma_permutation(encoding):
            raise ValueError(f"not a permutation without double or final descents: {encoding!r}")
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "values", _parse(encoding))
        object.__setattr__(self, "n", len(self.values))

    @property
    def size(self) -> int:
        """Number of letters, ``n``."""
        return self.n

    def __call__(self, i: int) -> int:
        """The image ``sigma(i)``, with ``i`` 1-based."""
        return self.values[i - 1]

    @cached_property
    def descent_set(self) -> tuple[int, ...]:
        """``{ i : sigma(i) > sigma(i + 1) }``, increasing. No two are consecutive."""
        return tuple(
            i for i in range(1, self.n) if self.values[i - 1] > self.values[i]
        )

    @cached_property
    def descents(self) -> int:
        """``des(sigma) = k - 1``: the fiber index, one less than ``k``."""
        return len(self.descent_set)

    def maj(self) -> int:
        """The major index ``sum_{i in Des(sigma)} i``."""
        return sum(self.descent_set)

    def comaj(self) -> int:
        """The comajor index ``sum_{i in Des(sigma)} (n - i)``."""
        return sum(self.n - i for i in self.descent_set)

    def inv(self) -> int:
        """The inversion number ``#{ i < j : sigma(i) > sigma(j) }``.

        Counted in ``O(n log n)`` with a Fenwick tree, since the resource probes
        reach ``n = 1024`` and the quadratic count does not fit their budget.
        """
        tree = [0] * (self.n + 1)
        total = 0
        for placed, value in enumerate(self.values):
            index = value
            seen = 0
            while index > 0:
                seen += tree[index]
                index -= index & -index
            total += placed - seen
            index = value
            while index <= self.n:
                tree[index] += 1
                index += index & -index
        return total

    def to_jsonable(self) -> str:
        return self.encoding


def gamma_permutation(values, *, validate: bool = True) -> GammaPermutation:
    """Build the object from its sequence of values ``sigma(1), ..., sigma(n)``."""
    return GammaPermutation(_encode(values), validate=validate)


def gamma_permutation_size(encoding_or_object) -> int:
    """Size ``n`` (module-level, for the value and resource gates)."""
    if isinstance(encoding_or_object, GammaPermutation):
        return encoding_or_object.n
    return len(encoding_or_object.split(","))


# ---------------------------------------------------------------------------
# Enumeration
# ---------------------------------------------------------------------------


def _iter_words(n: int, descents: int | None) -> Iterator[tuple[int, ...]]:
    """Words of ``[n]`` with no double descent, no final descent, ``descents`` descents.

    Grown one letter at a time: a double descent is rejected as soon as its third
    letter is placed, so the search never enters a branch it would have to discard.
    """
    word: list[int] = []
    used = [False] * (n + 2)

    def rec(position: int, falls: int) -> Iterator[tuple[int, ...]]:
        if descents is not None and falls > descents:
            return
        if position == n:
            if n > 1 and word[n - 2] > word[n - 1]:
                return
            if descents is None or falls == descents:
                yield tuple(word)
            return
        for value in range(1, n + 1):
            if used[value]:
                continue
            if position >= 2 and word[position - 2] > word[position - 1] > value:
                continue  # double descent
            used[value] = True
            word.append(value)
            yield from rec(
                position + 1,
                falls + (1 if position and word[position - 1] > value else 0),
            )
            word.pop()
            used[value] = False

    yield from rec(0, 0)


def iter_gamma_permutations_for_descents(n: int, k: int) -> Iterator[GammaPermutation]:
    """Yield every element of ``Gamma_{n,k}``: ``k - 1`` descents, none double or final."""
    if n < 1:
        raise ValueError("size must be positive")
    if not 1 <= k <= (n + 1) // 2:
        raise ValueError(f"Gamma_{{{n},{k}}} is empty: need 1 <= k <= floor((n + 1) / 2)")
    for word in _iter_words(n, k - 1):
        yield GammaPermutation(_encode(word), validate=False)


def iter_gamma_permutations(n: int) -> Iterator[GammaPermutation]:
    """Yield every size-``n`` object, fiber by fiber in increasing ``k``."""
    if n < 1:
        raise ValueError("size must be positive")
    for k in range(1, (n + 1) // 2 + 1):
        yield from iter_gamma_permutations_for_descents(n, k)


def gamma_permutation_from_descent_set(n: int, descent_set) -> GammaPermutation:
    """The element of ``Gamma_n`` with the given descent set, built in ``O(n)``.

    An admissible descent set is a subset of ``{1, ..., n - 2}`` with no two
    consecutive elements -- exactly the condition "no double descent, no final
    descent". The word fills the runs it cuts out with the highest values first, so
    every run is increasing and every run boundary is a descent, which realizes the
    set exactly.
    """
    if n < 1:
        raise ValueError("size must be positive")
    descent_set = tuple(sorted(descent_set))
    if any(not 1 <= descent <= n - 2 for descent in descent_set) or any(
        second - first < 2 for first, second in zip(descent_set, descent_set[1:])
    ):
        raise ValueError(
            f"not an admissible descent set for n={n}: {descent_set!r}"
        )
    values: list[int] = []
    top = n
    previous = 0
    for boundary in (*descent_set, n):
        length = boundary - previous
        values.extend(range(top - length + 1, top + 1))
        top -= length
        previous = boundary
    return GammaPermutation(_encode(values), validate=False)


def canonical_gamma_permutation(n: int, k: int, *, late: bool = False) -> GammaPermutation:
    """A single element of ``Gamma_{n,k}`` built without enumerating the fiber.

    The descent set is packed at the front (``{1, 3, 5, ...}``) or, with ``late``, at
    the back, so the two are extreme elements of the fiber; both cost ``O(n)``.
    """
    if not 1 <= k <= (n + 1) // 2:
        raise ValueError(f"Gamma_{{{n},{k}}} is empty: need 1 <= k <= floor((n + 1) / 2)")
    if late:
        descent_set = [n - 2 * step for step in range(1, k)]
    else:
        descent_set = [2 * step - 1 for step in range(1, k)]
    return gamma_permutation_from_descent_set(n, descent_set)
