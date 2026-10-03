"""Event-driven semantic judge gate between an isolated solver and checker."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from functools import partial
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Any, Callable, Mapping, Protocol
import uuid


GATE_PROTOCOL_VERSION = 1
JUDGE_MAX_SECONDS = 120.0
MAX_REQUEST_BYTES = 128_000
MAX_RESPONSE_BYTES = 64_000_000
_REQUEST_ID = re.compile(r"[a-f0-9]{32}\Z")
_SUBMISSION_ID = re.compile(r"s[0-9]{4,}\Z")
_SOURCE_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
_JUDGE_FIELDS = {"verdict", "category", "reason", "strategy_summary"}
_REQUEST_FIELDS = set(
    "schema_version request_id submission_id source source_sha256 description "
    "derivation parents".split()
)
_REJECT_CATEGORIES = set(
    "fitting_or_interpolation reverse_engineering hardcoding_or_lookup "
    "checker_gaming benchmark_specific invalid_mathematics insufficient_evidence".split()
)

ANTI_CHEATING_FEEDBACK = (
    "Abandon this mechanism and pivot to a genuinely natural mathematical strategy. "
    "Do not retry it through formatting changes, fitted constants, interpolation, "
    "reverse engineering, hardcoding, lookup, checker-specific logic, or another "
    "benchmark-specific rule."
)
CHECKER_REJECTION_FEEDBACK = (
    "The official checker rejected this exact source before semantic review. "
    "Address the reported implementation or mathematical failure "
    "without tailoring the construction to checker cases."
)
CHECKER_FAILURE_FEEDBACK = (
    "The checker did not produce a trustworthy result. Treat this as an "
    "infrastructure failure, not evidence for or against the mathematics."
)
JUDGE_FAILURE_FEEDBACK = (
    "The semantic judge did not produce a trustworthy decision. Treat this as an "
    "infrastructure failure and retry the unchanged source if the run budget permits."
)


class VerdictSchemaError(ValueError):
    pass


class SubmissionProtocolError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def append_event(run: Path, event: Mapping[str, Any]) -> None:
    with (run / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp": utc_now(), **event}, sort_keys=True) + "\n")


def ast_fingerprint(source: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        normalized = source.replace("\r\n", "\n").strip()
        return "text:" + hashlib.sha256(normalized.encode()).hexdigest()
    dumped = ast.dump(tree, annotate_fields=True, include_attributes=False)
    return "ast:" + hashlib.sha256(dumped.encode()).hexdigest()


@dataclass(frozen=True)
class JudgeDecision:
    verdict: str
    category: str
    reason: str
    strategy_summary: str

    @classmethod
    def parse(cls, raw: str) -> "JudgeDecision":
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as error:
            raise VerdictSchemaError("judge response is not valid JSON") from error
        if not isinstance(value, dict) or set(value) != _JUDGE_FIELDS:
            raise VerdictSchemaError(
                "judge response must contain exactly verdict, category, reason, "
                "and strategy_summary"
            )
        if any(not isinstance(value[field], str) for field in _JUDGE_FIELDS):
            raise VerdictSchemaError("all judge decision fields must be strings")
        verdict = value["verdict"]
        category = value["category"]
        reason = value["reason"].strip()
        summary = value["strategy_summary"].strip()
        if verdict not in {"approve", "reject"}:
            raise VerdictSchemaError("verdict must be approve or reject")
        if not reason or not summary or len(reason) > 1200 or len(summary) > 1200:
            raise VerdictSchemaError("reason and strategy_summary must be 1-1200 characters")
        if verdict == "approve" and category != "legitimate":
            raise VerdictSchemaError("approved decisions require category legitimate")
        if verdict == "reject" and category not in _REJECT_CATEGORIES:
            raise VerdictSchemaError("rejected decision has an unsupported category")
        return cls(verdict, category, reason, summary)

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class JudgeCallResult:
    status: str
    raw_output: str
    duration_seconds: float
    error: str | None = None
    metadata: Mapping[str, Any] | None = None


class JudgeEvaluator(Protocol):
    def evaluate(
        self,
        packet: Mapping[str, Any],
        *,
        deadline_monotonic: float,
        evidence_directory: Path,
    ) -> JudgeCallResult: ...


class CheckerEvaluator(Protocol):
    def evaluate(
        self,
        submission_id: str,
        source: Path,
        source_sha256: str,
        *,
        deadline_monotonic: float,
        evidence_directory: Path,
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class SubmissionRequest:
    request_id: str
    submission_id: str
    source: str
    source_sha256: str
    description: str
    derivation: str
    parents: tuple[str, ...]

    @classmethod
    def create(
        cls,
        *,
        submission_id: str,
        source: str,
        description: str,
        derivation: str,
        parents: tuple[str, ...] = (),
        request_id: str | None = None,
    ) -> "SubmissionRequest":
        return cls(
            request_id=request_id or uuid.uuid4().hex,
            submission_id=submission_id,
            source=source,
            source_sha256=hashlib.sha256(source.encode()).hexdigest(),
            description=description,
            derivation=derivation,
            parents=parents,
        ).validated()

    @classmethod
    def parse(cls, value: object) -> "SubmissionRequest":
        if not isinstance(value, dict) or set(value) != _REQUEST_FIELDS:
            raise SubmissionProtocolError("request must contain exactly the protocol fields")
        if value["schema_version"] != GATE_PROTOCOL_VERSION:
            raise SubmissionProtocolError("unsupported submission protocol version")
        if not isinstance(value["parents"], list) or not all(
            isinstance(parent, str) for parent in value["parents"]
        ):
            raise SubmissionProtocolError("parents must be a JSON string array")
        for field in _REQUEST_FIELDS - {"schema_version", "parents"}:
            if not isinstance(value[field], str):
                raise SubmissionProtocolError(f"{field} must be a string")
        return cls(
            request_id=value["request_id"],
            submission_id=value["submission_id"],
            source=value["source"],
            source_sha256=value["source_sha256"],
            description=value["description"],
            derivation=value["derivation"],
            parents=tuple(value["parents"]),
        ).validated()

    def validated(self) -> "SubmissionRequest":
        if not _REQUEST_ID.fullmatch(self.request_id):
            raise SubmissionProtocolError("request_id must be 32 lowercase hex characters")
        if not _SUBMISSION_ID.fullmatch(self.submission_id):
            raise SubmissionProtocolError("submission_id must match s followed by digits")
        encoded = self.source.encode("utf-8")
        if not self.source.strip() or len(encoded) > 64_000:
            raise SubmissionProtocolError("source must contain 1-64000 UTF-8 bytes")
        digest = hashlib.sha256(encoded).hexdigest()
        if not _SOURCE_SHA256.fullmatch(self.source_sha256) or self.source_sha256 != digest:
            raise SubmissionProtocolError("source_sha256 does not match source")
        if not self.description.strip() or len(self.description) > 12_000:
            raise SubmissionProtocolError("description must contain 1-12000 characters")
        if not self.derivation.strip() or len(self.derivation) > 24_000:
            raise SubmissionProtocolError("derivation must contain 1-24000 characters")
        if len(self.parents) > 64 or len(set(self.parents)) != len(self.parents):
            raise SubmissionProtocolError("parents must be unique and limited to 64 entries")
        if any(not _SUBMISSION_ID.fullmatch(parent) for parent in self.parents):
            raise SubmissionProtocolError("parent submission ID is invalid")
        if self.submission_id in self.parents:
            raise SubmissionProtocolError("a submission cannot be its own parent")
        return self

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": GATE_PROTOCOL_VERSION,
            "request_id": self.request_id,
            "submission_id": self.submission_id,
            "source": self.source,
            "source_sha256": self.source_sha256,
            "description": self.description,
            "derivation": self.derivation,
            "parents": list(self.parents),
        }


def build_judge_packet(
    problem_context: Mapping[str, Any], request: SubmissionRequest
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "context_scope": "one-current-problem-and-one-current-submission",
        "problem": dict(problem_context),
        "submission": {
            "submission_id": request.submission_id,
            "source": request.source,
            "source_sha256": request.source_sha256,
            "description": request.description,
            "derivation": request.derivation,
            "parents": list(request.parents),
        },
        "decision_rule": (
            "Approve only a genuine mathematical construction. Reject fitting, "
            "interpolation, reverse engineering, hardcoding, lookup, checker gaming, "
            "or a benchmark-specific rule. Return only the required four-field JSON."
        ),
        "response_fields": sorted(_JUDGE_FIELDS),
    }


def _checker_rejection_reason(result: Mapping[str, Any]) -> str:
    report = result.get("report")
    if not isinstance(report, Mapping):
        return "Official checker returned a valid rejection."
    gate_error = report.get("gate_error")
    if isinstance(gate_error, str) and gate_error.strip():
        return f"Official checker gate rejected the submission: {gate_error.strip()}"
    review_reason = report.get("review_reason")
    if isinstance(review_reason, str) and review_reason.strip():
        return f"Official checker requires expert review: {review_reason.strip()}"
    stage = report.get("checker_stage")
    if isinstance(stage, str) and stage.strip():
        return f"Official checker rejected the submission at stage {stage.strip()}."
    return "Official checker returned a valid rejection."


class SubmissionGate:
    """Capture every valid candidate before enforcing checker-before-judge order."""

    def __init__(
        self,
        *,
        run: Path,
        problem_context: Mapping[str, Any],
        judge: JudgeEvaluator,
        checker: CheckerEvaluator,
        judge_max_seconds: float = JUDGE_MAX_SECONDS,
        checker_max_seconds: float = 900.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not 0 < judge_max_seconds <= JUDGE_MAX_SECONDS:
            raise ValueError("judge_max_seconds must be in (0, 120]")
        if checker_max_seconds <= 0:
            raise ValueError("checker_max_seconds must be positive")
        self.run = run.resolve()
        self.problem_context = dict(problem_context)
        self.judge = judge
        self.checker = checker
        self.judge_max_seconds = judge_max_seconds
        self.checker_max_seconds = checker_max_seconds
        self.clock = clock
        for name in ("submissions", "judgements", "execution"):
            (self.run / name).mkdir(parents=True, exist_ok=True)
        self.rejected_state = self.run / "execution/rejected-source-fingerprints.json"

    def _record_candidate(self, request: SubmissionRequest) -> Path:
        directory = self.run / "submissions" / request.submission_id
        try:
            directory.mkdir(parents=False, exist_ok=False)
        except FileExistsError as error:
            raise SubmissionProtocolError("submission_id was already used") from error
        source = directory / "source.py"
        source.write_text(request.source, encoding="utf-8")
        write_json_atomic(directory / "request.json", request.as_dict())
        source.chmod(0o444)
        (directory / "request.json").chmod(0o444)
        append_event(
            self.run,
            {
                "type": "submission_captured",
                "request_id": request.request_id,
                "submission_id": request.submission_id,
                "source_sha256": request.source_sha256,
            },
        )
        return source

    def _rejected_fingerprints(self) -> set[str]:
        if not self.rejected_state.is_file():
            return set()
        try:
            value = json.loads(self.rejected_state.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SubmissionProtocolError("rejected-source evidence is malformed") from error
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise SubmissionProtocolError("rejected-source evidence is malformed")
        return set(value)

    def _remember_rejection(self, fingerprint: str) -> None:
        fingerprints = self._rejected_fingerprints()
        fingerprints.add(fingerprint)
        write_json_atomic(self.rejected_state, sorted(fingerprints))

    def _response(
        self,
        request: SubmissionRequest,
        *,
        verdict: str,
        category: str,
        reason: str,
        judge_invoked: bool,
        checker_invoked: bool,
        checker_result: Mapping[str, Any] | None,
        run_deadline_monotonic: float,
    ) -> dict[str, Any]:
        if verdict == "reject" and category in {"checker_rejection", "checker_review_required"}:
            feedback = f"{reason} {CHECKER_REJECTION_FEEDBACK}"
        elif verdict == "reject" and category == "checker_failure":
            feedback = f"{reason} {CHECKER_FAILURE_FEEDBACK}"
        elif verdict == "reject" and category in {
            "judge_timeout",
            "judge_failure",
            "malformed_judge_output",
            "run_budget_exhausted",
        }:
            feedback = f"{reason} {JUDGE_FAILURE_FEEDBACK}"
        elif verdict == "reject":
            feedback = f"{reason} {ANTI_CHEATING_FEEDBACK}"
        else:
            feedback = (
                "The official checker passed and the judge approved this mathematical "
                "strategy. Continue to submit only genuinely natural constructions."
            )
        return {
            "schema_version": GATE_PROTOCOL_VERSION,
            "request_id": request.request_id,
            "submission_id": request.submission_id,
            "source_sha256": request.source_sha256,
            "verdict": verdict,
            "category": category,
            "reason": reason,
            "feedback_to_solver": feedback,
            "judge_invoked": judge_invoked,
            "checker_invoked": checker_invoked,
            "checker_result": dict(checker_result) if checker_result is not None else None,
            "run_budget_seconds_remaining": max(
                0.0, run_deadline_monotonic - self.clock()
            ),
        }

    def _reject(
        self,
        request: SubmissionRequest,
        judgement: Path,
        fingerprint: str,
        *,
        category: str,
        reason: str,
        run_deadline_monotonic: float,
        judge_invoked: bool,
        checker_invoked: bool = False,
        checker_result: Mapping[str, Any] | None = None,
        remember_fingerprint: bool = False,
    ) -> dict[str, Any]:
        if remember_fingerprint:
            self._remember_rejection(fingerprint)
        response = self._response(
            request,
            verdict="reject",
            category=category,
            reason=reason,
            judge_invoked=judge_invoked,
            checker_invoked=checker_invoked,
            checker_result=checker_result,
            run_deadline_monotonic=run_deadline_monotonic,
        )
        write_json_atomic(judgement / "verdict.json", response)
        append_event(
            self.run,
            {
                "type": "submission_rejected",
                "submission_id": request.submission_id,
                "source_sha256": request.source_sha256,
                "category": category,
                "judge_invoked": judge_invoked,
                "checker_invoked": checker_invoked,
            },
        )
        return response

    def process(
        self,
        request: SubmissionRequest,
        *,
        run_deadline_monotonic: float,
    ) -> dict[str, Any]:
        request.validated()
        source = self._record_candidate(request)
        judgement = self.run / "judgements" / request.submission_id
        judgement.mkdir(parents=True, exist_ok=False)
        fingerprint = ast_fingerprint(request.source)
        reject = partial(
            self._reject,
            request,
            judgement,
            fingerprint,
            run_deadline_monotonic=run_deadline_monotonic,
        )
        if fingerprint in self._rejected_fingerprints():
            return reject(
                category="repeated_rejected_source",
                reason="This is the same AST-normalized source as an earlier rejection.",
                judge_invoked=False,
            )
        checker_deadline = min(
            self.clock() + self.checker_max_seconds, run_deadline_monotonic
        )
        if checker_deadline <= self.clock():
            return reject(
                category="run_budget_exhausted",
                reason="The total inference run budget expired before checker execution.",
                judge_invoked=False,
            )
        try:
            checker_result = dict(
                self.checker.evaluate(
                    request.submission_id,
                    source,
                    request.source_sha256,
                    deadline_monotonic=checker_deadline,
                    evidence_directory=judgement,
                )
            )
        except Exception as error:
            checker_result = {
                "status": "failure",
                "error_type": type(error).__name__,
                "source_sha256": request.source_sha256,
            }
        write_json_atomic(judgement / "checker-result.json", checker_result)
        append_event(
            self.run,
            {
                "type": "checker_gate_result",
                "submission_id": request.submission_id,
                "source_sha256": request.source_sha256,
                "status": checker_result.get("status"),
                "exit_code": checker_result.get("exit_code"),
            },
        )
        if self.clock() >= checker_deadline:
            return reject(
                category="checker_failure",
                reason="The official checker exceeded the total run deadline.",
                judge_invoked=False,
                checker_invoked=True,
                checker_result=checker_result,
            )
        if checker_result.get("status") != "completed":
            return reject(
                category="checker_failure",
                reason="The official checker failed to produce a valid bound report.",
                judge_invoked=False,
                checker_invoked=True,
                checker_result=checker_result,
            )
        report = checker_result.get("report")
        if not isinstance(report, Mapping):
            return reject(
                category="checker_failure",
                reason="The official checker report was not a JSON object.",
                judge_invoked=False,
                checker_invoked=True,
                checker_result=checker_result,
            )
        if checker_result.get("source_sha256") != request.source_sha256:
            return reject(
                category="checker_failure",
                reason="The checker receipt was not bound to the captured source hash.",
                judge_invoked=False,
                checker_invoked=True,
                checker_result=checker_result,
            )
        passed = report.get("passed")
        automatic = report.get("automatic_verdict")
        expert = report.get("expert_review_required")
        exit_code = checker_result.get("exit_code")
        if exit_code == 1 and passed is False and automatic is False and expert is False:
            return reject(
                category="checker_rejection",
                reason=_checker_rejection_reason(checker_result),
                judge_invoked=False,
                checker_invoked=True,
                checker_result=checker_result,
                remember_fingerprint=True,
            )
        if exit_code == 1 and passed is False and automatic is None and expert is True:
            return reject(
                category="checker_review_required",
                reason=_checker_rejection_reason(checker_result),
                judge_invoked=False,
                checker_invoked=True,
                checker_result=checker_result,
            )
        if not (exit_code == 0 and passed is True and automatic is True and expert is False):
            return reject(
                category="checker_failure",
                reason="The official checker returned an internally inconsistent result.",
                judge_invoked=False,
                checker_invoked=True,
                checker_result=checker_result,
            )
        reject = partial(
            reject, checker_invoked=True, checker_result=checker_result
        )
        packet = build_judge_packet(self.problem_context, request)
        write_json_atomic(judgement / "judge-packet.json", packet)
        judge_deadline = min(
            self.clock() + self.judge_max_seconds, run_deadline_monotonic
        )
        if judge_deadline <= self.clock():
            return reject(
                category="run_budget_exhausted",
                reason="The total inference run budget expired before semantic review.",
                judge_invoked=False,
            )
        try:
            call = self.judge.evaluate(
                packet,
                deadline_monotonic=judge_deadline,
                evidence_directory=judgement,
            )
        except Exception as error:
            call = JudgeCallResult("failure", "", 0.0, error=type(error).__name__)
        write_json_atomic(
            judgement / "judge-call.json",
            {
                **asdict(call),
                "raw_output": "stored separately" if call.raw_output else "",
                "metadata": dict(call.metadata or {}),
                "source_sha256": request.source_sha256,
            },
        )
        if call.raw_output:
            (judgement / "judge-output.json").write_text(call.raw_output, encoding="utf-8")
        if self.clock() >= judge_deadline or call.status == "timeout":
            return reject(
                category="judge_timeout",
                reason=call.error or "The judge exceeded its deadline.",
                judge_invoked=True,
            )
        if call.status != "completed":
            return reject(
                category="judge_failure",
                reason=call.error or "The judge failed to produce a decision.",
                judge_invoked=True,
            )
        try:
            decision = JudgeDecision.parse(call.raw_output)
        except VerdictSchemaError as error:
            return reject(
                category="malformed_judge_output",
                reason=str(error),
                judge_invoked=True,
            )
        write_json_atomic(
            judgement / "judge-decision.json",
            {**decision.as_dict(), "source_sha256": request.source_sha256},
        )
        if decision.verdict == "reject":
            return reject(
                category=decision.category,
                reason=decision.reason,
                judge_invoked=True,
                remember_fingerprint=True,
            )
        response = self._response(
            request,
            verdict="approve",
            category="legitimate",
            reason=decision.reason,
            judge_invoked=True,
            checker_invoked=True,
            checker_result=checker_result,
            run_deadline_monotonic=run_deadline_monotonic,
        )
        write_json_atomic(judgement / "verdict.json", response)
        append_event(
            self.run,
            {
                "type": "submission_approved",
                "submission_id": request.submission_id,
                "source_sha256": request.source_sha256,
            },
        )
        return response


class AnchoredFileSubmissionBroker:
    """Exchange files through directory descriptors opened before the solver starts.

    The solver may rename or replace any pathname in its workspace. Host reads and
    writes therefore stay relative to retained directory descriptors, reject links
    and non-regular files, and never traverse a solver-controlled pathname.
    """

    _REQUEST_NAME = re.compile(r"([a-f0-9]{32})\.json\Z")

    def __init__(self, workspace: Path, gate: SubmissionGate) -> None:
        if os.name != "posix" or not all(
            hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")
        ):
            raise ValueError("the inference broker requires POSIX openat protections")
        self.workspace = workspace.resolve()
        self.gate = gate
        self.root = self.workspace / ".qtbench-ipc"
        self.staging = self.root / "staging"
        self.requests = self.root / "requests"
        self.responses = self.root / "responses"
        self.root.mkdir(mode=0o700)
        self.staging.mkdir(mode=0o700)
        self.requests.mkdir(mode=0o700)
        self.responses.mkdir(mode=0o700)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        self._requests_fd = os.open(self.requests, flags)
        try:
            self._responses_fd = os.open(self.responses, flags)
        except BaseException:
            os.close(self._requests_fd)
            raise
        self._ignored_request_names: set[str] = set()
        self.approved_response: dict[str, Any] | None = None
        self._closed = False

    @staticmethod
    def _read_regular_at(directory_fd: int, name: str, maximum: int) -> bytes:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        descriptor = os.open(name, flags, dir_fd=directory_fd)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise SubmissionProtocolError(
                    "submission request must be a single-link regular file"
                )
            if metadata.st_size <= 0 or metadata.st_size > maximum:
                raise SubmissionProtocolError("request exceeds size limit")
            blocks: list[bytes] = []
            remaining = maximum + 1
            while remaining:
                block = os.read(descriptor, min(65_536, remaining))
                if not block:
                    break
                blocks.append(block)
                remaining -= len(block)
            payload = b"".join(blocks)
            if not payload or len(payload) > maximum:
                raise SubmissionProtocolError("request exceeds size limit")
            return payload
        finally:
            os.close(descriptor)

    @staticmethod
    def _write_all(descriptor: int, payload: bytes) -> None:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short response write")
            view = view[written:]

    def _write_response(self, request_id: str, response: Mapping[str, Any]) -> None:
        payload = (json.dumps(response, sort_keys=True) + "\n").encode("utf-8")
        if len(payload) > MAX_RESPONSE_BYTES:
            raise SubmissionProtocolError("submission response exceeds size limit")
        final_name = f"{request_id}.json"
        temporary_name = f".{request_id}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        descriptor = os.open(
            temporary_name, flags, 0o600, dir_fd=self._responses_fd
        )
        try:
            self._write_all(descriptor, payload)
            os.fsync(descriptor)
        except BaseException:
            try:
                os.unlink(temporary_name, dir_fd=self._responses_fd)
            except FileNotFoundError:
                pass
            raise
        finally:
            os.close(descriptor)
        try:
            os.replace(
                temporary_name,
                final_name,
                src_dir_fd=self._responses_fd,
                dst_dir_fd=self._responses_fd,
            )
        except BaseException:
            try:
                os.unlink(temporary_name, dir_fd=self._responses_fd)
            except FileNotFoundError:
                pass
            raise

    @staticmethod
    def _safe_text(value: object, default: str) -> str:
        return value if isinstance(value, str) else default

    def _malformed_response(
        self,
        request_id: str,
        value: object,
        error: BaseException,
        run_deadline_monotonic: float,
    ) -> dict[str, Any]:
        mapping = value if isinstance(value, dict) else {}
        return {
            "schema_version": GATE_PROTOCOL_VERSION,
            "request_id": request_id,
            "submission_id": self._safe_text(mapping.get("submission_id"), "unknown"),
            "source_sha256": self._safe_text(mapping.get("source_sha256"), ""),
            "verdict": "reject",
            "category": "malformed_submission_request",
            "reason": str(error),
            "feedback_to_solver": f"Malformed request. {ANTI_CHEATING_FEEDBACK}",
            "judge_invoked": False,
            "checker_invoked": False,
            "checker_result": None,
            "run_budget_seconds_remaining": max(
                0.0, run_deadline_monotonic - time.monotonic()
            ),
        }

    def _next_request_name(self) -> str | None:
        with os.scandir(self._requests_fd) as entries:
            for index, entry in enumerate(entries):
                if index >= 64:
                    break
                if entry.name not in self._ignored_request_names:
                    return entry.name
        return None

    def poll(self, *, run_deadline_monotonic: float) -> tuple[int, float]:
        """Process at most one request so transport abuse cannot stall budgeting."""

        name = self._next_request_name()
        if name is None:
            return 0, 0.0
        gate_seconds = 0.0
        value: object = None
        match = self._REQUEST_NAME.fullmatch(name)
        request_id = match.group(1) if match else "0" * 32
        try:
            if match is None:
                raise SubmissionProtocolError("request filename is invalid")
            payload = self._read_regular_at(self._requests_fd, name, MAX_REQUEST_BYTES)
            try:
                value = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
                raise SubmissionProtocolError(
                    "request is not valid UTF-8 JSON"
                ) from error
            request = SubmissionRequest.parse(value)
            if request.request_id != request_id:
                raise SubmissionProtocolError("request ID does not match its filename")
            gate_started = time.monotonic()
            response = self.gate.process(
                request, run_deadline_monotonic=run_deadline_monotonic
            )
            if response.get("verdict") == "approve":
                self.approved_response = dict(response)
            gate_seconds = time.monotonic() - gate_started
        except (OSError, SubmissionProtocolError) as error:
            response = self._malformed_response(
                request_id, value, error, run_deadline_monotonic
            )
            append_event(
                self.gate.run,
                {
                    "type": "submission_request_rejected",
                    "request_id": request_id,
                    "reason": str(error),
                },
            )
        finally:
            try:
                os.unlink(name, dir_fd=self._requests_fd)
            except FileNotFoundError:
                pass
            except OSError as error:
                self._ignored_request_names.add(name)
                append_event(
                    self.gate.run,
                    {
                        "type": "submission_request_cleanup_failed",
                        "request_id": request_id,
                        "reason": type(error).__name__,
                    },
                )
        if match is not None:
            try:
                self._write_response(request_id, response)
            except (OSError, SubmissionProtocolError) as error:
                append_event(
                    self.gate.run,
                    {
                        "type": "submission_response_failed",
                        "request_id": request_id,
                        "reason": type(error).__name__,
                    },
                )
        return 1, gate_seconds

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        os.close(self._requests_fd)
        os.close(self._responses_fd)
