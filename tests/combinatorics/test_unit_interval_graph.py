from __future__ import annotations

from math import comb

import pytest

from qtbench.combinatorics import (
    UnitIntervalGraphPermutation,
    canonical_unit_interval_graph_permutation,
    edges_from_b,
    is_dyck_graph_vector,
    is_unit_interval_graph_permutation,
    iter_dyck_graph_vectors,
    iter_unit_interval_graph_permutations,
    unit_interval_graph_permutation,
    unit_interval_graph_permutation_count,
    unit_interval_graph_permutation_ginv,
    unit_interval_graph_permutation_size,
)


def _catalan(n: int) -> int:
    return comb(2 * n, n) // (n + 1)


def _double_factorial_odd(n: int) -> int:
    value = 1
    for k in range(1, 2 * n, 2):
        value *= k
    return value


@pytest.mark.parametrize("n", range(1, 8))
def test_dyck_graph_count_is_catalan(n: int) -> None:
    vectors = list(iter_dyck_graph_vectors(n))
    assert len(vectors) == _catalan(n)
    assert len(set(vectors)) == len(vectors)
    assert all(is_dyck_graph_vector(b) for b in vectors)


@pytest.mark.parametrize("n", range(1, 7))
def test_object_count_is_odd_double_factorial(n: int) -> None:
    assert unit_interval_graph_permutation_count(n) == _double_factorial_odd(n)


def test_paper_example_graph_and_edges() -> None:
    # G = ([4], {(1,2),(2,3),(2,4),(3,4)}) is the Dyck graph with vector (2,4,4,4).
    b = (2, 4, 4, 4)
    assert edges_from_b(b) == frozenset({(1, 2), (2, 3), (2, 4), (3, 4)})
    obj = unit_interval_graph_permutation(b, (1, 2, 3, 4))
    assert obj.n == 4 and obj.b == b and obj.perm == (1, 2, 3, 4)
    assert obj.edges == edges_from_b(b)
    assert obj.ginv() == 0  # the identity has no inversions


def test_ginv_counts_adjacent_inversions() -> None:
    # K_3 (vector (3,3,3)): every pair is adjacent, so ginv = number of inversions.
    obj = unit_interval_graph_permutation((3, 3, 3), (3, 2, 1))
    assert obj.ginv() == 3
    # Empty graph (vector (1,2,3)): no edges, so ginv is always 0 (and only the
    # identity avoids a G-descent).
    identity = unit_interval_graph_permutation((1, 2, 3), (1, 2, 3))
    assert identity.ginv() == 0
    assert not is_unit_interval_graph_permutation("1,2,3|2,1,3")


def test_encoding_round_trip_and_size() -> None:
    for obj in iter_unit_interval_graph_permutations(4):
        assert is_unit_interval_graph_permutation(obj.encoding)
        assert UnitIntervalGraphPermutation(obj.encoding).encoding == obj.encoding
        assert unit_interval_graph_permutation_size(obj.encoding) == obj.n
        assert unit_interval_graph_permutation_size(obj) == obj.n
        assert unit_interval_graph_permutation_ginv(obj.encoding) == obj.ginv()


def test_identity_is_always_a_valid_object() -> None:
    for b in iter_dyck_graph_vectors(5):
        obj = canonical_unit_interval_graph_permutation(b)
        assert obj.perm == tuple(range(1, 6))
        assert is_unit_interval_graph_permutation(obj.encoding)


def test_invalid_vectors_and_permutations_are_rejected() -> None:
    assert not is_dyck_graph_vector(None)
    assert not is_dyck_graph_vector((True,))
    assert not is_dyck_graph_vector((1.0,))
    assert not is_dyck_graph_vector((2, 1, 3))  # not weakly increasing
    assert not is_dyck_graph_vector((1, 2, 2))  # b_3 < 3
    assert not is_unit_interval_graph_permutation("4,4,4,4|1,2,3")  # length mismatch
    assert not is_unit_interval_graph_permutation("1,2,3|1,1,2")  # not a permutation
    with pytest.raises(ValueError):
        UnitIntervalGraphPermutation("1,2,3|3,2,1")  # 3>2 non-edge is a G-descent
