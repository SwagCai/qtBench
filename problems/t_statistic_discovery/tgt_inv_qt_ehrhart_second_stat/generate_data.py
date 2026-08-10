#!/usr/bin/env python3
"""Generate public data for the threshold-graph spanning tree Ehrhart problem.

The target polynomials are the weighted Ehrhart functions

    E_G(q, t) = Ehr_{q,t}(F_G(-n, 1, ..., 1))

computed by the public oracle ``problems/t_statistic_discovery/
tgt_inv_qt_ehrhart_second_stat/ehrhart_oracle.py``. Each target is verified to
be q,t-symmetric, to total the number of spanning trees of ``G``, and to have
its q-marginal (``t = 1``) equal the ``inv`` distribution over those spanning
trees, which is Theorem 3.8 of arXiv:1610.08370. Positivity is also asserted:
that is Conjecture 6.1 there, open in general and the reason this problem is
posed. The scored evaluator never loads the oracle.

Flows and spanning trees are both streamed, so peak memory stays small.
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

from qtbench.combinatorics import iter_threshold_graphs, iter_threshold_spanning_trees
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "ehrhart_oracle.py")


def case_id(up_degrees: tuple[int, ...]) -> str:
    return f"n{len(up_degrees):02d}_u{'-'.join(str(value) for value in up_degrees)}"


def _fibers(max_n: int):
    for n in range(1, max_n + 1):
        yield from iter_threshold_graphs(n)


def _enumerate_fiber(up_degrees, keep_entries: bool):
    """Stream the spanning trees of the graph once."""
    inv_counter: Counter[int] = Counter()
    entries = []
    count = 0
    for tree in iter_threshold_spanning_trees(up_degrees):
        inv = tree.inv()
        inv_counter[inv] += 1
        if keep_entries:
            entries.append({"object": tree.encoding, "inv": inv})
        count += 1
    return inv_counter, count, entries


def verify(up_degrees, poly: dict, inv_counter: Counter, count: int) -> None:
    label = f"u={up_degrees}"
    total = sum(poly.values())
    if total != count:
        raise SystemExit(f"{label}: E totals {total} but the graph has {count} spanning trees")
    if any(value < 0 for value in poly.values()):
        raise SystemExit(f"{label}: E has a negative coefficient (Conjecture 6.1 fails?)")
    if poly != {(j, i): value for (i, j), value in poly.items()}:
        raise SystemExit(f"{label}: E is not q,t-symmetric")
    q_marginal: Counter[int] = Counter()
    for (i, _j), value in poly.items():
        q_marginal[i] += value
    if {a: c for a, c in q_marginal.items() if c} != {a: c for a, c in inv_counter.items() if c}:
        raise SystemExit(f"{label}: E(q,1) does not match the inv distribution")


def polynomial_case(up_degrees, poly: dict, count: int) -> dict:
    terms = [[i, j, poly[(i, j)]] for (i, j) in sorted(poly)]
    return {"case_id": case_id(up_degrees), "n": len(up_degrees),
            "up_degrees": list(up_degrees), "count": count,
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(up_degrees, poly: dict, count: int) -> dict:
    marginal: Counter[int] = Counter()
    for (_i, j), value in poly.items():
        marginal[j] += value
    terms = [[j, marginal[j]] for j in sorted(marginal) if marginal[j]]
    return {"case_id": case_id(up_degrees), "n": len(up_degrees),
            "up_degrees": list(up_degrees), "count": count,
            "term_count": len(terms), "terms": terms}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate threshold tree q,t data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=6,
                        help="largest n for the public polynomials")
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
    for up_degrees in _fibers(args.public_max_n):
        keep = len(up_degrees) <= args.instances_max_n
        inv_counter, count, entries = _enumerate_fiber(up_degrees, keep)
        poly = oracle.E_poly(up_degrees)
        verify(up_degrees, poly, inv_counter, count)
        poly_cases.append(polynomial_case(up_degrees, poly, count))
        q1_cases.append(q_equals_1_case(up_degrees, poly, count))
        if keep:
            instance_cases.append({"case_id": case_id(up_degrees), "n": len(up_degrees),
                                   "up_degrees": list(up_degrees), "count": count,
                                   "entries": entries})
        print(f"verified u={up_degrees}: trees={count}, terms={len(poly)}", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["q", "t"],
                    "known_statistic": "inv",
                    "source": "(q,t)-Ehrhart function of the flow polytope F_G(-n,1,...,1) (arXiv:1610.08370)",
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
                    "object_family": "threshold_graph_spanning_trees",
                    "known_statistic": "inv", "instances_max_n": args.instances_max_n,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
