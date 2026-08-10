from __future__ import annotations

from collections import Counter
from fractions import Fraction

from qtbench.combinatorics import (
    ZeroRootedTieredTree,
    canonical_zero_rooted_tiered_tree,
    is_zero_rooted_tiered_tree,
    iter_zero_rooted_tiered_trees,
    tiered_tree_inv,
    tiered_tree_size,
    zero_rooted_tiered_tree_count,
)


def _partitions(n: int, maxpart: int | None = None):
    if maxpart is None:
        maxpart = n
    if n == 0:
        yield ()
        return
    for part in range(min(n, maxpart), 0, -1):
        for rest in _partitions(n - part, part):
            yield (part, *rest)


def _level_functions(mu: tuple[int, ...]):
    """Every assignment of the tiers ``mu`` to the labels ``1, ..., |mu|``."""
    n = sum(mu)

    def rec(label: int, remaining: tuple[int, ...], prefix: tuple[int, ...]):
        if label > n:
            yield prefix
            return
        for index, left in enumerate(remaining):
            if left:
                yield from rec(
                    label + 1,
                    (*remaining[:index], left - 1, *remaining[index + 1 :]),
                    (*prefix, index + 1),
                )

    yield from rec(1, mu, ())


def _matrix_tree_count(mu: tuple[int, ...]) -> int:
    """``|RTT_0(mu)|`` computed independently, by the matrix-tree theorem.

    For each level function the compatibility graph has a universal vertex ``0``
    and an edge ``{i, j}``, ``i < j``, exactly when ``lv(i) < lv(j)``. The number
    of trees rooted at ``0`` is the determinant of the Laplacian with the row and
    column of ``0`` deleted.
    """
    n = sum(mu)
    total = 0
    for levels in _level_functions(mu):
        adjacency = [
            [1 if i != j and levels[min(i, j)] < levels[max(i, j)] else 0 for j in range(n)]
            for i in range(n)
        ]
        matrix = [
            [
                (1 + sum(adjacency[i])) if i == j else -Fraction(adjacency[i][j])
                for j in range(n)
            ]
            for i in range(n)
        ]
        total += _determinant(matrix)
    return total


def _determinant(matrix) -> int:
    rows = [[Fraction(value) for value in row] for row in matrix]
    n = len(rows)
    result = Fraction(1)
    for col in range(n):
        pivot = next((r for r in range(col, n) if rows[r][col] != 0), None)
        if pivot is None:
            return 0
        if pivot != col:
            rows[col], rows[pivot] = rows[pivot], rows[col]
            result = -result
        result *= rows[col][col]
        inverse = rows[col][col]
        rows[col] = [value / inverse for value in rows[col]]
        for r in range(col + 1, n):
            factor = rows[r][col]
            if factor:
                rows[r] = [a - factor * b for a, b in zip(rows[r], rows[col])]
    assert result.denominator == 1
    return int(result)


def test_single_tier_admits_exactly_one_tree() -> None:
    # With mu = (n) every non-root vertex sits on level 1, so no two of them are
    # compatible and the only spanning tree is the star at the root.
    for n in range(1, 7):
        assert zero_rooted_tiered_tree_count((n,)) == 1


def test_enumeration_matches_an_independent_matrix_tree_count() -> None:
    for n in range(1, 6):
        for mu in _partitions(n):
            assert zero_rooted_tiered_tree_count(mu) == _matrix_tree_count(mu)


def test_every_enumerated_tree_is_valid_and_well_formed() -> None:
    for n in range(1, 5):
        for mu in _partitions(n):
            seen = set()
            for tree in iter_zero_rooted_tiered_trees(mu):
                assert is_zero_rooted_tiered_tree(tree.encoding)
                assert tree.n == n and tree.vertex_count == n + 1
                assert tree.root == 0
                assert Counter(tree.levels) == Counter(
                    level for level, size in enumerate(mu, start=1) for _ in range(size)
                )
                assert tree.inv() >= 0
                # round-trips through the encoding
                assert ZeroRootedTieredTree(tree.encoding).encoding == tree.encoding
                assert tiered_tree_inv(tree.encoding) == tree.inv()
                assert tiered_tree_size(tree.encoding) == n
                seen.add(tree.encoding)
            assert len(seen) == zero_rooted_tiered_tree_count(mu)


def test_inv_on_hand_checked_small_trees() -> None:
    # mu = (1, 1). Only the level function lv(1) = 1, lv(2) = 2 makes 1 and 2
    # compatible, giving the three spanning trees of a triangle; the reversed
    # level function leaves only the star at the root. Exactly one of the four
    # trees has an inversion: the one where 1 hangs below 2, since 1 < 2 and 1 is
    # compatible with the root p(2) = 0.
    assert Counter(tree.inv() for tree in iter_zero_rooted_tiered_trees((1, 1))) == {0: 3, 1: 1}
    assert ZeroRootedTieredTree("1,2|0,1").inv() == 0
    assert ZeroRootedTieredTree("1,2|2,0").inv() == 1

    # mu = (2, 1) with lv = (1, 2, 1): only 1 and 2 are compatible, so hanging 1
    # below 2 is again the single inversion.
    assert ZeroRootedTieredTree("1,2,1|2,0,0").inv() == 1
    assert ZeroRootedTieredTree("1,2,1|0,1,0").inv() == 0


def test_deep_zero_rooted_tree_does_not_materialize_all_ancestor_sets() -> None:
    n = 2_048
    levels = tuple(range(1, n + 1))
    parents = (*range(2, n + 1), 0)
    encoding = ",".join(map(str, levels)) + "|" + ",".join(map(str, parents))

    tree = ZeroRootedTieredTree(encoding)
    assert tree.inv() == n * (n - 1) // 2
    assert "ancestors" not in tree.__dict__


def test_validation_rejects_malformed_encodings() -> None:
    assert not is_zero_rooted_tiered_tree("1,1|0")  # parent vector too short
    assert not is_zero_rooted_tiered_tree("0,1|0,1")  # level 0 is reserved for the root
    assert not is_zero_rooted_tiered_tree("1,3|0,1")  # level 2 is empty
    assert not is_zero_rooted_tiered_tree("1,1|0,1")  # edge inside one tier
    assert not is_zero_rooted_tiered_tree("2,1|0,1")  # 2 above 1 but labelled lower
    assert not is_zero_rooted_tiered_tree("1,2,3|3,3,2")  # a 2-3 cycle, root unreached
    assert is_zero_rooted_tiered_tree("1,2,3|0,1,2")


def test_canonical_tree_is_valid_and_cheap_for_large_sizes() -> None:
    for mu in ((1024,), (512, 512), tuple([1] * 512)):
        tree = canonical_zero_rooted_tiered_tree(mu)
        assert is_zero_rooted_tiered_tree(tree.encoding)
        assert tree.root == 0
        assert tree.parents == tuple([0] * sum(mu))
