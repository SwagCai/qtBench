#!/usr/bin/env python3
"""Generate public data for the Matchings-Jack statistic problem.

The target polynomials are the Jack connection coefficients
``c^lambda_{pi,sigma}(beta)`` of Goulden and Jackson, computed by the maintainer
oracle ``problems/q_statistic_discovery/match_jack_connection_q_stat/
jack_connection_oracle.py`` from the power-sum expansion of the Jack Cauchy sum,
exactly, by interpolation in ``beta = alpha - 1``.

For every partition ``lambda`` the generator enumerates the matchings of
``N_n = {1..n} u {1h..nh}``, sorts them into the fibers
``G^lambda_{pi,sigma} = {d : Lambda(d, eps) = pi, Lambda(d, delta_lambda) = sigma}``,
and verifies that each coefficient polynomial is

  * a polynomial in ``beta`` with nonnegative integer coefficients -- the content of
    the Matchings-Jack conjecture itself,
  * of degree at most ``d(pi,sigma;lambda) = (n - l(pi)) + (n - l(sigma)) - (n - l(lambda))``,
    the Dolega--Feray bound, which also rules out an under-sampled interpolation,
  * equal at ``beta = 0`` to the number of *bipartite* matchings in the fiber, and
    equal to the same number computed a second way, as the class-algebra structure
    constant counted by brute force over ``S_n``, and
  * equal at ``beta = 1`` to the size of the fiber, the ungraded count that any
    statistic reproduces.

The oracle's Jack construction is separately validated at several values of
``alpha`` against three facts it was not built from: the hook-product norm
``<J_lambda, J_lambda>_alpha = j_lambda``, dominance triangularity in the monomial
basis, and ``J_{(1^n)} = n! e_n``. The scored evaluator never loads the oracle.

Enumeration streams one matching at a time, so peak memory stays small.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.combinatorics import (
    iter_jack_matchings_for_partition,
    iter_partitions,
    jack_matching_count,
)
from qtbench.generation import load_trusted_oracle

VALIDATION_ALPHAS = (1, 2, 3, Fraction(1, 2), Fraction(5, 3))


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "jack_connection_oracle.py")


def case_id(n: int, index: int) -> str:
    return f"n{n:02d}_l{index:03d}"


def _fiber_data(
    lam: tuple[int, ...], keep_entries: bool
) -> tuple[Counter, Counter, list, int]:
    """Stream the objects of one ``lambda``: fiber sizes, bipartite counts, encodings."""
    sizes: Counter[tuple[tuple[int, ...], tuple[int, ...]]] = Counter()
    bipartite: Counter[tuple[tuple[int, ...], tuple[int, ...]]] = Counter()
    entries: list[str] = []
    count = 0
    for obj in iter_jack_matchings_for_partition(lam):
        key = (obj.epsilon_type(), obj.reference_type())
        sizes[key] += 1
        if obj.is_bipartite:
            bipartite[key] += 1
        if keep_entries:
            entries.append(obj.encoding)
        count += 1
    return sizes, bipartite, entries, count


def verify(
    n: int,
    lam: tuple[int, ...],
    polynomials: dict,
    structure: dict,
    sizes: Counter,
    bipartite: Counter,
    count: int,
) -> dict:
    """Check one ``lambda`` and return ``{(pi, sigma): [coefficients]}``."""
    kept: dict = {}
    for (other, pi, sigma), coefficients in polynomials.items():
        if other != lam:
            continue
        if any(value.denominator != 1 or value < 0 for value in coefficients):
            raise SystemExit(
                f"lam={lam} pi={pi} sigma={sigma}: c is not beta-positive integral: "
                f"{[str(v) for v in coefficients]}"
            )
        integral = [int(value) for value in coefficients]
        bound = (n - len(pi)) + (n - len(sigma)) - (n - len(lam))
        if integral and len(integral) - 1 > bound:
            raise SystemExit(f"lam={lam} pi={pi} sigma={sigma}: degree above d = {bound}")
        at_zero = integral[0] if integral else 0
        at_one = sum(integral)
        if at_zero != bipartite.get((pi, sigma), 0):
            raise SystemExit(
                f"lam={lam} pi={pi} sigma={sigma}: c(0) = {at_zero} but the fiber has "
                f"{bipartite.get((pi, sigma), 0)} bipartite matchings"
            )
        if at_zero != structure[(lam, pi, sigma)]:
            raise SystemExit(
                f"lam={lam} pi={pi} sigma={sigma}: c(0) = {at_zero} but the class-algebra "
                f"structure constant is {structure[(lam, pi, sigma)]}"
            )
        if at_one != sizes.get((pi, sigma), 0):
            raise SystemExit(
                f"lam={lam} pi={pi} sigma={sigma}: c(1) = {at_one} but the fiber has "
                f"{sizes.get((pi, sigma), 0)} matchings"
            )
        if integral:
            kept[(pi, sigma)] = integral
    if sum(sum(values) for values in kept.values()) != count:
        raise SystemExit(f"lam={lam}: the coefficients do not total the {count} objects")
    if set(kept) != {key for key, value in sizes.items() if value}:
        raise SystemExit(f"lam={lam}: nonzero coefficients and nonempty fibers disagree")
    return kept


def polynomial_case(n: int, index: int, lam: tuple[int, ...], kept: dict, count: int) -> dict:
    terms = []
    for pi, sigma in sorted(kept):
        for degree, coefficient in enumerate(kept[(pi, sigma)]):
            if coefficient:
                terms.append([list(pi), list(sigma), degree, coefficient])
    return {"case_id": case_id(n, index), "n": n, "lambda": list(lam), "count": count,
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(n: int, index: int, lam: tuple[int, ...], kept: dict, count: int) -> dict:
    terms = [
        [list(pi), list(sigma), sum(kept[(pi, sigma)])]
        for pi, sigma in sorted(kept)
    ]
    return {"case_id": case_id(n, index), "n": n, "lambda": list(lam), "count": count,
            "term_count": len(terms), "terms": terms}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Matchings-Jack data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=6,
                        help="largest size n for the public connection coefficients")
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
    for n in range(1, args.public_max_n + 1):
        started = time.perf_counter()
        for alpha in VALIDATION_ALPHAS:
            oracle.validate_jack(n, alpha)
        polynomials = oracle.connection_coefficient_polynomials(n)
        structure = oracle.class_algebra_structure_constants(n)
        fibers = 0
        keep = n <= args.instances_max_n
        for index, lam in enumerate(iter_partitions(n)):
            sizes, bipartite, entries, count = _fiber_data(lam, keep)
            kept = verify(n, lam, polynomials, structure, sizes, bipartite, count)
            fibers += len(kept)
            poly_cases.append(polynomial_case(n, index, lam, kept, count))
            q1_cases.append(q_equals_1_case(n, index, lam, kept, count))
            if keep:
                instance_cases.append({"case_id": case_id(n, index), "n": n,
                                       "lambda": list(lam), "count": count,
                                       "entries": entries})
        print(f"verified n={n}: {jack_matching_count(n)} objects, {fibers} nonempty "
              f"(pi, sigma) fibers ({time.perf_counter() - started:.1f}s)", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "variables": ["pi", "sigma", "q"], "known_statistics": [],
                    "source": "Jack connection coefficients c^lambda_{pi,sigma}(beta), beta -> q",
                    "public_max_n": args.public_max_n, "case_count": len(poly_cases),
                    "cases": poly_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "variables": ["pi", "sigma"], "specialization": {"q": 1},
                    "meaning": "c^lambda_{pi,sigma}(1) = |G^lambda_{pi,sigma}|, the double coset algebra specialization: the (pi, sigma) fiber sizes, an object-model check that any statistic satisfies.",
                    "public_max_n": args.public_max_n, "case_count": len(q1_cases),
                    "cases": q1_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "jack_matchings",
                    "known_statistics": [], "instances_max_n": args.instances_max_n,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
