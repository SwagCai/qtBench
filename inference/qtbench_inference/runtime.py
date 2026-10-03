"""One-problem solver, semantic judge, and authoritative checker orchestration."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence
import uuid

from .protocol import (
    AnchoredFileSubmissionBroker,
    JudgeCallResult,
    SubmissionGate,
    append_event,
    utc_now,
    write_json_atomic,
)
from .sandbox import (
    authenticate_api_key,
    codex_command,
    contained_command,
    find_codex,
    private_path,
    private_shell_environment,
    probe_sandbox,
)
from .workspace import (
    ProblemSpec,
    prepare_solver_workspace,
    repository_revision,
    resolve_problem,
    sha256_file,
    verify_solver_inputs,
)


DEFAULT_SOLVER_MODEL = "gpt-6-sol"
DEFAULT_JUDGE_MODEL = "gpt-6-sol"
DEFAULT_WALL_SECONDS = 7200.0
MAX_REPORT_BYTES = 64_000_000
JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "category", "reason", "strategy_summary"],
    "properties": {
        "verdict": {"type": "string", "enum": ["approve", "reject"]},
        "category": {
            "type": "string",
            "enum": [
                "legitimate",
                "fitting_or_interpolation",
                "reverse_engineering",
                "hardcoding_or_lookup",
                "checker_gaming",
                "benchmark_specific",
                "invalid_mathematics",
                "insufficient_evidence",
            ],
        },
        "reason": {"type": "string", "minLength": 1, "maxLength": 1200},
        "strategy_summary": {"type": "string", "minLength": 1, "maxLength": 1200},
    },
}


class TerminationRequested(BaseException):
    def __init__(self, signum: int) -> None:
        super().__init__(f"received signal {signum}")
        self.signum = signum


def _raise_termination(signum: int, _frame: object) -> None:
    raise TerminationRequested(signum)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_prompt(name: str) -> str:
    return (
        Path(__file__).resolve().parents[1] / "prompts" / name
    ).read_text(encoding="utf-8")


def _safe_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key
        in {
            "PATH",
            "LANG",
            "LC_ALL",
            "TMPDIR",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
        }
    }


def _terminate_process(process: subprocess.Popen[Any], grace_seconds: float = 1.0) -> None:
    if getattr(process, "_qtbench_contained", False):
        grace_seconds = max(grace_seconds, 6.0)
    if os.name == "posix":
        process_group = process.pid

        def group_exists() -> bool:
            try:
                os.killpg(process_group, 0)
                return True
            except ProcessLookupError:
                return False
            except PermissionError:
                return True

        if group_exists():
            try:
                os.killpg(process_group, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            deadline = time.monotonic() + grace_seconds
            try:
                process.wait(timeout=grace_seconds)
            except subprocess.TimeoutExpired:
                pass
            while group_exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            if group_exists():
                try:
                    os.killpg(process_group, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        try:
            process.wait(timeout=max(0.2, grace_seconds))
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


@dataclass(frozen=True)
class LaunchConfig:
    repo: Path
    state_root: Path
    run: Path
    codex: Path
    auth_home: Path
    problem: ProblemSpec
    solver_model: str
    solver_effort: str
    judge_model: str
    judge_effort: str
    wall_budget_seconds: float
    judge_timeout_seconds: float
    checker_timeout_seconds: float
    web_search: bool


class CodexJudge:
    def __init__(self, config: LaunchConfig, prompt: str) -> None:
        self.config = config
        self.prompt = prompt
        self.root = config.run / "judge-workspaces"
        self.root.mkdir(parents=True, exist_ok=True)
        self.root.chmod(0o700)

    def evaluate(
        self,
        packet: Mapping[str, Any],
        *,
        deadline_monotonic: float,
        evidence_directory: Path,
    ) -> JudgeCallResult:
        started = time.monotonic()
        submission = packet.get("submission")
        submission_id = (
            str(submission.get("submission_id", "submission"))
            if isinstance(submission, Mapping)
            else "submission"
        )
        workspace = self.root / f"{submission_id}-{uuid.uuid4().hex}"
        workspace.mkdir()
        workspace.chmod(0o700)
        input_path = evidence_directory / "judge-input.md"
        schema_path = evidence_directory / "judge-output-schema.json"
        decision_path = evidence_directory / "judge-decision.raw.json"
        input_path.write_text(
            self.prompt
            + "\n\n# Current review packet\n\n```json\n"
            + json.dumps(packet, indent=2, sort_keys=True)
            + "\n```\n",
            encoding="utf-8",
        )
        write_json_atomic(schema_path, JUDGE_SCHEMA)
        shell_environment = private_shell_environment(workspace, initialize=True)
        prefix, process_environment = codex_command(
            self.config.codex,
            workspace,
            auth_home=self.config.auth_home,
            model=self.config.judge_model,
            effort=self.config.judge_effort,
            shell_environment=shell_environment,
            writable=True,
            web_search=False,
        )
        command = prefix + [
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--output-schema",
            str(schema_path),
            "--json",
            "--output-last-message",
            str(decision_path),
            "-",
        ]
        command = contained_command(command)
        stdout_path = evidence_directory / "judge-events.jsonl"
        stderr_path = evidence_directory / "judge-stderr.log"
        process: subprocess.Popen[Any] | None = None
        try:
            remaining = deadline_monotonic - time.monotonic()
            if remaining <= 0:
                return JudgeCallResult("timeout", "", 0.0, "judge deadline expired")
            with (
                input_path.open("rb") as stdin,
                stdout_path.open("xb") as stdout,
                stderr_path.open("xb") as stderr,
            ):
                process = subprocess.Popen(
                    command,
                    cwd=workspace,
                    env=process_environment,
                    stdin=stdin,
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=(os.name == "posix"),
                )
                process._qtbench_contained = True  # type: ignore[attr-defined]
                try:
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:
                    _terminate_process(process, 0.5)
                    return JudgeCallResult(
                        "timeout", "", time.monotonic() - started, "judge deadline exceeded"
                    )
            if process.returncode != 0:
                return JudgeCallResult(
                    "failure",
                    "",
                    time.monotonic() - started,
                    f"judge process exited {process.returncode}",
                )
            if not decision_path.is_file() or decision_path.stat().st_size > 32_000:
                return JudgeCallResult(
                    "failure",
                    "",
                    time.monotonic() - started,
                    "judge output is missing or too large",
                )
            return JudgeCallResult(
                "completed",
                decision_path.read_text(encoding="utf-8"),
                time.monotonic() - started,
                metadata={"provider": "openai", "model": self.config.judge_model},
            )
        except Exception as error:
            return JudgeCallResult(
                "failure", "", time.monotonic() - started, type(error).__name__
            )
        finally:
            if process is not None:
                _terminate_process(process, 0.2)


class OfficialChecker:
    def __init__(self, config: LaunchConfig, benchmark_revision: str) -> None:
        self.config = config
        self.benchmark_revision = benchmark_revision
        self.script = config.repo / "scripts/evaluate/evaluate_scored_submission.py"
        if not self.script.is_file():
            raise ValueError("official scored checker is missing")

    def evaluate(
        self,
        submission_id: str,
        source: Path,
        source_sha256: str,
        *,
        deadline_monotonic: float,
        evidence_directory: Path,
    ) -> Mapping[str, Any]:
        if sha256_file(source) != source_sha256:
            raise ValueError("captured source changed before checker execution")
        _assert_clean_repository(self.config.repo)
        if repository_revision(self.config.repo) != self.benchmark_revision:
            raise ValueError("qtBench revision changed after inference launch")
        stdout_path = evidence_directory / "checker-stdout.json"
        stderr_path = evidence_directory / "checker-stderr.log"
        command = [
            sys.executable,
            str(self.script),
            self.config.problem.evaluator_kind,
            str(source),
            "--format",
            "json",
        ]
        command = contained_command(command)
        remaining = deadline_monotonic - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("checker deadline expired")
        process: subprocess.Popen[Any] | None = None
        try:
            with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
                process = subprocess.Popen(
                    command,
                    cwd=self.config.repo,
                    env=_safe_environment(),
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=(os.name == "posix"),
                )
                process._qtbench_contained = True  # type: ignore[attr-defined]
                try:
                    process.wait(timeout=remaining)
                except subprocess.TimeoutExpired as error:
                    _terminate_process(process, 0.5)
                    raise TimeoutError("official checker deadline exceeded") from error
            if stdout_path.stat().st_size > MAX_REPORT_BYTES:
                raise ValueError("official checker report exceeds 64 MB")
            try:
                report = json.loads(stdout_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError("official checker did not return one JSON report") from error
            if not isinstance(report, dict) or process.returncode not in {0, 1}:
                raise ValueError("official checker returned an invalid status or report")
            provenance = report.get("provenance")
            if not isinstance(provenance, dict):
                raise ValueError("official checker report has no provenance")
            if provenance.get("submission_sha256") != source_sha256:
                raise ValueError("official checker report source hash does not match capture")
            if provenance.get("problem_id") != self.config.problem.problem_id:
                raise ValueError("official checker report identifies the wrong problem")
            if provenance.get("evaluator_kind") != self.config.problem.evaluator_kind:
                raise ValueError("official checker report identifies the wrong evaluator")
            if provenance.get("repository_commit") != self.benchmark_revision:
                raise ValueError("official checker report repository revision does not match")
            if provenance.get("repository_dirty") is not False:
                raise ValueError("official checker report did not attest a clean repository")
            return {
                "schema_version": 1,
                "status": "completed",
                "submission_id": submission_id,
                "source_sha256": source_sha256,
                "exit_code": process.returncode,
                "report": report,
            }
        finally:
            if process is not None:
                _terminate_process(process, 0.2)


def _solver_prompt(config: LaunchConfig, *, continuation: int) -> str:
    base = _read_prompt("solver.md")
    access = (
        "Hosted Codex web search is available; shell commands still have no network."
        if config.web_search
        else "Hosted web search and shell network are disabled for this run."
    )
    continuation_text = (
        ""
        if continuation == 0
        else (
            f"\nThis is continuation {continuation} in the same isolated workspace. "
            "Inspect same-run files, continue submission IDs, and do not repeat completed work.\n"
        )
    )
    return (
        base
        + continuation_text
        + "\n# Selected run\n\n"
        + f"Problem: {config.problem.problem_id} ({config.problem.name})\n\n"
        + f"Total wall-clock run budget: {config.wall_budget_seconds:.0f} seconds.\n\n"
        + access
        + "\nRead CURRENT_PROBLEM.md before beginning.\n"
    )


def _launch_solver_segment(
    config: LaunchConfig,
    broker: AnchoredFileSubmissionBroker,
    *,
    segment: int,
    run_deadline: float,
) -> tuple[float, int, bool, bool]:
    workspace = config.run / "w"
    segment_dir = config.run / "solver" / f"segment-{segment:04d}"
    segment_dir.mkdir(parents=True)
    prompt = _solver_prompt(config, continuation=segment - 1)
    prompt_path = segment_dir / "prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    model_final = segment_dir / "model-final.md"
    shell_environment = private_shell_environment(workspace, initialize=False)
    shell_environment["QTBENCH_GATE_DIRECTORY"] = str(broker.root)
    prefix, process_environment = codex_command(
        config.codex,
        workspace,
        auth_home=config.auth_home,
        model=config.solver_model,
        effort=config.solver_effort,
        shell_environment=shell_environment,
        writable=True,
        web_search=config.web_search,
    )
    command = prefix + [
        "exec",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--json",
        "--output-last-message",
        str(model_final),
        "-",
    ]
    command = contained_command(command)
    started = time.monotonic()
    gate_seconds_total = 0.0
    budget_exhausted = False
    approved = False
    with (
        prompt_path.open("rb") as stdin,
        (segment_dir / "events.jsonl").open("xb") as stdout,
        (segment_dir / "stderr.log").open("xb") as stderr,
    ):
        process = subprocess.Popen(
            command,
            cwd=workspace,
            env=process_environment,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            start_new_session=(os.name == "posix"),
        )
        process._qtbench_contained = True  # type: ignore[attr-defined]
        try:
            while process.poll() is None:
                remaining = run_deadline - time.monotonic()
                if remaining <= 0:
                    budget_exhausted = True
                    _terminate_process(process)
                    break
                _processed, gate_seconds = broker.poll(
                    run_deadline_monotonic=run_deadline
                )
                gate_seconds_total += gate_seconds
                if broker.approved_response is not None:
                    approved = True
                    _terminate_process(process, 0.5)
                    break
                time.sleep(0.05)
        finally:
            _terminate_process(process, 0.5)
    drain_limit_reached = True
    for _ in range(256):
        drain_deadline = (
            time.monotonic()
            if broker.approved_response is not None
            else run_deadline
        )
        processed, gate_seconds = broker.poll(
            run_deadline_monotonic=drain_deadline
        )
        gate_seconds_total += gate_seconds
        if not processed:
            drain_limit_reached = False
            break
    if drain_limit_reached:
        append_event(config.run, {"type": "submission_drain_limit_reached"})
    if broker.approved_response is not None:
        approved = True
    if time.monotonic() >= run_deadline:
        budget_exhausted = True
    wall_seconds = max(0.0, time.monotonic() - started)
    result = {
        "schema_version": 1,
        "segment": segment,
        "returncode": process.returncode,
        "wall_seconds": wall_seconds,
        "gate_seconds": gate_seconds_total,
        "budget_exhausted": budget_exhausted,
        "approved": approved,
        "submission_drain_limit_reached": drain_limit_reached,
        "prompt_sha256": _sha256_text(prompt),
    }
    write_json_atomic(segment_dir / "result.json", result)
    return (
        wall_seconds,
        70 if drain_limit_reached else int(process.returncode or 0),
        budget_exhausted,
        approved,
    )


def run_solver(
    config: LaunchConfig, broker: AnchoredFileSubmissionBroker
) -> dict[str, Any]:
    started = time.monotonic()
    run_deadline = started + config.wall_budget_seconds
    segment = 0
    rapid_clean_exits = 0
    status = "failed"
    while time.monotonic() < run_deadline:
        segment += 1
        append_event(config.run, {"type": "solver_segment_started", "segment": segment})
        segment_wall, returncode, exhausted, approved = _launch_solver_segment(
            config, broker, segment=segment, run_deadline=run_deadline
        )
        wall_used = time.monotonic() - started
        append_event(
            config.run,
            {
                "type": "solver_segment_finished",
                "segment": segment,
                "returncode": returncode,
                "wall_seconds": segment_wall,
                "cumulative_wall_seconds": wall_used,
            },
        )
        if approved:
            status = "approved"
            break
        if exhausted or time.monotonic() >= run_deadline:
            status = "budget_exhausted"
            break
        if returncode != 0:
            status = "solver_failure"
            break
        rapid_clean_exits = rapid_clean_exits + 1 if segment_wall < 2.0 else 0
        if rapid_clean_exits >= 3:
            status = "repeated_early_exit"
            break
        time.sleep(min(1.0, max(0.0, run_deadline - time.monotonic())))
    result = {
        "schema_version": 1,
        "status": status,
        "segments": segment,
        "wall_seconds": round(time.monotonic() - started, 6),
        "budget_seconds": config.wall_budget_seconds,
    }
    if broker.approved_response is not None:
        submission_id = broker.approved_response["submission_id"]
        result["approved_submission_id"] = submission_id
        result["approved_source_sha256"] = broker.approved_response["source_sha256"]
        result["approved_source_path"] = str(
            config.run / "submissions" / submission_id / "source.py"
        )
    return result


def _new_run_path(state_root: Path, problem: ProblemSpec) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return state_root / "runs" / f"{stamp}-p{problem.problem_id:02d}-{uuid.uuid4().hex[:8]}"


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _assert_clean_repository(repo: Path) -> None:
    try:
        changed = subprocess.check_output(
            ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("could not verify the qtBench Git checkout") from error
    if changed.strip():
        raise ValueError(
            "qtBench checkout must be completely clean so checker provenance is exact"
        )


def _require_private_directory(path: Path, option: str) -> None:
    metadata = os.lstat(path)
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f"{option} must be a directory")
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o022:
        raise ValueError(
            f"{option} must be owned by the current user and not group/world-writable"
        )


def _build_config(args: argparse.Namespace) -> LaunchConfig:
    repo = args.repo.resolve()
    problem = resolve_problem(repo, args.problem)
    if args.state_root.is_symlink():
        raise ValueError("--state-root may not be a symlink")
    state_root = private_path(args.state_root)
    if state_root.exists():
        _require_private_directory(state_root, "--state-root")
    else:
        state_root.mkdir(parents=True)
        state_root.chmod(0o700)
        _require_private_directory(state_root, "--state-root")
    run = private_path(args.run_dir) if args.run_dir else _new_run_path(state_root, problem)
    if _under(run, repo) or _under(repo, run):
        raise ValueError("run state must be outside the qtBench checkout")
    if run.exists():
        raise ValueError(f"run directory already exists: {run}")
    if args.run_dir is not None:
        run.parent.mkdir(parents=True, exist_ok=True)
        _require_private_directory(run.parent, "--run-dir parent")
    run.mkdir(parents=True)
    run.chmod(0o700)
    auth_home = state_root / "auth" / uuid.uuid4().hex
    codex = find_codex(args.codex)
    web_search = problem.problem_id != 1 and not args.offline
    return LaunchConfig(
        repo=repo,
        state_root=state_root,
        run=run,
        codex=codex,
        auth_home=auth_home,
        problem=problem,
        solver_model=args.solver_model,
        solver_effort=args.solver_effort,
        judge_model=args.judge_model,
        judge_effort=args.judge_effort,
        wall_budget_seconds=args.minutes * 60.0,
        judge_timeout_seconds=args.judge_timeout,
        checker_timeout_seconds=args.checker_timeout,
        web_search=web_search,
    )


def prepare_run(config: LaunchConfig) -> AnchoredFileSubmissionBroker:
    _assert_clean_repository(config.repo)
    benchmark_revision = repository_revision(config.repo)
    submit_client = Path(__file__).with_name("submit_client.py")
    workspace = config.run / "w"
    inputs = prepare_solver_workspace(
        config.repo, workspace, config.problem, submit_client=submit_client
    )
    denied = config.run / "sandbox-denied-sentinel.txt"
    denied.write_text("must not be readable by solver or judge\n", encoding="utf-8")
    denied.chmod(0o600)
    probe_sandbox(config.codex, workspace, denied)
    version = subprocess.check_output(
        [str(config.codex), "--version"], text=True, timeout=10
    ).strip()
    solver_prompt = _read_prompt("solver.md")
    judge_prompt = _read_prompt("judge.md")
    manifest = {
        "schema_version": 1,
        "workflow": "isolated-solver-judge-gate-v1",
        "created_at": utc_now(),
        "benchmark_revision": benchmark_revision,
        "problem_id": config.problem.problem_id,
        "problem_name": config.problem.name,
        "evaluator_kind": config.problem.evaluator_kind,
        "provider": "openai",
        "solver": {"model": config.solver_model, "reasoning_effort": config.solver_effort},
        "judge": {"model": config.judge_model, "reasoning_effort": config.judge_effort},
        "wall_budget_seconds": config.wall_budget_seconds,
        "judge_timeout_seconds": config.judge_timeout_seconds,
        "checker_timeout_seconds": config.checker_timeout_seconds,
        "solver_web_search": config.web_search,
        "shell_network": "disabled",
        "sandbox_pid_namespace": "preflight-verified",
        "process_tree_containment": "dedicated-linux-subreaper",
        "checker_access": "host-only-before-semantic-review",
        "credential": {
            "environment": "OPENAI_API_KEY",
            "workspace_exposure": False,
            "artifact_exposure": False,
            "ephemeral_auth_store_removed_after_run": True,
        },
        "codex_version": version,
        "solver_prompt_sha256": _sha256_text(solver_prompt),
        "judge_prompt_sha256": _sha256_text(judge_prompt),
        "solver_input_manifest_sha256": _sha256_text(
            json.dumps(inputs, sort_keys=True)
        ),
    }
    write_json_atomic(config.run / "manifest.json", manifest)
    append_event(config.run, {"type": "run_prepared"})
    judge = CodexJudge(config, judge_prompt)
    checker = OfficialChecker(config, benchmark_revision)
    gate = SubmissionGate(
        run=config.run,
        problem_context=config.problem.judge_context(),
        judge=judge,
        checker=checker,
        judge_max_seconds=config.judge_timeout_seconds,
        checker_max_seconds=config.checker_timeout_seconds,
    )
    return AnchoredFileSubmissionBroker(workspace, gate)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("problem", help="stable numeric problem id or exact registry name")
    command.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parents[2]
    )
    command.add_argument(
        "--state-root", type=Path, default=Path.home() / ".qtbench-inference"
    )
    command.add_argument("--run-dir", type=Path)
    command.add_argument("--provider", choices=("openai",), default="openai")
    command.add_argument("--solver-model", default=DEFAULT_SOLVER_MODEL)
    command.add_argument("--solver-effort", default="high")
    command.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL)
    command.add_argument("--judge-effort", default="medium")
    command.add_argument("--minutes", type=float, default=120.0)
    command.add_argument("--judge-timeout", type=float, default=120.0)
    command.add_argument("--checker-timeout", type=float, default=900.0)
    command.add_argument("--codex", type=Path)
    command.add_argument("--offline", action="store_true")
    command.add_argument(
        "--check-only",
        action="store_true",
        help="prepare inputs and prove sandbox isolation without logging in or calling a model",
    )
    return command


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if not math.isfinite(args.minutes) or args.minutes <= 0:
        raise SystemExit("--minutes must be positive")
    if not math.isfinite(args.judge_timeout) or not 0 < args.judge_timeout <= 120:
        raise SystemExit("--judge-timeout must be in (0, 120]")
    if not math.isfinite(args.checker_timeout) or args.checker_timeout <= 0:
        raise SystemExit("--checker-timeout must be positive")
    config: LaunchConfig | None = None
    broker: AnchoredFileSubmissionBroker | None = None
    previous_sigterm = signal.signal(signal.SIGTERM, _raise_termination)
    try:
        config = _build_config(args)
        broker = prepare_run(config)
        if args.check_only:
            print(f"READY: sandbox and problem inputs verified at {config.run}")
            return 0
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        authenticate_api_key(config.codex, config.auth_home, api_key)
        del api_key
        verify_solver_inputs(config.run / "w")
        append_event(config.run, {"type": "run_started"})
        result = run_solver(config, broker)
        result["finished_at"] = utc_now()
        write_json_atomic(config.run / "result.json", result)
        append_event(config.run, {"type": "run_finished", "status": result["status"]})
        print(json.dumps({**result, "run": str(config.run)}, indent=2, sort_keys=True))
        return 0 if result["status"] in {"approved", "budget_exhausted"} else 1
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        message = str(error)
        secret = os.environ.get("OPENAI_API_KEY")
        if secret:
            message = message.replace(secret, "[REDACTED_PROVIDER_CREDENTIAL]")
        if config is not None:
            write_json_atomic(
                config.run / "failure.json",
                {"failed_at": utc_now(), "error_type": type(error).__name__, "message": message},
            )
        print(f"inference launch failed closed: {message}", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, TerminationRequested) as error:
        signum = error.signum if isinstance(error, TerminationRequested) else signal.SIGINT
        message = f"inference interrupted by signal {signum}; child processes were stopped"
        if config is not None:
            write_json_atomic(
                config.run / "failure.json",
                {
                    "failed_at": utc_now(),
                    "error_type": "interrupted",
                    "message": message,
                },
            )
        print(message, file=sys.stderr)
        return 128 + int(signum)
    finally:
        if broker is not None:
            broker.close()
        if config is not None and config.auth_home.exists():
            shutil.rmtree(config.auth_home)
        signal.signal(signal.SIGTERM, previous_sigterm)
