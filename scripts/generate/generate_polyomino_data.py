#!/usr/bin/env python3
"""Generate public data for the two parallelogram polyomino bijection problems.

This is the one generator that is *not* problem-specific, which is why it lives
here rather than under a single problem directory: problems ``4``
(`polyomino_area_bounce_exchange`) and ``5`` (`polyomino_area_bounce_transpose`)
consume exactly the same area/bounce data and differ only in the identity stamped
from ``--problem-dir``. Run it once per problem.

Writes the q,t-Narayana polynomials (joint area/bounce distribution over
parallelogram polyominoes with each ``m x n`` bounding box), their q=1
specialization (the bounce marginal), and the public polyomino instances with
their area and bounce values. area and bounce are both public here -- the task
is the bijection, not discovering a statistic -- so nothing is withheld.

Enumeration streams one polyomino at a time, so the peak memory is the size of
the distribution counters, not of the object set.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.combinatorics import (
    iter_parallelogram_polyominoes,
    polyomino_area,
    polyomino_bounce,
    polyomino_count,
)


def case_id(m: int, n: int) -> str:
    return f"m{m:02d}_n{n:02d}"


def _boxes(max_sum: int):
    for total in range(2, max_sum + 1):
        for m in range(1, total):
            yield m, total - m


def polynomial_case(m: int, n: int) -> dict:
    counter: Counter[tuple[int, int]] = Counter()
    count = 0
    for encoding in iter_parallelogram_polyominoes(m, n):
        counter[(polyomino_area(encoding), polyomino_bounce(encoding))] += 1
        count += 1
    if count != polyomino_count(m, n):
        raise RuntimeError(f"enumeration mismatch for m={m}, n={n}: {count} vs {polyomino_count(m, n)}")
    terms = [[area, bounce, counter[(area, bounce)]] for area, bounce in sorted(counter)]
    return {
        "case_id": case_id(m, n),
        "m": m,
        "n": n,
        "count": count,
        "term_count": len(terms),
        "terms": terms,
    }


def q_equals_1_case(case: dict) -> dict:
    marginal: Counter[int] = Counter()
    for _area, bounce, coefficient in case["terms"]:
        marginal[bounce] += coefficient
    terms = [[bounce, marginal[bounce]] for bounce in sorted(marginal)]
    return {
        "case_id": case["case_id"],
        "m": case["m"],
        "n": case["n"],
        "count": case["count"],
        "term_count": len(terms),
        "terms": terms,
    }


def instance_case(m: int, n: int) -> dict:
    entries = [
        {
            "polyomino": encoding,
            "area": polyomino_area(encoding),
            "bounce": polyomino_bounce(encoding),
        }
        for encoding in iter_parallelogram_polyominoes(m, n)
    ]
    return {"case_id": case_id(m, n), "m": m, "n": n, "count": len(entries), "entries": entries}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate polyomino area/bounce exchange data.")
    parser.add_argument("--problem-dir", type=Path, required=True)
    parser.add_argument(
        "--public-max-sum",
        type=int,
        default=14,
        help="largest bounding-box semiperimeter m+n for the public polynomials",
    )
    parser.add_argument(
        "--instances-max-sum",
        type=int,
        default=8,
        help="instances.json lists every polyomino, so it is capped smaller",
    )
    args = parser.parse_args()
    if args.public_max_sum < 2:
        parser.error("--public-max-sum must be at least 2")
    if not 2 <= args.instances_max_sum <= args.public_max_sum:
        parser.error(
            "--instances-max-sum must be at least 2 and no greater than "
            "--public-max-sum"
        )

    problem_dir = args.problem_dir.resolve()
    metadata = json.loads((problem_dir / "metadata.json").read_text(encoding="utf-8"))
    identity = {"problem_id": int(metadata["id"]), "problem_name": str(metadata["name"])}
    supported_targets = {
        (4, "polyomino_area_bounce_exchange"): "polyomino-area-bounce",
        (5, "polyomino_area_bounce_transpose"): "polyomino-transpose",
    }
    expected_evaluator = supported_targets.get(
        (identity["problem_id"], identity["problem_name"])
    )
    if expected_evaluator is None or metadata.get("evaluator_kind") != expected_evaluator:
        parser.error(
            "--problem-dir must identify the area/bounce exchange or transpose "
            "polyomino problem"
        )
    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    polynomial_cases = [polynomial_case(m, n) for m, n in _boxes(args.public_max_sum)]
    q1_cases = [q_equals_1_case(case) for case in polynomial_cases]
    instance_cases = [instance_case(m, n) for m, n in _boxes(args.instances_max_sum)]
    (data_dir / "polynomials.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                **identity,
                "variables": ["q", "t"],
                "statistics": {"q": "area", "t": "bounce"},
                "public_max_sum": args.public_max_sum,
                "case_count": len(polynomial_cases),
                "cases": polynomial_cases,
            },
            indent=2,
        ),
        encoding="utf-8", newline="\n",
    )

    q1_meaning = (
        "Bounce marginal; a necessary condition for the area/bounce-preserving transpose."
        if metadata["evaluator_kind"] == "polyomino-transpose"
        else "Bounce marginal; a necessary condition for the exchange."
    )
    (data_dir / "q_equals_1.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                **identity,
                "variables": ["t"],
                "specialization": {"q": 1},
                "meaning": q1_meaning,
                "public_max_sum": args.public_max_sum,
                "case_count": len(q1_cases),
                "cases": q1_cases,
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
                "object_family": "parallelogram_polyominoes",
                "statistics": ["area", "bounce"],
                "instances_max_sum": args.instances_max_sum,
                "case_count": len(instance_cases),
                "cases": instance_cases,
            },
            separators=(",", ":"),
        ),
        encoding="utf-8", newline="\n",
    )

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
