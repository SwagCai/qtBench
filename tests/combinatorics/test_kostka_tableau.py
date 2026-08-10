from __future__ import annotations

import pytest

from qtbench.combinatorics import (
    KostkaStandardTableau,
    canonical_kostka_standard_tableau,
    conjugate_partition,
    is_partition,
    is_kostka_standard_tableau,
    iter_kostka_standard_tableaux,
    iter_partitions,
    kostka_standard_tableau_count,
    kostka_tableau_maj,
    kostka_tableau_size,
)


def test_partitions_and_conjugation():
    assert iter_partitions(4) == ((4,), (3, 1), (2, 2), (2, 1, 1), (1, 1, 1, 1))
    for n in range(1, 9):
        for mu in iter_partitions(n):
            assert sum(conjugate_partition(mu)) == n
            assert conjugate_partition(conjugate_partition(mu)) == mu


@pytest.mark.parametrize("value", [None, 3, {1: 1}, (True,), (1.0,), (1, 2)])
def test_partition_predicate_rejects_invalid_inputs(value):
    assert not is_partition(value)


@pytest.mark.parametrize("n", range(1, 8))
def test_enumeration_matches_the_hook_length_formula(n):
    for lam in iter_partitions(n):
        tableaux = list(iter_kostka_standard_tableaux(lam, (n,)))
        assert len(tableaux) == kostka_standard_tableau_count(lam)
        assert len({tableau.encoding for tableau in tableaux}) == len(tableaux)
        for tableau in tableaux:
            assert is_kostka_standard_tableau(tableau.encoding)
            assert tableau.shape == lam
            assert tableau.n == n == kostka_tableau_size(tableau.encoding)
    # sum_lambda f^lambda is the number of involutions in S_n
    involutions = [1, 1, 2, 4, 10, 26, 76, 232]
    assert sum(kostka_standard_tableau_count(lam) for lam in iter_partitions(n)) == involutions[n]


def test_encoding_round_trip_and_descents():
    tableau = KostkaStandardTableau("2,1|1,2/3")
    assert tableau.mu == (2, 1)
    assert tableau.shape == (2, 1)
    assert tableau.rows == ((1, 2), (3,))
    assert tableau.cells == ((1, 1), (1, 2), (2, 1))
    assert tableau.descent_set() == (2,)
    assert tableau.maj() == 2 == kostka_tableau_maj("2,1|1,2/3")
    assert tableau.comaj() == 1
    assert tableau.to_jsonable() == tableau.encoding


@pytest.mark.parametrize(
    "encoding",
    [
        "2,2|2,3/1,4",     # column 1 is not increasing
        "2,1|2,1/3",       # row 1 is not increasing
        "2,1|1,2/4",       # entries are not 1..n
        "2,2|1,2/3",       # |mu| = 4 but T has 3 cells
        "1,2|1,2/3",       # mu is not weakly decreasing
        "2,1|1/2,3",       # the shape is not a partition
        "2,1",             # missing the tableau
    ],
)
def test_invalid_encodings_are_rejected(encoding):
    # mu and lambda are independent partitions of the same n, so "3|1,2/3" is valid
    assert is_kostka_standard_tableau("3|1,2/3")
    assert not is_kostka_standard_tableau(encoding)
    with pytest.raises(ValueError):
        KostkaStandardTableau(encoding)


@pytest.mark.parametrize("n", [1, 2, 5, 17, 64])
def test_canonical_tableaux_are_valid_with_extreme_descent_sets(n):
    for lam in iter_partitions(n) if n <= 5 else [(n,), tuple([1] * n), (n - 1, 1)]:
        mu = tuple(sorted(lam, reverse=True))
        by_rows = canonical_kostka_standard_tableau(lam, mu)
        by_columns = canonical_kostka_standard_tableau(lam, mu, by_columns=True)
        assert is_kostka_standard_tableau(by_rows.encoding)
        assert is_kostka_standard_tableau(by_columns.encoding)
        # the row-superstandard tableau descends exactly at the row boundaries
        boundaries = []
        total = 0
        for part in lam[:-1]:
            total += part
            boundaries.append(total)
        assert by_rows.descent_set() == tuple(boundaries)
        # the column-superstandard tableau ascends exactly at the column boundaries
        conjugate = conjugate_partition(lam)
        ascents = []
        total = 0
        for part in conjugate[:-1]:
            total += part
            ascents.append(total)
        assert by_columns.descent_set() == tuple(
            i for i in range(1, n) if i not in set(ascents)
        )
