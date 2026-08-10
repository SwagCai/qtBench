from __future__ import annotations

import ast
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# A task type is always the name of the directory the problem lives in. Arity is
# data, not a type: how many statistics are public lives in `known_statistic` or
# `known_statistics`, so a two-statistic or a no-statistic problem needs no
# category of its own.
TASK_TYPES = {
    "t_statistic_discovery",
    "q_statistic_discovery",
    "exchanging_bijection",
}
STATUSES = {"draft", "active", "calibration", "expert_review", "retired"}
REGISTRY_FIELDS = {
    "id",
    "name",
    "title",
    "task_type",
    "object_family",
    "status",
    "data",
    "problem_statement",
}
METADATA_FIELDS = {
    "schema_version",
    "id",
    "name",
    "title",
    "task_type",
    "object_family",
    "submission_signature",
    "evaluator_kind",
    "public_cases",
    "scoring",
}
# `public_cases` is intentionally problem-family-specific; the surrounding
# metadata contract is still fixed and versioned.
# Bijection problems are graded by an identity check in place of the polynomial
# comparison. The name records which identity, independently of the folder.
BIJECTION_NUMERICAL_GATE = {
    "dyck_area_bounce_exchange": "area_bounce_identities_and_distribution",
    "polyomino_area_bounce_exchange": "area_bounce_identities_and_distribution",
    "polyomino_area_bounce_transpose": "transpose_identities_and_distribution",
    "macdonald_fillings_inv_maj_exchange": "inv_maj_exchange_identities_and_distribution",
    "parking_area_dinv_exchange": "area_dinv_exchange_identities_and_distribution",
    "graph_sibling_tuft_exchange": "sibling_tuft_exchange_identities_and_distribution",
    "shifted_setvalued_pq_weight_bijection": "content_preserving_corollary_4_1_bijection",
    "andrews_bressoud_successive_rank_bijection": "weight_preserving_bijection_and_distribution",
    "improper_partition_matrix_inversion_sequence_bijection": "grading_preserving_bijection_and_distribution",
}
GATE_ORDER = [
    "capability_screen",
    "source_economy",
    "public_q_equals_1_and_exact_polynomials",
    "fresh_namespace_shuffled_replay",
    "value_audit",
    "resource_probes",
]


def test_registry_schema_matches_the_enforced_contract():
    schema = json.loads((ROOT / "problems" / "registry.schema.json").read_text())
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert set(schema["required"]) == {"schema_version", "problems"}
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == "0.1"
    item_schema = schema["properties"]["problems"]["items"]
    properties = item_schema["properties"]
    assert set(item_schema["required"]) == REGISTRY_FIELDS
    assert item_schema["additionalProperties"] is False
    assert set(properties["task_type"]["enum"]) == TASK_TYPES
    assert set(properties["status"]["enum"]) == STATUSES


def test_package_and_lock_versions_are_synchronized() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    project_version = project["project"]["version"]
    locked_project = [
        package for package in lock["package"] if package["name"] == "qtbench"
    ]
    assert len(locked_project) == 1
    assert locked_project[0]["version"] == project_version
    assert lock["requires-python"] == project["project"]["requires-python"]

    tree = ast.parse((ROOT / "src/qtbench/__init__.py").read_text(encoding="utf-8"))
    source_versions = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "__version__"
    ]
    assert source_versions == [project_version]


def test_build_backend_constraints_are_synchronized() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    uv_constraints = project["tool"]["uv"]["build-constraint-dependencies"]
    assert len(uv_constraints) == 1
    pinned_backend = uv_constraints[0]
    backend_name, backend_version = pinned_backend.split("==", 1)
    assert project["build-system"]["requires"] == [
        f"{backend_name}>={backend_version}"
    ]

    constraint_lines = [
        line.strip()
        for line in (ROOT / "build-constraints.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert len(constraint_lines) == 2
    assert constraint_lines[0].removesuffix("\\").rstrip() == pinned_backend
    assert re.fullmatch(r"--hash=sha256:[0-9a-f]{64}", constraint_lines[1])

def test_registry_entries_are_consistent():
    registry = json.loads((ROOT / "problems" / "registry.json").read_text())
    assert registry["schema_version"] == "0.1"
    assert set(registry) == {"schema_version", "problems"}
    assert registry["problems"]
    ids = [entry["id"] for entry in registry["problems"]]
    names = [entry["name"] for entry in registry["problems"]]
    assert len(ids) == len(set(ids)), "problem ids must be unique"
    assert len(names) == len(set(names)), "problem names must be unique"
    calibration_ids = {
        entry["id"] for entry in registry["problems"] if entry["status"] == "calibration"
    }
    assert calibration_ids == {1}

    for entry in registry["problems"]:
        assert set(entry) == REGISTRY_FIELDS
        assert type(entry["id"]) is int and entry["id"] >= 1
        assert re.fullmatch(r"[a-z][a-z0-9_]*", entry["name"])
        assert isinstance(entry["title"], str) and entry["title"]
        assert isinstance(entry["object_family"], str) and entry["object_family"]
        assert entry["status"] in STATUSES
        assert entry["task_type"] in TASK_TYPES
        expected_root = f"problems/{entry['task_type']}/{entry['name']}"
        assert entry["data"] == f"{expected_root}/data"
        assert entry["problem_statement"] == f"{expected_root}/problem.md"
        data_dir = ROOT / entry["data"]
        statement = ROOT / entry["problem_statement"]
        assert data_dir.is_dir(), f"missing data dir for {entry['name']}"
        assert statement.is_file(), f"missing problem.md for {entry['name']}"
        assert "## References\n" in statement.read_text(encoding="utf-8")
        assert (data_dir / "polynomials.json").is_file()
        assert (data_dir / "q_equals_1.json").is_file()

        metadata = json.loads((data_dir.parent / "metadata.json").read_text())
        assert metadata["schema_version"] == "0.1"
        expected_metadata_fields = METADATA_FIELDS.copy()
        if "known_statistics" in metadata:
            expected_metadata_fields.add("known_statistics")
            if metadata["known_statistics"]:
                expected_metadata_fields.add("known_statistics_file")
        else:
            expected_metadata_fields.update({"known_statistic", "known_statistic_file"})
        assert set(metadata) == expected_metadata_fields
        assert type(metadata["id"]) is int
        assert metadata["id"] == entry["id"]
        assert metadata["name"] == entry["name"]
        assert metadata["title"] == entry["title"]
        assert metadata["task_type"] == entry["task_type"]
        assert metadata["object_family"] == entry["object_family"]
        assert (
            isinstance(metadata["submission_signature"], str)
            and metadata["submission_signature"]
        )
        assert isinstance(metadata["evaluator_kind"], str) and re.fullmatch(
            r"[a-z][a-z0-9-]*", metadata["evaluator_kind"]
        )
        assert isinstance(metadata["public_cases"], dict) and metadata["public_cases"]
        assert set(metadata["scoring"]) >= {"gate_order", "case_score", "problem_score"}
        assert (
            isinstance(metadata["scoring"]["case_score"], str)
            and metadata["scoring"]["case_score"]
        )
        assert (
            isinstance(metadata["scoring"]["problem_score"], str)
            and metadata["scoring"]["problem_score"]
        )
        assert data_dir.parent.name == entry["name"]
        # the invariant: problems/<task_type>/<name>/, with no exceptions
        assert data_dir.parent.parent.name == entry["task_type"]
        instances = json.loads((data_dir / "instances.json").read_text())
        assert instances["schema_version"] == "0.1"
        assert instances["problem_id"] == entry["id"]
        assert instances["problem_name"] == entry["name"]
        assert instances["object_family"] == entry["object_family"]
        gate_order = metadata["scoring"]["gate_order"]
        # The numerical gate is named after the identity the problem asks for,
        # which is a property of the mathematics rather than of the folder:
        # `polyomino_area_bounce_transpose` lives under `exchanging_bijection`
        # for layout reasons but checks transpose identities.
        numerical_gate = BIJECTION_NUMERICAL_GATE.get(entry["name"])
        if numerical_gate is not None:
            expected_gate_order = [
                "capability_screen",
                "source_economy",
                numerical_gate,
                "fresh_namespace_shuffled_replay",
                "value_audit",
                "resource_and_identity_probes",
            ]
        else:
            expected_gate_order = GATE_ORDER
        assert gate_order == expected_gate_order
        assert "shuffled replay" in metadata["scoring"]["problem_score"]
        if "known_statistics" in metadata:
            assert isinstance(metadata["known_statistics"], list)
            assert all(
                isinstance(statistic, str) and statistic
                for statistic in metadata["known_statistics"]
            )
            assert len(metadata["known_statistics"]) == len(
                set(metadata["known_statistics"])
            )
            if not metadata["known_statistics"]:
                # An empty list means no statistic is public: the task is to
                # discover every graded statistic, so there is no known file.
                assert "known_statistics_file" not in metadata
                continue
            known_file = metadata["known_statistics_file"]
            assert known_file == "known_statistics.py"
        else:
            assert isinstance(metadata["known_statistic"], str)
            assert metadata["known_statistic"]
            known_file = metadata["known_statistic_file"]
            assert known_file == "known_statistic.py"
        assert (data_dir.parent / known_file).is_file()


def test_public_generation_layout_is_complete() -> None:
    registry = json.loads((ROOT / "problems" / "registry.json").read_text())
    shared_generator_ids = {4, 5}
    for entry in registry["problems"]:
        problem_dir = (ROOT / entry["data"]).parent
        if entry["id"] in shared_generator_ids:
            assert (ROOT / "scripts/generate/generate_polyomino_data.py").is_file()
        else:
            assert (problem_dir / "generate_data.py").is_file(), entry["name"]


def test_generation_artifacts_request_lf_newlines_explicitly() -> None:
    generation_scripts = sorted((ROOT / "problems").glob("*/*/generate_data.py"))
    generation_scripts.extend(sorted((ROOT / "scripts" / "generate").glob("*.py")))
    generation_scripts.extend(
        sorted((ROOT / "problems").glob("*/*/certify_exact.py"))
    )

    for script in generation_scripts:
        tree = ast.parse(script.read_text(encoding="utf-8"))
        writes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "write_text"
        ]
        for call in writes:
            newline = next(
                (keyword.value for keyword in call.keywords if keyword.arg == "newline"),
                None,
            )
            assert isinstance(newline, ast.Constant) and newline.value == "\n", script


def test_noncrossing_generator_resolves_default_oracle_from_problem_dir(tmp_path) -> None:
    source = (
        ROOT
        / "problems"
        / "t_statistic_discovery"
        / "nc_area_qt_narayana_second_stat"
    )
    clean_problem = tmp_path / source.name
    clean_problem.mkdir()
    shutil.copy2(source / "metadata.json", clean_problem / "metadata.json")

    result = subprocess.run(
        [
            sys.executable,
            str(source / "generate_data.py"),
            "--problem-dir",
            str(clean_problem),
            "--public-max-n",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert str(clean_problem / "oracle.py") in result.stderr


def test_noncrossing_generator_runs_from_a_clean_problem_copy(tmp_path) -> None:
    source = (
        ROOT
        / "problems"
        / "t_statistic_discovery"
        / "nc_area_qt_narayana_second_stat"
    )
    clean_problem = tmp_path / source.name
    clean_problem.mkdir()
    for name in ("metadata.json", "oracle.py"):
        shutil.copy2(source / name, clean_problem / name)

    result = subprocess.run(
        [
            sys.executable,
            str(source / "generate_data.py"),
            "--problem-dir",
            str(clean_problem),
            "--public-max-n",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    generated = json.loads(
        (clean_problem / "data" / "polynomials.json").read_text(encoding="utf-8")
    )
    assert (generated["problem_id"], generated["problem_name"]) == (1, source.name)
    committed = json.loads(
        (source / "data" / "polynomials.json").read_text(encoding="utf-8")
    )
    assert generated["cases"] == [
        case for case in committed["cases"] if case["n"] == 1
    ]


def test_type_b_generator_resolves_default_source_data_from_problem_dir(tmp_path) -> None:
    source = (
        ROOT
        / "problems"
        / "t_statistic_discovery"
        / "type_b_area_qt_catalan_second_stat"
    )
    clean_problem = tmp_path / source.name
    clean_problem.mkdir()
    shutil.copy2(source / "metadata.json", clean_problem / "metadata.json")
    (clean_problem / "source_data").mkdir()

    result = subprocess.run(
        [
            sys.executable,
            str(source / "generate_data.py"),
            "--problem-dir",
            str(clean_problem),
            "--public-max-n",
            "1",
            "--instances-max-n",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert str(
        clean_problem
        / "source_data"
        / "type_b_qt_catalan_known_n1_to_n6.json"
    ) in result.stderr


def test_type_b_generator_runs_from_a_clean_problem_copy(tmp_path) -> None:
    source = (
        ROOT
        / "problems"
        / "t_statistic_discovery"
        / "type_b_area_qt_catalan_second_stat"
    )
    clean_problem = tmp_path / source.name
    clean_problem.mkdir()
    shutil.copy2(source / "metadata.json", clean_problem / "metadata.json")
    shutil.copytree(source / "source_data", clean_problem / "source_data")

    result = subprocess.run(
        [
            sys.executable,
            str(source / "generate_data.py"),
            "--problem-dir",
            str(clean_problem),
            "--public-max-n",
            "1",
            "--instances-max-n",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    generated = json.loads(
        (clean_problem / "data" / "polynomials.json").read_text(encoding="utf-8")
    )
    assert (generated["problem_id"], generated["problem_name"]) == (3, source.name)
    committed = json.loads(
        (source / "data" / "polynomials.json").read_text(encoding="utf-8")
    )
    assert generated["cases"] == [
        case for case in committed["cases"] if case["n"] == 1
    ]


def test_public_oracles_declare_their_problem_identity() -> None:
    for oracle_path in sorted((ROOT / "problems").glob("*/*/*oracle.py")):
        tree = ast.parse(oracle_path.read_text())
        declarations = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in {"PROBLEM_ID", "PROBLEM_NAME"}
        }
        metadata = json.loads((oracle_path.parent / "metadata.json").read_text())
        assert declarations == {
            "PROBLEM_ID": metadata["id"],
            "PROBLEM_NAME": metadata["name"],
        }, oracle_path


def test_every_problem_declares_the_evaluator_kind_that_scores_it() -> None:
    """A reader must be able to get from a problem to its scoring command.

    The kind lives in `metadata.json`, in the problem statement, and in the CLI
    dispatch table; this pins all three together.
    """

    spec = importlib.util.spec_from_file_location(
        "qtbench_scored_cli", ROOT / "scripts" / "evaluate" / "evaluate_scored_submission.py"
    )
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    kind_of_dir = {
        path.resolve(): kind for kind, path in cli.DEFAULT_PROBLEM.items()
    }
    assert len(kind_of_dir) == 30

    registry = json.loads((ROOT / "problems" / "registry.json").read_text())
    registry_status = {
        entry["name"]: entry["status"] for entry in registry["problems"]
    }
    nonautomatic_kinds: set[str] = set()

    for metadata_path in sorted((ROOT / "problems").glob("*/*/metadata.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        kind = metadata["evaluator_kind"]
        assert kind_of_dir[metadata_path.parent.resolve()] == kind, metadata_path
        if registry_status[metadata["name"]] in {"draft", "expert_review", "retired"}:
            nonautomatic_kinds.add(kind)
        statement = (metadata_path.parent / "problem.md").read_text(encoding="utf-8")
        assert (
            f"evaluate_scored_submission.py {kind} " in statement
        ), f"{metadata_path.parent.name} does not show its scoring command"

    assert nonautomatic_kinds == set(cli.NON_AUTOMATIC_REASONS)


def test_taxonomy_backing_tests_all_exist() -> None:
    """The cheating taxonomy's honesty rests on its claims being checkable.

    Every test it names must resolve, or a status label can drift away from the
    behaviour that is supposed to justify it.
    """

    taxonomy = (ROOT / "docs/cheating/taxonomy.md").read_text(encoding="utf-8")
    named = set(re.findall(r"`(test_\w+)`", taxonomy))
    assert named, "taxonomy names no backing tests"

    defined: set[str] = set()
    for path in (ROOT / "tests").rglob("*.py"):
        defined |= set(re.findall(r"^def (test_\w+)", path.read_text(encoding="utf-8"), re.M))

    missing = sorted(named - defined)
    assert not missing, f"taxonomy names tests that do not exist: {missing}"
