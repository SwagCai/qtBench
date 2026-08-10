#!/usr/bin/env python3
"""Generate public data for the modified (q,t)-Kostka standard tableau problem.

The target polynomials are the modified (q,t)-Kostka polynomials

    K~_{lambda mu}(q, t) = < H~_mu(X; q, t), s_lambda >,

computed by the public oracle ``problems/t_statistic_discovery/
syt_qt_kostka_macdonald_pair_stat/macdonald_kostka_oracle.py`` from the
Haglund-Haiman-Loehr monomial formula (arXiv:math/0409538). Every target is
verified against the identities that tie the algebraic polynomial to the object
model before it is written:

* nonnegative coefficients and nonnegative exponents (Haiman's theorem);
* ``K~_{lambda mu}(1, 1) = |SYT(lambda)|``, checked against the enumerated fiber;
* ``K~_{lambda mu}(q, t) = K~_{lambda mu'}(t, q)`` (from ``H~_{mu'}(q,t) = H~_mu(t,q)``);
* ``K~_{lambda (n)}(q, t) = sum_T q^{maj(T)}`` and
  ``K~_{lambda (1^n)}(q, t) = sum_T t^{maj(T)}`` over ``SYT(lambda)``;
* ``K~_{lambda mu}(0, 1) = K_{lambda mu}``, the Kostka number, and
  ``K~_{lambda mu}(1, 0) = K_{lambda mu'}``.

Enumeration streams one tableau at a time, so peak memory stays small. The
scored evaluator never loads the oracle.
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

from qtbench.combinatorics import iter_kostka_standard_tableaux, iter_partitions
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "macdonald_kostka_oracle.py")


def _partition_text(mu) -> str:
    return ",".join(str(part) for part in mu)


def case_id(n: int, lam, mu) -> str:
    return f"n{n:02d}_l{'.'.join(str(part) for part in lam)}_m{'.'.join(str(part) for part in mu)}"


def _enumerate_fiber(lam, mu, keep_entries: bool):
    """Stream ``SYT(lambda) x {mu}`` once; return ``(maj_counter, count, entries)``."""
    maj_counter: Counter[int] = Counter()
    entries = []
    count = 0
    for tableau in iter_kostka_standard_tableaux(lam, mu):
        maj_counter[tableau.maj()] += 1
        if keep_entries:
            entries.append(tableau.encoding)
        count += 1
    return maj_counter, count, entries


def verify(n: int, lam, mu, table, maj_counter: Counter, count: int, oracle) -> None:
    poly = table[(lam, mu)]
    if any(coefficient < 0 for coefficient in poly.values()):
        raise SystemExit(f"K~_{lam},{mu} has a negative coefficient")
    if any(i < 0 or j < 0 for i, j in poly):
        raise SystemExit(f"K~_{lam},{mu} has a negative exponent")
    if sum(poly.values()) != count:
        raise SystemExit(
            f"K~_{lam},{mu}(1,1) = {sum(poly.values())} but |SYT({lam})| = {count}"
        )
    swapped = Counter(
        {(j, i): coefficient for (i, j), coefficient in table[(lam, oracle.conjugate(mu))].items()}
    )
    if poly != swapped:
        raise SystemExit(f"K~_{lam},{mu}(q,t) != K~_{lam},{mu}'(t,q)")

    q_marginal: Counter[int] = Counter()
    t_marginal: Counter[int] = Counter()
    at_q_zero = at_t_zero = 0
    for (i, j), coefficient in poly.items():
        q_marginal[i] += coefficient
        t_marginal[j] += coefficient
        at_q_zero += coefficient if i == 0 else 0
        at_t_zero += coefficient if j == 0 else 0
    if mu == (n,) and q_marginal != maj_counter:
        raise SystemExit(f"K~_{lam},({n}) is not the maj distribution of SYT({lam})")
    if mu == tuple([1] * n) and t_marginal != maj_counter:
        raise SystemExit(f"K~_{lam},(1^{n}) is not the maj distribution of SYT({lam})")
    if at_q_zero != oracle.kostka_number(lam, mu):
        raise SystemExit(f"K~_{lam},{mu}(0,1) is not the Kostka number K_{lam},{mu}")
    if at_t_zero != oracle.kostka_number(lam, oracle.conjugate(mu)):
        raise SystemExit(f"K~_{lam},{mu}(1,0) is not the Kostka number K_{lam},{mu}'")


def polynomial_case(n: int, lam, mu, poly, count: int) -> dict:
    terms = [[i, j, poly[(i, j)]] for (i, j) in sorted(poly)]
    return {
        "case_id": case_id(n, lam, mu),
        "n": n,
        "lam": list(lam),
        "mu": list(mu),
        "count": count,
        "term_count": len(terms),
        "terms": terms,
    }


def q_equals_1_case(n: int, lam, mu, poly, count: int) -> dict:
    marginal: Counter[int] = Counter()
    for (_i, j), coefficient in poly.items():
        marginal[j] += coefficient
    terms = [[j, marginal[j]] for j in sorted(marginal) if marginal[j]]
    return {
        "case_id": case_id(n, lam, mu),
        "n": n,
        "lam": list(lam),
        "mu": list(mu),
        "count": count,
        "term_count": len(terms),
        "terms": terms,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate modified (q,t)-Kostka data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-n", type=int, default=8,
                        help="largest |mu| for the public polynomials")
    parser.add_argument("--instances-max-n", type=int, default=6,
                        help="instances.json lists every object of every case up to this size")
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
        table = oracle.kostka_polynomials(n)
        keep = n <= args.instances_max_n
        for lam in iter_partitions(n):
            for mu in iter_partitions(n):
                maj_counter, count, entries = _enumerate_fiber(lam, mu, keep)
                verify(n, lam, mu, table, maj_counter, count, oracle)
                poly = table[(lam, mu)]
                poly_cases.append(polynomial_case(n, lam, mu, poly, count))
                q1_cases.append(q_equals_1_case(n, lam, mu, poly, count))
                if keep:
                    instance_cases.append(
                        {
                            "case_id": case_id(n, lam, mu),
                            "n": n,
                            "lam": list(lam),
                            "mu": list(mu),
                            "count": count,
                            "entries": entries,
                        }
                    )
        print(f"verified n={n}: {len(iter_partitions(n)) ** 2} pairs", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["q", "t"],
                    "known_statistics": [],
                    "source": "Schur coefficients K~_{lambda mu}(q,t) of the modified Macdonald polynomial H~_mu (arXiv:math/0409538)",
                    "public_max_n": args.public_max_n,
                    "case_count": len(poly_cases), "cases": poly_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["t"],
                    "specialization": {"q": 1},
                    "meaning": "Necessary one-variable distribution for the unknown t-statistic.",
                    "public_max_n": args.public_max_n,
                    "case_count": len(q1_cases), "cases": q1_cases}, indent=2), encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "kostka_standard_tableaux",
                    "known_statistics": [],
                    "instances_max_n": args.instances_max_n,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
