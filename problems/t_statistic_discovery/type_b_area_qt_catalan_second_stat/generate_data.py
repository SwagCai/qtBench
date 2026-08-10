#!/usr/bin/env python3
"""Generate public data for the type B q,t-Catalan area-partner problem.

The target type B q,t-Catalan polynomials (n=1..9) are read from the adjacent
committed ``source_data`` records.  These comprise published/cyclic values for
n<=4, reported direct-computation outputs for n=5,6, and conditional SL2-string
completions for n=7,8,9.  The direct-computation and reconstruction pipelines
are not included in this repository; this script re-emits the recorded targets
rather than deriving them.  See ``problem.md`` and ``source_data/README.md`` for
their precise provenance status.
Each extracted polynomial is verified to be q,t-symmetric, to total the type B
Catalan number binomial(2n,n), and to have its q-marginal equal to the type B
area distribution of the ported ``TypeBCatalanPath`` model.
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

from qtbench.combinatorics import enumerate_type_b_catalan_paths, type_b_catalan_number

SOURCE_FILES = (
    "type_b_qt_catalan_known_n1_to_n6.json",
    "type_b_qt_catalan_sl2_pattern_n7_n8.json",
    "type_b_qt_catalan_sl2_pattern_n9.json",
)


def load_target(source_dir: Path) -> dict[int, dict[tuple[int, int], int]]:
    target: dict[int, dict[tuple[int, int], int]] = {}
    for name in SOURCE_FILES:
        cases = json.loads((source_dir / name).read_text(encoding="utf-8"))["cases"]
        for case in cases.values():
            terms = {(int(t["q"]), int(t["t"])): int(t["coeff"]) for t in case["qt_polynomial"]}
            n = int(case["n"])
            if n in target:
                raise SystemExit(f"source data contains duplicate n={n}")
            if not terms or any(coefficient <= 0 for coefficient in terms.values()):
                raise SystemExit(f"source data contains invalid coefficients for n={n}")
            target[n] = terms
    return target


def verify(n: int, poly: dict[tuple[int, int], int]) -> None:
    if sum(poly.values()) != type_b_catalan_number(n):
        raise SystemExit(f"n={n}: coefficients do not total binomial(2n, n)")
    if poly != {(t, q): c for (q, t), c in poly.items()}:
        raise SystemExit(f"n={n}: polynomial is not q,t-symmetric")
    model = Counter(path.area() for path in enumerate_type_b_catalan_paths(n))
    q_marginal = Counter()
    for (q, _t), c in poly.items():
        q_marginal[q] += c
    if model != q_marginal:
        raise SystemExit(f"n={n}: type B area distribution does not match the target q-marginal")


def polynomial_case(n: int, poly: dict[tuple[int, int], int]) -> dict:
    terms = [[q, t, poly[(q, t)]] for q, t in sorted(poly)]
    return {"case_id": f"n{n:02d}", "n": n, "count": type_b_catalan_number(n),
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(n: int, poly: dict[tuple[int, int], int]) -> dict:
    marginal: Counter[int] = Counter()
    for (_q, t), c in poly.items():
        marginal[t] += c
    terms = [[t, marginal[t]] for t in sorted(marginal)]
    return {"case_id": f"n{n:02d}", "n": n, "count": type_b_catalan_number(n),
            "term_count": len(terms), "terms": terms}


def instance_case(n: int) -> dict:
    entries = [{"path": path.steps, "area": path.area()} for path in enumerate_type_b_catalan_paths(n)]
    return {"case_id": f"n{n:02d}", "n": n, "count": len(entries), "entries": entries}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate type B q,t-Catalan data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument(
        "--source-dir",
        type=Path,
        help="Directory holding the committed type_b_qt_catalan_*.json target "
        "records; defaults to <problem-dir>/source_data",
    )
    parser.add_argument("--public-max-n", type=int, default=9)
    parser.add_argument("--instances-max-n", type=int, default=6)
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
    expected_identity = {
        "problem_id": 3,
        "problem_name": "type_b_area_qt_catalan_second_stat",
    }
    if identity != expected_identity:
        raise SystemExit(
            f"--problem-dir identifies {identity}, expected {expected_identity}"
        )
    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    source_dir = (
        args.source_dir.resolve()
        if args.source_dir is not None
        else problem_dir / "source_data"
    )
    target = load_target(source_dir)
    for n in range(1, args.public_max_n + 1):
        if n not in target:
            raise SystemExit(f"source data is missing n={n}")
        verify(n, target[n])

    poly_cases = [polynomial_case(n, target[n]) for n in range(1, args.public_max_n + 1)]
    q1_cases = [q_equals_1_case(n, target[n]) for n in range(1, args.public_max_n + 1)]
    instance_cases = [instance_case(n) for n in range(1, args.instances_max_n + 1)]
    (data_dir / "polynomials.json").write_text(
        json.dumps(
            {"schema_version": "0.1", **identity, "variables": ["q", "t"],
             "known_statistic": "area",
             "source": "adjacent committed source_data records: published/cyclic n<=4, reported direct-computation n=5,6, conditional SL2-string completions n=7,8,9",
             "public_max_n": args.public_max_n, "case_count": len(poly_cases), "cases": poly_cases},
            indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )

    (data_dir / "q_equals_1.json").write_text(
        json.dumps(
            {"schema_version": "0.1", **identity, "variables": ["t"], "specialization": {"q": 1},
             "meaning": "Necessary one-variable distribution for the unknown partner statistic.",
             "public_max_n": args.public_max_n, "case_count": len(q1_cases), "cases": q1_cases},
            indent=2),
        encoding="utf-8", newline="\n",
    )

    (data_dir / "instances.json").write_text(
        json.dumps(
            {"schema_version": "0.1", **identity, "object_family": "type_b_catalan_paths",
             "known_statistic": "area", "instances_max_n": args.instances_max_n,
             "case_count": len(instance_cases), "cases": instance_cases},
            separators=(",", ":")),
        encoding="utf-8", newline="\n",
    )

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
