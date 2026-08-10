from __future__ import annotations

import json
import random
from collections import Counter
from contextlib import closing
from dataclasses import asdict, dataclass
from math import gcd
from pathlib import Path

from qtbench.combinatorics import (
    canonical_terms,
    enumerate_alternating_sign_matrices,
    enumerate_narayana_partitions,
    enumerate_type_b_catalan_paths,
    iter_decorated_labelled_dyck_paths,
    iter_gamma_parking_selections,
    iter_gamma_permutations_for_descents,
    iter_involutions_with_fixed_points,
    iter_jack_matchings_for_partition,
    iter_kostka_standard_tableaux,
    iter_labelled_rectangular_paths,
    iter_multi_labelled_dyck_paths,
    iter_noncrossing_partitions,
    iter_promotion_tableaux_for_shape,
    iter_rooted_tiered_trees,
    iter_st_labelled_polyominoes,
    iter_threshold_spanning_trees,
    iter_tamari_parking_pairs,
    iter_uig_permutations_for_vector,
    iter_uig_tableaux_for_vector,
    iter_zero_rooted_tiered_trees,
    joint_distribution,
    narayana_number,
)
from qtbench.evaluation.submission import StatisticFunction, load_statistic_function


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    n: int
    k: int
    count: int
    term_count: int
    correct: bool
    expected_term_count: int | None = None
    first_mismatch: dict | None = None
    l1_distance: int | None = None
    mismatch_count: int | None = None
    mismatches: list[dict] | None = None


@dataclass(frozen=True)
class GeneratedCase:
    n: int
    k: int
    count: int
    term_count: int
    terms: list[list[int]]


class UnsupportedDiagnosticProblemError(ValueError):
    """Raised when the legacy local diagnostic receives another problem."""


_DIAGNOSTIC_PROBLEM_ID = 1
_DIAGNOSTIC_PROBLEM_NAME = "nc_area_qt_narayana_second_stat"


_QT_PUBLIC_CONTRACT = (("q", "t"), ("t",), {"q": 1})
_PUBLIC_PROBLEM_CONTRACTS = {
    **{
        name: _QT_PUBLIC_CONTRACT
        for name in (
            "nc_area_qt_narayana_second_stat",
            "type_b_area_qt_catalan_second_stat",
            "dyck_area_bounce_exchange",
            "polyomino_area_bounce_exchange",
            "polyomino_area_bounce_transpose",
            "ddyck_area_qt_unified_delta_second_stat",
            "lpp_area_qt_theta_second_stat",
            "lrp_area_qt_rectangular_delta_second_stat",
            "mld_area_qt_super_nabla_second_stat",
            "ttree_inv_qt_xi_second_stat",
            "rtt_inv_qt_theta_second_stat",
            "tgt_inv_qt_ehrhart_second_stat",
            "syt_qt_kostka_macdonald_pair_stat",
            "macdonald_fillings_inv_maj_exchange",
            "parking_area_dinv_exchange",
            "graph_sibling_tuft_exchange",
        )
    },
    "gpf_sel_ut_delta_xi_second_stat": (
        ("partition", "u", "t"),
        ("partition", "t"),
        {"u": 1},
    ),
    "lgpf_sel_ut_delta_xi_schur_second_stat": (
        ("partition", "u", "t"),
        ("partition", "t"),
        {"u": 1},
    ),
    "tamari_park_trivariate_third_stat": (
        ("q1", "q2", "q3"),
        ("q3",),
        {"q1": 1, "q2": 1},
    ),
    "uig_ginv_shareshian_wachs_q_stat": (
        ("partition", "q"),
        ("partition",),
        {"q": 1},
    ),
    "uig_syt_llt_schur_q_stat": (
        ("partition", "q"),
        ("partition",),
        {"q": 1},
    ),
    "match_jack_connection_q_stat": (
        ("pi", "sigma", "q"),
        ("pi", "sigma"),
        {"q": 1},
    ),
    "nc_q_kreweras_q_stat": (
        ("partition", "q"),
        ("partition",),
        {"q": 1},
    ),
    "inv_orbit_harmonics_hilbert_q_stat": (
        ("q",),
        ("fixed_points",),
        {"q": 1},
    ),
    "perm_q_eulerian_gamma_q_stat": (("q",), ("descents",), {"q": 1}),
    "syt_promotion_csp_q_stat": (("q",), ("shape",), {"q": 1}),
    "asm_dpp_weight_q_stat": (("q",), ("n",), {"q": 1}),
    "shifted_setvalued_pq_weight_bijection": (
        ("entry_count",),
        (),
        {"entry_count": 1},
    ),
    "andrews_bressoud_successive_rank_bijection": (
        ("weight",),
        (),
        {"weight": 1},
    ),
    "improper_partition_matrix_inversion_sequence_bijection": (
        ("grading",),
        (),
        {"grading": 1},
    ),
}

# Every evaluator below treats these fields as structural case coordinates.
# Keep their JSON types exact here rather than allowing later ``int(...)``
# calls to silently reinterpret booleans, floats, or numeric strings.
_PUBLIC_CASE_COORDINATES = {
    "nc_area_qt_narayana_second_stat": (("n", "k"), ()),
    "type_b_area_qt_catalan_second_stat": (("n",), ()),
    "dyck_area_bounce_exchange": (("n",), ()),
    "polyomino_area_bounce_exchange": (("m", "n"), ()),
    "polyomino_area_bounce_transpose": (("m", "n"), ()),
    "ddyck_area_qt_unified_delta_second_stat": (("n", "k", "l"), ()),
    "lpp_area_qt_theta_second_stat": (("m", "n"), ()),
    "lrp_area_qt_rectangular_delta_second_stat": (("m", "n", "k"), ()),
    "mld_area_qt_super_nabla_second_stat": (("n", "k"), ()),
    "ttree_inv_qt_xi_second_stat": (("n",), ("mu",)),
    "rtt_inv_qt_theta_second_stat": (("n",), ("mu",)),
    "tgt_inv_qt_ehrhart_second_stat": (("n",), ("up_degrees",)),
    "syt_qt_kostka_macdonald_pair_stat": (("n",), ("lam", "mu")),
    "tamari_park_trivariate_third_stat": (("n",), ()),
    "gpf_sel_ut_delta_xi_second_stat": (("n",), ("gamma", "lam", "content")),
    "lgpf_sel_ut_delta_xi_schur_second_stat": (
        ("n",),
        ("gamma", "lam", "content"),
    ),
    "uig_ginv_shareshian_wachs_q_stat": (("n",), ("b",)),
    "uig_syt_llt_schur_q_stat": (("n",), ("b",)),
    "inv_orbit_harmonics_hilbert_q_stat": (("n", "a"), ()),
    "match_jack_connection_q_stat": (("n",), ("lambda",)),
    "perm_q_eulerian_gamma_q_stat": (("n", "k"), ()),
    "syt_promotion_csp_q_stat": (("cells", "modulus"), ("shape",)),
    "nc_q_kreweras_q_stat": (("n",), ()),
    "asm_dpp_weight_q_stat": (("n",), ()),
    "macdonald_fillings_inv_maj_exchange": (("n",), ("shape",)),
    "parking_area_dinv_exchange": (("n",), ()),
    "graph_sibling_tuft_exchange": (("n",), ()),
    "shifted_setvalued_pq_weight_bijection": ((), ("mu", "content")),
    "andrews_bressoud_successive_rank_bijection": (
        ("modulus", "residue", "weight"),
        (),
    ),
    "improper_partition_matrix_inversion_sequence_bijection": (("n",), ()),
}


def _case_id(n: int, k: int, *, prefix: str = "") -> str:
    stem = f"n{n:02d}_k{k:02d}"
    return f"{prefix}_{stem}" if prefix else stem


def _statistic_value(value, object_description) -> int:
    """Require the exact nonnegative-integer return type promised by the task."""
    if type(value) is not int:
        raise TypeError(
            f"statistic must return a nonnegative integer, got "
            f"{type(value).__name__} {value!r} for {object_description}"
        )
    if value < 0:
        raise ValueError(
            f"statistic must return a nonnegative integer, got {value} "
            f"for {object_description}"
        )
    try:
        str(value)
    except ValueError as error:
        raise ValueError(
            "statistic returned an integer that exceeds the runtime's "
            "integer-to-decimal digit limit for evaluator reporting"
        ) from error
    return value


def _ordered_objects(objects, generator: random.Random | None):
    if generator is None:
        return objects
    ordered = list(objects)
    if len(ordered) < 2:
        return ordered

    # Use a secret single-cycle permutation. Unlike an arbitrary shuffle, this
    # guarantees that no nonconstant "value by call position" schedule can
    # preserve the same object-to-value assignment by chance.
    cycle = list(range(len(ordered)))
    generator.shuffle(cycle)
    permutation = list(range(len(ordered)))
    for source, target in zip(cycle, cycle[1:] + cycle[:1], strict=True):
        permutation[source] = target
    return [ordered[index] for index in permutation]


def _iter_kreweras_objects(factory, count: int, generator: random.Random | None):
    """Stream one q-Kreweras fiber, with a secret cyclic replay when seeded.

    The public target has already validated ``count``, so a replay does not count
    the restartable stream first.  Instead, two iterators emit the tail and then
    the prefix of a rotation.  A rotation offset coprime to ``count`` is one cycle,
    so no nonconstant value-by-call-position schedule preserves its assignment.
    """

    if type(count) is not int or count < 0:
        raise ValueError("q-Kreweras object count must be a nonnegative integer")
    if generator is None:
        with closing(factory()) as objects:
            yield from objects
        return

    def take(objects):
        try:
            return next(objects)
        except StopIteration as error:
            raise ValueError(
                "q-Kreweras iterator ended before its validated public count"
            ) from error

    def require_exhausted(objects) -> None:
        try:
            next(objects)
        except StopIteration:
            return
        raise ValueError(
            "q-Kreweras iterator exceeded its validated public count"
        )

    if count < 2:
        with closing(factory()) as objects:
            if count == 1:
                yield take(objects)
            require_exhausted(objects)
        return

    offset = generator.randrange(1, count)
    while gcd(offset, count) != 1:
        offset = 1 if offset + 1 == count else offset + 1

    # Close the tail before restarting the enumerator for the prefix.  In
    # particular, an abort or short tail never opens a second iterator/cache.
    with closing(factory()) as tail:
        for _ in range(offset):
            take(tail)
        for _ in range(count - offset):
            yield take(tail)
        require_exhausted(tail)

    with closing(factory()) as prefix:
        for _ in range(offset):
            yield take(prefix)


def _terms_to_counter(terms: list[list[int]], exponent_count: int) -> Counter[tuple[int, ...]]:
    counter: Counter[tuple[int, ...]] = Counter()
    for term in terms:
        values = [int(value) for value in term]
        if len(values) != exponent_count + 1:
            raise ValueError(f"expected {exponent_count + 1} values per term, got {term}")
        *exponents, coefficient = values
        if coefficient:
            counter[tuple(exponents)] += coefficient
    return counter


def _term_mismatches(
    generated_terms: list[list[int]],
    expected_terms: list[list[int]],
    *,
    variables: tuple[str, ...],
) -> tuple[int, list[dict]]:
    generated = _terms_to_counter(generated_terms, len(variables))
    expected = _terms_to_counter(expected_terms, len(variables))
    l1_distance = 0
    mismatches: list[dict] = []
    for key in sorted(set(generated) | set(expected)):
        generated_coeff = generated.get(key, 0)
        expected_coeff = expected.get(key, 0)
        difference = generated_coeff - expected_coeff
        if difference:
            l1_distance += abs(difference)
            mismatches.append(
                {
                    "exponents": dict(zip(variables, key, strict=True)),
                    "generated_coeff": generated_coeff,
                    "expected_coeff": expected_coeff,
                    "difference": difference,
                }
            )
    return l1_distance, mismatches


def generate_case(
    *,
    n: int,
    k: int,
    statistic: StatisticFunction,
    order_generator: random.Random | None = None,
) -> GeneratedCase:
    partitions = enumerate_narayana_partitions(n, k)
    expected_count = narayana_number(n, k)
    if len(partitions) != expected_count:
        raise RuntimeError(f"enumeration mismatch for n={n}, k={k}: {len(partitions)} vs {expected_count}")

    counter = joint_distribution(
        _ordered_objects(partitions, order_generator),
        lambda partition: partition.area(),
        lambda partition: _statistic_value(statistic(partition), partition.blocks),
    )
    generated_terms = canonical_terms(counter)
    return GeneratedCase(
        n=n,
        k=k,
        count=len(partitions),
        term_count=len(generated_terms),
        terms=generated_terms,
    )


def evaluate_case(
    *,
    n: int,
    k: int,
    statistic: StatisticFunction,
    case_id: str | None = None,
    expected_terms: list[list[int]],
) -> CaseResult:
    generated = generate_case(n=n, k=k, statistic=statistic)
    return _evaluate_generated_case(
        generated=generated,
        case_id=case_id or _case_id(n, k),
        expected_terms=expected_terms,
    )


def _evaluate_generated_case(
    *,
    generated: GeneratedCase,
    case_id: str,
    expected_terms: list[list[int]],
) -> CaseResult:
    l1_distance, mismatches = _term_mismatches(generated.terms, expected_terms, variables=("q", "t"))

    return CaseResult(
        case_id=case_id,
        n=generated.n,
        k=generated.k,
        count=generated.count,
        term_count=generated.term_count,
        expected_term_count=len(expected_terms),
        correct=not mismatches,
        first_mismatch=mismatches[0] if mismatches else None,
        l1_distance=l1_distance,
        mismatch_count=len(mismatches),
        mismatches=mismatches,
    )


def _marginal_terms(terms: list[list[int]]) -> list[list[int]]:
    counter: Counter[int] = Counter()
    for _, t_exponent, coefficient in terms:
        counter[int(t_exponent)] += int(coefficient)
    return [[degree, counter[degree]] for degree in sorted(counter) if counter[degree]]


def _marginal_case_result(
    *,
    generated: GeneratedCase,
    case: dict,
) -> dict:
    generated_terms = _marginal_terms(generated.terms)
    l1_distance, mismatches = _term_mismatches(
        generated_terms,
        case["terms"],
        variables=("t",),
    )
    return {
        "case_id": case["case_id"],
        "n": generated.n,
        "k": generated.k,
        "count": generated.count,
        "term_count": len(generated_terms),
        "expected_term_count": len(case["terms"]),
        "correct": not mismatches,
        "l1_distance": l1_distance,
        "mismatch_count": len(mismatches),
        "first_mismatch": mismatches[0] if mismatches else None,
        "mismatches": mismatches,
    }


def _reject_duplicate_json_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _reject_nonstandard_json_constant(value: str):
    raise ValueError(f"non-standard JSON constant {value}")


def _load_json_document(path: Path):
    """Read one UTF-8 JSON document without permissive parser extensions."""

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonstandard_json_constant,
        )
    except ValueError as error:
        raise ValueError(f"{path} is not valid strict JSON: {error}") from error


def _problem_identity(problem_dir: Path) -> dict:
    metadata_path = problem_dir / "metadata.json"
    if metadata_path.exists():
        metadata = _load_json_document(metadata_path)
        if not isinstance(metadata, dict):
            raise ValueError(f"{metadata_path} must contain a JSON object")
        if metadata.get("schema_version") != "0.1":
            raise ValueError(f"{metadata_path} has unsupported schema_version")
        problem_id = metadata.get("id")
        problem_name = metadata.get("name")
        if type(problem_id) is not int or problem_id <= 0:
            raise ValueError(f"{metadata_path} has an invalid problem id")
        if not isinstance(problem_name, str) or not problem_name:
            raise ValueError(f"{metadata_path} has an invalid problem name")
        return {
            "problem_id": problem_id,
            "problem_name": problem_name,
        }
    return {
        "problem_id": None,
        "problem_name": problem_dir.name,
    }


def _require_supported_diagnostic_problem(problem_dir: Path) -> dict:
    identity = _problem_identity(problem_dir)
    if (
        identity["problem_id"],
        identity["problem_name"],
    ) != (_DIAGNOSTIC_PROBLEM_ID, _DIAGNOSTIC_PROBLEM_NAME):
        raise UnsupportedDiagnosticProblemError(
            "the legacy evaluate_submission diagnostic only supports problem 1 "
            f"({_DIAGNOSTIC_PROBLEM_NAME}); got "
            f"{identity['problem_name']} (id {identity['problem_id']}); use "
            "evaluate_scored_submission.py with that problem's evaluator kind"
        )
    return identity


def _load_public_data(problem_dir: Path, filename: str) -> dict:
    """Load and validate a scored public target file.

    These files are part of the checker input, not merely descriptive data.  A
    missing identity field or an empty case list must therefore fail closed
    instead of turning a numerical comparison into a vacuous success.
    """

    identity = _problem_identity(problem_dir)
    if identity["problem_id"] is None:
        raise ValueError(f"{problem_dir} has no metadata.json")
    path = problem_dir / "data" / filename
    data = _load_json_document(path)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    if data.get("schema_version") != "0.1":
        raise ValueError(f"{path} has unsupported schema_version")
    public_problem_id = data.get("problem_id")
    if (
        type(public_problem_id) is not int
        or public_problem_id != identity["problem_id"]
    ):
        raise ValueError(f"{path} problem_id does not match metadata.json")
    if data.get("problem_name") != identity["problem_name"]:
        raise ValueError(f"{path} problem_name does not match metadata.json")

    variables = data.get("variables")
    if (
        not isinstance(variables, list)
        or any(not isinstance(variable, str) or not variable for variable in variables)
        or len(set(variables)) != len(variables)
    ):
        raise ValueError(f"{path} must declare a list of distinct nonempty variable names")
    contract = _PUBLIC_PROBLEM_CONTRACTS.get(identity["problem_name"])
    if contract is not None:
        if filename == "polynomials.json":
            expected_variables, expected_specialization = contract[0], None
        elif filename == "q_equals_1.json":
            expected_variables, expected_specialization = contract[1], contract[2]
        else:
            expected_variables = expected_specialization = None
        if expected_variables is not None and tuple(variables) != expected_variables:
            raise ValueError(
                f"{path} variables {variables!r} do not match the evaluator contract "
                f"{list(expected_variables)!r}"
            )
        specialization = data.get("specialization")
        specialization_matches = specialization == expected_specialization
        if expected_specialization is not None:
            specialization_matches = specialization_matches and (
                isinstance(specialization, dict)
                and all(type(value) is int for value in specialization.values())
            )
        if not specialization_matches:
            raise ValueError(
                f"{path} specialization does not match the evaluator contract"
            )
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path} must contain at least one scored case")
    case_count = data.get("case_count")
    if type(case_count) is not int or case_count != len(cases):
        raise ValueError(f"{path} case_count does not match cases")

    case_ids: set[str] = set()
    scalar_coordinates, vector_coordinates = _PUBLIC_CASE_COORDINATES.get(
        identity["problem_name"], ((), ())
    )
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError(f"{path} contains a non-object case")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in case_ids:
            raise ValueError(f"{path} contains a missing or duplicate case_id")
        case_ids.add(case_id)
        for field in scalar_coordinates:
            if type(case.get(field)) is not int:
                raise ValueError(
                    f"{path} case {case_id} has an invalid integer coordinate {field!r}"
                )
        for field in vector_coordinates:
            coordinate = case.get(field)
            if not isinstance(coordinate, list) or any(
                type(value) is not int for value in coordinate
            ):
                raise ValueError(
                    f"{path} case {case_id} has an invalid integer-vector "
                    f"coordinate {field!r}"
                )
        count = case.get("count")
        if type(count) is not int or count <= 0:
            raise ValueError(f"{path} case {case_id} has an invalid object count")
        terms = case.get("terms")
        if not isinstance(terms, list) or not terms:
            raise ValueError(f"{path} case {case_id} has no polynomial terms")
        term_count = case.get("term_count")
        if type(term_count) is not int or term_count != len(terms):
            raise ValueError(f"{path} case {case_id} term_count does not match terms")
        exponents: set[str] = set()
        coefficient_total = 0
        for term in terms:
            if not isinstance(term, list) or len(term) != len(variables) + 1:
                raise ValueError(f"{path} case {case_id} has a malformed term")
            for variable, exponent in zip(variables, term[:-1], strict=True):
                if variable in {"partition", "pi", "sigma", "shape"}:
                    if (
                        not isinstance(exponent, list)
                        or not exponent
                        or any(type(part) is not int or part <= 0 for part in exponent)
                        or exponent != sorted(exponent, reverse=True)
                    ):
                        raise ValueError(
                            f"{path} case {case_id} has an invalid {variable} exponent"
                        )
                elif type(exponent) is not int or exponent < 0:
                    raise ValueError(
                        f"{path} case {case_id} has an invalid {variable} exponent"
                    )
            coefficient = term[-1]
            if type(coefficient) is not int or coefficient <= 0:
                raise ValueError(f"{path} case {case_id} has a nonpositive coefficient")
            coefficient_total += coefficient
            exponent_key = json.dumps(term[:-1], separators=(",", ":"), sort_keys=True)
            if exponent_key in exponents:
                raise ValueError(f"{path} case {case_id} has duplicate exponents")
            exponents.add(exponent_key)
        if coefficient_total != count:
            raise ValueError(
                f"{path} case {case_id} coefficients do not sum to object count"
            )
    return data


def _load_public_polynomials(problem_dir: Path) -> dict:
    return _load_public_data(problem_dir, "polynomials.json")


def _load_public_q_equals_1(problem_dir: Path) -> dict:
    return _load_public_data(problem_dir, "q_equals_1.json")


def _load_public_unrefined_marginal(
    problem_dir: Path, *, specialized_variable: str
) -> dict:
    """Load a constant q=1 marginal after the only grading is specialized."""

    data = _load_public_q_equals_1(problem_dir)
    if data["variables"] != [] or data.get("specialization") != {specialized_variable: 1}:
        raise ValueError(
            f"{problem_dir / 'data/q_equals_1.json'} must be the unrefined "
            f"{specialized_variable}=1 marginal"
        )
    for case in data["cases"]:
        if case["terms"] != [[case["count"]]]:
            raise ValueError(
                f"{problem_dir / 'data/q_equals_1.json'} case {case['case_id']} "
                "must encode its count as a constant polynomial"
            )
    return data


def _q_equals_1_terms(*, n: int, k: int, statistic: StatisticFunction) -> list[list[int]]:
    counter: Counter[int] = Counter()
    for partition in enumerate_narayana_partitions(n, k):
        value = _statistic_value(statistic(partition), partition.blocks)
        counter[value] += 1
    return [[degree, counter[degree]] for degree in sorted(counter) if counter[degree]]


def evaluate_q_equals_1_problem(
    *,
    problem_dir: str | Path,
    statistic: StatisticFunction,
) -> dict:
    problem_path = Path(problem_dir).resolve()
    identity = _require_supported_diagnostic_problem(problem_path)
    public_data = _load_public_q_equals_1(problem_path)
    results: list[dict] = []
    for case in public_data["cases"]:
        generated_terms = _q_equals_1_terms(n=int(case["n"]), k=int(case["k"]), statistic=statistic)
        l1_distance, mismatches = _term_mismatches(generated_terms, case["terms"], variables=("t",))
        results.append(
            {
                "case_id": case["case_id"],
                "n": int(case["n"]),
                "k": int(case["k"]),
                "count": int(case["count"]),
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not mismatches,
                "l1_distance": l1_distance,
                "mismatch_count": len(mismatches),
                "first_mismatch": mismatches[0] if mismatches else None,
                "mismatches": mismatches,
            }
        )

    correct_cases = sum(result["correct"] for result in results)
    return {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_cases == len(results),
        "correct_cases": correct_cases,
        "total_cases": len(results),
        "case_results": results,
    }


def evaluate_problem(
    *,
    problem_dir: str | Path,
    statistic: StatisticFunction,
    check_q_equals_1: bool = False,
) -> dict:
    problem_path = Path(problem_dir).resolve()
    identity = _require_supported_diagnostic_problem(problem_path)
    results: list[CaseResult] = []

    if check_q_equals_1:
        return evaluate_q_equals_1_problem(problem_dir=problem_path, statistic=statistic)

    public_data = _load_public_polynomials(problem_path)
    for case in public_data["cases"]:
        results.append(
            evaluate_case(
                n=int(case["n"]),
                k=int(case["k"]),
                case_id=case["case_id"],
                statistic=statistic,
                expected_terms=case["terms"],
            )
        )

    correct_cases = sum(result.correct for result in results)
    return {
        **identity,
        "split": "public",
        "passed": correct_cases == len(results),
        "correct_cases": correct_cases,
        "total_cases": len(results),
        "case_results": [asdict(result) for result in results],
    }


def evaluate_public_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic: StatisticFunction,
    order_seed: int | None = None,
) -> dict:
    """Check q=1 and q,t targets while evaluating each public object once."""

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[CaseResult] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        marginal_case = marginal_cases[case["case_id"]]
        n = int(case["n"])
        k = int(case["k"])
        if (int(marginal_case["n"]), int(marginal_case["k"])) != (n, k):
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")
        generated = generate_case(
            n=n,
            k=k,
            statistic=statistic,
            order_generator=order_generator,
        )
        full_results.append(
            _evaluate_generated_case(
                generated=generated,
                case_id=case["case_id"],
                expected_terms=case["terms"],
            )
        )
        marginal_results.append(
            _marginal_case_result(generated=generated, case=marginal_case)
        )

    correct_full = sum(result.correct for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": [asdict(result) for result in full_results],
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_type_b_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Type B q,t-Catalan analogue of :func:`evaluate_public_polynomial_checks`.

    Objects are type B Catalan paths keyed by size ``n`` (no ``k`` fiber); the
    public first statistic is ``area`` and the submission supplies the partner.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        n = int(case["n"])
        marginal_case = marginal_cases[case["case_id"]]
        if int(marginal_case["n"]) != n:
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")
        paths = _ordered_objects(enumerate_type_b_catalan_paths(n), order_generator)
        counter = joint_distribution(
            paths,
            lambda path: path.area(),
            lambda path: _statistic_value(statistic(path), path.steps),
        )
        generated_terms = canonical_terms(counter)

        l1_distance, mismatches = _term_mismatches(generated_terms, case["terms"], variables=("q", "t"))
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "count": len(paths),
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not mismatches,
                "l1_distance": l1_distance,
                "mismatch_count": len(mismatches),
                "first_mismatch": mismatches[0] if mismatches else None,
                "mismatches": mismatches,
            }
        )
        generated_marginal = _marginal_terms(generated_terms)
        l1_marginal, marginal_mismatches = _term_mismatches(
            generated_marginal, marginal_case["terms"], variables=("t",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "count": len(paths),
                "term_count": len(generated_marginal),
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_lpp_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Labelled parallelogram polyomino analogue of the type B checks.

    Objects are standardly labelled parallelogram polyominoes ``stLPP(m,n)``
    keyed by the bounding box ``(m,n)``; the public first statistic is the
    labelled ``area`` and the submission supplies the ``t``-partner. Each box is
    enumerated once and the submitted values are checked against both the full
    q,t target and its q=1 marginal.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        m = int(case["m"])
        n = int(case["n"])
        marginal_case = marginal_cases[case["case_id"]]
        if (int(marginal_case["m"]), int(marginal_case["n"])) != (m, n):
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        counter: Counter[tuple[int, int]] = Counter()
        count = 0
        for polyomino in _ordered_objects(
            iter_st_labelled_polyominoes(m, n), order_generator
        ):
            q_exponent = int(polyomino.area())
            t_exponent = _statistic_value(statistic(polyomino), polyomino.encoding)
            counter[(q_exponent, t_exponent)] += 1
            count += 1
        generated_terms = canonical_terms(counter)

        l1_distance, mismatches = _term_mismatches(generated_terms, case["terms"], variables=("q", "t"))
        full_results.append(
            {
                "case_id": case["case_id"],
                "m": m,
                "n": n,
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not mismatches,
                "l1_distance": l1_distance,
                "mismatch_count": len(mismatches),
                "first_mismatch": mismatches[0] if mismatches else None,
                "mismatches": mismatches,
            }
        )
        generated_marginal = _marginal_terms(generated_terms)
        l1_marginal, marginal_mismatches = _term_mismatches(
            generated_marginal, marginal_case["terms"], variables=("t",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "m": m,
                "n": n,
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_ddyck_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Doubly decorated Dyck path analogue of the labelled polyomino checks.

    Objects are standardly labelled doubly decorated Dyck paths ``LD(n)^{*k, •l}``
    keyed by the triple ``(n, k, l)``; the public first statistic is the decorated
    ``area`` and the submission supplies the ``t``-partner. Each fiber is
    enumerated once and the submitted values are checked against both the full
    q,t target and its q=1 marginal.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        n = int(case["n"])
        k = int(case["k"])
        l = int(case["l"])
        marginal_case = marginal_cases[case["case_id"]]
        if (int(marginal_case["n"]), int(marginal_case["k"]), int(marginal_case["l"])) != (n, k, l):
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        counter: Counter[tuple[int, int]] = Counter()
        count = 0
        for path in _ordered_objects(
            iter_decorated_labelled_dyck_paths(n, k, l), order_generator
        ):
            q_exponent = int(path.area())
            t_exponent = _statistic_value(statistic(path), path.encoding)
            counter[(q_exponent, t_exponent)] += 1
            count += 1
        generated_terms = canonical_terms(counter)

        l1_distance, mismatches = _term_mismatches(generated_terms, case["terms"], variables=("q", "t"))
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "k": k,
                "l": l,
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not mismatches,
                "l1_distance": l1_distance,
                "mismatch_count": len(mismatches),
                "first_mismatch": mismatches[0] if mismatches else None,
                "mismatches": mismatches,
            }
        )
        generated_marginal = _marginal_terms(generated_terms)
        l1_marginal, marginal_mismatches = _term_mismatches(
            generated_marginal, marginal_case["terms"], variables=("t",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "k": k,
                "l": l,
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_lrp_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Rise-decorated rectangular path analogue of the other polynomial checks.

    Objects are the standardly labelled decorated rectangular paths
    ``LRP(m+k, n+k)^{*k}`` keyed by the triple ``(m, n, k)``; the public first
    statistic is the decorated ``area`` and the submission supplies the
    ``t``-partner. Each fiber is enumerated once and the submitted values are
    checked against both the full q,t target and its q=1 marginal.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        m = int(case["m"])
        n = int(case["n"])
        k = int(case["k"])
        marginal_case = marginal_cases[case["case_id"]]
        if (int(marginal_case["m"]), int(marginal_case["n"]), int(marginal_case["k"])) != (m, n, k):
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        counter: Counter[tuple[int, int]] = Counter()
        count = 0
        for path in _ordered_objects(
            iter_labelled_rectangular_paths(m, n, k), order_generator
        ):
            q_exponent = int(path.area())
            t_exponent = _statistic_value(statistic(path), path.encoding)
            counter[(q_exponent, t_exponent)] += 1
            count += 1
        generated_terms = canonical_terms(counter)

        l1_distance, mismatches = _term_mismatches(generated_terms, case["terms"], variables=("q", "t"))
        full_results.append(
            {
                "case_id": case["case_id"],
                "m": m,
                "n": n,
                "k": k,
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not mismatches,
                "l1_distance": l1_distance,
                "mismatch_count": len(mismatches),
                "first_mismatch": mismatches[0] if mismatches else None,
                "mismatches": mismatches,
            }
        )
        generated_marginal = _marginal_terms(generated_terms)
        l1_marginal, marginal_mismatches = _term_mismatches(
            generated_marginal, marginal_case["terms"], variables=("t",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "m": m,
                "n": n,
                "k": k,
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_mld_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Multi-labelled Dyck path analogue of the doubly decorated Dyck path checks.

    Objects are the standard multi-labelled ``k^n`` Dyck paths ``LD_{k^n}`` keyed
    by the pair ``(n, k)``; the public first statistic is the rectangular ``area``
    and the submission supplies the ``t``-partner. Each fiber is enumerated once
    and the submitted values are checked against both the full q,t target and its
    q=1 marginal.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        n = int(case["n"])
        k = int(case["k"])
        marginal_case = marginal_cases[case["case_id"]]
        if (int(marginal_case["n"]), int(marginal_case["k"])) != (n, k):
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        counter: Counter[tuple[int, int]] = Counter()
        count = 0
        for path in _ordered_objects(
            iter_multi_labelled_dyck_paths(n, k), order_generator
        ):
            q_exponent = int(path.area())
            t_exponent = _statistic_value(statistic(path), path.encoding)
            counter[(q_exponent, t_exponent)] += 1
            count += 1
        generated_terms = canonical_terms(counter)

        l1_distance, mismatches = _term_mismatches(generated_terms, case["terms"], variables=("q", "t"))
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "k": k,
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not mismatches,
                "l1_distance": l1_distance,
                "mismatch_count": len(mismatches),
                "first_mismatch": mismatches[0] if mismatches else None,
                "mismatches": mismatches,
            }
        )
        generated_marginal = _marginal_terms(generated_terms)
        l1_marginal, marginal_mismatches = _term_mismatches(
            generated_marginal, marginal_case["terms"], variables=("t",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "k": k,
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def _trivariate_terms(counter: Counter[tuple[int, int, int]]) -> list[list[int]]:
    return [
        [int(d1), int(d2), int(d3), int(coefficient)]
        for (d1, d2, d3), coefficient in sorted(counter.items())
        if coefficient
    ]


def _third_marginal_terms(terms: list[list[int]]) -> list[list[int]]:
    counter: Counter[int] = Counter()
    for _d1, _d2, d3, coefficient in terms:
        counter[int(d3)] += int(coefficient)
    return [[degree, counter[degree]] for degree in sorted(counter) if counter[degree]]


def evaluate_tamari_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Trivariate analogue of the other polynomial checks.

    Objects are pairs ``(f, alpha)`` of a parking function and a Tamari-smaller
    Dyck path, keyed by the size ``n``. Two statistics are public here -- the
    chain length ``d(alpha, beta(f))`` and ``dinv(f)`` -- and the submission
    supplies the third. Each size is enumerated once and the submitted values are
    checked against both the full ``q1,q2,q3`` target and its ``q1 = q2 = 1``
    marginal.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("marginal and full public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        n = int(case["n"])
        marginal_case = marginal_cases[case["case_id"]]
        if int(marginal_case["n"]) != n:
            raise ValueError(f"marginal case identity mismatch for {case['case_id']}")

        counter: Counter[tuple[int, int, int]] = Counter()
        count = 0
        for pair in _ordered_objects(iter_tamari_parking_pairs(n), order_generator):
            chain = int(pair.chain())
            dinv = int(pair.dinv())
            third = _statistic_value(statistic(pair), pair.encoding)
            counter[(chain, dinv, third)] += 1
            count += 1
        generated_terms = _trivariate_terms(counter)

        l1_distance, mismatches = _term_mismatches(
            generated_terms, case["terms"], variables=("q1", "q2", "q3")
        )
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not mismatches,
                "l1_distance": l1_distance,
                "mismatch_count": len(mismatches),
                "first_mismatch": mismatches[0] if mismatches else None,
                "mismatches": mismatches,
            }
        )
        generated_marginal = _third_marginal_terms(generated_terms)
        l1_marginal, marginal_mismatches = _term_mismatches(
            generated_marginal, marginal_case["terms"], variables=("q3",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def _statistic_pair(value, object_description) -> tuple[int, int]:
    """Require the exact pair of nonnegative integers promised by the task."""
    if type(value) is not tuple or len(value) != 2:
        raise TypeError(
            f"statistic must return a pair of nonnegative integers, got "
            f"{type(value).__name__} {value!r} for {object_description}"
        )
    return (
        _statistic_value(value[0], object_description),
        _statistic_value(value[1], object_description),
    )


def evaluate_kostka_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Modified (q,t)-Kostka analogue of the other polynomial checks.

    Objects are the pairs ``(mu, T)`` with ``T`` a standard Young tableau, keyed
    by ``(lambda, mu)``; unlike every other statistic task no statistic is
    public, so the submission supplies **both** exponents at once as a pair. Each
    fiber ``SYT(lambda) x {mu}`` is enumerated once and the submitted values are
    checked against both the full q,t target ``K~_{lambda mu}(q, t)`` and its
    q=1 marginal.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        n = int(case["n"])
        lam = tuple(int(part) for part in case["lam"])
        mu = tuple(int(part) for part in case["mu"])
        marginal_case = marginal_cases[case["case_id"]]
        if (
            int(marginal_case["n"]),
            tuple(int(part) for part in marginal_case["lam"]),
            tuple(int(part) for part in marginal_case["mu"]),
        ) != (n, lam, mu):
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        counter: Counter[tuple[int, int]] = Counter()
        count = 0
        for tableau in _ordered_objects(
            iter_kostka_standard_tableaux(lam, mu), order_generator
        ):
            counter[_statistic_pair(statistic(tableau), tableau.encoding)] += 1
            count += 1
        generated_terms = canonical_terms(counter)

        l1_distance, mismatches = _term_mismatches(generated_terms, case["terms"], variables=("q", "t"))
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "lam": list(lam),
                "mu": list(mu),
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not mismatches,
                "l1_distance": l1_distance,
                "mismatch_count": len(mismatches),
                "first_mismatch": mismatches[0] if mismatches else None,
                "mismatches": mismatches,
            }
        )
        generated_marginal = _marginal_terms(generated_terms)
        l1_marginal, marginal_mismatches = _term_mismatches(
            generated_marginal, marginal_case["terms"], variables=("t",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "lam": list(lam),
                "mu": list(mu),
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_ttree_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Tiered tree analogue of the doubly decorated Dyck path checks.

    Objects are standard zero-rooted tiered trees ``RTT_0(mu)`` keyed by the
    partition ``mu`` of tier sizes; the public first statistic is ``inv`` and the
    submission supplies the ``t``-partner. Each fiber is enumerated once and the
    submitted values are checked against both the full q,t target and its q=1
    marginal.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        mu = tuple(int(part) for part in case["mu"])
        marginal_case = marginal_cases[case["case_id"]]
        if tuple(int(part) for part in marginal_case["mu"]) != mu:
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        counter: Counter[tuple[int, int]] = Counter()
        count = 0
        for tree in _ordered_objects(iter_zero_rooted_tiered_trees(mu), order_generator):
            q_exponent = int(tree.inv())
            t_exponent = _statistic_value(statistic(tree), tree.encoding)
            counter[(q_exponent, t_exponent)] += 1
            count += 1
        generated_terms = canonical_terms(counter)

        l1_distance, mismatches = _term_mismatches(generated_terms, case["terms"], variables=("q", "t"))
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": int(case["n"]),
                "mu": list(mu),
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not mismatches,
                "l1_distance": l1_distance,
                "mismatch_count": len(mismatches),
                "first_mismatch": mismatches[0] if mismatches else None,
                "mismatches": mismatches,
            }
        )
        generated_marginal = _marginal_terms(generated_terms)
        l1_marginal, marginal_mismatches = _term_mismatches(
            generated_marginal, marginal_case["terms"], variables=("t",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": int(case["n"]),
                "mu": list(mu),
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def _normalize_composition(value, n: int) -> tuple[int, ...]:
    """Validate a submitted composition of ``n`` and return its sorted partition.

    A submission for the Shareshian--Wachs problem returns a composition of ``n``
    (``theta(sigma)``); only its underlying partition ``lambda(theta(sigma))``
    matters, so the checker sorts it. Anything that is not a composition of ``n``
    is rejected.
    """
    if type(value) not in (tuple, list) or len(value) > n:
        raise ValueError(
            f"statistic must return a composition of {n}, got {type(value).__name__}"
        )
    parts = tuple(value)
    if (
        any(type(part) is not int for part in parts)
        or any(part <= 0 or part > n for part in parts)
        or sum(parts) != n
    ):
        raise ValueError(
            f"statistic must return a composition of {n}, got {type(value).__name__}"
        )
    return tuple(sorted(parts, reverse=True))


def _partition_full_target(terms: list) -> Counter[tuple[tuple[int, ...], int]]:
    counter: Counter[tuple[tuple[int, ...], int]] = Counter()
    for partition, q_exponent, coefficient in terms:
        if coefficient:
            counter[(tuple(int(part) for part in partition), int(q_exponent))] += int(coefficient)
    return counter


def _partition_marginal_target(terms: list) -> Counter[tuple[int, ...]]:
    counter: Counter[tuple[int, ...]] = Counter()
    for partition, coefficient in terms:
        if coefficient:
            counter[tuple(int(part) for part in partition)] += int(coefficient)
    return counter


def _partition_counter_diff(generated: Counter, expected: Counter, *, describe) -> tuple[int, list[dict]]:
    l1_distance = 0
    mismatches: list[dict] = []
    for key in sorted(set(generated) | set(expected)):
        difference = generated.get(key, 0) - expected.get(key, 0)
        if difference:
            l1_distance += abs(difference)
            mismatches.append(
                {
                    **describe(key),
                    "generated_coeff": generated.get(key, 0),
                    "expected_coeff": expected.get(key, 0),
                    "difference": difference,
                }
            )
    return l1_distance, mismatches


def evaluate_uig_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Shareshian--Wachs ``e``-positivity analogue of the other polynomial checks.

    Objects are Dyck graphs (natural unit interval graphs) ``G`` on ``[n]`` paired
    with a ``G``-nondescent permutation ``sigma in D_G^0``, keyed per graph by its
    right-endpoint vector ``b``. The submission returns a composition ``theta(sigma)``
    of ``n``; the checker groups the objects by the underlying partition
    ``lambda(theta(sigma))`` and by the public ``ginv`` statistic and checks the
    resulting partition-graded ``q``-polynomial against the elementary expansion of
    ``chi_G``. Each fiber is enumerated once; the full target and its ``q = 1``
    partition-multiset marginal are checked from the same submitted values.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        n = int(case["n"])
        b = tuple(int(value) for value in case["b"])
        marginal_case = marginal_cases[case["case_id"]]
        if tuple(int(value) for value in marginal_case["b"]) != b:
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        generated_full: Counter[tuple[tuple[int, ...], int]] = Counter()
        generated_marginal: Counter[tuple[int, ...]] = Counter()
        count = 0
        for obj in _ordered_objects(iter_uig_permutations_for_vector(b), order_generator):
            partition = _normalize_composition(statistic(obj), n)
            q_exponent = int(obj.ginv())
            if q_exponent < 0:
                raise ValueError(f"ginv must be nonnegative, got {q_exponent} for {obj.encoding}")
            generated_full[(partition, q_exponent)] += 1
            generated_marginal[partition] += 1
            count += 1

        expected_full = _partition_full_target(case["terms"])
        l1_full, full_mismatches = _partition_counter_diff(
            generated_full,
            expected_full,
            describe=lambda key: {"partition": list(key[0]), "q": key[1]},
        )
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "b": list(b),
                "count": count,
                "term_count": len(generated_full),
                "expected_term_count": len(expected_full),
                "correct": not full_mismatches,
                "l1_distance": l1_full,
                "mismatch_count": len(full_mismatches),
                "first_mismatch": full_mismatches[0] if full_mismatches else None,
                "mismatches": full_mismatches,
            }
        )
        expected_marginal = _partition_marginal_target(marginal_case["terms"])
        l1_marginal, marginal_mismatches = _partition_counter_diff(
            generated_marginal,
            expected_marginal,
            describe=lambda key: {"partition": list(key)},
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "b": list(b),
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(expected_marginal),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_llt_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Unicellular LLT analogue of the other polynomial checks.

    Objects are Dyck graphs (natural unit interval graphs) ``G`` on ``[n]`` paired
    with a standard Young tableau ``T`` of ``n`` cells, keyed per graph by its
    right-endpoint vector ``b``. The submission returns the ``q``-exponent
    ``lltstat_G(T)``; the checker groups the objects by the shape ``lambda`` of
    ``T``, which is read off the object rather than submitted, and checks the
    resulting shape-graded ``q``-polynomial against the Schur expansion of
    ``LLT_G``. Each fiber is enumerated once; the ``q = 1`` marginal recorded from
    the same pass is the shape distribution ``c_lambda(1) = f^lambda``, an
    object-model identity that holds for every statistic.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        n = int(case["n"])
        b = tuple(int(value) for value in case["b"])
        marginal_case = marginal_cases[case["case_id"]]
        if tuple(int(value) for value in marginal_case["b"]) != b:
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        generated_full: Counter[tuple[tuple[int, ...], int]] = Counter()
        generated_marginal: Counter[tuple[int, ...]] = Counter()
        count = 0
        for obj in _ordered_objects(iter_uig_tableaux_for_vector(b), order_generator):
            q_exponent = _statistic_value(statistic(obj), obj.encoding)
            generated_full[(obj.shape, q_exponent)] += 1
            generated_marginal[obj.shape] += 1
            count += 1

        expected_full = _partition_full_target(case["terms"])
        l1_full, full_mismatches = _partition_counter_diff(
            generated_full,
            expected_full,
            describe=lambda key: {"partition": list(key[0]), "q": key[1]},
        )
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "b": list(b),
                "count": count,
                "term_count": len(generated_full),
                "expected_term_count": len(expected_full),
                "correct": not full_mismatches,
                "l1_distance": l1_full,
                "mismatch_count": len(full_mismatches),
                "first_mismatch": full_mismatches[0] if full_mismatches else None,
                "mismatches": full_mismatches,
            }
        )
        expected_marginal = _partition_marginal_target(marginal_case["terms"])
        l1_marginal, marginal_mismatches = _partition_counter_diff(
            generated_marginal,
            expected_marginal,
            describe=lambda key: {"partition": list(key)},
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "b": list(b),
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(expected_marginal),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def _partition_pair_full_target(terms: list) -> Counter[tuple[tuple[int, ...], tuple[int, ...], int]]:
    counter: Counter[tuple[tuple[int, ...], tuple[int, ...], int]] = Counter()
    for pi, sigma, q_exponent, coefficient in terms:
        if coefficient:
            key = (
                tuple(int(part) for part in pi),
                tuple(int(part) for part in sigma),
                int(q_exponent),
            )
            counter[key] += int(coefficient)
    return counter


def _partition_pair_marginal_target(terms: list) -> Counter[tuple[tuple[int, ...], tuple[int, ...]]]:
    counter: Counter[tuple[tuple[int, ...], tuple[int, ...]]] = Counter()
    for pi, sigma, coefficient in terms:
        if coefficient:
            key = (tuple(int(part) for part in pi), tuple(int(part) for part in sigma))
            counter[key] += int(coefficient)
    return counter


def evaluate_mjack_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Matchings-Jack analogue of the other polynomial checks.

    Objects are perfect matchings of ``N_n`` paired with a partition ``lambda`` of
    ``n``, keyed per case by ``lambda``. The submission returns the exponent
    ``mjack(delta)``; the checker groups the objects of each case by the pair of
    cycle types ``(pi, sigma) = (Lambda(delta, eps), Lambda(delta, delta_lambda))``,
    which is read off the object rather than submitted, and checks the resulting
    ``(pi, sigma)``-graded ``q``-polynomial against the Jack connection coefficients.
    Each case is enumerated once; the ``q = 1`` marginal recorded from the same pass
    is the fiber-size table ``c^lambda_{pi,sigma}(1) = |G^lambda_{pi,sigma}|``, an
    object-model identity that holds for every statistic.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        n = int(case["n"])
        lam = tuple(int(part) for part in case["lambda"])
        marginal_case = marginal_cases[case["case_id"]]
        if tuple(int(part) for part in marginal_case["lambda"]) != lam:
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        generated_full: Counter[tuple[tuple[int, ...], tuple[int, ...], int]] = Counter()
        generated_marginal: Counter[tuple[tuple[int, ...], tuple[int, ...]]] = Counter()
        count = 0
        zero_locus_failure = None
        for obj in _ordered_objects(
            iter_jack_matchings_for_partition(lam), order_generator
        ):
            q_exponent = _statistic_value(statistic(obj), obj.encoding)
            if (q_exponent == 0) != obj.is_bipartite and zero_locus_failure is None:
                zero_locus_failure = (
                    f"mjack must be zero exactly on bipartite matchings; "
                    f"got {q_exponent} for {obj.encoding}"
                )
            fiber = (obj.epsilon_type(), obj.reference_type())
            generated_full[(*fiber, q_exponent)] += 1
            generated_marginal[fiber] += 1
            count += 1

        expected_full = _partition_pair_full_target(case["terms"])
        l1_full, full_mismatches = _partition_counter_diff(
            generated_full,
            expected_full,
            describe=lambda key: {"pi": list(key[0]), "sigma": list(key[1]), "q": key[2]},
        )
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "lambda": list(lam),
                "count": count,
                "term_count": len(generated_full),
                "expected_term_count": len(expected_full),
                "correct": not full_mismatches and zero_locus_failure is None,
                "zero_locus_failure": zero_locus_failure,
                "l1_distance": l1_full,
                "mismatch_count": len(full_mismatches),
                "first_mismatch": full_mismatches[0] if full_mismatches else None,
                "mismatches": full_mismatches,
            }
        )
        expected_marginal = _partition_pair_marginal_target(marginal_case["terms"])
        l1_marginal, marginal_mismatches = _partition_counter_diff(
            generated_marginal,
            expected_marginal,
            describe=lambda key: {"pi": list(key[0]), "sigma": list(key[1])},
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "lambda": list(lam),
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(expected_marginal),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_involution_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Orbit-harmonics Hilbert series analogue of the other polynomial checks.

    Objects are involutions, keyed per fiber by the pair ``(n, a)`` of the size and
    the number of fixed points, both read off the object rather than submitted. The
    submission returns the ``q``-exponent ``istat_{n,a}(pi)``, and the checker
    compares its distribution over ``M_{n,a}`` with the public Hilbert series
    ``H_{n,a}(q)``. Each fiber is enumerated once; the ``q = 1`` marginal recorded
    from the same pass is the fixed-point distribution of the fiber, an object-model
    identity that holds for every statistic.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        n = int(case["n"])
        a = int(case["a"])
        marginal_case = marginal_cases[case["case_id"]]
        if int(marginal_case["n"]) != n or int(marginal_case["a"]) != a:
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        generated: Counter[int] = Counter()
        fixed_points: Counter[int] = Counter()
        count = 0
        for obj in _ordered_objects(
            iter_involutions_with_fixed_points(n, a), order_generator
        ):
            generated[_statistic_value(statistic(obj), obj.encoding)] += 1
            fixed_points[obj.fix] += 1
            count += 1

        generated_terms = [[degree, generated[degree]] for degree in sorted(generated)]
        l1_full, full_mismatches = _term_mismatches(
            generated_terms, case["terms"], variables=("q",)
        )
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "a": a,
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not full_mismatches,
                "l1_distance": l1_full,
                "mismatch_count": len(full_mismatches),
                "first_mismatch": full_mismatches[0] if full_mismatches else None,
                "mismatches": full_mismatches,
            }
        )
        marginal_terms = [[value, fixed_points[value]] for value in sorted(fixed_points)]
        l1_marginal, marginal_mismatches = _term_mismatches(
            marginal_terms, marginal_case["terms"], variables=("fixed_points",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "a": a,
                "count": count,
                "term_count": len(marginal_terms),
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_qgamma_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """q-Eulerian gamma analogue of the other polynomial checks.

    Objects are permutations with no double descent and no final descent, keyed per
    fiber by the pair ``(n, k)`` of the size and one more than the number of
    descents, both read off the object rather than submitted. The submission returns
    the ``q``-exponent ``qgamma(sigma)``, and the checker compares its distribution
    over ``Gamma_{n,k}`` with the public coefficient ``a_{n,k}(q)``. Each fiber is
    enumerated once; the ``q = 1`` marginal recorded from the same pass is the
    descent count of the fiber, an object-model identity that holds for every
    statistic.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        n = int(case["n"])
        k = int(case["k"])
        marginal_case = marginal_cases[case["case_id"]]
        if int(marginal_case["n"]) != n or int(marginal_case["k"]) != k:
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        generated: Counter[int] = Counter()
        descents: Counter[int] = Counter()
        count = 0
        for obj in _ordered_objects(
            iter_gamma_permutations_for_descents(n, k), order_generator
        ):
            generated[_statistic_value(statistic(obj), obj.encoding)] += 1
            descents[obj.descents] += 1
            count += 1

        generated_terms = [[degree, generated[degree]] for degree in sorted(generated)]
        l1_full, full_mismatches = _term_mismatches(
            generated_terms, case["terms"], variables=("q",)
        )
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "k": k,
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not full_mismatches,
                "l1_distance": l1_full,
                "mismatch_count": len(full_mismatches),
                "first_mismatch": full_mismatches[0] if full_mismatches else None,
                "mismatches": full_mismatches,
            }
        )
        marginal_terms = [[value, descents[value]] for value in sorted(descents)]
        l1_marginal, marginal_mismatches = _term_mismatches(
            marginal_terms, marginal_case["terms"], variables=("descents",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "k": k,
                "count": count,
                "term_count": len(marginal_terms),
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_rtt_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Rooted tiered tree analogue of the zero-rooted tiered tree checks.

    Objects are standard rooted tiered trees ``stRTT(mu)`` keyed by the
    partition ``mu`` of tier sizes; unlike the zero-rooted family the root
    carries an ordinary label and joins the compatibility relation. The public
    first statistic is ``inv`` and the submission supplies the ``t``-partner.
    Each fiber is enumerated once and the submitted values are checked against
    both the full q,t target and its q=1 marginal.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        mu = tuple(int(part) for part in case["mu"])
        marginal_case = marginal_cases[case["case_id"]]
        if tuple(int(part) for part in marginal_case["mu"]) != mu:
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        counter: Counter[tuple[int, int]] = Counter()
        count = 0
        for tree in _ordered_objects(iter_rooted_tiered_trees(mu), order_generator):
            q_exponent = int(tree.inv())
            t_exponent = _statistic_value(statistic(tree), tree.encoding)
            counter[(q_exponent, t_exponent)] += 1
            count += 1
        generated_terms = canonical_terms(counter)

        l1_distance, mismatches = _term_mismatches(generated_terms, case["terms"], variables=("q", "t"))
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": int(case["n"]),
                "mu": list(mu),
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not mismatches,
                "l1_distance": l1_distance,
                "mismatch_count": len(mismatches),
                "first_mismatch": mismatches[0] if mismatches else None,
                "mismatches": mismatches,
            }
        )
        generated_marginal = _marginal_terms(generated_terms)
        l1_marginal, marginal_mismatches = _term_mismatches(
            generated_marginal, marginal_case["terms"], variables=("t",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": int(case["n"]),
                "mu": list(mu),
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_tgt_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Checks for the threshold-graph spanning tree problem.

    Objects are spanning trees of a connected threshold graph on ``{0, ..., n}``,
    keyed per fiber by the graph's up-degree vector. The public first statistic
    is ``inv`` and the submission supplies the ``t``-partner. The graph is part
    of the object, not just the fiber key, because the missing statistic
    provably depends on it. Each fiber is enumerated once and the submitted
    values are checked against both the full q,t target and its q=1 marginal,
    which is a theorem rather than a conjecture.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        up_degrees = tuple(int(value) for value in case["up_degrees"])
        marginal_case = marginal_cases[case["case_id"]]
        if tuple(int(value) for value in marginal_case["up_degrees"]) != up_degrees:
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        counter: Counter[tuple[int, int]] = Counter()
        count = 0
        objects = iter_threshold_spanning_trees(up_degrees)
        for tree in _ordered_objects(objects, order_generator):
            q_exponent = int(tree.inv())
            t_exponent = _statistic_value(statistic(tree), tree.encoding)
            counter[(q_exponent, t_exponent)] += 1
            count += 1
        generated_terms = canonical_terms(counter)

        l1_distance, mismatches = _term_mismatches(generated_terms, case["terms"], variables=("q", "t"))
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": int(case["n"]),
                "up_degrees": list(up_degrees),
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not mismatches,
                "l1_distance": l1_distance,
                "mismatch_count": len(mismatches),
                "first_mismatch": mismatches[0] if mismatches else None,
                "mismatches": mismatches,
            }
        )
        generated_marginal = _marginal_terms(generated_terms)
        l1_marginal, marginal_mismatches = _term_mismatches(
            generated_marginal, marginal_case["terms"], variables=("t",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": int(case["n"]),
                "up_degrees": list(up_degrees),
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def _partition_bigraded_target(terms: list) -> Counter[tuple[tuple[int, ...], int, int]]:
    counter: Counter[tuple[tuple[int, ...], int, int]] = Counter()
    for partition, u_exponent, t_exponent, coefficient in terms:
        if coefficient:
            key = (
                tuple(int(part) for part in partition),
                int(u_exponent),
                int(t_exponent),
            )
            counter[key] += int(coefficient)
    return counter


def evaluate_gpf_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
    lattice: bool = False,
) -> dict:
    """Checks for the two selected-area gamma-parking-function problems.

    Objects are pairs ``(p, S)`` with ``p`` a gamma-parking function of content
    ``lambda`` (a lattice one when ``lattice``) and ``S`` a subset of its area
    cells, keyed per fiber by ``(gamma, lambda)``. The public first statistic is
    ``#S``, which grades ``u``, and the submission supplies the ``t``-partner.
    The e-composition ``eta(p)`` is read off the object rather than submitted
    and grades the target by a partition, exactly as the shape does in the
    unicellular LLT problem. Each fiber is enumerated once; the ``u = 1``
    marginal recorded from the same pass is the eta-graded distribution of the
    unknown statistic.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("u=1 and u,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        gamma = tuple(int(part) for part in case["gamma"])
        content = tuple(int(part) for part in case["content"])
        marginal_case = marginal_cases[case["case_id"]]
        if (
            tuple(int(part) for part in marginal_case["gamma"]) != gamma
            or tuple(int(part) for part in marginal_case["content"]) != content
        ):
            raise ValueError(f"u=1 case identity mismatch for {case['case_id']}")

        generated_full: Counter[tuple[tuple[int, ...], int, int]] = Counter()
        generated_marginal: Counter[tuple[tuple[int, ...], int]] = Counter()
        count = 0
        objects = iter_gamma_parking_selections(gamma, content, lattice=lattice)
        for obj in _ordered_objects(objects, order_generator):
            eta = obj.eta()
            u_exponent = obj.selected_count()
            t_exponent = _statistic_value(statistic(obj), obj.encoding)
            generated_full[(eta, u_exponent, t_exponent)] += 1
            generated_marginal[(eta, t_exponent)] += 1
            count += 1

        expected_full = _partition_bigraded_target(case["terms"])
        l1_full, full_mismatches = _partition_counter_diff(
            generated_full,
            expected_full,
            describe=lambda key: {"partition": list(key[0]), "u": key[1], "t": key[2]},
        )
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": int(case["n"]),
                "gamma": list(gamma),
                "content": list(content),
                "count": count,
                "term_count": len(generated_full),
                "expected_term_count": len(expected_full),
                "correct": not full_mismatches,
                "l1_distance": l1_full,
                "mismatch_count": len(full_mismatches),
                "first_mismatch": full_mismatches[0] if full_mismatches else None,
                "mismatches": full_mismatches,
            }
        )
        expected_marginal = _partition_full_target(marginal_case["terms"])
        l1_marginal, marginal_mismatches = _partition_counter_diff(
            generated_marginal,
            expected_marginal,
            describe=lambda key: {"partition": list(key[0]), "t": key[1]},
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": int(case["n"]),
                "gamma": list(gamma),
                "content": list(content),
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(expected_marginal),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_lgpf_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """The lattice mode of ``evaluate_gpf_polynomial_checks``."""
    return evaluate_gpf_polynomial_checks(
        problem_dir=problem_dir,
        statistic=statistic,
        order_seed=order_seed,
        lattice=True,
    )


def evaluate_promotion_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Promotion cyclic sieving analogue of the other polynomial checks.

    Objects are standard Young tableaux of rectangular or staircase shape, keyed per
    case by that shape, which is read off the object rather than submitted. The
    submission returns the exponent, and the checker compares its distribution over
    ``SYT(lambda)`` with the public sieving polynomial ``C_lambda(q)``. Each shape is
    enumerated once; the ``q = 1`` marginal recorded from the same pass is the shape
    and size of the fiber, an object-model identity that holds for every statistic.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        shape = tuple(int(part) for part in case["shape"])
        marginal_case = marginal_cases[case["case_id"]]
        if tuple(int(part) for part in marginal_case["shape"]) != shape:
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        generated: Counter[int] = Counter()
        shapes: Counter[tuple[int, ...]] = Counter()
        count = 0
        for obj in _ordered_objects(
            iter_promotion_tableaux_for_shape(shape), order_generator
        ):
            generated[_statistic_value(statistic(obj), obj.encoding)] += 1
            shapes[obj.shape] += 1
            count += 1

        generated_terms = [[degree, generated[degree]] for degree in sorted(generated)]
        l1_full, full_mismatches = _term_mismatches(
            generated_terms, case["terms"], variables=("q",)
        )
        full_results.append(
            {
                "case_id": case["case_id"],
                "shape": list(shape),
                "modulus": int(case["modulus"]),
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not full_mismatches,
                "l1_distance": l1_full,
                "mismatch_count": len(full_mismatches),
                "first_mismatch": full_mismatches[0] if full_mismatches else None,
                "mismatches": full_mismatches,
            }
        )
        expected_marginal = _partition_marginal_target(marginal_case["terms"])
        l1_marginal, marginal_mismatches = _partition_counter_diff(
            shapes,
            expected_marginal,
            describe=lambda key: {"shape": list(key)},
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "shape": list(shape),
                "count": count,
                "term_count": len(shapes),
                "expected_term_count": len(expected_marginal),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_asm_q_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """Check a statistic on ASMs against the public DPP weight enumerator."""

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        n = int(case["n"])
        marginal_case = marginal_cases[case["case_id"]]
        if int(marginal_case["n"]) != n:
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")
        generated: Counter[int] = Counter()
        count = 0
        for obj in _ordered_objects(
            enumerate_alternating_sign_matrices(n), order_generator
        ):
            generated[_statistic_value(statistic(obj), obj.encoding)] += 1
            count += 1

        generated_terms = [[degree, generated[degree]] for degree in sorted(generated)]
        l1_full, full_mismatches = _term_mismatches(
            generated_terms, case["terms"], variables=("q",)
        )
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "count": count,
                "term_count": len(generated_terms),
                "expected_term_count": len(case["terms"]),
                "correct": not full_mismatches,
                "l1_distance": l1_full,
                "mismatch_count": len(full_mismatches),
                "first_mismatch": full_mismatches[0] if full_mismatches else None,
                "mismatches": full_mismatches,
            }
        )
        marginal_terms = [[n, count]]
        l1_marginal, marginal_mismatches = _term_mismatches(
            marginal_terms, marginal_case["terms"], variables=("n",)
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "count": count,
                "term_count": 1,
                "expected_term_count": len(marginal_case["terms"]),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_q = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_q["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_q,
    }


def evaluate_kreweras_polynomial_checks(
    *,
    problem_dir: str | Path,
    statistic,
    order_seed: int | None = None,
) -> dict:
    """q-Kreweras analogue of the other polynomial checks.

    Objects are noncrossing partitions of ``[n]``, keyed per case by ``n``. The
    submission returns the ``q``-exponent; the checker groups the objects by their
    block type, which is read off the object rather than submitted, and checks the
    resulting type-graded ``q``-polynomial against the public q-Kreweras numbers.
    The unseeded pass enumerates each size once.  A seeded replay streams a secret
    cyclic rotation from two restartable iterators without retaining the fiber.
    The ``q = 1`` marginal recorded from the same evaluation is the block-type
    distribution, an object-model identity that holds for every statistic.
    """

    problem_path = Path(problem_dir).resolve()
    identity = _problem_identity(problem_path)
    full_data = _load_public_polynomials(problem_path)
    marginal_data = _load_public_q_equals_1(problem_path)
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    if set(marginal_cases) != {case["case_id"] for case in full_data["cases"]}:
        raise ValueError("q=1 and q,t public cases do not agree")

    full_results: list[dict] = []
    marginal_results: list[dict] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case in full_data["cases"]:
        n = int(case["n"])
        marginal_case = marginal_cases[case["case_id"]]
        if int(marginal_case["n"]) != n:
            raise ValueError(f"q=1 case identity mismatch for {case['case_id']}")

        generated_full: Counter[tuple[tuple[int, ...], int]] = Counter()
        generated_marginal: Counter[tuple[int, ...]] = Counter()
        count = 0
        with closing(
            _iter_kreweras_objects(
                lambda n=n: iter_noncrossing_partitions(n),
                case["count"],
                order_generator,
            )
        ) as partitions:
            for obj in partitions:
                exponent = _statistic_value(statistic(obj), obj.blocks)
                generated_full[(obj.block_type, exponent)] += 1
                generated_marginal[obj.block_type] += 1
                count += 1

        expected_full = _partition_full_target(case["terms"])
        l1_full, full_mismatches = _partition_counter_diff(
            generated_full,
            expected_full,
            describe=lambda key: {"partition": list(key[0]), "q": key[1]},
        )
        full_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "count": count,
                "term_count": len(generated_full),
                "expected_term_count": len(expected_full),
                "correct": not full_mismatches,
                "l1_distance": l1_full,
                "mismatch_count": len(full_mismatches),
                "first_mismatch": full_mismatches[0] if full_mismatches else None,
                "mismatches": full_mismatches,
            }
        )
        expected_marginal = _partition_marginal_target(marginal_case["terms"])
        l1_marginal, marginal_mismatches = _partition_counter_diff(
            generated_marginal,
            expected_marginal,
            describe=lambda key: {"partition": list(key)},
        )
        marginal_results.append(
            {
                "case_id": case["case_id"],
                "n": n,
                "count": count,
                "term_count": len(generated_marginal),
                "expected_term_count": len(expected_marginal),
                "correct": not marginal_mismatches,
                "l1_distance": l1_marginal,
                "mismatch_count": len(marginal_mismatches),
                "first_mismatch": marginal_mismatches[0] if marginal_mismatches else None,
                "mismatches": marginal_mismatches,
            }
        )

    correct_full = sum(result["correct"] for result in full_results)
    correct_marginal = sum(result["correct"] for result in marginal_results)
    full_qt = {
        **identity,
        "split": "public",
        "passed": correct_full == len(full_results),
        "correct_cases": correct_full,
        "total_cases": len(full_results),
        "case_results": full_results,
    }
    q_equals_1 = {
        **identity,
        "split": "public_q_equals_1",
        "passed": correct_marginal == len(marginal_results),
        "correct_cases": correct_marginal,
        "total_cases": len(marginal_results),
        "case_results": marginal_results,
    }
    return {
        "passed": bool(q_equals_1["passed"] and full_qt["passed"]),
        "q_equals_1": q_equals_1,
        "full_qt": full_qt,
    }


def evaluate_submission_file(
    *,
    problem_dir: str | Path,
    submission_path: str | Path,
    check_q_equals_1: bool = False,
    function_name: str = "statistic",
) -> dict:
    """Diagnose a trusted Problem 1 file with caller privileges."""
    _require_supported_diagnostic_problem(Path(problem_dir).resolve())
    statistic = load_statistic_function(submission_path, function_name=function_name)
    return evaluate_problem(
        problem_dir=problem_dir,
        statistic=statistic,
        check_q_equals_1=check_q_equals_1,
    )
