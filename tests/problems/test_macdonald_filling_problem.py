from __future__ import annotations

import importlib.util
from collections import Counter
import json
from pathlib import Path

import pytest

import qtbench.evaluation.admission as admission
from qtbench.combinatorics import StandardMacdonaldFilling, conjugate_partition
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_standard_macdonald_fillings,
    load_macdonald_filling_terms,
    run_macdonald_filling_identity_gate,
)
from qtbench.evaluation.admission import evaluate_macdonald_filling_bijection

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems/exchanging_bijection/macdonald_fillings_inv_maj_exchange"


def test_public_targets_are_conjugate_symmetric():
    targets = load_macdonald_filling_terms(PROBLEM)
    assert len(targets) == 30
    assert sum(sum(term[-1] for term in terms) for terms in targets.values()) == 608_664
    for shape, terms in targets.items():
        conjugate = targets[conjugate_partition(shape)]
        assert Counter((inv, maj, coefficient) for inv, maj, coefficient in terms) == Counter(
            (maj, inv, coefficient) for inv, maj, coefficient in conjugate
        )


def test_known_statistics_match_instances():
    spec = importlib.util.spec_from_file_location("known", PROBLEM / "known_statistics.py")
    assert spec is not None and spec.loader is not None
    known = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(known)
    data = json.loads((PROBLEM / "data/instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            filling = StandardMacdonaldFilling(entry["filling"])
            assert known.inv(filling) == entry["inv"]
            assert known.maj(filling) == entry["maj"]


def test_identity_map_fails_the_exchange():
    target = load_macdonald_filling_terms(PROBLEM)
    result = evaluate_macdonald_filling_bijection(
        lambda filling: filling.encoding,
        lambda filling: filling.encoding,
        target,
    )
    assert not result["passed"]
    assert result["case_results"][0]["first_failure"] is not None


def test_large_identity_gate_rejects_the_identity_map():
    source = (
        "def forward(filling):\n    return filling.encoding\n\n"
        "def inverse(filling):\n    return filling.encoding\n"
    )
    with pytest.raises(ResourceGateError, match="rejected"):
        run_macdonald_filling_identity_gate(
            source,
            adversarial_standard_macdonald_fillings(8, seed=3),
            timeout_seconds=5.0,
            max_python_bytes=32_000_000,
        )


def test_numerical_gate_checks_the_inverse_exchange(monkeypatch):
    filling = StandardMacdonaldFilling("2,2|1,2/3,4")
    image = StandardMacdonaldFilling("2,2|4,2/3,1")
    bad_preimage = StandardMacdonaldFilling("2,2|1,2/4,3")
    monkeypatch.setattr(
        admission, "iter_standard_macdonald_fillings", lambda _shape: iter((filling,))
    )

    def forward(obj):
        return (
            filling.encoding if obj.encoding == bad_preimage.encoding else image.encoding
        )

    def inverse(obj):
        return (
            filling.encoding if obj.encoding == image.encoding else bad_preimage.encoding
        )

    result = evaluate_macdonald_filling_bijection(
        forward,
        inverse,
        {(2, 2): [[filling.inv(), image.inv(), 1]]},
    )

    assert not result["passed"]
    assert "inverse inv/maj exchange" in result["case_results"][0]["first_failure"]


def test_large_identity_gate_checks_the_inverse_exchange():
    source = """\
def forward(filling):
    if filling.encoding == '2,2|1,2/4,3':
        return '2,2|1,2/3,4'
    return '2,2|4,2/3,1'

def inverse(filling):
    if filling.encoding == '2,2|4,2/3,1':
        return '2,2|1,2/3,4'
    return '2,2|1,2/4,3'
"""
    with pytest.raises(ResourceGateError, match="inverse inv/maj exchange"):
        run_macdonald_filling_identity_gate(
            source,
            [StandardMacdonaldFilling("2,2|1,2/3,4")],
            timeout_seconds=5.0,
            max_python_bytes=32_000_000,
        )
