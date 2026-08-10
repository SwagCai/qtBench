"""Reference implementation of the public first statistic: the selection size.

An object is a pair ``(p, S)`` with ``p`` a gamma-parking function and ``S`` a
subset of its area cells, encoded as ``bottom|top|word|selected``. The public
statistic is

    sel(p, S) = #S,

the number of chosen area cells, which grades ``u`` in the target. The same
value is exposed as ``selection.selected_count()`` on the object passed to a
submission.
"""
from __future__ import annotations


def _encoding(selection) -> str:
    if hasattr(selection, "encoding"):
        return selection.encoding
    return selection


def sel(selection) -> int:
    selected_text = _encoding(selection).split("|")[3]
    if not selected_text:
        return 0
    return len(selected_text.split(","))


def statistic(selection) -> int:
    return sel(selection)
