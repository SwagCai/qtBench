from __future__ import annotations

from fractions import Fraction

import pytest

from qtbench.combinatorics import (
    LabelledRectangularPath,
    canonical_labelled_rectangular_path,
    is_labelled_rectangular_path,
    iter_labelled_rectangular_paths,
    labelled_rectangular_path_area,
    labelled_rectangular_path_count,
    labelled_rectangular_path_size,
)


def test_area_word_matches_the_undecorated_paper_example() -> None:
    # Figure 1 of arXiv:2206.00131: a 7x9 rectangular path with area word
    # (0, -11/9, -4/9, 1/3, -8/9, -1/9, 2/3, -5/9, 2/9), shift 11/9 and area 5.
    encoding = "NEENNNEENNNEENNE|1,2,3,4,5,6,7,8,9|"
    assert is_labelled_rectangular_path(encoding)
    path = LabelledRectangularPath(encoding)
    assert (path.m, path.n, path.k) == (7, 9, 0)
    assert path.area_word == (
        Fraction(0), Fraction(-11, 9), Fraction(-4, 9), Fraction(1, 3), Fraction(-8, 9),
        Fraction(-1, 9), Fraction(2, 3), Fraction(-5, 9), Fraction(2, 9),
    )
    assert path.shift == Fraction(11, 9)
    assert path.area() == 5


def test_area_matches_the_decorated_paper_example() -> None:
    # Figure 6 of arXiv:2206.00131: a 6x9 decorated rectangular Dyck path with
    # decorated rises {3, 6, 7} (so m = 3, n = 6, k = 3) and area 3.
    encoding = "NNNENENNNEENNEE|1,2,3,4,5,6,7,8,9|3,6,7"
    assert is_labelled_rectangular_path(encoding)
    path = LabelledRectangularPath(encoding)
    assert (path.m, path.n, path.k) == (3, 6, 3)
    assert sorted(path.rises) == [2, 3, 6, 7, 9]
    assert path.shift == 0  # weakly above the broken diagonal
    assert path.area() == 3


def test_every_enumerated_object_is_valid_and_well_formed() -> None:
    for m, n, k in ((1, 1, 1), (1, 2, 1), (2, 1, 1), (1, 3, 1), (1, 1, 2)):
        seen = set()
        for path in iter_labelled_rectangular_paths(m, n, k):
            assert is_labelled_rectangular_path(path.encoding)
            assert (path.m, path.n, path.k) == (m, n, k)
            assert path.path.endswith("E")
            assert path.decorated_rises <= path.rises
            assert path.area() >= 0
            # round-trips through the encoding
            assert LabelledRectangularPath(path.encoding).encoding == path.encoding
            assert labelled_rectangular_path_area(path.encoding) == path.area()
            assert labelled_rectangular_path_size(path.encoding) == m + n + 2 * k
            seen.add(path.encoding)
        assert len(seen) == labelled_rectangular_path_count(m, n, k)


def test_validation_rejects_malformed_encodings() -> None:
    assert not is_labelled_rectangular_path("NNEE|1,2")  # too few fields
    assert not is_labelled_rectangular_path("NNEEN|1,2,3|")  # does not end with East
    assert not is_labelled_rectangular_path("NNEE|1,1|")  # labels not a permutation
    assert not is_labelled_rectangular_path("NNEE|2,1|")  # labels decrease along the run
    assert not is_labelled_rectangular_path("NENE|1,2|2")  # row 2 is not a rise
    assert not is_labelled_rectangular_path("NNEE|1,2|2,3")  # too many decorations for the box
    # the decoration list is canonical: no repeats, increasing order
    assert not is_labelled_rectangular_path("NNEE|1,2|2,2")
    assert not is_labelled_rectangular_path("NNNEEE|1,2,3|3,2")
    assert is_labelled_rectangular_path("NNNEEE|1,2,3|2,3")
    assert is_labelled_rectangular_path("NNEE|1,2|2")


def test_canonical_object_is_valid_and_cheap_for_large_shapes() -> None:
    for height, width, k in ((512, 512, 4), (256, 768, 1)):
        shape = "N" * height + "E" * width
        path = canonical_labelled_rectangular_path(shape, k)
        assert is_labelled_rectangular_path(path.encoding)
        assert (path.m, path.n, path.k) == (width - k, height - k, k)
        assert path.area() > 0


@pytest.mark.parametrize("path,k", [("NEX", 0), ("NE", -1), ("EN", 0)])
def test_canonical_builder_rejects_invalid_path_or_decoration_count(path, k) -> None:
    with pytest.raises(ValueError):
        canonical_labelled_rectangular_path(path, k)
