#!/usr/bin/env python3
"""Generate public data for the labelled parallelogram polyomino problem.

The target polynomials are the Theta-operator Hilbert series

    F_{m,n}(q, t) = < Theta_{e_{m-1}} Theta_{e_{n-1}} e_1 , e_{1^{m+n-1}} >

computed by the public oracle
``problems/t_statistic_discovery/lpp_area_qt_theta_second_stat/theta_oracle.py``.
Each F_{m,n} is verified to be q,t-symmetric, to total ``|stLPP(m,n)|``, and to
have its q-marginal (``t = 1``) equal to the labelled ``area`` distribution over
``stLPP(m,n)`` -- this is Theorem (polyominoes) of arXiv:2202.05706 and is an
independent check that both the algebraic target and the combinatorial object
model are correct. The scored evaluator never loads the oracle.

Enumeration streams one polyomino at a time, so peak memory stays small.
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

from qtbench.combinatorics import (
    iter_st_labelled_polyominoes,
)
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "theta_oracle.py")


def case_id(m: int, n: int) -> str:
    return f"m{m:02d}_n{n:02d}"


def _boxes(max_sum: int):
    for total in range(2, max_sum + 1):
        for m in range(1, total):
            yield m, total - m


def _enumerate_box(m: int, n: int, keep_entries: bool):
    """Stream stLPP(m,n) once; return (area_counter, count, entries)."""
    area_counter: Counter[int] = Counter()
    entries = []
    count = 0
    for polyomino in iter_st_labelled_polyominoes(m, n):
        area = polyomino.area()
        area_counter[area] += 1
        if keep_entries:
            entries.append({"polyomino": polyomino.encoding, "area": area})
        count += 1
    return area_counter, count, entries


def verify(m: int, n: int, poly: dict, area_counter: Counter, count: int) -> None:
    total = sum(poly.values())
    if total != count:
        raise SystemExit(f"({m},{n}): F totals {total} but |stLPP| = {count}")
    if any(c < 0 for c in poly.values()):
        raise SystemExit(f"({m},{n}): F has a negative coefficient")
    if poly != {(j, i): c for (i, j), c in poly.items()}:
        raise SystemExit(f"({m},{n}): F is not q,t-symmetric")
    q_marginal: Counter[int] = Counter()
    for (i, _j), c in poly.items():
        q_marginal[i] += c
    if {a: c for a, c in q_marginal.items() if c} != {a: c for a, c in area_counter.items() if c}:
        raise SystemExit(f"({m},{n}): F(t=1) does not match the area distribution of stLPP")


def polynomial_case(m: int, n: int, poly: dict, count: int) -> dict:
    terms = [[i, j, poly[(i, j)]] for (i, j) in sorted(poly)]
    return {"case_id": case_id(m, n), "m": m, "n": n, "count": count,
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(m: int, n: int, poly: dict, count: int) -> dict:
    marginal: Counter[int] = Counter()
    for (_i, j), c in poly.items():
        marginal[j] += c
    terms = [[j, marginal[j]] for j in sorted(marginal) if marginal[j]]
    return {"case_id": case_id(m, n), "m": m, "n": n, "count": count,
            "term_count": len(terms), "terms": terms}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate labelled polyomino q,t data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-sum", type=int, default=8,
                        help="largest bounding-box semiperimeter m+n for the public polynomials")
    parser.add_argument("--instances-max-sum", type=int, default=7,
                        help="instances.json lists every object, so it is capped smaller")
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
    expected_identity = {
        "problem_id": 6,
        "problem_name": "lpp_area_qt_theta_second_stat",
    }
    if identity != expected_identity:
        raise SystemExit(
            f"--problem-dir identifies {identity}, expected {expected_identity}"
        )
    oracle = _load_oracle(problem_dir)
    if oracle.PROBLEM_ID != identity["problem_id"] or oracle.PROBLEM_NAME != identity["problem_name"]:
        raise SystemExit("oracle PROBLEM_ID/PROBLEM_NAME do not match the problem metadata")

    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # F_{m,n} = F_{n,m}; compute once per unordered box and reuse.
    poly_cache: dict[tuple[int, int], dict] = {}
    poly_cases = []
    q1_cases = []
    instance_cases = []
    for m, n in _boxes(args.public_max_sum):
        key = (min(m, n), max(m, n))
        if key not in poly_cache:
            poly_cache[key] = oracle.F_poly(key[0], key[1])
        poly = poly_cache[key]
        keep = m + n <= args.instances_max_sum
        area_counter, count, entries = _enumerate_box(m, n, keep)
        verify(m, n, poly, area_counter, count)
        poly_cases.append(polynomial_case(m, n, poly, count))
        q1_cases.append(q_equals_1_case(m, n, poly, count))
        if keep:
            instance_cases.append({"case_id": case_id(m, n), "m": m, "n": n,
                                   "count": count, "entries": entries})
        print(f"verified ({m},{n}): |stLPP|={count}, terms={len(poly)}", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["q", "t"],
                    "known_statistic": "area",
                    "source": "Hilbert series <Theta_{e_{m-1}} Theta_{e_{n-1}} e_1, e_{1^{m+n-1}}> (arXiv:2202.05706)",
                    "public_max_sum": args.public_max_sum, "case_count": len(poly_cases),
                    "cases": poly_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["t"],
                    "specialization": {"q": 1},
                    "meaning": "Necessary one-variable distribution for the unknown t-statistic.",
                    "public_max_sum": args.public_max_sum, "case_count": len(q1_cases),
                    "cases": q1_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "labelled_parallelogram_polyominoes",
                    "known_statistic": "area", "instances_max_sum": args.instances_max_sum,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
