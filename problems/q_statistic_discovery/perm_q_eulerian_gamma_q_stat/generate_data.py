#!/usr/bin/env python3
"""Generate public data for the q-Eulerian gamma coefficient problem.

The target polynomials are the coefficients ``a_{n,k}(q)`` of the Han-Jouhet-Zeng
expansion of Carlitz's ``q``-Eulerian polynomial,

    A_n(t,q) = sum_{k=1}^{floor((n+1)/2)} a_{n,k}(q) t^{k-1} (-t q^k; q)_{n+1-2k},

computed by the public oracle ``problems/q_statistic_discovery/
perm_q_eulerian_gamma_q_stat/q_eulerian_oracle.py``. For each size the generator
checks

  * ``A_n(t,q)`` from the recurrence against ``sum_{sigma in S_n} t^{des} q^{maj}``,
    enumerated over the whole symmetric group (up to ``--brute-max-n``),
  * ``A_n(t,q)`` against Carlitz's defining identity
    ``sum_j [j+1]_q^n t^j = A_n(t,q) / (t;q)_{n+1}``, as a truncated power series,
  * ``a_{n,k}(q)`` from the recurrence against ``a_{n,k}(q)`` solved out of the
    expansion, which also verifies that the expansion closes with no residue,
  * ``a_{n,k}(q)`` in ``N[q]`` -- the content of Han-Jouhet-Zeng's Theorem 1,
  * ``a_{n,k}(1) = |Gamma_{n,k}|``, the classical Eulerian gamma-coefficient,
    against the enumerated objects, and
  * the divisibility ``q^{binom(k,2)} | a_{n,k}(q)`` and the degree
    ``deg a_{n,k} = binom(k,2) + (k-1)(n-k)``.

The last two are recorded as observed properties of the public range; the
divisibility is the substitution behind the paper's Corollary 2.

Enumeration streams one permutation at a time, so peak memory stays small.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.combinatorics import iter_gamma_permutations_for_descents
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "q_eulerian_oracle.py")


def case_id(n: int, k: int) -> str:
    return f"n{n:02d}_k{k:02d}"


def _fiber(n: int, k: int, keep_entries: bool) -> tuple[list[str], Counter, int]:
    """Stream the fiber: ([object encodings], descent distribution, count)."""
    entries: list[str] = []
    descents: Counter[int] = Counter()
    count = 0
    for obj in iter_gamma_permutations_for_descents(n, k):
        if keep_entries:
            entries.append(obj.encoding)
        descents[obj.descents] += 1
        count += 1
    return entries, descents, count


def verify(n: int, k: int, coefficients: list[int], descents: Counter, count: int) -> None:
    if any(value < 0 for value in coefficients) or not coefficients:
        raise SystemExit(f"n={n} k={k}: a_{{n,k}} is not a nonzero element of N[q]: {coefficients}")
    # a_{n,k}(1) = |Gamma_{n,k}|, the classical Eulerian gamma-coefficient
    if sum(coefficients) != count:
        raise SystemExit(f"n={n} k={k}: a(1) = {sum(coefficients)} but the fiber has {count}")
    if set(descents) != {k - 1}:
        raise SystemExit(f"n={n} k={k}: the fiber has descent counts {sorted(descents)}")
    low = next(index for index, value in enumerate(coefficients) if value)
    if low < k * (k - 1) // 2:
        raise SystemExit(f"n={n} k={k}: q^binom(k,2) does not divide a_{{n,k}}")
    degree = len(coefficients) - 1
    expected = k * (k - 1) // 2 + (k - 1) * (n - k)
    if degree != expected:
        raise SystemExit(f"n={n} k={k}: degree {degree}, expected {expected}")


def polynomial_case(n: int, k: int, coefficients: list[int], count: int) -> dict:
    terms = [
        [degree, value] for degree, value in enumerate(coefficients) if value
    ]
    return {"case_id": case_id(n, k), "n": n, "k": k, "count": count,
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(n: int, k: int, count: int) -> dict:
    return {"case_id": case_id(n, k), "n": n, "k": k, "count": count,
            "term_count": 1, "terms": [[k - 1, count]]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate q-Eulerian gamma coefficient data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=9,
                        help="largest size n for the public gamma coefficients")
    parser.add_argument("--instances-max-n", type=int, default=8,
                        help="instances.json lists every object, so it is capped smaller")
    parser.add_argument("--brute-max-n", type=int, default=8,
                        help="recompute A_n(t,q) over the whole symmetric group up to this size")
    args = parser.parse_args()
    if args.public_max_n < 1:
        parser.error("--public-max-n must be positive")
    if not 1 <= args.instances_max_n <= args.public_max_n:
        parser.error(
            "--instances-max-n must be positive and no greater than --public-max-n"
        )
    if args.brute_max_n < 0:
        parser.error("--brute-max-n must be nonnegative")

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
        started = time.perf_counter()
        if n <= args.brute_max_n and oracle.q_eulerian(n) != oracle.q_eulerian_brute(n):
            raise SystemExit(f"n={n}: A_n from the recurrence differs from the S_n enumeration")
        failing = oracle.carlitz_identity_residue(n)
        if failing is not None:
            raise SystemExit(f"n={n}: Carlitz's identity fails at t^{failing}")
        coefficients = oracle.gamma_coefficients(n)
        if coefficients != oracle.gamma_coefficients_from_expansion(n):
            raise SystemExit(f"n={n}: the recurrence and the expansion disagree")
        objects = 0
        keep = n <= args.instances_max_n
        for k in sorted(coefficients):
            entries, descents, count = _fiber(n, k, keep)
            verify(n, k, coefficients[k], descents, count)
            poly_cases.append(polynomial_case(n, k, coefficients[k], count))
            q1_cases.append(q_equals_1_case(n, k, count))
            if keep:
                instance_cases.append({"case_id": case_id(n, k), "n": n, "k": k,
                                       "count": count, "entries": entries})
            objects += count
        print(f"verified n={n}: {objects} objects over {len(coefficients)} fibers "
              f"({time.perf_counter() - started:.1f}s)", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["q"],
                    "known_statistics": [],
                    "source": "Han-Jouhet-Zeng gamma coefficients a_{n,k}(q) of Carlitz's q-Eulerian polynomial",
                    "public_max_n": args.public_max_n, "case_count": len(poly_cases),
                    "cases": poly_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["descents"],
                    "specialization": {"q": 1},
                    "meaning": "a_{n,k}(1) = |Gamma_{n,k}|, the classical Eulerian gamma-coefficient: the fiber's descent count and size, an object-model check that any statistic satisfies.",
                    "public_max_n": args.public_max_n, "case_count": len(q1_cases),
                    "cases": q1_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "gamma_permutations",
                    "known_statistics": [], "instances_max_n": args.instances_max_n,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
