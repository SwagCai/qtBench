"""Iraci--Romero gamma-parking functions with a selected set of area cells.

Following Iraci and Romero (see the problem statements for references), for a
partition ``gamma |- m`` a **gamma-Dyck path of size n** is a parallelogram
polyomino of size ``(m + n + 1) x n``, that is a pair of North/East lattice
paths ``(P, Q)`` from ``(0, 0)`` to ``(m + n + 1, n)`` with the top path ``P``
strictly above the bottom path ``Q`` except at the two endpoints, such that

* ``Q`` has no two consecutive North steps, and
* writing ``alpha_i`` for the number of East steps of ``Q`` in row ``i``, the
  sequence ``(alpha_1 - 1, alpha_2, ..., alpha_n)`` rearranges to
  ``gamma + 1^n``.

A **labeled** gamma-Dyck path assigns a positive integer to every North step of
``P``, strictly increasing along consecutive North steps; the word ``w`` of
labels read bottom to top has content ``lambda``, meaning that the label ``i``
occurs ``lambda_i`` times. These are the gamma-parking functions ``PF^gamma_λ``.
When ``w`` is a lattice word the object lies in ``LPF^gamma_λ``.

The polyomino has at least ``(m + n + 1) + n - 1`` cells, and

    area(p) = (number of cells) - (m + 2n)

counts the surplus. The surplus cells are exactly those of column ``j`` lying
strictly above the minimal top path, so they form a canonical set ``Area(p)``
with ``#Area(p) = area(p)``. An object of this family is a pair ``(p, S)`` with
``S`` a subset of ``Area(p)``; the public statistic is ``#S``.

The canonical encoding is ``bottom|top|word|selected``, where ``bottom`` and
``top`` are the comma-separated column heights of ``Q`` and ``P``, ``word`` is
the comma-separated label word read bottom to top, and ``selected`` lists the
chosen cells as ``column.row`` in increasing order (empty for ``S`` empty). For
example ::

    0,0,0,1|1,2,2,2|1,2|2.1

is a ``(1)``-Dyck path of size ``2``, labeled ``1, 2`` bottom to top, with the
single cell of ``Area(p)`` selected.

The e-composition ``eta(p)`` of Definition 2.7 is read off the object and is
what grades the target; it is exposed as ``eta()`` and returned as a partition.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from itertools import permutations
from typing import Iterator

SEPARATOR = "|"
CELL_SEPARATOR = "."

GammaParkingWord = str


def _fiber_parameters(gamma, content) -> tuple[tuple[int, ...], tuple[int, ...]]:
    gamma = tuple(int(part) for part in gamma)
    content = tuple(int(part) for part in content)
    if (
        not content
        or any(part < 1 for part in content)
        or any(left < right for left, right in zip(content, content[1:]))
    ):
        raise ValueError("content must be a partition")
    if any(part < 1 for part in gamma) or any(
        left < right for left, right in zip(gamma, gamma[1:])
    ):
        raise ValueError("gamma must be a partition")
    return gamma, content


def _parse(encoding: str):
    bottom_text, top_text, word_text, selected_text = encoding.split(SEPARATOR)
    bottom = tuple(int(piece) for piece in bottom_text.split(","))
    top = tuple(int(piece) for piece in top_text.split(","))
    word = tuple(int(piece) for piece in word_text.split(","))
    if selected_text:
        selected = tuple(
            tuple(int(piece) for piece in field.split(CELL_SEPARATOR))
            for field in selected_text.split(",")
        )
    else:
        selected = ()
    return bottom, top, word, selected


def _encode(bottom, top, word, selected) -> str:
    return SEPARATOR.join(
        (
            ",".join(str(value) for value in bottom),
            ",".join(str(value) for value in top),
            ",".join(str(value) for value in word),
            ",".join(f"{column}{CELL_SEPARATOR}{row}" for column, row in selected),
        )
    )


def _area_cells(bottom, top) -> tuple[tuple[int, int], ...]:
    """Cells of the polyomino above the minimal top path, column by column.

    The cell ``(j, y)`` occupies ``[j - 1, j] x [y, y + 1]``. Column ``j`` may
    not drop below ``bottom[j] + 1``, so its surplus cells are the ones at
    heights ``bottom[j] + 1, ..., top[j - 1] - 1``.
    """
    return tuple(
        (column + 1, height)
        for column in range(len(bottom) - 1)
        for height in range(bottom[column + 1] + 1, top[column])
    )


def _label_gaps(top, n: int) -> tuple[int, ...]:
    """East steps of the top path after each of its ``n`` North steps."""
    gaps = []
    previous = 0
    run = 0
    started = False
    for height in top:
        for _ in range(height - previous):
            if started:
                gaps.append(run)
            run = 0
            started = True
        run += 1
        previous = height
    gaps.append(run)
    return tuple(gaps)


def _gamma_from_bottom(bottom) -> tuple[int, ...]:
    """The partition ``gamma`` recorded by the bottom path."""
    n = bottom[-1] + 1
    runs = [0] * n
    for height in bottom:
        runs[height] += 1
    parts = sorted([runs[0] - 1] + runs[1:], reverse=True)
    return tuple(part - 1 for part in parts if part > 1)


def is_gamma_parking_selection(encoding: str, *, lattice: bool = False) -> bool:
    """Whether ``encoding`` is a valid pair ``(p, S)``, optionally lattice."""
    if not isinstance(encoding, str) or encoding.count(SEPARATOR) != 3:
        return False
    try:
        bottom, top, word, selected = _parse(encoding)
    except ValueError:
        return False
    width = len(bottom)
    n = len(word)
    if n < 1 or len(top) != width or width < n + 1:
        return False
    if bottom[0] != 0 or bottom[-1] != n - 1:
        return False
    if any(bottom[j] > bottom[j + 1] for j in range(width - 1)):
        return False
    if any(bottom[j + 1] - bottom[j] > 1 for j in range(width - 1)):
        return False
    runs = [0] * n
    for height in bottom:
        runs[height] += 1
    if runs[0] < 2 or any(run < 1 for run in runs[1:]):
        return False
    if top[-1] != n or any(top[j] > top[j + 1] for j in range(width - 1)):
        return False
    if any(top[j] < bottom[j + 1] + 1 for j in range(width - 1)):
        return False
    gaps = _label_gaps(top, n)
    if len(gaps) != n:
        return False
    for index in range(1, n):
        if gaps[index - 1] == 0 and word[index - 1] >= word[index]:
            return False
    if any(letter < 1 for letter in word):
        return False
    content = [word.count(letter) for letter in range(1, max(word) + 1)]
    if any(content[i] < content[i + 1] for i in range(len(content) - 1)) or 0 in content:
        return False
    if lattice:
        counts: dict[int, int] = {}
        for letter in word:
            counts[letter] = counts.get(letter, 0) + 1
            if letter > 1 and counts[letter] > counts.get(letter - 1, 0):
                return False
    cells = _area_cells(bottom, top)
    if len(set(selected)) != len(selected) or list(selected) != sorted(selected):
        return False
    return set(selected) <= set(cells)


@dataclass(frozen=True, init=False)
class GammaParkingSelection:
    """A gamma-parking function together with a subset of its area cells."""

    encoding: str
    n: int

    def __init__(self, encoding: str, *, validate: bool = True, lattice: bool = False) -> None:
        if validate and not is_gamma_parking_selection(encoding, lattice=lattice):
            raise ValueError(f"not a gamma-parking function selection: {encoding!r}")
        _bottom, _top, word, _selected = _parse(encoding)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "n", len(word))

    @cached_property
    def _parsed(self):
        return _parse(self.encoding)

    @property
    def size(self) -> int:
        """The size parameter ``n + |gamma|`` of the fiber."""
        return self.n + sum(self.gamma)

    @cached_property
    def width(self) -> int:
        """Number of columns, ``|gamma| + n + 1``."""
        return len(self.bottom)

    @cached_property
    def bottom(self) -> tuple[int, ...]:
        """Column heights of the bottom path ``Q``."""
        return self._parsed[0]

    @cached_property
    def top(self) -> tuple[int, ...]:
        """Column heights of the top path ``P``."""
        return self._parsed[1]

    @cached_property
    def word(self) -> tuple[int, ...]:
        """Labels of the North steps of ``P``, read bottom to top."""
        return self._parsed[2]

    @cached_property
    def selected_cells(self) -> tuple[tuple[int, int], ...]:
        """The chosen subset ``S``, in increasing ``(column, row)`` order."""
        return self._parsed[3]

    @cached_property
    def gamma(self) -> tuple[int, ...]:
        """The partition ``gamma`` indexing the family."""
        return _gamma_from_bottom(self.bottom)

    @cached_property
    def content(self) -> tuple[int, ...]:
        """The content ``lambda``: ``content[i - 1]`` is the multiplicity of ``i``."""
        top_label = max(self.word)
        return tuple(self.word.count(letter) for letter in range(1, top_label + 1))

    @cached_property
    def bottom_runs(self) -> tuple[int, ...]:
        """East-step counts ``alpha_1, ..., alpha_n`` of ``Q``, row by row."""
        runs = [0] * self.n
        for height in self.bottom:
            runs[height] += 1
        return tuple(runs)

    @cached_property
    def area_cells(self) -> tuple[tuple[int, int], ...]:
        """The canonical set ``Area(p)``, in increasing ``(column, row)`` order."""
        return _area_cells(self.bottom, self.top)

    @cached_property
    def selected(self) -> frozenset[tuple[int, int]]:
        """The chosen subset ``S`` as a set."""
        return frozenset(self.selected_cells)

    @cached_property
    def gaps(self) -> tuple[int, ...]:
        """East steps of ``P`` after each North step, bottom to top."""
        return _label_gaps(self.top, self.n)

    @cached_property
    def ascents(self) -> frozenset[int]:
        """``Asc(w) = {i : w_i < w_{i+1}}``, using ``1``-based positions."""
        return frozenset(
            index
            for index in range(1, self.n)
            if self.word[index - 1] < self.word[index]
        )

    def area(self) -> int:
        """``area(p) = #Area(p)``."""
        return len(self.area_cells)

    def selected_count(self) -> int:
        """The public statistic ``#S``."""
        return len(self.selected_cells)

    def eta(self) -> tuple[int, ...]:
        """The e-composition ``eta(p)``, sorted into a partition."""
        gaps = list(self.gaps)
        for index in range(1, self.n + 1):
            if index not in self.ascents:
                gaps[index - 1] -= 1
        parts = []
        run = 1
        for index in range(1, self.n):
            if gaps[index - 1] == 0:
                run += 1
            else:
                parts.append(run)
                run = 1
        parts.append(run)
        return tuple(sorted(parts, reverse=True))

    def to_jsonable(self) -> str:
        return self.encoding


def gamma_parking_selection(
    bottom, top, word, selected, *, validate: bool = True, lattice: bool = False
) -> GammaParkingSelection:
    """Assemble a pair ``(p, S)`` from its four components."""
    return GammaParkingSelection(
        _encode(
            tuple(bottom),
            tuple(top),
            tuple(word),
            tuple(tuple(cell) for cell in selected),
        ),
        validate=validate,
        lattice=lattice,
    )


def gamma_parking_size(encoding_or_object) -> int:
    """The fiber size parameter ``n + |gamma|``."""
    if isinstance(encoding_or_object, GammaParkingSelection):
        return encoding_or_object.size
    return GammaParkingSelection(encoding_or_object, validate=False).size


def _iter_bottom_paths(gamma: tuple[int, ...], n: int) -> Iterator[tuple[int, ...]]:
    """Column heights of every admissible bottom path."""
    if len(gamma) > n:
        return
    target = tuple(sorted([part + 1 for part in gamma] + [1] * (n - len(gamma))))
    seen = set()
    for arrangement in permutations(target):
        if arrangement in seen:
            continue
        seen.add(arrangement)
        runs = (arrangement[0] + 1,) + arrangement[1:]
        heights: list[int] = []
        for level, run in enumerate(runs):
            heights.extend([level] * run)
        yield tuple(heights)


def _iter_top_paths(bottom: tuple[int, ...], n: int) -> Iterator[tuple[int, ...]]:
    """Column heights of every top path strictly above ``bottom``."""
    width = len(bottom)
    floors = [bottom[j] + 1 for j in range(1, width)] + [n]
    heights: list[int] = []

    def rec(column: int, previous: int) -> Iterator[tuple[int, ...]]:
        if column == width:
            yield tuple(heights)
            return
        for value in range(max(previous, floors[column]), n + 1):
            heights.append(value)
            yield from rec(column + 1, value)
            heights.pop()

    yield from rec(0, 0)


def _iter_words(gaps: tuple[int, ...], content: tuple[int, ...]) -> Iterator[tuple[int, ...]]:
    """Every label word with the given content, increasing on consecutive rises."""
    n = sum(content)
    remaining = list(content)
    word: list[int] = []

    def rec(index: int) -> Iterator[tuple[int, ...]]:
        if index == n:
            yield tuple(word)
            return
        floor = word[-1] if index and gaps[index - 1] == 0 else 0
        for letter in range(floor + 1, len(remaining) + 1):
            if remaining[letter - 1]:
                remaining[letter - 1] -= 1
                word.append(letter)
                yield from rec(index + 1)
                word.pop()
                remaining[letter - 1] += 1

    yield from rec(0)


def _is_lattice_word(word: tuple[int, ...]) -> bool:
    counts: dict[int, int] = {}
    for letter in word:
        counts[letter] = counts.get(letter, 0) + 1
        if letter > 1 and counts[letter] > counts.get(letter - 1, 0):
            return False
    return True


def _iter_subsets(cells: tuple[tuple[int, int], ...]):
    for mask in range(1 << len(cells)):
        yield tuple(cell for index, cell in enumerate(cells) if mask >> index & 1)


def iter_gamma_parking_selections(
    gamma, content, *, lattice: bool = False
) -> Iterator[GammaParkingSelection]:
    """Yield every pair ``(p, S)`` of the fiber ``(gamma, content)`` once."""
    gamma, content = _fiber_parameters(gamma, content)
    n = sum(content)
    for bottom in _iter_bottom_paths(gamma, n):
        for top in _iter_top_paths(bottom, n):
            gaps = _label_gaps(top, n)
            cells = _area_cells(bottom, top)
            for word in _iter_words(gaps, content):
                if lattice and not _is_lattice_word(word):
                    continue
                for selected in _iter_subsets(cells):
                    yield GammaParkingSelection(
                        _encode(bottom, top, word, selected), validate=False
                    )


def canonical_gamma_parking_selection(gamma, content) -> GammaParkingSelection:
    """The minimal-area object of the fiber, with ``S`` empty.

    The bottom path takes ``gamma`` in its first rows and the top path hugs it,
    so ``Area(p)`` is empty. Because the bottom path has no two consecutive
    North steps, neither does the hugging top path, so no pair of labels is
    constrained and the weakly increasing word is admissible. This gives one
    valid object per fiber without enumerating it.
    """
    gamma, content = _fiber_parameters(gamma, content)
    n = sum(content)
    if len(gamma) > n:
        raise ValueError("gamma has too many parts for the content")
    bottom = next(_iter_bottom_paths(gamma, n))
    top = tuple(bottom[j + 1] + 1 for j in range(len(bottom) - 1)) + (n,)
    word = tuple(
        letter for letter, multiplicity in enumerate(content, start=1)
        for _ in range(multiplicity)
    )
    return GammaParkingSelection(_encode(bottom, top, word, ()), validate=False)
