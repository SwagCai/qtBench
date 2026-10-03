from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from qtbench_inference import runtime


def test_run_solver_returns_approved_candidate_fields(
    tmp_path: Path, monkeypatch
) -> None:
    run = tmp_path / "run"
    run.mkdir()
    broker = SimpleNamespace(approved_response=None)
    calls = 0

    def approved_segment(config, received_broker, *, segment, run_deadline):
        nonlocal calls
        calls += 1
        received_broker.approved_response = {
            "submission_id": "s0007",
            "source_sha256": "a" * 64,
        }
        return 0.01, 0, False, True

    monkeypatch.setattr(runtime, "_launch_solver_segment", approved_segment)
    config = SimpleNamespace(run=run, wall_budget_seconds=60.0)

    result = runtime.run_solver(config, broker)

    assert calls == 1
    assert result["status"] == "approved"
    assert result["approved_submission_id"] == "s0007"
    assert result["approved_source_sha256"] == "a" * 64
    assert result["approved_source_path"] == str(
        run / "submissions/s0007/source.py"
    )
