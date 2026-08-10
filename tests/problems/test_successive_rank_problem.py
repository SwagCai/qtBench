from __future__ import annotations

import json
from pathlib import Path

from qtbench.combinatorics import is_successive_rank_partition_encoding
from qtbench.evaluation.admission import (
    ResourceGateError,
    adversarial_successive_rank_probes,
    evaluate_successive_rank_bijection,
    load_successive_rank_cases,
    run_successive_rank_identity_gate,
)
from qtbench.combinatorics import SuccessiveRankPartition
import pytest

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems/exchanging_bijection/andrews_bressoud_successive_rank_bijection"


def rank_maps(cases):
    forward, inverse = {}, {}
    for case in cases.values():
        for source, target in zip(sorted(case["source"]), sorted(case["target"]), strict=True):
            forward[source] = target
            inverse[target] = source
    return forward, inverse


def test_public_fibers_are_complete_and_exclude_known_special_cases():
    cases = load_successive_rank_cases(PROBLEM)
    assert len(cases) == 12
    assert sum(len(case["source"]) for case in cases.values()) == 1604
    assert all(case["modulus"] != 5 for case in cases.values())


def test_complete_rank_witness_passes_both_directions():
    cases = load_successive_rank_cases(PROBLEM)
    forward, inverse = rank_maps(cases)
    result = evaluate_successive_rank_bijection(
        lambda obj: forward[obj.encoding], lambda obj: inverse[obj.encoding], cases, order_seed=29
    )
    assert result["passed"]


def test_identity_map_fails_wrong_side_check():
    cases = load_successive_rank_cases(PROBLEM)
    result = evaluate_successive_rank_bijection(
        lambda obj: obj.encoding, lambda obj: obj.encoding, cases
    )
    assert not result["passed"]
    assert "wrong-side" in result["case_results"][0]["first_failure"]


def test_instance_sample_is_canonical():
    data = json.loads((PROBLEM / "data/instances.json").read_text())
    assert all(
        is_successive_rank_partition_encoding(entry["partition"])
        for case in data["cases"]
        for entry in case["entries"]
    )


def test_q_equals_one_is_the_unrefined_fixed_parameter_marginal():
    data = json.loads((PROBLEM / "data/q_equals_1.json").read_text())
    assert data["variables"] == []
    assert data["specialization"] == {"weight": 1}
    assert all(case["terms"] == [[case["count"]]] for case in data["cases"])


def test_large_gate_checks_canonical_outputs_from_both_sides():
    source_obj = SuccessiveRankPartition("S;7;2;2,2")
    target_obj = SuccessiveRankPartition("T;7;2;1,1,1,1")
    source = """\
def forward(obj):
    return 'T;7;2;1,1,1,1'

def inverse(obj):
    return 'S;7;2;2,2'
"""
    report = run_successive_rank_identity_gate(
        source, [source_obj, target_obj], timeout_seconds=5.0, max_python_bytes=32_000_000
    )
    assert report.checked_paths == 2
    bad = source.replace("T;7;2;1,1,1,1", "T;7;2;01,1,1,1")
    with pytest.raises(ResourceGateError, match="noncanonical"):
        run_successive_rank_identity_gate(
            bad, [source_obj], timeout_seconds=5.0, max_python_bytes=32_000_000
        )


def test_probe_factory_routes_both_sides():
    probes = adversarial_successive_rank_probes(16, seed=4)
    assert probes == adversarial_successive_rank_probes(16, seed=4)
    assert probes != adversarial_successive_rank_probes(16, seed=5)
    assert [name for name, _arguments in probes] == ["forward", "inverse"] * 8
    assert {
        (arguments[0].modulus, arguments[0].residue)
        for _name, arguments in probes
    } == {(6, 1), (6, 2), (7, 2), (7, 3)}
    assert all(
        len(arguments) == 1
        and is_successive_rank_partition_encoding(arguments[0].encoding)
        for _name, arguments in probes
    )
