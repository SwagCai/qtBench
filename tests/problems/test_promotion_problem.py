from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from qtbench.combinatorics import (
    iter_promotion_tableaux_for_shape,
    promotion_modulus,
)
from qtbench.evaluation import (
    adversarial_promotion_probes,
    adversarial_promotion_tableaux,
    evaluate_promotion_polynomial_checks,
    evaluate_promotion_submission,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "q_statistic_discovery" / "syt_promotion_csp_q_stat"
PROBLEM_ID = 22
PROBLEM_NAME = "syt_promotion_csp_q_stat"


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def _coefficients(case) -> dict[int, int]:
    return {int(degree): int(value) for degree, value in case["terms"]}


# ---------------------------------------------------------------------------
# An independent rebuild: promotion orbits, computed here from scratch
# ---------------------------------------------------------------------------


def _promote(rows):
    """Promotion as the composition of Bender-Knuth involutions ``t_1 ... t_{n-1}``.

    Deliberately *not* the jeu-de-taquin definition the oracle uses: ``t_i`` swaps the
    entries ``i`` and ``i + 1`` when they share neither a row nor a column, and their
    composition is promotion. Agreeing with the oracle is then evidence about the
    orbits rather than a restatement of one implementation.
    """
    position = {value: (r, c) for r, row in enumerate(rows) for c, value in enumerate(row)}
    grid = [list(row) for row in rows]
    for value in range(1, len(position)):
        (r1, c1), (r2, c2) = position[value], position[value + 1]
        if r1 != r2 and c1 != c2:
            grid[r1][c1], grid[r2][c2] = value + 1, value
            position[value], position[value + 1] = (r2, c2), (r1, c1)
    return tuple(tuple(row) for row in grid)


def _orbit_polynomial(shape) -> tuple[dict[int, int], list[int]]:
    tableaux = [obj.rows for obj in iter_promotion_tableaux_for_shape(shape)]
    modulus = promotion_modulus(shape)
    index = {rows: position for position, rows in enumerate(tableaux)}
    image = [index[_promote(rows)] for rows in tableaux]
    assert sorted(image) == list(range(len(tableaux)))       # promotion is a bijection
    seen = [False] * len(tableaux)
    sizes = []
    for start in range(len(tableaux)):
        if seen[start]:
            continue
        size, node = 0, start
        while not seen[node]:
            seen[node] = True
            node = image[node]
            size += 1
        sizes.append(size)
    coefficients: Counter[int] = Counter()
    for size in sizes:
        assert modulus % size == 0                          # d^N is the identity
        for step in range(size):
            coefficients[step * modulus // size] += 1
    return dict(coefficients), sizes


def test_polynomials_are_positive_and_total_the_fiber():
    data = _polynomials()
    assert data["variables"] == ["q"]
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    staircases = rectangles = 0
    for case in data["cases"]:
        shape = tuple(case["shape"])
        coefficients = _coefficients(case)
        assert all(value > 0 for value in coefficients.values())
        assert sum(coefficients.values()) == case["count"]
        assert max(coefficients) < case["modulus"]          # least-degree representative
        assert case["modulus"] == promotion_modulus(shape)
        if len(set(shape)) == 1:
            rectangles += 1
            assert case["modulus"] == sum(shape)
        else:
            staircases += 1
            assert case["modulus"] == 2 * sum(shape)
    assert (staircases, rectangles) == (3, 19)
    assert data["case_count"] == 22


@pytest.mark.parametrize("index", range(22))
def test_orbit_polynomial_rebuilt_from_scratch_matches(index):
    """Rebuild the orbits and the sieving polynomial from Bender-Knuth promotion."""
    case = _polynomials()["cases"][index]
    rebuilt, sizes = _orbit_polynomial(tuple(case["shape"]))
    assert rebuilt == _coefficients(case)
    assert sum(sizes) == case["count"]


def test_q_equals_1_is_the_shape_and_fiber_size():
    full = {case["case_id"]: case for case in _polynomials()["cases"]}
    marginal = json.loads((PROBLEM / "data" / "q_equals_1.json").read_text())
    assert marginal["variables"] == ["shape"]
    for case in marginal["cases"]:
        shape = tuple(case["shape"])
        size = sum(1 for _ in iter_promotion_tableaux_for_shape(shape))
        assert case["terms"] == [[list(shape), size]]
        assert case["count"] == size == full[case["case_id"]]["count"]


def test_rectangles_are_the_solved_family():
    """Rhoades: on a rectangle the answer is ``(maj - n(lambda)) mod N``."""
    for case in _polynomials()["cases"]:
        shape = tuple(case["shape"])
        if len(set(shape)) != 1:
            continue
        charge = sum(index * part for index, part in enumerate(shape))
        distribution: Counter[int] = Counter()
        for obj in iter_promotion_tableaux_for_shape(shape):
            distribution[(obj.maj() - charge) % obj.modulus] += 1
        assert dict(distribution) == _coefficients(case)


def test_instances_are_the_public_objects_of_their_shape():
    instances = json.loads((PROBLEM / "data" / "instances.json").read_text())
    assert instances["object_family"] == "promotion_tableaux"
    assert instances["known_statistics"] == []
    for case in instances["cases"]:
        expected = [obj.encoding for obj in iter_promotion_tableaux_for_shape(tuple(case["shape"]))]
        assert case["entries"] == expected
        assert case["count"] == len(expected)


# ---------------------------------------------------------------------------
# The checker adapter
# ---------------------------------------------------------------------------


def _reference_statistic():
    mapping: dict[str, int] = {}
    for case in _polynomials()["cases"]:
        exponents: list[int] = []
        for degree, value in case["terms"]:
            exponents.extend([degree] * value)
        encodings = sorted(
            obj.encoding for obj in iter_promotion_tableaux_for_shape(tuple(case["shape"]))
        )
        for encoding, exponent in zip(encodings, sorted(exponents), strict=True):
            mapping[encoding] = exponent

    def stat(obj):
        return mapping[obj.encoding]

    return stat


def _template_statistic():
    source = (ROOT / "examples" / "promotion_rectangle_maj_submission.py").read_text()
    namespace: dict = {}
    exec(compile(source, "promotion_rectangle_maj_submission.py", "exec"), namespace)
    return namespace["statistic"]


def test_reference_reproduces_target_and_template_solves_exactly_the_rectangles():
    result = evaluate_promotion_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_statistic(), order_seed=1
    )
    assert result["passed"]

    template = evaluate_promotion_polynomial_checks(
        problem_dir=PROBLEM, statistic=_template_statistic()
    )
    assert not template["full_qt"]["passed"]
    assert template["q_equals_1"]["passed"]
    wrong = {
        tuple(case["shape"])
        for case in template["full_qt"]["case_results"]
        if not case["correct"]
    }
    # exactly the staircases, which is the open half of the problem
    assert wrong == {(2, 1), (3, 2, 1), (4, 3, 2, 1)}


def test_valid_but_wrong_statistic_short_circuits_at_numerical_end_to_end():
    result = evaluate_promotion_submission(
        source="def statistic(tableau):\n    return 0\n",
        probes=lambda: adversarial_promotion_probes(96),
        problem_dir=PROBLEM,
        timeout_seconds=2.0,
        numerical_timeout_seconds=120.0,
        max_python_bytes=64_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"


@pytest.mark.parametrize("invalid", [True, 1.0, "1", (0,)])
def test_statistic_must_return_a_nonnegative_int(invalid):
    with pytest.raises(TypeError, match="nonnegative integer"):
        evaluate_promotion_polynomial_checks(problem_dir=PROBLEM, statistic=lambda _o: invalid)
    with pytest.raises(ValueError, match="nonnegative integer"):
        evaluate_promotion_polynomial_checks(problem_dir=PROBLEM, statistic=lambda _o: -1)


def test_probes_cover_both_shape_families():
    objects = adversarial_promotion_tableaux(256)
    assert any(obj.is_staircase for obj in objects)
    assert any(obj.is_rectangle for obj in objects)
    assert all(obj.n <= 256 for obj in objects)
    with pytest.raises(ValueError):
        adversarial_promotion_tableaux(2)




ORBIT_POSITION_SOURCE = """\
def statistic(tableau):
    shape = tableau.shape
    n = tableau.n
    modulus = tableau.modulus
    origin = tableau.rows
    current = [list(row) for row in origin]
    best = origin
    start = 0
    size = 0
    for _ in range(modulus):
        i = 0
        j = 0
        while True:
            right = current[i][j + 1] if j + 1 < shape[i] else 0
            below = current[i + 1][j] if i + 1 < len(shape) and j < shape[i + 1] else 0
            if right == 0 and below == 0:
                break
            if below == 0 or (right != 0 and right < below):
                current[i][j] = right
                j = j + 1
            else:
                current[i][j] = below
                i = i + 1
        size = size + 1
        current[i][j] = n + size
        if all(current[r][c] - size == origin[r][c]
               for r in range(len(shape)) for c in range(shape[r])):
            break
        comparison = 0
        for r in range(len(shape)):
            for c in range(shape[r]):
                value = current[r][c] - size
                if value != best[r][c]:
                    comparison = -1 if value < best[r][c] else 1
                    break
            if comparison != 0:
                break
        if comparison < 0:
            best = tuple(tuple(v - size for v in row) for row in current)
            start = size
    return ((-start) % size) * (modulus // size)
"""


def test_the_orbit_position_construction_solves_the_target():
    """It does, on every case -- the target is defined from the orbits.

    This is the caveat `problem.md` and `docs/checker.md` spell out: the checker
    compares distributions, and walking the orbit produces the right one everywhere,
    rectangles included. Nothing in the numerical stage can tell it from an intrinsic
    statistic. The next test confirms why no later gate keeps it out.
    """
    namespace: dict = {}
    exec(compile(ORBIT_POSITION_SOURCE, "orbit_position", "exec"), namespace)
    result = evaluate_promotion_polynomial_checks(
        problem_dir=PROBLEM, statistic=namespace["statistic"]
    )
    assert result["passed"]


def test_orbit_position_construction_passes_full_admission():
    result = evaluate_promotion_submission(
        source=ORBIT_POSITION_SOURCE,
        probes=lambda: adversarial_promotion_probes(64, seed=7),
        problem_dir=PROBLEM,
        timeout_seconds=2.0,
        numerical_timeout_seconds=120.0,
        max_python_bytes=64_000_000,
    )

    assert result["passed"]
    assert result["checker_stage"] == "complete"


def test_walking_an_orbit_is_cheap_so_no_gate_excludes_the_construction():
    """The uncomfortable fact `problem.md` and `docs/checker.md` state outright.

    A promotion is ``O(rows + columns)``, not ``O(n)``, so a full orbit walk is
    affordable at probe scale and no resource bound separates the orbit construction
    from an intrinsic statistic. This test pins the cost, not a rejection: if it ever
    started failing because orbits became expensive, the claim in the docs would need
    revisiting -- in the direction of the problem being better defended, not worse.
    """
    from qtbench.combinatorics import canonical_promotion_tableau, staircase_shape

    tableau = canonical_promotion_tableau(staircase_shape(44))
    assert tableau.n == 990
    steps = 0
    current = tableau.rows
    while True:
        current = _promote(current)
        steps += 1
        if current == tableau.rows:
            break
    assert steps == tableau.modulus            # a full orbit, the worst case
    assert steps * (len(tableau.shape) + tableau.shape[0]) < 200_000


def test_object_totals():
    assert sum(case["count"] for case in _polynomials()["cases"]) == 41894


def test_cli_orbit_position_receives_automatic_pass(tmp_path):
    """A mechanical pass is not mathematical acceptance of the orbit shortcut."""
    import subprocess
    import sys

    submission = tmp_path / "orbit_position.py"
    # Use the known rectangular answer and reconstruct only staircase orbits,
    # as documented in ACTION-1. The orbit walk retains only its minimum.
    source = ORBIT_POSITION_SOURCE.replace(
        "    shape = tableau.shape",
        "    shape = tableau.shape\n"
        "    if tableau.is_rectangle:\n"
        "        charge = sum(i * part for i, part in enumerate(shape))\n"
        "        return (tableau.maj() - charge) % tableau.modulus",
    )
    submission.write_text(source, encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/evaluate/evaluate_scored_submission.py"),
            "promotion",
            str(submission),
            "--format",
            "json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    result = json.loads(completed.stdout)
    assert completed.returncode == 0, result
    assert result["passed"] is True
    assert result["automatic_verdict"] is True
    assert result["expert_review_required"] is False
    assert result["checker_stage"] == "complete"
    assert result["provenance"]["problem_id"] == 22
    assert result["provenance"]["problem_name"] == PROBLEM_NAME
    assert result["provenance"]["evaluator_kind"] == "promotion"
    assert "review_reason" not in result
