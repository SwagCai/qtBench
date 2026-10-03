from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path


from qtbench.combinatorics import (
    decorated_labelled_dyck_count,
    iter_decorated_labelled_dyck_paths,
)
from qtbench.evaluation import (
    adversarial_ddyck_probes,
    evaluate_ddyck_polynomial_checks,
    evaluate_ddyck_submission,
    run_resource_gate,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "t_statistic_discovery" / "ddyck_area_qt_unified_delta_second_stat"
PROBLEM_ID = 7
PROBLEM_NAME = "ddyck_area_qt_unified_delta_second_stat"


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def test_polynomials_are_symmetric_and_total_the_ld_count():
    data = _polynomials()
    assert data["variables"] == ["q", "t"]
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    for case in data["cases"]:
        n, k, l = case["n"], case["k"], case["l"]
        assert 0 <= k and 0 <= l and k + l <= n - 1
        poly = {(q, t): c for q, t, c in case["terms"]}
        assert all(c > 0 for c in poly.values())
        assert sum(poly.values()) == case["count"] == decorated_labelled_dyck_count(n, k, l)
        assert poly == {(t, q): c for (q, t), c in poly.items()}  # q,t-symmetric
        # realizability: the q-marginal is the area distribution of LD(n)^{*k,•l}
        if n <= 5:
            q_marginal = Counter()
            for (q, _t), c in poly.items():
                q_marginal[q] += c
            model = Counter(p.area() for p in iter_decorated_labelled_dyck_paths(n, k, l))
            assert q_marginal == model


def test_known_statistic_matches_public_instances():
    spec = importlib.util.spec_from_file_location("known_ddyck", PROBLEM / "known_statistic.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((PROBLEM / "data" / "instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            assert module.statistic(entry["object"]) == entry["area"]


def _reference_partner():
    """A rank-assignment witness: proves the target is realizable over LD."""
    mapping: dict[str, int] = {}
    for case in _polynomials()["cases"]:
        column = defaultdict(list)
        for q, t, coeff in case["terms"]:
            column[q].extend([t] * coeff)
        for values in column.values():
            values.sort()
        fibers = defaultdict(list)
        for path in iter_decorated_labelled_dyck_paths(case["n"], case["k"], case["l"]):
            fibers[path.area()].append(path.encoding)
        for area, encodings in fibers.items():
            for encoding, value in zip(encodings, column[area], strict=True):
                mapping[encoding] = value

    def partner(path):
        return mapping[path.encoding]

    return partner


def test_reference_partner_reproduces_the_target_but_area_does_not():
    result = evaluate_ddyck_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_partner(), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    area_result = evaluate_ddyck_polynomial_checks(
        problem_dir=PROBLEM, statistic=lambda path: path.area()
    )
    assert not area_result["full_qt"]["passed"]


def test_constant_zero_short_circuits_at_numerical_end_to_end():
    result = evaluate_ddyck_submission(
        source="def statistic(path):\n    return 0\n",
        probes=lambda: adversarial_ddyck_probes(96),
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
        adversarial_ddyck_probes(256),
        timeout_seconds=5.0,
        max_python_bytes=64_000_000,
    )
    assert len(report.results) == len(adversarial_ddyck_probes(256))
