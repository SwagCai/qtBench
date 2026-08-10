from __future__ import annotations

import pytest

import qtbench.combinatorics.type_a.noncrossing as noncrossing
from qtbench.combinatorics import (
    NoncrossingPartition,
    enumerate_narayana_partitions,
    enumerate_noncrossing_partitions,
    iter_noncrossing_partitions,
    narayana_number,
)


def test_narayana_counts_small_range() -> None:
    for n in range(1, 8):
        for k in range(1, n + 1):
            assert len(enumerate_narayana_partitions(n, k)) == narayana_number(n, k)


def test_enumeration_releases_recursive_memoization() -> None:
    assert len(noncrossing.enumerate_noncrossing_partitions(3)) == 5
    assert noncrossing._enumerate_blocks.cache_info().currsize == 0


def test_streaming_enumeration_matches_materialized_order() -> None:
    expected = enumerate_noncrossing_partitions(4)
    assert list(iter_noncrossing_partitions(4)) == expected
    assert noncrossing._enumerate_blocks.cache_info().currsize == 0


def test_closing_streaming_enumeration_releases_recursive_memoization() -> None:
    partitions = iter_noncrossing_partitions(4, block_count=2)
    next(partitions)
    assert noncrossing._enumerate_blocks.cache_info().currsize > 0
    partitions.close()
    assert noncrossing._enumerate_blocks.cache_info().currsize == 0


def test_streaming_enumeration_releases_memoization_after_error(monkeypatch) -> None:
    def fail(cls, blocks, *, n):
        raise RuntimeError("injected construction failure")

    monkeypatch.setattr(
        NoncrossingPartition,
        "_from_canonical_blocks",
        classmethod(fail),
    )
    with pytest.raises(RuntimeError, match="injected construction failure"):
        list(iter_noncrossing_partitions(4, block_count=2))
    assert noncrossing._enumerate_blocks.cache_info().currsize == 0


def test_internal_enumerator_reuses_canonical_block_storage() -> None:
    blocks = ((1, 3), (2,))
    partition = NoncrossingPartition._from_canonical_blocks(blocks, n=3)
    assert partition.blocks is blocks


def test_area_matches_known_small_examples() -> None:
    assert NoncrossingPartition([[1], [2], [3]]).area() == 0
    assert NoncrossingPartition([[1, 2, 3]]).area() == 0
    assert NoncrossingPartition([[1, 4], [2, 3], [5]]).area() == 1


def test_partition_features_are_json_ready() -> None:
    partition = NoncrossingPartition([[1, 4], [2, 3], [5]])
    features = partition.feature_dict()
    assert features["n"] == 5
    assert features["k"] == 3
    assert features["rgf"] == [1, 2, 2, 1, 3]


@pytest.mark.parametrize("element", [True, 1.0])
def test_partition_rejects_noninteger_elements(element) -> None:
    with pytest.raises(ValueError, match="block elements must be integers"):
        NoncrossingPartition([[element]], n=1)


@pytest.mark.parametrize("size", [True, 1.0])
def test_partition_rejects_noninteger_size(size) -> None:
    with pytest.raises(ValueError, match="n must be a nonnegative integer"):
        NoncrossingPartition([[1]], n=size)
