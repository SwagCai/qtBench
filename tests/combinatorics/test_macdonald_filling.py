from __future__ import annotations

from collections import Counter
from math import factorial

import pytest

from qtbench.combinatorics import (
    StandardMacdonaldFilling,
    canonical_standard_macdonald_filling,
    conjugate_partition,
    is_standard_macdonald_filling,
    iter_partitions,
    iter_standard_macdonald_fillings,
    standard_macdonald_filling,
    standard_macdonald_filling_size,
)


def test_validation_and_fields():
    encoding = "3,2,1|1,5,2/4,3/6"
    assert is_standard_macdonald_filling(encoding)
    filling = StandardMacdonaldFilling(encoding)
    assert filling.shape == (3, 2, 1)
    assert filling.conjugate_shape == (3, 2, 1)
    assert filling.n == filling.size == standard_macdonald_filling_size(encoding) == 6
    assert filling.to_jsonable() == encoding


@pytest.mark.parametrize(
    "encoding",
    [
        "",
        "3,2|1,2/3,4,5",
        "3,2|1,2,3/4,4",
        "2,3|1,2/3,4,5",
        "2,2|01,2/3,4",
        "x|1",
    ],
)
def test_invalid_encodings(encoding):
    assert not is_standard_macdonald_filling(encoding)
    with pytest.raises(ValueError):
        StandardMacdonaldFilling(encoding)


def test_row_and_column_shapes_recover_classical_mahonian_statistics():
    row = StandardMacdonaldFilling("4|4,1,3,2")
    column = StandardMacdonaldFilling("1,1,1,1|2/3/1/4")
    assert row.inv() == 4 and row.maj() == 0
    assert column.inv() == 0 and column.maj() == 4


def test_builder_and_canonical_fillings():
    assert standard_macdonald_filling((2, 1), ((1, 3), (2,))).encoding == "2,1|1,3/2"
    for reverse in (False, True):
        filling = canonical_standard_macdonald_filling((8, 7, 3), reverse=reverse)
        assert is_standard_macdonald_filling(filling.encoding)


def test_enumeration_and_macdonald_qt_symmetry_through_size_seven():
    for n in range(1, 8):
        for shape in iter_partitions(n):
            fillings = list(iter_standard_macdonald_fillings(shape))
            assert len(fillings) == factorial(n)
            observed = Counter((filling.inv(), filling.maj()) for filling in fillings)
            conjugate = Counter(
                (filling.maj(), filling.inv())
                for filling in iter_standard_macdonald_fillings(conjugate_partition(shape))
            )
            assert observed == conjugate
