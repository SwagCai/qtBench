#!/usr/bin/env python3
"""Generate the DPP weight targets for alternating sign matrices."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Iterator

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.combinatorics import enumerate_alternating_sign_matrices

PROBLEM_ID = 27
PROBLEM_NAME = "asm_dpp_weight_q_stat"
EXPECTED_COUNTS = {1: 1, 2: 2, 3: 7, 4: 42, 5: 429, 6: 7436, 7: 218348}


def _multiply(left: list[int], right: list[int]) -> list[int]:
    product = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            product[i + j] += a * b
    return product


def _q_factorial(n: int) -> list[int]:
    result = [1]
    for factor in range(1, n + 1):
        result = _multiply(result, [1] * factor)
    return result


def _exact_divide(numerator: list[int], denominator: list[int]) -> list[int]:
    if denominator[0] != 1 or len(numerator) < len(denominator):
        raise ValueError("invalid exact polynomial division")
    remainder = numerator[:]
    quotient = [0] * (len(numerator) - len(denominator) + 1)
    for degree in range(len(quotient)):
        coefficient = remainder[degree]
        quotient[degree] = coefficient
        for offset, value in enumerate(denominator):
            remainder[degree + offset] -= coefficient * value
    if any(remainder):
        raise ValueError("q-factorial ratio is not a polynomial")
    while len(quotient) > 1 and quotient[-1] == 0:
        quotient.pop()
    return quotient


def dpp_product_distribution(n: int) -> Counter[int]:
    """Expand product [3k+1]_q!/[n+k]_q! from the cited DPP formula."""

    numerator = [1]
    denominator = [1]
    for k in range(n):
        numerator = _multiply(numerator, _q_factorial(3 * k + 1))
        denominator = _multiply(denominator, _q_factorial(n + k))
    quotient = _exact_divide(numerator, denominator)
    return Counter({degree: coefficient for degree, coefficient in enumerate(quotient) if coefficient})


def _weak_rows(
    length: int,
    maximum: int,
    upper_bounds: tuple[int, ...] | None = None,
) -> Iterator[tuple[int, ...]]:
    row: list[int] = []

    def extend() -> Iterator[tuple[int, ...]]:
        if len(row) == length:
            yield tuple(row)
            return
        top = row[-1] if row else maximum
        if upper_bounds is not None:
            top = min(top, upper_bounds[len(row)] - 1)
        for value in range(top, 0, -1):
            row.append(value)
            yield from extend()
            row.pop()

    yield from extend()


def enumerate_dpps(n: int) -> Iterator[tuple[tuple[int, ...], ...]]:
    """Enumerate descending plane partitions whose largest part is at most n."""

    yield ()
    rows: list[tuple[int, ...]] = []

    def extend() -> Iterator[tuple[tuple[int, ...], ...]]:
        previous = rows[-1] if rows else None
        maximum_length = n - 1 if previous is None else len(previous) - 1
        for length in range(1, maximum_length + 1):
            maximum = n if previous is None else len(previous)
            bounds = None if previous is None else previous[1:]
            for row in _weak_rows(length, maximum, bounds):
                if row[0] <= length:
                    continue
                rows.append(row)
                yield tuple(rows)
                yield from extend()
                rows.pop()

    yield from extend()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=7)
    parser.add_argument("--instances-max-n", type=int, default=4)
    args = parser.parse_args()
    if args.public_max_n not in EXPECTED_COUNTS:
        parser.error("--public-max-n must lie between 1 and 7")
    if not 1 <= args.instances_max_n <= args.public_max_n:
        parser.error("--instances-max-n must lie in the public range")
    problem_dir = args.problem_dir.resolve()
    metadata = json.loads((problem_dir / "metadata.json").read_text(encoding="utf-8"))
    if (metadata.get("id"), metadata.get("name")) != (PROBLEM_ID, PROBLEM_NAME):
        raise SystemExit(
            f"--problem-dir must identify problem {PROBLEM_ID} ({PROBLEM_NAME})"
        )

    cases = []
    for n in range(1, args.public_max_n + 1):
        distribution = Counter(sum(map(sum, dpp)) for dpp in enumerate_dpps(n))
        if distribution != dpp_product_distribution(n):
            raise SystemExit(f"n={n}: DPP enumeration disagrees with the product formula")
        asm_count = sum(1 for _ in enumerate_alternating_sign_matrices(n))
        dpp_count = sum(distribution.values())
        if dpp_count != asm_count or asm_count != EXPECTED_COUNTS[n]:
            raise SystemExit(
                f"n={n}: DPP count {dpp_count}, ASM count {asm_count}, "
                f"expected {EXPECTED_COUNTS[n]}"
            )
        cases.append(
            {
                "case_id": f"n{n:02d}",
                "n": n,
                "count": asm_count,
                "term_count": len(distribution),
                "terms": [[degree, distribution[degree]] for degree in sorted(distribution)],
            }
        )

    q1_cases = [
        {
            "case_id": case["case_id"],
            "n": case["n"],
            "count": case["count"],
            "term_count": 1,
            "terms": [[case["n"], case["count"]]],
        }
        for case in cases
    ]
    instance_cases = []
    for n in range(1, args.instances_max_n + 1):
        entries = [matrix.encoding for matrix in enumerate_alternating_sign_matrices(n)]
        instance_cases.append(
            {"case_id": f"n{n:02d}", "n": n, "count": len(entries), "entries": entries}
        )

    identity = {"problem_id": PROBLEM_ID, "problem_name": PROBLEM_NAME}
    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "polynomials.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                **identity,
                "variables": ["q"],
                "known_statistics": [],
                "source": "DPP sum-of-parts weight enumerator",
                "public_max_n": args.public_max_n,
                "case_count": len(cases),
                "cases": cases,
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
                "variables": ["n"],
                "specialization": {"q": 1},
                "meaning": "DPP(n,1) is the number of n by n alternating sign matrices.",
                "public_max_n": args.public_max_n,
                "case_count": len(cases),
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
                "object_family": "alternating_sign_matrices",
                "instances_max_n": args.instances_max_n,
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
