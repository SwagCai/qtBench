#!/usr/bin/env python3
"""Generate Chern--Fu Question 5.5 fibers."""
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

from qtbench.combinatorics import (
    iter_improper_partition_matrices,
    iter_restricted_inversion_sequences,
)

PROBLEM_ID = 30
PROBLEM_NAME = "improper_partition_matrix_inversion_sequence_bijection"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=9)
    args = parser.parse_args()
    if args.public_max_n < 3:
        parser.error("--public-max-n must be at least 3")
    problem_dir = args.problem_dir.resolve()
    metadata = json.loads((problem_dir / "metadata.json").read_text(encoding="utf-8"))
    if (metadata.get("id"), metadata.get("name")) != (PROBLEM_ID, PROBLEM_NAME):
        raise SystemExit(
            f"--problem-dir must identify problem {PROBLEM_ID} ({PROBLEM_NAME})"
        )
    polynomial_cases = []
    instance_cases = []
    for n in range(3, args.public_max_n + 1):
        source = iter_improper_partition_matrices(n)
        target = iter_restricted_inversion_sequences(n)
        source_distribution = Counter(obj.grading for obj in source)
        target_distribution = Counter(obj.grading for obj in target)
        if source_distribution != target_distribution:
            raise SystemExit(f"n={n}: source and target grading distributions differ")
        case_id = f"n{n:02d}"
        terms = [[grading, source_distribution[grading]] for grading in sorted(source_distribution)]
        polynomial_cases.append(
            {
                "case_id": case_id,
                "n": n,
                "count": len(source),
                "target_count": len(target),
                "term_count": len(terms),
                "terms": terms,
            }
        )
        sample = source[: min(8, len(source))]
        instance_cases.append(
            {
                "case_id": case_id,
                "n": n,
                "count": len(sample),
                "entries": [
                    {"matrix": obj.encoding, "semi_weight": obj.grading} for obj in sample
                ],
            }
        )
    identity = {"problem_id": PROBLEM_ID, "problem_name": PROBLEM_NAME}
    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "0.1",
        **identity,
        "variables": ["grading"],
        "statistics": {"source": "semi_weight", "target": "distinct_entries"},
        "public_max_n": args.public_max_n,
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
                "specialization": {"grading": 1},
                "meaning": "Unrefined cardinality of each size fiber.",
                "public_max_n": args.public_max_n,
                "case_count": len(polynomial_cases),
                "cases": [
                    {
                        "case_id": case["case_id"],
                        "n": case["n"],
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
                "object_family": "improper_partition_matrices_and_restricted_inversion_sequences",
                "public_max_n": args.public_max_n,
                "case_count": len(instance_cases),
                "cases": instance_cases,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8", newline="\n",
    )

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
