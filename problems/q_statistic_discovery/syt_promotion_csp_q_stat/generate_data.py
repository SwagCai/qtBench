#!/usr/bin/env python3
"""Generate public data for the promotion cyclic sieving statistic problem.

The target for each shape is the least-degree cyclic sieving polynomial of the
promotion action,

    C_lambda(q) = sum_{orbits O} (1 + q^{N/|O|} + ... + q^{(|O|-1)N/|O|}),

with ``N = rc`` for a rectangle ``c^r`` and ``N = k(k+1)`` for a staircase ``sc_k``,
computed by the public oracle ``problems/q_statistic_discovery/
syt_promotion_csp_q_stat/promotion_oracle.py``. For each shape the generator checks

  * promotion is a permutation of ``SYT(lambda)`` and ``d^N`` is the identity, so
    every orbit size divides ``N`` and the polynomial is well defined,
  * ``C_lambda(1) = |SYT(lambda)|``, against the enumerated fiber,
  * the cyclic sieving evaluations ``C_lambda(zeta^e) = #Fix(d^e)`` at every ``N``-th
    root of unity, verified exactly by cyclotomic polynomial division, and
  * on every rectangle, Rhoades' theorem: the distribution of
    ``(maj(T) - n(lambda)) mod N`` is exactly ``C_lambda(q)``. This is the solved
    family, and it is what an answer to the open staircase family has to specialize
    to.

The staircase ``sc_5`` is deliberately outside the public range: its ``292864``
tableaux do not fit the checker's per-case memory budget. A proposal should still be
tested there.

Enumeration streams one tableau at a time where it can, but the orbit computation
needs the whole fiber, which is why the shapes are capped by cell count.
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

from qtbench.combinatorics import (
    iter_promotion_tableaux_for_shape,
    promotion_modulus,
    rectangle_shape,
    staircase_shape,
)
from qtbench.generation import load_trusted_oracle


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "promotion_oracle.py")


def public_shapes(staircase_max_k: int, rectangle_max_cells: int) -> list[tuple[int, ...]]:
    """The public shape set: small staircases and every rectangle up to a cell cap."""
    shapes = [staircase_shape(k) for k in range(2, staircase_max_k + 1)]
    rectangles = []
    for columns in range(2, rectangle_max_cells // 2 + 1):
        for rows in range(2, rectangle_max_cells // columns + 1):
            rectangles.append(rectangle_shape(columns, rows))
    shapes.extend(sorted(rectangles, key=lambda shape: (sum(shape), shape)))
    return shapes


def case_id(index: int, shape) -> str:
    kind = "r" if len(set(shape)) == 1 else "s"
    return f"{kind}{sum(shape):02d}_{index:03d}"


def verify(shape, coefficients, modulus, count, oracle, tableaux) -> None:
    if sum(coefficients) != count:
        raise SystemExit(f"{shape}: C(1) = {sum(coefficients)} but the fiber has {count}")
    if any(value < 0 for value in coefficients):
        raise SystemExit(f"{shape}: C has a negative coefficient")
    if len(coefficients) > modulus:
        raise SystemExit(f"{shape}: C has degree {len(coefficients) - 1} >= N = {modulus}")
    oracle.check_promotion(tableaux, modulus)
    oracle.check_cyclic_sieving(coefficients, modulus, tableaux)
    if len(set(shape)) == 1:
        # Rhoades: on a rectangle the statistic is (maj - n(lambda)) mod N.
        charge = sum(index * part for index, part in enumerate(shape))
        cells = sum(shape)
        distribution: Counter[int] = Counter()
        for rows in tableaux:
            row_of = {value: r for r, row in enumerate(rows) for value in row}
            maj = sum(i for i in range(1, cells) if row_of[i + 1] > row_of[i])
            distribution[(maj - charge) % modulus] += 1
        expected = Counter({d: c for d, c in enumerate(coefficients) if c})
        if distribution != expected:
            raise SystemExit(f"{shape}: (maj - n(lambda)) mod N does not give C")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate promotion cyclic sieving data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--staircase-max-k", type=int, default=4)
    parser.add_argument("--rectangle-max-cells", type=int, default=16)
    parser.add_argument("--instances-max-cells", type=int, default=12,
                        help="instances.json lists every object, so it is capped smaller")
    args = parser.parse_args()
    if args.staircase_max_k < 2:
        parser.error("--staircase-max-k must be at least 2")
    if args.staircase_max_k > 4:
        parser.error("--staircase-max-k must be no greater than 4")
    if args.rectangle_max_cells < 4:
        parser.error("--rectangle-max-cells must be at least 4")
    if args.rectangle_max_cells > 16:
        parser.error("--rectangle-max-cells must be no greater than 16")
    public_max_cells = max(
        args.staircase_max_k * (args.staircase_max_k + 1) // 2,
        args.rectangle_max_cells,
    )
    if not 3 <= args.instances_max_cells <= public_max_cells:
        parser.error(
            "--instances-max-cells must be at least 3 and no greater than the "
            "largest public shape"
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
    for index, shape in enumerate(public_shapes(args.staircase_max_k, args.rectangle_max_cells)):
        started = time.perf_counter()
        objects = list(iter_promotion_tableaux_for_shape(shape))
        tableaux = [obj.rows for obj in objects]
        modulus = promotion_modulus(shape)
        coefficients = oracle.sieving_polynomial(tableaux, modulus)
        verify(shape, coefficients, modulus, len(objects), oracle, tableaux)
        terms = [[degree, value] for degree, value in enumerate(coefficients) if value]
        header = {"case_id": case_id(index, shape), "shape": list(shape),
                  "cells": sum(shape), "modulus": modulus, "count": len(objects)}
        poly_cases.append({**header, "term_count": len(terms), "terms": terms})
        q1_cases.append({**header, "term_count": 1,
                         "terms": [[list(shape), len(objects)]]})
        if sum(shape) <= args.instances_max_cells:
            instance_cases.append({**header, "entries": [obj.encoding for obj in objects]})
        print(f"verified {tuple(shape)}: |SYT|={len(objects)} N={modulus} "
              f"({time.perf_counter() - started:.1f}s)", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["q"],
                    "known_statistics": [],
                    "source": "least-degree cyclic sieving polynomial of promotion on SYT(lambda)",
                    "case_count": len(poly_cases), "cases": poly_cases}, indent=2),
        encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity, "variables": ["shape"],
                    "specialization": {"q": 1},
                    "meaning": "C_lambda(1) = |SYT(lambda)|: the shape and size of the fiber, an object-model check that any statistic satisfies.",
                    "case_count": len(q1_cases), "cases": q1_cases}, indent=2),
        encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": "promotion_tableaux", "known_statistics": [],
                    "instances_max_cells": args.instances_max_cells,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
