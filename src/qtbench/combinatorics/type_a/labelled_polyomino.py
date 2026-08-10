"""Standardly labelled parallelogram polyominoes and their labelled area.

A parallelogram polyomino of size ``m x n`` is a pair of monotone North/East
lattice paths from ``(0, 0)`` to ``(m, n)``; the upper (red) path starts North
and ends East, the lower (green) path starts East and ends North, and they touch
only at the two corners (the same objects enumerated in ``polyomino.py``). A cell
``(x, y)`` spans ``[x, x+1] x [y, y+1]``.

Following D'Adderio, Iraci, Le Borgne, Romero and Vanden Wyngaerd (see the
problem statement for references), a cell is *labelled* when it contains a
vertical step of the upper path (a *red* cell) and/or a horizontal step of the
lower path (a *green* cell):

* a North step of the upper path from ``(x, y)`` to ``(x, y+1)`` labels ``(x, y)``;
* an East step of the lower path from ``(x, y)`` to ``(x+1, y)`` labels ``(x, y)``.

Cell ``(0, 0)`` carries both a red and a green step (the *black* cell); there are
exactly ``m + n - 1`` labelled cells. A *standard labelling* is a bijection from
the labelled cells to ``[m + n - 1]`` whose labels are strictly increasing up
each column and strictly decreasing from left to right along each row. The set of
such objects is ``stLPP(m, n)``.

The public statistic is the labelled ``area``: the number of non-labelled cells
between the two paths for which the nearest labelled cell to the left in the same
row carries a strictly greater label than the nearest labelled cell below in the
same column.

The joint distribution of ``area`` and the unknown partner is the Hilbert series
``<Theta_{e_{m-1}} Theta_{e_{n-1}} e_1, e_{1^{m+n-1}}>``; ``area`` is public and
the ``t``-partner is the object of the discovery task.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass
from functools import cache, cached_property
from typing import Iterator

from .polyomino import (
    SEPARATOR,
    is_parallelogram_polyomino,
    iter_parallelogram_polyominoes,
)

LabelledPolyominoWord = str


def _shape_cells(upper: str, lower: str):
    """Parse a polyomino shape into its labelled cells and column spans.

    Returns ``(red_cells, green_cells, gh, rh)`` where ``red_cells`` are the
    upper path's North-step cells, ``green_cells`` the lower path's East-step
    cells, ``gh[x]`` the lower path's East-step height in column ``x`` (the
    bottom row of that column) and ``rh[x]`` the upper path's East-step height
    (one past the top row of that column).
    """
    red_cells: set[tuple[int, int]] = set()
    rh: dict[int, int] = {}
    x = y = 0
    for step in upper:
        if step == "N":
            red_cells.add((x, y))
            y += 1
        else:
            rh[x] = y
            x += 1
    green_cells: set[tuple[int, int]] = set()
    gh: dict[int, int] = {}
    x = y = 0
    for step in lower:
        if step == "E":
            green_cells.add((x, y))
            gh[x] = y
            x += 1
        else:
            y += 1
    return red_cells, green_cells, gh, rh


def _sorted_label_cells(red_cells, green_cells) -> tuple[tuple[int, int], ...]:
    """Labelled cells in the canonical ``(x, y)`` order used by the encoding."""
    return tuple(sorted(red_cells | green_cells))


def is_st_labelled_polyomino(encoding: str) -> bool:
    """Whether ``encoding`` is a valid ``upper|lower|labels`` standard labelling."""
    if not isinstance(encoding, str) or encoding.count(SEPARATOR) != 2:
        return False
    upper, lower, label_text = encoding.split(SEPARATOR)
    shape = f"{upper}{SEPARATOR}{lower}"
    if not is_parallelogram_polyomino(shape):
        return False
    m = upper.count("E")
    n = upper.count("N")
    red_cells, green_cells, _gh, _rh = _shape_cells(upper, lower)
    cells = _sorted_label_cells(red_cells, green_cells)
    pieces = label_text.split(",") if label_text else []
    if len(pieces) != len(cells) or len(cells) != m + n - 1:
        return False
    try:
        labels = [int(piece) for piece in pieces]
    except ValueError:
        return False
    if sorted(labels) != list(range(1, m + n)):
        return False
    label = dict(zip(cells, labels))
    return _labels_are_monotone(label)


def _labels_are_monotone(label: dict[tuple[int, int], int]) -> bool:
    by_col: dict[int, list[tuple[int, int]]] = {}
    by_row: dict[int, list[tuple[int, int]]] = {}
    for x, y in label:
        by_col.setdefault(x, []).append(y)
        by_row.setdefault(y, []).append(x)
    for x, ys in by_col.items():
        ys.sort()
        if any(label[(x, ys[i])] >= label[(x, ys[i + 1])] for i in range(len(ys) - 1)):
            return False
    for y, xs in by_row.items():
        xs.sort()
        if any(label[(xs[i], y)] <= label[(xs[i + 1], y)] for i in range(len(xs) - 1)):
            return False
    return True


@dataclass(frozen=True, init=False)
class LabelledParallelogramPolyomino:
    """A standardly labelled parallelogram polyomino.

    Encoded as ``upper + "|" + lower + "|" + labels`` where ``upper``/``lower``
    are the two North/East boundary words and ``labels`` lists the label of each
    labelled cell in the canonical ``(x, y)`` order (columns first, then rows).
    Public benchmark code exposes only structural data and the ``area``
    statistic; the unknown ``t``-partner belongs to the discovery task.
    """

    encoding: str
    upper: str
    lower: str
    m: int
    n: int

    def __init__(self, encoding: str, *, validate: bool = True) -> None:
        if validate and not is_st_labelled_polyomino(encoding):
            raise ValueError(f"not a standardly labelled parallelogram polyomino: {encoding!r}")
        upper, lower, _label_text = encoding.split(SEPARATOR)
        object.__setattr__(self, "encoding", encoding)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "m", upper.count("E"))
        object.__setattr__(self, "n", upper.count("N"))

    @property
    def size(self) -> int:
        """Number of labels, ``m + n - 1``."""
        return self.m + self.n - 1

    @cached_property
    def _shape(self):
        return _shape_cells(self.upper, self.lower)

    @cached_property
    def red_cells(self) -> frozenset[tuple[int, int]]:
        """Cells carrying a vertical step of the upper path (red and black)."""
        return frozenset(self._shape[0])

    @cached_property
    def green_cells(self) -> frozenset[tuple[int, int]]:
        """Cells carrying a horizontal step of the lower path (green and black)."""
        return frozenset(self._shape[1])

    @cached_property
    def label(self) -> dict[tuple[int, int], int]:
        """Map from each labelled cell ``(x, y)`` to its label."""
        red_cells, green_cells, _gh, _rh = self._shape
        cells = _sorted_label_cells(red_cells, green_cells)
        _upper, _lower, label_text = self.encoding.split(SEPARATOR)
        labels = [int(piece) for piece in label_text.split(",")]
        return dict(zip(cells, labels))

    @cached_property
    def labelled_cells(self) -> tuple[tuple[int, int, int], ...]:
        """Triples ``(x, y, label)`` in canonical ``(x, y)`` order."""
        return tuple((x, y, self.label[(x, y)]) for (x, y) in sorted(self.label))

    @cached_property
    def rows(self) -> dict[int, tuple[tuple[int, int], ...]]:
        """For each row ``y``, the ``(x, label)`` of its labelled cells, left to right."""
        out: dict[int, list[tuple[int, int]]] = {}
        for (x, y), value in self.label.items():
            out.setdefault(y, []).append((x, value))
        return {y: tuple(sorted(pairs)) for y, pairs in out.items()}

    @cached_property
    def columns(self) -> dict[int, tuple[tuple[int, int], ...]]:
        """For each column ``x``, the ``(y, label)`` of its labelled cells, bottom to top."""
        out: dict[int, list[tuple[int, int]]] = {}
        for (x, y), value in self.label.items():
            out.setdefault(x, []).append((y, value))
        return {x: tuple(sorted(pairs)) for x, pairs in out.items()}

    @cached_property
    def cells(self) -> tuple[tuple[int, int], ...]:
        """All cells enclosed by the two paths (column ``x`` spans ``[gh[x], rh[x])``)."""
        _red, _green, gh, rh = self._shape
        return tuple((x, y) for x in range(self.m) for y in range(gh[x], rh[x]))

    def area(self) -> int:
        """Labelled area: non-labelled cells with left label > below label."""
        _red, _green, gh, rh = self._shape
        label = self.label
        rows = self.rows
        columns = self.columns
        total = 0
        for x in range(self.m):
            column = columns.get(x, ())
            for y in range(gh[x], rh[x]):
                if (x, y) in label:
                    continue
                left = _nearest_label(rows.get(y, ()), x)
                below = _nearest_label(column, y)
                if left is not None and below is not None and left > below:
                    total += 1
        return total

    def to_jsonable(self) -> str:
        return self.encoding


def _nearest_label(sorted_pairs, bound):
    """Label of the ``(position, label)`` pair with largest position < ``bound``."""
    found = None
    for position, value in sorted_pairs:
        if position < bound:
            found = value
        else:
            break
    return found


def st_labelled_polyomino_area(encoding: str) -> int:
    """Labelled area of the standardly labelled polyomino given by ``encoding``."""
    return LabelledParallelogramPolyomino(encoding, validate=False).area()


def st_labelled_polyomino_size(encoding_or_object) -> int:
    """Semiperimeter ``m + n`` (module-level, for the value/resource gate)."""
    if isinstance(encoding_or_object, LabelledParallelogramPolyomino):
        return encoding_or_object.m + encoding_or_object.n
    upper, _lower, _labels = encoding_or_object.split(SEPARATOR)
    return len(upper)


# ---------------------------------------------------------------------------
# Standard labellings of a fixed shape (linear extensions of the label poset)
# ---------------------------------------------------------------------------


def _label_predecessors(red_cells, green_cells):
    """For each labelled cell, the cells that must carry a strictly smaller label."""
    cells = red_cells | green_cells
    preds: dict[tuple[int, int], set[tuple[int, int]]] = {c: set() for c in cells}
    by_col: dict[int, list[tuple[int, int]]] = {}
    by_row: dict[int, list[tuple[int, int]]] = {}
    for c in cells:
        by_col.setdefault(c[0], []).append(c)
        by_row.setdefault(c[1], []).append(c)
    for col in by_col.values():
        for a in col:
            for b in col:
                if a[1] < b[1]:  # lower cell < upper cell (labels increase upward)
                    preds[b].add(a)
    for row in by_row.values():
        for a in row:
            for b in row:
                if a[0] > b[0]:  # rightward cell < leftward cell (labels decrease left to right)
                    preds[b].add(a)
    return preds


def _iter_standard_labellings(red_cells, green_cells) -> Iterator[dict[tuple[int, int], int]]:
    """Yield every standard labelling of a fixed shape as ``cell -> label``."""
    preds = _label_predecessors(red_cells, green_cells)
    cells = list(preds)
    total = len(cells)
    assigned: dict[tuple[int, int], int] = {}

    def rec(next_label: int) -> Iterator[dict[tuple[int, int], int]]:
        if next_label > total:
            yield dict(assigned)
            return
        for c in cells:
            if c in assigned:
                continue
            if all(p in assigned for p in preds[c]):
                assigned[c] = next_label
                yield from rec(next_label + 1)
                del assigned[c]

    yield from rec(1)


def _encode(upper: str, lower: str, label: dict[tuple[int, int], int]) -> str:
    red_cells, green_cells, _gh, _rh = _shape_cells(upper, lower)
    cells = _sorted_label_cells(red_cells, green_cells)
    labels = ",".join(str(label[c]) for c in cells)
    return f"{upper}{SEPARATOR}{lower}{SEPARATOR}{labels}"


def iter_st_labelled_polyominoes(m: int, n: int) -> Iterator[LabelledParallelogramPolyomino]:
    """Yield every element of ``stLPP(m, n)`` once, streaming."""
    if m < 1 or n < 1:
        raise ValueError("both bounding-box dimensions must be positive")
    for shape in iter_parallelogram_polyominoes(m, n):
        upper, lower = shape.split(SEPARATOR)
        red_cells, green_cells, _gh, _rh = _shape_cells(upper, lower)
        for label in _iter_standard_labellings(red_cells, green_cells):
            yield LabelledParallelogramPolyomino(_encode(upper, lower, label), validate=False)


@cache
def enumerate_st_labelled_polyominoes(m: int, n: int) -> tuple[LabelledParallelogramPolyomino, ...]:
    """All of ``stLPP(m, n)`` (cached; use the iterator for large boxes)."""
    return tuple(iter_st_labelled_polyominoes(m, n))


def st_labelled_polyomino_count(m: int, n: int) -> int:
    """``|stLPP(m, n)|`` computed by streaming enumeration."""
    return sum(1 for _ in iter_st_labelled_polyominoes(m, n))


def canonical_standard_labelling(upper: str, lower: str) -> LabelledParallelogramPolyomino:
    """A canonical standard labelling of a fixed shape, in near-linear time.

    Used to build large valid objects for the resource and value gates without
    enumerating the whole fiber. A Kahn topological sort of the label poset's
    covering relations (adjacent cells in each column and row), breaking ties by
    the smallest ``(x, y)``, yields one deterministic linear extension.
    """
    if not is_parallelogram_polyomino(f"{upper}{SEPARATOR}{lower}"):
        raise ValueError("not a parallelogram-polyomino shape")
    red_cells, green_cells, _gh, _rh = _shape_cells(upper, lower)
    cells = red_cells | green_cells
    successors: dict[tuple[int, int], list[tuple[int, int]]] = {c: [] for c in cells}
    indegree: dict[tuple[int, int], int] = {c: 0 for c in cells}
    by_col: dict[int, list[tuple[int, int]]] = {}
    by_row: dict[int, list[tuple[int, int]]] = {}
    for c in cells:
        by_col.setdefault(c[0], []).append(c)
        by_row.setdefault(c[1], []).append(c)
    for column in by_col.values():
        column.sort(key=lambda c: c[1])
        for lower_cell, upper_cell in zip(column, column[1:]):
            successors[lower_cell].append(upper_cell)  # labels increase upward
            indegree[upper_cell] += 1
    for row in by_row.values():
        row.sort(key=lambda c: c[0])
        for left_cell, right_cell in zip(row, row[1:]):
            successors[right_cell].append(left_cell)  # labels decrease left to right
            indegree[left_cell] += 1

    ready = [c for c in cells if indegree[c] == 0]
    heapq.heapify(ready)
    assigned: dict[tuple[int, int], int] = {}
    next_label = 1
    while ready:
        cell = heapq.heappop(ready)
        assigned[cell] = next_label
        next_label += 1
        for successor in successors[cell]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(ready, successor)
    return LabelledParallelogramPolyomino(_encode(upper, lower, assigned))
