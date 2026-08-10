from __future__ import annotations

from pathlib import Path
import runpy
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]


INVALID_GENERATOR_ARGUMENTS = [
    ("scripts/generate/generate_polyomino_data.py", ["--public-max-sum", "1"]),
    (
        "problems/exchanging_bijection/dyck_area_bounce_exchange/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/exchanging_bijection/graph_sibling_tuft_exchange/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/exchanging_bijection/"
        "improper_partition_matrix_inversion_sequence_bijection/generate_data.py",
        ["--public-max-n", "2"],
    ),
    (
        "problems/exchanging_bijection/macdonald_fillings_inv_maj_exchange/generate_data.py",
        ["--public-max-n", "3"],
    ),
    (
        "problems/exchanging_bijection/parking_area_dinv_exchange/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/q_statistic_discovery/asm_dpp_weight_q_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/q_statistic_discovery/inv_orbit_harmonics_hilbert_q_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/q_statistic_discovery/inv_orbit_harmonics_hilbert_q_stat/generate_data.py",
        ["--exact-max-n", "-1"],
    ),
    (
        "problems/q_statistic_discovery/inv_orbit_harmonics_hilbert_q_stat/generate_data.py",
        ["--permutation-max-n", "-1"],
    ),
    (
        "problems/q_statistic_discovery/match_jack_connection_q_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/q_statistic_discovery/nc_q_kreweras_q_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/q_statistic_discovery/perm_q_eulerian_gamma_q_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/q_statistic_discovery/perm_q_eulerian_gamma_q_stat/generate_data.py",
        ["--brute-max-n", "-1"],
    ),
    (
        "problems/q_statistic_discovery/syt_promotion_csp_q_stat/generate_data.py",
        ["--staircase-max-k", "1"],
    ),
    (
        "problems/q_statistic_discovery/syt_promotion_csp_q_stat/generate_data.py",
        ["--staircase-max-k", "5"],
    ),
    (
        "problems/q_statistic_discovery/syt_promotion_csp_q_stat/generate_data.py",
        ["--rectangle-max-cells", "3"],
    ),
    (
        "problems/q_statistic_discovery/syt_promotion_csp_q_stat/generate_data.py",
        ["--rectangle-max-cells", "17"],
    ),
    (
        "problems/q_statistic_discovery/uig_ginv_shareshian_wachs_q_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/q_statistic_discovery/uig_syt_llt_schur_q_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/t_statistic_discovery/ddyck_area_qt_unified_delta_second_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/t_statistic_discovery/gpf_sel_ut_delta_xi_second_stat/generate_data.py",
        ["--public-max-size", "0"],
    ),
    (
        "problems/t_statistic_discovery/lgpf_sel_ut_delta_xi_schur_second_stat/generate_data.py",
        ["--public-max-size", "0"],
    ),
    (
        "problems/t_statistic_discovery/lpp_area_qt_theta_second_stat/generate_data.py",
        ["--public-max-sum", "1"],
    ),
    (
        "problems/t_statistic_discovery/lrp_area_qt_rectangular_delta_second_stat/generate_data.py",
        ["--public-max-semiperimeter", "3"],
    ),
    (
        "problems/t_statistic_discovery/lrp_area_qt_rectangular_delta_second_stat/generate_data.py",
        ["--instances-max-count", "0"],
    ),
    (
        "problems/t_statistic_discovery/mld_area_qt_super_nabla_second_stat/generate_data.py",
        ["--public-max-k", "0"],
    ),
    (
        "problems/t_statistic_discovery/mld_area_qt_super_nabla_second_stat/generate_data.py",
        ["--instances-max-count", "0"],
    ),
    (
        "problems/t_statistic_discovery/nc_area_qt_narayana_second_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/t_statistic_discovery/rtt_inv_qt_theta_second_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/t_statistic_discovery/syt_qt_kostka_macdonald_pair_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/t_statistic_discovery/tamari_park_trivariate_third_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/t_statistic_discovery/tgt_inv_qt_ehrhart_second_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/t_statistic_discovery/ttree_inv_qt_xi_second_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
    (
        "problems/t_statistic_discovery/type_b_area_qt_catalan_second_stat/generate_data.py",
        ["--public-max-n", "0"],
    ),
]


INSTANCE_RANGE_ARGUMENTS = [
    (
        "scripts/generate/generate_polyomino_data.py",
        ["--public-max-sum", "2", "--instances-max-sum", "3"],
    ),
    (
        "problems/exchanging_bijection/dyck_area_bounce_exchange/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/exchanging_bijection/macdonald_fillings_inv_maj_exchange/generate_data.py",
        ["--public-max-n", "4", "--instances-max-n", "5"],
    ),
    (
        "problems/exchanging_bijection/parking_area_dinv_exchange/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/q_statistic_discovery/asm_dpp_weight_q_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/q_statistic_discovery/inv_orbit_harmonics_hilbert_q_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/q_statistic_discovery/match_jack_connection_q_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/q_statistic_discovery/nc_q_kreweras_q_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/q_statistic_discovery/perm_q_eulerian_gamma_q_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/q_statistic_discovery/syt_promotion_csp_q_stat/generate_data.py",
        ["--staircase-max-k", "2", "--rectangle-max-cells", "4", "--instances-max-cells", "5"],
    ),
    (
        "problems/q_statistic_discovery/uig_ginv_shareshian_wachs_q_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/q_statistic_discovery/uig_syt_llt_schur_q_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/t_statistic_discovery/ddyck_area_qt_unified_delta_second_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/t_statistic_discovery/gpf_sel_ut_delta_xi_second_stat/generate_data.py",
        ["--public-max-size", "1", "--instances-max-size", "2"],
    ),
    (
        "problems/t_statistic_discovery/lgpf_sel_ut_delta_xi_schur_second_stat/generate_data.py",
        ["--public-max-size", "1", "--instances-max-size", "2"],
    ),
    (
        "problems/t_statistic_discovery/lpp_area_qt_theta_second_stat/generate_data.py",
        ["--public-max-sum", "2", "--instances-max-sum", "3"],
    ),
    (
        "problems/t_statistic_discovery/rtt_inv_qt_theta_second_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/t_statistic_discovery/syt_qt_kostka_macdonald_pair_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/t_statistic_discovery/tamari_park_trivariate_third_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/t_statistic_discovery/tgt_inv_qt_ehrhart_second_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/t_statistic_discovery/ttree_inv_qt_xi_second_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
    (
        "problems/t_statistic_discovery/type_b_area_qt_catalan_second_stat/generate_data.py",
        ["--public-max-n", "1", "--instances-max-n", "2"],
    ),
]


def test_problem_one_generator_help_warns_about_unrestricted_oracle(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    script = (
        ROOT
        / "problems/t_statistic_discovery/"
        "nc_area_qt_narayana_second_stat/generate_data.py"
    )
    monkeypatch.setattr(sys, "argv", [str(script), "--help"])

    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(script), run_name="__main__")

    assert exit_info.value.code == 0
    output = " ".join(capsys.readouterr().out.split())
    assert "trusted local oracle" in output
    assert "caller privileges" in output


@pytest.mark.parametrize(
    ("relative_script", "arguments"),
    INVALID_GENERATOR_ARGUMENTS + INSTANCE_RANGE_ARGUMENTS,
    ids=lambda value: str(value) if isinstance(value, str) else None,
)
def test_generators_reject_ranges_that_cannot_form_valid_public_data(
    relative_script: str,
    arguments: list[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    script = ROOT / relative_script
    arguments = ["--problem-dir", str(tmp_path), *arguments]
    monkeypatch.setattr(sys, "argv", [str(script), *arguments])

    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(script), run_name="__main__")

    assert exit_info.value.code == 2
    assert not (tmp_path / "data").exists()
