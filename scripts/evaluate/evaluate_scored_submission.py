#!/usr/bin/env python3
"""Run the full admission checks on a submission.

Passing is a necessary, not sufficient, condition for a real result: see
docs/checker.md.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qtbench.evaluation import (
    CHECKER_VERSION,
    GateError,
    ResourceGateError,
    SourceLimits,
    adversarial_ddyck_probes,
    adversarial_asm_probes,
    adversarial_connected_graph_probes,
    adversarial_shifted_pq_probes,
    adversarial_successive_rank_probes,
    adversarial_partition_matrix_inversion_probes,
    adversarial_dyck_probes,
    adversarial_gpf_probes,
    adversarial_involution_probes,
    adversarial_kostka_probes,
    adversarial_lgpf_probes,
    adversarial_llt_probes,
    adversarial_lpp_probes,
    adversarial_lrp_probes,
    adversarial_mjack_probes,
    adversarial_mld_probes,
    adversarial_macdonald_filling_probes,
    adversarial_parking_function_probes,
    adversarial_noncrossing_probes,
    adversarial_polyomino_probes,
    adversarial_promotion_probes,
    adversarial_qgamma_probes,
    adversarial_rtt_probes,
    adversarial_tgt_probes,
    adversarial_tamari_probes,
    adversarial_ttree_probes,
    adversarial_type_b_probes,
    adversarial_uig_probes,
    evaluate_area_bounce_submission,
    evaluate_asm_q_submission,
    evaluate_ddyck_submission,
    evaluate_gpf_submission,
    evaluate_graph_sibling_tuft_submission,
    evaluate_shifted_pq_submission,
    evaluate_successive_rank_submission,
    evaluate_partition_matrix_inversion_submission,
    evaluate_involution_submission,
    evaluate_kostka_submission,
    evaluate_kreweras_submission,
    evaluate_lgpf_submission,
    evaluate_llt_submission,
    evaluate_lpp_submission,
    evaluate_lrp_submission,
    evaluate_mjack_submission,
    evaluate_mld_submission,
    evaluate_macdonald_filling_submission,
    evaluate_parking_area_dinv_submission,
    evaluate_noncrossing_submission,
    evaluate_polyomino_area_bounce_submission,
    evaluate_polyomino_transpose_submission,
    evaluate_promotion_submission,
    evaluate_qgamma_submission,
    evaluate_rtt_submission,
    evaluate_tamari_submission,
    evaluate_tgt_submission,
    evaluate_ttree_submission,
    evaluate_type_b_submission,
    evaluate_uig_submission,
    load_area_bounce_terms,
    load_graph_sibling_tuft_terms,
    load_shifted_pq_cases,
    load_successive_rank_cases,
    load_partition_matrix_inversion_cases,
    load_macdonald_filling_terms,
    load_parking_area_dinv_terms,
    load_polyomino_area_bounce_terms,
)
from qtbench.evaluation.admission import _aggregate_process_budget


DEFAULT_PROBLEM = {
    "noncrossing": ROOT / "problems/t_statistic_discovery/nc_area_qt_narayana_second_stat",
    "type-b": ROOT / "problems/t_statistic_discovery/type_b_area_qt_catalan_second_stat",
    "lpp": ROOT / "problems/t_statistic_discovery/lpp_area_qt_theta_second_stat",
    "ddyck": ROOT / "problems/t_statistic_discovery/ddyck_area_qt_unified_delta_second_stat",
    "lrp": ROOT / "problems/t_statistic_discovery/lrp_area_qt_rectangular_delta_second_stat",
    "mld": ROOT / "problems/t_statistic_discovery/mld_area_qt_super_nabla_second_stat",
    "tamari": ROOT / "problems/t_statistic_discovery/tamari_park_trivariate_third_stat",
    "ttree": ROOT / "problems/t_statistic_discovery/ttree_inv_qt_xi_second_stat",
    "gpf": ROOT / "problems/t_statistic_discovery/gpf_sel_ut_delta_xi_second_stat",
    "rtt": ROOT / "problems/t_statistic_discovery/rtt_inv_qt_theta_second_stat",
    "lgpf": ROOT / "problems/t_statistic_discovery/lgpf_sel_ut_delta_xi_schur_second_stat",
    "tgt": ROOT / "problems/t_statistic_discovery/tgt_inv_qt_ehrhart_second_stat",
    "kostka": ROOT / "problems/t_statistic_discovery/syt_qt_kostka_macdonald_pair_stat",
    "uig": ROOT / "problems/q_statistic_discovery/uig_ginv_shareshian_wachs_q_stat",
    "llt": ROOT / "problems/q_statistic_discovery/uig_syt_llt_schur_q_stat",
    "involution": ROOT / "problems/q_statistic_discovery/inv_orbit_harmonics_hilbert_q_stat",
    "mjack": ROOT / "problems/q_statistic_discovery/match_jack_connection_q_stat",
    "qgamma": ROOT / "problems/q_statistic_discovery/perm_q_eulerian_gamma_q_stat",
    "promotion": ROOT / "problems/q_statistic_discovery/syt_promotion_csp_q_stat",
    "kreweras": ROOT / "problems/q_statistic_discovery/nc_q_kreweras_q_stat",
    "area-bounce": ROOT / "problems/exchanging_bijection/dyck_area_bounce_exchange",
    "polyomino-area-bounce": ROOT / "problems/exchanging_bijection/polyomino_area_bounce_exchange",
    "polyomino-transpose": ROOT / "problems/exchanging_bijection/polyomino_area_bounce_transpose",
    "macdonald-fillings": ROOT / "problems/exchanging_bijection/macdonald_fillings_inv_maj_exchange",
    "parking-area-dinv": ROOT / "problems/exchanging_bijection/parking_area_dinv_exchange",
    "graph-sibling-tuft": ROOT / "problems/exchanging_bijection/graph_sibling_tuft_exchange",
    "shifted-pq": ROOT / "problems/exchanging_bijection/shifted_setvalued_pq_weight_bijection",
    "successive-rank": ROOT / "problems/exchanging_bijection/andrews_bressoud_successive_rank_bijection",
    "partition-matrix-inversion": ROOT / "problems/exchanging_bijection/improper_partition_matrix_inversion_sequence_bijection",
    "asm-q": ROOT / "problems/q_statistic_discovery/asm_dpp_weight_q_stat",
}

STATISTIC_RUNNERS = {
    "noncrossing": (evaluate_noncrossing_submission, adversarial_noncrossing_probes),
    "type-b": (evaluate_type_b_submission, adversarial_type_b_probes),
    "lpp": (evaluate_lpp_submission, adversarial_lpp_probes),
    "ddyck": (evaluate_ddyck_submission, adversarial_ddyck_probes),
    "lrp": (evaluate_lrp_submission, adversarial_lrp_probes),
    "mld": (evaluate_mld_submission, adversarial_mld_probes),
    "tamari": (evaluate_tamari_submission, adversarial_tamari_probes),
    "ttree": (evaluate_ttree_submission, adversarial_ttree_probes),
    "gpf": (evaluate_gpf_submission, adversarial_gpf_probes),
    "rtt": (evaluate_rtt_submission, adversarial_rtt_probes),
    "lgpf": (evaluate_lgpf_submission, adversarial_lgpf_probes),
    "tgt": (evaluate_tgt_submission, adversarial_tgt_probes),
    "kostka": (evaluate_kostka_submission, adversarial_kostka_probes),
    "uig": (evaluate_uig_submission, adversarial_uig_probes),
    "llt": (evaluate_llt_submission, adversarial_llt_probes),
    "involution": (evaluate_involution_submission, adversarial_involution_probes),
    "mjack": (evaluate_mjack_submission, adversarial_mjack_probes),
    "qgamma": (evaluate_qgamma_submission, adversarial_qgamma_probes),
    "promotion": (evaluate_promotion_submission, adversarial_promotion_probes),
    "kreweras": (evaluate_kreweras_submission, adversarial_noncrossing_probes),
    "asm-q": (evaluate_asm_q_submission, adversarial_asm_probes),
}

BIJECTION_RUNNERS = {
    "area-bounce": (
        evaluate_area_bounce_submission,
        adversarial_dyck_probes,
        load_area_bounce_terms,
    ),
    "polyomino-area-bounce": (
        evaluate_polyomino_area_bounce_submission,
        adversarial_polyomino_probes,
        load_polyomino_area_bounce_terms,
    ),
    "polyomino-transpose": (
        evaluate_polyomino_transpose_submission,
        adversarial_polyomino_probes,
        load_polyomino_area_bounce_terms,
    ),
    "macdonald-fillings": (
        evaluate_macdonald_filling_submission,
        adversarial_macdonald_filling_probes,
        load_macdonald_filling_terms,
    ),
    "parking-area-dinv": (
        evaluate_parking_area_dinv_submission,
        adversarial_parking_function_probes,
        load_parking_area_dinv_terms,
    ),
    "graph-sibling-tuft": (
        evaluate_graph_sibling_tuft_submission,
        adversarial_connected_graph_probes,
        load_graph_sibling_tuft_terms,
    ),
    "shifted-pq": (
        evaluate_shifted_pq_submission,
        adversarial_shifted_pq_probes,
        load_shifted_pq_cases,
    ),
    "successive-rank": (
        evaluate_successive_rank_submission,
        adversarial_successive_rank_probes,
        load_successive_rank_cases,
    ),
    "partition-matrix-inversion": (
        evaluate_partition_matrix_inversion_submission,
        adversarial_partition_matrix_inversion_probes,
        load_partition_matrix_inversion_cases,
    ),
}

NON_AUTOMATIC_REASONS: dict[str, str] = {}


class ExpertReviewRequired(GateError):
    """The selected problem intentionally has no automatic admission verdict."""


MAX_SUBMISSION_INPUT_BYTES = 1_000_000
OFFICIAL_SOURCE_LIMITS = SourceLimits()
OFFICIAL_SCORING_CONFIG = {
    "version": 3,
    "checker_version": CHECKER_VERSION,
    "probe_n": 1024,
    "probe_timeout_seconds": 2.0,
    # Statistic numerical/replay budget; bijections use a separate profile below.
    "numerical_timeout_seconds": 60.0,
    # The tighter traced-allocation cap applies to adversarial resource and
    # identity probes. Numerical replay includes trusted exhaustive-enumerator
    # overhead, so admission.py uses the process ceiling for that stage.
    "max_python_bytes": 32_000_000,
    # Official isolated execution reserves 192 MiB for one worker and 64 MiB
    # for the evaluator parent inside a 256 MiB aggregate process envelope.
    "max_process_bytes": 201_326_592,
    "max_parent_process_bytes": 67_108_864,
    "max_aggregate_process_bytes": 268_435_456,
    "max_submission_input_bytes": MAX_SUBMISSION_INPUT_BYTES,
    "source_limits": asdict(OFFICIAL_SOURCE_LIMITS),
}
BIJECTION_SCORING_CONFIG = {
    **OFFICIAL_SCORING_CONFIG,
    "version": 4,
    "numerical_timeout_seconds": 480.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the qtBench admission checks.")
    parser.add_argument(
        "kind",
        choices=tuple(DEFAULT_PROBLEM),
    )
    parser.add_argument("submission", type=Path)
    parser.add_argument(
        "--format",
        choices=("summary", "json"),
        default="summary",
        help="'summary' prints a short human-readable report; 'json' prints the "
        "complete machine-readable result, including every public case",
    )
    return parser.parse_args()


def _read_submission_source(path: Path) -> str:
    """Read one bounded regular file without a path-level stat/read race."""

    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise GateError("capability screen: submission must be a regular file")
        if opened.st_size > MAX_SUBMISSION_INPUT_BYTES:
            raise GateError("capability screen: source exceeds the 1 MB hard limit")

        chunks = []
        remaining = MAX_SUBMISSION_INPUT_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        source_bytes = b"".join(chunks)
        if len(source_bytes) > MAX_SUBMISSION_INPUT_BYTES:
            raise GateError("capability screen: source exceeds the 1 MB hard limit")
        return source_bytes.decode("utf-8")
    finally:
        os.close(descriptor)


def _target_bundle_sha256(problem_dir: Path) -> str:
    """Hash the published identity and data bundle selected by the problem kind."""

    paths = [problem_dir / "metadata.json"]
    paths.extend(
        path for path in sorted((problem_dir / "data").rglob("*")) if path.is_file()
    )
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(problem_dir).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with path.open("rb") as handle:
            while chunk := handle.read(65_536):
                digest.update(chunk)
    return digest.hexdigest()


def _repository_provenance() -> dict[str, Any]:
    """Return an informational Git receipt when the checker runs from a checkout."""

    try:
        revision = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        status = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "status",
                "--porcelain",
                "--untracked-files=normal",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {"repository_commit": None, "repository_dirty": None}
    if len(revision) != 40 or any(
        character not in "0123456789abcdef" for character in revision
    ):
        return {"repository_commit": None, "repository_dirty": None}
    return {"repository_commit": revision, "repository_dirty": bool(status)}


def _problem_provenance(problem_dir: Path, evaluator_kind: str) -> dict[str, Any]:
    """Return stable public problem identity even for an early gate failure."""

    identity: dict[str, Any] = {
        "problem_id": None,
        "problem_name": problem_dir.name,
        "evaluator_kind": evaluator_kind,
    }
    try:
        metadata = json.loads(
            (problem_dir / "metadata.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return identity
    if not isinstance(metadata, dict):
        return identity
    if type(metadata.get("id")) is int and metadata["id"] > 0:
        identity["problem_id"] = metadata["id"]
    if isinstance(metadata.get("name"), str) and metadata["name"]:
        identity["problem_name"] = metadata["name"]
    return identity


def _jsonable(value):
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _split_line(label: str, split: Mapping[str, Any]) -> str:
    mark = "pass" if split["passed"] else "FAIL"
    line = f"  {label:<12} {mark}  {split['correct_cases']}/{split['total_cases']} cases"
    if split["passed"]:
        return line
    failed = next(
        (case for case in split.get("case_results", ()) if not case["correct"]), None
    )
    if failed is not None:
        line += f"; first wrong case {failed['case_id']}"
    return line


def _summary_text(value: Any) -> str:
    """Render untrusted error text on one encoding-safe terminal line."""

    return str(value).encode("unicode_escape", "backslashreplace").decode("ascii")


def _summary_lines(result: Mapping[str, Any]) -> list[str]:
    """Render the report a reader wants at a glance.

    The full result carries one entry per public case, which runs to tens of
    thousands of lines on the larger problems.  ``--format json`` still emits
    all of it; this view exists so that the common case fits on a screen.
    """

    if result.get("expert_review_required"):
        verdict = "EXPERT REVIEW REQUIRED"
    else:
        verdict = "PASSED" if result["passed"] else "did not pass"
    lines = [f"{verdict} (stopped at: {result['checker_stage']})"]
    provenance = result.get("provenance", {})
    if provenance.get("problem_name"):
        identity = provenance["problem_name"]
        if provenance.get("problem_id") is not None:
            identity += f" (id {provenance['problem_id']})"
        if provenance.get("evaluator_kind"):
            identity += f", kind {provenance['evaluator_kind']}"
        lines.append(f"  problem      {identity}")
    lines.extend(
        [
            "  scoring      official "
            f"(fixed configuration v{OFFICIAL_SCORING_CONFIG['version']})",
            f"  run seed     {result['run_seed']}",
        ]
    )
    if "review_reason" in result:
        lines.append(f"  review       {_summary_text(result['review_reason'])}")
        lines.append("  verdict      no automatic admission verdict was issued")
        return lines
    if "gate_error" in result:
        lines.append(f"  gate error   {_summary_text(result['gate_error'])}")
        return lines
    lines.append(f"  functions    {', '.join(result.get('function_names', ()))}")

    numerical = result.get("numerical")
    if numerical is not None:
        if "case_results" in numerical:  # bijection shape
            cases = numerical["case_results"]
            correct = sum(1 for case in cases if case["correct"])
            lines.append(_split_line("identities", {
                "passed": numerical["passed"],
                "correct_cases": correct,
                "total_cases": len(cases),
                "case_results": [
                    {
                        "correct": case["correct"],
                        "case_id": (
                            case["case_id"]
                            if "case_id" in case
                            else f"shape={case['shape']}"
                            if "shape" in case
                            else f"box=({case['m']},{case['n']})"
                            if "m" in case
                            else f"n={case['n']}"
                        ),
                    }
                    for case in cases
                ],
            }))
            failed = next((case for case in cases if not case["correct"]), None)
            if failed is not None and failed.get("first_failure"):
                lines.append(f"               {failed['first_failure']}")
        else:
            for label, key in (("q=1 marginal", "q_equals_1"), ("full target", "full_qt")):
                if key in numerical:
                    lines.append(_split_line(label, numerical[key]))

    determinism = result.get("determinism")
    if determinism is not None:
        lines.append(
            f"  replay       pass  {determinism.checked_objects} objects, "
            f"{determinism.fresh_namespaces} namespaces, seed {determinism.replay_seed}"
        )
    if result.get("resources") is not None:
        lines.append("  resources    pass")
    lines.append("")
    lines.append("Passing every stage is a necessary, not a sufficient, condition")
    lines.append("for a genuine mathematical solution; see docs/checker.md.")
    lines.append("Re-run with --format json for the complete per-case result.")
    return lines


def main() -> None:
    args = parse_args()
    scoring_config = (
        BIJECTION_SCORING_CONFIG
        if args.kind in BIJECTION_RUNNERS
        else OFFICIAL_SCORING_CONFIG
    )
    run_seed = secrets.randbits(128)
    os.environ["QTBENCH_RUN_SEED"] = str(run_seed)
    os.environ.pop("QTBENCH_REPLAY_SEED", None)
    problem_dir = DEFAULT_PROBLEM[args.kind]
    provenance = {
        **_problem_provenance(problem_dir, args.kind),
        **_repository_provenance(),
        "target_bundle_sha256": None,
        "submission_sha256": None,
    }
    common = {
        "source": "",
        "timeout_seconds": scoring_config["probe_timeout_seconds"],
        "numerical_timeout_seconds": scoring_config[
            "numerical_timeout_seconds"
        ],
        "max_python_bytes": scoring_config["max_python_bytes"],
        "max_process_bytes": scoring_config["max_process_bytes"],
        "limits": OFFICIAL_SOURCE_LIMITS,
    }
    try:
        with _aggregate_process_budget(
            max_parent_process_bytes=OFFICIAL_SCORING_CONFIG[
                "max_parent_process_bytes"
            ],
            max_aggregate_process_bytes=OFFICIAL_SCORING_CONFIG[
                "max_aggregate_process_bytes"
            ],
        ):
            provenance["target_bundle_sha256"] = _target_bundle_sha256(problem_dir)
            if args.kind in NON_AUTOMATIC_REASONS:
                raise ExpertReviewRequired(NON_AUTOMATIC_REASONS[args.kind])
            common["source"] = _read_submission_source(args.submission)
            provenance["submission_sha256"] = hashlib.sha256(
                common["source"].encode("utf-8")
            ).hexdigest()
            if args.kind in STATISTIC_RUNNERS:
                evaluate, make_probes = STATISTIC_RUNNERS[args.kind]
                result = evaluate(
                    **common,
                    probes=lambda: make_probes(
                        OFFICIAL_SCORING_CONFIG["probe_n"], seed=run_seed
                    ),
                    problem_dir=problem_dir,
                )
            else:
                evaluate, make_probes, load_terms = BIJECTION_RUNNERS[args.kind]
                result = evaluate(
                    **common,
                    probes=lambda: make_probes(
                        scoring_config["probe_n"], seed=run_seed
                    ),
                    target_terms=load_terms(problem_dir),
                )
    except ExpertReviewRequired as error:
        failure = {
            "passed": False,
            "automatic_verdict": None,
            "expert_review_required": True,
            "checker_stage": "expert_review",
            "checker_version": CHECKER_VERSION,
            "run_seed": run_seed,
            "scoring_mode": "official",
            "scoring_config": dict(scoring_config),
            "provenance": provenance,
            "review_reason": str(error),
        }
        if args.format == "json":
            print(json.dumps(failure, indent=2))
        else:
            print("\n".join(_summary_lines(failure)))
        raise SystemExit(1) from error
    except (GateError, ResourceGateError, OSError, ValueError) as error:
        failure = {
            "passed": False,
            "automatic_verdict": False,
            "expert_review_required": False,
            "checker_stage": "gate_error",
            "checker_version": CHECKER_VERSION,
            "run_seed": run_seed,
            "scoring_mode": "official",
            "scoring_config": dict(scoring_config),
            "provenance": provenance,
            "gate_error": str(error),
        }
        if args.format == "json":
            print(json.dumps(failure, indent=2))
        else:
            print("\n".join(_summary_lines(failure)))
        raise SystemExit(1) from error
    result["run_seed"] = run_seed
    result["automatic_verdict"] = bool(result["passed"])
    result["expert_review_required"] = False
    result["scoring_mode"] = "official"
    result["scoring_config"] = dict(scoring_config)
    result["provenance"] = provenance
    if args.format == "json":
        print(json.dumps(_jsonable(result), indent=2))
    else:
        print("\n".join(_summary_lines(result)))
    raise SystemExit(0 if result["passed"] else 1)

if __name__ == "__main__":
    main()
