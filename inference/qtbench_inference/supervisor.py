#!/usr/bin/env python3
"""Linux subreaper supervisor for one inference subprocess tree."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


PR_SET_PDEATHSIG = 1
PR_SET_CHILD_SUBREAPER = 36
_STOPPING_SIGNAL = 0


def _handle_signal(signum: int, _frame: object) -> None:
    global _STOPPING_SIGNAL
    if not _STOPPING_SIGNAL:
        _STOPPING_SIGNAL = signum


def _prctl(option: int, value: int) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(option, value, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _proc_identity(pid: int) -> tuple[int, int] | None:
    """Return (parent pid, start ticks) without confusing spaces in comm."""

    try:
        raw = (Path("/proc") / str(pid) / "stat").read_text(encoding="utf-8")
    except (FileNotFoundError, ProcessLookupError, PermissionError, OSError):
        return None
    closing = raw.rfind(")")
    if closing < 0:
        return None
    fields = raw[closing + 2 :].split()
    if len(fields) < 20:
        return None
    try:
        return int(fields[1]), int(fields[19])
    except ValueError:
        return None


def _all_processes() -> dict[int, tuple[int, int]]:
    records: dict[int, tuple[int, int]] = {}
    try:
        entries = os.scandir("/proc")
    except OSError:
        return records
    with entries:
        for entry in entries:
            if not entry.name.isdecimal():
                continue
            pid = int(entry.name)
            identity = _proc_identity(pid)
            if identity is not None:
                records[pid] = identity
    return records


def _descendants(root_pid: int) -> dict[int, int]:
    records = _all_processes()
    frontier = {root_pid}
    descendants: dict[int, int] = {}
    while frontier:
        children = {
            pid
            for pid, (parent, _started) in records.items()
            if parent in frontier and pid not in descendants
        }
        if not children:
            break
        for pid in children:
            descendants[pid] = records[pid][1]
        frontier = children
    return descendants


def _signal_identity(pid: int, started: int, signum: int) -> None:
    current = _proc_identity(pid)
    if current is None or current[1] != started:
        return
    try:
        os.kill(pid, signum)
    except (ProcessLookupError, PermissionError):
        pass


def _reap_available() -> bool:
    """Reap adopted children; return whether any child still exists."""

    child_exists = False
    while True:
        try:
            pid, _status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return child_exists
        except InterruptedError:
            continue
        if pid == 0:
            return True


def _terminate_descendants(grace_seconds: float = 0.2, kill_seconds: float = 3.0) -> bool:
    root_pid = os.getpid()
    identities: dict[int, int] = {}

    # Give every current descendant a short graceful signal, including processes
    # that changed session or process group.
    for _ in range(4):
        identities.update(_descendants(root_pid))
        for pid, started in identities.items():
            _signal_identity(pid, started, signal.SIGTERM)
        time.sleep(grace_seconds / 4)
        _reap_available()

    # Freeze repeatedly until the process set stabilizes. Once all known tasks
    # are stopped they cannot fork while the final identity-checked kill runs.
    stable_rounds = 0
    previous: set[tuple[int, int]] = set()
    freeze_deadline = time.monotonic() + 0.5
    while time.monotonic() < freeze_deadline and stable_rounds < 2:
        identities.update(_descendants(root_pid))
        current = set(identities.items())
        for pid, started in current:
            _signal_identity(pid, started, signal.SIGSTOP)
        if current == previous:
            stable_rounds += 1
        else:
            stable_rounds = 0
            previous = current
        time.sleep(0.01)

    for pid, started in identities.items():
        _signal_identity(pid, started, signal.SIGKILL)

    deadline = time.monotonic() + kill_seconds
    while time.monotonic() < deadline:
        _reap_available()
        remaining = _descendants(root_pid)
        if not remaining:
            # One more reap distinguishes no children from a live direct child
            # whose /proc record disappeared between scans.
            if not _reap_available():
                return True
        for pid, started in remaining.items():
            _signal_identity(pid, started, signal.SIGKILL)
        time.sleep(0.01)
    remaining = _descendants(root_pid)
    child_exists = _reap_available()
    return not remaining and not child_exists


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0] != "--" or len(arguments) == 1:
        print("usage: supervisor.py -- COMMAND [ARG ...]", file=sys.stderr)
        return 64
    if not sys.platform.startswith("linux") or not Path("/proc/self/stat").is_file():
        print("qtBench inference containment requires Linux /proc", file=sys.stderr)
        return 69

    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, _handle_signal)
    parent_pid = os.getppid()
    try:
        _prctl(PR_SET_CHILD_SUBREAPER, 1)
        _prctl(PR_SET_PDEATHSIG, signal.SIGTERM)
    except OSError as error:
        print(f"qtBench inference containment setup failed: {error}", file=sys.stderr)
        return 69
    if os.getppid() != parent_pid:
        return 143

    child = subprocess.Popen(arguments[1:])
    returncode: int | None = None
    while not _STOPPING_SIGNAL:
        returncode = child.poll()
        if returncode is not None:
            break
        time.sleep(0.02)

    cleaned = _terminate_descendants()
    if not cleaned:
        print("qtBench inference containment could not reap every descendant", file=sys.stderr)
        return 70
    if _STOPPING_SIGNAL:
        return 128 + _STOPPING_SIGNAL
    return int(returncode or 0)


if __name__ == "__main__":
    raise SystemExit(main())
