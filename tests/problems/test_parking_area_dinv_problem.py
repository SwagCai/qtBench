from __future__ import annotations

import importlib.util
from collections import Counter
import json
from pathlib import Path

import pytest

import qtbench.evaluation.admission as admission
from qtbench.combinatorics import ParkingFunction
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_parking_functions,
    load_parking_area_dinv_terms,
    run_parking_area_dinv_identity_gate,
)
from qtbench.evaluation.admission import evaluate_parking_area_dinv_bijection

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems/exchanging_bijection/parking_area_dinv_exchange"


def test_public_targets_are_symmetric_and_have_parking_counts():
    targets = load_parking_area_dinv_terms(PROBLEM)
    assert set(targets) == set(range(1, 8))
    for n, terms in targets.items():
        distribution = Counter({(area, dinv): coefficient for area, dinv, coefficient in terms})
        assert sum(distribution.values()) == (n + 1) ** (n - 1)
        assert distribution == Counter({(dinv, area): count for (area, dinv), count in distribution.items()})


def test_known_statistics_match_instances():
    spec = importlib.util.spec_from_file_location("known", PROBLEM / "known_statistics.py")
    assert spec is not None and spec.loader is not None
    known = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(known)
    data = json.loads((PROBLEM / "data/instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            parking = ParkingFunction(entry["parking"])
            assert known.area(parking) == entry["area"]
            assert known.dinv(parking) == entry["dinv"]


def test_identity_map_fails_the_exchange():
    result = evaluate_parking_area_dinv_bijection(
        lambda parking: parking.encoding,
        lambda parking: parking.encoding,
        load_parking_area_dinv_terms(PROBLEM),
    )
    assert not result["passed"]
    assert result["case_results"][-1]["first_failure"] is not None


def test_large_identity_gate_rejects_the_identity_map():
    source = (
        "def forward(parking):\n    return parking.encoding\n\n"
        "def inverse(parking):\n    return parking.encoding\n"
    )
    with pytest.raises(ResourceGateError, match="rejected"):
        run_parking_area_dinv_identity_gate(
            source,
            adversarial_parking_functions(8, seed=3),
            timeout_seconds=5.0,
            max_python_bytes=32_000_000,
        )


def test_numerical_gate_rejects_forward_only_toggle(monkeypatch):
    parking = ParkingFunction("0,0")
    image = ParkingFunction("0,1")
    bad_preimage = ParkingFunction("1,0")
    monkeypatch.setattr(admission, "iter_parking_functions", lambda _n: iter((parking,)))

    def forward(obj):
        return (
            parking.encoding if obj.encoding == bad_preimage.encoding else image.encoding
        )

    def inverse(obj):
        return (
            parking.encoding if obj.encoding == image.encoding else bad_preimage.encoding
        )

    result = evaluate_parking_area_dinv_bijection(
        forward,
        inverse,
        {2: [[parking.area(), image.area(), 1]]},
    )

    assert not result["passed"]
    assert "inverse area/dinv exchange" in result["case_results"][0]["first_failure"]


def test_large_identity_gate_rejects_forward_only_toggle():
    source = """\
def forward(parking):
    if parking.encoding == '1,0':
        return '0,0'
    return '0,1'

def inverse(parking):
    if parking.encoding == '0,1':
        return '0,0'
    return '1,0'
"""
    with pytest.raises(ResourceGateError, match="inverse area/dinv exchange"):
        run_parking_area_dinv_identity_gate(
            source,
            [ParkingFunction("0,0")],
            timeout_seconds=5.0,
            max_python_bytes=32_000_000,
        )
