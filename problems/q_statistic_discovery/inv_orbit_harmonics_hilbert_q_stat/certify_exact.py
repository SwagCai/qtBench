#!/usr/bin/env sage -python
"""Certify every published orbit-harmonics target by exact rank over ``QQ``.

Run from the repository root with::

    sage -python problems/q_statistic_discovery/\
        inv_orbit_harmonics_hilbert_q_stat/certify_exact.py

Sage's proof-enabled multimodular echelon algorithm reconstructs and verifies a
row echelon form over the rational field.  Finite-field agreement is not used as
the certificate.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.generation import load_trusted_oracle

try:
    from sage.all import QQ, matrix, version
except ModuleNotFoundError as error:  # pragma: no cover - depends on the host
    raise SystemExit(
        "this script needs a SageMath that provides `sage.all`.\n"
        "`sage -python -c 'import sage.all'` must succeed first. Modular\n"
        "repackagings such as passagemath install `sage.all` only once the\n"
        "relevant component packages are present. The shipped certificate in\n"
        "data/exact_certificate.json records the build that produced it."
    ) from error

PROBLEM_DIR = Path(__file__).resolve().parent
oracle = load_trusted_oracle(PROBLEM_DIR / "orbit_harmonics_oracle.py")
POLYNOMIALS = PROBLEM_DIR / "data" / "polynomials.json"
CERTIFICATE = PROBLEM_DIR / "data" / "exact_certificate.json"


def exact_hilbert_series(n: int, a: int) -> tuple[list[int], list[int]]:
    """Return the Hilbert series and cumulative ranks, computed over ``QQ``."""

    points = list(oracle.iter_involution_images(n, a))
    width = len(points)
    basis = matrix(QQ, 0, width, sparse=True)
    cumulative_ranks: list[int] = []
    for weight in range((n + a) // 2 + 1):
        entries: dict[tuple[int, int], int] = {}
        row_count = 0
        for indicator in oracle.iter_indicators_of_weight(
            points, n, spanning="involution", weight=weight
        ):
            for column in indicator.nonzero()[0]:
                entries[(row_count, int(column))] = 1
            row_count += 1
        incoming = matrix(QQ, row_count, width, entries, sparse=True)
        combined = basis.stack(incoming)
        echelon = combined.echelon_form(algorithm="multimodular", proof=True)
        rank = len(echelon.pivots())
        basis = echelon[:rank]
        cumulative_ranks.append(rank)
        if rank == width:
            break
    if cumulative_ranks[-1] != width:
        raise RuntimeError(f"exact indicators span only {cumulative_ranks[-1]} of {width}")
    previous = 0
    series: list[int] = []
    for rank in cumulative_ranks:
        series.append(rank - previous)
        previous = rank
    return series, cumulative_ranks


def main() -> None:
    encoded = POLYNOMIALS.read_bytes()
    target = json.loads(encoded)
    cases: list[dict] = []
    for case in target["cases"]:
        n = int(case["n"])
        a = int(case["a"])
        started = time.perf_counter()
        series, cumulative_ranks = exact_hilbert_series(n, a)
        expected = [0] * (max(int(term[0]) for term in case["terms"]) + 1)
        for degree, coefficient in case["terms"]:
            expected[int(degree)] = int(coefficient)
        if series != expected:
            raise SystemExit(
                f"{case['case_id']}: exact series {series} != published {expected}"
            )
        cases.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "a": a,
                "point_count": int(case["count"]),
                "cumulative_ranks": cumulative_ranks,
                "hilbert_series": series,
            }
        )
        print(
            f"certified {case['case_id']}: ranks={cumulative_ranks} "
            f"({time.perf_counter() - started:.1f}s)",
            flush=True,
        )

    certificate = {
        "schema_version": "0.1",
        "problem_id": oracle.PROBLEM_ID,
        "problem_name": oracle.PROBLEM_NAME,
        "method": "proof-enabled sparse row echelon form over QQ",
        "sage_version": version(),
        "polynomials_sha256": hashlib.sha256(encoded).hexdigest(),
        "case_count": len(cases),
        "cases": cases,
    }
    CERTIFICATE.write_text(json.dumps(certificate, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {CERTIFICATE}")


if __name__ == "__main__":
    main()
