#!/usr/bin/env python3
"""Stdlib-only synchronous client for the workspace-local submission broker."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import sys
import time


PROTOCOL_VERSION = 1
MAX_RESPONSE_BYTES = 64_000_000
_SUBMISSION_ID = re.compile(r"s[0-9]{4,}\Z")
_RESPONSE_FIELDS = {
    "schema_version",
    "request_id",
    "submission_id",
    "source_sha256",
    "verdict",
    "category",
    "reason",
    "feedback_to_solver",
    "judge_invoked",
    "checker_invoked",
    "checker_result",
    "run_budget_seconds_remaining",
}


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError("short submission request write")
        view = view[written:]


def _atomic_request(staging: Path, path: Path, payload: bytes) -> None:
    temporary = staging / f".{path.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    descriptor = os.open(temporary, flags, 0o600)
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(descriptor)
    try:
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _read_regular(path: Path, maximum: int) -> bytes:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > maximum:
            raise ValueError("submission broker response is not a bounded regular file")
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
            raise ValueError("submission broker response exceeds size limit")
        return payload
    finally:
        os.close(descriptor)


def submit(
    gate_directory: Path,
    request: dict,
    *,
    wait_seconds: float,
) -> dict:
    payload = json.dumps(request, sort_keys=True).encode("utf-8")
    if len(payload) > 128_000:
        raise ValueError("request exceeds size limit")
    if not 0 < wait_seconds < float("inf"):
        raise ValueError("wait interval must be finite and positive")
    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not re.fullmatch(r"[a-f0-9]{32}", request_id):
        raise ValueError("request ID is invalid")
    requests = gate_directory / "requests"
    responses = gate_directory / "responses"
    staging = gate_directory / "staging"
    request_path = requests / f"{request_id}.json"
    response_path = responses / f"{request_id}.json"
    _atomic_request(staging, request_path, payload)
    deadline = time.monotonic() + wait_seconds
    try:
        while True:
            try:
                response_payload = _read_regular(response_path, MAX_RESPONSE_BYTES)
                break
            except FileNotFoundError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("submission broker response deadline exceeded")
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        response = json.loads(response_payload.decode("utf-8"))
    finally:
        try:
            response_path.unlink()
        except FileNotFoundError:
            pass
    if (
        not isinstance(response, dict)
        or set(response) != _RESPONSE_FIELDS
        or response.get("schema_version") != PROTOCOL_VERSION
        or response.get("request_id") != request["request_id"]
        or response.get("submission_id") != request["submission_id"]
        or response.get("source_sha256") != request["source_sha256"]
        or response.get("verdict") not in {"approve", "reject"}
    ):
        raise ValueError("response does not match this request")
    return response


def main() -> None:
    parser = argparse.ArgumentParser(prog="qtbench-submit")
    parser.add_argument("--submission-id", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--derivation", required=True)
    parser.add_argument("--parents", default="")
    parser.add_argument("--wait-seconds", type=float, default=1800.0)
    args = parser.parse_args()
    if not _SUBMISSION_ID.fullmatch(args.submission_id):
        raise SystemExit("invalid submission ID")
    if not 0 < args.wait_seconds < float("inf"):
        raise SystemExit("wait interval must be finite and positive")
    source_path = Path(args.source)
    if not source_path.is_file() or source_path.is_symlink():
        raise SystemExit("source must be a regular non-symlink file")
    source = source_path.read_text(encoding="utf-8")
    if not source.strip() or len(source.encode("utf-8")) > 64_000:
        raise SystemExit("source must contain 1-64000 UTF-8 bytes")
    if not args.description.strip() or not args.derivation.strip():
        raise SystemExit("description and derivation are required")
    parents = [item for item in args.parents.split(",") if item]
    if len(set(parents)) != len(parents) or any(
        not _SUBMISSION_ID.fullmatch(item) for item in parents
    ):
        raise SystemExit("invalid or repeated parent ID")
    request_id = secrets.token_hex(16)
    request = {
        "schema_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "submission_id": args.submission_id,
        "source": source,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "description": args.description,
        "derivation": args.derivation,
        "parents": parents,
    }
    gate = Path(os.environ.get("QTBENCH_GATE_DIRECTORY", ".qtbench-ipc"))
    try:
        response = submit(gate, request, wait_seconds=args.wait_seconds)
    except (OSError, ValueError, TimeoutError, json.JSONDecodeError) as error:
        raise SystemExit(f"submission gate failed closed: {error}") from error
    print(json.dumps(response, indent=2, sort_keys=True))
    if response["verdict"] != "approve":
        raise SystemExit(3)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(1)
