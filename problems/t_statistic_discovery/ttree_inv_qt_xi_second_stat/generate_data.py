#!/usr/bin/env python3
"""Generate public data for the zero-rooted tiered-tree Xi problem.

The target polynomials are the Hilbert series

    F_mu(q, t) = < Xi e_mu , e_{1^{|mu|}} >

computed by the public oracle ``problems/t_statistic_discovery/
ttree_inv_qt_xi_second_stat/xi_oracle.py``. Each target is verified to total
``|RTT_0(mu)|`` and to have its q-marginal (``t = 1``) equal the ``inv``
distribution over standard zero-rooted tiered trees. The scored evaluator never
loads the oracle.

Enumeration streams one tree at a time, so peak memory stays small.
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

from qtbench.combinatorics import iter_zero_rooted_tiered_trees
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "xi_oracle.py")


def case_id(mu: tuple[int, ...]) -> str:
    return f"n{sum(mu):02d}_mu{'-'.join(str(part) for part in mu)}"


def _partitions(n: int, maxpart: int | None = None):
    if maxpart is None:
        maxpart = n
    if n == 0:
        yield ()
        return
    for part in range(min(n, maxpart), 0, -1):
        for rest in _partitions(n - part, part):
            yield (part, *rest)


def _fibers(max_n: int):
    for n in range(1, max_n + 1):
        yield from _partitions(n)


def _enumerate_fiber(mu: tuple[int, ...], keep_entries: bool):
    """Stream standard ``RTT_0(mu)`` once."""
    inv_counter: Counter[int] = Counter()
    entries = []
    count = 0
    for tree in iter_zero_rooted_tiered_trees(mu):
        inv = tree.inv()
        inv_counter[inv] += 1
        if keep_entries:
            entries.append({"object": tree.encoding, "inv": inv})
        count += 1
    return inv_counter, count, entries


def verify(mu: tuple[int, ...], poly: dict, inv_counter: Counter, count: int) -> None:
    total = sum(poly.values())
    if total != count:
        raise SystemExit(f"{mu}: F totals {total} but |RTT_0| = {count}")
    if any(c < 0 for c in poly.values()):
        raise SystemExit(f"{mu}: F has a negative coefficient")
    if poly != {(j, i): c for (i, j), c in poly.items()}:
        raise SystemExit(f"{mu}: F is not q,t-symmetric")
    q_marginal: Counter[int] = Counter()
    for (i, _j), c in poly.items():
        q_marginal[i] += c
    if {a: c for a, c in q_marginal.items() if c} != {a: c for a, c in inv_counter.items() if c}:
        raise SystemExit(f"{mu}: F(t=1) does not match the inv distribution of RTT_0")


def polynomial_case(mu: tuple[int, ...], poly: dict, count: int) -> dict:
    terms = [[i, j, poly[(i, j)]] for (i, j) in sorted(poly)]
    return {"case_id": case_id(mu), "n": sum(mu), "mu": list(mu), "count": count,
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(mu: tuple[int, ...], poly: dict, count: int) -> dict:
    marginal: Counter[int] = Counter()
    for (_i, j), c in poly.items():
        marginal[j] += c
    terms = [[j, marginal[j]] for j in sorted(marginal) if marginal[j]]
    return {"case_id": case_id(mu), "n": sum(mu), "mu": list(mu), "count": count,
            "term_count": len(terms), "terms": terms}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate tiered tree q,t data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=5,
                        help="largest |mu| for the public polynomials")
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

    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    poly_cases = []
    q1_cases = []
    instance_cases = []
    for mu in _fibers(args.public_max_n):
        keep = sum(mu) <= args.instances_max_n
        inv_counter, count, entries = _enumerate_fiber(mu, keep)
        # The true bidegree is the maximal inv; pass it as the interpolation bound.
        poly = oracle.F_poly(mu, max(inv_counter) if inv_counter else 0)
        verify(mu, poly, inv_counter, count)
        poly_cases.append(polynomial_case(mu, poly, count))
        q1_cases.append(q_equals_1_case(mu, poly, count))
        if keep:
            instance_cases.append({"case_id": case_id(mu), "n": sum(mu), "mu": list(mu),
                                   "count": count, "entries": entries})
        print(f"verified mu={mu}: |RTT_0|={count}, terms={len(poly)}", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["q", "t"],
                    "known_statistic": "inv",
                    "source": "Hilbert series <Xi e_mu, e_{1^{|mu|}}> (arXiv:2202.05706)",
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
                    "object_family": "zero_rooted_tiered_trees",
                    "known_statistic": "inv", "instances_max_n": args.instances_max_n,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
