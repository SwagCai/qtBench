"""Reference implementation of the public statistic: the G-inversion number ginv.

A Dyck graph / G-nondescent permutation object is encoded as ``b + "|" + perm``:
``b`` is the comma-separated right-endpoint vector of the graph ``G`` (edge
``(i, j)`` with ``i < j`` present iff ``j <= b_i``) and ``perm`` is the
comma-separated one-line notation of ``sigma``. The known statistic is

    ginv(G, sigma) = invTilde_G(sigma)
                   = #{ (i, j) : i < j, sigma_i > sigma_j, (sigma_j, sigma_i) in E },

i.e. the number of inversions of ``sigma`` whose two values are adjacent in ``G``.
The same value is exposed as ``obj.ginv()`` on the object passed to a submission.
"""
from __future__ import annotations


def _encoding(obj) -> str:
    if hasattr(obj, "encoding"):
        return obj.encoding
    return obj


def ginv(obj) -> int:
    b_text, perm_text = _encoding(obj).split("|")
    b = [int(piece) for piece in b_text.split(",")]
    perm = [int(piece) for piece in perm_text.split(",")]
    count = 0
    for i in range(len(perm)):
        higher = perm[i]
        for j in range(i + 1, len(perm)):
            lower = perm[j]
            if higher > lower and higher <= b[lower - 1]:
                count += 1
    return count


def statistic(obj) -> int:
    return ginv(obj)
