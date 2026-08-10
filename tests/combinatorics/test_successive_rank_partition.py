from __future__ import annotations

import pytest

from qtbench.combinatorics import (
    SuccessiveRankPartition,
    canonical_successive_rank_partition,
    is_successive_rank_partition_encoding,
    iter_successive_rank_partitions,
    successive_ranks,
)


def test_successive_ranks_only_use_diagonal_cells():
    assert successive_ranks((5, 3, 1)) == (2, 1)


@pytest.mark.parametrize(
    "encoding",
    ["S;07;2;5,3,1", "S;7;02;5,3,1", "S;7;2;05,3,1", "S;7;2;3,5,1"],
)
def test_encoding_rejects_noncanonical_or_nonpartition_text(encoding):
    assert not is_successive_rank_partition_encoding(encoding)


def test_both_classes_are_validated_and_enumerated():
    source = iter_successive_rank_partitions("source", 7, 2, 12)
    target = iter_successive_rank_partitions("target", 7, 2, 12)
    assert len(source) == len(target) == 21
    assert all(SuccessiveRankPartition(obj.encoding).side == "source" for obj in source)
    assert all(SuccessiveRankPartition(obj.encoding).side == "target" for obj in target)
    assert not is_successive_rank_partition_encoding("T;7;2;7,5")


@pytest.mark.parametrize(
    "side,modulus,residue,parts",
    [
        ("source", 7, 2, (5, 3, 1)),
        ("S", 2, 1, (1,)),
        ("S", 7, 2, (3, 5, 1)),
        ("S", 7, 2, ()),
        ("S", 7, 2, (True,)),
        ("T", 7, 2, (7, 5)),
    ],
)
def test_canonical_encoding_rejects_values_outside_the_family(
    side, modulus, residue, parts
):
    with pytest.raises(ValueError, match="invalid successive-rank partition"):
        canonical_successive_rank_partition(side, modulus, residue, parts)
