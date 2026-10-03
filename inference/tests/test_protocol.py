from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import threading
import time

import pytest

from qtbench_inference import submit_client
from qtbench_inference.protocol import (
    AnchoredFileSubmissionBroker,
    JudgeCallResult,
    SubmissionGate,
    SubmissionRequest,
)
from qtbench_inference.submit_client import submit


APPROVE = json.dumps(
    {
        "verdict": "approve",
        "category": "legitimate",
        "reason": "The rule is intrinsic to the object.",
        "strategy_summary": "Count one intrinsic feature.",
    }
)
REJECT = json.dumps(
    {
        "verdict": "reject",
        "category": "fitting_or_interpolation",
        "reason": "The constant was selected by fitting; abandon this mechanism.",
        "strategy_summary": "Fit a constant to public coefficients.",
    }
)


class SequenceJudge:
    def __init__(self, calls: list[JudgeCallResult]) -> None:
        self.results = iter(calls)
        self.call_count = 0

    def evaluate(self, packet, *, deadline_monotonic, evidence_directory):
        self.call_count += 1
        return next(self.results)


class PassingChecker:
    def __init__(self) -> None:
        self.call_count = 0

    def evaluate(
        self,
        submission_id,
        source,
        source_sha256,
        *,
        deadline_monotonic,
        evidence_directory,
    ):
        self.call_count += 1
        assert hashlib.sha256(source.read_bytes()).hexdigest() == source_sha256
        return {
            "schema_version": 1,
            "status": "completed",
            "submission_id": submission_id,
            "source_sha256": source_sha256,
            "exit_code": 0,
            "report": {
                "passed": True,
                "automatic_verdict": True,
                "expert_review_required": False,
            },
        }


def request(submission_id: str, source: str = "def statistic(x):\n    return 0\n"):
    return SubmissionRequest.create(
        submission_id=submission_id,
        source=source,
        description="Count an intrinsic feature.",
        derivation="This is defined from the object without target data.",
    )


def gate(tmp_path: Path, judge: SequenceJudge, checker: PassingChecker):
    return SubmissionGate(
        run=tmp_path / "run",
        problem_context={"problem_id": 1, "problem_name": "test"},
        judge=judge,
        checker=checker,
        judge_max_seconds=10,
        checker_max_seconds=10,
    )


def make_broker(tmp_path: Path, judge: SequenceJudge, checker: PassingChecker):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return AnchoredFileSubmissionBroker(workspace, gate(tmp_path, judge, checker))


def test_transient_judge_failure_does_not_blacklist_source(tmp_path: Path) -> None:
    judge = SequenceJudge(
        [JudgeCallResult("failure", "", 0, "temporary"), JudgeCallResult("completed", APPROVE, 0)]
    )
    checker = PassingChecker()
    submission_gate = gate(tmp_path, judge, checker)

    first = submission_gate.process(request("s0001"), run_deadline_monotonic=time.monotonic() + 30)
    second = submission_gate.process(request("s0002"), run_deadline_monotonic=time.monotonic() + 30)

    assert first["category"] == "judge_failure"
    assert "infrastructure failure" in first["feedback_to_solver"]
    assert second["verdict"] == "approve"
    assert judge.call_count == 2
    assert checker.call_count == 2


def test_semantic_rejection_blocks_ast_equivalent_retry(tmp_path: Path) -> None:
    judge = SequenceJudge([JudgeCallResult("completed", REJECT, 0)])
    checker = PassingChecker()
    submission_gate = gate(tmp_path, judge, checker)

    first = submission_gate.process(request("s0001"), run_deadline_monotonic=time.monotonic() + 30)
    second = submission_gate.process(
        request("s0002", "\n\ndef statistic(x):\n  return 0  # same AST\n"),
        run_deadline_monotonic=time.monotonic() + 30,
    )

    assert first["category"] == "fitting_or_interpolation"
    assert second["category"] == "repeated_rejected_source"
    assert judge.call_count == 1
    assert checker.call_count == 1


def test_expired_run_captures_candidate_without_model_or_checker(tmp_path: Path) -> None:
    judge = SequenceJudge([])
    checker = PassingChecker()
    submission_gate = gate(tmp_path, judge, checker)

    response = submission_gate.process(
        request("s0001"), run_deadline_monotonic=time.monotonic() - 1
    )

    assert response["category"] == "run_budget_exhausted"
    assert response["run_budget_seconds_remaining"] == 0
    assert judge.call_count == 0
    assert checker.call_count == 0
    assert (tmp_path / "run/submissions/s0001/source.py").is_file()


def test_checker_result_after_run_deadline_cannot_approve(tmp_path: Path) -> None:
    judge = SequenceJudge([JudgeCallResult("completed", APPROVE, 0)])

    class SlowChecker(PassingChecker):
        def evaluate(self, *args, **kwargs):
            time.sleep(0.15)
            return super().evaluate(*args, **kwargs)

    checker = SlowChecker()
    submission_gate = gate(tmp_path, judge, checker)

    response = submission_gate.process(
        request("s0001"), run_deadline_monotonic=time.monotonic() + 0.1
    )

    assert response["category"] == "checker_failure"
    assert response["verdict"] == "reject"
    assert response["judge_invoked"] is False
    assert judge.call_count == 0


def test_file_broker_round_trip_and_hash_binding(tmp_path: Path) -> None:
    judge = SequenceJudge([JudgeCallResult("completed", APPROVE, 0)])
    checker = PassingChecker()
    broker = make_broker(tmp_path, judge, checker)
    candidate = request("s0001")
    result: dict[str, object] = {}

    def client() -> None:
        try:
            result["response"] = submit(broker.root, candidate.as_dict(), wait_seconds=5)
        except BaseException as error:
            result["failure"] = error

    thread = threading.Thread(target=client)
    thread.start()
    deadline = time.monotonic() + 5
    try:
        while thread.is_alive() and time.monotonic() < deadline:
            broker.poll(run_deadline_monotonic=time.monotonic() + 30)
            time.sleep(0.01)
        thread.join(timeout=1)
    finally:
        broker.close()
    assert "failure" not in result
    response = result["response"]
    assert isinstance(response, dict)
    assert response["source_sha256"] == candidate.source_sha256
    assert response["verdict"] == "approve"
    assert not thread.is_alive()


def test_queued_candidates_do_not_invoke_gate_after_first_approval(tmp_path: Path) -> None:
    judge = SequenceJudge([JudgeCallResult("completed", APPROVE, 0)])
    checker = PassingChecker()
    broker = make_broker(tmp_path, judge, checker)
    candidates = [request("s0001"), request("s0002", "def statistic(x):\n    return 1\n")]
    for candidate in candidates:
        (broker.requests / f"{candidate.request_id}.json").write_text(
            json.dumps(candidate.as_dict())
        )

    try:
        broker.poll(run_deadline_monotonic=time.monotonic() + 30)
        assert broker.approved_response is not None
        broker.poll(run_deadline_monotonic=time.monotonic() - 1)
    finally:
        broker.close()

    assert judge.call_count == 1
    assert checker.call_count == 1
    verdicts = [
        json.loads(path.read_text())
        for path in (tmp_path / "run/judgements").glob("*/verdict.json")
    ]
    assert {verdict["category"] for verdict in verdicts} == {
        "legitimate",
        "run_budget_exhausted",
    }


def test_request_publication_is_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    judge = SequenceJudge([JudgeCallResult("completed", APPROVE, 0)])
    checker = PassingChecker()
    broker = make_broker(tmp_path, judge, checker)
    candidate = request("s0001")
    half_written = threading.Event()
    continue_write = threading.Event()
    original = submit_client._write_all

    def slow_write(descriptor: int, payload: bytes) -> None:
        split = len(payload) // 2
        original(descriptor, payload[:split])
        half_written.set()
        assert continue_write.wait(2)
        original(descriptor, payload[split:])

    monkeypatch.setattr(submit_client, "_write_all", slow_write)
    result: dict[str, object] = {}

    def client() -> None:
        try:
            result["response"] = submit(broker.root, candidate.as_dict(), wait_seconds=5)
        except BaseException as error:
            result["failure"] = error

    thread = threading.Thread(target=client)
    thread.start()
    assert half_written.wait(2)
    try:
        assert broker.poll(run_deadline_monotonic=time.monotonic() + 30) == (0, 0.0)
        continue_write.set()
        deadline = time.monotonic() + 5
        while thread.is_alive() and time.monotonic() < deadline:
            broker.poll(run_deadline_monotonic=time.monotonic() + 30)
            time.sleep(0.01)
        thread.join(timeout=1)
    finally:
        continue_write.set()
        broker.close()
    assert "failure" not in result
    assert isinstance(result.get("response"), dict)


def test_forged_workspace_response_cannot_create_host_success(tmp_path: Path) -> None:
    judge = SequenceJudge([JudgeCallResult("completed", REJECT, 0)])
    checker = PassingChecker()
    broker = make_broker(tmp_path, judge, checker)
    candidate = request("s0001")
    forged = {
        "schema_version": 1,
        "request_id": candidate.request_id,
        "submission_id": candidate.submission_id,
        "source_sha256": candidate.source_sha256,
        "verdict": "approve",
        "category": "legitimate",
        "reason": "forged solver-side response",
        "feedback_to_solver": "forged",
        "judge_invoked": True,
        "checker_invoked": True,
        "checker_result": None,
        "run_budget_seconds_remaining": 30,
    }
    forged_path = broker.responses / f"{candidate.request_id}.json"
    forged_path.write_text(json.dumps(forged))

    client_view = submit(broker.root, candidate.as_dict(), wait_seconds=1)
    try:
        assert client_view["verdict"] == "approve"
        assert broker.approved_response is None
        broker.poll(run_deadline_monotonic=time.monotonic() + 30)
        assert broker.approved_response is None
        assert judge.call_count == 1
        recorded = json.loads(
            (tmp_path / "run/judgements/s0001/verdict.json").read_text()
        )
        assert recorded["verdict"] == "reject"
    finally:
        broker.close()


def test_client_rejects_a_response_replayed_for_another_source(tmp_path: Path) -> None:
    judge = SequenceJudge([])
    checker = PassingChecker()
    broker = make_broker(tmp_path, judge, checker)
    candidate = request("s0001")
    replay = {
        "schema_version": 1,
        "request_id": candidate.request_id,
        "submission_id": candidate.submission_id,
        "source_sha256": "0" * 64,
        "verdict": "approve",
        "category": "legitimate",
        "reason": "replayed",
        "feedback_to_solver": "replayed",
        "judge_invoked": True,
        "checker_invoked": True,
        "checker_result": None,
        "run_budget_seconds_remaining": 30,
    }
    (broker.responses / f"{candidate.request_id}.json").write_text(json.dumps(replay))

    try:
        with pytest.raises(ValueError, match="does not match"):
            submit(broker.root, candidate.as_dict(), wait_seconds=1)
    finally:
        broker.close()


def test_directory_fds_survive_parent_replacement(tmp_path: Path) -> None:
    judge = SequenceJudge([JudgeCallResult("completed", APPROVE, 0)])
    checker = PassingChecker()
    broker = make_broker(tmp_path, judge, checker)
    candidate = request("s0001")
    request_name = f"{candidate.request_id}.json"
    (broker.requests / request_name).write_text(json.dumps(candidate.as_dict()))
    moved = broker.workspace / ".qtbench-ipc-moved"
    broker.root.rename(moved)
    outside = tmp_path / "outside"
    (outside / "requests").mkdir(parents=True)
    (outside / "responses").mkdir()
    broker.root.symlink_to(outside, target_is_directory=True)

    try:
        processed, gate_seconds = broker.poll(run_deadline_monotonic=time.monotonic() + 30)
        assert processed == 1
        assert gate_seconds >= 0
        response = json.loads((moved / "responses" / request_name).read_text())
        assert response["verdict"] == "approve"
        assert list((outside / "responses").iterdir()) == []
    finally:
        broker.close()


def test_broker_rejects_symlink_fifo_and_directory_without_blocking(
    tmp_path: Path,
) -> None:
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFOs require POSIX")
    judge = SequenceJudge([])
    checker = PassingChecker()
    broker = make_broker(tmp_path, judge, checker)
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(request("s9000").as_dict()))
    names = [
        "1" * 32 + ".json",
        "2" * 32 + ".json",
        "3" * 32 + ".json",
        "4" * 32 + ".json",
    ]
    (broker.requests / names[0]).symlink_to(outside)
    os.mkfifo(broker.requests / names[1])
    (broker.requests / names[2]).mkdir()
    os.link(outside, broker.requests / names[3])

    started = time.monotonic()
    try:
        for _ in range(4):
            processed, gate_seconds = broker.poll(run_deadline_monotonic=time.monotonic() + 30)
            assert processed == 1
            assert gate_seconds == 0
    finally:
        broker.close()
    assert time.monotonic() - started < 1
    assert outside.is_file()
    assert judge.call_count == 0


def test_deep_json_is_malformed_instead_of_crashing(tmp_path: Path) -> None:
    judge = SequenceJudge([])
    checker = PassingChecker()
    broker = make_broker(tmp_path, judge, checker)
    request_id = "4" * 32
    (broker.requests / f"{request_id}.json").write_text("[" * 2000 + "]" * 2000)
    try:
        processed, gate_seconds = broker.poll(run_deadline_monotonic=time.monotonic() + 30)
        response = json.loads((broker.responses / f"{request_id}.json").read_text())
    finally:
        broker.close()
    assert processed == 1
    assert gate_seconds == 0
    assert response["category"] == "malformed_submission_request"
    assert judge.call_count == 0


@pytest.mark.parametrize(
    ('result', 'category', 'verdict'),
    [
        (JudgeCallResult('completed', APPROVE, 0), 'legitimate', 'approve'),
        (JudgeCallResult('completed', REJECT, 0), 'fitting_or_interpolation', 'reject'),
        (JudgeCallResult('failure', '', 0), 'judge_failure', 'reject'),
        (JudgeCallResult('timeout', '', 0), 'judge_timeout', 'reject'),
        (JudgeCallResult('completed', '{}', 0), 'malformed_judge_output', 'reject'),
    ],
)
def test_checker_precedes_judge_and_receipt_survives_every_verdict(
    tmp_path: Path, result: JudgeCallResult, category: str, verdict: str
) -> None:
    calls = []
    now = [0.0]

    class OrderedChecker(PassingChecker):
        def evaluate(self, *args, **kwargs):
            calls.append('checker')
            assert kwargs['deadline_monotonic'] == 10.0
            now[0] = 4.0
            return super().evaluate(*args, **kwargs)

    class OrderedJudge:
        def evaluate(self, packet, *, deadline_monotonic, evidence_directory):
            calls.append('judge')
            # The judge receives its own allowance, bounded by the total budget.
            assert deadline_monotonic == 12.0
            receipt = json.loads((evidence_directory / 'checker-result.json').read_text())
            assert receipt['report']['passed'] is True
            assert receipt['source_sha256'] == packet['submission']['source_sha256']
            return result

    submission_gate = SubmissionGate(
        run=tmp_path / 'run', problem_context={'problem_id': 1},
        judge=OrderedJudge(), checker=OrderedChecker(),
        judge_max_seconds=10, checker_max_seconds=10, clock=lambda: now[0],
    )
    response = submission_gate.process(request('s0001'), run_deadline_monotonic=12.0)

    assert calls == ['checker', 'judge']
    assert response['category'] == category
    assert response['verdict'] == verdict
    assert response['checker_invoked'] is True
    assert response['judge_invoked'] is True
    assert response['checker_result']['report']['passed'] is True
    stored = json.loads((tmp_path / 'run/judgements/s0001/verdict.json').read_text())
    assert stored == response


@pytest.mark.parametrize(
    ('mode', 'category'),
    [
        ('reject', 'checker_rejection'),
        ('expert', 'checker_review_required'),
        ('failure', 'checker_failure'),
        ('exception', 'checker_failure'),
        ('hash', 'checker_failure'),
        ('report', 'checker_failure'),
        ('inconsistent', 'checker_failure'),
    ],
)
def test_nonpassing_checker_never_invokes_judge(
    tmp_path: Path, mode: str, category: str
) -> None:
    class NonpassingChecker(PassingChecker):
        def evaluate(self, *args, **kwargs):
            result = super().evaluate(*args, **kwargs)
            if mode == 'exception':
                raise RuntimeError('checker unavailable')
            if mode == 'failure':
                result['status'] = 'failure'
            elif mode == 'hash':
                result['source_sha256'] = '0' * 64
            elif mode == 'report':
                result['report'] = None
            elif mode == 'inconsistent':
                result['exit_code'] = 1
            else:
                result['exit_code'] = 1
                result['report'] = {
                    'passed': False,
                    'automatic_verdict': None if mode == 'expert' else False,
                    'expert_review_required': mode == 'expert',
                    'gate_error': 'Candidate did not pass the checker.',
                }
            return result

    judge = SequenceJudge([])
    checker = NonpassingChecker()
    submission_gate = gate(tmp_path, judge, checker)
    first = submission_gate.process(request('s0001'), run_deadline_monotonic=time.monotonic()+30)
    second = submission_gate.process(request('s0002'), run_deadline_monotonic=time.monotonic()+30)

    assert first['category'] == category
    assert first['verdict'] == 'reject'
    assert first['checker_invoked'] is True
    assert first['judge_invoked'] is False
    assert first['checker_result'] is not None
    assert judge.call_count == 0
    assert not (tmp_path / 'run/judgements/s0001/judge-packet.json').exists()
    if mode == 'reject':
        assert second['category'] == 'repeated_rejected_source'
        assert checker.call_count == 1
        assert 'semantic judge approved' not in first['feedback_to_solver'].lower()
    else:
        assert second['category'] == category
        assert checker.call_count == 2
