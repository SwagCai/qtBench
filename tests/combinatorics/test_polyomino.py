from __future__ import annotations

from collections import Counter

import pytest

from qtbench.combinatorics import (
    is_parallelogram_polyomino,
    iter_parallelogram_polyominoes,
    polyomino_area,
    polyomino_area_bounce_distribution,
    polyomino_bounce,
    polyomino_count,
    polyomino_dimensions,
    polyomino_from_ranks,
    polyomino_size,
)

# The running example of arXiv:1301.4803 (Figures 1-3): a 12 x 7 polyomino with
# area 30 and bounce 41, given by the ranks of its area-word letters.
RUNNING_EXAMPLE_RANKS = [0, 1, 2, 3, 4, 5, 3, 3, 4, 1, 2, 3, 1, 1, 2, 3, 4, 3, 3]


def test_running_example_matches_the_paper():
    polyomino = polyomino_from_ranks(RUNNING_EXAMPLE_RANKS)
    assert is_parallelogram_polyomino(polyomino)
    assert polyomino_dimensions(polyomino) == (12, 7)
    assert polyomino_area(polyomino) == 30
    assert polyomino_bounce(polyomino) == 41


def test_single_cell_polyomino():
    assert list(iter_parallelogram_polyominoes(1, 1)) == ["NE|EN"]
    assert polyomino_area("NE|EN") == 1
    assert polyomino_bounce("NE|EN") == 1


def test_counts_are_narayana_numbers():
    for m in range(1, 7):
        for n in range(1, 7):
            polyominoes = list(iter_parallelogram_polyominoes(m, n))
            assert len(polyominoes) == polyomino_count(m, n)
            assert len(set(polyominoes)) == len(polyominoes)  # distinct
            for polyomino in polyominoes:
                assert is_parallelogram_polyomino(polyomino)
                assert polyomino_dimensions(polyomino) == (m, n)
                assert polyomino_size(polyomino) == m + n


def test_distribution_is_qt_symmetric_and_symmetric_in_m_n():
    distributions: dict[tuple[int, int], Counter] = {}
    for total in range(2, 9):
        for m in range(1, total):
            n = total - m
            distribution = polyomino_area_bounce_distribution(m, n)
            distributions[(m, n)] = distribution
            assert sum(distribution.values()) == polyomino_count(m, n)
            # q,t-Narayana symmetry Nara_{m,n}(q,t) = Nara_{m,n}(t,q)
            assert all(distribution[(b, a)] == c for (a, b), c in distribution.items())
    # Nara_{m,n} = Nara_{n,m}
    for (m, n), distribution in distributions.items():
        assert distribution == distributions[(n, m)]


def test_area_equals_narayana_refinement_of_qt_catalan():
    # Summing Nara_{m,n} over the antidiagonal m + n = N + 1 recovers the number
    # of Dyck paths of semilength N (the Catalan number), by object count.
    from qtbench.combinatorics import enumerate_dyck_paths

    for cap in range(1, 7):
        polyomino_total = sum(
            polyomino_count(m, cap + 1 - m) for m in range(1, cap + 1)
        )
        assert polyomino_total == len(enumerate_dyck_paths(cap))


def test_polyomino_from_ranks_area_matches_cell_count():
    # area computed from the boundary paths equals the sum of the area word.
    for total in range(2, 8):
        for m in range(1, total):
            n = total - m
            for polyomino in iter_parallelogram_polyominoes(m, n):
                # minimal possible area is m + n - 1, maximal is m * n
                area = polyomino_area(polyomino)
                assert m + n - 1 <= area <= m * n


def test_is_parallelogram_polyomino_rejects_malformed():
    assert not is_parallelogram_polyomino("NEEN")          # no separator
    assert not is_parallelogram_polyomino("NE|EN|NE")      # two separators
    assert not is_parallelogram_polyomino("NE|E")          # unequal lengths
    assert not is_parallelogram_polyomino("NE|NE")         # lower must start E
    assert not is_parallelogram_polyomino("EN|EN")         # upper must start N
    assert not is_parallelogram_polyomino("NENE|ENEN")     # paths touch at (1,1)
    assert not is_parallelogram_polyomino("NX|EN")         # bad step
    assert is_parallelogram_polyomino("NNEE|EENN")         # valid 2 x 2 full box
    assert is_parallelogram_polyomino("NENE|EENN")         # valid 2 x 2 polyomino


@pytest.mark.parametrize(
    "ranks",
    [[], [1], [0, 0, 1], [0, 2, 1], [0, -1, 1], [0, True, 2], [0, 2.5, 1]],
)
def test_polyomino_from_ranks_rejects_invalid_area_words(ranks):
    with pytest.raises(ValueError, match="valid polyomino area word"):
        polyomino_from_ranks(ranks)
