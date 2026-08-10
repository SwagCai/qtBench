from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from qtbench.combinatorics import (
    adversarial_alternating_sign_matrices,
    enumerate_alternating_sign_matrices,
    is_alternating_sign_matrix_encoding,
)
from qtbench.evaluation.runner import evaluate_asm_q_polynomial_checks

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems/q_statistic_discovery/asm_dpp_weight_q_stat"
EXPECTED_COUNTS = {1: 1, 2: 2, 3: 7, 4: 42, 5: 429, 6: 7436, 7: 218348}


def test_public_dpp_targets_have_the_complete_asm_counts():
    data = json.loads((PROBLEM / "data/polynomials.json").read_text())
    assert data["known_statistics"] == []
    assert {case["n"]: case["count"] for case in data["cases"]} == EXPECTED_COUNTS
    for case in data["cases"]:
        assert sum(term[-1] for term in case["terms"]) == case["count"]
    assert data["cases"][2]["terms"] == [
        [0, 1],
        [2, 1],
        [3, 1],
        [4, 1],
        [5, 1],
        [6, 1],
        [8, 1],
    ]


def test_sample_encodings_are_valid_and_disclosed_as_a_sample():
    instances = json.loads((PROBLEM / "data/instances.json").read_text())
    assert instances["instances_max_n"] == 4
    for case in instances["cases"]:
        assert case["count"] == len(case["entries"])
        assert all(is_alternating_sign_matrix_encoding(value) for value in case["entries"])
    statement = (PROBLEM / "problem.md").read_text()
    assert "is a sample, not the scored set" in statement


def test_rank_assignment_witness_matches_the_public_target():
    data = json.loads((PROBLEM / "data/polynomials.json").read_text())
    values = {}
    for case in data["cases"]:
        degrees = (
            degree for degree, count in case["terms"] for _ in range(count)
        )
        values.update(
            (matrix.encoding, degree)
            for matrix, degree in zip(
                enumerate_alternating_sign_matrices(case["n"]),
                degrees,
                strict=True,
            )
        )
    result = evaluate_asm_q_polynomial_checks(
        problem_dir=PROBLEM,
        statistic=lambda matrix: values[matrix.encoding],
    )
    assert result["passed"]


def test_constant_statistic_fails_the_exact_distribution():
    result = evaluate_asm_q_polynomial_checks(
        problem_dir=PROBLEM,
        statistic=lambda _matrix: 0,
    )
    assert not result["passed"]


def test_adversarial_probes_are_large_varied_asms():
    matrices = adversarial_alternating_sign_matrices(1024, seed=17)
    assert {matrix.n for matrix in matrices} == {256}
    assert len(matrices) == len({matrix.encoding for matrix in matrices}) == 4
    assert Counter(matrix.negative_count for matrix in matrices) == Counter({0: 3, 1: 1})
