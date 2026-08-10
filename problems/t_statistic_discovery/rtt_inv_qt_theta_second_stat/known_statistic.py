"""Reference implementation of the public first statistic: the tree inversions.

A standard rooted tiered tree has an ordinary label on every vertex, including
the root, which is the unique vertex at level ``0``. Its encoding is
``levels + "|" + parents`` over the labels ``1, ..., n + 1``; the root is the
unique vertex whose parent entry is ``0``. Two vertices ``i < j`` are compatible
when ``lv(i) < lv(j)``, so the root is compatible exactly with the labels above
its own.

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
    size = len(levels)
    root = levels.index(0) + 1

    def compatible(i: int, j: int) -> bool:
        if i == j:
            return False
        low, high = (i, j) if i < j else (j, i)
        return levels[low - 1] < levels[high - 1]

    ancestors = []
    for i in range(1, size + 1):
        chain = set()
        current = parents[i - 1]
        while current:
            chain.add(current)
            current = parents[current - 1]
        ancestors.append(chain)

    count = 0
    for i in range(1, size + 1):
        if i == root:
            continue
        for j in range(1, i):
            if j == root:
                continue
            if i in ancestors[j - 1] and compatible(j, parents[i - 1]):
                count += 1
    return count


def statistic(tree) -> int:
    return inv(tree)
