from __future__ import annotations

import pytest

from qtbench.combinatorics import (
    PartitionMatrixInversion,
    canonical_improper_partition_matrix,
    canonical_restricted_inversion_sequence,
    is_partition_matrix_inversion_encoding,
    iter_improper_partition_matrices,
    iter_restricted_inversion_sequences,
)


@pytest.mark.parametrize(
    "encoding",
    ["I;00,0,1", "I;0,00,1", "M;01,1,1;1,1,1", "M;1,1,1;01,1,1"],
)
def test_encodings_reject_leading_zeroes(encoding):
    assert not is_partition_matrix_inversion_encoding(encoding)


def test_source_and_target_conditions_are_enforced():
    assert is_partition_matrix_inversion_encoding("M;1,1,1;1,1,1")
    assert is_partition_matrix_inversion_encoding("I;0,0,1")
    assert not is_partition_matrix_inversion_encoding("M;1,1;1,1")
    assert not is_partition_matrix_inversion_encoding("I;0,0,0")
    assert not is_partition_matrix_inversion_encoding("I;0,1,1")


def test_public_canonical_encoders_enforce_the_family_invariants():
    assert (
        canonical_improper_partition_matrix((1, 1, 1), (1, 1, 1))
        == "M;1,1,1;1,1,1"
    )
    assert canonical_restricted_inversion_sequence((0, 0, 1)) == "I;0,0,1"
    with pytest.raises(ValueError, match="invalid improper partition matrix"):
        canonical_improper_partition_matrix((1, 1), (1, 1))
    with pytest.raises(ValueError, match="invalid improper partition matrix"):
        canonical_improper_partition_matrix((True, True, True), (1, 1, 1))
    with pytest.raises(ValueError, match="invalid restricted inversion sequence"):
        canonical_restricted_inversion_sequence((0, 0, 0))
    with pytest.raises(ValueError, match="invalid restricted inversion sequence"):
        canonical_restricted_inversion_sequence((False, 0, 1))


def test_exhaustive_small_fibers_match_by_grading():
    for n, count in {2: 1, 3: 3, 4: 7, 5: 21, 6: 67}.items():
        source = iter_improper_partition_matrices(n)
        target = iter_restricted_inversion_sequences(n)
        assert len(source) == len(target) == count
        assert sorted(obj.grading for obj in source) == sorted(obj.grading for obj in target)
        assert all(PartitionMatrixInversion(obj.encoding).n == n for obj in (*source, *target))
