"""Reference implementation of the public first statistic: the decorated area.

A standardly labelled doubly decorated Dyck path is encoded as
``path + "|" + labels + "|" + drise + "|" + dvalley``: ``path`` is the North/East
word, ``labels`` lists the label of each vertical step in step order, and
``drise``/``dvalley`` are the comma-separated 1-indexed vertical-step positions of
the decorated rises and decorated valleys (either may be empty). The area word
``a`` has ``a_i = y - x`` at the ``i``-th North step, and

    area(D) = sum of a_i over vertical steps i that are NOT decorated rises.

The same value is exposed as ``path.area()`` on the object passed to a submission.
"""
from __future__ import annotations


def _encoding(path) -> str:
    if hasattr(path, "encoding"):
        return path.encoding
    return path


def _area_word(word: str):
    area = []
    x = y = 0
    for step in word:
        if step == "N":
            area.append(y - x)
            y += 1
        else:
            x += 1
    return area


def area(path) -> int:
    word, _labels, rise_text, _valley_text = _encoding(path).split("|")
    decorated_rises = {int(piece) for piece in rise_text.split(",")} if rise_text else set()
    letters = _area_word(word)
    return sum(a for i, a in enumerate(letters, start=1) if i not in decorated_rises)


def statistic(path) -> int:
    return area(path)
