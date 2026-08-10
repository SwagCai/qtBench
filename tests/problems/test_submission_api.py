"""The contract a participant actually programs against.

Two things a reader relies on and would hit within minutes of starting:
the public statistic implementation must agree with the object model's own
method, and every attribute a statement advertises must exist.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

import qtbench.evaluation.admission as admission

ROOT = Path(__file__).resolve().parents[2]
METADATA = sorted(
    (ROOT / "problems").glob("*/*/metadata.json"),
    key=lambda path: json.loads(path.read_text())["id"],
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _evaluator_kinds() -> dict[Path, str]:
    cli = _load(ROOT / "scripts/evaluate/evaluate_scored_submission.py", "qtbench_cli_api")
    return {Path(path).resolve(): kind for kind, path in cli.DEFAULT_PROBLEM.items()}


KINDS = _evaluator_kinds()
EVALUATOR_KIND_ALIASES = {"type-b": "type_b"}


class _SampleLimitReached(Exception):
    """Stop an evaluator after the requested number of objects was observed."""


def _sample_objects(problem_dir: Path, limit: int) -> list | None:
    """Take real objects from the evaluator's own enumeration."""
    public_kind = KINDS[problem_dir.resolve()]
    kind = EVALUATOR_KIND_ALIASES.get(public_kind, public_kind)
    evaluator = admission._STATISTIC_EVALUATORS.get(kind)
    if evaluator is None:
        return None
    collected: list = []

    def recorder(obj):
        if len(collected) < limit:
            collected.append(obj)
        if len(collected) == limit:
            raise _SampleLimitReached
        if kind == "uig":
            return (obj.n,)
        if kind == "kostka":
            return (0, 0)
        return 0

    try:
        evaluator(problem_dir=problem_dir, statistic=recorder, order_seed=None)
    except _SampleLimitReached:
        pass
    return collected


# The object model sometimes exposes a statistic under a fuller accessor name
# than the one the target grades by. Comparison still has to happen, so the
# mapping is explicit rather than silently skipped.
METHOD_ALIASES = {"sel": "selected_count"}


def _declared(metadata: dict) -> list[str]:
    declared = metadata.get("known_statistics")
    if declared is None:
        declared = [metadata["known_statistic"]] if metadata.get("known_statistic") else []
    return [name for name in declared if name]


@pytest.mark.parametrize("metadata_path", METADATA, ids=lambda p: p.parent.name)
def test_public_statistic_file_agrees_with_the_object_method(metadata_path: Path) -> None:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    files = [
        metadata[key]
        for key in ("known_statistic_file", "known_statistics_file")
        if key in metadata
    ]
    declared = _declared(metadata)
    if not files or not declared:
        assert not files and not declared, (
            f"{metadata['name']} must declare both a public statistic and its file"
        )
        return
    assert len(files) == 1, f"{metadata['name']} declares ambiguous statistic files"

    objects = _sample_objects(metadata_path.parent, limit=200)
    if objects is None:
        assert metadata["task_type"] == "exchanging_bijection", (
            f"{metadata['name']} is missing a statistic evaluator adapter"
        )
        return
    assert objects, f"{metadata['name']} evaluator enumerated no objects"

    module = _load(metadata_path.parent / files[0], f"known_{metadata['id']}")
    compared = 0
    for name in declared:
        function = getattr(module, name, None)
        if function is None and len(declared) == 1:
            function = getattr(module, "statistic", None)
        accessor = METHOD_ALIASES.get(name, name)
        method = getattr(type(objects[0]), accessor, None)
        assert function is not None, f"{name} has no implementation in {files[0]}"
        assert method is not None, (
            f"the object model exposes no accessor for {name!r}; add it to "
            f"METHOD_ALIASES so the two stay comparable"
        )
        for obj in objects:
            assert function(obj) == getattr(obj, accessor)(), (
                f"{name} disagrees with {accessor}() on {obj.encoding}"
            )
            compared += 1
    assert compared > 0, "nothing was compared"


@pytest.mark.parametrize("metadata_path", METADATA, ids=lambda p: p.parent.name)
def test_statement_advertises_only_attributes_that_exist(metadata_path: Path) -> None:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    objects = _sample_objects(metadata_path.parent, limit=1)
    if objects is None:
        assert metadata["task_type"] == "exchanging_bijection", (
            f"{metadata['name']} is missing a statistic evaluator adapter"
        )
        return
    assert objects, f"{metadata['name']} evaluator enumerated no objects"

    signature = metadata.get("submission_signature", "")
    match = re.search(r"\(([a-z_]+)\)", signature)
    assert match, f"{metadata['name']} has no parseable submission signature"
    parameter = match.group(1)

    statement = (metadata_path.parent / "problem.md").read_text(encoding="utf-8")
    advertised = set(re.findall(rf"`{parameter}\.([a-z_]+)", statement))
    assert advertised, f"{metadata['name']} advertises no object attributes"

    absent = sorted(name for name in advertised if not hasattr(objects[0], name))
    assert not absent, f"{metadata['name']} advertises nonexistent attributes: {absent}"
