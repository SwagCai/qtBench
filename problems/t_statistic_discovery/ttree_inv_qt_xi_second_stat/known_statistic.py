"""Reference implementation of the public first statistic: the tree inversions.

A standard zero-rooted tiered tree has an implicit root of label and level ``0``.
Its encoding is ``levels + "|" + parents`` for the non-root labels ``1, ..., n``.
A parent value of ``0`` denotes the root. Two non-root vertices ``i < j`` are
compatible when ``lv(i) < lv(j)``; the root is compatible with every vertex.

    inv(T) = #{ (i, j) : i, j non-root, j a descendant of i,
                         j compatible with p(i), and j < i }.

The same value is exposed as ``tree.inv()`` on the object passed to a submission.
"""
from __future__ import annotations


def _encoding(tree) -> str:
    if hasattr(tree, "encoding"):
        return tree.encoding
    return tree


def inv(tree) -> int:
    level_text, parent_text = _encoding(tree).split("|")
    levels = [int(piece) for piece in level_text.split(",")]
    parents = [int(piece) for piece in parent_text.split(",")]
    n = len(levels)

    def compatible(i: int, j: int) -> bool:
        if i == 0 or j == 0:
            return i != j
        low, high = (i, j) if i < j else (j, i)
        return levels[low - 1] < levels[high - 1]

    ancestors = []
    for i in range(1, n + 1):
        chain = set()
        current = parents[i - 1]
        while current:
            chain.add(current)
            current = parents[current - 1]
        ancestors.append(chain)

    count = 0
    for i in range(1, n + 1):
        for j in range(1, i):
            if i in ancestors[j - 1] and compatible(j, parents[i - 1]):
                count += 1
    return count


def statistic(tree) -> int:
    return inv(tree)
