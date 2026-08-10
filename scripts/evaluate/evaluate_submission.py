#!/usr/bin/env python3
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.evaluation import (
    UnsupportedDiagnosticProblemError,
    evaluate_submission_file,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Non-scoring diagnostic for trusted Problem 1 submissions; executes "
            "Python with the caller's privileges. Other problems require the "
            "scored evaluator and their dedicated evaluator kind."
        )
    )
    parser.add_argument(
        "problem_dir",
        type=Path,
        help="Problem 1 directory: problems/t_statistic_discovery/nc_area_qt_narayana_second_stat",
    )
    parser.add_argument("submission", type=Path, help="Python file defining statistic(partition) -> int")
    parser.add_argument(
        "--q-equals-1",
        action="store_true",
        help="Check the public q=1 marginal distribution instead of the full public q,t-polynomials.",
    )
    parser.add_argument("--function-name", default="statistic", help="Submission function name. Default: statistic")
    parser.add_argument(
        "--format",
        choices=["summary", "json"],
        default="summary",
        help="Output format. Default: summary.",
    )
    parser.add_argument("--json", action="store_true", help="Alias for --format json.")
    return parser.parse_args()


def _format_exponents(exponents: dict) -> str:
    return ", ".join(f"{name}={value}" for name, value in exponents.items())


def _problem_label(result: dict) -> str:
    problem_name = result.get("problem_name") or "unknown_problem"
    problem_id = result.get("problem_id")
    return f"{problem_name} (id {problem_id})" if problem_id is not None else problem_name


def _print_public_summary(result: dict) -> None:
    failed = [case for case in result["case_results"] if not case["correct"]]
    total_l1 = sum(case["l1_distance"] for case in result["case_results"])
    print(
        f"{_problem_label(result)} [{result['split']}]: "
        f"{result['correct_cases']}/{result['total_cases']} cases correct, total L1={total_l1}"
    )
    if not failed:
        print("All checked coefficient distributions match.")
        return

    shown_cases = failed[:10]
    print(f"Mismatching cases shown: {len(shown_cases)}/{len(failed)}")
    for case in shown_cases:
        print(
            f"- {case['case_id']} (n={case['n']}, k={case['k']}): "
            f"L1={case['l1_distance']}, mismatches={case['mismatch_count']}"
        )
        for mismatch in case["mismatches"][:8]:
            print(
                "  "
                f"{_format_exponents(mismatch['exponents'])}: "
                f"generated={mismatch['generated_coeff']}, "
                f"expected={mismatch['expected_coeff']}, "
                f"diff={mismatch['difference']}"
            )
        remaining = case["mismatch_count"] - min(case["mismatch_count"], 8)
        if remaining:
            print(f"  ... {remaining} more term mismatches")
    if len(failed) > len(shown_cases):
        print(f"... {len(failed) - len(shown_cases)} more mismatching cases")


def print_summary(result: dict) -> None:
    _print_public_summary(result)


def main() -> None:
    args = parse_args()
    # Submission files are intentionally unrestricted in this diagnostic tool
    # and may print while being imported or evaluated.  Keep stdout reserved
    # for the selected report format so ``--format json`` remains valid JSON.
    try:
        with redirect_stdout(sys.stderr):
            result = evaluate_submission_file(
                problem_dir=args.problem_dir,
                submission_path=args.submission,
                check_q_equals_1=args.q_equals_1,
                function_name=args.function_name,
            )
    except UnsupportedDiagnosticProblemError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    if args.json or args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print_summary(result)
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
