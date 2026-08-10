from __future__ import annotations

import ast
from pathlib import Path
import sys
from types import ModuleType

import pytest

from qtbench.generation import load_trusted_oracle


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_ORACLES = {
    "problems/t_statistic_discovery/lpp_area_qt_theta_second_stat/generate_data.py":
        "theta_oracle.py",
    "problems/t_statistic_discovery/ddyck_area_qt_unified_delta_second_stat/generate_data.py":
        "theta_nabla_oracle.py",
    "problems/q_statistic_discovery/uig_ginv_shareshian_wachs_q_stat/generate_data.py":
        "csf_oracle.py",
    "problems/t_statistic_discovery/ttree_inv_qt_xi_second_stat/generate_data.py":
        "xi_oracle.py",
    "problems/t_statistic_discovery/mld_area_qt_super_nabla_second_stat/generate_data.py":
        "super_nabla_oracle.py",
    "problems/t_statistic_discovery/lrp_area_qt_rectangular_delta_second_stat/generate_data.py":
        "rectangular_theta_oracle.py",
    "problems/t_statistic_discovery/tamari_park_trivariate_third_stat/generate_data.py":
        "trivariate_harmonics_oracle.py",
    "problems/t_statistic_discovery/syt_qt_kostka_macdonald_pair_stat/generate_data.py":
        "macdonald_kostka_oracle.py",
    "problems/q_statistic_discovery/uig_syt_llt_schur_q_stat/generate_data.py":
        "llt_oracle.py",
    "problems/q_statistic_discovery/inv_orbit_harmonics_hilbert_q_stat/generate_data.py":
        "orbit_harmonics_oracle.py",
    "problems/q_statistic_discovery/match_jack_connection_q_stat/generate_data.py":
        "jack_connection_oracle.py",
    "problems/q_statistic_discovery/perm_q_eulerian_gamma_q_stat/generate_data.py":
        "q_eulerian_oracle.py",
    "problems/t_statistic_discovery/gpf_sel_ut_delta_xi_second_stat/generate_data.py":
        "delta_xi_oracle.py",
    "problems/t_statistic_discovery/rtt_inv_qt_theta_second_stat/generate_data.py":
        "theta_oracle.py",
    "problems/t_statistic_discovery/lgpf_sel_ut_delta_xi_schur_second_stat/generate_data.py":
        "delta_xi_schur_oracle.py",
    "problems/t_statistic_discovery/tgt_inv_qt_ehrhart_second_stat/generate_data.py":
        "ehrhart_oracle.py",
    "problems/q_statistic_discovery/syt_promotion_csp_q_stat/generate_data.py":
        "promotion_oracle.py",
    "problems/q_statistic_discovery/nc_q_kreweras_q_stat/generate_data.py":
        "kreweras_oracle.py",
}


def _loader_function(tree: ast.Module) -> ast.FunctionDef | None:
    return next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "_load_oracle"
        ),
        None,
    )


def test_trusted_oracle_loader_distinguishes_same_basename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first_path = first_dir / "theta_oracle.py"
    second_path = second_dir / "theta_oracle.py"
    source = (
        "import sys\n"
        "REGISTERED_DURING_LOAD = "
        "sys.modules[__name__].__dict__ is globals()\n"
        "MARKER = {!r}\n"
    )
    first_path.write_text(source.format("first"), encoding="utf-8")
    second_path.write_text(source.format("second"), encoding="utf-8")

    decoy = ModuleType("theta_oracle")
    monkeypatch.setitem(sys.modules, "theta_oracle", decoy)
    original_sys_path = list(sys.path)

    first = load_trusted_oracle(first_path)
    second = load_trusted_oracle(second_path)

    assert first.MARKER == "first"
    assert second.MARKER == "second"
    assert first.REGISTERED_DURING_LOAD
    assert second.REGISTERED_DURING_LOAD
    assert first.__name__ != second.__name__
    assert Path(first.__file__).resolve() == first_path.resolve()
    assert Path(second.__file__).resolve() == second_path.resolve()
    assert first.__name__ not in sys.modules
    assert second.__name__ not in sys.modules
    assert sys.modules["theta_oracle"] is decoy
    assert sys.path == original_sys_path

    previous = ModuleType(first.__name__)
    monkeypatch.setitem(sys.modules, first.__name__, previous)
    reloaded = load_trusted_oracle(first_path)
    assert reloaded.MARKER == "first"
    assert sys.modules[first.__name__] is previous

    failing_path = tmp_path / "failing_oracle.py"
    failing_path.write_text(
        "import sys\n"
        "assert sys.modules[__name__].__dict__ is globals()\n"
        "raise RuntimeError('oracle failed during import')\n",
        encoding="utf-8",
    )
    module_names_before = {
        name for name in sys.modules if name.startswith("_qtbench_trusted_oracle_")
    }
    with pytest.raises(RuntimeError, match="oracle failed during import"):
        load_trusted_oracle(failing_path)
    assert {
        name for name in sys.modules if name.startswith("_qtbench_trusted_oracle_")
    } == module_names_before
    assert sys.path == original_sys_path


def test_generator_oracle_calls_are_path_bound() -> None:
    discovered = set()
    for generator_path in (ROOT / "problems").glob("*/*/generate_data.py"):
        tree = ast.parse(generator_path.read_text(encoding="utf-8"))
        if _loader_function(tree) is not None:
            discovered.add(generator_path.relative_to(ROOT).as_posix())
    assert discovered == set(GENERATOR_ORACLES)

    for relative_path, oracle_filename in GENERATOR_ORACLES.items():
        generator_path = ROOT / relative_path
        tree = ast.parse(generator_path.read_text(encoding="utf-8"))
        imports = {
            alias.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "qtbench.generation"
            for alias in node.names
        }
        assert "load_trusted_oracle" in imports, generator_path

        loader = _loader_function(tree)
        assert loader is not None
        assert len(loader.body) == 1
        statement = loader.body[0]
        assert isinstance(statement, ast.Return)
        call = statement.value
        assert isinstance(call, ast.Call)
        assert isinstance(call.func, ast.Name)
        assert call.func.id == "load_trusted_oracle"
        assert len(call.args) == 1
        assert not call.keywords
        oracle_path = call.args[0]
        assert isinstance(oracle_path, ast.BinOp)
        assert isinstance(oracle_path.op, ast.Div)
        assert isinstance(oracle_path.left, ast.Name)
        assert oracle_path.left.id == "problem_dir"
        assert isinstance(oracle_path.right, ast.Constant)
        assert oracle_path.right.value == oracle_filename
        assert (generator_path.parent / oracle_filename).is_file()


def test_exact_certifier_loads_its_oracle_by_path() -> None:
    certifier = (
        ROOT
        / "problems/q_statistic_discovery/"
        "inv_orbit_harmonics_hilbert_q_stat/certify_exact.py"
    )
    tree = ast.parse(certifier.read_text(encoding="utf-8"))
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "qtbench.generation"
        and any(alias.name == "load_trusted_oracle" for alias in node.names)
        for node in tree.body
    )
    oracle_assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "oracle"
            for target in node.targets
        )
    )
    call = oracle_assignment.value
    assert isinstance(call, ast.Call)
    assert isinstance(call.func, ast.Name)
    assert call.func.id == "load_trusted_oracle"
    oracle_path = call.args[0]
    assert isinstance(oracle_path, ast.BinOp)
    assert isinstance(oracle_path.op, ast.Div)
    assert isinstance(oracle_path.left, ast.Name)
    assert oracle_path.left.id == "PROBLEM_DIR"
    assert isinstance(oracle_path.right, ast.Constant)
    assert oracle_path.right.value == "orbit_harmonics_oracle.py"
