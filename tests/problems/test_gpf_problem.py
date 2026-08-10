from __future__ import annotations

import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest

import qtbench.combinatorics.type_a.gamma_parking as gamma_parking
from qtbench.combinatorics import (
    canonical_gamma_parking_selection,
    gamma_parking_size,
    is_gamma_parking_selection,
    iter_gamma_parking_selections,
)
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_gpf_probes,
    adversarial_lgpf_probes,
    evaluate_gpf_polynomial_checks,
    evaluate_gpf_submission,
    evaluate_lgpf_polynomial_checks,
    evaluate_lgpf_submission,
    run_resource_gate,
    run_value_audit,
)

ROOT = Path(__file__).resolve().parents[2] / "problems" / "t_statistic_discovery"
ORDINARY = ROOT / "gpf_sel_ut_delta_xi_second_stat"
LATTICE = ROOT / "lgpf_sel_ut_delta_xi_schur_second_stat"
PROBLEMS = (
    (ORDINARY, 18, "gpf_sel_ut_delta_xi_second_stat", False),
    (LATTICE, 20, "lgpf_sel_ut_delta_xi_schur_second_stat", True),
)


def _polynomials(problem: Path):
    return json.loads((problem / "data" / "polynomials.json").read_text())


@pytest.mark.parametrize("problem,problem_id,problem_name,lattice", PROBLEMS)
def test_targets_are_positive_and_total_the_pair_count(problem, problem_id, problem_name, lattice):
    data = _polynomials(problem)
    assert data["variables"] == ["partition", "u", "t"]
    assert data["problem_id"] == problem_id
    assert data["problem_name"] == problem_name
    for case in data["cases"]:
        gamma = tuple(case["gamma"])
        lam = tuple(case["lam"])
        content = tuple(case["content"])
        assert sum(lam) == case["n"] and sum(content) == case["n"]
        assert list(lam) == sorted(lam, reverse=True)
        assert len(gamma) <= case["n"]
        assert all(coeff > 0 for _eta, _u, _t, coeff in case["terms"])
        assert sum(coeff for _eta, _u, _t, coeff in case["terms"]) == case["count"]
        # The e-composition of every graded part is a partition of n.
        for eta, _u, _t, _coeff in case["terms"]:
            assert sum(eta) == case["n"]
            assert eta == sorted(eta, reverse=True)


@pytest.mark.parametrize("problem,problem_id,problem_name,lattice", PROBLEMS)
def test_t_equals_1_marginal_is_the_selected_cell_count(problem, problem_id, problem_name, lattice):
    """Theorem 1.1/1.2: at t=1 the target counts pairs by eta(p) and #S."""
    for case in _polynomials(problem)["cases"]:
        if case["n"] + sum(case["gamma"]) > 4:
            continue
        expected: Counter[tuple[tuple[int, ...], int]] = Counter()
        for eta, u, _t, coeff in case["terms"]:
            expected[(tuple(eta), u)] += coeff
        model: Counter[tuple[tuple[int, ...], int]] = Counter()
        objects = iter_gamma_parking_selections(
            tuple(case["gamma"]), tuple(case["content"]), lattice=lattice
        )
        count = 0
        for obj in objects:
            assert is_gamma_parking_selection(obj.encoding, lattice=lattice)
            assert obj.selected_count() == len(obj.selected_cells)
            assert set(obj.selected_cells) <= set(obj.area_cells)
            model[(obj.eta(), obj.selected_count())] += 1
            count += 1
        assert count == case["count"]
        assert model == expected


@pytest.mark.parametrize("problem,problem_id,problem_name,lattice", PROBLEMS)
def test_known_statistic_matches_public_instances(problem, problem_id, problem_name, lattice):
    spec = importlib.util.spec_from_file_location(
        f"known_{problem.name}", problem / "known_statistic.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((problem / "data" / "instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            assert module.statistic(entry["object"]) == entry["sel"]


def _reference_partner(problem: Path, lattice: bool):
    """A rank-assignment witness: proves the target is realizable over the fiber."""
    mapping: dict[str, int] = {}
    for case in _polynomials(problem)["cases"]:
        column = defaultdict(list)
        for eta, u, t, coeff in case["terms"]:
            column[(tuple(eta), u)].extend([t] * coeff)
        for values in column.values():
            values.sort()
        fibers = defaultdict(list)
        objects = iter_gamma_parking_selections(
            tuple(case["gamma"]), tuple(case["content"]), lattice=lattice
        )
        for obj in objects:
            fibers[(obj.eta(), obj.selected_count())].append(obj.encoding)
        for key, encodings in fibers.items():
            for encoding, value in zip(encodings, column[key], strict=True):
                mapping[encoding] = value

    def partner(selection):
        return mapping[selection.encoding]

    return partner


def test_reference_partner_reproduces_the_ordinary_target_but_sel_does_not():
    result = evaluate_gpf_polynomial_checks(
        problem_dir=ORDINARY, statistic=_reference_partner(ORDINARY, False), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    sel_result = evaluate_gpf_polynomial_checks(
        problem_dir=ORDINARY, statistic=lambda selection: selection.selected_count()
    )
    assert not sel_result["full_qt"]["passed"]


def test_reference_partner_reproduces_the_lattice_target_but_sel_does_not():
    result = evaluate_lgpf_polynomial_checks(
        problem_dir=LATTICE, statistic=_reference_partner(LATTICE, True), order_seed=1
    )
    assert result["passed"]
    assert result["q_equals_1"]["passed"] and result["full_qt"]["passed"]

    sel_result = evaluate_lgpf_polynomial_checks(
        problem_dir=LATTICE, statistic=lambda selection: selection.selected_count()
    )
    assert not sel_result["full_qt"]["passed"]


def test_the_two_problems_have_different_fibers():
    """The lattice family is a genuinely different dataset, not a relabelling."""
    gamma, lam = (1,), (2, 1)
    ordinary = {obj.encoding for obj in iter_gamma_parking_selections(gamma, lam)}
    lattice = {
        obj.encoding
        for obj in iter_gamma_parking_selections(gamma, (2, 1), lattice=True)
    }
    assert lattice < ordinary and lattice != ordinary


@pytest.mark.parametrize("gamma", [(1, 2), (0,), (-1,)])
def test_gamma_fiber_apis_reject_nonpartitions(gamma):
    with pytest.raises(ValueError, match="gamma must be a partition"):
        list(iter_gamma_parking_selections(gamma, (1, 1, 1)))
    with pytest.raises(ValueError, match="gamma must be a partition"):
        canonical_gamma_parking_selection(gamma, (1, 1, 1))


def test_canonical_gamma_fiber_rejects_too_many_parts():
    with pytest.raises(ValueError, match="too many parts"):
        canonical_gamma_parking_selection((1, 1), (1,))


@pytest.mark.parametrize("content", [(), (1, 2), (0,), (-1,)])
def test_gamma_fiber_apis_reject_invalid_content(content):
    with pytest.raises(ValueError, match="content must be a partition"):
        list(iter_gamma_parking_selections((1,), content))
    with pytest.raises(ValueError, match="content must be a partition"):
        canonical_gamma_parking_selection((1,), content)


def test_constant_zero_short_circuits_at_numerical_end_to_end():
    result = evaluate_gpf_submission(
        source="def statistic(selection):\n    return 0\n",
        probes=lambda: adversarial_gpf_probes(24),
        problem_dir=ORDINARY,
        timeout_seconds=2.0,
        numerical_timeout_seconds=120.0,
        max_python_bytes=64_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"
    assert result["value_audit"] is None

    lattice_result = evaluate_lgpf_submission(
        source="def statistic(selection):\n    return 0\n",
        probes=lambda: adversarial_lgpf_probes(24),
        problem_dir=LATTICE,
        timeout_seconds=2.0,
        numerical_timeout_seconds=120.0,
        max_python_bytes=64_000_000,
    )
    assert not lattice_result["passed"]
    assert lattice_result["checker_stage"] == "numerical"


def test_value_audit_wired_for_gamma_parking_selections():
    # a genuine small-valued statistic passes; a counting cheat is blocked
    genuine = "def statistic(selection):\n    return selection.area()\n"
    run_value_audit(
        genuine,
        adversarial_gpf_probes(64),
        value_exponent=8,
        timeout_seconds=5.0,
        size_of=gamma_parking_size,
    )

    counting = (
        "def statistic(selection):\n"
        "    total = 1\n"
        "    for _ in range(selection.n):\n"
        "        total = total + total\n"
        "    return total % 3\n"
    )
    with pytest.raises(ResourceGateError, match="magnitude bound|bit integer"):
        run_value_audit(
            counting,
            adversarial_gpf_probes(64),
            value_exponent=8,
            timeout_seconds=5.0,
            size_of=gamma_parking_size,
        )


def test_adversarial_probe_construction_does_not_materialize_all_area_cells(
    monkeypatch,
):
    def fail_if_materialized(*_args):
        raise AssertionError("probe builder materialized the quadratic area-cell set")

    monkeypatch.setattr(gamma_parking, "_area_cells", fail_if_materialized)
    probes = adversarial_gpf_probes(64, seed=1)
    selections = [arguments[0] for _name, arguments in probes]
    assert any(selection.selected_cells for selection in selections)
    assert all(
        len(selection.selected_cells) <= selection.width for selection in selections
    )


def test_resource_gate_accepts_a_polynomial_statistic_on_large_objects():
    # A genuine, polynomial-time statistic runs within limits on large probes.
    genuine = "def statistic(selection):\n    return selection.area() - selection.selected_count()\n"
    for probes in (adversarial_gpf_probes(192), adversarial_lgpf_probes(192)):
        report = run_resource_gate(
            genuine,
            probes,
            timeout_seconds=10.0,
            max_python_bytes=64_000_000,
        )
        assert len(report.results) == len(probes)
