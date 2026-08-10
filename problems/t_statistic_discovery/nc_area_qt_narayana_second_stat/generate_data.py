#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.combinatorics import (
    canonical_terms,
    enumerate_narayana_partitions,
    joint_distribution,
    narayana_number,
)
from qtbench.evaluation import load_statistic_function


def case_id(n: int, k: int) -> str:
    return f"n{n:02d}_k{k:02d}"


def public_cases(max_n: int) -> list[tuple[int, int]]:
    return [(n, k) for n in range(1, max_n + 1) for k in range(1, n + 1)]


def build_polynomial_case(n: int, k: int, statistic) -> dict:
    partitions = enumerate_narayana_partitions(n, k)
    expected = narayana_number(n, k)
    if len(partitions) != expected:
        raise RuntimeError(f"enumeration mismatch for n={n}, k={k}: got {len(partitions)}, expected {expected}")
    counter = joint_distribution(partitions, lambda partition: partition.area(), statistic)
    terms = canonical_terms(counter)
    return {
        "case_id": case_id(n, k),
        "n": n,
        "k": k,
        "count": len(partitions),
        "term_count": len(terms),
        "terms": terms,
    }


def public_polynomial_case(case: dict) -> dict:
    return {
        "case_id": case["case_id"],
        "n": case["n"],
        "k": case["k"],
        "count": case["count"],
        "term_count": case["term_count"],
        "terms": case["terms"],
    }


def q_equals_1_case(case: dict) -> dict:
    specialization: Counter[int] = Counter()
    for _, t_exponent, coefficient in case["terms"]:
        specialization[int(t_exponent)] += int(coefficient)
    terms = [[degree, specialization[degree]] for degree in sorted(specialization) if specialization[degree]]
    return {
        "case_id": case["case_id"],
        "n": case["n"],
        "k": case["k"],
        "count": case["count"],
        "term_count": len(terms),
        "terms": terms,
    }


def problem_identity(problem_dir: Path) -> dict:
    metadata_path = problem_dir / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"problem metadata is required for numeric id and name: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return {
        "problem_id": int(metadata["id"]),
        "problem_name": str(metadata["name"]),
    }


def build_instance_case(n: int, k: int) -> dict:
    entries = []
    for partition in enumerate_narayana_partitions(n, k):
        entries.append(
            {
                "partition": partition.to_jsonable(),
                "area": partition.area(),
            }
        )
    entries.sort(key=lambda item: tuple((block[0], len(block), tuple(block)) for block in item["partition"]))
    return {
        "case_id": case_id(n, k),
        "n": n,
        "k": k,
        "count": len(entries),
        "entries": entries,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate public data for a qtBench problem.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument(
        "--statistic-module",
        type=Path,
        help="trusted local oracle module executed with caller privileges and "
        "defining statistic(partition); defaults to <problem-dir>/oracle.py",
    )
    parser.add_argument("--public-max-n", type=int, default=10)
    args = parser.parse_args()
    if args.public_max_n < 1:
        parser.error("--public-max-n must be positive")
    return args


def main() -> None:
    args = parse_args()
    problem_dir = args.problem_dir.resolve()
    identity = problem_identity(problem_dir)
    expected_identity = {
        "problem_id": 1,
        "problem_name": "nc_area_qt_narayana_second_stat",
    }
    if identity != expected_identity:
        raise SystemExit(
            f"--problem-dir identifies {identity}, expected {expected_identity}"
        )
    statistic_module = (
        args.statistic_module.resolve()
        if args.statistic_module is not None
        else problem_dir / "oracle.py"
    )
    statistic = load_statistic_function(statistic_module)
    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    cases = public_cases(args.public_max_n)
    full_polynomial_cases = [build_polynomial_case(n, k, statistic) for n, k in cases]
    polynomial_cases = [public_polynomial_case(case) for case in full_polynomial_cases]
    polynomial_data = {
        "schema_version": "0.1",
        **identity,
        "variables": ["q", "t"],
        "known_statistic": "area",
        "public_max_n": args.public_max_n,
        "case_count": len(polynomial_cases),
        "cases": polynomial_cases,
    }

    q_equals_1_cases = [q_equals_1_case(case) for case in full_polynomial_cases]
    q_equals_1_data = {
        "schema_version": "0.1",
        **identity,
        "variables": ["t"],
        "specialization": {"q": 1},
        "meaning": "Necessary one-variable distribution for the unknown t-statistic.",
        "public_max_n": args.public_max_n,
        "case_count": len(q_equals_1_cases),
        "cases": q_equals_1_cases,
    }

    instance_cases = [build_instance_case(n, k) for n, k in cases]
    instance_data = {
        "schema_version": "0.1",
        **identity,
        "object_family": "noncrossing_partitions",
        "known_statistic": "area",
        "public_max_n": args.public_max_n,
        "case_count": len(instance_cases),
        "cases": instance_cases,
    }
    (data_dir / "polynomials.json").write_text(
        json.dumps(polynomial_data, indent=2), encoding="utf-8", newline="\n"
    )
    (data_dir / "q_equals_1.json").write_text(
        json.dumps(q_equals_1_data, indent=2), encoding="utf-8", newline="\n"
    )
    (data_dir / "instances.json").write_text(json.dumps(instance_data, separators=(",", ":")), encoding="utf-8", newline="\n")

    print(f"wrote {data_dir / 'polynomials.json'}")
    print(f"wrote {data_dir / 'q_equals_1.json'}")
    print(f"wrote {data_dir / 'instances.json'}")


if __name__ == "__main__":
    main()
