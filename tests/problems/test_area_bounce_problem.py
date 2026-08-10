from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from qtbench.combinatorics import dyck_area, dyck_bounce, enumerate_dyck_paths
from qtbench.evaluation import (
    adversarial_dyck_probes,
    evaluate_area_bounce_submission,
    load_area_bounce_terms,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "exchanging_bijection" / "dyck_area_bounce_exchange"


def test_polynomials_are_the_qt_catalan_and_are_symmetric():
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    assert data["variables"] == ["q", "t"]
    assert data["problem_id"] == 2
    for case in data["cases"]:
        expected = {(a, b): c for a, b, c in case["terms"]}
        # the q,t-Catalan symmetry holds for every published size (free check)
        assert expected == {(b, a): c for (a, b), c in expected.items()}
        # re-derive the distribution from enumeration for the smaller sizes
        if case["n"] <= 10:
            actual: dict[tuple[int, int], int] = {}
            for path in enumerate_dyck_paths(case["n"]):
                key = (dyck_area(path), dyck_bounce(path))
                actual[key] = actual.get(key, 0) + 1
            assert expected == actual


def test_known_statistics_match_public_instances():
    spec = importlib.util.spec_from_file_location("known_stats", PROBLEM / "known_statistics.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((PROBLEM / "data" / "instances.json").read_text())
    for case in data["cases"][:6]:
        for entry in case["entries"]:
            assert module.area(entry["path"]) == entry["area"]
            assert module.bounce(entry["path"]) == entry["bounce"]


def test_load_area_bounce_terms_matches_the_data_file():
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    terms = load_area_bounce_terms(PROBLEM)
    assert set(terms) == {case["n"] for case in data["cases"]}
    for case in data["cases"]:
        assert terms[case["n"]] == [list(term) for term in case["terms"]]


def test_identity_map_is_rejected_end_to_end():
    identity = "def forward(path):\n    return path\n\ndef inverse(path):\n    return path\n"
    result = evaluate_area_bounce_submission(
        source=identity,
        probes=lambda: adversarial_dyck_probes(64),
        target_terms=load_area_bounce_terms(PROBLEM),
        timeout_seconds=2.0,
        numerical_timeout_seconds=8.0,
        max_python_bytes=32_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"
