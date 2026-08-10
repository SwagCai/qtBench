"""Reference implementation of the public first statistic: the decorated area.

A standardly labelled rise-decorated rectangular path is encoded as
``path + "|" + labels + "|" + drise``: ``path`` is the North/East word (ending
with an East step), ``labels`` lists the label of each North step in step order
and ``drise`` lists the 1-indexed decorated rise rows. With ``k`` decorations the
path has size ``(m+k) x (n+k)``, the broken diagonal advances by ``m/n``
horizontally per undecorated row and by ``1`` per decorated row, and with
``col(i)`` the ``x``-coordinate of the ``i``-th North step and ``x_i`` the broken
diagonal at height ``i - 1``,

    a_i = x_i - col(i),   s = -min_i a_i,   area = sum_{i not in dr} floor(a_i + s).

Everything is done in integers by scaling the area word by ``n``.

The same value is exposed as ``path.area()`` on the object passed to a submission.
"""
from __future__ import annotations


def _encoding(path) -> str:
    if hasattr(path, "encoding"):
        return path.encoding
    return path


def area(path) -> int:
    word, _labels, rise_text = _encoding(path).split("|")
    decorated = {int(piece) for piece in rise_text.split(",")} if rise_text else set()
    k = len(decorated)
    m = word.count("E") - k
    n = word.count("N") - k

    scaled = []
    diagonal = 0
    x = 0
    row = 0
    for step in word:
        if step == "N":
            row += 1
            scaled.append(diagonal - n * x)
            diagonal += n if row in decorated else m
        else:
            x += 1
    shift = -min(scaled)
    return sum(
        (value + shift) // n
        for i, value in enumerate(scaled, start=1)
        if i not in decorated
    )


def statistic(path) -> int:
    return area(path)
