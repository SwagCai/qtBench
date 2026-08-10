#!/usr/bin/env python3
"""Generate public standard-filling Macdonald q,t-symmetry data."""
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

from qtbench.combinatorics import iter_partitions, iter_standard_macdonald_fillings


def case_id(shape) -> str:
    return "mu_" + "_".join(str(part) for part in shape)


def is_hook(shape) -> bool:
    return len(shape) == 1 or all(part == 1 for part in shape[1:])


def polynomial_case(shape) -> dict:
    counter = Counter(
        (filling.inv(), filling.maj())
        for filling in iter_standard_macdonald_fillings(shape)
    )
    terms = [[inv, maj, counter[(inv, maj)]] for inv, maj in sorted(counter)]
    return {
        "case_id": case_id(shape),
        "n": sum(shape),
        "shape": list(shape),
        "count": sum(counter.values()),
        "term_count": len(terms),
        "terms": terms,
    }


def marginal_case(case: dict) -> dict:
    counter: Counter[int] = Counter()
    for _inv, maj, coefficient in case["terms"]:
        counter[maj] += coefficient
    terms = [[maj, counter[maj]] for maj in sorted(counter)]
    return {
        "case_id": case["case_id"],
        "n": case["n"],
        "shape": case["shape"],
        "count": case["count"],
        "term_count": len(terms),
        "terms": terms,
    }


def instance_case(shape) -> dict:
    entries = [
        {"filling": filling.encoding, "inv": filling.inv(), "maj": filling.maj()}
        for filling in iter_standard_macdonald_fillings(shape)
    ]
    return {
        "case_id": case_id(shape),
        "n": sum(shape),
        "shape": list(shape),
        "count": len(entries),
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=8)
    parser.add_argument("--instances-max-n", type=int, default=5)
    args = parser.parse_args()
    if args.public_max_n < 4:
        parser.error("--public-max-n must be at least 4")
    if not 4 <= args.instances_max_n <= args.public_max_n:
        parser.error(
            "--instances-max-n must be at least 4 and no greater than --public-max-n"
        )

    problem_dir = args.problem_dir.resolve()
    metadata = json.loads((problem_dir / "metadata.json").read_text(encoding="utf-8"))
    identity = {"problem_id": metadata["id"], "problem_name": metadata["name"]}
    expected_identity = {
        "problem_id": 24,
        "problem_name": "macdonald_fillings_inv_maj_exchange",
    }
    if identity != expected_identity:
        raise SystemExit(
            f"--problem-dir identifies {identity}, expected {expected_identity}"
        )
    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    polynomial_cases = [
        polynomial_case(shape)
        for n in range(4, args.public_max_n + 1)
        for shape in iter_partitions(n)
        if not is_hook(shape)
    ]
    by_shape = {tuple(case["shape"]): case for case in polynomial_cases}
    for shape, case in by_shape.items():
        conjugate = tuple(sum(part > column for part in shape) for column in range(shape[0]))
        exchanged = sorted([maj, inv, coefficient] for inv, maj, coefficient in case["terms"])
        if exchanged != by_shape[conjugate]["terms"]:
            raise SystemExit(
                f"shape={shape}, conjugate={conjugate}: inv/maj distributions do not exchange"
            )
    marginal_cases = [marginal_case(case) for case in polynomial_cases]
    instance_cases = [
        instance_case(shape)
        for n in range(4, args.instances_max_n + 1)
        for shape in iter_partitions(n)
        if not is_hook(shape)
    ]
    (data_dir / "polynomials.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                **identity,
                "variables": ["q", "t"],
                "statistics": {"q": "inv", "t": "maj"},
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
                "meaning": "HHL maj marginal; necessary for the inv/maj exchange.",
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
                "object_family": "standard_macdonald_fillings",
                "statistics": ["inv", "maj"],
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
