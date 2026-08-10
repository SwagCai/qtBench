from __future__ import annotations

from collections import Counter

from qtbench.combinatorics import canonical_terms, terms_to_counter


def test_canonical_terms_sort_and_drop_zeroes() -> None:
    counter = Counter({(1, 0): 2, (0, 1): 1, (3, 3): 0})
    assert canonical_terms(counter) == [[0, 1, 1], [1, 0, 2]]


def test_terms_to_counter_combines_duplicates() -> None:
    assert terms_to_counter([[1, 0, 2], [1, 0, 3]]) == Counter({(1, 0): 5})
