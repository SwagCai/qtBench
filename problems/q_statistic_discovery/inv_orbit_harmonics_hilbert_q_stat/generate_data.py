#!/usr/bin/env python3
"""Generate public data for the involution orbit-harmonics Hilbert series problem.

The target polynomials are the Hilbert series

    H_{n,a}(q) = Hilb(R(M_{n,a}); q),        M_{n,a} = { pi in S_n : pi^2 = id, fix(pi) = a },

of the graded rings produced by applying orbit harmonics to the involution matrix
loci, computed by the public oracle ``problems/q_statistic_discovery/
inv_orbit_harmonics_hilbert_q_stat/orbit_harmonics_oracle.py`` straight from the
definition (the degree filtration of the function space on the locus). For each
fiber the series is verified to be

  * positive with integer coefficients,
  * consistent with the object model: ``H_{n,a}(1) = |M_{n,a}|``, which is what the
    ungraded isomorphism ``R(M_{n,a}) = C[M_{n,a}]`` says, and the count the public
    enumerator produces,
  * ``H_{n,n}(q) = 1`` on the identity fiber and
    ``H_{n,n-2}(q) = 1 + (C(n,2) - 1) q`` on the transposition fiber, where
    ``x_{ij}`` restricted to the locus is the indicator of ``(i j)``,
  * of top degree ``(n - a) / 2``, except ``n / 2 - 1`` on the fixed-point-free
    fiber, and
  * on the fixed-point-free fiber, equal to the longest-decreasing-subsequence
    generating function ``sum_pi q^{(n - lds(pi))/2}`` of Liu--Ma--Rhoades--Zhu,
    evaluated over the enumerated fiber rather than from the oracle.

The fast oracle is validated on a locus this problem never uses: for the *full*
permutation matrix locus the same code must return Rhoades' answer
``sum_{w in S_n} q^{n - lis(w)}``. It also recomputes every fiber with
``n <= exact_max_n`` over ``Q`` with ``Fraction`` arithmetic, and every fiber twice
modulo two unrelated primes. After generation, ``certify_exact.py`` certifies the
entire public range over ``Q`` with Sage's proof-enabled sparse echelon algorithm;
the checked-in certificate is tied to ``polynomials.json`` by SHA-256. The scored
evaluator never loads either computation.

Run with a numpy that has a threaded BLAS; the elimination is all matmuls::

    OPENBLAS_NUM_THREADS=8 python generate_data.py --problem-dir <dir>
"""
from __future__ import annotations

import argparse
import json
from bisect import bisect_left
from collections import Counter
from math import comb
from itertools import permutations
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.combinatorics import (
    involution_count,
    iter_involutions_with_fixed_points,
)
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "orbit_harmonics_oracle.py")


def case_id(n: int, a: int) -> str:
    return f"n{n:02d}_a{a:02d}"


def _longest_increasing(word) -> int:
    piles: list[int] = []
    for value in word:
        position = bisect_left(piles, value)
        if position == len(piles):
            piles.append(value)
        else:
            piles[position] = value
    return len(piles)


def _fiber(n: int, a: int, keep_entries: bool) -> tuple[list[str], Counter, int]:
    """Stream the fiber: ([object encodings], lds distribution, count)."""
    entries: list[str] = []
    decreasing: Counter[int] = Counter()
    count = 0
    for obj in iter_involutions_with_fixed_points(n, a):
        if keep_entries:
            entries.append(obj.encoding)
        decreasing[obj.longest_decreasing()] += 1
        count += 1
    return entries, decreasing, count


def verify(n: int, a: int, series: list[int], decreasing: Counter, count: int) -> None:
    if any(coefficient < 0 for coefficient in series) or not series[0] == 1:
        raise SystemExit(f"n={n} a={a}: H is not positive with constant term 1: {series}")
    if count != involution_count(n, a):
        raise SystemExit(f"n={n} a={a}: the enumerator produced {count} objects")
    # H_{n,a}(1) = |M_{n,a}|: the ungraded isomorphism R(M_{n,a}) = C[M_{n,a}].
    if sum(series) != count:
        raise SystemExit(f"n={n} a={a}: H(1) = {sum(series)} but the fiber has {count}")
    top = len(series) - 1
    expected_top = (n - a) // 2 - (1 if a == 0 else 0)
    if top != max(expected_top, 0):
        raise SystemExit(f"n={n} a={a}: top degree {top}, expected {max(expected_top, 0)}")
    if a == n and series != [1]:
        raise SystemExit(f"n={n}: the identity fiber has H = {series}")
    if a == n - 2 and series != [1, comb(n, 2) - 1][: top + 1]:
        raise SystemExit(f"n={n}: the transposition fiber has H = {series}")
    if a == 0:
        # Liu--Ma--Rhoades--Zhu: H_{n,0} is the lds generating function of the fiber.
        expected: Counter[int] = Counter()
        for length, multiplicity in decreasing.items():
            if (n - length) % 2:
                raise SystemExit(f"n={n}: a fixed-point-free involution has odd n - lds")
            expected[(n - length) // 2] += multiplicity
        if [expected[degree] for degree in range(top + 1)] != series:
            raise SystemExit(f"n={n}: H_{{n,0}} is not the lds generating function")


def validate_oracle(oracle, *, permutation_max_n: int) -> None:
    """Rhoades: the *full* permutation matrix locus has ``sum_w q^{n - lis(w)}``."""
    for n in range(1, permutation_max_n + 1):
        generated = oracle.permutation_hilbert_series(n)
        expected: Counter[int] = Counter()
        for word in permutations(range(1, n + 1)):
            expected[n - _longest_increasing(word)] += 1
        if [expected[degree] for degree in range(max(expected) + 1)] != generated:
            raise SystemExit(f"the oracle fails Rhoades' permutation locus answer at n={n}")
        print(f"oracle validated on the permutation matrix locus n={n}: {generated}", flush=True)


def _validate_float64_preflight(oracle, *, public_max_n: int, permutation_max_n: int) -> None:
    """Reject requested loci outside the oracle's exact float64 matmul range."""
    limit = oracle.float64_modular_point_limit()
    for n in range(1, public_max_n + 1):
        for a in range(n % 2, n + 1, 2):
            count = involution_count(n, a)
            if count > limit:
                raise ValueError(
                    f"--public-max-n={public_max_n} includes M_{{{n},{a}}} with "
                    f"{count} points, above the float64 modular limit {limit}"
                )
    permutation_count = 1
    for n in range(2, permutation_max_n + 1):
        permutation_count *= n
        if permutation_count > limit:
            raise ValueError(
                f"--permutation-max-n={permutation_max_n} includes S_{n} with "
                f"{permutation_count} points, above the float64 modular limit {limit}"
            )


def polynomial_case(n: int, a: int, series: list[int], count: int) -> dict:
    terms = [[degree, series[degree]] for degree in range(len(series)) if series[degree]]
    return {"case_id": case_id(n, a), "n": n, "a": a, "count": count,
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(n: int, a: int, count: int) -> dict:
    return {"case_id": case_id(n, a), "n": n, "a": a, "count": count,
            "term_count": 1, "terms": [[a, count]]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate involution orbit-harmonics data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=10,
                        help="largest size n for the public Hilbert series")
    parser.add_argument("--instances-max-n", type=int, default=9,
                        help="instances.json lists every object, so it is capped smaller")
    parser.add_argument("--exact-max-n", type=int, default=7,
                        help="recompute every fiber of this size or less over Q")
    parser.add_argument("--permutation-max-n", type=int, default=6,
                        help="validate the oracle on the permutation locus up to this size")
    args = parser.parse_args()
    if args.public_max_n < 1:
        parser.error("--public-max-n must be positive")
    if not 1 <= args.instances_max_n <= args.public_max_n:
        parser.error(
            "--instances-max-n must be positive and no greater than --public-max-n"
        )
    if args.exact_max_n < 0:
        parser.error("--exact-max-n must be nonnegative")
    if args.permutation_max_n < 0:
        parser.error("--permutation-max-n must be nonnegative")

    problem_dir = args.problem_dir.resolve()
    metadata = json.loads((problem_dir / "metadata.json").read_text(encoding="utf-8"))
    identity = {"problem_id": int(metadata["id"]), "problem_name": str(metadata["name"])}
    oracle = _load_oracle(problem_dir)
    if oracle.PROBLEM_ID != identity["problem_id"] or oracle.PROBLEM_NAME != identity["problem_name"]:
        raise SystemExit("oracle PROBLEM_ID/PROBLEM_NAME do not match the problem metadata")

    try:
        _validate_float64_preflight(
            oracle,
            public_max_n=args.public_max_n,
            permutation_max_n=args.permutation_max_n,
        )
    except ValueError as error:
        parser.error(str(error))

    validate_oracle(oracle, permutation_max_n=args.permutation_max_n)

    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    poly_cases = []
    q1_cases = []
    instance_cases = []
    for n in range(1, args.public_max_n + 1):
        for a in range(n % 2, n + 1, 2):
            started = time.perf_counter()
            series = oracle.involution_hilbert_series(n, a)
            if n <= args.exact_max_n:
                exact = oracle.involution_hilbert_series(n, a, exact=True)
                if exact != series:
                    raise SystemExit(f"n={n} a={a}: modular {series} != exact {exact}")
            keep = n <= args.instances_max_n
            entries, decreasing, count = _fiber(n, a, keep)
            verify(n, a, series, decreasing, count)
            poly_cases.append(polynomial_case(n, a, series, count))
            q1_cases.append(q_equals_1_case(n, a, count))
            if keep:
                instance_cases.append({"case_id": case_id(n, a), "n": n, "a": a,
                                       "count": count, "entries": entries})
            print(f"verified n={n} a={a}: |M|={count} H={series} "
                  f"({time.perf_counter() - started:.1f}s)", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["q"],
                    "known_statistics": [],
                    "source": "Hilbert series of the orbit harmonics quotient R(M_{n,a})",
                    "public_max_n": args.public_max_n, "case_count": len(poly_cases),
                    "cases": poly_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["fixed_points"],
                    "specialization": {"q": 1},
                    "meaning": "H_{n,a}(1) = |M_{n,a}|, the ungraded isomorphism R(M_{n,a}) = C[M_{n,a}]: the fiber's fixed-point count and size, an object-model check that any statistic satisfies.",
                    "public_max_n": args.public_max_n, "case_count": len(q1_cases),
                    "cases": q1_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "involutions",
                    "known_statistics": [], "instances_max_n": args.instances_max_n,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")
    print("run certify_exact.py with Sage before publishing regenerated targets")


if __name__ == "__main__":
    main()
