from __future__ import annotations

import pytest

from qtbench.combinatorics import (
    TamariParkingPair,
    canonical_tamari_parking_pair,
    intermediate_tamari_parking_pairs,
    is_tamari_parking_pair,
    iter_tamari_parking_pairs,
    tamari_parking_chain,
    tamari_parking_count,
    tamari_parking_dinv,
    tamari_parking_size,
)
from qtbench.combinatorics.type_a.tamari_parking import (
    dyck_area,
    enumerate_dyck_vectors,
    tamari_chain_length,
    tamari_up_covers,
)


def test_pair_count_is_the_trivariate_harmonics_dimension() -> None:
    # dim Harm_n = 2^n (n+1)^{n-2}, conjectured by Haiman and matched by the pairs.
    assert tamari_parking_count(1) == 1
    for n in range(2, 6):
        assert tamari_parking_count(n) == 2 ** n * (n + 1) ** (n - 2)


def test_dyck_vectors_are_counted_by_the_catalan_numbers() -> None:
    for n, catalan in enumerate((1, 2, 5, 14, 42, 132), start=1):
        assert len(enumerate_dyck_vectors(n)) == catalan


def test_chain_from_the_minimum_is_the_area() -> None:
    # The paper's remark: d(alpha_min, beta) is the usual area statistic.
    for n in range(1, 7):
        minimum = tuple(range(n))
        for beta in enumerate_dyck_vectors(n):
            assert tamari_chain_length(minimum, beta) == dyck_area(beta)


def test_the_tamari_lattice_is_not_graded() -> None:
    # 0022 is covered by 0011, and the area jumps by the length of the block, so
    # a chain length is not an area difference.
    alpha = (0, 0, 2, 2)
    beta = (0, 0, 1, 1)
    assert beta in tamari_up_covers(alpha)
    assert tamari_chain_length(alpha, beta) == 1
    assert dyck_area(beta) - dyck_area(alpha) == 2


def test_every_enumerated_pair_is_valid_and_well_formed() -> None:
    for n in range(1, 5):
        seen = set()
        for pair in iter_tamari_parking_pairs(n):
            assert is_tamari_parking_pair(pair.encoding)
            assert pair.n == n
            assert pair.beta == tuple(sorted(pair.parking_function))
            assert pair.chain() >= 0 and pair.dinv() >= 0
            assert (pair.chain() == 0) == (pair.alpha == pair.beta)
            # round-trips through the encoding
            assert TamariParkingPair(pair.encoding).encoding == pair.encoding
            assert tamari_parking_chain(pair.encoding) == pair.chain()
            assert tamari_parking_dinv(pair.encoding) == pair.dinv()
            assert tamari_parking_size(pair.encoding) == n
            seen.add(pair.encoding)
        assert len(seen) == tamari_parking_count(n)


def test_validation_rejects_malformed_encodings() -> None:
    assert not is_tamari_parking_pair("0,1")  # too few fields
    assert not is_tamari_parking_pair("1,1|0,0")  # not a parking function
    assert not is_tamari_parking_pair("0,1|1,1")  # alpha is not a Dyck path
    # beta(1,0) = (0,1) is the Tamari minimum, so only alpha = (0,1) sits below it
    assert not is_tamari_parking_pair("1,0|0,0")
    assert is_tamari_parking_pair("1,0|0,1")


def test_canonical_pair_is_valid_and_cheap_for_large_sizes() -> None:
    for n in (256, 1024):
        f = tuple(range(n))
        at_shape = canonical_tamari_parking_pair(f)
        at_minimum = canonical_tamari_parking_pair(f, at_minimum=True)
        assert at_shape.chain() == 0
        assert at_minimum.chain() == at_minimum.area()
        assert at_shape.n == at_minimum.n == n


@pytest.mark.parametrize("parking", [(), (1,), (0, 2), (-1, 0)])
def test_canonical_pair_rejects_non_parking_functions(parking) -> None:
    with pytest.raises(ValueError, match="not a parking function"):
        canonical_tamari_parking_pair(parking)


def test_intermediate_pairs_are_valid_and_strictly_between_the_extremes() -> None:
    # verified against the full Tamari order test, which is only affordable here
    for n in range(4, 9):
        pairs = intermediate_tamari_parking_pairs(n, [step * 7 + 3 for step in range(48)])
        assert len(pairs) == 4
        minimum = tuple(range(n))
        for pair in pairs:
            assert is_tamari_parking_pair(pair.encoding)
            assert pair.alpha != minimum and pair.alpha != pair.beta
    assert intermediate_tamari_parking_pairs(3, [0] * 48) == ()


def test_intermediate_pairs_are_cheap_to_build_at_gate_sizes() -> None:
    # the walk is linear in the number of steps, so large probes cost nothing to
    # build even though their chain length has no closed form
    for n in (256, 1024):
        pairs = intermediate_tamari_parking_pairs(n, [step * 5 + 1 for step in range(48)])
        assert len(pairs) == 4
        for pair in pairs:
            assert pair.n == n
            assert pair.beta == tuple(sorted(pair.parking_function))
            assert pair.alpha != tuple(range(n)) and pair.alpha != pair.beta
