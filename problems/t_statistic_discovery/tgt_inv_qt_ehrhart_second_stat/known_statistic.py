"""Reference implementation of the public first statistic: the tree inversions.

An object is a spanning tree of a connected threshold graph on ``{0, ..., n}``,
rooted at the dominating vertex ``0``, encoded as ``up_degrees + "|" + parents``
over the vertices ``1, ..., n``.

    inv(T) = #{ (i, j) : i > j, j a descendant of i in T }.

Equivalently, every vertex contributes the number of its ancestors that carry a
larger label. For a threshold graph every inversion is a ``kappa``-inversion, so
this is also Gessel's inversion enumerator statistic. The same value is exposed
as ``tree.inv()`` on the object passed to a submission.
"""
from __future__ import annotations


def _encoding(tree) -> str:
    if hasattr(tree, "encoding"):
        return tree.encoding
    return tree


def inv(tree) -> int:
    _up_text, parent_text = _encoding(tree).split("|")
    parents = [int(piece) for piece in parent_text.split(",")]
    total = 0
    for vertex in range(1, len(parents) + 1):
        current = parents[vertex - 1]
        while current:
            if current > vertex:
                total += 1
            current = parents[current - 1]
    return total


def statistic(tree) -> int:
    return inv(tree)
