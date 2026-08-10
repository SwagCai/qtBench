from __future__ import annotations

import pytest

from qtbench.combinatorics import (
    PromotionTableau,
    canonical_promotion_tableau,
    is_promotion_shape,
    is_promotion_tableau,
    iter_promotion_tableaux_for_shape,
    promotion_modulus,
    promotion_tableau,
    promotion_tableau_size,
    rectangle_shape,
    staircase_shape,
)

COUNTS = {
    (2, 1): 2, (3, 2, 1): 16, (4, 3, 2, 1): 768,
    (2, 2): 2, (3, 3): 5, (2, 2, 2): 5, (4, 4): 14, (3, 3, 3): 42, (4, 4, 4): 462,
}


@pytest.mark.parametrize("encoding", ["1,2/3", "1,2,3/4,5/6", "1,2/3,4", "1,3/2,4"])
def test_valid_promotion_tableaux(encoding):
    assert is_promotion_tableau(encoding)


@pytest.mark.parametrize(
    "encoding",
    ["", "1", "1,2,3", "1,2/4", "2,1/3", "3,1/2", "1,2,3/4,5", "a/b"],
)
def test_invalid_promotion_tableaux(encoding):
    assert not is_promotion_tableau(encoding)
    with pytest.raises(ValueError):
        PromotionTableau(encoding)


def test_shape_classification_and_modulus():
    assert is_promotion_shape((4, 3, 2, 1)) and is_promotion_shape((3, 3, 3))
    # single rows, single columns and non-rectangular non-staircase shapes are out
    assert not is_promotion_shape((5,))
    assert not is_promotion_shape((1, 1, 1))
    assert not is_promotion_shape((3, 1))
    assert promotion_modulus((4, 3, 2, 1)) == 20            # k(k+1), twice the cells
    assert promotion_modulus((4, 4, 4)) == 12               # rc, the cells
    with pytest.raises(ValueError):
        promotion_modulus((3, 1))


def test_enumeration_counts_and_fields():
    for shape, count in COUNTS.items():
        objects = list(iter_promotion_tableaux_for_shape(shape))
        assert len(objects) == count
        assert len({obj.encoding for obj in objects}) == count
        assert all(is_promotion_tableau(obj.encoding) for obj in objects)
        assert all(obj.shape == shape and obj.n == sum(shape) for obj in objects)
        assert all(obj.modulus == promotion_modulus(shape) for obj in objects)
        rectangle = len(set(shape)) == 1
        assert all(obj.is_rectangle == rectangle for obj in objects)
        assert all(obj.is_staircase == (not rectangle) for obj in objects)


def test_fields_of_a_single_object():
    obj = PromotionTableau("1,2,3/4,5/6")
    assert obj.shape == (3, 2, 1) and obj.n == obj.size == 6
    assert obj.descent_set() == (3, 5)
    assert obj.maj() == 8
    assert obj.comaj() == (6 - 3) + (6 - 5)
    assert obj.shape_charge() == 0 * 3 + 1 * 2 + 2 * 1
    assert promotion_tableau_size(obj) == promotion_tableau_size(obj.encoding) == 6
    assert obj.to_jsonable() == "1,2,3/4,5/6"


def test_canonical_tableaux_are_valid_for_large_shapes():
    for shape in (staircase_shape(45), rectangle_shape(256, 4), rectangle_shape(2, 512)):
        for by_columns in (False, True):
            obj = canonical_promotion_tableau(shape, by_columns=by_columns)
            assert is_promotion_tableau(obj.encoding)
            assert obj.shape == shape
    with pytest.raises(ValueError):
        canonical_promotion_tableau((3, 1))
    with pytest.raises(ValueError):
        staircase_shape(1)
    with pytest.raises(ValueError):
        rectangle_shape(1, 4)


def test_builder_round_trips():
    assert promotion_tableau(((1, 2), (3, 4))).encoding == "1,2/3,4"
    with pytest.raises(ValueError):
        promotion_tableau(((2, 1), (3, 4)))
