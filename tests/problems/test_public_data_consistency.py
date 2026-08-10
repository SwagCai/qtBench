from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
METADATA = sorted((ROOT / "problems").glob("*/*/metadata.json"))


def known_statistics(metadata: dict) -> list[str]:
    declared = metadata.get("known_statistics")
    if declared is None:
        declared = [metadata["known_statistic"]] if metadata.get("known_statistic") else []
    return [name for name in declared if name]


@pytest.mark.parametrize("metadata_path", METADATA, ids=lambda p: p.parent.name)
def test_instances_agree_with_the_target_marginal(metadata_path: Path) -> None:
    """`instances.json` and `polynomials.json` must tell the same story.

    Summing the target over every unknown exponent has to reproduce the
    multiset of public statistic values recorded per object. A participant
    reads both files, so a disagreement between them is a benchmark defect even
    though the same generator wrote both.
    """

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    declared = known_statistics(metadata)
    target = json.loads((metadata_path.parent / "data/polynomials.json").read_text())
    variables = target["variables"]

    if not declared:
        assert metadata.get("known_statistics") == [], (
            f"{metadata['name']} has no declared public statistic"
        )
        return
    if len(declared) >= len(variables):
        assert metadata["task_type"] == "exchanging_bijection", (
            f"{metadata['name']} leaves no unknown grading variable"
        )
        return

    # A leading "partition" entry indexes the target; it is not an exponent.
    offset = 1 if variables[0] == "partition" else 0
    instances = json.loads((metadata_path.parent / "data/instances.json").read_text())
    by_case = {case["case_id"]: case for case in target["cases"]}

    compared = 0
    for case in instances["cases"]:
        target_case = by_case[case["case_id"]]
        entries = case["entries"]
        if not entries or not isinstance(entries[0], dict):
            continue

        observed = Counter(
            tuple(entry[name] for name in declared) for entry in entries
        )
        expected: Counter[tuple[int, ...]] = Counter()
        for term in target_case["terms"]:
            expected[tuple(term[offset + i] for i in range(len(declared)))] += term[-1]

        assert observed == expected, f"{metadata_path.parent.name}/{case['case_id']}"
        compared += sum(observed.values())

    assert compared > 0, "no objects were compared"


@pytest.mark.parametrize("metadata_path", METADATA, ids=lambda p: p.parent.name)
def test_instances_are_a_labelled_subset_of_the_scored_range(metadata_path: Path) -> None:
    """`instances.json` shows fewer fibers than scoring uses, and must say so.

    The instance sample can use a smaller bound than the public target. A reader
    who treats `instances.json` as the scored range would therefore validate
    against a fraction of what is scored. Every problem whose sample is strictly
    smaller has to disclose that in its statement.
    """

    problem_dir = metadata_path.parent
    target = json.loads((problem_dir / "data/polynomials.json").read_text())
    instances = json.loads((problem_dir / "data/instances.json").read_text())

    target_cases = {case["case_id"] for case in target["cases"]}
    instance_cases = {case["case_id"] for case in instances["cases"]}
    assert instance_cases <= target_cases, "instances.json has cases that are not scored"

    if instance_cases == target_cases:
        return

    statement = (problem_dir / "problem.md").read_text(encoding="utf-8")
    assert "is a sample, not the scored set" in statement, (
        f"{problem_dir.name} publishes {len(instance_cases)} of "
        f"{len(target_cases)} scored fibers without saying so in problem.md"
    )


@pytest.mark.parametrize("metadata_path", METADATA, ids=lambda p: p.parent.name)
def test_marginal_file_is_derivable_from_the_target(metadata_path: Path) -> None:
    """`q_equals_1.json` must be exactly what its name and header claim.

    For most problems it is the target summed over the submitted exponent. For
    the three whose target is already one-variable it is instead a re-grading by
    an index read off the object, and then the only derivable statement is that
    each case totals the object count. Both forms are checked here, so neither
    file can drift from the other.
    """

    problem_dir = metadata_path.parent
    target = json.loads((problem_dir / "data/polynomials.json").read_text())
    marginal = json.loads((problem_dir / "data/q_equals_1.json").read_text())
    by_case = {case["case_id"]: case for case in marginal["cases"]}

    assert {c["case_id"] for c in marginal["cases"]} == {
        c["case_id"] for c in target["cases"]
    }, "marginal and target cover different cases"

    dropped = [v for v in target["variables"] if v not in marginal["variables"]]
    regrades = not set(marginal["variables"]) <= set(target["variables"])

    compared = 0
    for case in target["cases"]:
        shipped = by_case[case["case_id"]]
        if regrades:
            # fiber-size check: the only invariant is the total
            assert sum(t[-1] for t in shipped["terms"]) == case["count"], case["case_id"]
            compared += 1
            continue
        keep = [i for i, v in enumerate(target["variables"]) if v not in dropped]
        derived: Counter[str] = Counter()
        for term in case["terms"]:
            derived[json.dumps([term[i] for i in keep], sort_keys=True)] += term[-1]
        actual: Counter[str] = Counter()
        for term in shipped["terms"]:
            actual[json.dumps(list(term[:-1]), sort_keys=True)] += term[-1]
        assert derived == actual, f"{problem_dir.name}/{case['case_id']}"
        compared += len(derived)

    assert compared > 0


# Encoding examples a statement shows are the first thing a reader types in.
# Each entry is (problem directory name, encoding shown in problem.md).
STATEMENT_ENCODINGS = [
    (path.parent.name, encoding)
    for path in METADATA
    for encoding in re.findall(
        r"```text\n([0-9A-Za-z,;|/.\-]+)\n```", (path.parent / "problem.md").read_text()
    )
    if ("|" in encoding or "," in encoding)
    # skip schema lines like "bottom|top|word|selected": an object encoding
    # always carries digits, a field-name template never does.
    and any(character.isdigit() for character in encoding)
]


def test_statement_encoding_examples_are_discovered() -> None:
    assert STATEMENT_ENCODINGS, (
        "the statement-example collector found nothing; its syntax contract may have drifted"
    )


@pytest.mark.parametrize(
    "problem_name,encoding",
    STATEMENT_ENCODINGS,
    ids=[f"{n}-{e[:24]}" for n, e in STATEMENT_ENCODINGS],
)
def test_statement_encoding_examples_are_real_objects(problem_name, encoding) -> None:
    """A worked encoding in a statement must be an object the benchmark has.

    Two of these named a cell that the object does not contain, which a reader
    would hit while building their very first object.
    """

    problem_dir = next((ROOT / "problems").glob(f"*/{problem_name}"))
    instances = json.loads((problem_dir / "data/instances.json").read_text())

    published = set()
    for case in instances["cases"]:
        for entry in case["entries"]:
            value = entry
            if isinstance(entry, dict):
                key = next(k for k in entry if not isinstance(entry[k], int))
                value = entry[key]
            if isinstance(value, str):
                published.add(value)

    assert encoding in published, (
        f"{problem_name}: problem.md shows {encoding!r}, which is not among the "
        f"objects the problem publishes. A worked example must be one a reader "
        f"can find in data/instances.json."
    )
