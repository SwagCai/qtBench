from __future__ import annotations

import pytest

from qtbench.combinatorics import (
    MultiLabelledDyckPath,
    canonical_multi_labelled_dyck_path,
    is_multi_labelled_dyck_path,
    iter_multi_labelled_dyck_paths,
    multi_labelled_dyck_area,
    multi_labelled_dyck_count,
    multi_labelled_dyck_size,
)


def test_single_object_when_n_is_one() -> None:
    for k in range(1, 5):
        assert multi_labelled_dyck_count(1, k) == 1


def test_smallest_nontrivial_fiber_matches_the_hand_count() -> None:
    # n = 2, k = 1: the two 2x2 Dyck paths. NNEE has no East step between the two
    # North steps, so both rows must increase (1 object, area 1); NENE has one, so
    # at most one of the two rows may descend (3 objects, area 0).
    paths = list(iter_multi_labelled_dyck_paths(2, 1))
    assert len(paths) == 4
    assert sorted(path.area() for path in paths) == [0, 0, 0, 1]


def test_every_enumerated_object_is_valid_and_well_formed() -> None:
    for k in (1, 2):
        for n in range(1, 4):
            seen = set()
            for path in iter_multi_labelled_dyck_paths(n, k):
                assert is_multi_labelled_dyck_path(path.encoding)
                assert path.n == n and path.k == k
                assert len(path.rows) == k + 1
                assert path.area() >= 0
                assert all(
                    descents <= gap for descents, gap in zip(path.descents, path.gaps)
                )
                # round-trips through the encoding
                assert MultiLabelledDyckPath(path.encoding).encoding == path.encoding
                assert multi_labelled_dyck_area(path.encoding) == path.area()
                assert multi_labelled_dyck_size(path.encoding) == n
                seen.add(path.encoding)
            assert len(seen) == multi_labelled_dyck_count(n, k)


def test_area_is_the_rectangular_area_of_the_shape() -> None:
    # The highest path N^n E^{kn} has col(i) = 0, hence area = k * binom(n, 2).
    for k in (1, 2, 3):
        for n in (1, 4, 7):
            shape = "N" * n + "E" * (k * n)
            path = canonical_multi_labelled_dyck_path(shape, k)
            assert path.area() == k * n * (n - 1) // 2
            assert path.area_word == tuple(k * (i - 1) for i in range(1, n + 1))


def test_validation_rejects_malformed_encodings() -> None:
    assert not is_multi_labelled_dyck_path("NENE|1,2")  # too few label rows
    assert not is_multi_labelled_dyck_path("ENNE|1,2|1,2")  # below the diagonal
    assert not is_multi_labelled_dyck_path("NENE|1,1|1,2")  # not a permutation
    assert not is_multi_labelled_dyck_path("NNEE|2,1|1,2")  # a descent with no East step
    assert not is_multi_labelled_dyck_path("NENE|2,1|2,1")  # two descents, one East step
    assert is_multi_labelled_dyck_path("NENE|2,1|1,2")


def test_canonical_labelling_is_valid_and_cheap_for_large_paths() -> None:
    for k in (1, 3):
        for shape in ("N" * 512 + "E" * (512 * k), ("N" + "E" * k) * 512):
            path = canonical_multi_labelled_dyck_path(shape, k)
            assert is_multi_labelled_dyck_path(path.encoding)
            assert path.n == 512 and path.k == k


@pytest.mark.parametrize("path,k", [("NEX", 1), ("NNEE", 2), ("NE", 0)])
def test_canonical_builder_rejects_invalid_path_or_label_count(path, k) -> None:
    with pytest.raises(ValueError):
        canonical_multi_labelled_dyck_path(path, k)
