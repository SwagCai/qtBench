from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from qtbench.combinatorics import (
    iter_parallelogram_polyominoes,
    polyomino_area,
    polyomino_bounce,
    polyomino_count,
)
from qtbench.evaluation import (
    adversarial_polyomino_probes,
    evaluate_polyomino_transpose_submission,
    load_polyomino_area_bounce_terms,
)
from qtbench.evaluation.admission import evaluate_polyomino_transpose_bijection

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "exchanging_bijection" / "polyomino_area_bounce_transpose"
PROBLEM_ID = 5
PROBLEM_NAME = "polyomino_area_bounce_transpose"


def test_public_polynomial_file_schema():
    assert {path.name for path in (PROBLEM / "data").glob("*.json")} == {
        "instances.json",
        "polynomials.json",
        "q_equals_1.json",
    }
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    assert data["variables"] == ["q", "t"]
    for case in data["cases"]:
        assert case["count"] == polyomino_count(case["m"], case["n"])
        assert case["term_count"] == len(case["terms"])


def test_targets_are_symmetric_in_the_bounding_box():
    data = json.loads((PROBLEM / "data" / "polynomials.json").read_text())
    by_box = {(case["m"], case["n"]): {(a, b): c for a, b, c in case["terms"]} for case in data["cases"]}
    for (m, n), expected in by_box.items():
        # the transpose symmetry Nara_{m,n} = Nara_{n,m} the bijection must realize
        assert expected == by_box[(n, m)]


def test_known_statistics_match_public_instances():
    spec = importlib.util.spec_from_file_location("known_stats", PROBLEM / "known_statistics.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = json.loads((PROBLEM / "data" / "instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            assert module.area(entry["polyomino"]) == entry["area"]
            assert module.bounce(entry["polyomino"]) == entry["bounce"]


def _build_transpose(max_sum):
    """A correct area/bounce-preserving bijection Polyo_{m,n} <-> Polyo_{n,m}."""
    fmap = {}
    done = set()
    for total in range(2, max_sum + 1):
        for m in range(1, total):
            n = total - m
            if (m, n) in done:
                continue
            if m == n:
                for e in iter_parallelogram_polyominoes(m, n):
                    fmap[e] = e
                done.add((m, n))
                continue
            here = {}
            for e in iter_parallelogram_polyominoes(m, n):
                here.setdefault((polyomino_area(e), polyomino_bounce(e)), []).append(e)
            there = {}
            for e in iter_parallelogram_polyominoes(n, m):
                there.setdefault((polyomino_area(e), polyomino_bounce(e)), []).append(e)
            for key, lst in here.items():
                partners = there[key]
                assert len(partners) == len(lst)
                for e, o in zip(lst, partners):
                    fmap[e] = o
                    fmap[o] = e
            done.add((m, n))
            done.add((n, m))
    return fmap


def test_correct_transpose_bijection_is_accepted():
    max_sum = 8
    fmap = _build_transpose(max_sum)
    forward = lambda e: fmap[e]  # involution => inverse == forward
    target = load_polyomino_area_bounce_terms(PROBLEM)
    target = {box: terms for box, terms in target.items() if box[0] + box[1] <= max_sum}
    result = evaluate_polyomino_transpose_bijection(forward, forward, target)
    assert result["passed"], [c for c in result["case_results"] if not c["correct"]][:2]


def test_identity_map_is_rejected_end_to_end():
    identity = "def forward(p):\n    return p\n\ndef inverse(p):\n    return p\n"
    result = evaluate_polyomino_transpose_submission(
        source=identity,
        probes=lambda: adversarial_polyomino_probes(64),
        target_terms=load_polyomino_area_bounce_terms(PROBLEM),
        timeout_seconds=2.0,
        numerical_timeout_seconds=8.0,
        max_python_bytes=32_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"
