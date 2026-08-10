#!/usr/bin/env python3
"""Generate public data for the unicellular LLT Schur coefficient problem.

The target polynomials are the Schur-basis coefficients of the unicellular LLT
polynomial,

    LLT_G(X; q) = sum_{lambda |- n} c_lambda^G(q) s_lambda(X),

for every Dyck graph (natural unit interval graph) ``G`` on ``[n]``, computed by
the public oracle ``problems/q_statistic_discovery/
uig_syt_llt_schur_q_stat/llt_oracle.py``. For each graph the expansion is
verified to be

  * Schur positive with integer coefficients (Grojnowski--Haiman),
  * consistent with the object model: ``c_lambda^G(1) = f^lambda``, the number of
    standard Young tableaux of shape ``lambda`` in the fiber, which is the
    ``q = 1`` degeneration ``LLT_G(X; 1) = p_1^n``,
  * of degree at most ``|E|``, with ``c_{(n)}^G(q) = 1`` and
    ``c_{(1^n)}^G(q) = q^{|E|}`` at the two extreme shapes, and
  * transpose-symmetric: ``c_{lambda'}^G(q) = q^{|E|} c_lambda^G(1/q)``, the
    coefficientwise form of ``omega LLT_G(X; q) = q^{|E|} LLT_G(X; 1/q)``.

The second check ties the algebraic target to the combinatorial objects, the
analogue of the ``t = 1`` marginal check in the other problems; the last two are
proven symmetries that pin the ends of the ``q``-range. The scored evaluator
never loads the oracle.

Enumeration streams one tableau at a time, so peak memory stays small.
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
    iter_uig_tableaux_for_vector,
)
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "llt_oracle.py")


def case_id(n: int, index: int) -> str:
    return f"n{n:02d}_g{index:03d}"


def _conjugate(lam: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sum(1 for part in lam if part > column) for column in range(lam[0]))


def _shape_distribution(
    b: tuple[int, ...], keep_entries: bool
) -> tuple[Counter, list, int]:
    """Stream the fiber: return (shape distribution, [object encodings], count)."""
    distribution: Counter[tuple[int, ...]] = Counter()
    entries = []
    count = 0
    for obj in iter_uig_tableaux_for_vector(b):
        distribution[obj.shape] += 1
        if keep_entries:
            entries.append(obj.encoding)
        count += 1
    return distribution, entries, count


def verify(b: tuple[int, ...], expansion: dict, shapes: Counter, count: int) -> None:
    n = len(b)
    num_edges = sum(1 for i in range(1, n + 1) for j in range(i + 1, b[i - 1] + 1))
    for lam, poly in expansion.items():
        # Schur positivity: integer, nonnegative coefficients.
        if any(coeff < 0 for coeff in poly.values()):
            raise SystemExit(f"b={b}: c_{lam} has a negative coefficient (Schur positivity)")
        if max(poly) > num_edges:
            raise SystemExit(f"b={b}: c_{lam} has degree above |E| = {num_edges}")
        # transpose symmetry: c_{lambda'}(q) = q^{|E|} c_lambda(1/q).
        mirrored = expansion.get(_conjugate(lam), {})
        if {num_edges - exp: coeff for exp, coeff in poly.items()} != mirrored:
            raise SystemExit(f"b={b}: c_{lam} and c_{_conjugate(lam)} are not transpose-symmetric")
    if expansion.get((n,)) != {0: 1}:
        raise SystemExit(f"b={b}: c_(n) is {expansion.get((n,))}, expected 1")
    if expansion.get(tuple([1] * n)) != {num_edges: 1}:
        raise SystemExit(f"b={b}: c_(1^n) is not q^{num_edges}")
    # object-model identity: c_lambda(1) = f^lambda, so the fiber realizes the target.
    marginal = {lam: sum(poly.values()) for lam, poly in expansion.items()}
    if marginal != dict(shapes):
        raise SystemExit(f"b={b}: c_lambda(1) does not match the SYT counts of the fiber")
    if sum(marginal.values()) != count:
        raise SystemExit(f"b={b}: coefficients total {sum(marginal.values())} but the fiber has {count}")


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
    parser = argparse.ArgumentParser(description="Generate unicellular LLT Schur coefficient data.")
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
            expansion = oracle.llt_schur_expansion(b)
            shapes, entries, count = _shape_distribution(b, keep)
            verify(b, expansion, shapes, count)
            poly_cases.append(polynomial_case(n, index, b, expansion, count))
            q1_cases.append(q_equals_1_case(n, index, b, expansion, count))
            if keep:
                instance_cases.append({"case_id": case_id(n, index), "n": n, "b": list(b),
                                       "count": count, "entries": entries})
        print(f"verified n={n}: {sum(1 for _ in iter_dyck_graph_vectors(n))} graphs", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["partition", "q"],
                    "known_statistics": [],
                    "source": "Schur expansion of the unicellular LLT polynomial LLT_G[X;q]",
                    "public_max_n": args.public_max_n, "case_count": len(poly_cases),
                    "cases": poly_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["partition"],
                    "specialization": {"q": 1},
                    "meaning": "LLT_G[X;1] = p_1^n, so c_lambda(1) = f^lambda: the shape distribution of the fiber, an object-model check that any statistic satisfies.",
                    "public_max_n": args.public_max_n, "case_count": len(q1_cases),
                    "cases": q1_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "unit_interval_graph_tableaux",
                    "known_statistics": [], "instances_max_n": args.instances_max_n,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
