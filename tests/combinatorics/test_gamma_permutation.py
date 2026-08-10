from __future__ import annotations

from itertools import permutations

import pytest

from qtbench.combinatorics import (
    GammaPermutation,
    canonical_gamma_permutation,
    gamma_permutation,
    gamma_permutation_from_descent_set,
    gamma_permutation_size,
    is_gamma_permutation,
    iter_gamma_permutations,
    iter_gamma_permutations_for_descents,
)

OBJECT_COUNTS = [1, 1, 3, 9, 39, 189, 1107, 7281]


@pytest.mark.parametrize(
    "encoding",
    ["1", "1,2", "2,1,3", "3,1,2", "2,1,4,3,5", "1,2,3,4", "5,3,4,1,2"],
)
def test_valid_gamma_permutations(encoding):
    assert is_gamma_permutation(encoding)


@pytest.mark.parametrize(
    "encoding",
    [
        "",
        "2,1",          # final descent
        "1,3,2",        # final descent
        "3,2,1,4",      # double descent
        "1,2,4",        # not a permutation
        "1,1,2",
        "a,b",
    ],
)
def test_invalid_gamma_permutations(encoding):
    assert not is_gamma_permutation(encoding)
    with pytest.raises(ValueError):
        GammaPermutation(encoding)


def test_fields_of_a_single_object():
    obj = GammaPermutation("2,1,4,3,5")
    assert (obj.n, obj.size) == (5, 5)
    assert obj.values == (2, 1, 4, 3, 5)
    assert obj(1) == 2 and obj(5) == 5
    assert obj.descent_set == (1, 3)
    assert obj.descents == 2
    assert obj.maj() == 4
    assert obj.comaj() == (5 - 1) + (5 - 3)
    assert obj.inv() == 2
    assert gamma_permutation_size(obj) == gamma_permutation_size(obj.encoding) == 5
    assert obj.to_jsonable() == "2,1,4,3,5"


def test_enumeration_matches_brute_force():
    for n in range(1, 8):
        brute = sorted(
            word
            for word in permutations(range(1, n + 1))
            if (n < 2 or word[n - 2] < word[n - 1])
            and not any(word[i - 1] > word[i] > word[i + 1] for i in range(1, n - 1))
        )
        assert sorted(obj.values for obj in iter_gamma_permutations(n)) == brute
        assert len(brute) == OBJECT_COUNTS[n - 1]


def test_fibers_partition_the_objects_by_descent_count():
    for n in range(1, 8):
        seen = set()
        for k in range(1, (n + 1) // 2 + 1):
            fiber = list(iter_gamma_permutations_for_descents(n, k))
            assert all(obj.descents == k - 1 and obj.n == n for obj in fiber)
            assert all(is_gamma_permutation(obj.encoding) for obj in fiber)
            seen.update(obj.encoding for obj in fiber)
        assert len(seen) == OBJECT_COUNTS[n - 1]


def test_descent_sets_have_no_two_consecutive_and_avoid_the_end():
    for n in range(1, 8):
        for obj in iter_gamma_permutations(n):
            descent_set = obj.descent_set
            assert all(1 <= descent <= n - 2 for descent in descent_set)
            assert all(
                second - first >= 2
                for first, second in zip(descent_set, descent_set[1:])
            )


def test_from_descent_set_realizes_the_set_exactly():
    for n in range(1, 9):
        for k in range(1, (n + 1) // 2 + 1):
            for late in (False, True):
                obj = canonical_gamma_permutation(n, k, late=late)
                assert is_gamma_permutation(obj.encoding)
                assert obj.descents == k - 1
    assert gamma_permutation_from_descent_set(7, [1, 3]).encoding == "7,5,6,1,2,3,4"
    assert gamma_permutation_from_descent_set(4, []).encoding == "1,2,3,4"
    for n, k in ((1024, 1), (1024, 512), (1025, 513)):
        obj = canonical_gamma_permutation(n, k)
        assert is_gamma_permutation(obj.encoding) and obj.descents == k - 1


def test_inadmissible_descent_sets_and_fibers_are_rejected():
    with pytest.raises(ValueError):
        gamma_permutation_from_descent_set(5, [3, 4])   # consecutive
    with pytest.raises(ValueError):
        gamma_permutation_from_descent_set(5, [4])      # final descent
    with pytest.raises(ValueError):
        gamma_permutation_from_descent_set(5, [0])
    with pytest.raises(ValueError):
        canonical_gamma_permutation(4, 3)               # k > floor((n+1)/2)
    with pytest.raises(ValueError):
        next(iter_gamma_permutations_for_descents(4, 3))
    with pytest.raises(ValueError):
        next(iter_gamma_permutations(0))


def test_builder_round_trips():
    assert gamma_permutation((2, 1, 3)).encoding == "2,1,3"
    with pytest.raises(ValueError):
        gamma_permutation((2, 1))
