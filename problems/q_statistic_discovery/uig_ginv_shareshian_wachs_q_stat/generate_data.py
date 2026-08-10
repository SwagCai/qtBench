#!/usr/bin/env python3
"""Generate public data for the Shareshian--Wachs ``e``-positivity problem.

The target polynomials are the elementary-basis coefficients of the chromatic
quasisymmetric function of Shareshian and Wachs,

    chi_G[X; q] = sum_{lambda |- n} c_lambda(q) e_lambda,

for every Dyck graph (natural unit interval graph) ``G`` on ``[n]``, computed by
the public oracle ``problems/q_statistic_discovery/
uig_ginv_shareshian_wachs_q_stat/csf_oracle.py``. For each graph the expansion is
verified to be

  * ``e``-positive with integer coefficients (the Shareshian--Wachs conjecture),
  * reciprocal with ambient exponent ``|E|`` in each ``c_lambda`` (a proven
    symmetry), and
  * consistent with the object model: ``sum_lambda c_lambda(q)`` equals the
    ``ginv`` generating function ``sum_{sigma in D_G^0} q^{ginv_G(sigma)}`` (so, at
    ``q = 1``, ``sum_lambda c_lambda(1) = |D_G^0|``).

The last check ties the algebraic target to the combinatorial objects and the
public ``ginv`` statistic, the analogue of the ``t = 1`` marginal check in the
other problems. The scored evaluator never loads the oracle.

Enumeration streams one permutation at a time, so peak memory stays small.
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
    iter_dyck_graph_vectors,
    iter_uig_permutations_for_vector,
)
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "csf_oracle.py")


def case_id(n: int, index: int) -> str:
    return f"n{n:02d}_g{index:03d}"


def _poly_add(a: dict, b: dict) -> dict:
    out = dict(a)
    for exp, coeff in b.items():
        out[exp] = out.get(exp, 0) + coeff
    return {exp: coeff for exp, coeff in out.items() if coeff}


def _ginv_generating_function(
    b: tuple[int, ...], keep_entries: bool
) -> tuple[Counter, list, int]:
    """Stream ``D_G^0``: return (ginv distribution, [(object, ginv)], count)."""
    distribution: Counter[int] = Counter()
    entries = []
    count = 0
    for obj in iter_uig_permutations_for_vector(b):
        g = obj.ginv()
        distribution[g] += 1
        if keep_entries:
            entries.append({"object": obj.encoding, "ginv": g})
        count += 1
    return distribution, entries, count


def verify(b: tuple[int, ...], expansion: dict, ginv_dist: Counter, count: int) -> None:
    num_edges = sum(1 for i in range(1, len(b) + 1) for j in range(i + 1, b[i - 1] + 1))
    total_poly: dict = {}
    for lam, poly in expansion.items():
        # e-positivity: integer, nonnegative coefficients.
        if any(coeff < 0 for coeff in poly.values()):
            raise SystemExit(f"b={b}: c_{lam} has a negative coefficient (e-positivity)")
        # Reciprocity: c_lambda(q) = q^{|E|} c_lambda(1/q).  The actual degree
        # may be smaller than |E| when the coefficients at both endpoints vanish.
        for exp, coeff in poly.items():
            if poly.get(num_edges - exp, 0) != coeff:
                raise SystemExit(f"b={b}: c_{lam} is not reciprocal with ambient exponent |E|={num_edges}")
        total_poly = _poly_add(total_poly, poly)
    # total identity: sum_lambda c_lambda(q) == sum_sigma q^{ginv}.
    ginv_poly = {exp: coeff for exp, coeff in ginv_dist.items() if coeff}
    if total_poly != ginv_poly:
        raise SystemExit(f"b={b}: sum_lambda c_lambda(q) != ginv generating function")
    if sum(total_poly.values()) != count:
        raise SystemExit(f"b={b}: e-coefficients total {sum(total_poly.values())} but |D_G^0| = {count}")


def polynomial_case(n: int, index: int, b: tuple[int, ...], expansion: dict, count: int) -> dict:
    terms = []
    for lam in sorted(expansion):
        for exp in sorted(expansion[lam]):
            terms.append([list(lam), exp, expansion[lam][exp]])
    return {"case_id": case_id(n, index), "n": n, "b": list(b), "count": count,
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(n: int, index: int, b: tuple[int, ...], expansion: dict, count: int) -> dict:
    terms = []
    for lam in sorted(expansion):
        coeff = sum(expansion[lam].values())
        if coeff:
            terms.append([list(lam), coeff])
    return {"case_id": case_id(n, index), "n": n, "b": list(b), "count": count,
            "term_count": len(terms), "terms": terms}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Shareshian--Wachs e-positivity data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=7,
                        help="largest number of vertices n for the public polynomials")
    parser.add_argument("--instances-max-n", type=int, default=6,
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
    for n in range(1, args.public_max_n + 1):
        keep = n <= args.instances_max_n
        for index, b in enumerate(iter_dyck_graph_vectors(n)):
            expansion = oracle.chi_e_expansion(b)
            ginv_dist, entries, count = _ginv_generating_function(b, keep)
            verify(b, expansion, ginv_dist, count)
            poly_cases.append(polynomial_case(n, index, b, expansion, count))
            q1_cases.append(q_equals_1_case(n, index, b, expansion, count))
            if keep:
                instance_cases.append({"case_id": case_id(n, index), "n": n, "b": list(b),
                                       "count": count, "entries": entries})
        print(f"verified n={n}: {sum(1 for _ in iter_dyck_graph_vectors(n))} graphs", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["partition", "q"],
                    "known_statistic": "ginv",
                    "source": "Elementary expansion of the Shareshian-Wachs chromatic quasisymmetric function chi_G[X;q]",
                    "public_max_n": args.public_max_n, "case_count": len(poly_cases),
                    "cases": poly_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["partition"],
                    "specialization": {"q": 1},
                    "meaning": "Necessary partition-multiset distribution for the unknown theta statistic.",
                    "public_max_n": args.public_max_n, "case_count": len(q1_cases),
                    "cases": q1_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "unit_interval_graph_permutations",
                    "known_statistic": "ginv", "instances_max_n": args.instances_max_n,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
