from __future__ import annotations

from qtbench.combinatorics import (
    area_bounce_distribution,
    dyck_area,
    dyck_bounce,
    enumerate_dyck_paths,
    first_return,
    is_dyck_path,
)


def test_dyck_enumeration_and_statistics() -> None:
    catalan = [1, 1, 2, 5, 14, 42, 132, 429]
    for n, expected_count in enumerate(catalan):
        paths = enumerate_dyck_paths(n)
        assert len(paths) == expected_count
        assert len(set(paths)) == expected_count
        assert all(is_dyck_path(path) for path in paths)
        assert sum(area_bounce_distribution(n).values()) == expected_count

    assert dyck_area("NENE") == 0
    assert dyck_bounce("NENE") == 1
    assert dyck_area("NNEE") == 1
    assert dyck_bounce("NNEE") == 0


def test_first_return_is_a_strict_structural_decomposition() -> None:
    for n in range(1, 8):
        for path in enumerate_dyck_paths(n):
            left, right = first_return(path)
            assert path == f"N{left}E{right}"
            assert is_dyck_path(left)
            assert is_dyck_path(right)
            assert len(left) < len(path)
            assert len(right) < len(path)
            assert len(left) + len(right) == len(path) - 2


def test_dyck_predicate_rejects_nonstring_inputs() -> None:
    assert not is_dyck_path(None)
    assert not is_dyck_path(b"NE")
