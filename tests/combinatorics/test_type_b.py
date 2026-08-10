from __future__ import annotations

from collections import Counter
from math import comb

from qtbench.combinatorics import (
    enumerate_type_b_catalan_paths,
    is_type_b_catalan_path,
    type_b_catalan_number,
)


def test_count_is_the_type_b_catalan_number():
    for n in range(0, 8):
        paths = enumerate_type_b_catalan_paths(n)
        assert len(paths) == comb(2 * n, n) == type_b_catalan_number(n)


def test_enumerated_paths_are_valid_and_have_size_n():
    for n in range(1, 7):
        for path in enumerate_type_b_catalan_paths(n):
            assert is_type_b_catalan_path(path.steps)
            assert len(path.steps) == 2 * n
            assert path.n == n


def test_validity_rejects_paths_below_the_diagonal():
    assert not is_type_b_catalan_path("EN")  # first step east goes below y=x
    assert not is_type_b_catalan_path("NEE")  # odd length / below diagonal
    assert is_type_b_catalan_path("NN")
    assert is_type_b_catalan_path("NE")


def test_validity_rejects_nonstring_inputs():
    assert not is_type_b_catalan_path(None)
    assert not is_type_b_catalan_path(b"NE")


def test_area_matches_area_word_and_small_distribution():
    for n in range(1, 6):
        for path in enumerate_type_b_catalan_paths(n):
            assert path.area() == sum(path.area_word)
            assert path.area() >= 0
    # the n=2 area distribution is the type B q,t-Catalan q-marginal
    dist = Counter(p.area() for p in enumerate_type_b_catalan_paths(2))
    assert [dist[a] for a in range(max(dist) + 1)] == [1, 2, 1, 1, 1]


def test_area_max_is_n_squared():
    for n in range(1, 6):
        assert max(p.area() for p in enumerate_type_b_catalan_paths(n)) == n * n
