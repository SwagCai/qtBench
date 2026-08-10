from __future__ import annotations

import pytest

from qtbench.combinatorics import (
    DecoratedLabelledDyckPath,
    canonical_decorated_labelled_dyck_path,
    decorated_labelled_dyck_area,
    decorated_labelled_dyck_count,
    decorated_dyck_size,
    is_decorated_labelled_dyck_path,
    iter_decorated_labelled_dyck_paths,
)


def test_standard_labelling_count_is_parking_functions_for_no_decorations() -> None:
    # |LD(n)^{*0,•0}| = number of parking functions of size n = (n+1)^{n-1}.
    for n in range(1, 7):
        assert decorated_labelled_dyck_count(n, 0, 0) == (n + 1) ** (n - 1)


def test_fibers_are_nonempty_exactly_when_k_plus_l_at_most_n_minus_1() -> None:
    for n in range(1, 6):
        for k in range(0, n + 1):
            for l in range(0, n + 1):
                count = decorated_labelled_dyck_count(n, k, l)
                if k + l <= n - 1:
                    assert count > 0
                else:
                    assert count == 0


def test_every_enumerated_object_is_valid_and_well_formed() -> None:
    for n in range(1, 5):
        for k in range(0, n):
            for l in range(0, n - k):
                if n - k - l < 1:
                    continue
                seen = set()
                for path in iter_decorated_labelled_dyck_paths(n, k, l):
                    assert is_decorated_labelled_dyck_path(path.encoding)
                    assert path.n == n and path.k == k and path.l == l
                    assert path.decorated_rises <= path.rises
                    assert path.decorated_valleys <= path.contractible_valleys
                    assert path.area() >= 0
                    # round-trips through the encoding
                    assert DecoratedLabelledDyckPath(path.encoding).encoding == path.encoding
                    assert decorated_labelled_dyck_area(path.encoding) == path.area()
                    assert decorated_dyck_size(path.encoding) == n
                    seen.add(path.encoding)
                assert len(seen) == decorated_labelled_dyck_count(n, k, l)


def test_area_word_and_decorated_area_match_the_paper_convention() -> None:
    # Figure 1 (left) of arXiv:2312.03956 has area word 0,1,1,1,2,3,2,0 and
    # decorated rises {2,6}, so area = 0+1+1+2+2+0 = 6. The decorated area depends
    # only on the shape and the decorated rises, so any valid labelling reproduces
    # it; the North/East word below is the shape of that area word.
    encoding = "NNENENNNEENEEENE|1,2,3,4,5,6,7,8|2,6|"
    assert is_decorated_labelled_dyck_path(encoding)
    obj = DecoratedLabelledDyckPath(encoding)
    assert obj.area_word == (0, 1, 1, 1, 2, 3, 2, 0)
    assert obj.rises == frozenset({2, 5, 6})
    assert obj.area() == 6


def test_validation_rejects_malformed_encodings() -> None:
    assert not is_decorated_labelled_dyck_path("NE|1|")  # too few fields
    assert not is_decorated_labelled_dyck_path("EN|1||")  # not a Dyck path
    assert not is_decorated_labelled_dyck_path("NNEE|2,1||")  # labels not increasing on the rise
    assert not is_decorated_labelled_dyck_path("NE|1|1|")  # step 1 is not a rise
    assert not is_decorated_labelled_dyck_path("NNEE|1,2|2|1")  # a decorated non-valley
    assert is_decorated_labelled_dyck_path("NNEE|1,2|2|")  # a valid decorated rise


def test_contractible_valley_uses_labels_for_single_east_gap() -> None:
    # Path NENE: step 2 is a valley with one East step before it. It is
    # contractible iff the label below is smaller than the valley's label.
    increasing = DecoratedLabelledDyckPath("NENE|1,2||", validate=False)
    assert increasing.valleys == frozenset({2})
    assert increasing.contractible_valleys == frozenset({2})
    decreasing = DecoratedLabelledDyckPath("NENE|2,1||", validate=False)
    assert decreasing.valleys == frozenset({2})
    assert decreasing.contractible_valleys == frozenset()


@pytest.mark.parametrize(
    "path,k,l",
    [("NEX", 0, 0), ("NE", -1, 0), ("NE", 0, -1)],
)
def test_canonical_builder_rejects_invalid_path_or_decoration_counts(path, k, l) -> None:
    with pytest.raises(ValueError):
        canonical_decorated_labelled_dyck_path(path, k, l)
