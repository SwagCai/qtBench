#!/usr/bin/env python3
"""Generate finite Andrews--Bressoud partition fibers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.combinatorics import iter_successive_rank_partitions

PROBLEM_ID = 29
PROBLEM_NAME = "andrews_bressoud_successive_rank_bijection"
PUBLIC_CASES = tuple(
    (modulus, residue, weight)
    for modulus, residue in ((6, 1), (6, 2), (7, 2), (7, 3))
    for weight in (12, 20, 28)
)


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
    for modulus, residue, weight in PUBLIC_CASES:
        source = iter_successive_rank_partitions("source", modulus, residue, weight)
        target = iter_successive_rank_partitions("target", modulus, residue, weight)
        if len(source) != len(target):
            raise SystemExit(
                f"modulus={modulus} residue={residue} weight={weight}: "
                f"source count {len(source)} does not match target count {len(target)}"
            )
        case_id = f"m{modulus:02d}_r{residue:02d}_n{weight:02d}"
        polynomial_cases.append(
            {
                "case_id": case_id,
                "modulus": modulus,
                "residue": residue,
                "weight": weight,
                "count": len(source),
                "target_count": len(target),
                "term_count": 1,
                "terms": [[weight, len(source)]],
            }
        )
        sample = source[: min(8, len(source))]
        instance_cases.append(
            {
                "case_id": case_id,
                "modulus": modulus,
                "residue": residue,
                "weight": weight,
                "count": len(sample),
                "entries": [
                    {"partition": obj.encoding, "successive_ranks": list(obj.ranks)}
                    for obj in sample
                ],
            }
        )
    identity = {"problem_id": PROBLEM_ID, "problem_name": PROBLEM_NAME}
    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "0.1",
        **identity,
        "variables": ["weight"],
        "statistics": {"weight": "sum_of_parts"},
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
                "specialization": {"weight": 1},
                "meaning": "Unrefined cardinality of each fixed-parameter fiber.",
                "case_count": len(polynomial_cases),
                "cases": [
                    {
                        "case_id": case["case_id"],
                        "modulus": case["modulus"],
                        "residue": case["residue"],
                        "weight": case["weight"],
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
                "object_family": "integer_partitions_with_successive_rank_or_residue_constraints",
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
