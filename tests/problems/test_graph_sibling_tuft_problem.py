from __future__ import annotations

from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path
import re
import shutil

import pytest

from qtbench.combinatorics import ConnectedGraph
from qtbench.evaluation import (
    ResourceGateError,
    adversarial_connected_graphs,
    load_graph_sibling_tuft_terms,
    run_graph_sibling_tuft_identity_gate,
)
from qtbench.evaluation.admission import evaluate_graph_sibling_tuft_bijection

ROOT = Path(__file__).resolve().parents[2]
PROBLEM = ROOT / "problems/exchanging_bijection/graph_sibling_tuft_exchange"
EXPECTED_COUNTS = {1: 1, 2: 1, 3: 2, 4: 6, 5: 21, 6: 112, 7: 853}


def test_public_targets_are_complete_and_symmetric():
    targets = load_graph_sibling_tuft_terms(PROBLEM)
    assert set(targets) == set(EXPECTED_COUNTS)
    for n, case in targets.items():
        distribution = Counter(
            {(sibling, tuft): coefficient for sibling, tuft, coefficient in case["terms"]}
        )
        assert len(case["graphs"]) == sum(distribution.values()) == EXPECTED_COUNTS[n]
        assert len(case["graphs"]) == len(set(case["graphs"]))
        assert distribution == Counter(
            {(tuft, sibling): count for (sibling, tuft), count in distribution.items()}
        )


@pytest.mark.parametrize(
    "defect",
    [
        "noncanonical",
        "wrong_size",
        "duplicate_graph",
        "wrong_count",
        "duplicate_case",
        "boolean_case_count",
    ],
)
def test_loader_rejects_malformed_graph_corpora(tmp_path, defect):
    problem = tmp_path / "problem"
    shutil.copytree(PROBLEM, problem, ignore=shutil.ignore_patterns("__pycache__"))
    path = problem / "data/instances.json"
    data = json.loads(path.read_text())
    if defect == "noncanonical":
        data["cases"][2]["entries"][0]["graph"] = "3:6"
    elif defect == "wrong_size":
        data["cases"][2]["entries"][0]["graph"] = "2:1"
    elif defect == "duplicate_graph":
        data["cases"][2]["entries"][1]["graph"] = data["cases"][2]["entries"][0]["graph"]
    elif defect == "wrong_count":
        data["cases"][0]["count"] += 1
    elif defect == "duplicate_case":
        data["cases"].insert(1, dict(data["cases"][0]))
        data["case_count"] += 1
    else:
        data["cases"] = data["cases"][:1]
        data["case_count"] = True
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_graph_sibling_tuft_terms(problem)


def test_loader_rejects_duplicate_json_keys_in_graph_corpus(tmp_path):
    problem = tmp_path / "problem"
    shutil.copytree(PROBLEM, problem, ignore=shutil.ignore_patterns("__pycache__"))
    path = problem / "data/instances.json"
    document = path.read_text(encoding="utf-8")
    document, replacements = re.subn(
        r'("schema_version"\s*:\s*"[^"]*")',
        r"\1,\1",
        document,
        count=1,
    )
    assert replacements == 1
    path.write_text(
        document,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate JSON object key"):
        load_graph_sibling_tuft_terms(problem)


def test_loader_rejects_nonobject_graph_corpus(tmp_path):
    problem = tmp_path / "problem"
    shutil.copytree(PROBLEM, problem, ignore=shutil.ignore_patterns("__pycache__"))
    path = problem / "data/instances.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="must contain a JSON object"):
        load_graph_sibling_tuft_terms(problem)


def test_known_statistics_and_reductions_match_instances():
    spec = importlib.util.spec_from_file_location("known", PROBLEM / "known_statistics.py")
    assert spec is not None and spec.loader is not None
    known = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(known)
    data = json.loads((PROBLEM / "data/instances.json").read_text())
    for case in data["cases"]:
        for entry in case["entries"]:
            graph = ConnectedGraph(entry["graph"])
            assert known.sibling_number(graph) == entry["sibling_number"]
            assert known.tuft_number(graph) == entry["tuft_number"]
            assert known.reduction(graph) == entry["reduction"]


def test_rank_matching_witness_passes_the_complete_public_checker():
    targets = load_graph_sibling_tuft_terms(PROBLEM)
    mapping = {}
    for case in targets.values():
        fibers = defaultdict(list)
        for encoding in case["graphs"]:
            graph = ConnectedGraph(encoding, validate=False)
            fibers[(graph.reduction, graph.sibling_number(), graph.tuft_number())].append(encoding)
        for key, source in fibers.items():
            reduction, sibling, tuft = key
            target = fibers[(reduction, tuft, sibling)]
            for left, right in zip(sorted(source), sorted(target)):
                mapping[left] = right
    result = evaluate_graph_sibling_tuft_bijection(
        lambda graph: mapping[graph.encoding],
        lambda graph: mapping[graph.encoding],
        targets,
    )
    assert result["passed"]


def test_identity_map_fails_the_exchange():
    result = evaluate_graph_sibling_tuft_bijection(
        lambda graph: graph.encoding,
        lambda graph: graph.encoding,
        load_graph_sibling_tuft_terms(PROBLEM),
    )
    assert not result["passed"]
    assert result["case_results"][-1]["first_failure"] is not None


def test_public_checker_rejects_noncanonical_output():
    graph = ConnectedGraph("3:3")
    result = evaluate_graph_sibling_tuft_bijection(
        lambda _graph: "3:6",
        lambda obj: obj.encoding,
        {3: {"terms": [[0, 2, 1]], "graphs": [graph.encoding]}},
    )
    assert not result["passed"]
    assert "noncanonical" in result["case_results"][0]["first_failure"]


def test_public_checker_rejects_a_reduction_changing_exchange():
    left = ConnectedGraph("5:03a")
    right = ConnectedGraph("5:0fe")
    assert (left.sibling_number(), left.tuft_number()) == (0, 1)
    assert (right.sibling_number(), right.tuft_number()) == (1, 0)
    assert left.reduction != right.reduction
    toggle = {left.encoding: right.encoding, right.encoding: left.encoding}
    result = evaluate_graph_sibling_tuft_bijection(
        lambda graph: toggle[graph.encoding],
        lambda graph: toggle[graph.encoding],
        {5: {"terms": [[0, 1, 1], [1, 0, 1]], "graphs": list(toggle)}},
    )
    assert not result["passed"]
    assert "reduction was not preserved" in result["case_results"][0]["first_failure"]


def test_large_identity_gate_rejects_identity_map():
    source = "def forward(graph):\n    return graph.encoding\n\ndef inverse(graph):\n    return graph.encoding\n"
    with pytest.raises(ResourceGateError, match="exchange"):
        run_graph_sibling_tuft_identity_gate(
            source,
            [ConnectedGraph("3:3")],
            timeout_seconds=5.0,
            max_python_bytes=32_000_000,
        )


def test_large_identity_gate_rejects_a_reduction_changing_exchange():
    source = """\
def forward(graph):
    if graph.encoding == '5:03a':
        return '5:0fe'
    return '5:03a'

def inverse(graph):
    if graph.encoding == '5:03a':
        return '5:0fe'
    return '5:03a'
"""
    with pytest.raises(ResourceGateError, match="reduction was not preserved"):
        run_graph_sibling_tuft_identity_gate(
            source,
            [ConnectedGraph("5:03a")],
            timeout_seconds=5.0,
            max_python_bytes=32_000_000,
        )


def test_large_identity_gate_rejects_noncanonical_round_trip():
    source = """\
def forward(graph):
    if graph.encoding == '4:07':
        return '4:3f'
    return '4:07'

def inverse(graph):
    if graph.encoding == '4:07':
        return '4:3f'
    return '4:3e'
"""
    with pytest.raises(ResourceGateError, match="round-trip failed"):
        run_graph_sibling_tuft_identity_gate(
            source,
            [ConnectedGraph("4:07")],
            timeout_seconds=5.0,
            max_python_bytes=32_000_000,
        )


def test_large_identity_gate_checks_the_inverse_preimage_identity():
    source = """\
def forward(graph):
    if graph.encoding == '4:1f':
        return '4:0d'
    if graph.encoding == '4:0f':
        return '4:1f'
    return '4:1f'

def inverse(graph):
    if graph.encoding == '4:1f':
        return '4:0f'
    if graph.encoding == '4:0d':
        return '4:1f'
    return '4:1f'
"""
    with pytest.raises(ResourceGateError, match="inverse sibling/tuft exchange"):
        run_graph_sibling_tuft_identity_gate(
            source,
            [ConnectedGraph("4:1f")],
            timeout_seconds=5.0,
            max_python_bytes=32_000_000,
        )


def test_large_forced_exchange_fits_the_default_gate_budget():
    n = 1024
    edge_count = n * (n - 1) // 2
    width = (edge_count + 3) // 4
    star = f"{n}:{((1 << (n - 1)) - 1):0{width}x}"
    complete = f"{n}:{((1 << edge_count) - 1):0{width}x}"
    source = """\
def star(graph):
    n = graph.n
    width = (n * (n - 1) // 2 + 3) // 4
    tail_width = (n - 1 + 3) // 4
    first = ('f', '1', '3', '7')[(n - 1) % 4]
    return str(n) + ':' + '0' * (width - tail_width) + first + 'f' * (tail_width - 1)

def complete(graph):
    n = graph.n
    edge_count = n * (n - 1) // 2
    width = (edge_count + 3) // 4
    first = ('f', '1', '3', '7')[edge_count % 4]
    return str(n) + ':' + first + 'f' * (width - 1)

def forward(graph):
    if graph.tuft_number() == graph.n - 1:
        return complete(graph)
    return star(graph)

def inverse(graph):
    return forward(graph)
"""
    report = run_graph_sibling_tuft_identity_gate(
        source,
        [ConnectedGraph(star, validate=False), ConnectedGraph(complete, validate=False)],
        timeout_seconds=2.0,
        max_python_bytes=32_000_000,
    )
    assert report.checked_paths == 2


def test_adversarial_connected_graphs_include_large_extreme_pairs():
    graphs = adversarial_connected_graphs(64, seed=7)
    assert {graph.n for graph in graphs} >= {7, 16, 32, 64}
    for n in (16, 32, 64):
        extremes = [graph for graph in graphs if graph.n == n]
        assert sorted((graph.sibling_number(), graph.tuft_number()) for graph in extremes) == [
            (0, n - 1),
            (n - 1, 0),
        ]
