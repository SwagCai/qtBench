"""Codex permission-profile helpers for isolated solver and judge processes."""

from __future__ import annotations

from functools import lru_cache
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import time


PERMISSION_PROFILE_NAME = "qtbench_inference"
SUPERVISOR = Path(__file__).with_name("supervisor.py")
_CODEX_DISTRIBUTIONS = {
    ("linux", "x86_64"): ("codex-linux-x64", "x86_64-unknown-linux-musl"),
    ("linux", "aarch64"): ("codex-linux-arm64", "aarch64-unknown-linux-musl"),
    ("darwin", "x86_64"): ("codex-darwin-x64", "x86_64-apple-darwin"),
    ("darwin", "aarch64"): ("codex-darwin-arm64", "aarch64-apple-darwin"),
}
_UNSAFE_STATE_ROOTS = (
    Path("/tmp"),
    Path("/var/tmp"),
    Path("/dev/shm"),
    Path("/private/tmp"),
    Path("/private/var/tmp"),
    Path("/var/folders"),
    Path("/private/var/folders"),
)


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def private_path(path: Path) -> Path:
    """Reject shared temporary roots for run, authentication, and agent state."""

    resolved = path.expanduser().resolve(strict=False)
    if any(_under(resolved, root) for root in _UNSAFE_STATE_ROOTS):
        raise ValueError("inference state must not be under a shared temporary root")
    return resolved


def contained_command(command: list[str]) -> list[str]:
    """Wrap one untrusted process tree in the Linux subreaper supervisor."""

    if not sys.platform.startswith("linux") or not Path("/proc/self/stat").is_file():
        raise ValueError("the inference scaffold requires Linux with a mounted /proc")
    if not SUPERVISOR.is_file():
        raise ValueError("the inference process-tree supervisor is missing")
    return [sys.executable, str(SUPERVISOR), "--", *command]


@lru_cache(maxsize=1)
def sandbox_python() -> Path:
    """Return a system interpreter covered by Codex's minimal read profile."""

    for candidate in (Path("/usr/bin/python3"), Path("/usr/local/bin/python3")):
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            continue
        version = subprocess.run(
            [
                str(candidate),
                "-c",
                "import sys; raise SystemExit(sys.version_info < (3, 11))",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        if version.returncode == 0:
            return candidate
    raise ValueError("the inference sandbox requires a system Python 3.11+ interpreter")


def prepare_private_runtime(
    workspace: Path, *, initialize: bool
) -> dict[str, Path]:
    workspace = private_path(workspace)
    runtime = workspace / ".qtbench-runtime"
    paths = {
        "root": runtime,
        "home": runtime / "home",
        "tmp": runtime / "tmp",
        "pycache": runtime / "tmp/pycache",
    }
    if initialize:
        for path in paths.values():
            if path.is_symlink():
                raise ValueError("private runtime path may not be a symlink")
            created = not path.exists()
            path.mkdir(parents=True, exist_ok=True)
            if created:
                path.chmod(0o700)
    for path in paths.values():
        metadata = os.lstat(path)
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.getuid():
            raise ValueError("private runtime directory was replaced")
    return paths


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _codex_runtime_read_path(codex: Path) -> Path:
    """Return the narrow path the sandbox must read to run this Codex build."""

    codex = codex.resolve(strict=True)
    runtime = codex.parent.parent
    if (
        codex.parent.name == "bin"
        and runtime.parent.name == "vendor"
        and runtime.name in {target for _, target in _CODEX_DISTRIBUTIONS.values()}
    ):
        return runtime
    return codex


def permission_arguments(*, writable: bool, codex: Path) -> list[str]:
    """Build a deny-by-default profile with one effective workspace root."""

    access = "write" if writable else "read"
    codex_runtime = _codex_runtime_read_path(codex)
    filesystem = [
        '\":root\"=\"deny\"',
        '\":minimal\"=\"read\"',
        f'{_toml_string(str(codex_runtime))}=\"read\"',
        f'\":workspace_roots\"={{\".\"=\"{access}\"}}',
    ]
    profile = (
        "{filesystem={" + ",".join(filesystem) + "},network={enabled=false}}"
    )
    return [
        "-c",
        f'default_permissions="{PERMISSION_PROFILE_NAME}"',
        "-c",
        f"permissions.{PERMISSION_PROFILE_NAME}={profile}",
    ]


def private_shell_environment(
    workspace: Path, *, initialize: bool = False
) -> dict[str, str]:
    """Return the complete environment visible to model-generated commands."""

    runtime = prepare_private_runtime(workspace, initialize=initialize)
    local_bin = workspace.resolve() / ".qtbench-bin"
    path = os.pathsep.join(
        part
        for part in (
            str(local_bin) if local_bin.is_dir() else "",
            str(sandbox_python().parent),
            "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        )
        if part
    )
    return {
        "HOME": str(runtime["home"]),
        "TMPDIR": str(runtime["tmp"]),
        "TMP": str(runtime["tmp"]),
        "TEMP": str(runtime["tmp"]),
        "PYTHONPYCACHEPREFIX": str(runtime["pycache"]),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(workspace.resolve() / "src"),
        "PATH": path,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


def shell_environment_policy_argument(environment: dict[str, str]) -> str:
    values = ",".join(
        f"{_toml_string(key)}={_toml_string(value)}"
        for key, value in sorted(environment.items())
    )
    return (
        'shell_environment_policy={inherit="none",'
        f"ignore_default_excludes=false,set={{{values}}}}}"
    )


def codex_process_environment(auth_home: Path) -> dict[str, str]:
    """Give Codex its auth store without exposing host credentials to tools."""

    allowed = {
        name: value
        for name, value in os.environ.items()
        if name
        in {
            "PATH",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "NO_PROXY",
            "ALL_PROXY",
            "LANG",
            "LC_ALL",
            "TERM",
        }
    }
    allowed["CODEX_HOME"] = str(private_path(auth_home))
    return allowed


def _platform_codex_distribution() -> tuple[str, str] | None:
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "arm64": "aarch64"}.get(machine, machine)
    return _CODEX_DISTRIBUTIONS.get((sys.platform, machine))


def _native_codex_executable(entrypoint: Path) -> Path | None:
    entrypoint = entrypoint.expanduser().resolve(strict=False)
    if not entrypoint.is_file() or not os.access(entrypoint, os.X_OK):
        return None
    if entrypoint.name != "codex.js":
        return entrypoint

    distribution = _platform_codex_distribution()
    if distribution is None:
        return None
    package_name, target = distribution
    package_root = entrypoint.parent.parent
    platform_roots = (
        package_root / "node_modules" / "@openai" / package_name,
        package_root.parent / package_name,
        package_root,
    )
    for platform_root in platform_roots:
        native = (platform_root / "vendor" / target / "bin" / "codex").resolve(
            strict=False
        )
        if native.is_file() and os.access(native, os.X_OK):
            return native
    return None


def find_codex(explicit: Path | None = None) -> Path:
    candidates = []
    if explicit is not None:
        candidates.append(explicit.expanduser())
    resolved = shutil.which("codex")
    if resolved:
        candidates.append(Path(resolved))
    candidates.append(Path("/Applications/ChatGPT.app/Contents/Resources/codex"))
    for candidate in candidates:
        native = _native_codex_executable(candidate)
        if native is not None:
            return native
    raise ValueError(
        "Codex CLI native executable was not found; reinstall it or pass "
        "--codex /absolute/path/to/codex"
    )


def authenticate_api_key(codex: Path, auth_home: Path, api_key: str) -> None:
    """Store an API key in a private Codex home without placing it on argv."""

    if not api_key or "\n" in api_key or "\r" in api_key:
        raise ValueError("OPENAI_API_KEY must be a nonempty single-line value")
    auth_home = private_path(auth_home)
    auth_home.mkdir(parents=True, exist_ok=True)
    auth_home.chmod(0o700)
    result = subprocess.run(
        [
            str(codex),
            "-c",
            'cli_auth_credentials_store="file"',
            "login",
            "--with-api-key",
        ],
        input=api_key + "\n",
        env=codex_process_environment(auth_home),
        text=True,
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise ValueError("Codex API-key login failed; no provider output was retained")
    auth_file = auth_home / "auth.json"
    if not auth_file.is_file():
        raise ValueError("Codex login did not create its private authentication file")
    auth_file.chmod(0o600)


def codex_command(
    codex: Path,
    workspace: Path,
    *,
    auth_home: Path,
    model: str,
    effort: str,
    shell_environment: dict[str, str],
    writable: bool,
    web_search: bool,
) -> tuple[list[str], dict[str, str]]:
    command = [
        str(codex),
        *permission_arguments(writable=writable, codex=codex),
        "-c",
        f"model_reasoning_effort={json.dumps(effort)}",
        "-c",
        shell_environment_policy_argument(shell_environment),
        "-c",
        'cli_auth_credentials_store="file"',
        "-c",
        'web_search="live"' if web_search else 'web_search="disabled"',
        "--strict-config",
        "-m",
        model,
        "-a",
        "never",
        "-C",
        str(workspace.resolve()),
    ]
    if web_search:
        command.append("--search")
    return command, codex_process_environment(auth_home)


def probe_sandbox(codex: Path, workspace: Path, denied_file: Path) -> None:
    """Prove an allowed read succeeds and an outside read fails before inference."""

    workspace = private_path(workspace)
    allowed_file = workspace / ".qtbench-runtime/sandbox-probe.txt"
    allowed_file.parent.mkdir(parents=True, exist_ok=True)
    allowed_file.write_text("allowed\n", encoding="utf-8")
    command = [
        str(codex),
        *permission_arguments(writable=True, codex=codex),
        "sandbox",
        "-P",
        PERMISSION_PROFILE_NAME,
        "-C",
        str(workspace),
        "--",
        str(sandbox_python()),
        "-c",
    ]
    environment = private_shell_environment(workspace, initialize=True)
    allowed = subprocess.run(
        [
            *command,
            (
                "from pathlib import Path; "
                "p=Path('.qtbench-runtime/sandbox-write.txt'); "
                "p.write_text('write-ok'); print(p.read_text())"
            ),
        ],
        cwd=workspace,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    denied = subprocess.run(
        [*command, f"from pathlib import Path; print(Path({str(denied_file)!r}).read_text())"],
        cwd=workspace,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    network = subprocess.run(
        [
            *command,
            "import socket; socket.socket(socket.AF_INET, socket.SOCK_STREAM)",
        ],
        cwd=workspace,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    namespace = subprocess.run(
        [*command, "import os; print(os.readlink('/proc/self/ns/pid'))"],
        cwd=workspace,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    reserved_results = {
        name: subprocess.run(
            [
                *command,
                (
                    "from pathlib import Path; "
                    f"p=Path({name!r}); p.mkdir(exist_ok=True); "
                    "(p / 'qtbench-probe').write_text('unsafe')"
                ),
            ],
            cwd=workspace,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )
        for name in (".codex", ".git", ".agents")
    }
    if allowed.returncode != 0 or "write-ok" not in allowed.stdout:
        stderr = allowed.stderr.strip()[-2_000:] or "(no stderr)"
        raise ValueError(
            "Codex is installed, but its local sandbox cannot read and write the solver workspace "
            f"(exit {allowed.returncode}): {stderr}"
        )
    if denied.returncode == 0 or denied.stdout:
        raise ValueError(
            "Codex sandbox isolation probe failed: a file outside the workspace was readable"
        )
    if network.returncode == 0:
        raise ValueError(
            "Codex sandbox isolation probe failed: a shell process could create a network socket"
        )
    host_pid_namespace = os.readlink("/proc/self/ns/pid")
    sandbox_pid_namespace = namespace.stdout.strip().splitlines()
    if (
        namespace.returncode != 0
        or not sandbox_pid_namespace
        or sandbox_pid_namespace[-1] == host_pid_namespace
    ):
        raise ValueError(
            "Codex sandbox isolation probe failed: no private PID namespace was observed"
        )
    if any(result.returncode == 0 for result in reserved_results.values()) or any(
        (workspace / name / "qtbench-probe").exists()
        for name in (".codex", ".git", ".agents")
    ):
        raise ValueError(
            "Codex sandbox isolation probe failed: a reserved control path was writable"
        )

    ready = workspace / ".qtbench-runtime/containment-ready"
    escaped = workspace / ".qtbench-runtime/containment-escaped"
    child_code = (
        "import time; from pathlib import Path; time.sleep(1.0); "
        f"Path({str(escaped)!r}).write_text('escaped')"
    )
    parent_code = (
        "import subprocess, sys, time; from pathlib import Path; "
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}], start_new_session=True); "
        f"Path({str(ready)!r}).write_text('ready'); time.sleep(30)"
    )
    containment = subprocess.Popen(
        contained_command([*command, parent_code]),
        cwd=workspace,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 8
        while not ready.is_file() and containment.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        if not ready.is_file():
            raise ValueError(
                "Codex process containment probe could not start a detached sandbox child"
            )
        containment.terminate()
        try:
            containment.wait(timeout=4)
        except subprocess.TimeoutExpired as error:
            containment.kill()
            containment.wait()
            raise ValueError("Codex process containment cleanup exceeded its deadline") from error
        time.sleep(1.2)
        if escaped.exists():
            raise ValueError(
                "Codex process containment probe failed: a detached child survived cleanup"
            )
    finally:
        if containment.poll() is None:
            containment.terminate()
            try:
                containment.wait(timeout=4)
            except subprocess.TimeoutExpired:
                containment.kill()
                containment.wait()
