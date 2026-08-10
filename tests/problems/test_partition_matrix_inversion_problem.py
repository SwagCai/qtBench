from __future__ import annotations

import json
from pathlib import Path

from qtbench.combinatorics import PartitionMatrixInversion, is_partition_matrix_inversion_encoding
from qtbench.evaluation.admission import (
    ResourceGateError,
    adversarial_partition_matrix_inversion_probes,
    evaluate_partition_matrix_inversion_bijection,
    load_partition_matrix_inversion_cases,
    run_partition_matrix_inversion_identity_gate,
)
import pytest

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems/exchanging_bijection/improper_partition_matrix_inversion_sequence_bijection"


def rank_maps(cases):
    forward, inverse = {}, {}
    for case in cases.values():
        source_fibers, target_fibers = {}, {}
        for encoding in case["source"]:
            source_fibers.setdefault(PartitionMatrixInversion(encoding, validate=False).grading, []).append(encoding)
        for encoding in case["target"]:
            target_fibers.setdefault(PartitionMatrixInversion(encoding, validate=False).grading, []).append(encoding)
        for grading, source in source_fibers.items():
            for left, right in zip(sorted(source), sorted(target_fibers[grading]), strict=True):
                forward[left] = right
                inverse[right] = left
    return forward, inverse


def test_public_fibers_have_published_counts():
    cases = load_partition_matrix_inversion_cases(PROBLEM)
    assert {n: len(case["source"]) for n, case in cases.items()} == {
        3: 3, 4: 7, 5: 21, 6: 67, 7: 237, 8: 907, 9: 3741
    }


def test_complete_rank_witness_passes_both_directions():
    cases = load_partition_matrix_inversion_cases(PROBLEM)
    forward, inverse = rank_maps(cases)
    result = evaluate_partition_matrix_inversion_bijection(
        lambda obj: forward[obj.encoding], lambda obj: inverse[obj.encoding], cases, order_seed=30
    )
    assert result["passed"]


def test_identity_map_fails_wrong_side_check():
    cases = load_partition_matrix_inversion_cases(PROBLEM)
    result = evaluate_partition_matrix_inversion_bijection(
        lambda obj: obj.encoding, lambda obj: obj.encoding, cases
    )
    assert not result["passed"]
    assert "wrong-side" in result["case_results"][0]["first_failure"]


def test_instance_sample_is_canonical():
    data = json.loads((PROBLEM / "data/instances.json").read_text())
    assert all(
        is_partition_matrix_inversion_encoding(entry["matrix"])
        for case in data["cases"]
        for entry in case["entries"]
    )


def test_large_gate_checks_canonical_outputs_from_both_sides():
    source_obj = PartitionMatrixInversion("M;1,2,3,4;1,2,3,4")
    target_obj = PartitionMatrixInversion("I;0,1,2,3")
    source = """\
def forward(obj):
    return 'I;0,1,2,3'

def inverse(obj):
    return 'M;1,2,3,4;1,2,3,4'
"""
    report = run_partition_matrix_inversion_identity_gate(
        source, [source_obj, target_obj], timeout_seconds=5.0, max_python_bytes=32_000_000
    )
    assert report.checked_paths == 2
    bad = source.replace("I;0,1,2,3", "I;00,1,2,3")
    with pytest.raises(ResourceGateError, match="noncanonical"):
        run_partition_matrix_inversion_identity_gate(
            bad, [source_obj], timeout_seconds=5.0, max_python_bytes=32_000_000
        )


def test_probe_factory_routes_both_sides():
    probes = adversarial_partition_matrix_inversion_probes(16, seed=4)
    assert probes == adversarial_partition_matrix_inversion_probes(16, seed=4)
    assert probes != adversarial_partition_matrix_inversion_probes(16, seed=5)
    assert [name for name, _arguments in probes] == ["forward", "inverse"] * 2
    assert all(
        len(arguments) == 1
        and is_partition_matrix_inversion_encoding(arguments[0].encoding)
        for _name, arguments in probes
    )
