from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from qtbench.combinatorics import NoncrossingPartition, narayana_number

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "t_statistic_discovery" / "nc_area_qt_narayana_second_stat"
PROBLEM_ID = 1
PROBLEM_NAME = "nc_area_qt_narayana_second_stat"


def test_public_polynomial_file_schema() -> None:
    assert {path.name for path in (PROBLEM / "data").glob("*.json")} == {
        "instances.json",
        "polynomials.json",
        "q_equals_1.json",
    }
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text(encoding="utf-8"))
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    assert data["variables"] == ["q", "t"]
    assert data["public_max_n"] == 10
    assert data["case_count"] == 55
    for case in data["cases"]:
        assert case["count"] == narayana_number(case["n"], case["k"])
        assert case["term_count"] == len(case["terms"])
        assert "sha256" not in case


def test_q_equals_1_specializes_public_polynomials() -> None:
    polynomial_data = json.loads((PROBLEM / "data" / "polynomials.json").read_text(encoding="utf-8"))
    specialization_data = json.loads((PROBLEM / "data" / "q_equals_1.json").read_text(encoding="utf-8"))
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
        assert specialization["n"] == case["n"]
        assert specialization["k"] == case["k"]
        assert specialization["count"] == case["count"]
        assert specialization["terms"] == expected_terms
        assert sum(coefficient for _, coefficient in specialization["terms"]) == case["count"]


def test_public_instance_file_has_no_target_statistic() -> None:
    data = json.loads((PROBLEM / "data" / "instances.json").read_text(encoding="utf-8"))
    first_entry = data["cases"][0]["entries"][0]
    assert set(first_entry) == {"partition", "area"}
    assert "target" not in first_entry
    assert "bounce" not in first_entry
    assert "rgf" not in first_entry


def test_known_statistic_file_matches_public_instances() -> None:
    spec = importlib.util.spec_from_file_location("known_statistic", PROBLEM / "known_statistic.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    data = json.loads((PROBLEM / "data" / "instances.json").read_text(encoding="utf-8"))
    for case in data["cases"]:
        for entry in case["entries"]:
            partition = NoncrossingPartition(entry["partition"], n=case["n"])
            assert module.statistic(partition) == entry["area"]
