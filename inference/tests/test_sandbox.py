from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import time

import pytest

from qtbench_inference.runtime import _require_private_directory, _terminate_process
from qtbench_inference.sandbox import (
    authenticate_api_key,
    codex_process_environment,
    contained_command,
    find_codex,
    permission_arguments,
    private_shell_environment,
)


def test_authentication_uses_private_file_store_and_key_stays_off_argv(
    private_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tmp_path = private_tmp_path
    fake = tmp_path / "codex"
    fake.write_text(
        """#!/usr/bin/env python3
import json, os, pathlib, sys
home = pathlib.Path(os.environ['CODEX_HOME'])
key = sys.stdin.read().strip()
(home / 'auth.json').write_text(json.dumps({'OPENAI_API_KEY': key, 'auth_mode': 'apikey'}))
(home / 'invocation.json').write_text(json.dumps({'argv': sys.argv, 'env': sorted(os.environ)}))
""",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    auth_home = tmp_path / "auth"
    secret = "unit-test-provider-secret"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    authenticate_api_key(fake, auth_home, secret)

    invocation = json.loads((auth_home / "invocation.json").read_text())
    assert all(secret not in argument for argument in invocation["argv"])
    assert "OPENAI_API_KEY" not in invocation["env"]
    assert stat.S_IMODE(auth_home.stat().st_mode) == 0o700
    assert stat.S_IMODE((auth_home / "auth.json").stat().st_mode) == 0o600
    assert "OPENAI_API_KEY" not in codex_process_environment(auth_home)


def test_runtime_validation_never_follows_solver_symlinks(
    private_tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # This unit test exercises runtime-path validation, not interpreter discovery.
    monkeypatch.setattr(
        "qtbench_inference.sandbox.sandbox_python", lambda: Path(sys.executable)
    )
    tmp_path = private_tmp_path
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    private_shell_environment(workspace, initialize=True)
    runtime_tmp = workspace / ".qtbench-runtime/tmp"
    shutil.rmtree(runtime_tmp)
    outside = tmp_path / "outside"
    outside.mkdir()
    outside.chmod(0o755)
    runtime_tmp.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="replaced"):
        private_shell_environment(workspace, initialize=False)

    assert stat.S_IMODE(outside.stat().st_mode) == 0o755


def test_permission_profile_disables_all_shell_network() -> None:
    arguments = " ".join(
        permission_arguments(writable=True, codex=Path("/usr/bin/true"))
    )

    assert "enabled=false" in arguments
    assert "unix_sockets" not in arguments


def test_npm_wrapper_resolves_native_runtime_without_granting_prefix(
    private_tmp_path: Path,
) -> None:
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "arm64": "aarch64"}.get(machine, machine)
    distributions = {
        ("linux", "x86_64"): ("codex-linux-x64", "x86_64-unknown-linux-musl"),
        ("linux", "aarch64"): ("codex-linux-arm64", "aarch64-unknown-linux-musl"),
        ("darwin", "x86_64"): ("codex-darwin-x64", "x86_64-apple-darwin"),
        ("darwin", "aarch64"): ("codex-darwin-arm64", "aarch64-apple-darwin"),
    }
    package_name, target = distributions[(sys.platform, machine)]
    package_root = private_tmp_path / "prefix/lib/node_modules/@openai/codex"
    wrapper = package_root / "bin/codex.js"
    runtime = (
        package_root / "node_modules/@openai" / package_name / "vendor" / target
    )
    native = runtime / "bin/codex"
    wrapper.parent.mkdir(parents=True)
    native.parent.mkdir(parents=True)
    wrapper.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    native.write_bytes(b"native")
    wrapper.chmod(0o755)
    native.chmod(0o755)
    linked_entrypoint = private_tmp_path / "prefix/bin/codex"
    linked_entrypoint.parent.mkdir(parents=True)
    linked_entrypoint.symlink_to(wrapper)

    resolved = find_codex(linked_entrypoint)
    arguments = " ".join(permission_arguments(writable=True, codex=resolved))

    assert resolved == native.resolve()
    assert f'"{runtime.resolve()}"="read"' in arguments
    assert f'"{package_root.resolve()}"="read"' not in arguments
    assert f'"{private_tmp_path.resolve()}"="read"' not in arguments


def test_standalone_codex_grants_only_the_executable(private_tmp_path: Path) -> None:
    native = private_tmp_path / "standalone/codex"
    native.parent.mkdir()
    native.write_bytes(b"native")
    native.chmod(0o755)

    resolved = find_codex(native)
    arguments = " ".join(permission_arguments(writable=False, codex=resolved))

    assert resolved == native.resolve()
    assert f'"{native.resolve()}"="read"' in arguments
    assert f'"{native.parent.resolve()}"="read"' not in arguments


def test_state_root_must_be_private_and_owned(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir(mode=0o777)
    state.chmod(0o777)

    with pytest.raises(ValueError, match="not group/world-writable"):
        _require_private_directory(state, "--state-root")


@pytest.mark.skipif(os.name != "posix", reason="process groups require POSIX")
def test_cleanup_kills_descendant_after_leader_exits(tmp_path: Path) -> None:
    child_path = tmp_path / "child.pid"
    process = subprocess.Popen(
        ["/bin/sh", "-c", f"sleep 30 & echo $! > {child_path!s}"],
        start_new_session=True,
    )
    process.wait(timeout=5)
    child_pid = int(child_path.read_text().strip())

    _terminate_process(process, 0.2)
    time.sleep(0.1)

    status = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(child_pid)],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert not status or status.startswith("Z")


@pytest.mark.skipif(os.name != "posix", reason="signal cleanup requires POSIX")
def test_sigterm_unwinds_through_process_group_cleanup(tmp_path: Path) -> None:
    child_path = tmp_path / "child.pid"
    script = tmp_path / "signal_cleanup.py"
    script.write_text(
        f"""
import signal, subprocess, time
from pathlib import Path
from qtbench_inference.runtime import TerminationRequested, _raise_termination, _terminate_process

signal.signal(signal.SIGTERM, _raise_termination)
child = subprocess.Popen(['sleep', '30'], start_new_session=True)
Path({str(child_path)!r}).write_text(str(child.pid))
try:
    time.sleep(30)
except TerminationRequested:
    pass
finally:
    _terminate_process(child, 0.2)
""",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    process = subprocess.Popen([sys.executable, str(script)], env=environment)
    deadline = time.monotonic() + 5
    while not child_path.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert child_path.exists()
    child_pid = int(child_path.read_text())

    process.terminate()
    process.wait(timeout=5)

    status = subprocess.run(
        ["ps", "-o", "stat=", "-p", str(child_pid)],
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert process.returncode == 0
    assert not status or status.startswith("Z")


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux subreaper")
def test_supervisor_reaps_a_detached_descendant(tmp_path: Path) -> None:
    ready = tmp_path / "ready"
    escaped = tmp_path / "escaped"
    child_code = (
        "import time; from pathlib import Path; time.sleep(0.8); "
        f"Path({str(escaped)!r}).write_text('escaped')"
    )
    parent_code = (
        "import subprocess, sys, time; from pathlib import Path; "
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}], start_new_session=True); "
        f"Path({str(ready)!r}).write_text('ready'); time.sleep(30)"
    )
    process = subprocess.Popen(
        contained_command([sys.executable, "-c", parent_code]),
        start_new_session=True,
    )
    process._qtbench_contained = True  # type: ignore[attr-defined]
    deadline = time.monotonic() + 5
    while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.02)
    assert ready.exists()

    _terminate_process(process, 0.2)
    time.sleep(1)

    assert not escaped.exists()
