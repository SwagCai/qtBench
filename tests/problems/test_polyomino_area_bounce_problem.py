from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from qtbench.combinatorics import (
    iter_parallelogram_polyominoes,
    polyomino_area,
    polyomino_bounce,
    polyomino_count,
)
from qtbench.evaluation import (
    adversarial_polyomino_probes,
    evaluate_polyomino_area_bounce_submission,
    load_polyomino_area_bounce_terms,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "exchanging_bijection" / "polyomino_area_bounce_exchange"
PROBLEM_ID = 4
PROBLEM_NAME = "polyomino_area_bounce_exchange"


def test_public_polynomial_file_schema():
    assert {path.name for path in (PROBLEM / "data").glob("*.json")} == {
        "instances.json",
        "polynomials.json",
        "q_equals_1.json",
    }
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    assert data["variables"] == ["q", "t"]
    assert data["statistics"] == {"q": "area", "t": "bounce"}
    for case in data["cases"]:
        assert case["count"] == polyomino_count(case["m"], case["n"])
        assert case["term_count"] == len(case["terms"])


def test_polynomials_are_the_qt_narayana_and_are_symmetric():
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    by_box = {(case["m"], case["n"]): case for case in data["cases"]}
    for (m, n), case in by_box.items():
        expected = {(a, b): c for a, b, c in case["terms"]}
        # q,t-Narayana symmetry holds for every published box (free check)
        assert expected == {(b, a): c for (a, b), c in expected.items()}
        # symmetry in the bounding box: Nara_{m,n} = Nara_{n,m}
        mirror = {(a, b): c for a, b, c in by_box[(n, m)]["terms"]}
        assert expected == mirror
        # re-derive the distribution from enumeration for the smaller boxes
        if m + n <= 9:
            actual: dict[tuple[int, int], int] = {}
            for polyomino in iter_parallelogram_polyominoes(m, n):
                key = (polyomino_area(polyomino), polyomino_bounce(polyomino))
                actual[key] = actual.get(key, 0) + 1
            assert expected == actual


def test_q_equals_1_is_the_bounce_marginal():
    polynomial_data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    specialization_data = json.loads((PROBLEM / "data" / "q_equals_1.json").read_text())
    assert specialization_data["variables"] == ["t"]
    assert specialization_data["specialization"] == {"q": 1}
    assert specialization_data["case_count"] == polynomial_data["case_count"]

    specializations = {case["case_id"]: case for case in specialization_data["cases"]}
    for case in polynomial_data["cases"]:
        expected: dict[int, int] = {}
        for _, t_exponent, coefficient in case["terms"]:
            expected[t_exponent] = expected.get(t_exponent, 0) + coefficient
        expected_terms = [[degree, expected[degree]] for degree in sorted(expected)]
        specialization = specializations[case["case_id"]]
        assert specialization["terms"] == expected_terms
        assert sum(coefficient for _, coefficient in specialization["terms"]) == case["count"]


def test_known_statistics_match_public_instances():
    spec = importlib.util.spec_from_file_location("known_stats", PROBLEM / "known_statistics.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((PROBLEM / "data" / "instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            assert module.area(entry["polyomino"]) == entry["area"]
            assert module.bounce(entry["polyomino"]) == entry["bounce"]


def test_load_polyomino_area_bounce_terms_matches_the_data_file():
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    terms = load_polyomino_area_bounce_terms(PROBLEM)
    assert set(terms) == {(case["m"], case["n"]) for case in data["cases"]}
    for case in data["cases"]:
        assert terms[(case["m"], case["n"])] == [list(term) for term in case["terms"]]


def test_identity_map_is_rejected_end_to_end():
    identity = "def forward(p):\n    return p\n\ndef inverse(p):\n    return p\n"
    result = evaluate_polyomino_area_bounce_submission(
        source=identity,
        probes=lambda: adversarial_polyomino_probes(64),
        target_terms=load_polyomino_area_bounce_terms(PROBLEM),
        timeout_seconds=2.0,
        numerical_timeout_seconds=8.0,
        max_python_bytes=32_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"
