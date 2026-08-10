#!/usr/bin/env python3
"""Generate public data for the doubly decorated Dyck path unified-Delta problem.

The target polynomials are the unified-Delta Hilbert series

    F_{n,k,l}(q, t) = < Theta_{e_k} Theta_{e_l} nabla e_{n-k-l} , e_{1^n} >

computed by the public oracle ``problems/t_statistic_discovery/
ddyck_area_qt_unified_delta_second_stat/theta_nabla_oracle.py``. Each F_{n,k,l}
is verified to be q,t-symmetric, to total ``|LD(n)^{*k, •l}|``, and to have its
q-marginal (``t = 1``) equal the ``area`` distribution over the standardly
labelled doubly decorated Dyck paths ``LD(n)^{*k, •l}`` -- the unified Delta
conjecture of arXiv:2312.03956 at the Hilbert-series level, and an independent
check that both the algebraic target and the combinatorial object model agree.
The scored evaluator never loads the oracle.

Enumeration streams one path at a time, so peak memory stays small.
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
    iter_decorated_labelled_dyck_paths,
)
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "theta_nabla_oracle.py")


def case_id(n: int, k: int, l: int) -> str:
    return f"n{n:02d}_k{k:02d}_l{l:02d}"


def _fibers(max_n: int):
    for n in range(1, max_n + 1):
        for k in range(0, n):
            for l in range(0, n - k):
                if n - k - l >= 1:
                    yield n, k, l


def _enumerate_fiber(n: int, k: int, l: int, keep_entries: bool):
    """Stream LD(n)^{*k, •l} once; return (area_counter, count, entries)."""
    area_counter: Counter[int] = Counter()
    entries = []
    count = 0
    for path in iter_decorated_labelled_dyck_paths(n, k, l):
        area = path.area()
        area_counter[area] += 1
        if keep_entries:
            entries.append({"object": path.encoding, "area": area})
        count += 1
    return area_counter, count, entries


def verify(n: int, k: int, l: int, poly: dict, area_counter: Counter, count: int) -> None:
    total = sum(poly.values())
    if total != count:
        raise SystemExit(f"({n},{k},{l}): F totals {total} but |LD| = {count}")
    if any(c < 0 for c in poly.values()):
        raise SystemExit(f"({n},{k},{l}): F has a negative coefficient")
    if poly != {(j, i): c for (i, j), c in poly.items()}:
        raise SystemExit(f"({n},{k},{l}): F is not q,t-symmetric")
    q_marginal: Counter[int] = Counter()
    for (i, _j), c in poly.items():
        q_marginal[i] += c
    if {a: c for a, c in q_marginal.items() if c} != {a: c for a, c in area_counter.items() if c}:
        raise SystemExit(f"({n},{k},{l}): F(t=1) does not match the area distribution of LD")


def polynomial_case(n: int, k: int, l: int, poly: dict, count: int) -> dict:
    terms = [[i, j, poly[(i, j)]] for (i, j) in sorted(poly)]
    return {"case_id": case_id(n, k, l), "n": n, "k": k, "l": l, "count": count,
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(n: int, k: int, l: int, poly: dict, count: int) -> dict:
    marginal: Counter[int] = Counter()
    for (_i, j), c in poly.items():
        marginal[j] += c
    terms = [[j, marginal[j]] for j in sorted(marginal) if marginal[j]]
    return {"case_id": case_id(n, k, l), "n": n, "k": k, "l": l, "count": count,
            "term_count": len(terms), "terms": terms}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate doubly decorated Dyck path q,t data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=6,
                        help="largest path size n for the public polynomials")
    parser.add_argument("--instances-max-n", type=int, default=5,
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

    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    poly_cases = []
    q1_cases = []
    instance_cases = []
    for n, k, l in _fibers(args.public_max_n):
        keep = n <= args.instances_max_n
        area_counter, count, entries = _enumerate_fiber(n, k, l, keep)
        # The true bidegree is the maximal area; pass it as the interpolation bound.
        poly = oracle.F_poly(n, k, l, max(area_counter) if area_counter else 0)
        verify(n, k, l, poly, area_counter, count)
        poly_cases.append(polynomial_case(n, k, l, poly, count))
        q1_cases.append(q_equals_1_case(n, k, l, poly, count))
        if keep:
            instance_cases.append({"case_id": case_id(n, k, l), "n": n, "k": k, "l": l,
                                   "count": count, "entries": entries})
        print(f"verified (n={n},k={k},l={l}): |LD|={count}, terms={len(poly)}", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["q", "t"],
                    "known_statistic": "area",
                    "source": "Hilbert series <Theta_{e_k} Theta_{e_l} nabla e_{n-k-l}, e_{1^n}> (arXiv:2312.03956)",
                    "public_max_n": args.public_max_n, "case_count": len(poly_cases),
                    "cases": poly_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["t"],
                    "specialization": {"q": 1},
                    "meaning": "Necessary one-variable distribution for the unknown t-statistic.",
                    "public_max_n": args.public_max_n, "case_count": len(q1_cases),
                    "cases": q1_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "decorated_labelled_dyck_paths",
                    "known_statistic": "area", "instances_max_n": args.instances_max_n,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
