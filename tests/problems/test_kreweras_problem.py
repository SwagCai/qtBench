from __future__ import annotations

import json
import random
import runpy
from collections import Counter, defaultdict
from math import comb, factorial, gcd
from pathlib import Path

import pytest

import qtbench.combinatorics.type_a.noncrossing as noncrossing
import qtbench.evaluation.runner as runner
from qtbench.combinatorics import (
    iter_noncrossing_partitions,
    iter_partitions,
)
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_noncrossing_probes,
    evaluate_kreweras_polynomial_checks,
    evaluate_kreweras_submission,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems" / "q_statistic_discovery" / "nc_q_kreweras_q_stat"
PROBLEM_ID = 23
PROBLEM_NAME = "nc_q_kreweras_q_stat"
PUBLIC_MAX_N = 11


def _polynomials():
    return json.loads((PROBLEM / "data" / "polynomials.json").read_text())


def _by_type(case) -> dict[tuple[int, ...], dict[int, int]]:
    out: dict[tuple[int, ...], dict[int, int]] = defaultdict(dict)
    for lam, degree, value in case["terms"]:
        out[tuple(lam)][degree] = value
    return out


def _kreweras_number(lam, n: int) -> int:
    """Kreweras' closed form, written here independently of the oracle."""
    value = factorial(n) // factorial(n + 1 - len(lam))
    for multiplicity in Counter(lam).values():
        value //= factorial(multiplicity)
    return value


class _GuardedStream:
    """Small restartable test stream that fails if a consumer tries to size it."""

    def __init__(self, count: int) -> None:
        self._values = iter(range(count))
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.closed:
            raise StopIteration
        return next(self._values)

    def __length_hint__(self):
        raise AssertionError("q-Kreweras replay must not materialize its stream")

    def close(self) -> None:
        self.closed = True


@pytest.mark.parametrize("count", [0, 1, 2, 6])
def test_seeded_kreweras_stream_is_one_coprime_rotation(count: int) -> None:
    created: list[_GuardedStream] = []

    def factory():
        stream = _GuardedStream(count)
        created.append(stream)
        return stream

    objects = runner._iter_kreweras_objects(factory, count, random.Random(37))
    if count == 0:
        with pytest.raises(StopIteration):
            next(objects)
        assert len(created) == 1
        assert all(stream.closed for stream in created)
        return

    offset = next(objects)
    if count == 1:
        assert offset == 0
        with pytest.raises(StopIteration):
            next(objects)
        assert len(created) == 1
        assert all(stream.closed for stream in created)
        return

    assert 1 <= offset < count
    assert gcd(offset, count) == 1
    expected = offset + 1
    for _ in range(count - 1):
        if expected == count:
            expected = 0
        assert next(objects) == expected
        expected += 1
    with pytest.raises(StopIteration):
        next(objects)
    assert len(created) == 2
    assert all(stream.closed for stream in created)

    visited = set()
    position = 0
    while position not in visited:
        visited.add(position)
        position = (position + offset) % count
    assert position == 0
    assert len(visited) == count


@pytest.mark.parametrize("count", [0, 1, 2, 6])
def test_seeded_kreweras_stream_rejects_an_overlong_tail(count: int) -> None:
    created: list[_GuardedStream] = []

    def factory():
        stream = _GuardedStream(count + 1)
        created.append(stream)
        return stream

    objects = runner._iter_kreweras_objects(factory, count, random.Random(37))
    if count < 2:
        for expected in range(count):
            assert next(objects) == expected
    else:
        selector = random.Random(37)
        offset = selector.randrange(1, count)
        while gcd(offset, count) != 1:
            offset = 1 if offset + 1 == count else offset + 1
        for expected in range(offset, count):
            assert next(objects) == expected

    with pytest.raises(ValueError, match="exceeded its validated public count"):
        next(objects)
    assert len(created) == 1
    assert created[0].closed


def test_seeded_kreweras_stream_closes_tail_before_creating_prefix() -> None:
    events: list[str] = []

    class RecordingStream(_GuardedStream):
        def __init__(self, count: int, name: str) -> None:
            super().__init__(count)
            self.name = name

        def close(self) -> None:
            events.append(f"close:{self.name}")
            super().close()

    def factory():
        name = "tail" if not events else "prefix"
        events.append(f"create:{name}")
        return RecordingStream(6, name)

    for _ in runner._iter_kreweras_objects(factory, 6, random.Random(37)):
        pass

    assert events == [
        "create:tail",
        "close:tail",
        "create:prefix",
        "close:prefix",
    ]


def test_seeded_kreweras_stream_is_deterministic_and_closes_on_abort() -> None:
    first = runner._iter_kreweras_objects(
        lambda: _GuardedStream(12), 12, random.Random(91)
    )
    second = runner._iter_kreweras_objects(
        lambda: _GuardedStream(12), 12, random.Random(91)
    )
    for _ in range(12):
        assert next(first) == next(second)
    for objects in (first, second):
        with pytest.raises(StopIteration):
            next(objects)

    created: list[_GuardedStream] = []

    def factory():
        stream = _GuardedStream(12)
        created.append(stream)
        return stream

    objects = runner._iter_kreweras_objects(factory, 12, random.Random(91))
    next(objects)
    objects.close()
    assert len(created) == 1
    assert all(stream.closed for stream in created)

    short: list[_GuardedStream] = []

    def short_factory():
        stream = _GuardedStream(1)
        short.append(stream)
        return stream

    with pytest.raises(ValueError, match="validated public count"):
        for _ in runner._iter_kreweras_objects(
            short_factory, 2, random.Random(91)
        ):
            pass
    assert len(short) == 1
    assert all(stream.closed for stream in short)

    prefix_short: list[_GuardedStream] = []

    def prefix_short_factory():
        stream = _GuardedStream(2 if not prefix_short else 0)
        prefix_short.append(stream)
        return stream

    with pytest.raises(ValueError, match="validated public count"):
        for _ in runner._iter_kreweras_objects(
            prefix_short_factory, 2, random.Random(91)
        ):
            pass
    assert len(prefix_short) == 2
    assert all(stream.closed for stream in prefix_short)


def test_seeded_kreweras_stream_closes_recursive_cache_after_prefix_abort() -> None:
    noncrossing._enumerate_blocks.cache_clear()
    count = 42
    seed = 19
    selector = random.Random(seed)
    offset = selector.randrange(1, count)
    while gcd(offset, count) != 1:
        offset = 1 if offset + 1 == count else offset + 1

    created = []

    def factory():
        stream = iter_noncrossing_partitions(5)
        created.append(stream)
        return stream

    objects = runner._iter_kreweras_objects(
        factory, count, random.Random(seed)
    )
    try:
        for _ in range(count - offset + 1):
            next(objects)
        assert len(created) == 2
        assert noncrossing._enumerate_blocks.cache_info().currsize > 0
    finally:
        objects.close()
    assert noncrossing._enumerate_blocks.cache_info().currsize == 0


def test_polynomials_are_positive_and_total_the_catalan_number():
    data = _polynomials()
    assert data["variables"] == ["partition", "q"]
    assert data["problem_id"] == PROBLEM_ID
    assert data["problem_name"] == PROBLEM_NAME
    for case in data["cases"]:
        n = case["n"]
        assert all(value > 0 for *_key, value in case["terms"])
        assert sum(value for *_key, value in case["terms"]) == case["count"]
        assert case["count"] == comb(2 * n, n) // (n + 1)
        by_type = _by_type(case)
        assert set(by_type) == set(iter_partitions(n))
    assert data["case_count"] == PUBLIC_MAX_N


def test_each_type_totals_its_kreweras_number():
    """``Krew_lambda(1)`` against Kreweras' closed form and against the objects."""
    for case in _polynomials()["cases"]:
        n = case["n"]
        counts = Counter(obj.block_type for obj in iter_noncrossing_partitions(n))
        for lam, poly in _by_type(case).items():
            assert sum(poly.values()) == _kreweras_number(lam, n) == counts[lam]


def test_the_extreme_types_are_monomials():
    """``(1^n)`` sits at ``0`` and ``(n)`` at ``n(n-1)``, both single partitions."""
    for case in _polynomials()["cases"]:
        n = case["n"]
        by_type = _by_type(case)
        assert by_type[tuple([1] * n)] == {0: 1}
        assert by_type[(n,)] == {n * (n - 1): 1}


def test_types_sum_to_the_q_catalan_number():
    """``sum_lambda Krew_lambda(q) = (1/[n+1]_q) [2n ; n]_q``, recomputed here."""

    def multiply(left, right):
        out = [0] * (len(left) + len(right) - 1)
        for i, x in enumerate(left):
            for j, y in enumerate(right):
                out[i + j] += x * y
        while out and out[-1] == 0:
            out.pop()
        return out

    def divide(numerator, denominator):
        numerator = list(numerator)
        quotient = [0] * (len(numerator) - len(denominator) + 1)
        for degree in range(len(quotient) - 1, -1, -1):
            value, rest = divmod(numerator[degree + len(denominator) - 1], denominator[-1])
            assert rest == 0
            quotient[degree] = value
            for offset, coefficient in enumerate(denominator):
                numerator[degree + offset] -= value * coefficient
        assert not any(numerator)
        return quotient

    def factorial_q(m):
        out = [1]
        for value in range(1, m + 1):
            out = multiply(out, [1] * value)
        return out

    for case in _polynomials()["cases"]:
        n = case["n"]
        total: Counter[int] = Counter()
        for _lam, degree, value in case["terms"]:
            total[degree] += value
        expected = divide(
            divide(factorial_q(2 * n), multiply(factorial_q(n), factorial_q(n))),
            [1] * (n + 1),
        )
        assert [total[degree] for degree in range(len(expected))] == expected
        assert max(total) == len(expected) - 1


def test_generator_polynomial_addition_preserves_degrees_above_399():
    generator = runpy.run_path(str(PROBLEM / "generate_data.py"))
    degree = 21 * 20
    high_degree_term = [0] * degree + [1]

    assert generator["_add_polynomials"]([1], high_degree_term) == (
        [1] + [0] * (degree - 1) + [1]
    )


def test_q_equals_1_is_the_block_type_distribution():
    full = {case["case_id"]: case for case in _polynomials()["cases"]}
    marginal = json.loads((PROBLEM / "data" / "q_equals_1.json").read_text())
    assert marginal["variables"] == ["partition"]
    for case in marginal["cases"]:
        got = {tuple(lam): value for lam, value in case["terms"]}
        assert got == Counter(
            obj.block_type for obj in iter_noncrossing_partitions(case["n"])
        )
        expected: Counter[tuple[int, ...]] = Counter()
        for lam, _degree, value in full[case["case_id"]]["terms"]:
            expected[tuple(lam)] += value
        assert got == dict(expected)


def test_instances_are_the_public_objects():
    instances = json.loads((PROBLEM / "data" / "instances.json").read_text())
    assert instances["object_family"] == "noncrossing_partitions"
    assert instances["known_statistics"] == []
    for case in instances["cases"]:
        assert case["count"] == len(case["entries"])
        for entry, obj in zip(
            case["entries"],
            iter_noncrossing_partitions(case["n"]),
            strict=True,
        ):
            assert entry == obj.to_jsonable()


# ---------------------------------------------------------------------------
# The checker adapter
# ---------------------------------------------------------------------------


def _reference_statistic():
    mapping: dict[bytes, int] = {}
    for case in _polynomials()["cases"]:
        column = defaultdict(list)
        for lam, degree, value in case["terms"]:
            column[tuple(lam)].extend([degree] * value)
        fibers = defaultdict(list)
        for obj in iter_noncrossing_partitions(case["n"]):
            fibers[obj.block_type].append(bytes(obj.to_rgf()))
        for block_type, encodings in fibers.items():
            encodings.sort()
            for encoding, exponent in zip(
                encodings, sorted(column[block_type]), strict=True
            ):
                mapping[encoding] = exponent

    def krewstat(obj):
        return mapping[bytes(obj.to_rgf())]

    return krewstat


def test_reference_reproduces_target_but_area_does_not():
    result = evaluate_kreweras_polynomial_checks(
        problem_dir=PROBLEM, statistic=_reference_statistic(), order_seed=1
    )
    assert result["passed"]

    area = evaluate_kreweras_polynomial_checks(
        problem_dir=PROBLEM, statistic=lambda obj: obj.area()
    )
    assert not area["full_qt"]["passed"]
    assert area["q_equals_1"]["passed"]
    correct = {case["n"] for case in area["full_qt"]["case_results"] if case["correct"]}
    assert correct == {1}


def test_fresh_rotated_replay_rejects_a_position_only_statistic(tmp_path: Path):
    n = 4
    full: Counter[tuple[tuple[int, ...], int]] = Counter()
    marginal: Counter[tuple[int, ...]] = Counter()
    for position, obj in enumerate(iter_noncrossing_partitions(n)):
        full[(obj.block_type, position)] += 1
        marginal[obj.block_type] += 1
    count = sum(full.values())
    full_terms = [
        [list(block_type), exponent, coefficient]
        for (block_type, exponent), coefficient in sorted(full.items())
    ]
    marginal_terms = [
        [list(block_type), coefficient]
        for block_type, coefficient in sorted(marginal.items())
    ]

    problem_dir = tmp_path / PROBLEM_NAME
    data_dir = problem_dir / "data"
    data_dir.mkdir(parents=True)
    (problem_dir / "metadata.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "id": PROBLEM_ID,
                "name": PROBLEM_NAME,
            }
        ),
        encoding="utf-8",
    )
    identity = {
        "schema_version": "0.1",
        "problem_id": PROBLEM_ID,
        "problem_name": PROBLEM_NAME,
        "case_count": 1,
    }
    (data_dir / "polynomials.json").write_text(
        json.dumps(
            {
                **identity,
                "variables": ["partition", "q"],
                "cases": [
                    {
                        "case_id": "n04",
                        "n": n,
                        "count": count,
                        "term_count": len(full_terms),
                        "terms": full_terms,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "q_equals_1.json").write_text(
        json.dumps(
            {
                **identity,
                "variables": ["partition"],
                "specialization": {"q": 1},
                "cases": [
                    {
                        "case_id": "n04",
                        "n": n,
                        "count": count,
                        "term_count": len(marginal_terms),
                        "terms": marginal_terms,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def position_statistic():
        state = [None, -1]

        def statistic(obj):
            if state[0] != obj.blocks:
                state[0] = obj.blocks
                state[1] += 1
            return state[1]

        return statistic

    assert evaluate_kreweras_polynomial_checks(
        problem_dir=problem_dir, statistic=position_statistic()
    )["passed"]

    source = (
        "state = [None, -1]\n\n"
        "def statistic(partition):\n"
        "    if state[0] != partition.blocks:\n"
        "        state[0] = partition.blocks\n"
        "        state[1] += 1\n"
        "    return state[1]\n"
    )
    with pytest.raises(ResourceGateError, match="fresh shuffled replay"):
        evaluate_kreweras_submission(
            source=source,
            probes=(),
            problem_dir=problem_dir,
            timeout_seconds=2.0,
            numerical_timeout_seconds=10.0,
            max_python_bytes=32_000_000,
            max_process_bytes=128_000_000,
        )


def test_valid_but_wrong_statistic_short_circuits_at_numerical_end_to_end():
    result = evaluate_kreweras_submission(
        source="def statistic(partition):\n    return 0\n",
        probes=lambda: adversarial_noncrossing_probes(96),
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
        evaluate_kreweras_polynomial_checks(problem_dir=PROBLEM, statistic=lambda _o: invalid)
    with pytest.raises(ValueError, match="nonnegative integer"):
        evaluate_kreweras_polynomial_checks(problem_dir=PROBLEM, statistic=lambda _o: -1)




def test_object_totals_are_the_catalan_numbers():
    data = _polynomials()
    assert sum(case["count"] for case in data["cases"]) == 82499
    assert [case["count"] for case in data["cases"]] == [
        comb(2 * n, n) // (n + 1) for n in range(1, PUBLIC_MAX_N + 1)
    ]
