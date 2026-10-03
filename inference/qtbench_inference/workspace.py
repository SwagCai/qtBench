"""Build one-problem solver workspaces from explicit public inputs."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid
from typing import Any


INPUT_MANIFEST = ".qtbench-solver-inputs.json"
ALLOWLIST_POLICY = "qtbench-inference-explicit-input-allowlist-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class ProblemSpec:
    problem_id: int
    name: str
    title: str
    task_type: str
    statement_path: Path
    problem_root: Path
    metadata_path: Path
    data_path: Path
    evaluator_kind: str
    submission_signature: str
    known_file: Path | None
    statement: str
    metadata: dict[str, Any]

    def judge_context(self) -> dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "problem_name": self.name,
            "title": self.title,
            "task_type": self.task_type,
            "problem_statement": self.statement,
            "submission_interface": self.submission_signature,
            "checker_protocol": {
                "evaluator_kind": self.evaluator_kind,
                "public_cases": self.metadata.get("public_cases", {}),
                "scoring": self.metadata.get("scoring", {}),
            },
        }


def _safe_repo_path(repo: Path, relative: str | Path) -> Path:
    candidate = (repo / Path(relative)).resolve()
    if not _under(candidate, repo) or candidate.is_symlink():
        raise ValueError(f"unsafe repository path: {relative}")
    return candidate


def resolve_problem(repo: Path, selector: str) -> ProblemSpec:
    repo = repo.resolve()
    registry_path = repo / "problems/registry.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        entries = registry["problems"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError("repository has no valid problems/registry.json") from error
    if not isinstance(entries, list):
        raise ValueError("problem registry entries must be a list")
    numeric = selector.isdecimal()
    matches = [
        entry
        for entry in entries
        if isinstance(entry, dict)
        and (
            entry.get("id") == int(selector)
            if numeric
            else entry.get("name") == selector
        )
    ]
    if len(matches) != 1:
        raise ValueError(f"problem selector {selector!r} did not identify one problem")
    entry = matches[0]
    try:
        problem_id = entry["id"]
        name = entry["name"]
        title = entry["title"]
        task_type = entry["task_type"]
        statement_relative = Path(entry["problem_statement"])
        data_relative = Path(entry["data"])
    except (KeyError, TypeError) as error:
        raise ValueError("selected registry entry is malformed") from error
    if type(problem_id) is not int or problem_id <= 0:
        raise ValueError("selected problem has an invalid numeric id")
    if not all(
        isinstance(value, str) and value.strip()
        for value in (name, title, task_type)
    ):
        raise ValueError("selected problem is missing required text fields")
    statement_path = _safe_repo_path(repo, statement_relative)
    problem_root = statement_path.parent
    metadata_path = _safe_repo_path(repo, problem_root.relative_to(repo) / "metadata.json")
    data_path = _safe_repo_path(repo, data_relative)
    try:
        statement = statement_path.read_text(encoding="utf-8")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("selected problem statement or metadata is malformed") from error
    if not statement.strip() or not isinstance(metadata, dict):
        raise ValueError("selected problem statement or metadata is empty")
    if metadata.get("id") != problem_id or metadata.get("name") != name:
        raise ValueError("registry and problem metadata disagree")
    evaluator_kind = metadata.get("evaluator_kind")
    submission_signature = metadata.get("submission_signature")
    if not isinstance(evaluator_kind, str) or not evaluator_kind.strip():
        raise ValueError("problem metadata has no evaluator_kind")
    if not isinstance(submission_signature, str) or not submission_signature.strip():
        raise ValueError("problem metadata has no submission_signature")
    known_name = metadata.get("known_statistic_file") or metadata.get(
        "known_statistics_file"
    )
    known_file = (
        _safe_repo_path(repo, problem_root.relative_to(repo) / str(known_name))
        if known_name
        else None
    )
    return ProblemSpec(
        problem_id=problem_id,
        name=name,
        title=title,
        task_type=task_type,
        statement_path=statement_path,
        problem_root=problem_root,
        metadata_path=metadata_path,
        data_path=data_path,
        evaluator_kind=evaluator_kind,
        submission_signature=submission_signature,
        known_file=known_file,
        statement=statement,
        metadata=metadata,
    )


def repository_revision(repo: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("qtBench checkout must be a Git repository") from error


def _tracked_files(repo: Path, roots: list[Path]) -> list[Path]:
    relative_roots = [root.resolve().relative_to(repo.resolve()) for root in roots]
    try:
        output = subprocess.check_output(
            ["git", "-C", str(repo), "ls-files", "--", *map(str, relative_roots)],
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError("could not enumerate tracked solver inputs") from error
    files = sorted(Path(line) for line in output.splitlines() if line)
    for root, relative in zip(roots, relative_roots, strict=True):
        if root.is_file() and relative not in files:
            raise ValueError(f"required solver input is not tracked: {relative}")
        if root.is_dir() and not any(_under(path, relative) for path in files):
            raise ValueError(f"required solver input directory is empty: {relative}")
    dirty = subprocess.check_output(
        [
            "git",
            "-C",
            str(repo),
            "status",
            "--porcelain",
            "--untracked-files=no",
            "--",
            *map(str, relative_roots),
        ],
        text=True,
    )
    if dirty.strip():
        raise ValueError("public inputs for the selected problem must be committed")
    return files


def _write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def prepare_solver_workspace(
    repo: Path,
    destination: Path,
    problem: ProblemSpec,
    *,
    submit_client: Path,
) -> dict[str, Any]:
    """Copy only the public material needed to work on one selected problem."""

    repo = repo.resolve()
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"refusing to replace solver workspace: {destination}")
    roots = [
        repo / "docs/checker.md",
        repo / "src/qtbench/__init__.py",
        repo / "src/qtbench/combinatorics",
        problem.statement_path,
        problem.metadata_path,
        problem.data_path,
    ]
    if problem.known_file is not None:
        roots.append(problem.known_file)
    tracked = _tracked_files(repo, roots)
    destination.mkdir(parents=True)
    destination.chmod(0o700)
    for relative in tracked:
        origin = repo / relative
        if origin.is_symlink() or not origin.is_file():
            raise ValueError(f"solver input is not a regular file: {relative}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
    shutil.copy2(problem.statement_path, destination / "CURRENT_PROBLEM.md")
    client = destination / ".qtbench-bin/qtbench-submit"
    client.parent.mkdir()
    shutil.copy2(submit_client, client)
    client.chmod(0o755)
    for reserved in (".codex", ".git", ".agents"):
        if (destination / reserved).exists():
            raise ValueError(f"reserved solver control path was populated: {reserved}")
    revision = repository_revision(repo)
    copied = sorted(path for path in destination.rglob("*") if path.is_file())
    evidence = {
        "schema_version": 1,
        "policy": ALLOWLIST_POLICY,
        "problem_id": problem.problem_id,
        "problem_name": problem.name,
        "benchmark_revision": revision,
        "allowlisted_roots": [str(path.relative_to(repo)) for path in roots],
        "files": [
            {
                "path": str(path.relative_to(destination)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in copied
        ],
        "excluded": [
            "other benchmark problems",
            "checker implementation",
            "generation oracles",
            "example and proposed solutions",
            "trajectory history",
            "Git history",
            "host credentials",
        ],
    }
    _write_json_atomic(destination / INPUT_MANIFEST, evidence)
    return evidence


def verify_solver_inputs(workspace: Path) -> dict[str, Any]:
    try:
        value = json.loads((workspace / INPUT_MANIFEST).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("solver input manifest is malformed") from error
    if value.get("policy") != ALLOWLIST_POLICY or not isinstance(
        value.get("files"), list
    ):
        raise ValueError("solver input manifest is malformed")
    for entry in value["files"]:
        path = workspace / entry["path"]
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing solver input: {entry['path']}")
        if path.stat().st_size != entry["bytes"] or sha256_file(path) != entry["sha256"]:
            raise ValueError(f"solver input changed: {entry['path']}")
    return value
