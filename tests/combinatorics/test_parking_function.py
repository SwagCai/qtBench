from __future__ import annotations

from collections import Counter

import pytest

from qtbench.combinatorics import (
    ParkingFunction,
    canonical_parking_function,
    is_parking_function_word,
    iter_parking_functions,
    parking_function,
    parking_function_size,
)


def test_validation_and_fields():
    obj = ParkingFunction("2,0,1,0")
    assert is_parking_function_word(obj.encoding)
    assert obj.values == (2, 0, 1, 0)
    assert obj.shape == (0, 0, 1, 2)
    assert obj.n == obj.size == parking_function_size(obj.encoding) == 4
    assert obj.to_jsonable() == obj.encoding


@pytest.mark.parametrize("encoding", ["", "00", "1", "0,2", "-1,0", "a,0"])
def test_invalid_encodings(encoding):
    assert not is_parking_function_word(encoding)
    with pytest.raises(ValueError):
        ParkingFunction(encoding)


def test_builder_and_canonical_objects():
    assert parking_function((0, 0, 2)).encoding == "0,0,2"
    for reverse in (False, True):
        assert is_parking_function_word(canonical_parking_function(512, reverse=reverse).encoding)


def test_counts_and_area_dinv_symmetry_through_size_six():
    for n in range(1, 7):
        objects = list(iter_parking_functions(n))
        assert len(objects) == (n + 1) ** (n - 1)
        distribution = Counter((obj.area(), obj.dinv()) for obj in objects)
        assert distribution == Counter({(dinv, area): count for (area, dinv), count in distribution.items()})
