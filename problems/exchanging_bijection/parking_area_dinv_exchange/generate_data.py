#!/usr/bin/env python3
"""Generate public parking-function area/dinv exchange data."""
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

from qtbench.combinatorics import iter_parking_functions


def case_id(n: int) -> str:
    return f"n{n:02d}"


def polynomial_case(n: int) -> dict:
    counter = Counter((obj.area(), obj.dinv()) for obj in iter_parking_functions(n))
    terms = [[area, dinv, counter[(area, dinv)]] for area, dinv in sorted(counter)]
    exchanged = Counter({(dinv, area): count for (area, dinv), count in counter.items()})
    if counter != exchanged:
        raise SystemExit(f"n={n}: area/dinv distribution is not symmetric")
    return {
        "case_id": case_id(n),
        "n": n,
        "count": sum(counter.values()),
        "term_count": len(terms),
        "terms": terms,
    }


def marginal_case(case: dict) -> dict:
    counter: Counter[int] = Counter()
    for _area, dinv, coefficient in case["terms"]:
        counter[dinv] += coefficient
    terms = [[dinv, counter[dinv]] for dinv in sorted(counter)]
    return {
        "case_id": case["case_id"],
        "n": case["n"],
        "count": case["count"],
        "term_count": len(terms),
        "terms": terms,
    }


def instance_case(n: int) -> dict:
    entries = [
        {"parking": obj.encoding, "area": obj.area(), "dinv": obj.dinv()}
        for obj in iter_parking_functions(n)
    ]
    return {"case_id": case_id(n), "n": n, "count": len(entries), "entries": entries}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=7)
    parser.add_argument("--instances-max-n", type=int, default=5)
    args = parser.parse_args()
    if args.public_max_n < 1:
        parser.error("--public-max-n must be positive")
    if not 1 <= args.instances_max_n <= args.public_max_n:
        parser.error(
            "--instances-max-n must be positive and no greater than --public-max-n"
        )
    problem_dir = args.problem_dir.resolve()
    metadata = json.loads((problem_dir / "metadata.json").read_text(encoding="utf-8"))
    identity = {"problem_id": metadata["id"], "problem_name": metadata["name"]}
    expected_identity = {
        "problem_id": 25,
        "problem_name": "parking_area_dinv_exchange",
    }
    if identity != expected_identity:
        raise SystemExit(
            f"--problem-dir identifies {identity}, expected {expected_identity}"
        )
    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    polynomial_cases = [polynomial_case(n) for n in range(1, args.public_max_n + 1)]
    marginal_cases = [marginal_case(case) for case in polynomial_cases]
    instance_cases = [instance_case(n) for n in range(1, args.instances_max_n + 1)]
    (data_dir / "polynomials.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                **identity,
                "variables": ["q", "t"],
                "statistics": {"q": "area", "t": "dinv"},
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
                "meaning": "Parking dinv marginal; necessary for the exchange.",
                "public_max_n": args.public_max_n,
                "case_count": len(marginal_cases),
                "cases": marginal_cases,
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
                "object_family": "parking_functions",
                "statistics": ["area", "dinv"],
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
