#!/usr/bin/env python3
"""Generate public data for the multi-labelled Dyck path super-nabla problem.

The target polynomials are the super-nabla Hilbert series

    H_{n,k}(q, t) = < nabla_*^k e_n , e_{1^n} tensor ... tensor e_{1^n} >

computed by the public oracle ``problems/t_statistic_discovery/
mld_area_qt_super_nabla_second_stat/super_nabla_oracle.py``. Each H_{n,k} is
verified to be q,t-symmetric, to total the number of standard multi-labelled
``k^n`` Dyck paths, and to have its q-marginal (``t = 1``) equal their ``area``
distribution -- the theorem of arXiv:2303.00560 at the Hilbert-series level, and
an independent check that both the algebraic target and the combinatorial object
model agree. The scored evaluator never loads the oracle.

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

from qtbench.combinatorics import iter_multi_labelled_dyck_paths
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "super_nabla_oracle.py")


def case_id(n: int, k: int) -> str:
    return f"k{k:02d}_n{n:02d}"


def _fibers(max_k: int):
    """Public fibers: ``1 <= k <= max_k`` and ``1 <= n <= max(3, 6 - k)``.

    The object count grows very fast in both parameters, so the size cap shrinks
    as the number of label rows grows.
    """
    for k in range(1, max_k + 1):
        for n in range(1, max(3, 6 - k) + 1):
            yield n, k


def _enumerate_fiber(n: int, k: int, max_entries: int):
    """Stream the standard elements of LD_{k^n} once; return (area_counter, count, entries)."""
    area_counter: Counter[int] = Counter()
    entries: list[dict] | None = []
    count = 0
    for path in iter_multi_labelled_dyck_paths(n, k):
        area = path.area()
        area_counter[area] += 1
        count += 1
        if entries is not None and count <= max_entries:
            entries.append({"object": path.encoding, "area": area})
        elif entries is not None:
            # This fiber will not be published in instances.json.  Release its
            # partial sample for the remainder of a potentially large scan.
            entries = None
    return area_counter, count, entries or []


def verify(n: int, k: int, poly: dict, area_counter: Counter, count: int) -> None:
    total = sum(poly.values())
    if total != count:
        raise SystemExit(f"(n={n},k={k}): H totals {total} but |LD| = {count}")
    if any(c < 0 for c in poly.values()):
        raise SystemExit(f"(n={n},k={k}): H has a negative coefficient")
    if poly != {(j, i): c for (i, j), c in poly.items()}:
        raise SystemExit(f"(n={n},k={k}): H is not q,t-symmetric")
    q_marginal: Counter[int] = Counter()
    for (i, _j), c in poly.items():
        q_marginal[i] += c
    if {a: c for a, c in q_marginal.items() if c} != {a: c for a, c in area_counter.items() if c}:
        raise SystemExit(f"(n={n},k={k}): H(t=1) does not match the area distribution of LD")


def polynomial_case(n: int, k: int, poly: dict, count: int) -> dict:
    terms = [[i, j, poly[(i, j)]] for (i, j) in sorted(poly)]
    return {"case_id": case_id(n, k), "n": n, "k": k, "count": count,
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(n: int, k: int, poly: dict, count: int) -> dict:
    marginal: Counter[int] = Counter()
    for (_i, j), c in poly.items():
        marginal[j] += c
    terms = [[j, marginal[j]] for j in sorted(marginal) if marginal[j]]
    return {"case_id": case_id(n, k), "n": n, "k": k, "count": count,
            "term_count": len(terms), "terms": terms}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate multi-labelled Dyck path q,t data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-k", type=int, default=4,
                        help="largest number of extra label rows k")
    parser.add_argument("--instances-max-count", type=int, default=10_000,
                        help="instances.json lists every object, so large fibers are skipped")
    args = parser.parse_args()
    if args.public_max_k < 1:
        parser.error("--public-max-k must be positive")
    if args.instances_max_count < 1:
        parser.error("--instances-max-count must be positive")

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
    for n, k in _fibers(args.public_max_k):
        area_counter, count, entries = _enumerate_fiber(
            n, k, args.instances_max_count
        )
        # The true bidegree is the maximal area; pass it as the interpolation bound.
        poly = oracle.H_poly(n, k, max(area_counter) if area_counter else 0)
        verify(n, k, poly, area_counter, count)
        poly_cases.append(polynomial_case(n, k, poly, count))
        q1_cases.append(q_equals_1_case(n, k, poly, count))
        if count <= args.instances_max_count:
            instance_cases.append({"case_id": case_id(n, k), "n": n, "k": k,
                                   "count": count, "entries": entries})
        print(f"verified (n={n},k={k}): |LD|={count}, terms={len(poly)}", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["q", "t"],
                    "known_statistic": "area",
                    "source": "Hilbert series <nabla_*^k e_n, e_{1^n}^{(x)(k+1)}> (arXiv:2303.00560)",
                    "public_max_k": args.public_max_k, "case_count": len(poly_cases),
                    "cases": poly_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["t"],
                    "specialization": {"q": 1},
                    "meaning": "Necessary one-variable distribution for the unknown t-statistic.",
                    "public_max_k": args.public_max_k, "case_count": len(q1_cases),
                    "cases": q1_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "multi_labelled_dyck_paths",
                    "known_statistic": "area",
                    "instances_max_count": args.instances_max_count,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
