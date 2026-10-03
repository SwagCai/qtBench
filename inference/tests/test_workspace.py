from __future__ import annotations

import json
from pathlib import Path
import shutil

from qtbench_inference.workspace import (
    prepare_solver_workspace,
    resolve_problem,
    verify_solver_inputs,
)


def test_every_registry_problem_builds_from_the_public_allowlist(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    registry = json.loads((repo / "problems/registry.json").read_text())
    submit_client = repo / "inference/qtbench_inference/submit_client.py"

    for entry in registry["problems"]:
        problem = resolve_problem(repo, str(entry["id"]))
        assert resolve_problem(repo, problem.name).problem_id == problem.problem_id
        workspace = tmp_path / f"p{problem.problem_id:02d}"
        evidence = prepare_solver_workspace(
            repo, workspace, problem, submit_client=submit_client
        )
        assert verify_solver_inputs(workspace)["problem_id"] == problem.problem_id
        paths = {item["path"] for item in evidence["files"]}
        assert "CURRENT_PROBLEM.md" in paths
        assert ".qtbench-bin/qtbench-submit" in paths
        assert not any((workspace / name).exists() for name in (".codex", ".git", ".agents"))
        assert not any("oracle" in path or "generate_data" in path for path in paths)
        shutil.rmtree(workspace)
