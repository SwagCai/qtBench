#!/usr/bin/env python3
"""Generate finite Corollary 4.1 shifted-tableau fibers."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.combinatorics import iter_shifted_setvalued_tableaux, shifted_extensions

PROBLEM_ID = 28
PROBLEM_NAME = "shifted_setvalued_pq_weight_bijection"
PUBLIC_CASES = (
    ((3, 1), (1, 1, 1, 1)),
    ((3, 1), (2, 1, 1)),
    ((3, 1), (1, 1, 1, 1, 1)),
    ((3, 1), (2, 2, 1)),
    ((3, 2), (1, 1, 1, 1, 1)),
    ((3, 2), (3, 2, 1, 1)),
    ((3, 2), (4, 2, 1)),
)


def fiber(mu: tuple[int, ...], content: tuple[int, ...]):
    source = list(iter_shifted_setvalued_tableaux("Q", mu, mu, content))
    target = []
    for shape, sign in shifted_extensions(mu):
        tableaux = list(iter_shifted_setvalued_tableaux("P", mu, shape, content))
        (source if sign < 0 else target).extend(tableaux)
    if len(source) != len(target):
        raise SystemExit(
            f"mu={mu} content={content}: source count {len(source)} "
            f"does not match target count {len(target)}"
        )
    if len({obj.encoding for obj in source}) != len(source):
        raise SystemExit(f"mu={mu} content={content}: duplicate source tableau")
    if len({obj.encoding for obj in target}) != len(target):
        raise SystemExit(f"mu={mu} content={content}: duplicate target tableau")
    return source, target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    problem_dir = args.problem_dir.resolve()
    metadata = json.loads((problem_dir / "metadata.json").read_text(encoding="utf-8"))
    if (metadata.get("id"), metadata.get("name")) != (PROBLEM_ID, PROBLEM_NAME):
        raise SystemExit(
            f"--problem-dir must identify problem {PROBLEM_ID} ({PROBLEM_NAME})"
        )
    polynomial_cases = []
    instance_cases = []
    for index, (mu, content) in enumerate(PUBLIC_CASES, 1):
        source, target = fiber(mu, content)
        case_id = f"f{index:02d}"
        component_counts = Counter(obj.family + ":" + ",".join(map(str, obj.shape)) for obj in source)
        polynomial_cases.append(
            {
                "case_id": case_id,
                "mu": list(mu),
                "content": list(content),
                "count": len(source),
                "source_component_counts": [[key, component_counts[key]] for key in sorted(component_counts)],
                "target_count": len(target),
                "term_count": 1,
                "terms": [[sum(content), len(source)]],
            }
        )
        sample = source[: min(8, len(source))]
        instance_cases.append(
            {
                "case_id": case_id,
                "mu": list(mu),
                "content": list(content),
                "count": len(sample),
                "entries": [
                    {"tableau": obj.encoding, "entry_count": obj.entry_count} for obj in sample
                ],
            }
        )
    identity = {"problem_id": PROBLEM_ID, "problem_name": PROBLEM_NAME}
    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "0.1",
        **identity,
        "variables": ["entry_count"],
        "statistics": {"entry_count": "entry_count"},
        "case_count": len(polynomial_cases),
        "cases": polynomial_cases,
    }
    (data_dir / "polynomials.json").write_text(json.dumps(payload, indent=2), encoding="utf-8", newline="\n")
    (data_dir / "q_equals_1.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                **identity,
                "variables": [],
                "specialization": {"entry_count": 1},
                "meaning": "Unrefined cardinality of each fixed-content fiber.",
                "case_count": len(polynomial_cases),
                "cases": [
                    {
                        "case_id": case["case_id"],
                        "mu": case["mu"],
                        "content": case["content"],
                        "count": case["count"],
                        "term_count": 1,
                        "terms": [[case["count"]]],
                    }
                    for case in polynomial_cases
                ],
            },
            indent=2,
        ),
        encoding="utf-8", newline="\n",
    )
    (data_dir / "instances.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                **identity,
                "object_family": "set_valued_shifted_tableaux",
                "case_count": len(instance_cases),
                "cases": instance_cases,
            },
            indent=2,
        ),
        encoding="utf-8", newline="\n",
    )

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
