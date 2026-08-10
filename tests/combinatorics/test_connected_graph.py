from __future__ import annotations

from qtbench.combinatorics import (
    ConnectedGraph,
    canonical_connected_graph,
    is_connected_graph_encoding,
)


def test_canonical_encoding_is_invariant_under_relabeling():
    edges = [(0, 1), (1, 2), (2, 3), (0, 3), (0, 2)]
    relabel = (2, 0, 3, 1)
    relabeled = [(relabel[left], relabel[right]) for left, right in edges]
    assert canonical_connected_graph(4, edges) == canonical_connected_graph(4, relabeled)


def test_encoding_validation_rejects_noncanonical_and_nonconnected_words():
    assert is_connected_graph_encoding("3:3")
    assert not is_connected_graph_encoding("3:6")
    assert not is_connected_graph_encoding("3:1")
    assert not is_connected_graph_encoding("03:3")
    assert not is_connected_graph_encoding("4:007")


def test_sibling_tuft_statistics_on_extreme_graphs():
    star = ConnectedGraph(canonical_connected_graph(4, [(0, 1), (0, 2), (0, 3)]))
    complete = ConnectedGraph(
        canonical_connected_graph(4, [(left, right) for left in range(4) for right in range(left + 1, 4)])
    )
    assert (star.sibling_number(), star.tuft_number()) == (0, 3)
    assert (complete.sibling_number(), complete.tuft_number()) == (3, 0)
    assert star.reduction == complete.reduction == "1:0"


def test_reduction_removes_leaves_but_keeps_the_leafless_core():
    cycle = canonical_connected_graph(4, [(0, 1), (1, 2), (2, 3), (3, 0)])
    cycle_with_leaf = ConnectedGraph(
        canonical_connected_graph(5, [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4)])
    )
    assert cycle_with_leaf.reduction == cycle


def test_k2_is_its_own_reduction():
    graph = ConnectedGraph("2:1")
    assert graph.sibling_number() == graph.tuft_number() == 1
    assert graph.reduction == graph.encoding
