from __future__ import annotations

import json
from pathlib import Path

from qtbench.combinatorics import is_shifted_setvalued_tableau_encoding
from qtbench.evaluation.admission import (
    adversarial_shifted_pq_probes,
    evaluate_shifted_pq_bijection,
    load_shifted_pq_cases,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems/exchanging_bijection/shifted_setvalued_pq_weight_bijection"


def rank_maps(cases):
    forward = {}
    inverse = {}
    for case in cases.values():
        for source, target in zip(sorted(case["source"]), sorted(case["target"]), strict=True):
            forward[source] = target
            inverse[target] = source
    return forward, inverse


def test_public_cases_include_a_nonempty_negative_summand():
    cases = load_shifted_pq_cases(PROBLEM)
    assert len(cases) == 7
    assert len(cases["f06"]["source"]) == len(cases["f06"]["target"]) == 228
    assert sum(value.startswith("P;3,2;4,3;") for value in cases["f06"]["source"]) == 12


def test_complete_rank_witness_passes_both_directions():
    cases = load_shifted_pq_cases(PROBLEM)
    forward, inverse = rank_maps(cases)
    result = evaluate_shifted_pq_bijection(
        lambda tableau: forward[tableau.encoding],
        lambda tableau: inverse[tableau.encoding],
        cases,
        order_seed=19,
    )
    assert result["passed"]


def test_wrong_side_identity_map_fails():
    cases = load_shifted_pq_cases(PROBLEM)
    result = evaluate_shifted_pq_bijection(
        lambda tableau: tableau.encoding,
        lambda tableau: tableau.encoding,
        cases,
    )
    assert not result["passed"]
    assert "wrong-side" in result["case_results"][0]["first_failure"]


def test_instance_sample_is_canonical_and_disclosed():
    data = json.loads((PROBLEM / "data/instances.json").read_text())
    assert all(
        is_shifted_setvalued_tableau_encoding(entry["tableau"])
        for case in data["cases"]
        for entry in case["entries"]
    )
    assert "is a sample, not the scored set" in (PROBLEM / "problem.md").read_text()


def test_q_equals_one_is_the_unrefined_fixed_content_marginal():
    data = json.loads((PROBLEM / "data/q_equals_1.json").read_text())
    assert data["variables"] == []
    assert data["specialization"] == {"entry_count": 1}
    assert all(case["terms"] == [[case["count"]]] for case in data["cases"])


def test_probe_factory_uses_seeded_valid_objects_on_both_sides():
    probes = adversarial_shifted_pq_probes(64, seed=4)
    assert probes == adversarial_shifted_pq_probes(64, seed=4)
    assert probes != adversarial_shifted_pq_probes(64, seed=5)
    assert [name for name, _arguments in probes] == ["forward", "inverse"] * 2
    assert all(
        is_shifted_setvalued_tableau_encoding(arguments[0].encoding)
        for _name, arguments in probes
    )
