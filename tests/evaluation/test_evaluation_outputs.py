from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

import qtbench.evaluation.runner as runner
from qtbench.evaluation import (
    evaluate_problem,
    evaluate_public_polynomial_checks,
    evaluate_q_equals_1_problem,
    evaluate_submission_file,
    load_statistic_function,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "t_statistic_discovery" / "nc_area_qt_narayana_second_stat"
TYPE_B_PROBLEM = (
    ROOT
    / "problems"
    / "t_statistic_discovery"
    / "type_b_area_qt_catalan_second_stat"
)
MLD_PROBLEM = (
    ROOT
    / "problems"
    / "t_statistic_discovery"
    / "mld_area_qt_super_nabla_second_stat"
)
CONSTANT_ZERO = ROOT / "examples" / "constant_zero_submission.py"
PROBLEM_ID = 1
PROBLEM_NAME = "nc_area_qt_narayana_second_stat"


def test_submission_loader_uses_normal_module_registration(tmp_path: Path) -> None:
    submission = tmp_path / "dataclass_submission.py"
    submission.write_text(
        "from __future__ import annotations\n\n"
        "from dataclasses import dataclass\n\n"
        "@dataclass\n"
        "class Helper:\n"
        "    value: int\n\n"
        "def statistic(_partition):\n"
        "    return Helper(0).value\n",
        encoding="utf-8",
    )

    previous = sys.modules.get("qtbench_submission")
    sentinel = ModuleType("qtbench_submission")
    sys.modules["qtbench_submission"] = sentinel
    try:
        statistic = load_statistic_function(submission)

        assert statistic(None) == 0
        assert sys.modules["qtbench_submission"] is sentinel
    finally:
        if previous is None:
            sys.modules.pop("qtbench_submission", None)
        else:
            sys.modules["qtbench_submission"] = previous


def test_submission_loader_restores_module_registration_after_rejection(
    tmp_path: Path,
) -> None:
    submission = tmp_path / "missing_statistic.py"
    submission.write_text("value = 1\n", encoding="utf-8")
    previous = sys.modules.pop("qtbench_submission", None)
    try:
        with pytest.raises(AttributeError, match="must define callable statistic"):
            load_statistic_function(submission)
        assert "qtbench_submission" not in sys.modules
    finally:
        if previous is not None:
            sys.modules["qtbench_submission"] = previous


def test_secret_order_is_one_cycle() -> None:
    original = list(range(12))
    reordered = runner._ordered_objects(original, random.Random(7))

    assert sorted(reordered) == original
    assert all(source != target for source, target in enumerate(reordered))

    visited = set()
    current = 0
    while current not in visited:
        visited.add(current)
        current = reordered[current]
    assert current == 0
    assert len(visited) == len(original)


def test_public_qt_evaluator_reports_l1_and_term_mismatches() -> None:
    result = evaluate_submission_file(problem_dir=PROBLEM, submission_path=CONSTANT_ZERO)

    assert result["split"] == "public"
    assert result["problem_id"] == PROBLEM_ID
    assert result["problem_name"] == PROBLEM_NAME
    failed_cases = [case for case in result["case_results"] if not case["correct"]]
    assert failed_cases

    first_failed = failed_cases[0]
    assert first_failed["l1_distance"] > 0
    assert first_failed["mismatch_count"] == len(first_failed["mismatches"])
    assert set(first_failed["first_mismatch"]["exponents"]) == {"q", "t"}


def test_public_q_equals_1_evaluator_reports_marginal_mismatches() -> None:
    result = evaluate_submission_file(
        problem_dir=PROBLEM,
        submission_path=CONSTANT_ZERO,
        check_q_equals_1=True,
    )

    assert result["split"] == "public_q_equals_1"
    failed_cases = [case for case in result["case_results"] if not case["correct"]]
    assert failed_cases

    first_failed = failed_cases[0]
    assert first_failed["l1_distance"] > 0
    assert first_failed["mismatch_count"] == len(first_failed["mismatches"])
    assert set(first_failed["first_mismatch"]["exponents"]) == {"t"}


def test_legacy_diagnostic_rejects_other_problem_before_import(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "submission-imported"
    submission = tmp_path / "mld_submission.py"
    submission.write_text(
        f"open({str(marker)!r}, 'w', encoding='utf-8').write('imported')\n\n"
        "def statistic(_path):\n"
        "    return 0\n",
        encoding="utf-8",
    )

    with pytest.raises(
        runner.UnsupportedDiagnosticProblemError,
        match="only supports problem 1.*mld_area_qt_super_nabla_second_stat",
    ):
        evaluate_submission_file(
            problem_dir=MLD_PROBLEM,
            submission_path=submission,
        )

    assert not marker.exists()


def test_evaluate_problem_rejects_other_problem_before_loading_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_work(*_args, **_kwargs):
        raise AssertionError("unsupported diagnostic started numerical work")

    monkeypatch.setattr(runner, "_load_public_polynomials", unexpected_work)

    with pytest.raises(
        runner.UnsupportedDiagnosticProblemError,
        match="only supports problem 1.*mld_area_qt_super_nabla_second_stat",
    ):
        evaluate_problem(problem_dir=MLD_PROBLEM, statistic=unexpected_work)


def test_q_equals_1_problem_rejects_other_problem_before_loading_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_work(*_args, **_kwargs):
        raise AssertionError("unsupported diagnostic started marginal work")

    monkeypatch.setattr(runner, "_load_public_q_equals_1", unexpected_work)

    with pytest.raises(
        runner.UnsupportedDiagnosticProblemError,
        match="only supports problem 1.*mld_area_qt_super_nabla_second_stat",
    ):
        evaluate_q_equals_1_problem(
            problem_dir=MLD_PROBLEM,
            statistic=unexpected_work,
        )


def test_q_equals_1_is_only_a_weaker_diagnostic() -> None:
    area = lambda partition: partition.area()

    marginal = evaluate_problem(
        problem_dir=PROBLEM,
        statistic=area,
        check_q_equals_1=True,
    )
    full = evaluate_problem(problem_dir=PROBLEM, statistic=area)

    assert marginal["passed"]
    assert not full["passed"]


def test_combined_public_checks_call_the_statistic_once_per_object() -> None:
    expected_calls = sum(
        case["count"]
        for case in json.loads(
            (PROBLEM / "data" / "polynomials.json").read_text(encoding="utf-8")
        )["cases"]
    )
    calls = 0

    def area(partition):
        nonlocal calls
        calls += 1
        return partition.area()

    result = evaluate_public_polynomial_checks(
        problem_dir=PROBLEM,
        statistic=area,
    )

    assert calls == expected_calls
    assert result["q_equals_1"]["passed"]
    assert not result["full_qt"]["passed"]


def test_every_registered_problem_declares_and_loads_public_contracts() -> None:
    registry = json.loads(
        (ROOT / "problems" / "registry.json").read_text(encoding="utf-8")
    )["problems"]
    registered_ids = {entry["id"] for entry in registry}
    registered_names = {entry["name"] for entry in registry}

    assert len(registered_ids) == len(registry)
    assert set(runner._PUBLIC_CASE_COORDINATES) == registered_names
    assert set(runner._PUBLIC_PROBLEM_CONTRACTS) == registered_names

    loaded_polynomial_ids = set()
    loaded_marginal_ids = set()
    for entry in registry:
        problem = (ROOT / entry["data"]).parent
        polynomials = runner._load_public_polynomials(problem)
        assert (polynomials["problem_id"], polynomials["problem_name"]) == (
            entry["id"],
            entry["name"],
        )
        loaded_polynomial_ids.add(polynomials["problem_id"])
        del polynomials

        marginal = runner._load_public_q_equals_1(problem)
        assert (marginal["problem_id"], marginal["problem_name"]) == (
            entry["id"],
            entry["name"],
        )
        loaded_marginal_ids.add(marginal["problem_id"])
        del marginal

    assert loaded_polynomial_ids == registered_ids
    assert loaded_marginal_ids == registered_ids


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("problem_id", 999, "problem_id"),
        ("case_count", 0, "case_count"),
        ("cases", [], "at least one scored case"),
        ("variables", ["t", "q"], "evaluator contract"),
    ],
)
def test_public_target_loader_fails_closed(
    tmp_path: Path, field: str, value, message: str
) -> None:
    problem = tmp_path / PROBLEM_NAME
    (problem / "data").mkdir(parents=True)
    shutil.copyfile(PROBLEM / "metadata.json", problem / "metadata.json")
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    data[field] = value
    (problem / "data" / "polynomials.json").write_text(json.dumps(data))

    with pytest.raises(ValueError, match=message):
        runner._load_public_polynomials(problem)


def test_public_marginal_loader_enforces_the_evaluator_specialization(
    tmp_path: Path,
) -> None:
    problem = tmp_path / PROBLEM_NAME
    (problem / "data").mkdir(parents=True)
    shutil.copyfile(PROBLEM / "metadata.json", problem / "metadata.json")
    data = json.loads((PROBLEM / "data" / "q_equals_1.json").read_text())
    data["specialization"] = {"q": 2}
    (problem / "data" / "q_equals_1.json").write_text(json.dumps(data))

    with pytest.raises(ValueError, match="specialization.*evaluator contract"):
        runner._load_public_q_equals_1(problem)


def test_type_b_target_loader_enforces_the_evaluator_contract(tmp_path: Path) -> None:
    problem = tmp_path / TYPE_B_PROBLEM.name
    (problem / "data").mkdir(parents=True)
    shutil.copyfile(TYPE_B_PROBLEM / "metadata.json", problem / "metadata.json")
    data = json.loads(
        (TYPE_B_PROBLEM / "data" / "q_equals_1.json").read_text()
    )
    data["variables"] = ["q"]
    (problem / "data" / "q_equals_1.json").write_text(json.dumps(data))

    with pytest.raises(ValueError, match="variables.*evaluator contract"):
        runner._load_public_q_equals_1(problem)


def test_public_target_loader_rejects_malformed_metadata(tmp_path: Path) -> None:
    problem = tmp_path / PROBLEM_NAME
    (problem / "data").mkdir(parents=True)
    metadata = json.loads((PROBLEM / "metadata.json").read_text())
    metadata["id"] = str(metadata["id"])
    (problem / "metadata.json").write_text(json.dumps(metadata))
    shutil.copyfile(
        PROBLEM / "data" / "polynomials.json",
        problem / "data" / "polynomials.json",
    )

    with pytest.raises(ValueError, match="invalid problem id"):
        runner._load_public_polynomials(problem)


@pytest.mark.parametrize(
    ("filename", "duplicate_field"),
    [
        ("metadata.json", "schema_version"),
        ("data/polynomials.json", "schema_version"),
    ],
)
def test_public_target_loader_rejects_duplicate_json_keys(
    tmp_path: Path, filename: str, duplicate_field: str
) -> None:
    problem = tmp_path / PROBLEM_NAME
    (problem / "data").mkdir(parents=True)
    shutil.copyfile(PROBLEM / "metadata.json", problem / "metadata.json")
    shutil.copyfile(
        PROBLEM / "data" / "polynomials.json",
        problem / "data" / "polynomials.json",
    )
    path = problem / filename
    document = path.read_text(encoding="utf-8")
    marker = f'"{duplicate_field}": "0.1"'
    path.write_text(
        document.replace(marker, f'{marker},\n  {marker}', 1),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate JSON object key"):
        runner._load_public_polynomials(problem)


def test_public_target_loader_rejects_nonstandard_json_constants(
    tmp_path: Path,
) -> None:
    problem = tmp_path / PROBLEM_NAME
    (problem / "data").mkdir(parents=True)
    shutil.copyfile(PROBLEM / "metadata.json", problem / "metadata.json")
    data = (PROBLEM / "data" / "polynomials.json").read_text(encoding="utf-8")
    data = data.replace('"problem_id": 1', '"problem_id": NaN', 1)
    (problem / "data" / "polynomials.json").write_text(data, encoding="utf-8")

    with pytest.raises(ValueError, match="non-standard JSON constant NaN"):
        runner._load_public_polynomials(problem)


def test_public_target_loader_rejects_boolean_identity_and_specialization(
    tmp_path: Path,
) -> None:
    problem = tmp_path / PROBLEM_NAME
    (problem / "data").mkdir(parents=True)
    shutil.copyfile(PROBLEM / "metadata.json", problem / "metadata.json")
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    data["problem_id"] = True
    (problem / "data" / "polynomials.json").write_text(json.dumps(data))

    with pytest.raises(ValueError, match="problem_id"):
        runner._load_public_polynomials(problem)

    marginal = json.loads((PROBLEM / "data" / "q_equals_1.json").read_text())
    marginal["specialization"] = {"q": True}
    (problem / "data" / "q_equals_1.json").write_text(json.dumps(marginal))

    with pytest.raises(ValueError, match="specialization.*evaluator contract"):
        runner._load_public_q_equals_1(problem)


@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        ("metadata.json", []),
        ("data/polynomials.json", []),
    ],
)
def test_public_target_loader_rejects_nonobject_documents(
    tmp_path: Path, filename: str, payload
) -> None:
    problem = tmp_path / PROBLEM_NAME
    (problem / "data").mkdir(parents=True)
    shutil.copyfile(PROBLEM / "metadata.json", problem / "metadata.json")
    shutil.copyfile(
        PROBLEM / "data" / "polynomials.json",
        problem / "data" / "polynomials.json",
    )
    (problem / filename).write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="must contain a JSON object"):
        runner._load_public_polynomials(problem)


@pytest.mark.parametrize("field", ["case_count", "term_count"])
def test_public_target_loader_rejects_boolean_counts(
    tmp_path: Path, field: str
) -> None:
    problem = tmp_path / PROBLEM_NAME
    (problem / "data").mkdir(parents=True)
    shutil.copyfile(PROBLEM / "metadata.json", problem / "metadata.json")
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    if field == "case_count":
        data["cases"] = data["cases"][:1]
        data["case_count"] = True
    else:
        data["cases"][0]["terms"] = data["cases"][0]["terms"][:1]
        data["cases"][0]["term_count"] = True
        data["cases"][0]["count"] = data["cases"][0]["terms"][0][-1]
    (problem / "data" / "polynomials.json").write_text(json.dumps(data))

    with pytest.raises(ValueError, match=field):
        runner._load_public_polynomials(problem)


def test_public_target_loader_rejects_malformed_exponents(tmp_path: Path) -> None:
    problem = tmp_path / PROBLEM_NAME
    (problem / "data").mkdir(parents=True)
    shutil.copyfile(PROBLEM / "metadata.json", problem / "metadata.json")
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    data["cases"][0]["terms"][0][0] = True
    (problem / "data" / "polynomials.json").write_text(json.dumps(data))

    with pytest.raises(ValueError, match="invalid q exponent"):
        runner._load_public_polynomials(problem)


@pytest.mark.parametrize("invalid", [True, 1.5, "1", None])
def test_public_target_loader_rejects_coerced_scalar_coordinates(
    tmp_path: Path, invalid
) -> None:
    problem = tmp_path / PROBLEM_NAME
    (problem / "data").mkdir(parents=True)
    shutil.copyfile(PROBLEM / "metadata.json", problem / "metadata.json")
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    data["cases"][0]["n"] = invalid
    (problem / "data" / "polynomials.json").write_text(json.dumps(data))

    with pytest.raises(ValueError, match="invalid integer coordinate 'n'"):
        runner._load_public_polynomials(problem)


@pytest.mark.parametrize("invalid", [[True], [1.5], ["1"], 1, None])
def test_public_target_loader_rejects_coerced_vector_coordinates(
    tmp_path: Path, invalid
) -> None:
    source = ROOT / "problems/t_statistic_discovery/ttree_inv_qt_xi_second_stat"
    problem = tmp_path / source.name
    (problem / "data").mkdir(parents=True)
    shutil.copyfile(source / "metadata.json", problem / "metadata.json")
    data = json.loads((source / "data" / "polynomials.json").read_text())
    data["cases"][0]["mu"] = invalid
    (problem / "data" / "polynomials.json").write_text(json.dumps(data))

    with pytest.raises(ValueError, match="invalid integer-vector coordinate 'mu'"):
        runner._load_public_polynomials(problem)


def test_public_target_loader_rejects_coefficient_total_mismatch(tmp_path: Path) -> None:
    problem = tmp_path / PROBLEM_NAME
    (problem / "data").mkdir(parents=True)
    shutil.copyfile(PROBLEM / "metadata.json", problem / "metadata.json")
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    data["cases"][0]["terms"][0][-1] += 1
    (problem / "data" / "polynomials.json").write_text(json.dumps(data))

    with pytest.raises(ValueError, match="coefficients do not sum to object count"):
        runner._load_public_polynomials(problem)


@pytest.mark.parametrize("invalid", [True, 1.5, "1"])
def test_public_checker_requires_an_exact_integer_statistic(invalid) -> None:
    with pytest.raises(TypeError, match="nonnegative integer"):
        evaluate_public_polynomial_checks(
            problem_dir=PROBLEM,
            statistic=lambda _partition: invalid,
        )


def test_public_checker_rejects_an_integer_unavailable_to_json_reporting() -> None:
    original_limit = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(640)
    try:
        with pytest.raises(ValueError, match="evaluator reporting"):
            runner._statistic_value(10**640, "object")
    finally:
        sys.set_int_max_str_digits(original_limit)
