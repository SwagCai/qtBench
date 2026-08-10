from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest

import qtbench.evaluation.admission as admission
from qtbench.evaluation import ResourceGateError


def test_resident_bytes_reports_the_current_process() -> None:
    assert admission._resident_bytes(os.getpid()) > 0


def test_windows_resident_bytes_dispatches_to_the_native_reader(monkeypatch) -> None:
    monkeypatch.setattr(admission.sys, "platform", "win32")
    monkeypatch.setattr(admission, "_windows_resident_bytes", lambda pid: pid + 17)

    assert admission._resident_bytes(25) == 42


@pytest.mark.skipif(sys.platform != "win32", reason="requires the Windows API")
def test_windows_native_reader_reports_the_current_working_set() -> None:
    assert admission._windows_resident_bytes(os.getpid()) > 0


@pytest.mark.parametrize(
    ("result", "message"),
    [
        (SimpleNamespace(returncode=1, stdout=""), "could not measure RSS"),
        (SimpleNamespace(returncode=0, stdout=""), "returned no RSS"),
        (SimpleNamespace(returncode=0, stdout="not-a-number"), "invalid RSS"),
    ],
)
def test_ps_rss_failures_are_not_treated_as_zero(
    monkeypatch, result, message
) -> None:
    class MissingStatm:
        def exists(self) -> bool:
            return False

    monkeypatch.setattr(admission.sys, "platform", "darwin")
    monkeypatch.setattr(admission, "Path", lambda _path: MissingStatm())
    monkeypatch.setattr(
        admission.shutil, "which", lambda *_args, **_kwargs: "/bin/ps"
    )
    monkeypatch.setattr(admission.subprocess, "run", lambda *_args, **_kwargs: result)

    with pytest.raises(OSError, match=message):
        admission._resident_bytes(123)


def test_ps_rss_uses_a_system_path_instead_of_inherited_path(monkeypatch) -> None:
    class MissingStatm:
        def exists(self) -> bool:
            return False

    command = None

    def system_ps(executable, *, path):
        assert executable == "ps"
        assert path == os.defpath
        return "/bin/ps"

    def run(args, **_kwargs):
        nonlocal command
        command = args
        return SimpleNamespace(returncode=0, stdout="42\n")

    monkeypatch.setattr(admission.sys, "platform", "darwin")
    monkeypatch.setattr(admission, "Path", lambda _path: MissingStatm())
    monkeypatch.setattr(admission.shutil, "which", system_ps)
    monkeypatch.setattr(admission.subprocess, "run", run)

    assert admission._resident_bytes(123) == 42 * 1_024
    assert command == ["/bin/ps", "-o", "rss=", "-p", "123"]


def test_ps_rss_timeout_fails_closed(monkeypatch) -> None:
    class MissingStatm:
        def exists(self) -> bool:
            return False

    def timed_out(*_args, **kwargs):
        assert kwargs["timeout"] == 0.25
        raise admission.subprocess.TimeoutExpired("/bin/ps", 0.25)

    monkeypatch.setattr(admission.sys, "platform", "darwin")
    monkeypatch.setattr(admission, "Path", lambda _path: MissingStatm())
    monkeypatch.setattr(admission.shutil, "which", lambda *_args, **_kwargs: "/bin/ps")
    monkeypatch.setattr(admission.subprocess, "run", timed_out)

    with pytest.raises(OSError, match="timed out"):
        admission._resident_bytes(123, timeout_seconds=0.25)


def test_ps_rss_fails_closed_when_system_ps_is_unavailable(monkeypatch) -> None:
    class MissingStatm:
        def exists(self) -> bool:
            return False

    def missing_ps(executable, *, path):
        assert executable == "ps"
        assert path == os.defpath
        return None

    monkeypatch.setattr(admission.sys, "platform", "darwin")
    monkeypatch.setattr(admission, "Path", lambda _path: MissingStatm())
    monkeypatch.setattr(admission.shutil, "which", missing_ps)
    monkeypatch.setattr(
        admission.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("subprocess must not run"),
    )

    with pytest.raises(OSError, match="system ps is unavailable"):
        admission._resident_bytes(123)


def test_missing_sigxcpu_falls_back_to_a_portable_child_error(monkeypatch) -> None:
    class ClosedParent:
        def poll(self, _timeout):
            return True

        def recv_bytes(self, _limit):
            raise EOFError

    class FailedProcess:
        exitcode = 1

        def is_alive(self):
            return False

        def join(self, timeout=None):
            assert timeout == 0.0
            return None

    monkeypatch.delattr(admission.signal, "SIGXCPU", raising=False)

    with pytest.raises(ResourceGateError, match="returned no valid result"):
        admission._wait_for_child(
            ClosedParent(),
            FailedProcess(),
            timeout_seconds=1.0,
            max_process_bytes=256_000_000,
            label="platform probe",
        )


def test_wall_clock_timeout_is_reported_without_signals(monkeypatch) -> None:
    class NeverReadyParent:
        def poll(self, _timeout):
            return False

    class LiveProcess:
        terminated = False

    clock = iter((10.0, 11.1))
    monkeypatch.setattr(admission.time, "monotonic", lambda: next(clock))
    process = LiveProcess()

    with pytest.raises(ResourceGateError, match="exceeded 1.000 seconds"):
        admission._wait_for_child(
            NeverReadyParent(),
            process,
            timeout_seconds=1.0,
            max_process_bytes=256_000_000,
            label="platform probe",
        )

    assert process.terminated is False


def test_rss_limit_is_reported_to_the_process_owner(monkeypatch) -> None:
    class WaitingParent:
        def poll(self, _timeout):
            return False

    class LiveProcess:
        pid = 123
        terminated = False

    process = LiveProcess()
    monkeypatch.setattr(admission, "_resident_bytes", lambda _pid, **_kwargs: 257)

    with pytest.raises(ResourceGateError, match="used 257 process bytes"):
        admission._wait_for_child(
            WaitingParent(),
            process,
            timeout_seconds=1.0,
            max_process_bytes=256,
            label="platform probe",
        )

    assert process.terminated is False


def test_rss_measurement_failure_is_reported_to_the_process_owner(monkeypatch) -> None:
    class WaitingParent:
        def poll(self, _timeout):
            return False

    class LiveProcess:
        pid = 123
        terminated = False

    process = LiveProcess()

    def unavailable_rss(_pid, **_kwargs):
        raise OSError("RSS API unavailable")

    monkeypatch.setattr(admission, "_resident_bytes", unavailable_rss)

    with pytest.raises(ResourceGateError, match="could not measure worker memory"):
        admission._wait_for_child(
            WaitingParent(),
            process,
            timeout_seconds=1.0,
            max_process_bytes=256,
            label="platform probe",
        )

    assert process.terminated is False


def test_rss_command_timeout_is_capped_by_the_worker_deadline(monkeypatch) -> None:
    class WaitingParent:
        def poll(self, timeout):
            assert timeout == pytest.approx(0.05)
            return False

    class LiveProcess:
        pid = 123

    clock = iter((10.0, 10.25, 10.25))
    observed_timeout = None

    def unavailable_rss(_pid, *, timeout_seconds):
        nonlocal observed_timeout
        observed_timeout = timeout_seconds
        raise OSError("RSS API unavailable")

    monkeypatch.setattr(admission.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(admission, "_resident_bytes", unavailable_rss)

    with pytest.raises(ResourceGateError, match="could not measure worker memory"):
        admission._wait_for_child(
            WaitingParent(),
            LiveProcess(),
            timeout_seconds=0.5,
            max_process_bytes=256,
            label="platform probe",
            deadline=10.5,
        )

    assert observed_timeout == pytest.approx(0.25)


def test_aggregate_budget_rejects_incompatible_caps_before_worker_start(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admission,
        "_resident_bytes",
        lambda *_args, **_kwargs: pytest.fail("RSS must not be measured"),
    )
    monkeypatch.setattr(
        admission,
        "_multiprocessing_context",
        lambda: pytest.fail("worker context must not be created"),
    )

    with admission._aggregate_process_budget(
        max_parent_process_bytes=20,
        max_aggregate_process_bytes=30,
    ):
        with pytest.raises(ValueError, match="must not exceed"):
            admission._run_isolated(
                lambda: None,
                (),
                timeout_seconds=1.0,
                max_process_bytes=11,
                label="aggregate probe",
            )


def test_aggregate_preflight_reserves_ipc_before_worker_start(monkeypatch) -> None:
    context_created = False

    def context_must_not_be_created():
        nonlocal context_created
        context_created = True
        raise AssertionError("worker context must not be created")

    monkeypatch.setattr(admission, "_resident_bytes", lambda _pid: 2_000_001)
    monkeypatch.setattr(
        admission, "_multiprocessing_context", context_must_not_be_created
    )

    with admission._aggregate_process_budget(
        max_parent_process_bytes=10_000_000,
        max_aggregate_process_bytes=30_000_000,
    ):
        with pytest.raises(ResourceGateError, match="parent reserve"):
            admission._run_isolated(
                lambda: None,
                (),
                timeout_seconds=1.0,
                max_process_bytes=20_000_000,
                label="aggregate probe",
            )

    assert context_created is False


def test_aggregate_wait_rejects_the_combined_parent_and_worker_rss(
    monkeypatch,
) -> None:
    class ReadyParent:
        def poll(self, _timeout):
            return True

        def recv_bytes(self, limit):
            assert limit == admission._MAX_IPC_BYTES
            return b"encoded"

    class LiveProcess:
        pid = 123

    rss_samples = iter(
        (
            (123, 20),
            (os.getpid(), 15),
            (123, 21),
            (os.getpid(), 8_000_015),
        )
    )

    def resident_bytes(pid, **_kwargs):
        expected_pid, resident = next(rss_samples)
        assert pid == expected_pid
        return resident

    monkeypatch.setattr(admission, "_resident_bytes", resident_bytes)

    with pytest.raises(ResourceGateError, match="8000036 aggregate process bytes"):
        admission._wait_for_child(
            ReadyParent(),
            LiveProcess(),
            timeout_seconds=1.0,
            max_process_bytes=25,
            label="aggregate probe",
            aggregate_budget=admission._AggregateProcessBudget(
                max_parent_process_bytes=8_000_020,
                max_aggregate_process_bytes=8_000_035,
            ),
        )


def test_aggregate_wait_requires_ipc_headroom_before_receiving_payload(
    monkeypatch,
) -> None:
    class ReadyParent:
        polled = False
        received = False

        def poll(self, _timeout):
            self.polled = True
            return True

        def recv_bytes(self, _limit):
            self.received = True
            raise AssertionError("payload must not be received")

    class LiveProcess:
        pid = 123

    def resident_bytes(pid, **_kwargs):
        if pid == 123:
            return 1
        assert pid == os.getpid()
        return 2_000_001

    parent = ReadyParent()
    monkeypatch.setattr(admission, "_resident_bytes", resident_bytes)

    with pytest.raises(ResourceGateError, match="plus IPC headroom"):
        admission._wait_for_child(
            parent,
            LiveProcess(),
            timeout_seconds=1.0,
            max_process_bytes=20_000_000,
            label="aggregate probe",
            aggregate_budget=admission._AggregateProcessBudget(
                max_parent_process_bytes=10_000_000,
                max_aggregate_process_bytes=30_000_000,
            ),
        )

    assert parent.polled is True
    assert parent.received is False


def test_aggregate_wait_fails_closed_if_parent_rss_cannot_be_measured(
    monkeypatch,
) -> None:
    class WaitingParent:
        def poll(self, _timeout):
            return False

    class LiveProcess:
        pid = 123

    def resident_bytes(pid, **_kwargs):
        if pid == 123:
            return 10
        assert pid == os.getpid()
        raise OSError("RSS API unavailable")

    monkeypatch.setattr(admission, "_resident_bytes", resident_bytes)

    with pytest.raises(
        ResourceGateError, match="could not measure evaluator parent memory"
    ):
        admission._wait_for_child(
            WaitingParent(),
            LiveProcess(),
            timeout_seconds=1.0,
            max_process_bytes=20,
            label="aggregate probe",
            aggregate_budget=admission._AggregateProcessBudget(
                max_parent_process_bytes=20,
                max_aggregate_process_bytes=40,
            ),
        )
