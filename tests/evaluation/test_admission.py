from __future__ import annotations

import math
import pickle
import sys
from pathlib import Path

import pytest

import qtbench.evaluation.admission as admission
from qtbench.combinatorics import NoncrossingPartition
from qtbench.evaluation import (
    GateError,
    ResourceGateError,
    adversarial_dyck_paths,
    adversarial_dyck_probes,
    adversarial_noncrossing_probes,
    check_capability_screen,
    check_source_economy,
    evaluate_area_bounce_submission,
    evaluate_noncrossing_submission,
    public_area_bounce_terms,
    run_area_bounce_identity_gate,
    run_resource_gate,
)

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems/t_statistic_discovery/nc_area_qt_narayana_second_stat"


# The intended second statistic (a bounce-analogue) that solves the problem.
KNOWN_GOOD = """\
def statistic(partition):
    repeated_maxima = []
    nonmaximal_elements = []
    for block in partition.blocks_by_max:
        repeated_maxima.extend([block[-1]] * (len(block) - 1))
        nonmaximal_elements.extend(block[:-1])
    if not repeated_maxima:
        return 0
    nonmaximal_elements.sort()
    total = 0
    index = 0
    while index < len(repeated_maxima):
        current = repeated_maxima[index]
        total += partition.n - current
        index = sum(1 for value in nonmaximal_elements if value < current)
    return total
"""

AREA_ONLY = "def statistic(partition):\n    return partition.area()\n"

# A correct area/bounce bijection built by rank-matching inside (area, bounce)
# bags. It satisfies every identity, but it enumerates the whole path set, so it
# is only feasible for tiny sizes.
ENUMERATION_BIJECTION = """\
def area(path):
    x = 0
    y = 0
    total = 0
    for step in path:
        if step == "N":
            total += y - x
            y += 1
        else:
            x += 1
    return total

def bounce(path):
    y = 0
    heights = []
    for step in path:
        if step == "N":
            y += 1
        else:
            heights.append(y)
    n = len(heights)
    point = 0
    total = 0
    while point < n:
        point = heights[point]
        total += n - point
    return total

def paths(n):
    result = [""]
    for step in range(2 * n):
        nxt = []
        for word in result:
            up = word.count("N")
            down = word.count("E")
            if up < n:
                nxt.append(word + "N")
            if down < up:
                nxt.append(word + "E")
        result = nxt
    return result

def forward(path):
    n = len(path) // 2
    key = (area(path), bounce(path))
    source = []
    target = []
    for candidate in paths(n):
        candidate_key = (area(candidate), bounce(candidate))
        if candidate_key == key:
            source.append(candidate)
        if candidate_key == (key[1], key[0]):
            target.append(candidate)
    source.sort()
    target.sort()
    return target[source.index(path)]

def inverse(path):
    return forward(path)
"""

IDENTITY_MAP = "def forward(path):\n    return path\n\ndef inverse(path):\n    return path\n"


def nc_probes(n, count=4):
    return adversarial_noncrossing_probes(n)[:count]


class _ReprBomb:
    def __repr__(self):
        raise AssertionError("parent validator rendered an untrusted result")


class _IterationBomb:
    def __len__(self):
        raise AssertionError("parent validator measured an untrusted result")

    def __iter__(self):
        raise AssertionError("parent validator iterated an untrusted result")


# --------------------------------------------------------------------------
# Capability screen
# --------------------------------------------------------------------------


def test_capability_safety_accepts_a_plain_statistic():
    assert check_capability_screen(KNOWN_GOOD) == ("statistic",)


@pytest.mark.parametrize(
    "source",
    [
        # The injected helpers are module-level objects shared by every
        # namespace in the process, so an attribute written on one of them
        # would outlive the "fresh namespace" that STATE-1 replay relies on.
        "def statistic(partition):\n    split_head.stash = {}\n    return 0\n",
        "def statistic(partition):\n    first_return.seen = 1\n    return 0\n",
        # The trusted object must not be mutable by the submission either.
        "def statistic(partition):\n    partition.cache = 1\n    return 0\n",
        "def statistic(partition):\n    del split_head.stash\n    return 0\n",
        "def statistic(partition):\n    split_head.n += 1\n    return 0\n",
    ],
)
def test_capability_screen_rejects_attribute_writes(source):
    with pytest.raises(GateError, match="attribute"):
        check_capability_screen(source)


def test_no_admitted_attribute_reaches_a_frame_or_code_object():
    """The reflection ban has to cover the whole reachable surface, not a list.

    Enumerates every non-underscore attribute of every value a submission can
    construct and asserts none of the ones the screen admits yields a frame,
    code object, traceback, or module.
    """

    import types

    def generator_body():
        yield 1

    generator = generator_body()
    next(generator)
    try:
        raise ValueError("probe")
    except ValueError as error:
        exception = error

    samples = [
        1, "a", [1], (1,), {1: 1}, {1}, frozenset({1}), range(2), True, 1.0,
        generator, exception, admission.split_head, admission.first_return,
        len, enumerate([1]), zip([1], [2]), reversed([1]), iter([1]),
    ]
    dangerous = (types.FrameType, types.CodeType, types.ModuleType, types.TracebackType)

    escapes = []
    for value in samples:
        for name in dir(value):
            if name.startswith("_") or name in admission._BANNED_ATTRIBUTES:
                continue
            try:
                attribute = getattr(value, name)
            except Exception:
                continue
            if isinstance(attribute, dangerous):
                escapes.append((type(value).__name__, name))
    assert not escapes, escapes


def test_helper_attributes_cannot_carry_state_between_namespaces():
    """The screen is what makes `load_restricted_functions` namespaces fresh.

    `split_head` and `first_return` are injected by identity, so without the
    screen a value stashed on one would be readable from the replay namespace.
    """

    stash = "def statistic(partition):\n    split_head.stash = 1\n    return 0\n"
    with pytest.raises(GateError):
        check_capability_screen(stash)
    assert not hasattr(admission.split_head, "stash")


@pytest.mark.parametrize(
    "source",
    [
        "import os\ndef statistic(partition):\n    return 0\n",
        "def statistic(partition):\n    return partition.__class__\n",
        "def statistic(partition):\n    return (x for x in partition.blocks).gi_frame\n",
        "def statistic(partition):\n    return open('t')\n",
        "def statistic(partition):\n    return eval('1')\n",
        "def statistic(partition):\n    return '{0.__class__}'.format(partition)\n",
        "def statistic(partition):\n    template='{0.__class__}'\n    return template.format(partition)\n",
        "@staticmethod\ndef statistic(partition):\n    return 0\n",
        "def statistic(partition, cache=[1, 2, 3]):\n    return len(cache)\n",
        "def statistic(partition, *extra):\n    return len(extra)\n",
        # A lambda binds a callable just as a `def` does, so the same signature
        # rule applies to it.
        "helper = lambda partition, cache={}: partition.n\n"
        "def statistic(partition):\n    return 0\n",
        "helper = lambda partition, *extra: partition.n\n"
        "def statistic(partition):\n    return 0\n",
        "def statistic(partition):\n"
        "    return max(map(lambda block, cache={}: len(block), partition.blocks))\n",
    ],
)
def test_capability_safety_blocks_escapes_and_dynamic_signatures(source):
    with pytest.raises(GateError, match="capability screen|not allowed|not available"):
        check_capability_screen(source)


@pytest.mark.parametrize(
    "binding",
    [
        "def sum(values):\n    return 0",
        "sum = lambda values: 0",
        "sum: int = lambda values: 0",
        "sum, extra = (lambda values: 0), 1",
        "sum = (lambda values: 0) if 1 else (lambda values: 1)",
        "for sum in [(lambda values: 0)]:\n    pass",
        "if 1:\n    sum = lambda values: 0",
        "if 1:\n    def sum(values):\n        return 0",
        "sum = other = lambda values: 0",
        # aliasing a submitted function onto the builtin's name
        "def helper(values):\n    return 0\nsum = helper",
    ],
)
def test_capability_safety_blocks_shadowing_trusted_names(binding):
    """Every module binding is checked, not just a top-level `def`.

    `visit_Call` admits a call to any whitelisted builtin name, so a submission
    that binds one in its own namespace makes its `sum(...)` reach the binding
    instead. Screening only `def` left every other spelling open.
    """

    source = f"{binding}\ndef statistic(partition):\n    return sum(partition.blocks)\n"
    with pytest.raises(GateError, match="shadow trusted names"):
        check_capability_screen(source)


@pytest.mark.parametrize(
    "source",
    [
        "(sum := (lambda values: 0))\ndef statistic(partition):\n    return sum(partition)\n",
        "[(sum := (lambda values: 0)) for _ in range(1)]\n"
        "def statistic(partition):\n    return sum(partition)\n",
        "list((sum := (lambda values: 0)) for _ in range(1))\n"
        "def statistic(partition):\n    return sum(partition)\n",
        "match [(lambda values: 0)]:\n    case [sum]:\n        pass\n"
        "def statistic(partition):\n    return sum(partition)\n",
        "match [(lambda values: 0)]:\n    case [other as sum]:\n        pass\n"
        "def statistic(partition):\n    return sum(partition)\n",
        # rejected as constructs, so ordinary uses go too
        "def statistic(partition):\n    return len([y for y in partition.blocks if (v := y)])\n",
        "def statistic(partition):\n"
        "    match partition.n:\n        case 0:\n            return 0\n    return 1\n",
    ],
)
def test_capability_screen_rejects_walrus_and_match(source):
    """These two bind outward from a nested construct, so enumeration misses them.

    An assignment expression inside a comprehension, and a `match` capture
    pattern, both land in the module namespace while `_module_bound_names` is
    skipping the comprehension or failing to see a pattern's plain-string name.
    Neither is needed to express a statistic, so the screen rejects the
    construct rather than chase each spelling.
    """

    with pytest.raises(GateError, match=r"(NamedExpr|Match) is not allowed"):
        check_capability_screen(source)


def test_capability_safety_allows_a_local_builtin_name():
    """Only module bindings are screened; a function local keeps its own scope."""

    source = (
        "def statistic(partition):\n"
        "    sum = 0\n"
        "    for block in partition.blocks:\n"
        "        sum = sum + len(block)\n"
        "    return sum\n"
    )
    assert check_capability_screen(source) == ("statistic",)


def test_capability_safety_allows_a_plain_lambda():
    """Only the signature rule reaches a lambda; the form itself is still fine.

    `sorted(..., key=lambda ...)` is ordinary code for a statistic, so screening
    lambdas must not become a ban on them.
    """

    source = (
        "def statistic(partition):\n"
        "    blocks = sorted(partition.blocks, key=lambda block: block[0])\n"
        "    return len(blocks)\n"
    )
    assert check_capability_screen(source) == ("statistic",)


def test_capability_safety_allows_underscore_throwaway():
    # `for _ in range(n)` is a common idiom; only dunder names are dangerous.
    source = "def statistic(partition):\n    t = 0\n    for _ in range(partition.n):\n        t += 1\n    return t\n"
    assert check_capability_screen(source) == ("statistic",)


def test_submission_audit_policy_allows_only_declared_reads(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    target = data_dir / "target.json"
    target.write_text("{}")

    admission._deny_submission_audit_events(
        "open", (str(target), "r"), allowed_read_paths=(data_dir,)
    )
    with pytest.raises(PermissionError):
        admission._deny_submission_audit_events(
            "open", (str(target), "w"), allowed_read_paths=(data_dir,)
        )
    with pytest.raises(PermissionError):
        admission._deny_submission_audit_events("os.remove", (str(target),))


def test_hardened_probes_cover_three_scales() -> None:
    initial = adversarial_noncrossing_probes(64, seed=7)[:1]
    hardened = admission._hardened_probes(initial, kind="noncrossing")
    sizes = {arguments[0].n for _name, arguments in hardened}

    assert {16, 32, 64} <= sizes


@pytest.mark.parametrize("kind", sorted(admission._PROBE_BUILDERS))
def test_structural_size_covers_every_registered_probe_kind(kind) -> None:
    calls = admission._PROBE_BUILDERS[kind](8, seed=7)

    assert calls
    assert all(
        type(admission._structural_size(arguments[0])) is int
        and admission._structural_size(arguments[0]) > 0
        for _name, arguments in calls
    )


def test_probe_builder_registry_covers_every_declared_builder() -> None:
    declared = {
        value
        for name, value in vars(admission).items()
        if name.startswith("adversarial_")
        and name.endswith("_probes")
        and callable(value)
    }

    assert set(admission._PROBE_BUILDERS.values()) == declared


def test_asm_hardened_probes_use_three_effective_capped_scales() -> None:
    initial = admission.adversarial_asm_probes(1024, seed=7)
    hardened = admission._hardened_probes(initial, kind="asm-q")

    assert {arguments[0].n for _name, arguments in hardened} == {64, 128, 256}


def test_shifted_pq_hardening_uses_three_orders_without_repeating_maximum() -> None:
    supplied = admission.adversarial_shifted_pq_tableaux(1024, seed=7)
    hardened = admission._hardened_shifted_pq_tableaux(supplied)
    encodings = [tableau.encoding for tableau in hardened]

    assert {tableau.mu[0] for tableau in hardened} == {256, 512, 1024}
    assert len(encodings) == len(set(encodings))
    assert sum(tableau.mu[0] == 1024 for tableau in hardened) == len(supplied)


def test_tree_probe_parent_sampling_matches_the_list_reference(monkeypatch) -> None:
    seed = 37
    n = 12

    zero_generator = admission.random.Random(seed)
    zero_levels = []
    level = 0
    for _ in range(n):
        if zero_generator.getrandbits(1):
            level += 1
        zero_levels.append(max(1, level))
    zero_parents = []
    for vertex in range(1, n + 1):
        candidates = [
            0,
            *(
                other
                for other in range(1, vertex)
                if zero_levels[other - 1] < zero_levels[vertex - 1]
            ),
        ]
        zero_parents.append(zero_generator.choice(candidates))
    zero_reference = (
        ",".join(map(str, zero_levels))
        + "|"
        + ",".join(map(str, zero_parents))
    )
    zero_actual = admission.adversarial_zero_rooted_tiered_trees(n, seed=seed)[-1]
    assert zero_actual.encoding == zero_reference
    admission.ZeroRootedTieredTree(zero_actual.encoding)

    rooted_generator = admission.random.Random(seed)
    rooted_levels = [0]
    level = 1
    for _ in range(n):
        rooted_levels.append(level)
        if rooted_generator.getrandbits(1):
            level += 1
    rooted_parents = [0]
    for vertex in range(2, n + 2):
        candidates = [
            other
            for other in range(1, vertex)
            if rooted_levels[other - 1] < rooted_levels[vertex - 1]
        ]
        rooted_parents.append(rooted_generator.choice(candidates))
    rooted_reference = (
        ",".join(map(str, rooted_levels))
        + "|"
        + ",".join(map(str, rooted_parents))
    )
    rooted_actual = admission.adversarial_rooted_tiered_trees(n, seed=seed)[-1]
    assert rooted_actual.encoding == rooted_reference
    admission.RootedTieredTree(rooted_actual.encoding)

    threshold_generator = admission.random.Random(seed)
    threshold_shapes = [
        admission.threshold_up_degrees(n, range(1, n)),
        admission.threshold_up_degrees(n, ()),
        admission.threshold_up_degrees(n, range(1, n, 2)),
    ]
    threshold_references = []
    for up_degrees in threshold_shapes:
        parents = []
        for vertex in range(1, n + 1):
            candidates = [
                other
                for other in range(vertex)
                if vertex <= other + up_degrees[other]
            ]
            parents.append(threshold_generator.choice(candidates))
        threshold_references.append(
            ",".join(map(str, up_degrees)) + "|" + ",".join(map(str, parents))
        )
    threshold_actual = admission.adversarial_threshold_spanning_trees(
        n, seed=seed
    )[3:6]
    assert [tree.encoding for tree in threshold_actual] == threshold_references
    for tree in threshold_actual:
        admission.ThresholdSpanningTree(tree.encoding)

    class RangeOnlyRandom(admission.random.Random):
        def choice(self, sequence):
            assert type(sequence) is range
            return super().choice(sequence)

    monkeypatch.setattr(
        admission, "_probe_random", lambda _seed: RangeOnlyRandom(seed)
    )
    admission.adversarial_zero_rooted_tiered_trees(n, seed=seed)
    admission.adversarial_rooted_tiered_trees(n, seed=seed)
    admission.adversarial_threshold_spanning_trees(n, seed=seed)


def test_unseeded_asm_probes_use_the_recorded_run_seed(monkeypatch) -> None:
    observed = []

    def fake_matrices(_size, *, seed=None):
        observed.append(seed)
        return []

    monkeypatch.setenv("QTBENCH_RUN_SEED", "123")
    monkeypatch.setattr(
        admission, "adversarial_alternating_sign_matrices", fake_matrices
    )

    assert admission.adversarial_asm_probes(64) == []
    assert admission.adversarial_asm_probes(64) == []
    assert observed[0] is not None
    assert observed[0] == observed[1]


def test_large_probe_pair_and_composition_validators_fail_closed() -> None:
    pair_calls = admission.adversarial_kostka_probes(8, seed=7)[:1]
    pair_report = admission.ResourceReport(0.0, 0, ((0, True),))
    with pytest.raises(ResourceGateError, match="pair of nonnegative integers"):
        admission._validate_pair_probe_results(pair_report, pair_calls)

    composition_calls = admission.adversarial_uig_probes(8, seed=7)[:1]
    composition_report = admission.ResourceReport(0.0, 0, ((1,),))
    with pytest.raises(ResourceGateError, match="invalid composition"):
        admission._validate_composition_probe_results(
            composition_report, composition_calls
        )


def test_compositions_accept_only_bounded_builtin_sequences() -> None:
    assert admission._normalize_composition((2, 1), 3) == (2, 1)
    assert admission._normalize_composition([1, 2], 3) == (2, 1)
    assert admission._normalize_composition((), 0) == ()
    assert admission._normalize_composition([], 0) == ()

    calls = admission.adversarial_uig_probes(8, seed=7)[:1]
    obj = calls[0][1][0]
    invalid_results = (
        range(obj.n, obj.n + 1),
        _IterationBomb(),
        [1] * (obj.n + 1),
        (1,) * (obj.n + 1),
    )
    for invalid in invalid_results:
        report = admission.ResourceReport(0.0, 0, (invalid,))
        with pytest.raises(ResourceGateError, match="invalid composition"):
            admission._validate_composition_probe_results(report, calls)


def test_resource_validators_reject_integers_unavailable_to_json() -> None:
    original_limit = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(640)
    try:
        huge = 10**640
        integer_calls = admission.adversarial_noncrossing_probes(8, seed=7)[:1]
        integer_report = admission.ResourceReport(0.0, 0, (huge,))
        with pytest.raises(ResourceGateError, match="official JSON output"):
            admission._validate_integer_probe_results(integer_report, integer_calls)

        pair_calls = admission.adversarial_kostka_probes(8, seed=7)[:1]
        for result in ((huge, 0), (0, huge)):
            pair_report = admission.ResourceReport(0.0, 0, (result,))
            with pytest.raises(ResourceGateError, match="official JSON output"):
                admission._validate_pair_probe_results(pair_report, pair_calls)
    finally:
        sys.set_int_max_str_digits(original_limit)


def test_parent_validators_do_not_render_untrusted_results() -> None:
    invalid = _ReprBomb()
    checks = (
        (
            admission._validate_integer_probe_results,
            admission.adversarial_noncrossing_probes(8, seed=7)[:1],
        ),
        (
            admission._validate_pair_probe_results,
            admission.adversarial_kostka_probes(8, seed=7)[:1],
        ),
        (
            admission._validate_composition_probe_results,
            admission.adversarial_uig_probes(8, seed=7)[:1],
        ),
    )
    for validator, calls in checks:
        report = admission.ResourceReport(0.0, 0, (invalid,))
        with pytest.raises(ResourceGateError):
            validator(report, calls)








@pytest.mark.parametrize(
    "source",
    [
        "def statistic(partition):\n    return 'not an int'\n",
        "def statistic(partition):\n    return -1\n",
        "def statistic(partition):\n    return None\n",
        "def statistic(partition):\n    raise ValueError('boom')\n",
    ],
)
def test_degenerate_returns_fail_gracefully(source):
    # None of these may crash the checker; each must surface as a gate error.
    with pytest.raises((GateError, ResourceGateError)):
        evaluate_noncrossing_submission(
            source=source,
            probes=lambda: adversarial_noncrossing_probes(64),
            problem_dir=PROBLEM,
            timeout_seconds=2.0,
            numerical_timeout_seconds=6.0,
            max_python_bytes=32_000_000,
        )


def test_capability_safety_allows_dicts_sets_and_recursion():
    # These were forbidden by the old DSL; genuine algorithms use them freely.
    source = (
        "def statistic(partition):\n"
        "    seen = {}\n"
        "    marks = set()\n"
        "    for block in partition.blocks:\n"
        "        seen[block[0]] = len(block)\n"
        "        marks.add(block[-1])\n"
        "    return len(seen) + len(marks)\n"
    )
    assert check_capability_screen(source) == ("statistic",)


# --------------------------------------------------------------------------
# Source economy
# --------------------------------------------------------------------------


def test_source_economy_accepts_short_source():
    check_source_economy(KNOWN_GOOD)


@pytest.mark.parametrize(
    "source",
    [
        "def statistic(path):\n    return 0\n" + "# padding\n" * 200,
        f'def statistic(path):\n    return {"x" * 400!r}\n',
    ],
)
def test_source_economy_rejects_oversized_sources(source):
    with pytest.raises(GateError, match="lines|literal bytes|bytes|tokens"):
        check_source_economy(source)


def test_source_economy_counts_float_and_complex_literals():
    floats = ", ".join(f"{index}.5" for index in range(40))
    complexes = ", ".join(f"{index + 1}j" for index in range(20))
    for source in (
        f"def statistic(path):\n    return [{floats}]\n",
        f"def statistic(path):\n    return [{complexes}]\n",
    ):
        with pytest.raises(GateError, match="literal bytes"):
            check_source_economy(source)


def test_bijection_target_loader_rejects_duplicate_structural_cases():
    data = {
        "cases": [
            {"case_id": "first", "n": 4, "terms": [[0, 0, 1]]},
            {"case_id": "second", "n": 4, "terms": [[1, 1, 1]]},
        ]
    }

    with pytest.raises(ValueError, match="duplicate structural case 4"):
        admission._unique_target_terms(data, lambda case: case["n"])


# --------------------------------------------------------------------------
# Referential transparency
# --------------------------------------------------------------------------


def test_assignment_fingerprint_tracks_objects_not_call_order():
    first = NoncrossingPartition([(1,), (2,)], n=2, validate=False)
    second = NoncrossingPartition([(1, 2)], n=2, validate=False)
    source = (
        "assigned = {}\n"
        "def statistic(partition):\n"
        "    key = partition.blocks\n"
        "    if key not in assigned:\n"
        "        assigned[key] = len(assigned)\n"
        "    return assigned[key]\n"
    )
    key = b"referential-test"

    forward = admission.load_restricted_functions(source)["statistic"]
    record_forward, forward_state = admission._recording_statistic(
        forward, "noncrossing", key, repeat=True
    )
    record_forward(first)
    record_forward(second)

    reverse = admission.load_restricted_functions(source)["statistic"]
    record_reverse, reverse_state = admission._recording_statistic(
        reverse, "noncrossing", key, repeat=True
    )
    record_reverse(second)
    record_reverse(first)

    assert forward_state["count"] == reverse_state["count"] == 2
    assert forward_state["fingerprint"] != reverse_state["fingerprint"]


# --------------------------------------------------------------------------
# Resource gate
# --------------------------------------------------------------------------


class _FakeConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeProcess:
    def __init__(
        self,
        *,
        exits_during_join=False,
        natural_exitcode=0,
        terminate_stops=True,
        kill_stops=True,
    ):
        self.started = False
        self.alive = False
        self.reaped = False
        self.closed = False
        self.exitcode = None
        self.exits_during_join = exits_during_join
        self.natural_exitcode = natural_exitcode
        self.terminate_stops = terminate_stops
        self.kill_stops = kill_stops
        self.events = []
        self.join_timeouts = []

    def start(self):
        self.started = True
        self.alive = True
        self.events.append("start")

    def is_alive(self):
        assert not self.closed
        return self.alive

    def terminate(self):
        self.events.append("terminate")
        if self.terminate_stops:
            self.alive = False
            self.exitcode = -15

    def kill(self):
        self.events.append("kill")
        if self.kill_stops:
            self.alive = False
            self.exitcode = -9

    def join(self, timeout=None):
        self.join_timeouts.append(timeout)
        self.events.append(("join", timeout))
        if self.alive and self.exits_during_join:
            self.alive = False
            self.exitcode = self.natural_exitcode
        if not self.alive:
            self.reaped = True

    def close(self):
        assert not self.alive
        assert self.reaped
        self.events.append("close")
        self.closed = True


class _FakeContext:
    def __init__(self, parent, child, process):
        self.parent = parent
        self.child = child
        self.process = process

    def Pipe(self, *, duplex):
        assert duplex is False
        return self.parent, self.child

    def Process(self, *, target, args):
        assert callable(target)
        assert args[-1] is self.child
        return self.process


def _assert_bounded_joins(process):
    assert process.join_timeouts
    assert all(
        timeout is not None
        and type(timeout) in (int, float)
        and math.isfinite(timeout)
        and timeout >= 0
        and timeout <= 1.0
        for timeout in process.join_timeouts
    )


def test_isolated_worker_closes_process_and_pipe_handles(monkeypatch):
    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess(exits_during_join=True)
    context = _FakeContext(parent, child, process)
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)
    encoded = pickle.dumps(("ok",))
    real_loads = admission.pickle.loads

    def loads_after_worker_exit(payload):
        assert process.alive is False
        return real_loads(payload)

    monkeypatch.setattr(
        admission, "_wait_for_child", lambda *_args, **_kwargs: encoded
    )
    monkeypatch.setattr(admission.pickle, "loads", loads_after_worker_exit)

    result = admission._run_isolated(
        lambda: None,
        (),
        timeout_seconds=1.0,
        max_process_bytes=1_000_000,
        label="test",
    )

    assert result == ("ok",)
    assert parent.closed and child.closed
    assert process.reaped and process.closed
    _assert_bounded_joins(process)
    assert "terminate" not in process.events
    assert "kill" not in process.events


def test_isolated_worker_rejects_parent_growth_after_deserialization(monkeypatch):
    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess(exits_during_join=True)
    context = _FakeContext(parent, child, process)
    parent_rss = iter((1, 10_000_001))
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)
    monkeypatch.setattr(
        admission, "_resident_bytes", lambda *_args, **_kwargs: next(parent_rss)
    )
    monkeypatch.setattr(
        admission, "_wait_for_child", lambda *_args, **_kwargs: pickle.dumps(("ok",))
    )

    with admission._aggregate_process_budget(
        max_parent_process_bytes=10_000_000,
        max_aggregate_process_bytes=20_000_000,
    ):
        with pytest.raises(
            ResourceGateError, match="parent process bytes after worker exit"
        ):
            admission._run_isolated(
                lambda: None,
                (),
                timeout_seconds=1.0,
                max_process_bytes=10_000_000,
                label="test",
            )

    assert parent.closed and child.closed
    assert process.reaped and process.closed


def test_isolated_worker_cleans_up_when_waiting_fails(monkeypatch):
    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess()
    context = _FakeContext(parent, child, process)
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)

    def fail_wait(*_args, **_kwargs):
        raise ResourceGateError("simulated wait failure")

    monkeypatch.setattr(admission, "_wait_for_child", fail_wait)
    with pytest.raises(ResourceGateError, match="simulated wait failure"):
        admission._run_isolated(
            lambda: None,
            (),
            timeout_seconds=1.0,
            max_process_bytes=1_000_000,
            label="test",
        )

    assert parent.closed and child.closed
    assert process.reaped and process.closed
    _assert_bounded_joins(process)
    assert "terminate" in process.events
    assert "kill" not in process.events


def test_isolated_worker_cleans_up_if_start_launches_then_raises(monkeypatch):
    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess()
    context = _FakeContext(parent, child, process)
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)

    def launch_then_fail():
        process.started = True
        process.alive = True
        process.events.append("start")
        raise RuntimeError("simulated interrupted start")

    monkeypatch.setattr(process, "start", launch_then_fail)
    with pytest.raises(RuntimeError, match="simulated interrupted start"):
        admission._run_isolated(
            lambda: None,
            (),
            timeout_seconds=1.0,
            max_process_bytes=1_000_000,
            label="test",
        )

    assert parent.closed and child.closed
    assert process.reaped and process.closed
    _assert_bounded_joins(process)
    assert "terminate" in process.events


def test_isolated_worker_closes_pipes_if_process_construction_fails(monkeypatch):
    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess()
    context = _FakeContext(parent, child, process)

    def fail_process_construction(**_kwargs):
        raise RuntimeError("simulated process construction failure")

    monkeypatch.setattr(context, "Process", fail_process_construction)
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)

    with pytest.raises(RuntimeError, match="simulated process construction failure"):
        admission._run_isolated(
            lambda: None,
            (),
            timeout_seconds=1.0,
            max_process_bytes=1_000_000,
            label="test",
        )

    assert parent.closed and child.closed
    assert process.started is False
    assert process.closed is False


def test_isolated_worker_kills_a_process_that_ignores_terminate(monkeypatch):
    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess(terminate_stops=False)
    context = _FakeContext(parent, child, process)
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)
    monkeypatch.setattr(
        admission,
        "_wait_for_child",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ResourceGateError("simulated wait failure")
        ),
    )

    with pytest.raises(ResourceGateError, match="simulated wait failure"):
        admission._run_isolated(
            lambda: None,
            (),
            timeout_seconds=1.0,
            max_process_bytes=1_000_000,
            label="test",
        )

    assert parent.closed and child.closed
    assert process.reaped and process.closed
    _assert_bounded_joins(process)
    assert process.events.index("terminate") < process.events.index("kill")


def test_cleanup_does_not_close_when_worker_liveness_is_unknown(monkeypatch):
    process = _FakeProcess(terminate_stops=False, kill_stops=False)
    process.start()

    def unknown_liveness():
        raise OSError("liveness unavailable")

    monkeypatch.setattr(process, "is_alive", unknown_liveness)

    assert admission._cleanup_worker_process(process, started=True) is False
    assert process.closed is False
    assert "close" not in process.events
    _assert_bounded_joins(process)


def test_cleanup_does_not_close_a_worker_that_survives_kill():
    process = _FakeProcess(terminate_stops=False, kill_stops=False)
    process.start()

    assert admission._cleanup_worker_process(process, started=True) is False
    assert process.alive is True
    assert process.closed is False
    assert "terminate" in process.events
    assert "kill" in process.events
    _assert_bounded_joins(process)


def test_cleanup_failure_does_not_mask_wait_error(monkeypatch):
    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess()
    context = _FakeContext(parent, child, process)
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)
    primary = ResourceGateError("simulated wait failure")
    monkeypatch.setattr(
        admission,
        "_wait_for_child",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(primary),
    )
    monkeypatch.setattr(
        admission,
        "_cleanup_worker_process",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("simulated cleanup failure")
        ),
    )

    with pytest.raises(ResourceGateError, match="simulated wait failure") as caught:
        admission._run_isolated(
            lambda: None,
            (),
            timeout_seconds=1.0,
            max_process_bytes=1_000_000,
            label="test",
        )

    assert parent.closed and child.closed
    assert caught.value is primary
    assert str(caught.value) == "simulated wait failure"
    assert caught.value.__notes__ == [
        "test worker cleanup could not confirm process exit (RuntimeError)"
    ]


def test_incomplete_cleanup_adds_a_note_to_the_primary_error(monkeypatch):
    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess(terminate_stops=False, kill_stops=False)
    context = _FakeContext(parent, child, process)
    primary = ResourceGateError("simulated wait failure")
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)
    monkeypatch.setattr(
        admission,
        "_wait_for_child",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(primary),
    )

    with pytest.raises(ResourceGateError, match="simulated wait failure") as caught:
        admission._run_isolated(
            lambda: None,
            (),
            timeout_seconds=1.0,
            max_process_bytes=1_000_000,
            label="test",
        )

    assert caught.value is primary
    assert str(caught.value) == "simulated wait failure"
    assert caught.value.__notes__ == [
        "test worker cleanup could not confirm process exit"
    ]
    assert process.alive is True
    assert process.closed is False
    _assert_bounded_joins(process)


def test_incomplete_cleanup_fails_a_nominal_result_closed(monkeypatch):
    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess(exits_during_join=True)
    context = _FakeContext(parent, child, process)
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)
    monkeypatch.setattr(
        admission,
        "_wait_for_child",
        lambda *_args, **_kwargs: pickle.dumps(("payload",)),
    )
    monkeypatch.setattr(
        admission, "_cleanup_worker_process", lambda *_args, **_kwargs: False
    )

    ambient = LookupError("ambient caller error")
    try:
        raise ambient
    except LookupError:
        with pytest.raises(
            ResourceGateError, match="worker cleanup could not confirm process exit"
        ):
            admission._run_isolated(
                lambda: None,
                (),
                timeout_seconds=1.0,
                max_process_bytes=1_000_000,
                label="test",
            )

    assert parent.closed and child.closed
    assert getattr(ambient, "__notes__", []) == []


def test_wait_error_prefers_an_observed_sigxcpu_exit(monkeypatch):
    sigxcpu = getattr(admission.signal, "SIGXCPU", None)
    if sigxcpu is None:
        pytest.skip("SIGXCPU is unavailable")

    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess()
    context = _FakeContext(parent, child, process)
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)

    def fail_after_cpu_exit(*_args, **_kwargs):
        process.alive = False
        process.exitcode = -sigxcpu
        raise ResourceGateError("simulated RSS measurement failure")

    monkeypatch.setattr(admission, "_wait_for_child", fail_after_cpu_exit)

    with pytest.raises(ResourceGateError, match="exceeded its CPU limit"):
        admission._run_isolated(
            lambda: None,
            (),
            timeout_seconds=1.0,
            max_process_bytes=1_000_000,
            label="test",
        )

    assert process.reaped and process.closed


def test_payload_followed_by_sigxcpu_is_rejected(monkeypatch):
    sigxcpu = getattr(admission.signal, "SIGXCPU", None)
    if sigxcpu is None:
        pytest.skip("SIGXCPU is unavailable")

    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess(exits_during_join=True, natural_exitcode=-sigxcpu)
    context = _FakeContext(parent, child, process)
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)
    monkeypatch.setattr(
        admission,
        "_wait_for_child",
        lambda *_args, **_kwargs: pickle.dumps(("payload",)),
    )

    with pytest.raises(ResourceGateError, match="exceeded its CPU limit"):
        admission._run_isolated(
            lambda: None,
            (),
            timeout_seconds=1.0,
            max_process_bytes=1_000_000,
            label="test",
        )

    assert process.reaped and process.closed
    _assert_bounded_joins(process)


def test_isolated_worker_rejects_a_payload_before_process_exit(monkeypatch):
    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess()
    context = _FakeContext(parent, child, process)
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)
    monkeypatch.setattr(
        admission, "_wait_for_child", lambda *_args, **_kwargs: pickle.dumps(("ok",))
    )

    with pytest.raises(ResourceGateError, match="exceeded 1.000 seconds"):
        admission._run_isolated(
            lambda: None,
            (),
            timeout_seconds=1.0,
            max_process_bytes=1_000_000,
            label="test",
        )

    assert process.reaped and process.closed
    _assert_bounded_joins(process)
    assert "terminate" in process.events


def test_isolated_worker_rejects_an_abnormal_exit_after_payload(monkeypatch):
    parent = _FakeConnection()
    child = _FakeConnection()
    process = _FakeProcess(exits_during_join=True, natural_exitcode=3)
    context = _FakeContext(parent, child, process)
    monkeypatch.setattr(admission, "_multiprocessing_context", lambda: context)
    monkeypatch.setattr(
        admission, "_wait_for_child", lambda *_args, **_kwargs: pickle.dumps(("ok",))
    )

    with pytest.raises(ResourceGateError, match="abnormally with exitcode 3"):
        admission._run_isolated(
            lambda: None,
            (),
            timeout_seconds=1.0,
            max_process_bytes=1_000_000,
            label="test",
        )

    assert process.reaped and process.closed
    _assert_bounded_joins(process)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_resource_gate_rejects_invalid_timeouts_before_starting_a_worker(
    timeout, monkeypatch
):
    def worker_must_not_start():
        raise AssertionError("worker must not start")

    monkeypatch.setattr(
        admission,
        "_multiprocessing_context",
        worker_must_not_start,
    )
    with pytest.raises(ValueError, match="timeout_seconds must be finite and positive"):
        run_resource_gate(
            "def run(value):\n    return value\n",
            [("run", (0,))],
            timeout_seconds=timeout,
            max_python_bytes=1_000_000,
        )


@pytest.mark.parametrize(
    ("argument", "value"),
    [
        ("max_python_bytes", 0),
        ("max_python_bytes", float("nan")),
        ("max_process_bytes", 0),
        ("max_process_bytes", float("inf")),
    ],
)
def test_resource_gate_rejects_invalid_memory_budgets_before_starting_a_worker(
    argument, value, monkeypatch
):
    def worker_must_not_start():
        raise AssertionError("worker must not start")

    monkeypatch.setattr(
        admission,
        "_multiprocessing_context",
        worker_must_not_start,
    )
    options = {
        "timeout_seconds": 1.0,
        "max_python_bytes": 1_000_000,
        "max_process_bytes": 2_000_000,
    }
    options[argument] = value
    with pytest.raises(ValueError, match=rf"{argument} must be a positive integer"):
        run_resource_gate(
            "def run(value):\n    return value\n",
            [("run", (0,))],
            **options,
        )


def test_identity_gate_rejects_invalid_python_budget_before_starting_a_worker(
    monkeypatch,
):
    def worker_must_not_start(*_args, **_kwargs):
        raise AssertionError("worker must not start")

    monkeypatch.setattr(admission, "_run_isolated", worker_must_not_start)
    with pytest.raises(ValueError, match="max_python_bytes must be a positive integer"):
        run_area_bounce_identity_gate(
            "def forward(path):\n    return path\ndef inverse(path):\n    return path\n",
            [],
            timeout_seconds=1.0,
            max_python_bytes=float("nan"),
        )


def test_resource_gate_stops_time_and_memory_attacks():
    looping = "def run(value):\n    while True:\n        value += 1\n"
    with pytest.raises(ResourceGateError, match="exceeded"):
        run_resource_gate(looping, [("run", (0,))], timeout_seconds=0.2, max_python_bytes=1_000_000)

    allocating = "def run(value):\n    data = [value] * 2000000\n    return len(data)\n"
    with pytest.raises(ResourceGateError, match="allocated|bytes"):
        run_resource_gate(allocating, [("run", (0,))], timeout_seconds=2.0, max_python_bytes=1_000_000)


def test_resource_gate_counts_top_level_retained_allocations():
    source = "cache = [0] * 200000\ndef run(value):\n    return value\n"
    with pytest.raises(ResourceGateError, match="allocated|bytes"):
        run_resource_gate(
            source,
            [("run", (0,))],
            timeout_seconds=2.0,
            max_python_bytes=1_000_000,
        )


def test_resource_gate_accepts_the_known_statistic_at_scale():
    report = run_resource_gate(
        KNOWN_GOOD,
        [("statistic", (partition,)) for _, (partition,) in nc_probes(256)],
        timeout_seconds=3.0,
        max_python_bytes=32_000_000,
    )
    assert len(report.results) == len(nc_probes(256))


def test_resource_gate_bounds_worker_output_transfer():
    source = "def run(value):\n    return 'x' * 9000000\n"
    with pytest.raises(ResourceGateError, match="IPC limit"):
        run_resource_gate(
            source,
            [("run", (0,))],
            timeout_seconds=3.0,
            max_python_bytes=16_000_000,
        )


# --------------------------------------------------------------------------
# Area/bounce identity gate
# --------------------------------------------------------------------------


def test_identity_gate_accepts_a_correct_bijection_at_tiny_size():
    report = run_area_bounce_identity_gate(
        ENUMERATION_BIJECTION,
        adversarial_dyck_paths(4, seed=1),
        timeout_seconds=5.0,
        max_python_bytes=64_000_000,
    )
    assert report.checked_paths == len(adversarial_dyck_paths(4, seed=1))


def test_identity_gate_rejects_a_wrong_map():
    with pytest.raises(ResourceGateError, match="rejected"):
        run_area_bounce_identity_gate(
            IDENTITY_MAP,
            adversarial_dyck_paths(8, seed=1),
            timeout_seconds=5.0,
            max_python_bytes=32_000_000,
        )


def test_identity_gate_rejects_enumeration_bijection_at_scale():
    with pytest.raises(ResourceGateError):
        run_area_bounce_identity_gate(
            ENUMERATION_BIJECTION,
            adversarial_dyck_paths(64, seed=1),
            timeout_seconds=1.0,
            max_python_bytes=32_000_000,
        )


@pytest.mark.parametrize(
    "evaluate",
    [
        admission.evaluate_area_bounce_bijection,
        admission.evaluate_polyomino_area_bounce_bijection,
        admission.evaluate_polyomino_transpose_bijection,
        admission.evaluate_macdonald_filling_bijection,
        admission.evaluate_parking_area_dinv_bijection,
        admission.evaluate_graph_sibling_tuft_bijection,
    ],
    ids=["area_bounce", "polyomino", "transpose", "macdonald", "parking", "graph"],
)
def test_bijection_numerical_stage_rejects_an_empty_target(evaluate):
    """`all(...)` over no cases is True, so an empty target must fail closed.

    The statistic side is protected by the validated target loader; the
    bijection evaluators take the target as a caller-supplied mapping.
    """

    with pytest.raises(GateError, match="no scored cases"):
        evaluate(lambda obj: obj, lambda obj: obj, {}, None)


def test_unseeded_numerical_order_preserves_streaming_input():
    objects = iter(("first", "second"))

    assert admission._shuffled_objects(objects, None) is objects


def test_bijection_numerical_stage_reports_determinism():
    numerical, determinism, _elapsed, _peak = admission._run_numerical_isolated(
        kind="area_bounce",
        source=ENUMERATION_BIJECTION,
        target_terms=admission.public_area_bounce_terms(3),
        timeout_seconds=10.0,
        max_python_bytes=64_000_000,
        max_process_bytes=128_000_000,
    )
    assert numerical["passed"]
    assert _peak is None
    assert determinism is not None
    assert determinism.fresh_namespaces == 2
    assert determinism.replay_seed is not None
    # STATE-1 claims the replay covers `forward` and `inverse` alike.  The
    # evaluator calls each of them twice per public path, so both callables are
    # recorded exactly when the count is four times the public path count.
    public_paths = sum(len(admission.enumerate_dyck_paths(n)) for n in (1, 2, 3))
    assert determinism.checked_objects == 4 * public_paths
    assert determinism.replayed_calls == 2 * determinism.checked_objects


# The `inverse` copy is standalone so that it does not share the first-call
# state installed in `forward`; otherwise the cheat would be self-defeating.
STANDALONE_INVERSE = """def inverse(path):
    n = len(path) // 2
    key = (area(path), bounce(path))
    source = []
    target = []
    for candidate in paths(n):
        candidate_key = (area(candidate), bounce(candidate))
        if candidate_key == key:
            source.append(candidate)
        if candidate_key == (key[1], key[0]):
            target.append(candidate)
    source.sort()
    target.sort()
    return target[source.index(path)]
"""

FIRST_CALL_ONLY_BIJECTION = ENUMERATION_BIJECTION.replace(
    "def inverse(path):\n    return forward(path)\n", STANDALONE_INVERSE
).replace(
    "def forward(path):\n    n = len(path) // 2\n",
    "seen = set()\n\ndef forward(path):\n    n = len(path) // 2\n"
    "    if path in seen:\n        return path\n"
    "    seen.add(path)\n",
)


def test_bijection_rejects_a_first_call_only_forward():
    numerical, determinism, _elapsed, _peak = admission._run_numerical_isolated(
        kind="area_bounce",
        source=FIRST_CALL_ONLY_BIJECTION,
        target_terms=admission.public_area_bounce_terms(3),
        timeout_seconds=10.0,
        max_python_bytes=64_000_000,
        max_process_bytes=128_000_000,
    )
    # The round-trip identities already call `forward` twice per path, so a
    # first-call-only map never survives to the replay stage.
    assert not numerical["passed"]
    assert determinism is None


# --------------------------------------------------------------------------
# End-to-end submission adapters
# --------------------------------------------------------------------------


def test_asm_submission_that_passes_numerical_completes_post_numerical_gates(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        admission,
        "_run_numerical_isolated",
        lambda **_kwargs: ({"passed": True}, None, 0.0, 0),
    )
    source = "def statistic(matrix):\n    return matrix.inversion_number\n"

    result = admission.evaluate_asm_q_submission(
        source=source,
        probes=lambda: admission.adversarial_asm_probes(16, seed=7),
        problem_dir=ROOT / "problems/q_statistic_discovery/asm_dpp_weight_q_stat",
        timeout_seconds=5.0,
        max_python_bytes=32_000_000,
        max_process_bytes=192 * 1024 * 1024,
    )

    assert result["passed"]
    assert result["checker_stage"] == "complete"
    assert len(result["resources"].results) > 0


def test_noncrossing_known_good_passes_every_stage():
    result = evaluate_noncrossing_submission(
        source=KNOWN_GOOD,
        probes=lambda: adversarial_noncrossing_probes(128),
        problem_dir=PROBLEM,
        timeout_seconds=3.0,
        max_python_bytes=32_000_000,
    )
    assert result["passed"]
    assert result["checker_stage"] == "complete"
    assert result["numerical"]["q_equals_1"]["passed"]
    assert result["numerical"]["full_qt"]["passed"]
    assert result["determinism"].checked_objects > 0
    assert result["numerical_peak_python_bytes"] > 0
    assert result["determinism"].replayed_calls == 2 * result["determinism"].checked_objects


def test_noncrossing_allows_intermediate_large_integer_without_audit():
    source = KNOWN_GOOD.replace(
        "    return total\n",
        "    waste = 1\n"
        "    for step in range(2 * partition.n):\n"
        "        waste = waste + waste\n"
        "    return total + waste - waste\n",
    )
    result = evaluate_noncrossing_submission(
        source=source,
        probes=lambda: adversarial_noncrossing_probes(128),
        problem_dir=PROBLEM,
        timeout_seconds=3.0,
        max_python_bytes=32_000_000,
    )
    assert result["passed"]
    assert "value_audit" not in result


def test_noncrossing_area_only_short_circuits_at_numerical():
    result = evaluate_noncrossing_submission(
        source=AREA_ONLY,
        probes=lambda: adversarial_noncrossing_probes(128),
        problem_dir=PROBLEM,
        timeout_seconds=3.0,
        max_python_bytes=32_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"
    assert result["numerical"]["q_equals_1"]["passed"]
    assert not result["numerical"]["full_qt"]["passed"]
    assert result["resources"] is None




def test_noncrossing_rejects_invalid_outputs_on_large_resource_probes():
    source = KNOWN_GOOD.replace(
        "def statistic(partition):\n",
        "def statistic(partition):\n    if partition.n > 10:\n        return None\n",
    )
    with pytest.raises(ResourceGateError, match="expected a nonnegative integer"):
        evaluate_noncrossing_submission(
            source=source,
            probes=lambda: adversarial_noncrossing_probes(128),
            problem_dir=PROBLEM,
            timeout_seconds=3.0,
            max_python_bytes=32_000_000,
        )


def test_noncrossing_rejects_first_call_only_statistic():
    source = (
        "seen = set()\n\n"
        + KNOWN_GOOD.replace(
            "def statistic(partition):\n",
            "def statistic(partition):\n"
            "    key = (partition.n, partition.blocks)\n"
            "    if key in seen:\n"
            "        return 0\n"
            "    seen.add(key)\n",
        )
    )
    with pytest.raises(
        ResourceGateError,
        match="diagnostic replay seed .*official scored CLI intentionally ignores",
    ):
        evaluate_noncrossing_submission(
            source=source,
            probes=lambda: adversarial_noncrossing_probes(128),
            problem_dir=PROBLEM,
            timeout_seconds=3.0,
            max_python_bytes=32_000_000,
        )


def test_noncrossing_accepts_deterministic_memoization():
    source = (
        "cache = {}\n\n"
        + KNOWN_GOOD.replace(
            "def statistic(partition):\n",
            "def statistic(partition):\n"
            "    key = (partition.n, partition.blocks)\n"
            "    if key in cache:\n"
            "        return cache[key]\n",
        )
        .replace(
            "    if not repeated_maxima:\n        return 0\n",
            "    if not repeated_maxima:\n        cache[key] = 0\n        return 0\n",
        )
        .replace(
            "    return total\n",
            "    cache[key] = total\n    return total\n",
        )
    )
    result = evaluate_noncrossing_submission(
        source=source,
        probes=lambda: adversarial_noncrossing_probes(128),
        problem_dir=PROBLEM,
        timeout_seconds=3.0,
        max_python_bytes=32_000_000,
    )
    assert result["passed"]
    assert result["determinism"].fresh_namespaces == 2


def test_noncrossing_stage_order(monkeypatch):
    order = []
    numerical_kwargs = {}

    def safety(source):
        order.append("safety")
        return ("statistic",)

    def economy(source, *, limits):
        order.append("economy")

    def numerical(**kwargs):
        order.append("numerical")
        numerical_kwargs.update(kwargs)
        return (
            {"passed": True},
            admission.DeterminismReport(
                checked_objects=1,
                replayed_calls=2,
                fresh_namespaces=2,
            ),
            0.0,
            0,
        )

    def resources(*args, **kwargs):
        order.append("resources")
        return admission.ResourceReport(
            elapsed_seconds=0.0,
            peak_python_bytes=0,
            results=tuple(0 for _ in args[1]),
        )

    monkeypatch.setattr(admission, "check_capability_screen", safety)
    monkeypatch.setattr(admission, "check_source_economy", economy)
    monkeypatch.setattr(admission, "_run_numerical_isolated", numerical)
    monkeypatch.setattr(admission, "run_resource_gate", resources)

    result = admission.evaluate_noncrossing_submission(
        source="ignored",
        probes=[("statistic", (NoncrossingPartition([(1,)], n=1, validate=False),))],
        problem_dir=PROBLEM,
        timeout_seconds=1.0,
        max_python_bytes=1_000_000,
    )
    assert result["passed"]
    assert order == ["safety", "economy", "numerical", "resources"]
    # Exhaustive numerical checks include trusted enumeration overhead, so they
    # use the process ceiling; the tighter Python-allocation cap applies to the
    # adversarial resource and identity gates.
    assert numerical_kwargs["max_python_bytes"] == 256_000_000
    assert numerical_kwargs["max_process_bytes"] == 256_000_000


# --------------------------------------------------------------------------
# End-to-end area/bounce
# --------------------------------------------------------------------------


def test_area_bounce_identity_map_short_circuits_at_numerical():
    result = evaluate_area_bounce_submission(
        source=IDENTITY_MAP,
        probes=lambda: adversarial_dyck_probes(128),
        target_terms=public_area_bounce_terms(5),
        timeout_seconds=3.0,
        max_python_bytes=32_000_000,
    )
    assert not result["passed"]
    assert result["checker_stage"] == "numerical"


def test_area_bounce_enumeration_bijection_is_blocked_after_numerical():
    # Correct on the tiny public sizes, but blocked by a resource-limited gate
    # once it must run on large objects.
    with pytest.raises(ResourceGateError):
        evaluate_area_bounce_submission(
            source=ENUMERATION_BIJECTION,
            probes=lambda: adversarial_dyck_probes(64),
            target_terms=public_area_bounce_terms(4),
            timeout_seconds=1.0,
            max_python_bytes=32_000_000,
        )
