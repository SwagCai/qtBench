from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

import qtbench.evaluation.admission as admission

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "evaluate" / "evaluate_scored_submission.py"


def load_cli_module():
    spec = importlib.util.spec_from_file_location("qtbench_scored_cli", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_official_memory_config(config) -> None:
    assert admission.CHECKER_VERSION == 16
    assert config["version"] == 2
    assert config["checker_version"] == 16
    assert config["max_process_bytes"] == 201_326_592
    assert config["max_parent_process_bytes"] == 67_108_864
    assert config["max_aggregate_process_bytes"] == 268_435_456
    assert (
        config["max_process_bytes"] + config["max_parent_process_bytes"]
        == config["max_aggregate_process_bytes"]
    )


def test_cli_dispatch_covers_every_registered_problem() -> None:
    module = load_cli_module()
    registry = json.loads((ROOT / "problems" / "registry.json").read_text())

    assert set(module.STATISTIC_RUNNERS) | set(module.BIJECTION_RUNNERS) == set(
        module.DEFAULT_PROBLEM
    )
    assert len(module.DEFAULT_PROBLEM) == len(registry["problems"]) == 30
    assert all(path.is_dir() for path in module.DEFAULT_PROBLEM.values())
    assert {path.resolve() for path in module.DEFAULT_PROBLEM.values()} == {
        ((ROOT / entry["data"]).parent).resolve()
        for entry in registry["problems"]
    }


@pytest.mark.parametrize(
    "option,value",
    [
        ("--probe-n", "1"),
        ("--probe-timeout", "999"),
        ("--numerical-timeout", "999"),
        ("--python-memory-mb", "999"),
        ("--process-memory-mb", "999"),
        ("--seed", "7"),
    ],
)
def test_scored_cli_rejects_security_configuration_overrides(
    option: str, value: str
) -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "noncrossing", "missing.py", option, value],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert f"unrecognized arguments: {option} {value}" in completed.stderr


def test_scored_cli_rejects_problem_directory_override(tmp_path: Path) -> None:
    submission = tmp_path / "constant.py"
    submission.write_text("def statistic(partition):\n    return 0\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "noncrossing",
            str(submission),
            "--problem-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert "unrecognized arguments: --problem-dir" in completed.stderr


def test_scored_cli_does_not_execute_rejected_top_level_side_effect(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "scored-executed"
    submission = tmp_path / "side_effect_submission.py"
    submission.write_text(
        f"open({str(marker)!r}, 'w', encoding='utf-8').write('executed')\n\n"
        "def statistic(partition):\n"
        "    return 0\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "noncrossing",
            str(submission),
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["passed"] is False
    assert result["checker_stage"] == "gate_error"
    assert "capability screen" in result["gate_error"]
    assert not marker.exists()


def test_cli_rejects_oversized_source_before_reading_it(tmp_path: Path) -> None:
    submission = tmp_path / "oversized.py"
    submission.write_bytes(b"#" * 1_000_001)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "noncrossing",
            str(submission),
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["passed"] is False
    assert result["automatic_verdict"] is False
    assert result["expert_review_required"] is False
    assert result["checker_version"] == admission.CHECKER_VERSION
    assert result["scoring_mode"] == "official"
    assert result["scoring_config"] == load_cli_module().OFFICIAL_SCORING_CONFIG
    assert_official_memory_config(result["scoring_config"])
    assert "1 MB" in result["gate_error"]


def test_cli_reports_missing_bijection_coordinate_as_json_gate_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_cli_module()
    source_problem = (
        ROOT
        / "problems"
        / "exchanging_bijection"
        / "macdonald_fillings_inv_maj_exchange"
    )
    problem = tmp_path / source_problem.name
    (problem / "data").mkdir(parents=True)
    (problem / "metadata.json").write_text(
        (source_problem / "metadata.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    target = json.loads(
        (source_problem / "data" / "polynomials.json").read_text(encoding="utf-8")
    )
    del target["cases"][0]["shape"]
    (problem / "data" / "polynomials.json").write_text(
        json.dumps(target), encoding="utf-8"
    )

    monkeypatch.setitem(module.DEFAULT_PROBLEM, "macdonald-fillings", problem)
    monkeypatch.setattr(
        module,
        "parse_args",
        lambda: SimpleNamespace(
            kind="macdonald-fillings",
            submission=ROOT / "examples" / "identity_bijection_submission.py",
            format="json",
        ),
    )

    with pytest.raises(SystemExit) as exit_info:
        module.main()

    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out.strip()
    result = json.loads(captured.out)
    assert result["passed"] is False
    assert result["automatic_verdict"] is False
    assert result["checker_stage"] == "gate_error"
    assert "invalid integer-vector coordinate 'shape'" in result["gate_error"]
    assert "Traceback" not in captured.err


def test_scored_main_records_provenance_and_replaces_inherited_seed_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    module = load_cli_module()
    submission = tmp_path / "constant.py"
    submission.write_text("def statistic(partition):\n    return 0\n", encoding="utf-8")
    observed = {}

    def make_probes(n: int, *, seed: int):
        observed["probe_n"] = n
        observed["probe_seed"] = seed
        return []

    def evaluate(**kwargs):
        observed["run_seed"] = os.environ.get("QTBENCH_RUN_SEED")
        observed["replay_seed"] = os.environ.get("QTBENCH_REPLAY_SEED")
        observed["max_process_bytes"] = kwargs["max_process_bytes"]
        budget = admission._AGGREGATE_PROCESS_BUDGET.get()
        observed["max_parent_process_bytes"] = budget.max_parent_process_bytes
        observed["max_aggregate_process_bytes"] = (
            budget.max_aggregate_process_bytes
        )
        kwargs["probes"]()
        return {
            "passed": True,
            "checker_stage": "complete",
            "checker_version": admission.CHECKER_VERSION,
            "function_names": (),
        }

    monkeypatch.setattr(
        module,
        "parse_args",
        lambda: SimpleNamespace(
            kind="noncrossing", submission=submission, format="json"
        ),
    )
    monkeypatch.setattr(module.secrets, "randbits", lambda _bits: 12345)
    monkeypatch.setitem(module.STATISTIC_RUNNERS, "noncrossing", (evaluate, make_probes))
    monkeypatch.setenv("QTBENCH_RUN_SEED", "7")
    monkeypatch.setenv("QTBENCH_REPLAY_SEED", "11")

    with pytest.raises(SystemExit) as exit_info:
        module.main()

    assert exit_info.value.code == 0
    assert observed == {
        "run_seed": "12345",
        "replay_seed": None,
        "probe_n": module.OFFICIAL_SCORING_CONFIG["probe_n"],
        "probe_seed": 12345,
        "max_process_bytes": 201_326_592,
        "max_parent_process_bytes": 67_108_864,
        "max_aggregate_process_bytes": 268_435_456,
    }
    assert admission._AGGREGATE_PROCESS_BUDGET.get() is None
    result = json.loads(capsys.readouterr().out)
    assert result["run_seed"] == 12345
    assert result["checker_version"] == 16
    assert_official_memory_config(result["scoring_config"])
    assert result["automatic_verdict"] is True
    assert result["expert_review_required"] is False
    assert result["provenance"]["submission_sha256"] == hashlib.sha256(
        submission.read_bytes()
    ).hexdigest()
    assert len(result["provenance"]["target_bundle_sha256"]) == 64
    assert result["provenance"]["problem_id"] == 1
    assert result["provenance"]["problem_name"] == "nc_area_qt_narayana_second_stat"
    assert result["provenance"]["evaluator_kind"] == "noncrossing"
    repository_commit = result["provenance"]["repository_commit"]
    assert repository_commit is None or (
        len(repository_commit) == 40
        and all(character in "0123456789abcdef" for character in repository_commit)
    )
    assert result["provenance"]["repository_dirty"] in (True, False, None)


def test_repository_provenance_marks_untracked_files_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_cli_module()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "tracked.txt"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=qtBench test",
            "-c",
            "user.email=qtbench@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)

    assert module._repository_provenance()["repository_dirty"] is False
    (tmp_path / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    assert module._repository_provenance()["repository_dirty"] is True


def test_problem_provenance_tolerates_non_utf8_metadata(tmp_path: Path) -> None:
    module = load_cli_module()
    (tmp_path / "metadata.json").write_bytes(b"\xff")

    assert module._problem_provenance(tmp_path, "example-kind") == {
        "problem_id": None,
        "problem_name": tmp_path.name,
        "evaluator_kind": "example-kind",
    }


def test_problem_provenance_tolerates_json_value_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_cli_module()
    (tmp_path / "metadata.json").write_text("{}", encoding="utf-8")

    def fail_parse(_document: str):
        raise ValueError("integer conversion limit exceeded")

    monkeypatch.setattr(module.json, "loads", fail_parse)

    assert module._problem_provenance(tmp_path, "example-kind") == {
        "problem_id": None,
        "problem_name": tmp_path.name,
        "evaluator_kind": "example-kind",
    }


@pytest.mark.parametrize("output_format", ["summary", "json"])
@pytest.mark.parametrize("result_shape", ["integer", "pair"])
def test_official_formats_report_json_unavailable_probe_integers(
    output_format: str,
    result_shape: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_cli_module()
    submission = tmp_path / "constant.py"
    submission.write_text("def statistic(partition):\n    return 0\n", encoding="utf-8")
    original_limit = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(640)
    huge = 10**640

    def evaluate(**_kwargs):
        if result_shape == "integer":
            calls = admission.adversarial_noncrossing_probes(8, seed=7)[:1]
            report = admission.ResourceReport(0.0, 0, (huge,))
            admission._validate_integer_probe_results(report, calls)
        else:
            calls = admission.adversarial_kostka_probes(8, seed=7)[:1]
            report = admission.ResourceReport(0.0, 0, ((0, huge),))
            admission._validate_pair_probe_results(report, calls)
        raise AssertionError("resource-result validation unexpectedly returned")

    monkeypatch.setattr(
        module,
        "parse_args",
        lambda: SimpleNamespace(
            kind="noncrossing", submission=submission, format=output_format
        ),
    )
    monkeypatch.setitem(
        module.STATISTIC_RUNNERS,
        "noncrossing",
        (evaluate, lambda _n, *, seed: (seed,)),
    )
    try:
        with pytest.raises(SystemExit) as exit_info:
            module.main()
    finally:
        sys.set_int_max_str_digits(original_limit)

    assert exit_info.value.code == 1
    captured = capsys.readouterr()
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err
    if output_format == "json":
        result = json.loads(captured.out)
        assert result["passed"] is False
        assert result["checker_stage"] == "gate_error"
        assert "official JSON output" in result["gate_error"]
    else:
        assert "did not pass" in captured.out
        assert "gate error" in captured.out
        assert "official JSON output" in captured.out


def test_scored_cli_rejects_fifo_without_waiting_for_eof(tmp_path: Path) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFOs are unavailable on this platform")
    submission = tmp_path / "submission.pipe"
    os.mkfifo(submission)

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "noncrossing",
            str(submission),
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert "regular file" in result["gate_error"]


def test_cli_requires_expert_review_for_promotion(tmp_path: Path) -> None:
    submission = tmp_path / "orbit_position.py"
    submission.write_text("def statistic(tableau):\n    return 0\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "promotion",
            str(submission),
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["passed"] is False
    assert result["automatic_verdict"] is None
    assert result["expert_review_required"] is True
    assert result["checker_stage"] == "expert_review"
    assert result["checker_version"] == admission.CHECKER_VERSION
    assert_official_memory_config(result["scoring_config"])
    assert "expert source review" in result["review_reason"]
    assert "gate_error" not in result
    assert result["provenance"]["problem_id"] == 22
    assert result["provenance"]["problem_name"] == "syt_promotion_csp_q_stat"
    assert result["provenance"]["evaluator_kind"] == "promotion"


def test_cli_defaults_to_a_short_human_readable_report(tmp_path: Path) -> None:
    # The full result carries one record per public case; problem 1 alone has
    # tens of thousands of lines of it.  The default view has to stay readable.
    submission = tmp_path / "constant.py"
    submission.write_text("def statistic(partition):\n    return 0\n", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "noncrossing", str(submission)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert len(completed.stdout.splitlines()) < 20
    assert "did not pass" in completed.stdout
    assert "nc_area_qt_narayana_second_stat (id 1), kind noncrossing" in completed.stdout
    assert "scoring      official (fixed configuration v2)" in completed.stdout
    assert "run seed" in completed.stdout
    assert "necessary, not a sufficient, condition" in completed.stdout
    with pytest.raises(json.JSONDecodeError):
        json.loads(completed.stdout)


def test_summary_escapes_untrusted_multiline_and_surrogate_errors() -> None:
    module = load_cli_module()
    lines = module._summary_lines(
        {
            "passed": False,
            "automatic_verdict": False,
            "expert_review_required": False,
            "checker_stage": "gate_error",
            "run_seed": 1,
            "gate_error": "first\nsecond\ud800",
        }
    )

    assert lines[-1] == r"  gate error   first\nsecond\ud800"


def test_cli_renders_macdonald_shape_failures(tmp_path: Path) -> None:
    submission = tmp_path / "identity.py"
    submission.write_text(
        "def forward(filling):\n    return filling\n\n"
        "def inverse(filling):\n    return filling\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "macdonald-fillings",
            str(submission),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "first wrong case shape=[2, 2]" in completed.stdout
    assert "invalid filling" in completed.stdout
