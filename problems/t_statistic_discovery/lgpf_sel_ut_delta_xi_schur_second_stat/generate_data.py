#!/usr/bin/env python3
"""Generate public data for the selected-area lattice gamma-parking problem.

The targets are the elementary coefficients

    Delta_{m_gamma} Xi s_lambda |_{q -> 1 + u} = sum_eta c_eta(u, t) e_eta

computed by the public oracle ``problems/t_statistic_discovery/
lgpf_sel_ut_delta_xi_schur_second_stat/delta_xi_schur_oracle.py``. Each
``c_eta`` is verified to lie in ``N[u, t]`` (Conjecture 13.1 of
arXiv:2203.10342) and to have its ``t = 1`` specialisation equal the u-graded
count of pairs ``(p, S)`` with ``eta(p) = eta``, where ``p`` runs over the
lattice gamma-parking functions of content ``lambda'``, which is Theorem 1.2
there. The scored evaluator never loads the oracle.

Enumeration streams one pair at a time, so peak memory stays small outside the
instance range.
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

from qtbench.combinatorics import iter_gamma_parking_selections
from qtbench.generation import load_trusted_oracle

LATTICE = True
OBJECT_FAMILY = "lattice_gamma_parking_selections"
SOURCE = (
    "Elementary coefficients of Delta_{m_gamma} Xi s_lambda at q = 1 + u "
    "(the lattice companion of Conjecture 13.2 of arXiv:2203.10342)"
)


def _load_oracle(problem_dir: Path):
    return load_trusted_oracle(problem_dir / "delta_xi_schur_oracle.py")


def _partitions(n: int, maxpart: int | None = None):
    if maxpart is None:
        maxpart = n
    if n == 0:
        yield ()
        return
    for part in range(min(n, maxpart), 0, -1):
        for rest in _partitions(n - part, part):
            yield (part, *rest)


def conjugate(lam: tuple[int, ...]) -> tuple[int, ...]:
    if not lam:
        return ()
    return tuple(sum(1 for part in lam if part >= i) for i in range(1, lam[0] + 1))


def content_of(lam: tuple[int, ...]) -> tuple[int, ...]:
    """The content of the objects indexed by the Schur/elementary index ``lam``."""
    return conjugate(lam) if LATTICE else lam


def case_id(gamma: tuple[int, ...], lam: tuple[int, ...]) -> str:
    gamma_text = "-".join(str(part) for part in gamma) if gamma else "0"
    lam_text = "-".join(str(part) for part in lam)
    return f"n{sum(lam):02d}_g{gamma_text}_l{lam_text}"


def _fibers(max_size: int):
    """Every ``(gamma, lam)`` with ``|lam| + |gamma| <= max_size``."""
    for n in range(1, max_size + 1):
        for lam in _partitions(n):
            for m in range(0, max_size - n + 1):
                for gamma in _partitions(m):
                    if len(gamma) <= n:
                        yield gamma, lam


def _enumerate_fiber(gamma, content, keep_entries: bool):
    """Stream the fiber once, binning pairs by ``(eta(p), #S)``."""
    pair_counter: Counter[tuple[tuple[int, ...], int]] = Counter()
    entries = []
    count = 0
    max_area = 0
    for obj in iter_gamma_parking_selections(gamma, content, lattice=LATTICE):
        selected = obj.selected_count()
        pair_counter[(obj.eta(), selected)] += 1
        max_area = max(max_area, obj.area())
        if keep_entries:
            entries.append({"object": obj.encoding, "sel": selected})
        count += 1
    return pair_counter, count, entries, max_area


def _coefficients(oracle, gamma, lam, max_area):
    """Interpolate the eta-graded target, widening the bound if it is too small."""
    bound = max_area + 2
    for _attempt in range(4):
        try:
            return oracle.e_coefficients(gamma, lam, bound)
        except ValueError as error:
            if "too small" not in str(error):
                raise
            bound += 3
    raise SystemExit(f"gamma={gamma} lam={lam}: interpolation bound never sufficed")


def verify(gamma, lam, target, pair_counter, count) -> None:
    label = f"gamma={gamma} lam={lam}"
    total = 0
    marginal: Counter[tuple[tuple[int, ...], int]] = Counter()
    for eta, poly in target.items():
        if any(value < 0 for value in poly.values()):
            raise SystemExit(f"{label}: c_{eta} has a negative coefficient")
        for (u, _t), value in poly.items():
            marginal[(eta, u)] += value
            total += value
    if {key: value for key, value in marginal.items() if value} != {
        key: value for key, value in pair_counter.items() if value
    }:
        raise SystemExit(f"{label}: c(t=1) does not match the u-graded pair count")
    if total != count:
        raise SystemExit(f"{label}: targets total {total} but the fiber has {count} pairs")


def polynomial_case(gamma, lam, content, target, count) -> dict:
    terms = []
    for eta in sorted(target):
        for (u, t) in sorted(target[eta]):
            if target[eta][(u, t)]:
                terms.append([list(eta), u, t, target[eta][(u, t)]])
    return {"case_id": case_id(gamma, lam), "n": sum(lam), "gamma": list(gamma),
            "lam": list(lam), "content": list(content), "count": count,
            "term_count": len(terms), "terms": terms}


def q_equals_1_case(gamma, lam, content, target, count) -> dict:
    marginal: Counter[tuple[tuple[int, ...], int]] = Counter()
    for eta, poly in target.items():
        for (_u, t), value in poly.items():
            marginal[(eta, t)] += value
    terms = [
        [list(eta), t, marginal[(eta, t)]]
        for eta, t in sorted(marginal)
        if marginal[(eta, t)]
    ]
    return {"case_id": case_id(gamma, lam), "n": sum(lam), "gamma": list(gamma),
            "lam": list(lam), "content": list(content), "count": count,
            "term_count": len(terms), "terms": terms}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate lattice gamma-parking u,t data.")
    parser.add_argument("--problem-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--public-max-size", type=int, default=5,
                        help="largest |lam| + |gamma| for the public polynomials")
    parser.add_argument("--instances-max-size", type=int, default=4,
                        help="instances.json lists every pair, so it is capped smaller")
    args = parser.parse_args()
    if args.public_max_size < 1:
        parser.error("--public-max-size must be positive")
    if not 1 <= args.instances_max_size <= args.public_max_size:
        parser.error(
            "--instances-max-size must be positive and no greater than "
            "--public-max-size"
        )

    problem_dir = args.problem_dir.resolve()
    metadata = json.loads((problem_dir / "metadata.json").read_text(encoding="utf-8"))
    identity = {"problem_id": int(metadata["id"]), "problem_name": str(metadata["name"])}
    expected_identity = {
        "problem_id": 20,
        "problem_name": "lgpf_sel_ut_delta_xi_schur_second_stat",
    }
    if identity != expected_identity:
        raise SystemExit(
            f"--problem-dir identifies {identity}, expected {expected_identity}"
        )
    oracle = _load_oracle(problem_dir)
    if oracle.PROBLEM_ID != identity["problem_id"] or oracle.PROBLEM_NAME != identity["problem_name"]:
        raise SystemExit("oracle PROBLEM_ID/PROBLEM_NAME do not match the problem metadata")

    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    poly_cases = []
    q1_cases = []
    instance_cases = []
    for gamma, lam in _fibers(args.public_max_size):
        content = content_of(lam)
        keep = sum(lam) + sum(gamma) <= args.instances_max_size
        pair_counter, count, entries, max_area = _enumerate_fiber(gamma, content, keep)
        target = _coefficients(oracle, gamma, lam, max_area)
        verify(gamma, lam, target, pair_counter, count)
        poly_cases.append(polynomial_case(gamma, lam, content, target, count))
        q1_cases.append(q_equals_1_case(gamma, lam, content, target, count))
        if keep:
            instance_cases.append({"case_id": case_id(gamma, lam), "n": sum(lam),
                                   "gamma": list(gamma), "lam": list(lam),
                                   "content": list(content), "count": count,
                                   "entries": entries})
        print(f"verified gamma={gamma} lam={lam}: pairs={count}", flush=True)

    (data_dir / "polynomials.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "variables": ["partition", "u", "t"],
                    "known_statistic": "sel", "source": SOURCE,
                    "public_max_size": args.public_max_size,
                    "case_count": len(poly_cases), "cases": poly_cases}, indent=2),
        encoding="utf-8", newline="\n")

    (data_dir / "q_equals_1.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "variables": ["partition", "t"], "specialization": {"u": 1},
                    "meaning": "Necessary eta-graded distribution for the unknown t-statistic.",
                    "public_max_size": args.public_max_size,
                    "case_count": len(q1_cases), "cases": q1_cases}, indent=2),
        encoding="utf-8", newline="\n")

    (data_dir / "instances.json").write_text(
        json.dumps({"schema_version": "0.1", **identity,
                    "object_family": OBJECT_FAMILY, "known_statistic": "sel",
                    "instances_max_size": args.instances_max_size,
                    "case_count": len(instance_cases), "cases": instance_cases},
                   separators=(",", ":")), encoding="utf-8", newline="\n")

    for name in ("polynomials.json", "q_equals_1.json", "instances.json"):
        print(f"wrote {data_dir / name}")


if __name__ == "__main__":
    main()
