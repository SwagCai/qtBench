from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from math import gcd
from pathlib import Path

import pytest

from qtbench.combinatorics import (
    iter_labelled_rectangular_paths,
    labelled_rectangular_path_count,
)
from qtbench.evaluation import (
    adversarial_lrp_probes,
    evaluate_lrp_polynomial_checks,
    evaluate_lrp_submission,
    run_resource_gate,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "t_statistic_discovery" / "lrp_area_qt_rectangular_delta_second_stat"
PROBLEM_ID = 11
PROBLEM_NAME = "lrp_area_qt_rectangular_delta_second_stat"


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def test_generator_drops_entries_when_a_fiber_exceeds_the_instance_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "generate_lrp", PROBLEM / "generate_data.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class FakePath:
        encoding = "fake"

        def area(self) -> int:
            return 0

    monkeypatch.setattr(
        module,
        "iter_labelled_rectangular_paths",
        lambda _m, _n, _k: iter((FakePath(), FakePath(), FakePath())),
    )

    area_counter, count, entries = module._enumerate_fiber(1, 1, 1, 2)

    assert area_counter == Counter({0: 3})
    assert count == 3
    assert entries == []

    _area_counter, count, entries = module._enumerate_fiber(1, 1, 1, 3)
    assert count == 3
    assert len(entries) == 3


def test_polynomials_are_positive_and_total_the_lrp_count():
    data = _polynomials()
    assert data["variables"] == ["q", "t"]
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    seen_non_coprime = 0
    for case in data["cases"]:
        m, n, k = case["m"], case["n"], case["k"]
        assert k >= 1
        assert (m + k) + (n + k) <= 10
        seen_non_coprime += gcd(m, n) > 1
        poly = {(q, t): c for q, t, c in case["terms"]}
        assert all(c > 0 for c in poly.values())
        assert sum(poly.values()) == case["count"]
        # realizability: the q-marginal is the area distribution of LRP
        if case["count"] <= 1000:
            assert case["count"] == labelled_rectangular_path_count(m, n, k)
            q_marginal = Counter()
            for (q, _t), c in poly.items():
                q_marginal[q] += c
            model = Counter(path.area() for path in iter_labelled_rectangular_paths(m, n, k))
            assert q_marginal == model
    # the source conjecture is stated for arbitrary sides, so d = gcd(m, n) > 1
    # fibers must be published too
    assert seen_non_coprime > 0


def test_target_is_not_q_t_symmetric():
    # The [m+k]_q prefactor breaks the symmetry, so the transposed convention in
    # the problem statement is a genuine relabelling and not a symmetry.
    asymmetric = 0
    for case in _polynomials()["cases"]:
        poly = {(q, t): c for q, t, c in case["terms"]}
        if poly != {(t, q): c for (q, t), c in poly.items()}:
            asymmetric += 1
    assert asymmetric > 0


def test_known_statistic_matches_public_instances():
    spec = importlib.util.spec_from_file_location("known_lrp", PROBLEM / "known_statistic.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((PROBLEM / "data" / "instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            assert module.statistic(entry["object"]) == entry["area"]


def _reference_partner():
    """A rank-assignment witness: proves the target is realizable over LRP."""
    mapping: dict[str, int] = {}
    for case in _polynomials()["cases"]:
        column = defaultdict(list)
        for q, t, coeff in case["terms"]:
            column[q].extend([t] * coeff)
        for values in column.values():
            values.sort()
        fibers = defaultdict(list)
        for path in iter_labelled_rectangular_paths(case["m"], case["n"], case["k"]):
            fibers[path.area()].append(path.encoding)
        for area, encodings in fibers.items():
            for encoding, value in zip(encodings, column[area], strict=True):
                mapping[encoding] = value

    def partner(path):
        return mapping[path.encoding]

    return partner


def test_reference_partner_reproduces_the_target_but_area_does_not():
    result = evaluate_lrp_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_partner(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    area_result = evaluate_lrp_polynomial_checks(
        problem_dir=PROBLEM, statistic=lambda path: path.area()
    )
    assert not area_result["full_qt"]["passed"]


def test_constant_zero_short_circuits_at_numerical_end_to_end():
    result = evaluate_lrp_submission(
        source="def statistic(path):\n    return 0\n",
        probes=lambda: adversarial_lrp_probes(96),
        problem_dir=PROBLEM,
        timeout_seconds=2.0,
        numerical_timeout_seconds=60.0,
        max_python_bytes=64_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"




def test_resource_gate_accepts_a_polynomial_statistic_on_large_paths():
    # A genuine, polynomial-time statistic runs within limits on large probes.
    genuine = "def statistic(path):\n    return path.area()\n"
    report = run_resource_gate(
        genuine,
        adversarial_lrp_probes(256),
        timeout_seconds=10.0,
        max_python_bytes=64_000_000,
    )
    assert len(report.results) == len(adversarial_lrp_probes(256))
