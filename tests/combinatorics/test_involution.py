from __future__ import annotations

from math import comb

import pytest

from qtbench.combinatorics import (
    Involution,
    canonical_involution,
    conjugate_partition,
    involution,
    involution_count,
    involution_size,
    is_involution,
    iter_involutions,
    iter_involutions_with_fixed_points,
)

INVOLUTION_NUMBERS = [1, 2, 4, 10, 26, 76, 232, 764]


@pytest.mark.parametrize(
    "encoding",
    ["1", "2,1", "1,2,3", "2,1,4,3", "3,2,1", "1,3,2,5,4"],
)
def test_valid_involutions(encoding):
    assert is_involution(encoding)


@pytest.mark.parametrize(
    "encoding",
    ["", "0", "2,3,1", "1,1", "2", "1,2,4", "a,b", "1,2,3,"],
)
def test_invalid_involutions(encoding):
    assert not is_involution(encoding)
    with pytest.raises(ValueError):
        Involution(encoding)


def test_fields_of_a_single_involution():
    pi = Involution("2,1,3,5,4")
    assert (pi.n, pi.size) == (5, 5)
    assert pi.images == (2, 1, 3, 5, 4)
    assert pi(1) == 2 and pi(3) == 3
    assert pi.fixed_points == (3,)
    assert pi.fix == 1
    assert pi.pairs == ((1, 2), (4, 5))
    assert involution_size(pi) == involution_size(pi.encoding) == 5
    assert pi.to_jsonable() == "2,1,3,5,4"


def test_rsk_shape_and_subsequence_lengths():
    # 4,3,2,1 is the nested fixed-point-free involution: one column of four cells.
    assert Involution("4,3,2,1").rsk_shape == (1, 1, 1, 1)
    # 2,1,4,3 is (1 2)(3 4): two rows of two.
    assert Involution("2,1,4,3").rsk_shape == (2, 2)
    assert Involution("1,2,3").rsk_shape == (3,)
    pi = Involution("3,2,1,4")
    assert pi.longest_increasing() == pi.rsk_shape[0]
    assert pi.longest_decreasing() == len(pi.rsk_shape)


def test_enumeration_sizes_and_fibers():
    for n, total in enumerate(INVOLUTION_NUMBERS, start=1):
        objects = list(iter_involutions(n))
        assert len(objects) == total
        assert len({obj.encoding for obj in objects}) == total
        for a in range(n % 2, n + 1, 2):
            fiber = list(iter_involutions_with_fixed_points(n, a))
            assert len(fiber) == involution_count(n, a) == comb(n, a) * _double(n - a - 1)
            assert all(obj.fix == a and obj.n == n for obj in fiber)
            assert all(is_involution(obj.encoding) for obj in fiber)


def _double(k: int) -> int:
    product = 1
    for size in range(1, k + 1, 2):
        product *= size
    return product


def test_rsk_shape_has_one_odd_column_per_fixed_point():
    """The classical RSK fact that fixes the fiber of an object by its shape."""
    for n in range(1, 8):
        for obj in iter_involutions(n):
            columns = conjugate_partition(obj.rsk_shape)
            assert sum(1 for column in columns if column % 2) == obj.fix
            assert sum(obj.rsk_shape) == n


def test_empty_fibers_are_rejected():
    with pytest.raises(ValueError):
        involution_count(4, 1)
    with pytest.raises(ValueError):
        next(iter_involutions_with_fixed_points(4, 3))
    with pytest.raises(ValueError):
        canonical_involution(5, 2)
    with pytest.raises(ValueError):
        next(iter_involutions(0))


def test_canonical_involutions_are_the_two_extremes():
    assert canonical_involution(6, 0).encoding == "2,1,4,3,6,5"
    assert canonical_involution(6, 0, nested=True).encoding == "6,5,4,3,2,1"
    assert canonical_involution(7, 3).encoding == "2,1,4,3,5,6,7"
    assert canonical_involution(7, 3, nested=True).encoding == "4,3,2,1,5,6,7"
    for n, a in ((64, 0), (64, 32), (65, 1), (65, 65)):
        consecutive = canonical_involution(n, a)
        nested = canonical_involution(n, a, nested=True)
        assert is_involution(consecutive.encoding) and consecutive.fix == a
        assert is_involution(nested.encoding) and nested.fix == a
        if a < n:
            assert consecutive.longest_decreasing() == 2
            assert nested.longest_decreasing() == n - a


def test_involution_builder_round_trips():
    assert involution((2, 1, 4, 3)).encoding == "2,1,4,3"
    with pytest.raises(ValueError):
        involution((2, 3, 1))
