from __future__ import annotations

import pytest

from qtbench.combinatorics import (
    ShiftedSetValuedTableau,
    canonical_shifted_setvalued_tableau,
    is_shifted_setvalued_tableau_encoding,
    iter_shifted_setvalued_tableaux,
    shifted_extensions,
)


def test_canonical_encoding_and_public_features():
    encoding = "Q;3,1;3,1;1|3|5|7"
    tableau = ShiftedSetValuedTableau(encoding)
    assert is_shifted_setvalued_tableau_encoding(encoding)
    assert tableau.content == (1, 1, 1, 1)
    assert tableau.entry_count == tableau.size == 4
    assert tableau.side == "source"
    assert tableau.feature_dict()["shape"] == [3, 1]


@pytest.mark.parametrize(
    "encoding",
    [
        "Q;03,1;3,1;1|3|5|7",
        "Q;3,1;3,1;01|3|5|7",
        "Q;3,1;3,1;1|3|5|07",
        "Q;3,1;3,1;1.1|3|5|7",
        "Q;3,1;3,1;3|1|5|7",
        "P;3,1;4,1;1|3|5|7|9",
    ],
)
def test_validator_rejects_noncanonical_or_invalid_encodings(encoding):
    assert not is_shifted_setvalued_tableau_encoding(encoding)
    with pytest.raises(ValueError):
        ShiftedSetValuedTableau(encoding)


def test_extension_sign_detects_the_negative_consecutive_part_case():
    assert set(dict(shifted_extensions((3, 1))).values()) == {1}
    assert dict(shifted_extensions((3, 2))) == {
        (3, 2): 1,
        (4, 2): 1,
        (4, 3): -1,
    }


def test_corollary_fibers_match_with_and_without_negative_summand():
    for mu, content, expected in [
        ((3, 1), (1, 1, 1, 1), (32, 0, 32)),
        ((3, 2), (3, 2, 1, 1), (216, 12, 228)),
    ]:
        q_count = sum(1 for _ in iter_shifted_setvalued_tableaux("Q", mu, mu, content))
        negative = positive = 0
        for shape, sign in shifted_extensions(mu):
            count = sum(1 for _ in iter_shifted_setvalued_tableaux("P", mu, shape, content))
            if sign < 0:
                negative += count
            else:
                positive += count
        assert (q_count, negative, positive) == expected
        assert q_count + negative == positive


def test_diagonal_unprime_max_rule_is_enforced():
    with pytest.raises(ValueError):
        canonical_shifted_setvalued_tableau(
            "P", (3, 1), (3, 1), ((1, 2), (3,), (5,), (7,))
        )
