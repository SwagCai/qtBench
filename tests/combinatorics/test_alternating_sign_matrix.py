from __future__ import annotations

from qtbench.combinatorics import (
    AlternatingSignMatrix,
    alternating_sign_matrix_from_permutation,
    canonical_alternating_sign_matrix,
    enumerate_alternating_sign_matrices,
    is_alternating_sign_matrix_encoding,
)


def test_encoding_validation_is_exact_and_canonical():
    diamond = "3:0+0/+-+/0+0"
    assert is_alternating_sign_matrix_encoding(diamond)
    assert AlternatingSignMatrix(diamond).encoding == diamond
    assert not is_alternating_sign_matrix_encoding("03:0+0/+-+/0+0")
    assert not is_alternating_sign_matrix_encoding("3:0+0/+-+/0+00")
    assert not is_alternating_sign_matrix_encoding("3:0+0/+--/0+0")


def test_canonical_constructor_rejects_bad_rows_and_columns():
    assert canonical_alternating_sign_matrix([[1, 0], [0, 1]]) == "2:+0/0+"
    try:
        canonical_alternating_sign_matrix([[1, 0], [1, 0]])
    except ValueError:
        pass
    else:
        raise AssertionError("invalid column sums were accepted")


def test_monotone_triangle_enumerator_has_the_asm_counts():
    expected = {1: 1, 2: 2, 3: 7, 4: 42, 5: 429, 6: 7436}
    assert {
        n: sum(1 for _ in enumerate_alternating_sign_matrices(n)) for n in expected
    } == expected


def test_public_features_match_permutation_and_diamond_examples():
    reverse = alternating_sign_matrix_from_permutation((2, 1, 0))
    diamond = AlternatingSignMatrix("3:0+0/+-+/0+0")
    assert (reverse.negative_count, reverse.inversion_number) == (0, 3)
    assert (diamond.negative_count, diamond.inversion_number) == (1, 2)
    assert diamond.feature_dict()["rows"] == [[0, 1, 0], [1, -1, 1], [0, 1, 0]]
