from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from qtbench.combinatorics import (
    iter_tamari_parking_pairs,
    tamari_parking_count,
)
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_tamari_probes,
    evaluate_tamari_polynomial_checks,
    evaluate_tamari_submission,
    run_resource_gate,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "t_statistic_discovery" / "tamari_park_trivariate_third_stat"
PROBLEM_ID = 12
PROBLEM_NAME = "tamari_park_trivariate_third_stat"


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def test_polynomials_are_symmetric_and_total_the_harmonics_dimension():
    data = _polynomials()
    assert data["variables"] == ["q1", "q2", "q3"]
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    for case in data["cases"]:
        n = case["n"]
        poly = {(d1, d2, d3): c for d1, d2, d3, c in case["terms"]}
        assert all(c > 0 for c in poly.values())
        assert sum(poly.values()) == case["count"] == tamari_parking_count(n)
        assert case["count"] == (1 if n == 1 else 2 ** n * (n + 1) ** (n - 2))
        # symmetric in q1, q2, q3
        for (d1, d2, d3), value in poly.items():
            for permuted in ((d1, d3, d2), (d2, d1, d3), (d3, d2, d1)):
                assert poly.get(permuted, 0) == value


def test_the_two_specializations_match_the_object_model():
    for case in _polynomials()["cases"]:
        n = case["n"]
        poly = {(d1, d2, d3): c for d1, d2, d3, c in case["terms"]}
        at_zero = Counter()
        at_one = Counter()
        for (d1, d2, d3), value in poly.items():
            at_one[(d1, d2)] += value
            if d3 == 0:
                at_zero[(d1, d2)] += value

        shuffle = Counter()
        joint = Counter()
        seen = set()
        for pair in iter_tamari_parking_pairs(n):
            joint[(pair.chain(), pair.dinv())] += 1
            if pair.parking_function not in seen:
                seen.add(pair.parking_function)
                shuffle[(pair.area(), pair.dinv())] += 1
        # q3 = 0 is the shuffle theorem, q3 = 1 is the source paper's Conjecture 1
        assert at_zero == shuffle
        assert at_one == joint
        assert sum(shuffle.values()) == (n + 1) ** (n - 1)


def test_known_statistics_match_public_instances():
    spec = importlib.util.spec_from_file_location("known_tamari", PROBLEM / "known_statistics.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((PROBLEM / "data" / "instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            assert module.chain(entry["object"]) == entry["chain"]
            assert module.dinv(entry["object"]) == entry["dinv"]


def _reference_partner():
    """A rank-assignment witness: proves the target is realizable over the pairs."""
    mapping: dict[str, int] = {}
    for case in _polynomials()["cases"]:
        column = defaultdict(list)
        for d1, d2, d3, coeff in case["terms"]:
            column[(d1, d2)].extend([d3] * coeff)
        for values in column.values():
            values.sort()
        fibers = defaultdict(list)
        for pair in iter_tamari_parking_pairs(case["n"]):
            fibers[(pair.chain(), pair.dinv())].append(pair.encoding)
        for key, encodings in fibers.items():
            for encoding, value in zip(encodings, column[key], strict=True):
                mapping[encoding] = value

    def partner(pair):
        return mapping[pair.encoding]

    return partner


def test_reference_partner_reproduces_the_target_but_dinv_does_not():
    result = evaluate_tamari_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_partner(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    dinv_result = evaluate_tamari_polynomial_checks(
        problem_dir=PROBLEM, statistic=lambda pair: pair.dinv()
    )
    assert not dinv_result["full_qt"]["passed"]


def test_constant_zero_short_circuits_at_numerical_end_to_end():
    result = evaluate_tamari_submission(
        source="def statistic(pair):\n    return 0\n",
        probes=lambda: adversarial_tamari_probes(96),
        problem_dir=PROBLEM,
        timeout_seconds=2.0,
        numerical_timeout_seconds=60.0,
        max_python_bytes=64_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"




def test_resource_gate_accepts_a_polynomial_statistic_on_large_pairs():
    # A genuine, polynomial-time statistic runs within limits on large probes.
    genuine = "def statistic(pair):\n    return pair.dinv()\n"
    report = run_resource_gate(
        genuine,
        adversarial_tamari_probes(256),
        timeout_seconds=10.0,
        max_python_bytes=64_000_000,
    )
    assert len(report.results) == len(adversarial_tamari_probes(256))


def test_resource_gate_blocks_a_statistic_that_searches_the_tamari_interval():
    # chain() is a closed form at the two extremes but a longest-path search in
    # between, so the probes must include intermediate alphas or this passes.
    searching = "def statistic(pair):\n    return pair.chain()\n"
    with pytest.raises(ResourceGateError, match="seconds"):
        run_resource_gate(
            searching,
            adversarial_tamari_probes(64),
            timeout_seconds=5.0,
            max_python_bytes=64_000_000,
        )
