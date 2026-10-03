from __future__ import annotations

import json
from pathlib import Path
import sys
import time

import pytest

from qtbench_inference.protocol import JudgeCallResult, SubmissionGate, SubmissionRequest
from qtbench_inference.runtime import LaunchConfig, OfficialChecker
from qtbench_inference.workspace import repository_revision, resolve_problem


APPROVE = json.dumps(
    {
        "verdict": "approve",
        "category": "legitimate",
        "reason": "Offline test approval for the committed calibration solution.",
        "strategy_summary": "Use the known intrinsic calibration statistic.",
    }
)


class FakeApprovingJudge:
    def __init__(self):
        self.call_count = 0

    def evaluate(self, packet, *, deadline_monotonic, evidence_directory):
        self.call_count += 1
        receipt = json.loads((evidence_directory / "checker-result.json").read_text())
        assert receipt["report"]["passed"] is True
        assert receipt["source_sha256"] == packet["submission"]["source_sha256"]
        return JudgeCallResult("completed", APPROVE, 0.0, metadata={"provider": "fake"})


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux containment")
@pytest.mark.parametrize("valid", [True, False])
def test_real_checker_gates_fake_judge(tmp_path: Path, valid: bool) -> None:
    """Exercise the full judge gate without making a provider call."""

    repo = Path(__file__).resolve().parents[2]
    problem = resolve_problem(repo, "1")
    revision = repository_revision(repo)
    config = LaunchConfig(
        repo=repo,
        state_root=tmp_path / "state",
        run=tmp_path / "run",
        codex=Path("/bin/false"),
        auth_home=tmp_path / "auth",
        problem=problem,
        solver_model="unused",
        solver_effort="unused",
        judge_model="unused",
        judge_effort="unused",
        wall_budget_seconds=60,
        judge_timeout_seconds=10,
        checker_timeout_seconds=60,
        web_search=False,
    )
    example = "noncrossing_calibration_submission.py" if valid else "constant_zero_submission.py"
    source = (repo / "examples" / example).read_text()
    judge = FakeApprovingJudge()
    request = SubmissionRequest.create(
        submission_id="s0001",
        source=source,
        description="Use the intrinsic area statistic from the solved calibration problem.",
        derivation="The problem statement proves that area has the required distribution.",
    )
    gate = SubmissionGate(
        run=config.run,
        problem_context=problem.judge_context(),
        judge=judge,
        checker=OfficialChecker(config, revision),
        judge_max_seconds=10,
        checker_max_seconds=60,
    )

    response = gate.process(
        request, run_deadline_monotonic=time.monotonic() + 60
    )

    assert response["verdict"] == ("approve" if valid else "reject")
    assert response["judge_invoked"] is valid
    assert judge.call_count == int(valid)
    assert response["checker_invoked"] is True
    checker_result = response["checker_result"]
    assert checker_result["exit_code"] == (0 if valid else 1)
    assert checker_result["report"]["passed"] is valid
    assert checker_result["report"]["provenance"]["repository_commit"] == revision
    assert checker_result["report"]["provenance"]["repository_dirty"] is False
