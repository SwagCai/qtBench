#!/usr/bin/env python3
"""Generate public data for the q-Kreweras statistic problem.

The targets are the type A q-Kreweras numbers of Reiner and Sommers at the classical
parameter ``m = n + 1``, computed by the public oracle
``problems/q_statistic_discovery/nc_q_kreweras_q_stat/kreweras_oracle.py``
from their closed formula. For each size the generator checks

  * every ``Krew_lambda(q)`` lies in ``N[q]``,
  * ``Krew_lambda(1)`` is the number of noncrossing partitions of block type
    ``lambda``, counted by enumerating ``NC(n)``, and equals Kreweras' closed form
    ``n! / ((n + 1 - l(lambda))! prod_j m_j(lambda)!)``, and
  * ``sum_lambda Krew_lambda(q)`` is the MacMahon q-Catalan number
    ``(1 / [n+1]_q) [2n ; n]_q``, so the refinement is exact.

The scored evaluator never loads the oracle.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from itertools import zip_longest
from math import factorial
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.combinatorics import enumerate_noncrossing_partitions, iter_partitions
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "kreweras_oracle.py")


def case_id(n: int) -> str:
    return f"n{n:02d}"


def kreweras_number(lam, n: int) -> int:
    """``n! / ((n + 1 - l(lambda))! prod_j m_j(lambda)!)``, Kreweras' closed form."""
    value = factorial(n) // factorial(n + 1 - len(lam))
    for multiplicity in Counter(lam).values():
        value //= factorial(multiplicity)
    return value


def _add_polynomials(left: list[int], right: list[int]) -> list[int]:
    return [
        left_value + right_value
        for left_value, right_value in zip_longest(left, right, fillvalue=0)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate q-Kreweras data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=11)
    parser.add_argument("--instances-max-n", type=int, default=9)
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
    oracle = _load_oracle(problem_dir)
    if oracle.PROBLEM_ID != identity["problem_id"] or oracle.PROBLEM_NAME != identity["problem_name"]:
        raise SystemExit("oracle PROBLEM_ID/PROBLEM_NAME do not match the problem metadata")

    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    poly_cases, q1_cases, instance_cases = [], [], []
    for n in range(1, args.public_max_n + 1):
        started = time.perf_counter()
        objects = enumerate_noncrossing_partitions(n)
        counts = Counter(obj.block_type for obj in objects)
        terms, marginal, total = [], [], []
        for lam in iter_partitions(n):
            coefficients = oracle.kreweras(lam, n)
            if any(value < 0 for value in coefficients) or not coefficients:
                raise SystemExit(f"n={n} lambda={lam}: not a nonzero element of N[q]")
            if sum(coefficients) != counts[lam]:
                raise SystemExit(
                    f"n={n} lambda={lam}: Krew(1) = {sum(coefficients)} but {counts[lam]} partitions"
                )
            if sum(coefficients) != kreweras_number(lam, n):
                raise SystemExit(f"n={n} lambda={lam}: disagrees with Kreweras' closed form")
            for degree, value in enumerate(coefficients):
                if value:
                    terms.append([list(lam), degree, value])
            marginal.append([list(lam), sum(coefficients)])
            total = _add_polynomials(total, coefficients)
        while total and total[-1] == 0:
            total.pop()
        if total != oracle.q_catalan(n):
            raise SystemExit(f"n={n}: the types do not sum to the q-Catalan number")
        header = {"case_id": case_id(n), "n": n, "count": len(objects)}
        poly_cases.append({**header, "term_count": len(terms), "terms": terms})
        q1_cases.append({**header, "term_count": len(marginal), "terms": marginal})
        if n <= args.instances_max_n:
            instance_cases.append({**header, "entries": [obj.to_jsonable() for obj in objects]})
        print(f"verified n={n}: |NC(n)|={len(objects)} types={len(marginal)} "
              f"({time.perf_counter() - started:.1f}s)", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "variables": ["partition", "q"], "known_statistics": [],
                    "source": "type A q-Kreweras numbers Krew_lambda(q) of Reiner-Sommers at m = n + 1",
                    "public_max_n": args.public_max_n, "case_count": len(poly_cases),
                    "cases": poly_cases}, indent=2), encoding="utf-8", newline="\n")
    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["partition"],
                    "specialization": {"q": 1},
                    "meaning": "Krew_lambda(1) is the Kreweras number: the block-type distribution of NC(n), an object-model check that any statistic satisfies.",
                    "public_max_n": args.public_max_n, "case_count": len(q1_cases),
                    "cases": q1_cases}, indent=2), encoding="utf-8", newline="\n")
    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "noncrossing_partitions", "known_statistics": [],
                    "instances_max_n": args.instances_max_n,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")
    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
