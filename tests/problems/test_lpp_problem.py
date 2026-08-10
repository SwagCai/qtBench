from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

from qtbench.combinatorics import (
    iter_st_labelled_polyominoes,
    st_labelled_polyomino_count,
    st_labelled_polyomino_size,
)
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_lpp_probes,
    evaluate_lpp_polynomial_checks,
    evaluate_lpp_submission,
    run_resource_gate,
    run_value_audit,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "t_statistic_discovery" / "lpp_area_qt_theta_second_stat"
PROBLEM_ID = 6
PROBLEM_NAME = "lpp_area_qt_theta_second_stat"


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def test_polynomials_are_symmetric_and_total_the_stlpp_count():
    data = _polynomials()
    assert data["variables"] == ["q", "t"]
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    for case in data["cases"]:
        m, n = case["m"], case["n"]
        poly = {(q, t): c for q, t, c in case["terms"]}
        assert all(c > 0 for c in poly.values())
        assert sum(poly.values()) == case["count"] == st_labelled_polyomino_count(m, n)
        assert poly == {(t, q): c for (q, t), c in poly.items()}  # q,t-symmetric
        # realizability: the q-marginal is the labelled area distribution of stLPP(m,n)
        if m + n <= 7:
            q_marginal = Counter()
            for (q, _t), c in poly.items():
                q_marginal[q] += c
            model = Counter(p.area() for p in iter_st_labelled_polyominoes(m, n))
            assert q_marginal == model


def test_known_statistic_matches_public_instances():
    spec = importlib.util.spec_from_file_location("known_lpp", PROBLEM / "known_statistic.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((PROBLEM / "data" / "instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            assert module.statistic(entry["polyomino"]) == entry["area"]


def _reference_partner():
    """A rank-assignment witness: proves the target is realizable over stLPP."""
    mapping: dict[str, int] = {}
    for case in _polynomials()["cases"]:
        column = defaultdict(list)
        for q, t, coeff in case["terms"]:
            column[q].extend([t] * coeff)
        for values in column.values():
            values.sort()
        fibers = defaultdict(list)
        for polyomino in iter_st_labelled_polyominoes(case["m"], case["n"]):
            fibers[polyomino.area()].append(polyomino.encoding)
        for area, encodings in fibers.items():
            for encoding, value in zip(encodings, column[area], strict=True):
                mapping[encoding] = value

    def partner(polyomino):
        return mapping[polyomino.encoding]

    return partner


def test_reference_partner_reproduces_the_target_but_area_does_not():
    result = evaluate_lpp_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_partner(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    area_result = evaluate_lpp_polynomial_checks(
        problem_dir=PROBLEM, statistic=lambda polyomino: polyomino.area()
    )
    assert not area_result["full_qt"]["passed"]


def test_constant_zero_short_circuits_at_numerical_end_to_end():
    result = evaluate_lpp_submission(
        source="def statistic(polyomino):\n    return 0\n",
        probes=lambda: adversarial_lpp_probes(96),
        problem_dir=PROBLEM,
        timeout_seconds=2.0,
        numerical_timeout_seconds=20.0,
        max_python_bytes=64_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"
    assert result["value_audit"] is None


def test_value_audit_wired_for_labelled_polyominoes():
    # a genuine small-valued statistic passes; a counting cheat is blocked
    genuine = "def statistic(polyomino):\n    return len(polyomino.labelled_cells)\n"
    run_value_audit(
        genuine,
        adversarial_lpp_probes(64),
        value_exponent=8,
        timeout_seconds=5.0,
        size_of=st_labelled_polyomino_size,
    )

    counting = (
        "def statistic(polyomino):\n"
        "    total = 1\n"
        "    for _ in range(polyomino.m + polyomino.n):\n"
        "        total = total + total\n"
        "    return total % 3\n"
    )
    with pytest.raises(ResourceGateError, match="magnitude bound|bit integer"):
        run_value_audit(
            counting,
            adversarial_lpp_probes(64),
            value_exponent=8,
            timeout_seconds=5.0,
            size_of=st_labelled_polyomino_size,
        )


def test_resource_gate_accepts_a_polynomial_statistic_on_large_lpp():
    # A genuine, polynomial-time statistic runs within limits on large probes.
    genuine = "def statistic(polyomino):\n    return polyomino.area()\n"
    report = run_resource_gate(
        genuine,
        adversarial_lpp_probes(256),
        timeout_seconds=5.0,
        max_python_bytes=64_000_000,
    )
    assert len(report.results) == len(adversarial_lpp_probes(256))
