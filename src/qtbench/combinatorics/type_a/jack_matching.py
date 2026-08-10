"""Matchings paired with a reference partition, for the Matchings-Jack task.

Let ``N_n = {1, ..., n} u {1h, ..., nh}`` and let ``F_n`` be the set of perfect
matchings of ``N_n``. For matchings ``d_1, d_2`` the multigraph ``G(d_1, d_2)`` is a
disjoint union of even cycles whose edges alternate between the two matchings, and
``Lambda(d_1, d_2)`` is the partition of ``n`` recording *half* the length of each
cycle. Two matchings are distinguished:

    eps       = { {1, 1h}, ..., {n, nh} },
    delta_lam = { {1, 2h}, {2, 3h}, ..., {lam_1, 1h}, {lam_1 + 1, lam_1 + 2h}, ... },

the second built by closing up one cycle per part of ``lam``, so that both are
bipartite and ``Lambda(eps, delta_lam) = lam``. Goulden and Jackson's family is

    G^lam_{pi,sigma} = { d in F_n : Lambda(d, eps) = pi, Lambda(d, delta_lam) = sigma },

and the Matchings-Jack conjecture asks for a statistic on it whose generating
function is the Jack connection coefficient ``c^lam_{pi,sigma}(beta)``.

An object of this family is therefore a pair ``(lam, d)``: the matching together
with the partition that selects the reference matching ``delta_lam``. The fiber it
is graded in, ``(pi, sigma)``, is read off the object. Elements of ``N_n`` are
numbered ``1, ..., n`` for the unhatted class and ``n + 1, ..., 2n`` for the hatted
one, so a matching is a fixed-point-free involution of ``[2n]`` and the canonical
encoding is ``lam + "|" + images``, the parts of ``lam`` followed by the one-line
notation of that involution. For example ::

    2|3,4,1,2

is ``lam = (2)`` paired with ``eps = {{1, 1h}, {2, 2h}}`` in ``F_2``.

No statistic on this family is public. Bipartiteness is exposed because the
conjecture pins the statistic to zero exactly on the bipartite matchings.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Iterator

from .kostka_tableau import is_partition, iter_partitions

SEPARATOR = "|"

JackMatchingWord = str


def _parse(encoding: str):
    lam_text, images_text = encoding.split(SEPARATOR)
    lam = tuple(int(piece) for piece in lam_text.split(","))
    images = tuple(int(piece) for piece in images_text.split(","))
    return lam, images


def _encode(lam, images) -> str:
    head = ",".join(str(part) for part in lam)
    body = ",".join(str(value) for value in images)
    return f"{head}{SEPARATOR}{body}"


def is_jack_matching(encoding: str) -> bool:
    """Whether ``encoding`` is a valid ``lam|images`` pair of a partition and a matching."""
    if not isinstance(encoding, str) or encoding.count(SEPARATOR) != 1:
        return False
    try:
        lam, images = _parse(encoding)
    except ValueError:
        return False
    if not is_partition(lam) or len(images) != 2 * sum(lam):
        return False
    letters = 2 * sum(lam)
    if sorted(images) != list(range(1, letters + 1)):
        return False
    return all(
        images[images[i - 1] - 1] == i and images[i - 1] != i
        for i in range(1, letters + 1)
    )


def matching_cycle_type(first, second, n: int) -> tuple[int, ...]:
    """``Lambda`` of two matchings of ``[2n]``, given in one-line notation.

    Walks each alternating cycle once, taking one step along each matching per
    turn, so the number of turns is half the cycle length.
    """
    seen = [False] * (2 * n + 1)
    lengths: list[int] = []
    for start in range(1, 2 * n + 1):
        if seen[start]:
            continue
        length = 0
        node = start
        while not seen[node]:
            seen[node] = True
            node = first[node - 1]
            seen[node] = True
            node = second[node - 1]
            length += 1
        lengths.append(length)
    return tuple(sorted(lengths, reverse=True))


def epsilon_images(n: int) -> tuple[int, ...]:
    """``eps = {{i, ih}}``, in one-line notation on ``[2n]``."""
    return tuple(i + n if i <= n else i - n for i in range(1, 2 * n + 1))


def reference_images(lam: tuple[int, ...]) -> tuple[int, ...]:
    """``delta_lam``, in one-line notation on ``[2n]``: one cycle per part of ``lam``."""
    n = sum(lam)
    images = [0] * (2 * n)
    start = 1
    for part in lam:
        for index in range(part):
            i = start + index
            j = start + (index + 1) % part
            images[i - 1] = j + n
            images[j + n - 1] = i
        start += part
    return tuple(images)


@dataclass(frozen=True, init=False)
class JackMatching:
    """A perfect matching of ``N_n`` paired with the partition ``lam`` of ``n``.

    Encoded as ``lam + "|" + images``, with ``images`` the one-line notation of the
    matching read as a fixed-point-free involution of ``[2n]`` (``1..n`` is the
    unhatted class, ``n+1..2n`` the hatted one). Public benchmark code exposes the
    matching, the reference matching ``delta_lam``, bipartiteness, and the two
    cycle types that index the fiber; the graded statistic belongs to the discovery
    task.
    """

    encoding: str
    lam: tuple[int, ...]
    images: tuple[int, ...]
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_jack_matching(encoding):
            raise ValueError(f"not a partition / matching pair: {encoding!r}")
        lam, images = _parse(encoding)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "lam", lam)
        object.__setattr__(self, "images", images)
        object.__setattr__(self, "n", sum(lam))

    @property
    def size(self) -> int:
        """Half the number of letters, ``n``."""
        return self.n

    @cached_property
    def pairs(self) -> tuple[tuple[int, int], ...]:
        """The matching as pairs ``(i, j)`` with ``i < j``, increasing in ``i``."""
        return tuple(
            (i, image)
            for i, image in enumerate(self.images, start=1)
            if image > i
        )

    @cached_property
    def is_bipartite(self) -> bool:
        """Whether every pair joins the two classes of ``N_n``.

        The conjectured statistic vanishes exactly on these matchings.
        """
        return all((i <= self.n) != (j <= self.n) for i, j in self.pairs)

    @cached_property
    def reference(self) -> tuple[int, ...]:
        """``delta_lam`` in one-line notation, the reference matching of ``lam``."""
        return reference_images(self.lam)

    def epsilon_type(self) -> tuple[int, ...]:
        """``pi = Lambda(d, eps)``, the first index of the fiber."""
        return matching_cycle_type(self.images, epsilon_images(self.n), self.n)

    def reference_type(self) -> tuple[int, ...]:
        """``sigma = Lambda(d, delta_lam)``, the second index of the fiber."""
        return matching_cycle_type(self.images, self.reference, self.n)

    def to_jsonable(self) -> str:
        return self.encoding


def jack_matching(lam, images, *, validate: bool = True) -> JackMatching:
    """Build the object ``(lam, d)`` from a partition and a matching in one-line form."""
    return JackMatching(_encode(lam, images), validate=validate)


def jack_matching_size(encoding_or_object) -> int:
    """Size ``n`` (module-level, for the value and resource gates)."""
    if isinstance(encoding_or_object, JackMatching):
        return encoding_or_object.n
    lam_text = encoding_or_object.split(SEPARATOR)[0]
    return sum(int(piece) for piece in lam_text.split(","))


# ---------------------------------------------------------------------------
# Enumeration
# ---------------------------------------------------------------------------


def _iter_matching_images(letters: int) -> Iterator[tuple[int, ...]]:
    """One-line notation of every perfect matching of ``[letters]``."""
    images = [0] * letters

    def rec(free: tuple[int, ...]):
        if not free:
            yield tuple(images)
            return
        first, rest = free[0], free[1:]
        for index, partner in enumerate(rest):
            images[first - 1] = partner
            images[partner - 1] = first
            yield from rec(rest[:index] + rest[index + 1:])
        images[first - 1] = 0

    yield from rec(tuple(range(1, letters + 1)))


def iter_jack_matchings_for_partition(lam: tuple[int, ...]) -> Iterator[JackMatching]:
    """Yield ``(lam, d)`` for every perfect matching ``d`` of ``N_n``, ``n = |lam|``."""
    if not is_partition(lam) or not lam:
        raise ValueError(f"not a partition: {lam!r}")
    for images in _iter_matching_images(2 * sum(lam)):
        yield JackMatching(_encode(lam, images), validate=False)


def iter_jack_matchings(n: int) -> Iterator[JackMatching]:
    """Yield every size-``n`` object: all partitions of ``n``, all matchings of ``N_n``."""
    if n < 1:
        raise ValueError("size must be positive")
    for lam in iter_partitions(n):
        yield from iter_jack_matchings_for_partition(lam)


def jack_matching_count(n: int) -> int:
    """``p(n) (2n - 1)!!``, the number of size-``n`` objects."""
    matchings = 1
    for size in range(1, 2 * n, 2):
        matchings *= size
    return sum(1 for _ in iter_partitions(n)) * matchings


def canonical_jack_matching(
    lam: tuple[int, ...], *, kind: str = "epsilon"
) -> JackMatching:
    """A single valid object built without enumerating the fiber.

    ``kind`` selects the matching: ``"epsilon"`` and ``"reference"`` give the two
    distinguished bipartite matchings ``eps`` and ``delta_lam``, and
    ``"within_class"`` pairs each class with itself as far as possible, which is
    the most non-bipartite matching there is (a single crossing pair survives when
    ``n`` is odd). So the extremes of the conjectured statistic are both cheap to
    probe.
    """
    if not is_partition(lam) or not lam:
        raise ValueError(f"not a partition: {lam!r}")
    n = sum(lam)
    if kind == "epsilon":
        images = epsilon_images(n)
    elif kind == "reference":
        images = reference_images(lam)
    elif kind == "within_class":
        values = list(range(1, 2 * n + 1))
        for offset in (0, n):
            for i in range(1, n - n % 2, 2):
                values[offset + i - 1] = offset + i + 1
                values[offset + i] = offset + i
        if n % 2:
            values[n - 1] = 2 * n
            values[2 * n - 1] = n
        images = tuple(values)
    else:
        raise ValueError(f"unknown canonical matching kind: {kind!r}")
    return JackMatching(_encode(lam, images), validate=False)
