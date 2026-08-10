#!/usr/bin/env python3
"""Generate public data for the rise-decorated rectangular path problem.

The target polynomials are the rectangular Delta Hilbert series

    G_{m,n,k}(q, t)
      = < ([m+k]_q/[gcd(m,n)]_q) Theta_{e_k} p_{m,n}, h_{1^{n+k}} >

computed by the public oracle ``problems/t_statistic_discovery/
lrp_area_qt_rectangular_delta_second_stat/rectangular_theta_oracle.py``. The
source paper reads ``area`` off the exponent of ``t``; qtBench publishes the known
statistic as the exponent of ``q``, so the oracle returns the transposed
polynomial. Each target is verified to be nonnegative, to total
``|LRP(m+k, n+k)^{*k}|``, and to have its ``area``-marginal equal the ``area``
distribution over those paths -- Conjecture 4.5 of arXiv:2206.00131 at the
Hilbert-series level, and an independent check that both the algebraic target and
the combinatorial object model agree. The scored evaluator never loads the oracle.

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

from qtbench.combinatorics import iter_labelled_rectangular_paths
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "rectangular_theta_oracle.py")


def case_id(m: int, n: int, k: int) -> str:
    return f"m{m:02d}_n{n:02d}_k{k:02d}"


def _fibers(max_semiperimeter: int):
    """Public fibers: all ``m, n, k >= 1`` with ``m + n + 2k <= max``.

    ``k >= 1`` isolates the decorated problem.  At ``k = 0`` the Dyck-path
    companion is known for all ``m, n``; the arbitrary-path identity is known
    in the coprime case and conjectural in general.
    """
    for total in range(4, max_semiperimeter + 1):
        for k in range(1, (total - 1) // 2 + 1):
            for m in range(1, total - 2 * k):
                n = total - 2 * k - m
                if n >= 1:
                    yield m, n, k


def _enumerate_fiber(m: int, n: int, k: int, max_entries: int):
    """Stream LRP(m+k, n+k)^{*k} once; return (area_counter, count, entries)."""
    area_counter: Counter[int] = Counter()
    entries: list[dict] | None = []
    count = 0
    for path in iter_labelled_rectangular_paths(m, n, k):
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


def verify(m: int, n: int, k: int, poly: dict, area_counter: Counter, count: int) -> None:
    total = sum(poly.values())
    if total != count:
        raise SystemExit(f"({m},{n},{k}): G totals {total} but |LRP| = {count}")
    if any(c < 0 for c in poly.values()):
        raise SystemExit(f"({m},{n},{k}): G has a negative coefficient")
    marginal: Counter[int] = Counter()
    for (area, _partner), c in poly.items():
        marginal[area] += c
    if {a: c for a, c in marginal.items() if c} != {a: c for a, c in area_counter.items() if c}:
        raise SystemExit(f"({m},{n},{k}): G(t=1) does not match the area distribution of LRP")


def polynomial_case(m: int, n: int, k: int, poly: dict, count: int) -> dict:
    terms = [[i, j, poly[(i, j)]] for (i, j) in sorted(poly)]
    return {"case_id": case_id(m, n, k), "m": m, "n": n, "k": k, "count": count,
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(m: int, n: int, k: int, poly: dict, count: int) -> dict:
    marginal: Counter[int] = Counter()
    for (_area, partner), c in poly.items():
        marginal[partner] += c
    terms = [[j, marginal[j]] for j in sorted(marginal) if marginal[j]]
    return {"case_id": case_id(m, n, k), "m": m, "n": n, "k": k, "count": count,
            "term_count": len(terms), "terms": terms}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate rise-decorated rectangular path q,t data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-semiperimeter", type=int, default=10,
                        help="largest (m+k) + (n+k) for the public polynomials")
    parser.add_argument("--instances-max-count", type=int, default=3_000,
                        help="instances.json lists every object, so large fibers are skipped")
    args = parser.parse_args()
    if args.public_max_semiperimeter < 4:
        parser.error("--public-max-semiperimeter must be at least 4")
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
    for m, n, k in _fibers(args.public_max_semiperimeter):
        area_counter, count, entries = _enumerate_fiber(
            m, n, k, args.instances_max_count
        )
        poly = oracle.G_poly(m, n, k, max(4, (m + k) * (n + k) // 2 + m + k))
        verify(m, n, k, poly, area_counter, count)
        poly_cases.append(polynomial_case(m, n, k, poly, count))
        q1_cases.append(q_equals_1_case(m, n, k, poly, count))
        if count <= args.instances_max_count:
            instance_cases.append({"case_id": case_id(m, n, k), "m": m, "n": n, "k": k,
                                   "count": count, "entries": entries})
        print(f"verified (m={m},n={n},k={k}): |LRP|={count}, terms={len(poly)}", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["q", "t"],
                    "known_statistic": "area",
                    "source": "Hilbert series <([m+k]_q/[gcd(m,n)]_q) Theta_{e_k} p_{m,n}, h_{1^{n+k}}> (arXiv:2206.00131), transposed",
                    "public_max_semiperimeter": args.public_max_semiperimeter,
                    "case_count": len(poly_cases), "cases": poly_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["t"],
                    "specialization": {"q": 1},
                    "meaning": "Necessary one-variable distribution for the unknown t-statistic.",
                    "public_max_semiperimeter": args.public_max_semiperimeter,
                    "case_count": len(q1_cases), "cases": q1_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "labelled_rectangular_paths",
                    "known_statistic": "area",
                    "instances_max_count": args.instances_max_count,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
