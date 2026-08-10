"""Standardly labelled doubly decorated Dyck paths and their (decorated) area.

Following Iraci, Nadeau and Vanden Wyngaerd (see the problem statement for
references), a *decorated labelled Dyck path* of size ``n`` is a Dyck path from
``(0, 0)`` to ``(n, n)`` (unit North/East steps, weakly above the diagonal
``x = y``) together with

* a positive-integer label on each North (vertical) step, strictly increasing
  along each maximal run of consecutive vertical steps (bottom to top), and
* a choice of ``k`` decorated *rises* and ``l`` decorated *contractible valleys*.

A **rise** is a vertical step preceded by another vertical step; a **valley** is a
vertical step preceded by a horizontal step. A valley (the ``i``-th vertical step,
with ``e`` horizontal steps immediately before it) is **contractible** when
``e >= 2``, or when ``e == 1`` and the label of the ``(i-1)``-th vertical step is
strictly smaller than the label of the ``i``-th. ``LD(n)^{*k, •l}`` is the set of
size-``n`` decorated labelled Dyck paths with ``k`` decorated rises and ``l``
decorated valleys.

A **standard labelling** uses each of ``1, ..., n`` exactly once; the standardly
labelled objects are the ones selected by the Hilbert-series pairing
``<Theta_{e_k} Theta_{e_l} nabla e_{n-k-l}, e_{1^n}>``.

The public statistic is the (decorated) ``area``: with area word ``a`` (``a_i`` is
the number of whole cells in row ``i`` between the path and the diagonal),

    area(D) = sum of a_i over vertical steps i that are NOT decorated rises.

The joint distribution of ``area`` and the unknown partner is that Hilbert
series; ``area`` is public and the ``t``-partner is the object of the discovery
task.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cache, cached_property
from itertools import combinations
from typing import Iterator

from .dyck import enumerate_dyck_paths, is_dyck_path

SEPARATOR = "|"

DecoratedDyckWord = str


def _area_word(path: str) -> tuple[int, ...]:
    """Area word ``a`` of a Dyck path: ``a_i = y - x`` when the i-th N is taken."""
    area = []
    x = y = 0
    for step in path:
        if step == "N":
            area.append(y - x)
            y += 1
        else:
            x += 1
    return tuple(area)


def _east_gaps(path: str) -> tuple[int, ...]:
    """Number of East steps immediately before each North step (in step order)."""
    gaps = []
    run = 0
    for step in path:
        if step == "N":
            gaps.append(run)
            run = 0
        else:
            run += 1
    return tuple(gaps)


def _rises_and_valleys(path: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """1-indexed vertical steps that are rises / valleys (step 1 is neither)."""
    gaps = _east_gaps(path)
    rises = tuple(i for i in range(2, len(gaps) + 1) if gaps[i - 1] == 0)
    valleys = tuple(i for i in range(2, len(gaps) + 1) if gaps[i - 1] > 0)
    return rises, valleys


def _contractible_valleys(path: str, labels: tuple[int, ...]) -> tuple[int, ...]:
    """Valleys that may be decorated, given the labels."""
    gaps = _east_gaps(path)
    out = []
    for i in range(2, len(gaps) + 1):
        e = gaps[i - 1]
        if e >= 2:
            out.append(i)
        elif e == 1 and labels[i - 2] < labels[i - 1]:
            out.append(i)
    return tuple(out)


def _parse(encoding: str):
    upper, label_text, rise_text, valley_text = encoding.split(SEPARATOR)
    labels = tuple(int(piece) for piece in label_text.split(",")) if label_text else ()
    drise = frozenset(int(piece) for piece in rise_text.split(",")) if rise_text else frozenset()
    dvalley = (
        frozenset(int(piece) for piece in valley_text.split(",")) if valley_text else frozenset()
    )
    return upper, labels, drise, dvalley


def is_decorated_labelled_dyck_path(encoding: str) -> bool:
    """Whether ``encoding`` is a valid ``path|labels|drise|dvalley`` object."""
    if not isinstance(encoding, str) or encoding.count(SEPARATOR) != 3:
        return False
    path, label_text, rise_text, valley_text = encoding.split(SEPARATOR)
    if not is_dyck_path(path):
        return False
    n = path.count("N")
    try:
        labels = [int(piece) for piece in label_text.split(",")] if label_text else []
        drise = [int(piece) for piece in rise_text.split(",")] if rise_text else []
        dvalley = [int(piece) for piece in valley_text.split(",")] if valley_text else []
    except ValueError:
        return False
    if sorted(labels) != list(range(1, n + 1)):
        return False
    labels_t = tuple(labels)
    rises, valleys = _rises_and_valleys(path)
    # labels strictly increase along each run of consecutive vertical steps
    if any(labels_t[i - 2] >= labels_t[i - 1] for i in rises):
        return False
    if len(set(drise)) != len(drise) or not set(drise) <= set(rises):
        return False
    contractible = set(_contractible_valleys(path, labels_t))
    if len(set(dvalley)) != len(dvalley) or not set(dvalley) <= contractible:
        return False
    return True


@dataclass(frozen=True, init=False)
class DecoratedLabelledDyckPath:
    """A standardly labelled doubly decorated Dyck path.

    Encoded as ``path + "|" + labels + "|" + drise + "|" + dvalley`` where ``path``
    is the North/East word, ``labels`` lists the label of each vertical step in
    step order (bottom to top), and ``drise``/``dvalley`` are the comma-separated
    1-indexed vertical-step positions of the decorated rises and decorated
    valleys (either may be empty). Public benchmark code exposes only structural
    data and the ``area`` statistic; the unknown ``t``-partner belongs to the
    discovery task.
    """

    encoding: str
    path: str
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_decorated_labelled_dyck_path(encoding):
            raise ValueError(f"not a standardly labelled decorated Dyck path: {encoding!r}")
        path = encoding.split(SEPARATOR)[0]
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "n", path.count("N"))

    @property
    def size(self) -> int:
        """Number of labels / vertical steps, ``n``."""
        return self.n

    @cached_property
    def _parsed(self):
        return _parse(self.encoding)

    @cached_property
    def labels(self) -> tuple[int, ...]:
        """Label of each vertical step in step order (bottom to top)."""
        return self._parsed[1]

    @cached_property
    def area_word(self) -> tuple[int, ...]:
        """Area word ``a``; ``area_word[i-1]`` is the cells in row ``i``."""
        return _area_word(self.path)

    @cached_property
    def rises(self) -> frozenset[int]:
        """1-indexed vertical steps that are rises."""
        return frozenset(_rises_and_valleys(self.path)[0])

    @cached_property
    def valleys(self) -> frozenset[int]:
        """1-indexed vertical steps that are valleys."""
        return frozenset(_rises_and_valleys(self.path)[1])

    @cached_property
    def contractible_valleys(self) -> frozenset[int]:
        """1-indexed valleys that may carry a decoration."""
        return frozenset(_contractible_valleys(self.path, self.labels))

    @cached_property
    def decorated_rises(self) -> frozenset[int]:
        """1-indexed vertical steps carrying a rise decoration (``DRise``)."""
        return self._parsed[2]

    @cached_property
    def decorated_valleys(self) -> frozenset[int]:
        """1-indexed vertical steps carrying a valley decoration (``DValley``)."""
        return self._parsed[3]

    @property
    def k(self) -> int:
        """Number of decorated rises."""
        return len(self.decorated_rises)

    @property
    def l(self) -> int:
        """Number of decorated valleys."""
        return len(self.decorated_valleys)

    def area(self) -> int:
        """Decorated area: the area-word letters off the decorated rises."""
        drise = self.decorated_rises
        area_word = self.area_word
        return sum(a for i, a in enumerate(area_word, start=1) if i not in drise)

    def to_jsonable(self) -> str:
        return self.encoding


def decorated_labelled_dyck_area(encoding: str) -> int:
    """Decorated area of the object given by ``encoding``."""
    return DecoratedLabelledDyckPath(encoding, validate=False).area()


def decorated_dyck_size(encoding_or_object) -> int:
    """Size ``n`` (module-level, for the value/resource gate)."""
    if isinstance(encoding_or_object, DecoratedLabelledDyckPath):
        return encoding_or_object.n
    return encoding_or_object.split(SEPARATOR)[0].count("N")


# ---------------------------------------------------------------------------
# Standard labellings of a fixed shape (linear extensions of the run chains)
# ---------------------------------------------------------------------------


def _vertical_runs(path: str) -> list[list[int]]:
    """Maximal runs of consecutive vertical steps, as lists of 1-indexed steps."""
    rises, _valleys = _rises_and_valleys(path)
    rise_set = set(rises)
    n = path.count("N")
    runs: list[list[int]] = []
    for i in range(1, n + 1):
        if i in rise_set:
            runs[-1].append(i)  # continues the current run
        else:
            runs.append([i])  # starts a new run (valley or the first step)
    return runs


def _iter_standard_labellings(path: str) -> Iterator[tuple[int, ...]]:
    """Yield every labelling (as a step-ordered tuple) increasing along each run."""
    runs = _vertical_runs(path)
    n = path.count("N")
    pointers = [0] * len(runs)
    assigned: dict[int, int] = {}

    def rec(label: int) -> Iterator[tuple[int, ...]]:
        if label > n:
            yield tuple(assigned[i] for i in range(1, n + 1))
            return
        for j, run in enumerate(runs):
            if pointers[j] < len(run):
                position = run[pointers[j]]
                assigned[position] = label
                pointers[j] += 1
                yield from rec(label + 1)
                pointers[j] -= 1
                del assigned[position]

    yield from rec(1)


def _encode(path: str, labels: tuple[int, ...], drise, dvalley) -> str:
    label_text = ",".join(str(v) for v in labels)
    rise_text = ",".join(str(i) for i in sorted(drise))
    valley_text = ",".join(str(i) for i in sorted(dvalley))
    return f"{path}{SEPARATOR}{label_text}{SEPARATOR}{rise_text}{SEPARATOR}{valley_text}"


def iter_decorated_labelled_dyck_paths(
    n: int, k: int, l: int
) -> Iterator[DecoratedLabelledDyckPath]:
    """Yield every element of ``LD(n)^{*k, •l}`` (standard labelling) once, streaming."""
    if n < 1:
        raise ValueError("size must be positive")
    if k < 0 or l < 0:
        raise ValueError("decoration counts must be nonnegative")
    for path in enumerate_dyck_paths(n):
        rises, _valleys = _rises_and_valleys(path)
        if len(rises) < k:
            continue
        for labels in _iter_standard_labellings(path):
            contractible = _contractible_valleys(path, labels)
            if len(contractible) < l:
                continue
            for drise in combinations(rises, k):
                drise_set = frozenset(drise)
                for dvalley in combinations(contractible, l):
                    yield DecoratedLabelledDyckPath(
                        _encode(path, labels, drise_set, frozenset(dvalley)),
                        validate=False,
                    )


@cache
def enumerate_decorated_labelled_dyck_paths(
    n: int, k: int, l: int
) -> tuple[DecoratedLabelledDyckPath, ...]:
    """All of ``LD(n)^{*k, •l}`` (cached; use the iterator for large fibers)."""
    return tuple(iter_decorated_labelled_dyck_paths(n, k, l))


def decorated_labelled_dyck_count(n: int, k: int, l: int) -> int:
    """``|LD(n)^{*k, •l}|`` computed by streaming enumeration."""
    return sum(1 for _ in iter_decorated_labelled_dyck_paths(n, k, l))


def canonical_decorated_labelled_dyck_path(
    path: str, k: int, l: int
) -> DecoratedLabelledDyckPath:
    """A canonical size-``n`` object on ``path`` with ``k``/``l`` decorations.

    The labelling assigns ``1, ..., n`` to vertical steps in step order after
    sorting each run ascending (the lexicographically-first standard labelling),
    then decorates the first ``k`` rises and first ``l`` contractible valleys.
    Used to build large valid objects for the resource and value gates without
    enumerating the (exponential) fiber. Requires the shape to admit ``k`` rises
    and ``l`` contractible valleys under this labelling.
    """
    if k < 0 or l < 0:
        raise ValueError("decoration counts must be nonnegative")
    runs = _vertical_runs(path)
    n = path.count("N")
    labels_list = [0] * (n + 1)
    next_label = 1
    for run in runs:
        for position in run:  # runs are increasing, assign ascending labels
            labels_list[position] = next_label
            next_label += 1
    labels = tuple(labels_list[1:])
    rises, _valleys = _rises_and_valleys(path)
    contractible = _contractible_valleys(path, labels)
    if len(rises) < k or len(contractible) < l:
        raise ValueError(f"shape {path!r} cannot carry {k} rises and {l} valleys")
    drise = frozenset(rises[:k])
    dvalley = frozenset(contractible[:l])
    return DecoratedLabelledDyckPath(_encode(path, labels, drise, dvalley))
