from __future__ import annotations

from dataclasses import dataclass

import pytest

import qtbench.evaluation.admission as admission


SOURCE = """\
def forward(item):
    return item.encoding

def inverse(item):
    return item.encoding
"""

TIMEOUT_SECONDS = 5.0
NUMERICAL_TIMEOUT_SECONDS = 11.0
MAX_PYTHON_BYTES = 32_000_000
MAX_PROCESS_BYTES = 192 * 1024 * 1024


@dataclass(frozen=True)
class AdapterCase:
    evaluator: str
    numerical_kind: str
    value_probes: str
    hardener: str
    identity_gate: str
    scaled_hardening_attribute: str | None = None


CASES = (
    AdapterCase(
        evaluator="evaluate_parking_area_dinv_submission",
        numerical_kind="parking_area_dinv",
        value_probes="adversarial_parking_function_probes",
        hardener="_hardened_parking_functions",
        identity_gate="run_parking_area_dinv_identity_gate",
    ),
    AdapterCase(
        evaluator="evaluate_graph_sibling_tuft_submission",
        numerical_kind="graph_sibling_tuft",
        value_probes="adversarial_connected_graph_probes",
        hardener="_hardened_connected_graphs",
        identity_gate="run_graph_sibling_tuft_identity_gate",
    ),
    AdapterCase(
        evaluator="evaluate_shifted_pq_submission",
        numerical_kind="shifted_pq",
        value_probes="adversarial_shifted_pq_probes",
        hardener="_hardened_shifted_pq_tableaux",
        identity_gate="run_shifted_pq_identity_gate",
    ),
    AdapterCase(
        evaluator="evaluate_successive_rank_submission",
        numerical_kind="successive_rank",
        value_probes="adversarial_successive_rank_probes",
        hardener="adversarial_successive_rank_partitions",
        identity_gate="run_successive_rank_identity_gate",
        scaled_hardening_attribute="weight",
    ),
    AdapterCase(
        evaluator="evaluate_partition_matrix_inversion_submission",
        numerical_kind="partition_matrix_inversion",
        value_probes="adversarial_partition_matrix_inversion_probes",
        hardener="adversarial_partition_matrix_inversions",
        identity_gate="run_partition_matrix_inversion_identity_gate",
        scaled_hardening_attribute="n",
    ),
)

VALUE_PROBE_FACTORIES = tuple(case.value_probes for case in CASES)
HARDENERS = tuple(case.hardener for case in CASES)
IDENTITY_GATES = tuple(case.identity_gate for case in CASES)


def _unexpected_adapter_call(name):
    def fail(*_args, **_kwargs):
        pytest.fail(f"submission adapter called the wrong component: {name}")

    return fail


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.numerical_kind)
def test_scored_bijection_adapter_reaches_every_gate(monkeypatch, case) -> None:
    """Exercise the five scored adapters whose inner checkers had coverage only."""

    original_capability_screen = admission.check_capability_screen
    original_source_economy = admission.check_source_economy
    original_value_probes = getattr(admission, case.value_probes)
    original_hardener = getattr(admission, case.hardener)

    limits = admission.SourceLimits()
    target_terms = {"adapter": case.numerical_kind}
    supplied_calls = original_value_probes(8, seed=7)
    supplied_objects = [arguments[0] for _name, arguments in supplied_calls]

    order = []
    captured = {}
    numerical_report = {"passed": True, "kind": case.numerical_kind}
    determinism_report = admission.DeterminismReport(
        checked_objects=2,
        replayed_calls=4,
        fresh_namespaces=2,
    )

    def capability_screen(candidate_source):
        order.append("capability")
        assert candidate_source == SOURCE
        return original_capability_screen(candidate_source)

    def source_economy(candidate_source, *, limits):
        order.append("economy")
        assert candidate_source == SOURCE
        assert limits is captured["limits"]
        return original_source_economy(candidate_source, limits=limits)

    def numerical(**kwargs):
        order.append("numerical")
        captured["numerical_kwargs"] = kwargs
        return numerical_report, determinism_report, 0.25, 1_024

    def resolve_probes():
        order.append("supplied-probes")
        return supplied_calls

    captured["limits"] = limits
    monkeypatch.setattr(admission, "check_capability_screen", capability_screen)
    monkeypatch.setattr(admission, "check_source_economy", source_economy)
    monkeypatch.setattr(admission, "_run_numerical_isolated", numerical)
    for name in VALUE_PROBE_FACTORIES:
        monkeypatch.setattr(admission, name, _unexpected_adapter_call(name))
    for name in HARDENERS:
        monkeypatch.setattr(admission, name, _unexpected_adapter_call(name))
    for name in IDENTITY_GATES:
        monkeypatch.setattr(admission, name, _unexpected_adapter_call(name))

    expected_scales = None
    if case.scaled_hardening_attribute is None:

        def harden(objects):
            order.append("hardened")
            assert list(objects) == supplied_objects
            hardened = original_hardener(objects)
            assert hardened
            captured["hardened"] = hardened
            return hardened

        monkeypatch.setattr(admission, case.hardener, harden)
    else:
        max_size = max(
            getattr(obj, case.scaled_hardening_attribute) for obj in supplied_objects
        )
        expected_scales = sorted(
            {max(4, max_size // 4), max(4, max_size // 2), max(4, max_size)}
        )
        captured["scale_outputs"] = {}

        def harden(size, *, seed=None):
            if not captured["scale_outputs"]:
                order.append("hardened")
            assert seed is None
            hardened = original_hardener(size, seed=17)
            captured["scale_outputs"][size] = hardened
            return hardened

        monkeypatch.setattr(admission, case.hardener, harden)

    def identity_gate(
        candidate_source,
        objects,
        *,
        timeout_seconds,
        max_python_bytes,
        max_process_bytes,
    ):
        order.append("identity/resource")
        assert candidate_source == SOURCE
        assert timeout_seconds == TIMEOUT_SECONDS
        assert max_python_bytes == MAX_PYTHON_BYTES
        assert max_process_bytes == MAX_PROCESS_BYTES
        if case.scaled_hardening_attribute is None:
            assert objects is captured["hardened"]
        else:
            assert sorted(captured["scale_outputs"]) == expected_scales
            expected_objects = [
                *supplied_objects,
                *(
                    obj
                    for scale in expected_scales
                    for obj in captured["scale_outputs"][scale]
                ),
            ]
            assert list(objects) == expected_objects
        report = admission.IdentityReport(
            elapsed_seconds=0.5,
            peak_python_bytes=2_048,
            checked_paths=len(objects),
        )
        captured["identity_report"] = report
        return report

    monkeypatch.setattr(admission, case.identity_gate, identity_gate)

    evaluator = getattr(admission, case.evaluator)
    result = evaluator(
        source=SOURCE,
        probes=resolve_probes,
        target_terms=target_terms,
        timeout_seconds=TIMEOUT_SECONDS,
        max_python_bytes=MAX_PYTHON_BYTES,
        max_process_bytes=MAX_PROCESS_BYTES,
        numerical_timeout_seconds=NUMERICAL_TIMEOUT_SECONDS,
        limits=limits,
    )

    assert order == [
        "capability",
        "economy",
        "numerical",
        "supplied-probes",
        "hardened",
        "identity/resource",
    ]
    assert captured["numerical_kwargs"] == {
        "kind": case.numerical_kind,
        "source": SOURCE,
        "target_terms": target_terms,
        "timeout_seconds": NUMERICAL_TIMEOUT_SECONDS,
        "max_python_bytes": MAX_PROCESS_BYTES,
        "max_process_bytes": MAX_PROCESS_BYTES,
    }
    assert result["passed"]
    assert result["checker_stage"] == "complete"
    assert result["function_names"] == ("forward", "inverse")
    assert result["numerical"] is numerical_report
    assert result["determinism"] is determinism_report
    assert result["numerical_elapsed_seconds"] == 0.25
    assert result["numerical_peak_python_bytes"] == 1_024
    assert "value_audit" not in result
    assert result["resources"] is captured["identity_report"]
