from __future__ import annotations

import pytest

from qtbench.combinatorics import (
    LabelledParallelogramPolyomino,
    canonical_standard_labelling,
    is_st_labelled_polyomino,
    iter_st_labelled_polyominoes,
    st_labelled_polyomino_area,
    st_labelled_polyomino_count,
    st_labelled_polyomino_size,
)

# The 11 x 7 labelled polyomino from Figure (fig:polyomino) of arXiv:2202.05706,
# whose labelled area is stated to be 10.
PAPER_UPPER = "NNNEENEEENEEENNEEE"
PAPER_LOWER = "EEENEENNEENEEENENN"
PAPER_LABELS = "4,7,8,3,1,3,6,5,2,7,1,4,3,7,9,1,3"
PAPER_ENCODING = f"{PAPER_UPPER}|{PAPER_LOWER}|{PAPER_LABELS}"


def test_paper_example_area_is_ten():
    # The figure is a general (non-standard) labelling illustrating the area rule.
    assert st_labelled_polyomino_area(PAPER_ENCODING) == 10
    assert LabelledParallelogramPolyomino(PAPER_ENCODING, validate=False).area() == 10


def test_paper_example_structure():
    p = LabelledParallelogramPolyomino(PAPER_ENCODING, validate=False)
    assert (p.m, p.n) == (11, 7)
    assert p.size == 17 == len(p.labelled_cells)
    # exactly m green-or-black and n red-or-black cells; one shared black cell
    assert len(p.green_cells) == p.m and len(p.red_cells) == p.n
    assert (0, 0) in p.green_cells and (0, 0) in p.red_cells


@pytest.mark.parametrize(
    "m,n,expected",
    [(1, 1, 1), (2, 2, 5), (2, 3, 17), (3, 2, 17), (3, 3, 146), (2, 4, 49), (3, 4, 922)],
)
def test_counts(m, n, expected):
    assert st_labelled_polyomino_count(m, n) == expected


def test_enumeration_is_valid_and_monotone():
    for m, n in [(2, 2), (2, 3), (3, 3), (2, 5)]:
        seen = set()
        for polyomino in iter_st_labelled_polyominoes(m, n):
            encoding = polyomino.encoding
            assert encoding not in seen  # distinct objects
            seen.add(encoding)
            assert is_st_labelled_polyomino(encoding)
            # labels are exactly [m+n-1]
            assert sorted(polyomino.label.values()) == list(range(1, m + n))
            # columns strictly increase upward, rows strictly decrease left to right
            for _x, pairs in polyomino.columns.items():
                labels = [label for _y, label in pairs]
                assert labels == sorted(labels) and len(set(labels)) == len(labels)
            for _y, pairs in polyomino.rows.items():
                labels = [label for _x, label in pairs]
                assert labels == sorted(labels, reverse=True)


def test_validator_rejects_malformed_encodings():
    assert not is_st_labelled_polyomino("NE|EN")  # missing labels field
    assert not is_st_labelled_polyomino("NE|EN|2")  # label not in [1]
    assert not is_st_labelled_polyomino("NENE|EENN|1,2,3")  # row 0 not decreasing left to right
    assert not is_st_labelled_polyomino("EN|NE|1")  # upper must start N, lower start E
    assert is_st_labelled_polyomino("NE|EN|1")


def test_canonical_labelling_is_valid_and_efficient_for_large_boxes():
    # A near-linear canonical labelling of a large shape (used for gate probes).
    upper = "N" * 200 + "E" * 200
    lower = "E" * 200 + "N" * 200
    obj = canonical_standard_labelling(upper, lower)
    assert is_st_labelled_polyomino(obj.encoding)
    assert st_labelled_polyomino_size(obj) == 400
    assert obj.area() >= 0


@pytest.mark.parametrize(
    "upper,lower",
    [("EN", "NE"), ("NE", "NE"), ("NX", "EN")],
)
def test_canonical_labelling_rejects_invalid_shapes(upper, lower):
    with pytest.raises(ValueError, match="not a parallelogram-polyomino shape"):
        canonical_standard_labelling(upper, lower)
