from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]

SAMPLE_BOUNDS = {
    "exchanging_bijection/dyck_area_bounce_exchange": ("instances_max_n", 8),
    "exchanging_bijection/graph_sibling_tuft_exchange": ("instances_max_n", 7),
    "exchanging_bijection/macdonald_fillings_inv_maj_exchange": (
        "instances_max_n",
        5,
    ),
    "exchanging_bijection/parking_area_dinv_exchange": ("instances_max_n", 5),
    "exchanging_bijection/polyomino_area_bounce_exchange": (
        "instances_max_sum",
        8,
    ),
    "exchanging_bijection/polyomino_area_bounce_transpose": (
        "instances_max_sum",
        8,
    ),
    "t_statistic_discovery/lpp_area_qt_theta_second_stat": (
        "instances_max_sum",
        7,
    ),
    "t_statistic_discovery/ddyck_area_qt_unified_delta_second_stat": (
        "instances_max_n",
        5,
    ),
    "t_statistic_discovery/type_b_area_qt_catalan_second_stat": (
        "instances_max_n",
        6,
    ),
    "q_statistic_discovery/asm_dpp_weight_q_stat": ("instances_max_n", 4),
    "q_statistic_discovery/uig_ginv_shareshian_wachs_q_stat": (
        "instances_max_n",
        6,
    ),
    "t_statistic_discovery/ttree_inv_qt_xi_second_stat": ("instances_max_n", 4),
    "t_statistic_discovery/tamari_park_trivariate_third_stat": (
        "instances_max_n",
        4,
    ),
    "q_statistic_discovery/uig_syt_llt_schur_q_stat": ("instances_max_n", 6),
    "q_statistic_discovery/inv_orbit_harmonics_hilbert_q_stat": (
        "instances_max_n",
        9,
    ),
    "q_statistic_discovery/match_jack_connection_q_stat": ("instances_max_n", 5),
    "q_statistic_discovery/perm_q_eulerian_gamma_q_stat": (
        "instances_max_n",
        8,
    ),
    "q_statistic_discovery/syt_promotion_csp_q_stat": (
        "instances_max_cells",
        12,
    ),
    "t_statistic_discovery/gpf_sel_ut_delta_xi_second_stat": (
        "instances_max_size",
        4,
    ),
    "t_statistic_discovery/lrp_area_qt_rectangular_delta_second_stat": (
        "instances_max_count",
        3_000,
    ),
    "t_statistic_discovery/mld_area_qt_super_nabla_second_stat": (
        "instances_max_count",
        10_000,
    ),
    "t_statistic_discovery/rtt_inv_qt_theta_second_stat": ("instances_max_n", 4),
    "t_statistic_discovery/lgpf_sel_ut_delta_xi_schur_second_stat": (
        "instances_max_size",
        4,
    ),
    "t_statistic_discovery/syt_qt_kostka_macdonald_pair_stat": (
        "instances_max_n",
        6,
    ),
    "t_statistic_discovery/tgt_inv_qt_ehrhart_second_stat": ("instances_max_n", 5),
    "q_statistic_discovery/nc_q_kreweras_q_stat": ("instances_max_n", 9),
}


def test_sample_bounds_table_covers_every_declared_instances_bound() -> None:
    discovered: dict[str, tuple[str, int]] = {}
    for instances_path in sorted(ROOT.glob("problems/*/*/data/instances.json")):
        instances = json.loads(instances_path.read_text(encoding="utf-8"))
        bound_fields = sorted(
            key for key in instances if key.startswith("instances_max_")
        )
        if not bound_fields:
            continue
        assert len(bound_fields) == 1, (
            f"{instances_path} declares multiple sample bounds"
        )
        bound_field = bound_fields[0]
        relative_problem_dir = str(
            instances_path.parent.parent.relative_to(ROOT / "problems")
        )
        discovered[relative_problem_dir] = (bound_field, instances[bound_field])

    assert discovered == SAMPLE_BOUNDS


@pytest.mark.parametrize(
    ("relative_problem_dir", "bound_field", "expected"),
    [
        (relative_problem_dir, bound_field, expected)
        for relative_problem_dir, (bound_field, expected) in SAMPLE_BOUNDS.items()
    ],
    ids=[Path(relative_problem_dir).name for relative_problem_dir in SAMPLE_BOUNDS],
)
def test_reduced_samples_use_instances_bound(
    relative_problem_dir: str,
    bound_field: str,
    expected: int,
) -> None:
    problem_dir = ROOT / "problems" / relative_problem_dir
    instances = json.loads(
        (problem_dir / "data" / "instances.json").read_text(encoding="utf-8")
    )

    assert instances[bound_field] == expected
    assert not any(key.startswith("public_max_") for key in instances)
