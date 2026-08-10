from __future__ import annotations

from math import comb

import pytest

from qtbench.combinatorics import (
    UnitIntervalGraphTableau,
    canonical_unit_interval_graph_tableau,
    edges_from_b,
    is_unit_interval_graph_tableau,
    iter_dyck_graph_vectors,
    iter_uig_tableaux_for_vector,
    iter_unit_interval_graph_tableaux,
    unit_interval_graph_tableau,
    unit_interval_graph_tableau_count,
    unit_interval_graph_tableau_size,
)


def _catalan(n: int) -> int:
    return comb(2 * n, n) // (n + 1)


def _involutions(n: int) -> int:
    previous, current = 1, 1
    for k in range(2, n + 1):
        previous, current = current, current + (k - 1) * previous
    return current


@pytest.mark.parametrize("n", range(1, 8))
def test_object_count_is_catalan_times_involutions(n: int) -> None:
    # The fiber of one graph is the disjoint union of the SYT(lambda), and
    # sum_lambda f^lambda is the number of involutions of S_n.
    assert unit_interval_graph_tableau_count(n) == _catalan(n) * _involutions(n)
    assert len(list(iter_uig_tableaux_for_vector(tuple([n] * n)))) == _involutions(n)


def test_paper_example_graph_with_a_tableau() -> None:
    # G = ([4], {(1,2),(2,3),(2,4),(3,4)}) paired with the tableau 123/4.
    b = (2, 4, 4, 4)
    obj = unit_interval_graph_tableau(b, ((1, 2, 3), (4,)))
    assert obj.encoding == "2,4,4,4|1,2,3/4"
    assert obj.n == 4 and obj.b == b and obj.shape == (3, 1)
    assert obj.edges == edges_from_b(b)
    assert obj.cells == ((1, 1), (1, 2), (1, 3), (2, 1))
    assert obj.descent_set() == (3,) and obj.maj() == 3 and obj.comaj() == 1


def test_descent_statistics_at_the_extreme_shapes() -> None:
    b = (5, 5, 5, 5, 5)
    row = canonical_unit_interval_graph_tableau(b, (5,))
    column = canonical_unit_interval_graph_tableau(b, (1, 1, 1, 1, 1))
    assert row.descent_set() == () and row.maj() == 0
    assert column.descent_set() == (1, 2, 3, 4) and column.maj() == 10


def test_encoding_round_trip_and_size() -> None:
    for obj in iter_unit_interval_graph_tableaux(4):
        assert is_unit_interval_graph_tableau(obj.encoding)
        assert UnitIntervalGraphTableau(obj.encoding).encoding == obj.encoding
        assert unit_interval_graph_tableau_size(obj.encoding) == obj.n
        assert unit_interval_graph_tableau_size(obj) == obj.n


def test_superstandard_tableaux_are_valid_objects() -> None:
    for b in iter_dyck_graph_vectors(4):
        for lam in ((4,), (2, 2), (2, 1, 1), (1, 1, 1, 1)):
            for by_columns in (False, True):
                obj = canonical_unit_interval_graph_tableau(b, lam, by_columns=by_columns)
                assert is_unit_interval_graph_tableau(obj.encoding)
                assert obj.shape == lam


def test_invalid_pairs_are_rejected() -> None:
    assert not is_unit_interval_graph_tableau("2,1,3|1,2/3")   # b not weakly increasing
    assert not is_unit_interval_graph_tableau("1,2,3|2,3/1")   # column not increasing
    assert not is_unit_interval_graph_tableau("1,2,3|2,1/3")   # row not increasing
    assert not is_unit_interval_graph_tableau("1,2|1,2/3")     # |b| != number of cells
    assert not is_unit_interval_graph_tableau("1,2,3|1/2,3")   # shape not a partition
    with pytest.raises(ValueError):
        UnitIntervalGraphTableau("1,2,3|1,2,2")
