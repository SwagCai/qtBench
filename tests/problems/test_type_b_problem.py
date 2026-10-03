from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from math import comb
from pathlib import Path


from qtbench.combinatorics import enumerate_type_b_catalan_paths
from qtbench.evaluation import (
    adversarial_type_b_probes,
    evaluate_type_b_polynomial_checks,
    evaluate_type_b_submission,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "t_statistic_discovery" / "type_b_area_qt_catalan_second_stat"


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def test_polynomials_are_symmetric_and_total_the_type_b_catalan_number():
    data = _polynomials()
    assert data["variables"] == ["q", "t"]
    assert data["problem_id"] == 3
    assert data["public_max_n"] == 9
    for case in data["cases"]:
        n = case["n"]
        poly = {(q, t): c for q, t, c in case["terms"]}
        assert sum(poly.values()) == comb(2 * n, n) == case["count"]
        assert poly == {(t, q): c for (q, t), c in poly.items()}  # q,t-symmetric
        # realizability: the q-marginal is the type B area distribution
        if n <= 7:
            q_marginal = Counter()
            for (q, _t), c in poly.items():
                q_marginal[q] += c
            model = Counter(p.area() for p in enumerate_type_b_catalan_paths(n))
            assert q_marginal == model


def test_known_statistic_matches_public_instances():
    spec = importlib.util.spec_from_file_location("known_b", PROBLEM / "known_statistic.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((PROBLEM / "data" / "instances.json").read_text())
    for case in data["cases"]:
        by_steps = {p.steps: p for p in enumerate_type_b_catalan_paths(case["n"])}
        for entry in case["entries"]:
            assert module.statistic(by_steps[entry["path"]]) == entry["area"]


def _reference_partner():
    """A rank-assignment witness: proves the target is realizable over the paths."""
    mapping: dict[str, int] = {}
    for case in _polynomials()["cases"]:
        column = defaultdict(list)
        for q, t, coeff in case["terms"]:
            column[q].extend([t] * coeff)
        for values in column.values():
            values.sort()
        fibers = defaultdict(list)
        for path in enumerate_type_b_catalan_paths(case["n"]):
            fibers[path.area()].append(path.steps)
        for area, steps_list in fibers.items():
            for steps, value in zip(steps_list, column[area], strict=True):
                mapping[steps] = value

    def partner(path):
        return mapping[path.steps]

    return partner


def test_reference_partner_reproduces_the_target_but_area_does_not():
    result = evaluate_type_b_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_partner(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    area_result = evaluate_type_b_polynomial_checks(
        problem_dir=PROBLEM, statistic=lambda path: path.area()
    )
    assert not area_result["full_qt"]["passed"]


def test_constant_zero_short_circuits_at_numerical_end_to_end():
    result = evaluate_type_b_submission(
        source="def statistic(path):\n    return 0\n",
        probes=lambda: adversarial_type_b_probes(128),
        problem_dir=PROBLEM,
        timeout_seconds=2.0,
        numerical_timeout_seconds=8.0,
        max_python_bytes=32_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"
