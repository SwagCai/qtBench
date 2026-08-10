from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "evaluate" / "evaluate_submission.py"
PROBLEM = (
    ROOT
    / "problems"
    / "t_statistic_discovery"
    / "nc_area_qt_narayana_second_stat"
)
MLD_PROBLEM = (
    ROOT
    / "problems"
    / "t_statistic_discovery"
    / "mld_area_qt_super_nabla_second_stat"
)
CALIBRATION = ROOT / "examples" / "noncrossing_calibration_submission.py"


def test_json_output_reports_a_passing_submission() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(PROBLEM),
            str(CALIBRATION),
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    result = json.loads(completed.stdout)
    assert result["passed"] is True
    assert result["correct_cases"] == result["total_cases"]


def test_json_output_is_not_corrupted_by_submission_stdout(tmp_path: Path) -> None:
    submission = tmp_path / "noisy_submission.py"
    submission.write_text(
        'print("submission diagnostic")\n\n'
        "def statistic(partition):\n"
        "    return 0\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(PROBLEM),
            str(submission),
            "--q-equals-1",
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
    assert "submission diagnostic" in completed.stderr


def test_diagnostic_cli_executes_submission_with_caller_privileges(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "diagnostic-executed"
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
            str(PROBLEM),
            str(submission),
            "--q-equals-1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert marker.read_text(encoding="utf-8") == "executed"


def test_diagnostic_cli_rejects_another_problem_family() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(MLD_PROBLEM),
            str(CALIBRATION),
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "only supports problem 1" in completed.stderr
    assert "mld_area_qt_super_nabla_second_stat (id 10)" in completed.stderr
    assert "Traceback" not in completed.stderr


def test_diagnostic_cli_help_warns_about_unrestricted_execution() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "trusted" in completed.stdout
    assert "caller's privileges" in completed.stdout
    assert "Problem 1" in completed.stdout
