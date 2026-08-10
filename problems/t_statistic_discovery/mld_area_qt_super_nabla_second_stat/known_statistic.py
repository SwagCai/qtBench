"""Reference implementation of the public first statistic: the rectangular area.

A standard multi-labelled ``k^n`` Dyck path is encoded as
``path + "|" + row_0 + "|" + ... + "|" + row_k``: ``path`` is the North/East word
of a ``kn x n`` Dyck path and each ``row_j`` lists the ``j``-th label of every
North step in step order (a permutation of ``[n]``). With ``col(i)`` the
``x``-coordinate of the ``i``-th North step,

    area(pi) = sum_{i=1}^{n} ( k (i - 1) - col(i) ),

the number of whole lattice cells between the path and the main diagonal
``ky = x``. It does not depend on the labels.

The same value is exposed as ``path.area()`` on the object passed to a submission.
"""
from __future__ import annotations


def _encoding(path) -> str:
    if hasattr(path, "encoding"):
        return path.encoding
    return path


def area(path) -> int:
    word = _encoding(path).split("|")[0]
    n = word.count("N")
    k = word.count("E") // n
    total = 0
    x = 0
    row = 0
    for step in word:
        if step == "N":
            total += k * row - x
            row += 1
        else:
            x += 1
    return total


def statistic(path) -> int:
    return area(path)
