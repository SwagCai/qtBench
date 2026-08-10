from __future__ import annotations

import pytest

from qtbench.combinatorics import (
    JackMatching,
    canonical_jack_matching,
    epsilon_images,
    is_jack_matching,
    iter_jack_matchings,
    iter_jack_matchings_for_partition,
    iter_partitions,
    jack_matching,
    jack_matching_count,
    jack_matching_size,
    matching_cycle_type,
    reference_images,
)

OBJECT_COUNTS = [1, 6, 45, 525, 6615]


@pytest.mark.parametrize(
    "encoding",
    ["1|2,1", "2|3,4,1,2", "2|2,1,4,3", "1,1|3,4,1,2", "2,1|4,5,6,1,2,3"],
)
def test_valid_jack_matchings(encoding):
    assert is_jack_matching(encoding)


@pytest.mark.parametrize(
    "encoding",
    [
        "",
        "2|1,2,3,4",          # not fixed-point-free
        "2|3,4,1",            # wrong length
        "1,2|3,4,1,2",        # lambda not weakly decreasing
        "2|3,4,2,1",          # not an involution
        "2,3,4,1,2",          # no separator
        "2|a,b,c,d",
    ],
)
def test_invalid_jack_matchings(encoding):
    assert not is_jack_matching(encoding)
    with pytest.raises(ValueError):
        JackMatching(encoding)


def test_fields_of_a_single_object():
    obj = JackMatching("2,1|2,1,4,3,6,5")
    assert (obj.n, obj.size) == (3, 3)
    assert obj.lam == (2, 1)
    assert obj.pairs == ((1, 2), (3, 4), (5, 6))
    # {1,2} and {4,5} stay inside a class, so this one is not bipartite
    assert not obj.is_bipartite
    assert jack_matching_size(obj) == jack_matching_size(obj.encoding) == 3
    assert obj.to_jsonable() == "2,1|2,1,4,3,6,5"


def test_epsilon_and_reference_are_bipartite_with_cycle_type_lambda():
    """``Lambda(eps, delta_lambda) = lambda``, and both matchings are bipartite."""
    for n in range(1, 8):
        for lam in iter_partitions(n):
            eps = epsilon_images(n)
            reference = reference_images(lam)
            assert matching_cycle_type(eps, reference, n) == lam
            assert matching_cycle_type(reference, eps, n) == lam
            for kind in ("epsilon", "reference"):
                obj = canonical_jack_matching(lam, kind=kind)
                assert obj.is_bipartite
            assert canonical_jack_matching(lam, kind="epsilon").epsilon_type() == tuple(
                [1] * n
            )
            assert canonical_jack_matching(lam, kind="reference").reference_type() == tuple(
                [1] * n
            )
            assert canonical_jack_matching(lam, kind="epsilon").reference_type() == lam


def test_enumeration_sizes_and_uniqueness():
    for n, total in enumerate(OBJECT_COUNTS, start=1):
        objects = list(iter_jack_matchings(n))
        assert len(objects) == total == jack_matching_count(n)
        assert len({obj.encoding for obj in objects}) == total
        assert all(is_jack_matching(obj.encoding) for obj in objects)
        assert all(obj.n == n for obj in objects)
        for lam in iter_partitions(n):
            fiber = list(iter_jack_matchings_for_partition(lam))
            assert len(fiber) == total // sum(1 for _ in iter_partitions(n))
            assert all(obj.lam == lam for obj in fiber)


def test_cycle_types_are_partitions_of_n():
    for n in range(1, 6):
        for obj in iter_jack_matchings(n):
            for kind in (obj.epsilon_type(), obj.reference_type()):
                assert sum(kind) == n
                assert list(kind) == sorted(kind, reverse=True)


def test_bipartite_exactly_when_no_pair_stays_in_a_class():
    for n in range(1, 5):
        for obj in iter_jack_matchings(n):
            within = sum(1 for i, j in obj.pairs if (i <= n) == (j <= n))
            assert obj.is_bipartite == (within == 0)
            assert within % 2 == 0  # the two classes contribute equally


def test_within_class_probe_is_as_far_from_bipartite_as_possible():
    for n, expected in ((6, 6), (7, 6), (64, 64)):
        obj = canonical_jack_matching((n,), kind="within_class")
        within = sum(1 for i, j in obj.pairs if (i <= n) == (j <= n))
        assert within == expected
        assert not obj.is_bipartite


def test_invalid_partitions_and_kinds_are_rejected():
    with pytest.raises(ValueError):
        canonical_jack_matching((1, 2))
    with pytest.raises(ValueError):
        canonical_jack_matching((2,), kind="nonsense")
    with pytest.raises(ValueError):
        next(iter_jack_matchings_for_partition(()))
    with pytest.raises(ValueError):
        next(iter_jack_matchings(0))


def test_builder_round_trips():
    assert jack_matching((2,), (3, 4, 1, 2)).encoding == "2|3,4,1,2"
    with pytest.raises(ValueError):
        jack_matching((2,), (1, 2, 3, 4))
