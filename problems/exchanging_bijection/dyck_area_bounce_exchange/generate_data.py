#!/usr/bin/env python3
"""Generate public data for the Dyck area/bounce exchanging-bijection problem.

Writes the q,t-Catalan (joint area/bounce distribution), its q=1 specialization
(the bounce marginal), and the public Dyck-path instances with their area and
bounce values. area and bounce are both public here -- the task is the bijection,
not discovering a statistic -- so nothing is withheld.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.combinatorics import dyck_area, dyck_bounce, enumerate_dyck_paths


def case_id(n: int) -> str:
    return f"n{n:02d}"


def polynomial_case(n: int) -> dict:
    counter: Counter[tuple[int, int]] = Counter(
        (dyck_area(path), dyck_bounce(path)) for path in enumerate_dyck_paths(n)
    )
    terms = [[area, bounce, counter[(area, bounce)]] for area, bounce in sorted(counter)]
    return {
        "case_id": case_id(n),
        "n": n,
        "count": len(enumerate_dyck_paths(n)),
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
        "n": case["n"],
        "count": case["count"],
        "term_count": len(terms),
        "terms": terms,
    }


def instance_case(n: int) -> dict:
    entries = [
        {"path": path, "area": dyck_area(path), "bounce": dyck_bounce(path)}
        for path in enumerate_dyck_paths(n)
    ]
    return {"case_id": case_id(n), "n": n, "count": len(entries), "entries": entries}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate area/bounce exchange data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=13)
    parser.add_argument(
        "--instances-max-n",
        type=int,
        default=8,
        help="instances.json lists every path, so it is capped smaller than the polynomials",
    )
    args = parser.parse_args()
    if args.public_max_n < 1:
        parser.error("--public-max-n must be positive")
    if not 1 <= args.instances_max_n <= args.public_max_n:
        parser.error(
            "--instances-max-n must be positive and no greater than --public-max-n"
        )

    problem_dir = args.problem_dir.resolve()
    metadata = json.loads((problem_dir / "metadata.json").read_text(encoding="utf-8"))
    identity = {"problem_id": int(metadata["id"]), "problem_name": str(metadata["name"])}
    expected_identity = {
        "problem_id": 2,
        "problem_name": "dyck_area_bounce_exchange",
    }
    if identity != expected_identity:
        raise SystemExit(
            f"--problem-dir identifies {identity}, expected {expected_identity}"
        )
    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    polynomial_cases = [polynomial_case(n) for n in range(1, args.public_max_n + 1)]
    q1_cases = [q_equals_1_case(case) for case in polynomial_cases]
    instance_cases = [instance_case(n) for n in range(1, args.instances_max_n + 1)]
    (data_dir / "polynomials.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                **identity,
                "variables": ["q", "t"],
                "statistics": {"q": "area", "t": "bounce"},
                "public_max_n": args.public_max_n,
                "case_count": len(polynomial_cases),
                "cases": polynomial_cases,
            },
            indent=2,
        ),
        encoding="utf-8", newline="\n",
    )

    (data_dir / "q_equals_1.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                **identity,
                "variables": ["t"],
                "specialization": {"q": 1},
                "meaning": "Bounce marginal; a necessary condition for the exchange.",
                "public_max_n": args.public_max_n,
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
                "object_family": "dyck_paths",
                "statistics": ["area", "bounce"],
                "instances_max_n": args.instances_max_n,
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
