#!/usr/bin/env python3
"""Generate public data for the trivariate diagonal harmonics Tamari problem.

The target polynomials are the trigraded Hilbert series of trivariate diagonal
harmonics

    H_n(q1, q2, q3) = sum_d dim(Harm_{n,d}) q1^{d1} q2^{d2} q3^{d3},

assembled by the public oracle ``problems/t_statistic_discovery/
tamari_park_trivariate_third_stat/trivariate_harmonics_oracle.py`` from the
graded Frobenius characteristics published in arXiv:1105.3738 for ``n <= 5``.
Each H_n is verified to be symmetric in ``q1, q2, q3``, to total
``2^n (n+1)^{n-2} = |{(f, alpha)}|``, to reduce at ``q3 = 0`` to the shuffle
theorem enumerator ``sum_f q1^{area(beta(f))} q2^{dinv(f)}``, and to reduce at
``q3 = 1`` to ``sum_{(f,alpha)} q1^{d(alpha,beta(f))} q2^{dinv(f)}``. These are
the specializations surrounding Equation (49), which ties the proposed missing
statistic to the object model and to both public statistics. The scored
evaluator never loads the oracle.

Enumeration streams one pair at a time, so peak memory stays small.
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

from qtbench.combinatorics import iter_tamari_parking_pairs
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "trivariate_harmonics_oracle.py")


def case_id(n: int) -> str:
    return f"n{n:02d}"


def _enumerate_fiber(n: int, keep_entries: bool):
    """Stream the pairs of size ``n`` once; return (joint, shuffle, count, entries)."""
    joint: Counter[tuple[int, int]] = Counter()
    shuffle: Counter[tuple[int, int]] = Counter()
    entries = []
    previous_parking: tuple[int, ...] | None = None
    count = 0
    for pair in iter_tamari_parking_pairs(n):
        chain = pair.chain()
        dinv = pair.dinv()
        joint[(chain, dinv)] += 1
        # The iterator exhausts all alpha for one parking function before
        # advancing to the next, so no global seen-set is needed.
        if pair.parking_function != previous_parking:
            shuffle[(pair.area(), dinv)] += 1
            previous_parking = pair.parking_function
        if keep_entries:
            entries.append({"object": pair.encoding, "chain": chain, "dinv": dinv})
        count += 1
    return joint, shuffle, count, entries


def verify(n: int, poly: dict, oracle, joint: Counter, shuffle: Counter, count: int) -> None:
    total = sum(poly.values())
    if total != count:
        raise SystemExit(f"n={n}: H totals {total} but the object count is {count}")
    expected = 1 if n == 1 else 2 ** n * (n + 1) ** (n - 2)
    if count != expected:
        raise SystemExit(f"n={n}: object count {count} is not 2^n (n+1)^(n-2) = {expected}")
    if any(c < 0 for c in poly.values()):
        raise SystemExit(f"n={n}: H has a negative coefficient")
    if not oracle.is_symmetric(poly):
        raise SystemExit(f"n={n}: H is not symmetric in q1, q2, q3")
    if oracle.bivariate_slice(poly, 0) != {key: value for key, value in shuffle.items() if value}:
        raise SystemExit(f"n={n}: H(q3=0) does not match the shuffle theorem enumerator")
    if oracle.bivariate_slice(poly, 1) != {key: value for key, value in joint.items() if value}:
        raise SystemExit(f"n={n}: H(q3=1) does not match the (chain, dinv) enumerator")


def polynomial_case(n: int, poly: dict, count: int) -> dict:
    terms = [[d1, d2, d3, poly[(d1, d2, d3)]] for (d1, d2, d3) in sorted(poly)]
    return {"case_id": case_id(n), "n": n, "count": count,
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(n: int, poly: dict, count: int) -> dict:
    marginal: Counter[int] = Counter()
    for (_d1, _d2, d3), value in poly.items():
        marginal[d3] += value
    terms = [[d3, marginal[d3]] for d3 in sorted(marginal) if marginal[d3]]
    return {"case_id": case_id(n), "n": n, "count": count,
            "term_count": len(terms), "terms": terms}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate trivariate Tamari data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=5,
                        help="largest n; the published Frobenius table stops at 5")
    parser.add_argument("--instances-max-n", type=int, default=4,
                        help="instances.json lists every object, so it is capped smaller")
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
    if args.public_max_n > oracle.PUBLIC_MAX_N:
        raise SystemExit(f"no published data beyond n = {oracle.PUBLIC_MAX_N}")

    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    poly_cases = []
    q1_cases = []
    instance_cases = []
    for n in range(1, args.public_max_n + 1):
        keep = n <= args.instances_max_n
        joint, shuffle, count, entries = _enumerate_fiber(n, keep)
        poly = oracle.H_poly(n)
        verify(n, poly, oracle, joint, shuffle, count)
        poly_cases.append(polynomial_case(n, poly, count))
        q1_cases.append(q_equals_1_case(n, poly, count))
        if keep:
            instance_cases.append({"case_id": case_id(n), "n": n, "count": count,
                                   "entries": entries})
        print(f"verified n={n}: pairs={count}, terms={len(poly)}", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["q1", "q2", "q3"],
                    "known_statistics": ["chain", "dinv"],
                    "source": "trigraded Hilbert series of trivariate diagonal harmonics and the missing-statistic formula (49) of arXiv:1105.3738",
                    "public_max_n": args.public_max_n, "case_count": len(poly_cases),
                    "cases": poly_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["q3"],
                    "specialization": {"q1": 1, "q2": 1},
                    "meaning": "Necessary one-variable distribution for the unknown third statistic.",
                    "public_max_n": args.public_max_n, "case_count": len(q1_cases),
                    "cases": q1_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "tamari_parking_pairs",
                    "known_statistics": ["chain", "dinv"],
                    "instances_max_n": args.instances_max_n,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
