"""Reference implementation of the public first statistic: the labelled area.

A standardly labelled parallelogram polyomino is encoded as
``upper + "|" + lower + "|" + labels``: ``upper``/``lower`` are the two North/East
boundary words and ``labels`` lists the label of each labelled cell in the
canonical ``(x, y)`` order (columns first, then rows). ``area`` counts the
non-labelled cells between the two paths whose nearest labelled cell to the left
in the same row carries a strictly greater label than the nearest labelled cell
below in the same column. The same value is exposed as ``polyomino.area()`` on
the object passed to a submission.
"""
from __future__ import annotations


def _encoding(polyomino) -> str:
    if hasattr(polyomino, "encoding"):
        return polyomino.encoding
    return polyomino


def _parse(encoding: str):
    upper, lower, label_text = encoding.split("|")
    red_cells = set()
    rh = {}
    x = y = 0
    for step in upper:
        if step == "N":
            red_cells.add((x, y))
            y += 1
        else:
            rh[x] = y
            x += 1
    green_cells = set()
    gh = {}
    x = y = 0
    for step in lower:
        if step == "E":
            green_cells.add((x, y))
            gh[x] = y
            x += 1
        else:
            y += 1
    cells = sorted(red_cells | green_cells)
    labels = [int(piece) for piece in label_text.split(",")]
    label = dict(zip(cells, labels))
    return label, gh, rh


def _nearest(sorted_pairs, bound):
    found = None
    for position, value in sorted_pairs:
        if position < bound:
            found = value
        else:
            break
    return found


def area(polyomino) -> int:
    label, gh, rh = _parse(_encoding(polyomino))
    rows: dict[int, list[tuple[int, int]]] = {}
    columns: dict[int, list[tuple[int, int]]] = {}
    for (x, y), value in label.items():
        rows.setdefault(y, []).append((x, value))
        columns.setdefault(x, []).append((y, value))
    rows = {y: sorted(pairs) for y, pairs in rows.items()}
    columns = {x: sorted(pairs) for x, pairs in columns.items()}

    total = 0
    for x in sorted(rh):
        for y in range(gh[x], rh[x]):
            if (x, y) in label:
                continue
            left = _nearest(rows.get(y, ()), x)
            below = _nearest(columns.get(x, ()), y)
            if left is not None and below is not None and left > below:
                total += 1
    return total


def statistic(polyomino) -> int:
    return area(polyomino)
