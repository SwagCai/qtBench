"""qtBench admission checks.

Passing these checks is a **necessary** condition for a submission to be
scored, never a sufficient one. A genuine combinatorial statistic or bijection
passes them, but so can a polynomial-time "ranking" construction that reads the
answer off the known target polynomial and distributes values by rank. No
executable test can separate a natural statistic from such a construction,
because the construction is a bona fide polynomial-time function of a single
object (see ``docs/checker.md``).

What the checks *do* guarantee cheaply is that a passing submission:

1. passes the restricted-Python capability screen (no imports, reflection, I/O,
   or networking through the admitted language);
2. is short (no embedded answer table can fit);
3. reproduces the public target on every public size;
4. returns the same value for each public object in a fresh shuffled replay;
5. stays within the configured time and memory budgets on sampled large
   adversarial objects (which rules out straightforward enumeration of the
   exponential object set).

The checker deliberately makes no semantic or mathematical-authenticity
decision about a surviving program.
"""

from __future__ import annotations

import ast
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import io
import math
import multiprocessing
import os
import pickle
import random
import secrets
import shutil
import signal
import subprocess
import sys
import time
import tokenize
import tracemalloc
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from qtbench.combinatorics import (
    AlternatingSignMatrix,
    ConnectedGraph,
    DecoratedLabelledDyckPath,
    GammaParkingSelection,
    GammaPermutation,
    Involution,
    JackMatching,
    KostkaStandardTableau,
    LabelledParallelogramPolyomino,
    LabelledRectangularPath,
    MultiLabelledDyckPath,
    NoncrossingPartition,
    ParkingFunction,
    PartitionMatrixInversion,
    PromotionTableau,
    StandardMacdonaldFilling,
    ShiftedSetValuedTableau,
    SuccessiveRankPartition,
    RootedTieredTree,
    TamariParkingPair,
    ThresholdSpanningTree,
    TypeBCatalanPath,
    UnitIntervalGraphPermutation,
    UnitIntervalGraphTableau,
    ZeroRootedTieredTree,
    area_bounce_distribution,
    adversarial_alternating_sign_matrices,
    alternating_sign_matrix_size,
    canonical_decorated_labelled_dyck_path,
    canonical_connected_graph,
    canonical_gamma_parking_selection,
    canonical_gamma_permutation,
    canonical_involution,
    canonical_jack_matching,
    canonical_kostka_standard_tableau,
    canonical_labelled_rectangular_path,
    canonical_multi_labelled_dyck_path,
    canonical_parking_function,
    canonical_improper_partition_matrix,
    canonical_restricted_inversion_sequence,
    canonical_promotion_tableau,
    canonical_standard_macdonald_filling,
    canonical_shifted_setvalued_tableau,
    canonical_successive_rank_partition,
    canonical_rooted_tiered_tree,
    canonical_standard_labelling,
    canonical_tamari_parking_pair,
    canonical_threshold_spanning_tree,
    canonical_zero_rooted_tiered_tree,
    canonical_unit_interval_graph_permutation,
    canonical_unit_interval_graph_tableau,
    connected_graph_size,
    dyck_area,
    dyck_bounce,
    enumerate_dyck_paths,
    first_return,
    gamma_parking_selection,
    gamma_permutation_from_descent_set,
    intermediate_tamari_parking_pairs,
    involution,
    is_dyck_path,
    is_connected_graph_encoding,
    is_shifted_setvalued_tableau_encoding,
    is_successive_rank_partition_encoding,
    jack_matching,
    is_parallelogram_polyomino,
    is_parking_function_word,
    is_partition_matrix_inversion_encoding,
    is_standard_macdonald_filling,
    iter_parallelogram_polyominoes,
    iter_parking_functions,
    iter_improper_partition_matrices,
    iter_restricted_inversion_sequences,
    iter_standard_macdonald_fillings,
    iter_shifted_setvalued_tableaux,
    iter_successive_rank_partitions,
    polyomino_area,
    polyomino_area_bounce_distribution,
    polyomino_bounce,
    polyomino_count,
    polyomino_dimensions,
    polyomino_from_ranks,
    polyomino_size,
    parking_function,
    partition_matrix_inversion_size,
    shifted_extensions,
    shifted_shape_cells,
    shifted_tableau_size,
    successive_rank_partition_size,
    standard_macdonald_filling,
    rectangle_shape,
    staircase_shape,
    threshold_up_degrees,
    unit_interval_graph_permutation,
)
from qtbench.evaluation.runner import (
    _load_json_document,
    _load_public_polynomials,
    _load_public_unrefined_marginal,
    _normalize_composition,
    evaluate_ddyck_polynomial_checks,
    evaluate_asm_q_polynomial_checks,
    evaluate_gpf_polynomial_checks,
    evaluate_lgpf_polynomial_checks,
    evaluate_rtt_polynomial_checks,
    evaluate_tgt_polynomial_checks,
    evaluate_involution_polynomial_checks,
    evaluate_kreweras_polynomial_checks,
    evaluate_promotion_polynomial_checks,
    evaluate_qgamma_polynomial_checks,
    evaluate_kostka_polynomial_checks,
    evaluate_llt_polynomial_checks,
    evaluate_lpp_polynomial_checks,
    evaluate_mjack_polynomial_checks,
    evaluate_lrp_polynomial_checks,
    evaluate_mld_polynomial_checks,
    evaluate_public_polynomial_checks,
    evaluate_tamari_polynomial_checks,
    evaluate_ttree_polynomial_checks,
    evaluate_type_b_polynomial_checks,
    evaluate_uig_polynomial_checks,
)


class GateError(ValueError):
    """A static admission check (capability screen or source economy) failed."""


class ResourceGateError(RuntimeError):
    """A dynamic admission check (resource or identity gate) failed."""


CHECKER_VERSION = 18


@dataclass(frozen=True)
class SourceLimits:
    max_bytes: int = 8_192
    max_lines: int = 160
    max_tokens: int = 1_500
    max_ast_nodes: int = 2_000
    max_literal_bytes: int = 256


@dataclass(frozen=True)
class ResourceReport:
    elapsed_seconds: float
    peak_python_bytes: int
    results: tuple[Any, ...]


@dataclass(frozen=True)
class DeterminismReport:
    checked_objects: int
    replayed_calls: int
    fresh_namespaces: int
    replay_seed: int | None = None


@dataclass(frozen=True)
class IdentityReport:
    elapsed_seconds: float
    peak_python_bytes: int
    checked_paths: int


# ---------------------------------------------------------------------------
# Capability safety
# ---------------------------------------------------------------------------

_UNSAFE_NODES = (
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Import,
    ast.ImportFrom,
    # An assignment expression inside a comprehension, and a `match` capture
    # pattern, both bind in the enclosing scope, so `_module_bound_names` cannot
    # see them without tracking each spelling. Neither is needed to express a
    # statistic, so the construct is rejected instead.
    ast.Match,
    ast.NamedExpr,
)

_BANNED_NAMES = {
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "help",
    "input",
    "locals",
    "memoryview",
    "object",
    "open",
    "setattr",
    "super",
    "type",
    "vars",
}

_BANNED_ATTRIBUTES = {
    # Frame- and code-bearing attributes of generators, coroutines, and
    # tracebacks. The code objects are inert without `exec` or `types`, which
    # the builtin whitelist withholds, but they are the same reflective surface
    # as the frames and are excluded on the same grounds.
    "ag_code",
    "ag_frame",
    "cr_code",
    "cr_frame",
    "f_back",
    "f_builtins",
    "f_code",
    "f_globals",
    "f_locals",
    "format",
    "format_map",
    "gi_code",
    "gi_frame",
    "tb_frame",
    "tb_next",
}


def split_head(sequence):
    if not sequence:
        raise ValueError("split_head requires a nonempty sequence")
    return sequence[0], sequence[1:]


_SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "first_return": first_return,
    "frozenset": frozenset,
    "int": int,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "range": range,
    "reversed": reversed,
    "RuntimeError": RuntimeError,
    "set": set,
    "sorted": sorted,
    "split_head": split_head,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "ValueError": ValueError,
    "zip": zip,
}

_ALLOWED_CALLS = frozenset(_SAFE_BUILTINS)


def source_sha256(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


class _ExecutionSafetyChecker(ast.NodeVisitor):
    """Reject capability escapes without judging the algorithm."""

    def __init__(self, defined_functions: set[str]) -> None:
        self.defined_functions = defined_functions

    @staticmethod
    def fail(node: ast.AST, message: str) -> None:
        raise GateError(f"capability screen:{getattr(node, 'lineno', '?')}: {message}")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.decorator_list:
            self.fail(node, "decorators are not allowed")
        self.check_signature(node)
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        # A lambda is the other way to bind a callable, and
        # `load_restricted_functions` exposes one exactly like a `def`. Without
        # this the signature rule would hold for one definition form only.
        self.check_signature(node)
        self.generic_visit(node)

    def check_signature(self, node: ast.FunctionDef | ast.Lambda) -> None:
        if (
            node.args.defaults
            or node.args.kw_defaults
            or node.args.vararg is not None
            or node.args.kwarg is not None
            or node.args.kwonlyargs
            or node.args.posonlyargs
        ):
            self.fail(node, "default, keyword-only, and variadic arguments are not allowed")

    def visit_Name(self, node: ast.Name) -> None:
        # Dunder names (``__builtins__``, ``__import__``, ...) are the dangerous
        # ones; a single-underscore local such as ``for _ in range(n)`` is fine.
        if node.id.startswith("__") or node.id in _BANNED_NAMES:
            self.fail(node, f"name {node.id!r} is not allowed")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Writing an attribute is never part of computing a statistic, and it is
        # the one way a submission can reach state that outlives its namespace:
        # the injected helpers are module-level objects shared by every
        # namespace in the process, so `helper.stash = ...` would survive the
        # fresh-namespace replay that referential transparency depends on. The
        # same rule stops a submission mutating the trusted object it is given.
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.fail(node, f"assigning to attribute {node.attr!r} is not allowed")
        if node.attr.startswith("_") or node.attr in _BANNED_ATTRIBUTES:
            self.fail(node, f"attribute {node.attr!r} is not allowed")
        self.visit(node.value)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id not in self.defined_functions | _ALLOWED_CALLS:
                self.fail(node, f"call to {node.func.id!r} is not available")
        elif not isinstance(node.func, ast.Attribute):
            self.fail(node, "dynamic calls are not allowed")
        self.generic_visit(node)


def _module_bound_names(tree: ast.Module) -> set[str]:
    """Return the names a submission binds in its own module namespace.

    ``load_restricted_functions`` hands the evaluator whatever callables that
    namespace holds, so a binding here is what can take a trusted builtin's
    name. This reads ``def`` names together with every ``Store`` target left at
    module scope -- plain, annotated, augmented, unpacked, ``for`` and ``with``
    -- plus the ``global`` declarations that reach back out of a nested scope.
    Function and comprehension bodies keep their own scope and are skipped, so
    an ordinary local ``total = 0`` is untouched.

    ``except E as name`` is deliberately skipped: Python deletes that name when
    the handler exits, so it never reaches the namespace.

    Everything else this does not read is a construct ``_UNSAFE_NODES`` already
    rejects, and the two are only correct together. ``import``, ``class``,
    ``async def``, ``match`` captures and assignment expressions each bind a
    module name that no branch below would see, so relaxing that tuple without
    revisiting this function would reopen the shadowing gap.
    """

    scopes = (
        ast.FunctionDef,
        ast.Lambda,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
    )
    bound: set[str] = set()
    pending = list(ast.iter_child_nodes(tree))
    while pending:
        node = pending.pop()
        if isinstance(node, ast.Global):
            bound.update(node.names)
            continue
        if isinstance(node, scopes):
            if isinstance(node, ast.FunctionDef):
                # The definition binds its own name out here; its body does not.
                bound.add(node.name)
            pending.extend(
                inner for inner in ast.walk(node) if isinstance(inner, ast.Global)
            )
            continue
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
        pending.extend(ast.iter_child_nodes(node))
    return bound


def check_capability_screen(source: str) -> tuple[str, ...]:
    """Screen a submission for capability escapes and return its function names."""

    encoded = source.encode("utf-8")
    if len(encoded) > 1_000_000:
        raise GateError("capability screen: source exceeds the 1 MB hard limit")
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise GateError(f"invalid Python: {error}") from error
    nodes = list(ast.walk(tree))
    if len(nodes) > 100_000:
        raise GateError("capability screen: source AST exceeds the hard limit")
    for node in nodes:
        if isinstance(node, _UNSAFE_NODES):
            raise GateError(
                f"capability screen: {type(node).__name__} is not allowed "
                f"at line {getattr(node, 'lineno', '?')}"
            )

    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    names = {node.name for node in functions}
    # Any module binding can shadow a whitelisted builtin, and `visit_Call`
    # admits a call to a whitelisted name, so the submission's own `sum(...)`
    # would reach it. Only a top-level `def` may be called by name, so `names`
    # below stays as it was.
    reserved = _module_bound_names(tree) & _ALLOWED_CALLS
    if reserved:
        raise GateError(f"submitted functions shadow trusted names: {sorted(reserved)}")
    checker = _ExecutionSafetyChecker(names)
    checker.visit(tree)
    return tuple(function.name for function in functions)


# ---------------------------------------------------------------------------
# Source economy
# ---------------------------------------------------------------------------


def _significant_token_count(source: str) -> int:
    ignored = {
        tokenize.COMMENT,
        tokenize.DEDENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
        tokenize.INDENT,
        tokenize.NEWLINE,
        tokenize.NL,
    }
    return sum(
        token.type not in ignored
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
    )


def _literal_size(value: object) -> int:
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    if isinstance(value, bytes):
        return len(value)
    if isinstance(value, bool) or value is None:
        return 1
    if isinstance(value, int):
        return max(1, (value.bit_length() + 7) // 8)
    if isinstance(value, float):
        return 8
    if isinstance(value, complex):
        return 16
    return 0


def check_source_economy(source: str, *, limits: SourceLimits = SourceLimits()) -> None:
    """Reject submissions large enough to embed an answer table."""

    encoded = source.encode("utf-8")
    if len(encoded) > limits.max_bytes:
        raise GateError(f"source has {len(encoded)} bytes, limit is {limits.max_bytes}")
    line_count = len(source.splitlines())
    if line_count > limits.max_lines:
        raise GateError(f"source has {line_count} lines, limit is {limits.max_lines}")
    token_count = _significant_token_count(source)
    if token_count > limits.max_tokens:
        raise GateError(f"source has {token_count} tokens, limit is {limits.max_tokens}")

    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise GateError(f"invalid Python: {error}") from error
    nodes = list(ast.walk(tree))
    if len(nodes) > limits.max_ast_nodes:
        raise GateError(f"source has {len(nodes)} AST nodes, limit is {limits.max_ast_nodes}")
    literal_bytes = sum(
        _literal_size(node.value) for node in nodes if isinstance(node, ast.Constant)
    )
    if literal_bytes > limits.max_literal_bytes:
        raise GateError(
            f"source contains {literal_bytes} literal bytes, limit is {limits.max_literal_bytes}"
        )


# ---------------------------------------------------------------------------
# Sandboxed loading and process limits
# ---------------------------------------------------------------------------


def load_restricted_functions(source: str) -> dict[str, Any]:
    environment: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "first_return": first_return,
        "split_head": split_head,
    }
    exec(compile(source, "<submission>", "exec"), environment, environment)
    return {
        name: value
        for name, value in environment.items()
        if callable(value) and name not in {"first_return", "split_head"}
    }


def _install_process_limits(*, timeout_seconds: float, max_process_bytes: int) -> None:
    # In-process CPU and address-space limits are only reliable on Linux; macOS
    # delivers RLIMIT_CPU spuriously. On every platform the real timeout is the
    # parent's wall-clock deadline in _wait_for_child, backed by RSS polling and
    # the tracemalloc peak, so skipping these limits off Linux stays sound.
    if not sys.platform.startswith("linux"):
        return
    try:
        import resource
    except ImportError:
        return

    cpu_seconds = max(1, int(timeout_seconds) + 1)
    limits = [
        (getattr(resource, "RLIMIT_CPU", None), (cpu_seconds, cpu_seconds + 1)),
        (getattr(resource, "RLIMIT_CORE", None), (0, 0)),
    ]
    if hasattr(resource, "RLIMIT_AS"):
        limits.append((resource.RLIMIT_AS, (max_process_bytes, max_process_bytes)))
    for limit, values in limits:
        if limit is None:
            continue
        try:
            resource.setrlimit(limit, values)
        except (OSError, ValueError):
            pass


def _deny_submission_audit_events(
    event: str,
    arguments: tuple[Any, ...],
    *,
    allowed_read_paths: tuple[Path, ...] = (),
) -> None:
    denied = (
        "ctypes.",
        "import",
        "os.",
        "socket.",
        "subprocess.",
    )
    if event == "open":
        path = arguments[0] if arguments else None
        mode = arguments[1] if len(arguments) > 1 else None
        if isinstance(path, (str, bytes, os.PathLike)) and isinstance(mode, str):
            resolved = Path(path).resolve()
            read_only = not any(character in mode for character in "wax+")
            if read_only and any(
                resolved == allowed or allowed in resolved.parents
                for allowed in allowed_read_paths
            ):
                return
        raise PermissionError(f"submission audit event is not allowed: {event}")
    if event.startswith(denied):
        raise PermissionError(f"submission audit event is not allowed: {event}")


def _install_submission_audit_hook(*, problem_dir=None) -> None:
    allowed: tuple[Path, ...] = ()
    if problem_dir is not None:
        problem_path = Path(problem_dir).resolve()
        allowed = (problem_path / "metadata.json", problem_path / "data")

    def audit(event: str, arguments: tuple[Any, ...]) -> None:
        _deny_submission_audit_events(event, arguments, allowed_read_paths=allowed)

    sys.addaudithook(audit)


def _multiprocessing_context():
    methods = multiprocessing.get_all_start_methods()
    return multiprocessing.get_context("spawn" if "spawn" in methods else methods[0])


def _validate_timeout_seconds(timeout_seconds: float) -> None:
    valid = False
    if type(timeout_seconds) in (int, float):
        try:
            valid = timeout_seconds > 0 and math.isfinite(timeout_seconds)
        except OverflowError:
            pass
    if not valid:
        raise ValueError("timeout_seconds must be finite and positive")


def _validate_byte_limit(value: int, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive integer")


def _windows_resident_bytes(pid: int) -> int:
    """Return a process's Windows working-set size through the native API."""

    import ctypes
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("page_fault_count", wintypes.DWORD),
            ("peak_working_set_size", ctypes.c_size_t),
            ("working_set_size", ctypes.c_size_t),
            ("quota_peak_paged_pool_usage", ctypes.c_size_t),
            ("quota_paged_pool_usage", ctypes.c_size_t),
            ("quota_peak_nonpaged_pool_usage", ctypes.c_size_t),
            ("quota_nonpaged_pool_usage", ctypes.c_size_t),
            ("pagefile_usage", ctypes.c_size_t),
            ("peak_pagefile_usage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    )
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

    # GetProcessMemoryInfo requires a query right together with VM_READ.
    process_query_limited_information = 0x1000
    process_vm_read = 0x0010
    handle = kernel32.OpenProcess(
        process_query_limited_information | process_vm_read,
        False,
        pid,
    )
    if not handle:
        raise OSError(ctypes.get_last_error(), f"OpenProcess failed for pid {pid}")
    try:
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            raise OSError(
                ctypes.get_last_error(),
                f"GetProcessMemoryInfo failed for pid {pid}",
            )
        return int(counters.working_set_size)
    finally:
        kernel32.CloseHandle(handle)


_PS_RSS_TIMEOUT_SECONDS = 0.5


def _resident_bytes(
    pid: int, *, timeout_seconds: float = _PS_RSS_TIMEOUT_SECONDS
) -> int:
    if sys.platform == "win32":
        return _windows_resident_bytes(pid)
    statm = Path(f"/proc/{pid}/statm")
    if statm.exists():
        fields = statm.read_text(encoding="ascii").split()
        return int(fields[1]) * os.sysconf("SC_PAGE_SIZE")
    ps = shutil.which("ps", path=os.defpath)
    if ps is None:
        raise OSError("could not measure RSS: system ps is unavailable")
    try:
        result = subprocess.run(
            [ps, "-o", "rss=", "-p", str(pid)],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        raise OSError(f"ps timed out while measuring RSS for pid {pid}") from error
    except OSError as error:
        raise OSError(f"could not run ps to measure RSS for pid {pid}") from error
    if result.returncode != 0:
        raise OSError(f"ps could not measure RSS for pid {pid}")
    value = result.stdout.strip()
    if not value:
        raise OSError(f"ps returned no RSS for pid {pid}")
    try:
        return int(value) * 1024
    except ValueError as error:
        raise OSError(f"ps returned an invalid RSS for pid {pid}") from error


def _is_cpu_limit_exit(exitcode: int | None) -> bool:
    sigxcpu = getattr(signal, "SIGXCPU", None)
    return sigxcpu is not None and exitcode == -sigxcpu


def _observed_worker_exitcode(process) -> int | None:
    """Return an already-available worker exit code without waiting."""

    try:
        process.join(timeout=0.0)
    except Exception:
        pass
    try:
        return process.exitcode
    except Exception:
        return None


_PROCESS_CLEANUP_GRACE_SECONDS = 0.5
_MAX_IPC_BYTES = 8_000_000


@dataclass(frozen=True)
class _AggregateProcessBudget:
    max_parent_process_bytes: int
    max_aggregate_process_bytes: int


_AGGREGATE_PROCESS_BUDGET: ContextVar[_AggregateProcessBudget | None] = ContextVar(
    "qtbench_aggregate_process_budget", default=None
)


@contextmanager
def _aggregate_process_budget(
    *, max_parent_process_bytes: int, max_aggregate_process_bytes: int
) -> Iterator[None]:
    """Apply an aggregate process budget to isolated workers in this context."""

    _validate_byte_limit(max_parent_process_bytes, "max_parent_process_bytes")
    _validate_byte_limit(max_aggregate_process_bytes, "max_aggregate_process_bytes")
    if max_parent_process_bytes > max_aggregate_process_bytes:
        raise ValueError(
            "max_parent_process_bytes must not exceed "
            "max_aggregate_process_bytes"
        )
    token = _AGGREGATE_PROCESS_BUDGET.set(
        _AggregateProcessBudget(
            max_parent_process_bytes=max_parent_process_bytes,
            max_aggregate_process_bytes=max_aggregate_process_bytes,
        )
    )
    try:
        yield
    finally:
        _AGGREGATE_PROCESS_BUDGET.reset(token)


def _preflight_aggregate_process_budget(
    *, max_process_bytes: int, label: str
) -> _AggregateProcessBudget | None:
    budget = _AGGREGATE_PROCESS_BUDGET.get()
    if budget is None:
        return None
    if (
        max_process_bytes + budget.max_parent_process_bytes
        > budget.max_aggregate_process_bytes
    ):
        raise ValueError(
            "max_process_bytes plus max_parent_process_bytes must not exceed "
            "max_aggregate_process_bytes"
        )
    try:
        parent_resident = _resident_bytes(os.getpid())
    except OSError as error:
        raise ResourceGateError(
            f"{label} could not measure evaluator parent memory"
        ) from error
    if parent_resident + _MAX_IPC_BYTES > budget.max_parent_process_bytes:
        raise ResourceGateError(
            f"{label} evaluator parent uses {parent_resident} process bytes; "
            f"with {_MAX_IPC_BYTES} bytes of IPC headroom it exceeds the "
            f"{budget.max_parent_process_bytes} byte parent reserve"
        )
    return budget


def _cleanup_worker_process(process, *, started: bool) -> bool:
    """Best-effort bounded cleanup; return whether the worker is known stopped."""

    def join(timeout: float) -> None:
        try:
            process.join(timeout=timeout)
        except Exception:
            pass

    def is_alive() -> bool | None:
        try:
            return process.is_alive()
        except Exception:
            return None

    if started:
        join(0.0)
        alive = is_alive()
        if alive is not False:
            try:
                process.terminate()
            except Exception:
                pass
            join(_PROCESS_CLEANUP_GRACE_SECONDS)
            alive = is_alive()
        if alive is not False:
            try:
                process.kill()
            except Exception:
                pass
            join(_PROCESS_CLEANUP_GRACE_SECONDS)
            alive = is_alive()
    else:
        alive = False

    if alive is False:
        try:
            process.close()
        except Exception:
            pass
    return alive is False


def _wait_for_child(
    parent,
    process,
    *,
    timeout_seconds: float,
    max_process_bytes: int,
    label: str,
    deadline: float | None = None,
    aggregate_budget: _AggregateProcessBudget | None = None,
):
    if deadline is None:
        deadline = time.monotonic() + timeout_seconds

    def check_process_memory(
        *, allow_exited_worker: bool, reserve_ipc_headroom: bool
    ) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ResourceGateError(
                f"{label} exceeded {timeout_seconds:.3f} seconds"
            )
        measurement_count = 2 if aggregate_budget is not None else 1
        measurement_timeout = min(
            _PS_RSS_TIMEOUT_SECONDS, remaining / measurement_count
        )
        try:
            worker_resident = _resident_bytes(
                process.pid,
                timeout_seconds=measurement_timeout,
            )
        except OSError as error:
            if allow_exited_worker and _observed_worker_exitcode(process) is not None:
                worker_resident = 0
            else:
                raise ResourceGateError(
                    f"{label} could not measure worker memory"
                ) from error
        if worker_resident > max_process_bytes:
            raise ResourceGateError(
                f"{label} used {worker_resident} process bytes, "
                f"limit is {max_process_bytes}"
            )
        if aggregate_budget is None:
            return
        try:
            parent_resident = _resident_bytes(
                os.getpid(),
                timeout_seconds=measurement_timeout,
            )
        except OSError as error:
            raise ResourceGateError(
                f"{label} could not measure evaluator parent memory"
            ) from error
        reserved_parent = parent_resident + (
            _MAX_IPC_BYTES if reserve_ipc_headroom else 0
        )
        if reserved_parent > aggregate_budget.max_parent_process_bytes:
            headroom = " plus IPC headroom" if reserve_ipc_headroom else ""
            raise ResourceGateError(
                f"{label} used {parent_resident} evaluator parent process bytes"
                f"{headroom}, "
                f"limit is {aggregate_budget.max_parent_process_bytes}"
            )
        aggregate_resident = worker_resident + reserved_parent
        if aggregate_resident > aggregate_budget.max_aggregate_process_bytes:
            raise ResourceGateError(
                f"{label} used {aggregate_resident} aggregate process bytes, "
                f"limit is {aggregate_budget.max_aggregate_process_bytes}"
            )

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ResourceGateError(f"{label} exceeded {timeout_seconds:.3f} seconds")
        ready = parent.poll(min(0.05, remaining))
        if aggregate_budget is not None:
            check_process_memory(
                allow_exited_worker=True,
                reserve_ipc_headroom=True,
            )
        if ready:
            try:
                encoded = parent.recv_bytes(_MAX_IPC_BYTES)
            except (EOFError, OSError) as error:
                exitcode = _observed_worker_exitcode(process)
                if _is_cpu_limit_exit(exitcode):
                    raise ResourceGateError(f"{label} exceeded its CPU limit") from error
                raise ResourceGateError(
                    f"{label} returned no valid result within the "
                    f"{_MAX_IPC_BYTES} byte IPC limit (exitcode {exitcode})"
                ) from error
            if aggregate_budget is not None:
                check_process_memory(
                    allow_exited_worker=True,
                    reserve_ipc_headroom=False,
                )
            return encoded
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ResourceGateError(
                f"{label} exceeded {timeout_seconds:.3f} seconds"
            )
        if aggregate_budget is None:
            check_process_memory(
                allow_exited_worker=False,
                reserve_ipc_headroom=False,
            )


def _run_isolated(target, args, *, timeout_seconds, max_process_bytes, label):
    _validate_timeout_seconds(timeout_seconds)
    _validate_byte_limit(max_process_bytes, "max_process_bytes")
    aggregate_budget = _preflight_aggregate_process_budget(
        max_process_bytes=max_process_bytes, label=label
    )
    context = _multiprocessing_context()
    parent, child = context.Pipe(duplex=False)
    process = None
    start_attempted = False
    deadline = time.monotonic() + timeout_seconds
    primary_error = None
    try:
        process = context.Process(target=target, args=(*args, child))
        # Set this before ``start`` so asynchronous failures cannot lose a child
        # that was launched but whose ``start`` call did not return normally.
        start_attempted = True
        process.start()
        child.close()
        try:
            encoded = _wait_for_child(
                parent,
                process,
                timeout_seconds=timeout_seconds,
                max_process_bytes=max_process_bytes,
                label=label,
                deadline=deadline,
                aggregate_budget=aggregate_budget,
            )
        except ResourceGateError as error:
            if _is_cpu_limit_exit(_observed_worker_exitcode(process)):
                raise ResourceGateError(f"{label} exceeded its CPU limit") from error
            raise
        process.join(timeout=max(0.0, deadline - time.monotonic()))
        if process.is_alive():
            raise ResourceGateError(f"{label} exceeded {timeout_seconds:.3f} seconds")
        exitcode = process.exitcode
        if _is_cpu_limit_exit(exitcode):
            raise ResourceGateError(f"{label} exceeded its CPU limit")
        if time.monotonic() > deadline:
            raise ResourceGateError(f"{label} exceeded {timeout_seconds:.3f} seconds")
        if exitcode != 0:
            raise ResourceGateError(
                f"{label} worker exited abnormally with exitcode {exitcode}"
            )
        try:
            payload = pickle.loads(encoded)
        except Exception as error:
            raise ResourceGateError(
                f"{label} returned no valid result within the "
                f"{_MAX_IPC_BYTES} byte IPC limit (exitcode {exitcode})"
            ) from error
        if time.monotonic() > deadline:
            raise ResourceGateError(f"{label} exceeded {timeout_seconds:.3f} seconds")
        if aggregate_budget is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ResourceGateError(
                    f"{label} exceeded {timeout_seconds:.3f} seconds"
                )
            try:
                parent_resident = _resident_bytes(
                    os.getpid(),
                    timeout_seconds=min(_PS_RSS_TIMEOUT_SECONDS, remaining),
                )
            except OSError as error:
                raise ResourceGateError(
                    f"{label} could not measure evaluator parent memory"
                ) from error
            if parent_resident > aggregate_budget.max_parent_process_bytes:
                raise ResourceGateError(
                    f"{label} used {parent_resident} evaluator parent process bytes "
                    f"after worker exit, limit is "
                    f"{aggregate_budget.max_parent_process_bytes}"
                )
            if time.monotonic() > deadline:
                raise ResourceGateError(
                    f"{label} exceeded {timeout_seconds:.3f} seconds"
                )
        return payload
    except BaseException as error:
        primary_error = error
        raise
    finally:
        # Gates can run many isolated workers in one evaluator invocation.
        # Close both pipe endpoints and the Process sentinel deterministically
        # instead of relying on implementation-specific garbage collection.
        for connection in (parent, child):
            try:
                connection.close()
            except Exception:
                pass
        cleanup_error = None
        cleanup_stopped = process is None
        if process is not None:
            try:
                cleanup_stopped = _cleanup_worker_process(
                    process, started=start_attempted
                )
            except Exception as error:
                cleanup_error = error
                cleanup_stopped = False
        if not cleanup_stopped:
            note = f"{label} worker cleanup could not confirm process exit"
            if cleanup_error is not None:
                note += f" ({type(cleanup_error).__name__})"
            if primary_error is None:
                raise ResourceGateError(note) from cleanup_error
            primary_error.add_note(note)


def _send_to_parent(connection, payload) -> None:
    """Serialize in the limited child and bound what the parent will receive."""

    encoded = pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)
    if len(encoded) > _MAX_IPC_BYTES:
        raise ResourceGateError(
            f"worker result exceeds the {_MAX_IPC_BYTES} byte IPC limit"
        )
    connection.send_bytes(encoded)


# ---------------------------------------------------------------------------
# Resource gate
# ---------------------------------------------------------------------------


def _resource_worker(source, calls, timeout_seconds, max_process_bytes, connection) -> None:
    try:
        _install_process_limits(
            timeout_seconds=timeout_seconds, max_process_bytes=max_process_bytes
        )
        _install_submission_audit_hook()
        tracemalloc.start()
        functions = load_restricted_functions(source)
        start = time.perf_counter()
        results = tuple(functions[name](*arguments) for name, arguments in calls)
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        _send_to_parent(connection, ("ok", elapsed, peak, results))
    except BaseException as error:  # noqa: BLE001 - reported to the parent
        _send_to_parent(connection, ("error", type(error).__name__, str(error)))
    finally:
        connection.close()


def run_resource_gate(
    source: str,
    calls: Sequence[tuple[str, tuple[Any, ...]]],
    *,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
) -> ResourceReport:
    _validate_byte_limit(max_python_bytes, "max_python_bytes")
    payload = _run_isolated(
        _resource_worker,
        (source, calls, timeout_seconds, max_process_bytes),
        timeout_seconds=timeout_seconds,
        max_process_bytes=max_process_bytes,
        label="submission",
    )
    if payload[0] != "ok":
        raise ResourceGateError(f"submission raised {payload[1]}: {payload[2]}")
    _, elapsed, peak, results = payload
    if peak > max_python_bytes:
        raise ResourceGateError(
            f"submission allocated {peak} Python bytes, limit is {max_python_bytes}"
        )
    return ResourceReport(elapsed_seconds=elapsed, peak_python_bytes=peak, results=results)


def _structural_size(value: Any) -> int | None:
    """Return the structural size used to scale adversarial probes."""

    if isinstance(value, AlternatingSignMatrix):
        return alternating_sign_matrix_size(value)
    if isinstance(value, ConnectedGraph):
        return connected_graph_size(value)
    if isinstance(value, PartitionMatrixInversion):
        return partition_matrix_inversion_size(value)
    if isinstance(value, ShiftedSetValuedTableau):
        return shifted_tableau_size(value)
    if isinstance(value, SuccessiveRankPartition):
        return successive_rank_partition_size(value)
    if isinstance(value, (NoncrossingPartition, TypeBCatalanPath)):
        return value.n
    if isinstance(value, LabelledParallelogramPolyomino):
        return value.m + value.n
    if isinstance(value, DecoratedLabelledDyckPath):
        return value.n
    if isinstance(value, LabelledRectangularPath):
        return value.width + value.height
    if isinstance(value, MultiLabelledDyckPath):
        return value.n
    if isinstance(value, ZeroRootedTieredTree):
        return value.n
    if isinstance(value, RootedTieredTree):
        return value.n
    if isinstance(value, ThresholdSpanningTree):
        return value.n
    if isinstance(value, GammaParkingSelection):
        return value.size
    if isinstance(value, TamariParkingPair):
        return value.n
    if isinstance(value, UnitIntervalGraphPermutation):
        return value.n
    if isinstance(value, UnitIntervalGraphTableau):
        return value.n
    if isinstance(value, KostkaStandardTableau):
        return value.n
    if isinstance(value, Involution):
        return value.n
    if isinstance(value, JackMatching):
        return value.n
    if isinstance(value, GammaPermutation):
        return value.n
    if isinstance(value, PromotionTableau):
        return value.n
    if isinstance(value, StandardMacdonaldFilling):
        return value.n
    if isinstance(value, ParkingFunction):
        return value.n
    if isinstance(value, str):
        return len(value) // 2
    return None


# ---------------------------------------------------------------------------
# Adversarial probes
# ---------------------------------------------------------------------------

_RUN_SEED_ENV = "QTBENCH_RUN_SEED"
_REPLAY_SEED_ENV = "QTBENCH_REPLAY_SEED"


def _configured_run_seed() -> int | None:
    value = os.environ.get(_RUN_SEED_ENV)
    return int(value) if value is not None else None


def _derived_run_seed(label: str) -> int:
    base = _configured_run_seed()
    if base is None:
        return secrets.randbits(128)
    digest = hashlib.sha256(f"{base}:{label}".encode("ascii")).digest()
    return int.from_bytes(digest[:16], "big")


def _probe_random(seed: int | None) -> random.Random:
    return random.Random(_derived_run_seed("adversarial-probes") if seed is None else seed)


def _rainbow_partition(n: int) -> NoncrossingPartition:
    blocks = [(value, n + 1 - value) for value in range(1, n // 2 + 1)]
    if n % 2:
        blocks.append((n // 2 + 1,))
    return NoncrossingPartition(blocks, n=n, validate=False)


def _random_interval_partition(n: int, generator: random.Random) -> NoncrossingPartition:
    blocks: list[tuple[int, ...]] = []
    start = 1
    while start <= n:
        length = generator.randint(1, min(11, n - start + 1))
        blocks.append(tuple(range(start, start + length)))
        start += length
    return NoncrossingPartition(blocks, n=n, validate=False)


def _random_nested_partition(n: int, generator: random.Random) -> NoncrossingPartition:
    blocks: list[tuple[int, ...]] = []
    start = 1
    while start <= n:
        length = generator.randint(1, min(17, n - start + 1))
        end = start + length - 1
        left = start
        right = end
        while left < right:
            blocks.append((left, right))
            left += 1
            right -= 1
        if left == right:
            blocks.append((left,))
        start = end + 1
    return NoncrossingPartition(blocks, n=n, validate=False)


def adversarial_noncrossing_partitions(
    n: int, *, seed: int | None = None
) -> list[NoncrossingPartition]:
    if n < 1:
        raise ValueError("noncrossing probe size must be positive")
    generator = _probe_random(seed)
    adjacent = [(value, value + 1) for value in range(1, n, 2)]
    if n % 2:
        adjacent.append((n,))
    opened = n // 3
    maximum = 2 * opened + 1
    delayed = [tuple([*range(1, opened + 1), maximum])]
    delayed.extend((value,) for value in range(opened + 1, maximum))
    delayed.extend((value,) for value in range(maximum + 1, n + 1))
    return [
        NoncrossingPartition([(value,) for value in range(1, n + 1)], n=n, validate=False),
        NoncrossingPartition([tuple(range(1, n + 1))], n=n, validate=False),
        NoncrossingPartition(adjacent, n=n, validate=False),
        _rainbow_partition(n),
        NoncrossingPartition(delayed, n=n, validate=False),
        _random_interval_partition(n, generator),
        _random_nested_partition(n, generator),
    ]


def adversarial_noncrossing_probes(
    n: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (partition,))
        for partition in adversarial_noncrossing_partitions(n, seed=seed)
    ]


def _random_dyck_path(n: int, generator: random.Random) -> str:
    north = 0
    east = 0
    result: list[str] = []
    while east < n:
        if north == n:
            result.append("E")
            east += 1
        elif north == east or generator.getrandbits(1):
            result.append("N")
            north += 1
        else:
            result.append("E")
            east += 1
    return "".join(result)


def adversarial_dyck_paths(n: int, *, seed: int | None = None) -> list[str]:
    if n < 1:
        raise ValueError("Dyck probe size must be positive")
    generator = _probe_random(seed)
    return [
        "NE" * n,
        "N" * n + "E" * n,
        "NNEE" * (n // 2) + ("NE" if n % 2 else ""),
        _random_dyck_path(n, generator),
        _random_dyck_path(n, generator),
    ]


def adversarial_dyck_probes(
    n: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        (function_name, (path,))
        for path in adversarial_dyck_paths(n, seed=seed)
        for function_name in ("forward", "inverse")
    ]


def _full_polyomino(m: int, n: int) -> str:
    return f"{'N' * n}{'E' * m}|{'E' * m}{'N' * n}"


def _random_polyomino(m: int, n: int, generator: random.Random) -> str:
    # A random valid area word: start at rank 0, then each rank lies in
    # [1, previous + 1] with parity fixing barred (even) vs unbarred (odd). The
    # rank-1 (unbarred) and rank-2 (barred) options are always available, so the
    # remaining unbarred/barred budget can always be spent -- no dead ends.
    ranks = [0]
    unbarred_left = m
    barred_left = n - 1
    previous = 0
    for _ in range(m + n - 1):
        choices = [
            rank
            for rank in range(1, previous + 2)
            if (rank % 2 == 1 and unbarred_left) or (rank % 2 == 0 and barred_left)
        ]
        rank = generator.choice(choices)
        ranks.append(rank)
        if rank % 2 == 1:
            unbarred_left -= 1
        else:
            barred_left -= 1
        previous = rank
    return polyomino_from_ranks(ranks)


def _polyomino_boxes(size: int) -> list[tuple[int, int]]:
    if size < 2:
        raise ValueError("polyomino probe size must be at least 2")
    boxes = {
        (size // 2, size - size // 2),
        (max(1, size // 4), size - max(1, size // 4)),
        (1, size - 1),
    }
    return sorted(boxes)


def adversarial_parallelogram_polyominoes(size: int, *, seed: int | None = None) -> list[str]:
    """Large valid polyominoes across a few bounding boxes of semiperimeter ``size``."""
    generator = _probe_random(seed)
    polyominoes: list[str] = []
    for m, n in _polyomino_boxes(size):
        polyominoes.append(_full_polyomino(m, n))
        polyominoes.append(_random_polyomino(m, n, generator))
    return polyominoes


def adversarial_polyomino_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        (function_name, (polyomino,))
        for polyomino in adversarial_parallelogram_polyominoes(size, seed=seed)
        for function_name in ("forward", "inverse")
    ]


def adversarial_labelled_polyominoes(
    size: int, *, seed: int | None = None
) -> list[LabelledParallelogramPolyomino]:
    """Large standardly labelled polyominoes across a few bounding boxes.

    Each shape is given its lexicographically-first standard labelling, so the
    probe is a single valid object without enumerating the (exponential) fiber.
    """
    generator = _probe_random(seed)
    objects: list[LabelledParallelogramPolyomino] = []
    for m, n in _polyomino_boxes(size):
        for shape in (_full_polyomino(m, n), _random_polyomino(m, n, generator)):
            upper, lower = shape.split("|")
            objects.append(canonical_standard_labelling(upper, lower))
    return objects


def adversarial_lpp_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (polyomino,))
        for polyomino in adversarial_labelled_polyominoes(size, seed=seed)
    ]


def adversarial_decorated_labelled_dyck_paths(
    size: int, *, seed: int | None = None
) -> list[DecoratedLabelledDyckPath]:
    """Large standardly labelled doubly decorated Dyck paths of size ``size``.

    Each shape gets the lexicographically-first standard labelling and then a
    deterministic set of rise/valley decorations, so every probe is a single
    valid object without enumerating the (exponential) fiber. A few shapes and
    decoration counts (all rises, all valleys, a mix) exercise the statistic.
    """
    if size < 1:
        raise ValueError("decorated Dyck probe size must be positive")
    generator = _probe_random(seed)
    objects: list[DecoratedLabelledDyckPath] = []
    for shape in adversarial_dyck_paths(size, seed=generator.getrandbits(64)):
        base = canonical_decorated_labelled_dyck_path(shape, 0, 0)
        rises = len(base.rises)
        valleys = len(base.contractible_valleys)
        for k, l in {(0, 0), (rises, 0), (0, valleys), (rises // 2, valleys // 2)}:
            objects.append(canonical_decorated_labelled_dyck_path(shape, k, l))
    return objects


def adversarial_ddyck_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (path,))
        for path in adversarial_decorated_labelled_dyck_paths(size, seed=seed)
    ]


def _random_rectangular_path(width: int, height: int, generator: random.Random) -> str:
    """A random ``width x height`` North/East word ending with an East step.

    The first two steps are North so the shape always has a rise to decorate.
    """
    steps = ["N"] * (height - 2) + ["E"] * (width - 1)
    generator.shuffle(steps)
    return "NN" + "".join(steps) + "E"


def adversarial_labelled_rectangular_paths(
    size: int, *, seed: int | None = None
) -> list[LabelledRectangularPath]:
    """Large standardly labelled decorated rectangular paths of semiperimeter ``size``.

    Each shape gets the canonical labelling and decoration of
    ``canonical_labelled_rectangular_path``, so every probe is a single valid
    object without enumerating the (exponential) fiber. A few boxes, decoration
    counts and shapes (the highest path, a random path) exercise the statistic;
    the decoration count is clamped to what the shape and box actually admit.
    """
    if size < 4:
        raise ValueError("rectangular path probe size must be at least 4")
    generator = _probe_random(seed)
    objects: list[LabelledRectangularPath] = []
    for height in (size // 2, size // 4):
        width = size - height
        if width < 2 or height < 2:
            continue
        for shape in (
            "N" * height + "E" * width,
            _random_rectangular_path(width, height, generator),
        ):
            rises = sum(
                1
                for i in range(1, len(shape))
                if shape[i] == "N" and shape[i - 1] == "N"
            )
            for wanted in (1, size // 8):
                k = max(1, min(wanted, rises, width - 1, height - 1))
                objects.append(canonical_labelled_rectangular_path(shape, k))
    return objects


def adversarial_lrp_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (path,))
        for path in adversarial_labelled_rectangular_paths(size, seed=seed)
    ]


def _random_rectangular_dyck_path(n: int, k: int, generator: random.Random) -> str:
    """A random ``kn x n`` Dyck path: ``col(i)`` weakly increasing with ``col(i) <= k(i-1)``."""
    columns = []
    previous = 0
    for i in range(1, n + 1):
        previous = generator.randint(previous, k * (i - 1))
        columns.append(previous)
    pieces = []
    seen = 0
    for column in columns:
        pieces.append("E" * (column - seen))
        pieces.append("N")
        seen = column
    pieces.append("E" * (k * n - seen))
    return "".join(pieces)


def adversarial_multi_labelled_dyck_paths(
    size: int, *, seed: int | None = None
) -> list[MultiLabelledDyckPath]:
    """Large standard multi-labelled ``k^n`` Dyck paths with ``n = size``.

    Each shape gets the canonical multi-labelling of
    ``canonical_multi_labelled_dyck_path``, so every probe is a single valid
    object without enumerating the (exponential) fiber. A few label counts and
    shapes (the highest-area path, the zero-area staircase, a random path)
    exercise the statistic.
    """
    if size < 1:
        raise ValueError("multi-labelled Dyck probe size must be positive")
    generator = _probe_random(seed)
    objects: list[MultiLabelledDyckPath] = []
    for k in (1, 2, 3):
        shapes = [
            "N" * size + "E" * (k * size),          # maximal area
            ("N" + "E" * k) * size,                 # zero-area staircase
            _random_rectangular_dyck_path(size, k, generator),
        ]
        for shape in shapes:
            objects.append(canonical_multi_labelled_dyck_path(shape, k))
    return objects


def adversarial_mld_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (path,))
        for path in adversarial_multi_labelled_dyck_paths(size, seed=seed)
    ]


def adversarial_tamari_parking_pairs(
    size: int, *, seed: int | None = None
) -> list[TamariParkingPair]:
    """Large pairs ``(f, alpha)`` of size ``size``, valid by construction.

    The first eight take ``alpha`` at an extreme -- the shape ``beta(f)`` or the
    Tamari minimum -- where the chain length is a closed form. A statistic that
    only has to be cheap there could still call ``chain()`` internally and be
    pathological in general, so the probes also include intermediate ``alpha``
    reached by walking a Tamari chain up from the minimum; those intervals have no
    closed form. A few parking functions (the all-zero one, the staircase, a
    random one) exercise the statistic.
    """
    if size < 1:
        raise ValueError("Tamari parking probe size must be positive")
    generator = _probe_random(seed)
    staircase = tuple(range(size))
    shuffled = list(staircase)
    generator.shuffle(shuffled)
    parking_functions = [
        tuple([0] * size),
        staircase,
        tuple(shuffled),
        tuple(min(i, generator.randrange(size)) for i in range(size)),
    ]
    extremes = [
        canonical_tamari_parking_pair(f, at_minimum=at_minimum)
        for f in parking_functions
        for at_minimum in (False, True)
    ]
    # 48 steps put the two interior alphas roughly 16 and 32 covers below beta,
    # which already makes the longest-chain search intractable from size 32 up,
    # while the walk itself stays linear in the number of steps
    choices = [generator.randrange(1 << 30) for _ in range(48)]
    return [*extremes, *intermediate_tamari_parking_pairs(size, choices)]


def adversarial_tamari_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (pair,))
        for pair in adversarial_tamari_parking_pairs(size, seed=seed)
    ]


def adversarial_zero_rooted_tiered_trees(
    size: int, *, seed: int | None = None
) -> list[ZeroRootedTieredTree]:
    """Large standard zero-rooted tiered trees on ``size`` non-root vertices.

    Each tier vector gets the canonical root-star from
    ``canonical_zero_rooted_tiered_tree``, so every probe is a single valid object
    without enumerating the (exponential) fiber. A few tier shapes (one tier, two
    tiers, fully tiered) plus a random compatible tree exercise the statistic.
    """
    generator = _probe_random(seed)
    n = max(1, size)
    half = max(1, n // 2)
    objects = [
        canonical_zero_rooted_tiered_tree((n,)),
        canonical_zero_rooted_tiered_tree((half, n - half) if n - half else (n,)),
        canonical_zero_rooted_tiered_tree(tuple([1] * n)),
    ]
    # Weakly increasing positive levels make every earlier lower-tier label a
    # compatible parent. Attaching each vertex to root 0 or one such label keeps
    # the result connected and acyclic by construction.
    levels = []
    level = 0
    for _ in range(n):
        if generator.getrandbits(1):
            level += 1
        levels.append(max(1, level))
    parents = []
    parent_stop = 1
    for i in range(1, n + 1):
        if i > 1 and levels[i - 2] < levels[i - 1]:
            parent_stop = i
        parents.append(generator.choice(range(parent_stop)))
    encoding = ",".join(str(v) for v in levels) + "|" + ",".join(str(v) for v in parents)
    objects.append(ZeroRootedTieredTree(encoding, validate=False))
    return objects


def adversarial_ttree_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (tree,))
        for tree in adversarial_zero_rooted_tiered_trees(size, seed=seed)
    ]


def _block_labelling(gaps: Sequence[int], n: int) -> tuple[int, ...]:
    """A lattice word that always respects the top path's consecutive rises.

    Consecutive North steps have to carry strictly increasing labels, so label
    each maximal run of them ``1, 2, 3, ...``. Every prefix then has at least as
    many ``j``s as ``j + 1``s, and the content is the partition counting the
    runs by length.
    """
    word = []
    position = 1
    for index in range(n):
        word.append(position)
        position = position + 1 if index < n - 1 and gaps[index] == 0 else 1
    return tuple(word)


def _random_gamma_parking_selection(
    n: int,
    gamma: tuple[int, ...],
    generator: random.Random,
    *,
    lattice: bool,
) -> GammaParkingSelection:
    """One random large pair ``(p, S)``, built without enumerating the fiber."""
    runs = [part + 1 for part in gamma] + [1] * (n - len(gamma))
    generator.shuffle(runs)
    runs[0] += 1
    bottom = tuple(level for level, run in enumerate(runs) for _ in range(run))
    width = len(bottom)
    floors = [bottom[column + 1] + 1 for column in range(width - 1)] + [n]
    top: list[int] = []
    previous = 0
    for column in range(width):
        low = max(previous, floors[column])
        previous = n if column == width - 1 else generator.randint(low, n)
        top.append(previous)
    top = tuple(top)
    skeleton = gamma_parking_selection(bottom, top, [1] * n, (), validate=False)
    gaps = skeleton.gaps
    word = _block_labelling(gaps, n)
    if not lattice:
        # Relabel each run of consecutive North steps by an increasing choice of
        # distinct labels, which keeps the content equal to 1^n.
        order = list(range(1, n + 1))
        generator.shuffle(order)
        word = list(order)
        start = 0
        for index in range(n):
            if index == n - 1 or gaps[index] != 0:
                word[start : index + 1] = sorted(word[start : index + 1])
                start = index + 1
        word = tuple(word)
    # Keep probe construction itself linear and outside the worker's resource
    # budget: materializing every area cell can require quadratic parent memory.
    # The canonical companion probe has S empty; here choose one valid cell in
    # every nonempty column to exercise a broad, nontrivial selection.
    selected = []
    for column in range(len(bottom) - 1):
        lowest = bottom[column + 1] + 1
        if lowest < top[column]:
            selected.append(
                (column + 1, generator.randint(lowest, top[column] - 1))
            )
    return gamma_parking_selection(bottom, top, word, selected, validate=False)


def adversarial_gamma_parking_selections(
    size: int, *, seed: int | None = None, lattice: bool = False
) -> list[GammaParkingSelection]:
    """Large pairs ``(p, S)`` with ``n + |gamma| = size``.

    Each probe is a single valid object built directly, never by enumerating the
    (exponential) fiber. The canonical minimal-area object of a few fibers is
    joined by random tall paths with a random subset of their area cells.
    """
    generator = _probe_random(seed)
    total = max(2, size)
    shapes = [
        (total, ()),
        (max(1, total // 2), (total - max(1, total // 2),)),
        (max(1, total - 2), (1, 1)) if total >= 4 else (total, ()),
    ]
    objects: list[GammaParkingSelection] = []
    for n, gamma in shapes:
        gamma = tuple(part for part in gamma if part)
        if len(gamma) > n:
            continue
        content = tuple([1] * n) if not lattice else (n,)
        objects.append(canonical_gamma_parking_selection(gamma, content))
        objects.append(
            _random_gamma_parking_selection(n, gamma, generator, lattice=lattice)
        )
    return objects


def adversarial_gpf_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (obj,))
        for obj in adversarial_gamma_parking_selections(size, seed=seed)
    ]


def adversarial_lgpf_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (obj,))
        for obj in adversarial_gamma_parking_selections(size, seed=seed, lattice=True)
    ]


def adversarial_rooted_tiered_trees(
    size: int, *, seed: int | None = None
) -> list[RootedTieredTree]:
    """Large standard rooted tiered trees on ``size`` non-root vertices.

    Each tier vector gets the canonical root-star from
    ``canonical_rooted_tiered_tree``, so every probe is a single valid object
    without enumerating the (exponential) fiber. A few tier shapes (one tier,
    two tiers, fully tiered) plus a random compatible tree exercise the
    statistic.
    """
    generator = _probe_random(seed)
    n = max(1, size)
    half = max(1, n // 2)
    objects = [
        canonical_rooted_tiered_tree((n,)),
        canonical_rooted_tiered_tree((half, n - half) if n - half else (n,)),
        canonical_rooted_tiered_tree(tuple([1] * n)),
    ]
    # Label 1 stays alone at level 0 and the remaining levels increase weakly
    # with the labels, so every earlier label of a strictly lower level is an
    # admissible parent; that keeps the result connected and acyclic.
    levels = [0]
    level = 1
    for _ in range(n):
        levels.append(level)
        if generator.getrandbits(1):
            level += 1
    parents = [0]
    parent_stop = 2
    for vertex in range(2, n + 2):
        if levels[vertex - 2] < levels[vertex - 1]:
            parent_stop = vertex
        parents.append(generator.choice(range(1, parent_stop)))
    encoding = ",".join(str(v) for v in levels) + "|" + ",".join(str(v) for v in parents)
    objects.append(RootedTieredTree(encoding, validate=False))
    return objects


def adversarial_rtt_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (tree,))
        for tree in adversarial_rooted_tiered_trees(size, seed=seed)
    ]


def adversarial_threshold_spanning_trees(
    size: int, *, seed: int | None = None
) -> list[ThresholdSpanningTree]:
    """Large spanning trees of connected threshold graphs on ``size`` non-root vertices.

    Each graph gets the star from ``canonical_threshold_spanning_tree``, so every
    probe is a valid object without enumerating the (exponential) fiber. The
    complete graph, the star and a random graph in between are joined by random
    spanning trees, including deep ones that make ``inv`` nontrivial.
    """
    generator = _probe_random(seed)
    n = max(1, size)
    shapes = [
        threshold_up_degrees(n, range(1, n)),          # the complete graph
        threshold_up_degrees(n, ()),                   # the star
        threshold_up_degrees(n, range(1, n, 2)),       # every other up-degree
    ]
    objects = [canonical_threshold_spanning_tree(up) for up in shapes]
    for up_degrees in shapes:
        # Attaching each vertex to a smaller neighbour keeps the result a tree;
        # vertex 0 dominates, so a smaller neighbour always exists.
        parents = []
        parent_stop = 1
        for vertex in range(1, n + 1):
            if up_degrees[vertex - 1] > 0:
                parent_stop = vertex
            while (
                parent_stop > 1
                and vertex
                > (parent_stop - 1) + up_degrees[parent_stop - 1]
            ):
                parent_stop -= 1
            parents.append(generator.choice(range(parent_stop)))
        encoding = (
            ",".join(str(value) for value in up_degrees)
            + "|"
            + ",".join(str(value) for value in parents)
        )
        objects.append(ThresholdSpanningTree(encoding, validate=False))
    # A path, the deepest possible tree, which maximises the ancestor walks.
    complete = threshold_up_degrees(n, range(1, n))
    path = ",".join(str(value) for value in complete) + "|" + ",".join(
        str(vertex - 1) for vertex in range(1, n + 1)
    )
    objects.append(ThresholdSpanningTree(path, validate=False))
    return objects


def adversarial_tgt_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (tree,))
        for tree in adversarial_threshold_spanning_trees(size, seed=seed)
    ]


def _random_partition(n: int, generator: random.Random) -> tuple[int, ...]:
    """A random partition of ``n``: cut ``n`` into blocks, then sort decreasingly."""
    parts: list[int] = []
    remaining = n
    while remaining:
        part = generator.randint(1, remaining)
        parts.append(part)
        remaining -= part
    return tuple(sorted(parts, reverse=True))


def _probe_partitions(n: int, generator: random.Random) -> list[tuple[int, ...]]:
    """A spread of partitions of ``n``: row, column, hook, two rows, staircase, random."""
    height = 1
    while (height + 1) * (height + 2) // 2 <= n:
        height += 1
    staircase = list(range(height, 0, -1))
    staircase[0] += n - sum(staircase)
    return [
        (n,),
        tuple([1] * n),
        (n - n // 2, *([1] * (n // 2))),
        (n - n // 2, *([n // 2] if n // 2 else [])),
        tuple(sorted(staircase, reverse=True)),
        _random_partition(n, generator),
    ]


def adversarial_kostka_standard_tableaux(
    size: int, *, seed: int | None = None
) -> list[KostkaStandardTableau]:
    """Large ``(mu, T)`` objects spanning very different shapes of ``lambda`` and ``mu``.

    Both superstandard tableaux of each shape are used: the row-superstandard one
    has the smallest possible descent set and the column-superstandard one the
    largest, so a probe is a single valid object built without enumerating the
    (exponential) fiber ``SYT(lambda)``.
    """
    if size < 1:
        raise ValueError("Kostka tableau probe size must be positive")
    generator = _probe_random(seed)
    shapes = _probe_partitions(size, generator)
    return [
        canonical_kostka_standard_tableau(lam, mu, by_columns=by_columns)
        for index, lam in enumerate(shapes)
        for mu in (shapes[-1 - index], shapes[index])
        for by_columns in (False, True)
    ]


def adversarial_kostka_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (tableau,))
        for tableau in adversarial_kostka_standard_tableaux(size, seed=seed)
    ]


def _random_dyck_graph_vector(n: int, generator: random.Random) -> tuple[int, ...]:
    """A random valid right-endpoint vector: weakly increasing with ``i <= b_i <= n``."""
    b: list[int] = []
    previous = 0
    for i in range(1, n + 1):
        value = generator.randint(max(i, previous), n)
        b.append(value)
        previous = value
    return tuple(b)


def adversarial_unit_interval_graph_permutations(
    size: int, *, seed: int | None = None
) -> list[UnitIntervalGraphPermutation]:
    """Large valid ``(G, sigma)`` objects across a few graph shapes and permutations.

    The identity permutation has no descents, so it lies in ``D_G^0`` for every
    graph; that builds a single valid object per shape without enumerating the
    (exponential) fiber. The complete graph ``K_size`` has ``D_G^0 = S_size``, so it
    also accepts the reversal and a random permutation -- high-``ginv`` inputs that
    exercise the statistic. Every probe is a single valid object of ``size`` vertices.
    """
    if size < 1:
        raise ValueError("unit interval graph probe size must be positive")
    generator = _probe_random(seed)
    empty = tuple(range(1, size + 1))               # b_i = i: only the identity is valid
    complete = tuple(size for _ in range(size))      # K_size: every permutation is valid
    half = tuple(min(size, i + size // 2) for i in range(1, size + 1))
    reverse = tuple(range(size, 0, -1))
    random_perm = list(range(1, size + 1))
    generator.shuffle(random_perm)
    objects = [
        canonical_unit_interval_graph_permutation(empty),
        canonical_unit_interval_graph_permutation(complete),
        canonical_unit_interval_graph_permutation(half),
        canonical_unit_interval_graph_permutation(_random_dyck_graph_vector(size, generator)),
        unit_interval_graph_permutation(complete, reverse, validate=False),
        unit_interval_graph_permutation(complete, tuple(random_perm), validate=False),
    ]
    return objects


def adversarial_uig_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (obj,))
        for obj in adversarial_unit_interval_graph_permutations(size, seed=seed)
    ]


def adversarial_unit_interval_graph_tableaux(
    size: int, *, seed: int | None = None
) -> list[UnitIntervalGraphTableau]:
    """Large valid ``(G, T)`` objects across very different graphs and shapes.

    The graphs run from the empty graph to ``K_size``; the shapes are the usual
    spread of partitions of ``size``, each in both superstandard tableaux (the
    row one has the smallest possible descent set and the column one the
    largest). Every probe is a single valid object built without enumerating the
    (exponential) fiber.
    """
    if size < 1:
        raise ValueError("unit interval graph tableau probe size must be positive")
    generator = _probe_random(seed)
    vectors = [
        tuple(range(1, size + 1)),                              # b_i = i: no edges
        tuple(size for _ in range(size)),                       # K_size
        tuple(min(size, i + size // 2) for i in range(1, size + 1)),
        _random_dyck_graph_vector(size, generator),
    ]
    shapes = _probe_partitions(size, generator)
    return [
        canonical_unit_interval_graph_tableau(b, lam, by_columns=by_columns)
        for index, lam in enumerate(shapes)
        for b in (vectors[index % len(vectors)],)
        for by_columns in (False, True)
    ]


def adversarial_llt_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (obj,))
        for obj in adversarial_unit_interval_graph_tableaux(size, seed=seed)
    ]


def _random_matching_images(letters: int, generator: random.Random) -> tuple[int, ...]:
    order = list(range(1, letters + 1))
    generator.shuffle(order)
    images = [0] * letters
    for i, j in zip(order[::2], order[1::2]):
        images[i - 1] = j
        images[j - 1] = i
    return tuple(images)


def adversarial_jack_matchings(size: int, *, seed: int | None = None) -> list[JackMatching]:
    """Large ``(lambda, delta)`` objects across very different partitions and matchings.

    The partitions are the usual spread over ``size``; each is paired with the two
    distinguished bipartite matchings ``eps`` and ``delta_lambda``, on which the
    conjectured statistic must vanish, with the all-within-class matching, which is
    as far from bipartite as a matching gets, and with a uniformly shuffled one.
    Every probe is a single valid object built without enumerating the
    (exponentially large) fiber.
    """
    if size < 1:
        raise ValueError("Jack matching probe size must be positive")
    generator = _probe_random(seed)
    objects: list[JackMatching] = []
    for lam in _probe_partitions(size, generator):
        objects.extend(
            canonical_jack_matching(lam, kind=kind)
            for kind in ("epsilon", "reference", "within_class")
        )
        objects.append(
            jack_matching(lam, _random_matching_images(2 * size, generator), validate=False)
        )
    return objects


def adversarial_mjack_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (obj,))
        for obj in adversarial_jack_matchings(size, seed=seed)
    ]


def _probe_promotion_shapes(size: int) -> list[tuple[int, ...]]:
    """Rectangular and staircase shapes with at most ``size`` cells, as large as fit."""
    shapes: list[tuple[int, ...]] = []
    k = 2
    while (k + 1) * (k + 2) // 2 <= size:
        k += 1
    if k >= 2:
        shapes.append(staircase_shape(k))
    for rows in (2, 3, 4):
        columns = max(2, size // rows)
        if columns * rows <= size:
            shapes.append(rectangle_shape(columns, rows))
            if columns != rows:
                shapes.append(rectangle_shape(rows, columns))
    return shapes


def adversarial_promotion_tableaux(size: int, *, seed: int | None = None) -> list[PromotionTableau]:
    """Large tableaux over both shape families, in their two extreme fillings.

    The shapes are the largest staircase fitting in ``size`` cells and a spread of
    rectangles; each contributes its row- and column-superstandard tableaux, whose
    descent sets are the two extremes. Every probe is a single valid object built
    without enumerating the (exponentially large) fiber.
    """
    if size < 3:
        raise ValueError("promotion tableau probe size must be at least 3")
    return [
        canonical_promotion_tableau(shape, by_columns=by_columns)
        for shape in _probe_promotion_shapes(size)
        for by_columns in (False, True)
    ]


def adversarial_promotion_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (obj,))
        for obj in adversarial_promotion_tableaux(size, seed=seed)
    ]


def _probe_macdonald_shapes(size: int) -> list[tuple[int, ...]]:
    if size < 4:
        raise ValueError("Macdonald filling probe size must be at least 4")
    two_row = ((size + 1) // 2, size // 2)
    tall = tuple([2] * (size // 2) + ([1] if size % 2 else []))
    return [(size - 2, 2), two_row, tall]


def adversarial_standard_macdonald_fillings(
    size: int, *, seed: int | None = None
) -> list[StandardMacdonaldFilling]:
    generator = _probe_random(seed)
    objects: list[StandardMacdonaldFilling] = []
    for shape in _probe_macdonald_shapes(size):
        objects.extend(
            canonical_standard_macdonald_filling(shape, reverse=reverse)
            for reverse in (False, True)
        )
        values = list(range(1, size + 1))
        generator.shuffle(values)
        rows = []
        offset = 0
        for width in shape:
            rows.append(values[offset : offset + width])
            offset += width
        objects.append(standard_macdonald_filling(shape, rows, validate=False))
    return objects


def adversarial_macdonald_filling_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    objects = adversarial_standard_macdonald_fillings(size, seed=seed)
    return [(name, (obj,)) for obj in objects for name in ("forward", "inverse")]


def adversarial_parking_functions(
    size: int, *, seed: int | None = None
) -> list[ParkingFunction]:
    if size < 1:
        raise ValueError("parking-function probe size must be positive")
    generator = _probe_random(seed)
    middle = [(index - 1) // 2 for index in range(1, size + 1)]
    generator.shuffle(middle)
    zeros = [0] * size
    shuffled_staircase = list(range(size))
    generator.shuffle(shuffled_staircase)
    return [
        canonical_parking_function(size),
        canonical_parking_function(size, reverse=True),
        parking_function(zeros, validate=False),
        parking_function(middle, validate=False),
        parking_function(shuffled_staircase, validate=False),
    ]


def adversarial_parking_function_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    objects = adversarial_parking_functions(size, seed=seed)
    return [(name, (obj,)) for obj in objects for name in ("forward", "inverse")]


def adversarial_connected_graphs(
    size: int, *, seed: int | None = None
) -> list[ConnectedGraph]:
    """Canonical moderate probes and forced extreme pairs at large sizes."""

    if size < 1:
        raise ValueError("connected-graph probe size must be positive")
    n = min(size, 7)
    generator = _probe_random(seed)
    edge_sets = [
        [(vertex, vertex + 1) for vertex in range(n - 1)],
    ]
    if n >= 3:
        edge_sets.append([(vertex, (vertex + 1) % n) for vertex in range(n)])
    random_edges = [(vertex, vertex + 1) for vertex in range(n - 1)]
    for left in range(n):
        for right in range(left + 2, n):
            if generator.randrange(3) == 0:
                random_edges.append((left, right))
    edge_sets.append(random_edges)
    encodings = {canonical_connected_graph(n, edges) for edges in edge_sets}
    for extreme_size in {max(1, size // 4), max(1, size // 2), size}:
        edge_count = extreme_size * (extreme_size - 1) // 2
        width = max(1, (edge_count + 3) // 4)
        star_bits = (1 << (extreme_size - 1)) - 1
        complete_bits = (1 << edge_count) - 1
        encodings.add(f"{extreme_size}:{star_bits:0{width}x}")
        encodings.add(f"{extreme_size}:{complete_bits:0{width}x}")
    return [ConnectedGraph(encoding, validate=False) for encoding in sorted(encodings)]


def adversarial_connected_graph_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    objects = adversarial_connected_graphs(size, seed=seed)
    return [(name, (obj,)) for obj in objects for name in ("forward", "inverse")]


def adversarial_asm_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    if seed is None:
        seed = _derived_run_seed("adversarial-probes")
    return [
        ("statistic", (matrix,))
        for matrix in adversarial_alternating_sign_matrices(size, seed=seed)
    ]


def adversarial_shifted_pq_tableaux(
    size: int, *, seed: int | None = None
) -> list[ShiftedSetValuedTableau]:
    n = max(3, size)
    generator = _probe_random(seed)

    def singleton(family, mu, shape):
        cells = tuple(
            (
                2 * label
                - (
                    row != column
                    and generator.randrange(2)
                ),
            )
            for label, (row, column) in enumerate(shifted_shape_cells(shape), 1)
        )
        encoding = canonical_shifted_setvalued_tableau(family, mu, shape, cells)
        return ShiftedSetValuedTableau(encoding, validate=False)

    separated_mu = (n, 1)
    consecutive_mu = (n, n - 1)
    return [
        singleton("Q", separated_mu, separated_mu),
        singleton("P", separated_mu, separated_mu),
        singleton("P", consecutive_mu, (n + 1, n)),
        singleton("P", consecutive_mu, consecutive_mu),
    ]


def adversarial_shifted_pq_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("forward" if tableau.side == "source" else "inverse", (tableau,))
        for tableau in adversarial_shifted_pq_tableaux(size, seed=seed)
    ]


def _hardened_shifted_pq_tableaux(
    supplied: Sequence[ShiftedSetValuedTableau],
) -> list[ShiftedSetValuedTableau]:
    """Add two lower probe orders without regenerating the supplied maximum."""

    max_order = max((tableau.mu[0] for tableau in supplied), default=3)
    lower_orders = sorted({max(3, max_order // 4), max(3, max_order // 2)})
    generated = [
        tableau
        for order in lower_orders
        for tableau in adversarial_shifted_pq_tableaux(order)
    ]
    by_encoding = {tableau.encoding: tableau for tableau in [*supplied, *generated]}
    return list(by_encoding.values())


def adversarial_successive_rank_partitions(
    size: int, *, seed: int | None = None
) -> list[SuccessiveRankPartition]:
    k = max(2, int(size**0.5))
    generator = _probe_random(seed)
    result: list[SuccessiveRankPartition] = []
    for modulus, residue in ((6, 1), (6, 2), (7, 2), (7, 3)):
        lower_rank = max(0, 2 - residue)
        upper_rank = modulus - residue - 2
        height = max(2, k + generator.choice((-1, 0, 1)))
        source_parts = (
            (height + lower_rank,) * height,
            (height + upper_rank,) * height,
        )
        forbidden = {0, residue, (-residue) % modulus}
        allowed_parts = tuple(
            part for part in range(1, 2 * modulus + 1) if part % modulus not in forbidden
        )
        part_count = max(2, size // max(allowed_parts))
        target_parts = (
            (max(allowed_parts),) * part_count,
            tuple(
                sorted(
                    (generator.choice(allowed_parts) for _ in range(part_count)),
                    reverse=True,
                )
            ),
        )
        for source, target in zip(source_parts, target_parts, strict=True):
            result.extend(
                [
                    SuccessiveRankPartition(
                        canonical_successive_rank_partition("S", modulus, residue, source)
                    ),
                    SuccessiveRankPartition(
                        canonical_successive_rank_partition("T", modulus, residue, target)
                    ),
                ]
            )
    return result


def adversarial_successive_rank_probes(
    size: int = 1024, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("forward" if partition.side == "source" else "inverse", (partition,))
        for partition in adversarial_successive_rank_partitions(size, seed=seed)
    ]


def adversarial_partition_matrix_inversions(
    size: int, *, seed: int | None = None
) -> list[PartitionMatrixInversion]:
    n = max(4, size)
    generator = _probe_random(seed)
    diagonal = tuple(range(1, n + 1))
    result = [
        PartitionMatrixInversion(canonical_improper_partition_matrix(diagonal, diagonal)),
        PartitionMatrixInversion(canonical_restricted_inversion_sequence(tuple(range(n)))),
    ]
    blocks = []
    current = 1
    for position in range(n - 1):
        blocks.append(current)
        if position < n - 2 and generator.randrange(2):
            current += 1
    blocks.append(current + 1)
    rows = columns = tuple(blocks)
    entries = []
    value = 0
    position = 0
    while position < n:
        pair = position + 1 < n - 1 and generator.randrange(2)
        entries.extend((value, value) if pair else (value,))
        position += 2 if pair else 1
        value += 1
    entries = tuple(entries)
    result.extend(
        [
            PartitionMatrixInversion(canonical_improper_partition_matrix(rows, columns)),
            PartitionMatrixInversion(canonical_restricted_inversion_sequence(entries)),
        ]
    )
    return result


def adversarial_partition_matrix_inversion_probes(
    size: int = 1024, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("forward" if obj.side == "source" else "inverse", (obj,))
        for obj in adversarial_partition_matrix_inversions(size, seed=seed)
    ]


def _probe_descent_counts(n: int) -> list[int]:
    """A spread of fibers ``k`` of size ``n``: every ``k`` here has ``1 <= k <= (n+1)/2``."""
    top = (n + 1) // 2
    return sorted({1, max(1, top // 4), max(1, top // 2), max(1, (3 * top) // 4), top})


def adversarial_gamma_permutations(size: int, *, seed: int | None = None) -> list[GammaPermutation]:
    """Large permutations spread over the fibers ``Gamma_{size,k}`` of one size.

    Each fiber in the spread contributes its two extreme elements -- the descent set
    packed at the front and packed at the back -- plus one on a uniformly random
    admissible descent set of the same fiber. Every probe is a single valid object
    built without enumerating the (exponentially large) fiber.
    """
    if size < 1:
        raise ValueError("gamma permutation probe size must be positive")
    generator = _probe_random(seed)
    objects: list[GammaPermutation] = []
    for k in _probe_descent_counts(size):
        objects.extend(
            canonical_gamma_permutation(size, k, late=late) for late in (False, True)
        )
        objects.append(_random_gamma_permutation(size, k, generator))
    return objects


def _random_gamma_permutation(n: int, k: int, generator: random.Random) -> GammaPermutation:
    """A uniformly random *descent set* of the fiber, realized in ``O(n)``.

    Admissible descent sets of ``Gamma_{n,k}`` are the ``(k-1)``-subsets of
    ``{1, ..., n-2}`` with no two consecutive elements; subtracting ``0, 1, 2, ...``
    from the sorted elements is the standard bijection with all ``(k-1)``-subsets of
    ``{1, ..., n-k}``, which is what is sampled here.
    """
    chosen = sorted(generator.sample(range(1, n - k + 1), k - 1))
    descent_set = [value + offset for offset, value in enumerate(chosen)]
    return gamma_permutation_from_descent_set(n, descent_set)


def adversarial_qgamma_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (obj,))
        for obj in adversarial_gamma_permutations(size, seed=seed)
    ]


def _probe_fixed_point_counts(n: int) -> list[int]:
    """A spread of fibers ``a`` of size ``n``: every ``a`` here has ``a = n mod 2``."""
    counts = set()
    for value in (0, n // 4, n // 2, (3 * n) // 4, n):
        a = value if value % 2 == n % 2 else value - 1
        if a < 0:
            a += 2
        if 0 <= a <= n:
            counts.add(a)
    return sorted(counts)


def _random_involution(n: int, a: int, generator: random.Random) -> Involution:
    letters = list(range(1, n + 1))
    generator.shuffle(letters)
    images = list(range(1, n + 1))
    moved = letters[:n - a]
    for i, j in zip(moved[::2], moved[1::2]):
        images[i - 1] = j
        images[j - 1] = i
    return involution(images, validate=False)


def adversarial_involutions(size: int, *, seed: int | None = None) -> list[Involution]:
    """Large involutions spread over the fibers ``M_{size,a}`` of one size.

    Each fiber ``a`` in the spread contributes its two extreme shapes -- the
    consecutive matching ``(1 2)(3 4) ...``, whose longest decreasing subsequence is
    ``2``, and the nested one, whose longest decreasing subsequence is ``size - a``
    -- plus a uniformly shuffled member. Every probe is a single valid object built
    without enumerating the (exponentially large) fiber.
    """
    if size < 1:
        raise ValueError("involution probe size must be positive")
    generator = _probe_random(seed)
    return [
        obj
        for a in _probe_fixed_point_counts(size)
        for obj in (
            canonical_involution(size, a),
            canonical_involution(size, a, nested=True),
            _random_involution(size, a, generator),
        )
    ]


def adversarial_involution_probes(
    size: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (obj,))
        for obj in adversarial_involutions(size, seed=seed)
    ]


def _random_type_b_path(n: int, generator: random.Random) -> str:
    x = y = 0
    result: list[str] = []
    for _ in range(2 * n):
        if x < y and generator.getrandbits(1):
            result.append("E")
            x += 1
        else:
            result.append("N")
            y += 1
    return "".join(result)


def adversarial_type_b_catalan_paths(n: int, *, seed: int | None = None) -> list[TypeBCatalanPath]:
    if n < 1:
        raise ValueError("type B probe size must be positive")
    generator = _probe_random(seed)
    words = [
        "N" * (2 * n),
        "N" * n + "E" * n,
        "NE" * n,
        "NNEE" * (n // 2) + "N" * (2 * (n % 2)),
        _random_type_b_path(n, generator),
        _random_type_b_path(n, generator),
    ]
    return [TypeBCatalanPath(word) for word in words]


def adversarial_type_b_probes(
    n: int, *, seed: int | None = None
) -> list[tuple[str, tuple[Any, ...]]]:
    return [
        ("statistic", (path,))
        for path in adversarial_type_b_catalan_paths(n, seed=seed)
    ]


# Every built-in evaluator kind registers the probe builder that feeds its
# value/resource checks.  Keeping this table at module scope lets the structural
# sizing regression exercise new families automatically instead of maintaining
# a second, hand-picked list of object types.
_PROBE_BUILDERS: dict[
    str, Callable[..., list[tuple[str, tuple[Any, ...]]]]
] = {
    "gpf": adversarial_gpf_probes,
    "lgpf": adversarial_lgpf_probes,
    "rtt": adversarial_rtt_probes,
    "tgt": adversarial_tgt_probes,
    "kostka": adversarial_kostka_probes,
    "noncrossing": adversarial_noncrossing_probes,
    "type_b": adversarial_type_b_probes,
    "lpp": adversarial_lpp_probes,
    "ddyck": adversarial_ddyck_probes,
    "lrp": adversarial_lrp_probes,
    "mld": adversarial_mld_probes,
    "tamari": adversarial_tamari_probes,
    "ttree": adversarial_ttree_probes,
    "uig": adversarial_uig_probes,
    "llt": adversarial_llt_probes,
    "involution": adversarial_involution_probes,
    "mjack": adversarial_mjack_probes,
    "qgamma": adversarial_qgamma_probes,
    "promotion": adversarial_promotion_probes,
    "kreweras": adversarial_noncrossing_probes,
    "asm-q": adversarial_asm_probes,
    "area_bounce": adversarial_dyck_probes,
    "polyomino_area_bounce": adversarial_polyomino_probes,
    "polyomino_transpose": adversarial_polyomino_probes,
    "macdonald_fillings": adversarial_macdonald_filling_probes,
    "parking_area_dinv": adversarial_parking_function_probes,
    "graph_sibling_tuft": adversarial_connected_graph_probes,
    "shifted_pq": adversarial_shifted_pq_probes,
    "successive_rank": adversarial_successive_rank_probes,
    "partition_matrix_inversion": adversarial_partition_matrix_inversion_probes,
}


def _probe_size(calls: Sequence[tuple[str, tuple[Any, ...]]]) -> int:
    sizes = [
        size
        for _, arguments in calls
        if arguments and (size := _structural_size(arguments[0])) is not None
    ]
    if not sizes:
        raise GateError("resource probes do not contain a recognized structural object")
    return max(sizes)


def _hardened_probes(
    calls: Sequence[tuple[str, tuple[Any, ...]]], *, kind: str
) -> list[tuple[str, tuple[Any, ...]]]:
    size = _probe_size(calls)
    sizes = sorted({max(1, size // 4), max(1, size // 2), size})
    generate = _PROBE_BUILDERS[kind]
    generated = [call for probe_size in sizes for call in generate(probe_size)]
    return [*calls, *generated]


def _hardened_dyck_paths(paths: Sequence[str]) -> list[str]:
    size = max((len(path) // 2 for path in paths), default=0)
    if size < 1:
        raise GateError("identity probes do not contain a recognized Dyck path")
    sizes = sorted({max(1, size // 4), max(1, size // 2), size})
    generated = [path for probe_size in sizes for path in adversarial_dyck_paths(probe_size)]
    return [*paths, *generated]


def _hardened_polyominoes(polyominoes: Sequence[str]) -> list[str]:
    size = max((polyomino_size(polyomino) for polyomino in polyominoes), default=0)
    if size < 2:
        raise GateError("identity probes do not contain a recognized polyomino")
    sizes = sorted({max(2, size // 4), max(2, size // 2), size})
    generated = [
        polyomino for probe_size in sizes for polyomino in adversarial_parallelogram_polyominoes(probe_size)
    ]
    return [*polyominoes, *generated]


def _hardened_macdonald_fillings(
    fillings: Sequence[StandardMacdonaldFilling],
) -> list[StandardMacdonaldFilling]:
    size = max((filling.n for filling in fillings), default=0)
    if size < 4:
        raise GateError("identity probes do not contain a recognized Macdonald filling")
    sizes = sorted({max(4, size // 4), max(4, size // 2), size})
    generated = [
        filling
        for probe_size in sizes
        for filling in adversarial_standard_macdonald_fillings(probe_size)
    ]
    return [*fillings, *generated]


def _hardened_parking_functions(
    parking_functions: Sequence[ParkingFunction],
) -> list[ParkingFunction]:
    size = max((parking.n for parking in parking_functions), default=0)
    if size < 1:
        raise GateError("identity probes do not contain a recognized parking function")
    sizes = sorted({max(1, size // 4), max(1, size // 2), size})
    generated = [
        parking
        for probe_size in sizes
        for parking in adversarial_parking_functions(probe_size)
    ]
    return [*parking_functions, *generated]


def _hardened_connected_graphs(
    graphs: Sequence[ConnectedGraph],
) -> list[ConnectedGraph]:
    size = max((graph.n for graph in graphs), default=0)
    if size < 1:
        raise GateError("identity probes do not contain a recognized connected graph")
    generated = adversarial_connected_graphs(size)
    by_encoding = {graph.encoding: graph for graph in [*graphs, *generated]}
    return list(by_encoding.values())


def _resolve(value):
    return value() if callable(value) else value


# ---------------------------------------------------------------------------
# Numerical evaluation
# ---------------------------------------------------------------------------


def _shuffled_objects(objects, generator: random.Random | None):
    if generator is None:
        return objects
    ordered = list(objects)
    if len(ordered) < 2:
        return ordered
    cycle = list(range(len(ordered)))
    generator.shuffle(cycle)
    permutation = list(range(len(ordered)))
    for source, target in zip(cycle, cycle[1:] + cycle[:1], strict=True):
        permutation[source] = target
    return [ordered[index] for index in permutation]


def evaluate_area_bounce_bijection(
    forward,
    inverse,
    target_terms: Mapping[int, Sequence[Sequence[int]]],
    order_seed: int | None = None,
) -> dict[str, Any]:
    # An empty target would make the comparison below pass with nothing
    # compared: `all(...)` over no cases is True. The loader never produces
    # one, but the target is a caller-supplied mapping, so fail closed here.
    if not target_terms:
        raise GateError("public target contains no scored cases")
    case_results: list[dict[str, Any]] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for n in sorted(target_terms):
        expected = Counter(
            {
                (int(area), int(bounce)): int(coefficient)
                for area, bounce, coefficient in target_terms[n]
            }
        )
        generated: Counter[tuple[int, int]] = Counter()
        first_failure: str | None = None
        paths = _shuffled_objects(enumerate_dyck_paths(n), order_generator)
        for path in paths:
            image = forward(path)
            preimage = inverse(path)
            if not isinstance(image, str) or not is_dyck_path(image) or len(image) != len(path):
                first_failure = f"forward produced an invalid size-{n} path for {path}"
                break
            if not isinstance(preimage, str) or not is_dyck_path(preimage) or len(preimage) != len(path):
                first_failure = f"inverse produced an invalid size-{n} path for {path}"
                break
            if inverse(image) != path or forward(preimage) != path:
                first_failure = f"round-trip failed for {path}"
                break
            if dyck_area(path) != dyck_bounce(image) or dyck_bounce(path) != dyck_area(image):
                first_failure = f"area/bounce exchange failed for {path}"
                break
            generated[(dyck_area(path), dyck_area(image))] += 1

        correct = first_failure is None and generated == expected
        case_results.append(
            {
                "n": n,
                "count": len(enumerate_dyck_paths(n)),
                "correct": correct,
                "first_failure": first_failure,
                "polynomial_match": generated == expected,
            }
        )
        # Stop at the first failing size so a wrong submission never pays for
        # enumerating the larger sizes.
        if not correct:
            break
    return {
        "passed": all(result["correct"] for result in case_results),
        "case_results": case_results,
    }


def public_area_bounce_terms(max_n: int) -> dict[int, list[list[int]]]:
    return {
        n: [
            [area, bounce, coefficient]
            for (area, bounce), coefficient in sorted(area_bounce_distribution(n).items())
        ]
        for n in range(1, max_n + 1)
    }


def _unique_target_terms(data: Mapping[str, Any], key_of) -> dict[Any, list[list[int]]]:
    terms_by_key: dict[Any, list[list[int]]] = {}
    for case in data["cases"]:
        key = key_of(case)
        if key in terms_by_key:
            raise ValueError(f"public target contains duplicate structural case {key!r}")
        terms_by_key[key] = [list(term) for term in case["terms"]]
    return terms_by_key


def load_area_bounce_terms(problem_dir) -> dict[int, list[list[int]]]:
    """Read the published area/bounce target from a problem's data/ directory."""

    data = _load_public_polynomials(Path(problem_dir).resolve())
    return _unique_target_terms(data, lambda case: int(case["n"]))


def evaluate_polyomino_area_bounce_bijection(
    forward,
    inverse,
    target_terms: Mapping[tuple[int, int], Sequence[Sequence[int]]],
    order_seed: int | None = None,
) -> dict[str, Any]:
    # An empty target would make the comparison below pass with nothing
    # compared: `all(...)` over no cases is True. The loader never produces
    # one, but the target is a caller-supplied mapping, so fail closed here.
    if not target_terms:
        raise GateError("public target contains no scored cases")
    case_results: list[dict[str, Any]] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for m, n in sorted(target_terms):
        expected = Counter(
            {
                (int(area), int(bounce)): int(coefficient)
                for area, bounce, coefficient in target_terms[(m, n)]
            }
        )
        generated: Counter[tuple[int, int]] = Counter()
        first_failure: str | None = None
        polyominoes = _shuffled_objects(
            iter_parallelogram_polyominoes(m, n), order_generator
        )
        for polyomino in polyominoes:
            image = forward(polyomino)
            preimage = inverse(polyomino)
            if (
                not isinstance(image, str)
                or not is_parallelogram_polyomino(image)
                or polyomino_dimensions(image) != (m, n)
            ):
                first_failure = f"forward produced an invalid ({m},{n}) polyomino for {polyomino}"
                break
            if (
                not isinstance(preimage, str)
                or not is_parallelogram_polyomino(preimage)
                or polyomino_dimensions(preimage) != (m, n)
            ):
                first_failure = f"inverse produced an invalid ({m},{n}) polyomino for {polyomino}"
                break
            if inverse(image) != polyomino or forward(preimage) != polyomino:
                first_failure = f"round-trip failed for {polyomino}"
                break
            if polyomino_area(polyomino) != polyomino_bounce(image) or polyomino_bounce(
                polyomino
            ) != polyomino_area(image):
                first_failure = f"area/bounce exchange failed for {polyomino}"
                break
            generated[(polyomino_area(polyomino), polyomino_area(image))] += 1

        correct = first_failure is None and generated == expected
        case_results.append(
            {
                "m": m,
                "n": n,
                "count": polyomino_count(m, n),
                "correct": correct,
                "first_failure": first_failure,
                "polynomial_match": generated == expected,
            }
        )
        # Stop at the first failing box so a wrong submission never pays for
        # enumerating the larger boxes.
        if not correct:
            break
    return {
        "passed": all(result["correct"] for result in case_results),
        "case_results": case_results,
    }


def public_polyomino_area_bounce_terms(max_sum: int) -> dict[tuple[int, int], list[list[int]]]:
    terms: dict[tuple[int, int], list[list[int]]] = {}
    for total in range(2, max_sum + 1):
        for m in range(1, total):
            n = total - m
            distribution = polyomino_area_bounce_distribution(m, n)
            terms[(m, n)] = [
                [area, bounce, coefficient]
                for (area, bounce), coefficient in sorted(distribution.items())
            ]
    return terms


def load_polyomino_area_bounce_terms(problem_dir) -> dict[tuple[int, int], list[list[int]]]:
    """Read the published polyomino area/bounce target from ``data/``."""

    data = _load_public_polynomials(Path(problem_dir).resolve())
    return _unique_target_terms(
        data, lambda case: (int(case["m"]), int(case["n"]))
    )


def evaluate_polyomino_transpose_bijection(
    forward,
    inverse,
    target_terms: Mapping[tuple[int, int], Sequence[Sequence[int]]],
    order_seed: int | None = None,
) -> dict[str, Any]:
    """Check a bijection ``Polyo_{m,n} -> Polyo_{n,m}`` preserving area and bounce.

    Such a bijection is a combinatorial proof of the m,n symmetry
    ``Nara_{m,n}(q,t) = Nara_{n,m}(q,t)``; ``forward`` sends a box-(m,n) polyomino
    to a box-(n,m) polyomino with the same area and bounce, and ``inverse``
    reverses it.
    """
    # An empty target would make the comparison below pass with nothing
    # compared: `all(...)` over no cases is True. The loader never produces
    # one, but the target is a caller-supplied mapping, so fail closed here.
    if not target_terms:
        raise GateError("public target contains no scored cases")
    case_results: list[dict[str, Any]] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for m, n in sorted(target_terms):
        expected = Counter(
            {
                (int(area), int(bounce)): int(coefficient)
                for area, bounce, coefficient in target_terms[(n, m)]
            }
        )
        generated: Counter[tuple[int, int]] = Counter()
        first_failure: str | None = None
        polyominoes = _shuffled_objects(
            iter_parallelogram_polyominoes(m, n), order_generator
        )
        for polyomino in polyominoes:
            image = forward(polyomino)
            preimage = inverse(polyomino)
            if (
                not isinstance(image, str)
                or not is_parallelogram_polyomino(image)
                or polyomino_dimensions(image) != (n, m)
            ):
                first_failure = f"forward produced an invalid ({n},{m}) polyomino for {polyomino}"
                break
            if (
                not isinstance(preimage, str)
                or not is_parallelogram_polyomino(preimage)
                or polyomino_dimensions(preimage) != (n, m)
            ):
                first_failure = f"inverse produced an invalid ({n},{m}) polyomino for {polyomino}"
                break
            if inverse(image) != polyomino or forward(preimage) != polyomino:
                first_failure = f"round-trip failed for {polyomino}"
                break
            if polyomino_area(image) != polyomino_area(polyomino) or polyomino_bounce(
                image
            ) != polyomino_bounce(polyomino):
                first_failure = f"area/bounce not preserved for {polyomino}"
                break
            generated[(polyomino_area(image), polyomino_bounce(image))] += 1

        correct = first_failure is None and generated == expected
        case_results.append(
            {
                "m": m,
                "n": n,
                "count": polyomino_count(m, n),
                "correct": correct,
                "first_failure": first_failure,
                "polynomial_match": generated == expected,
            }
        )
        # Stop at the first failing box so a wrong submission never pays for
        # enumerating the larger boxes.
        if not correct:
            break
    return {
        "passed": all(result["correct"] for result in case_results),
        "case_results": case_results,
    }


def load_macdonald_filling_terms(problem_dir) -> dict[tuple[int, ...], list[list[int]]]:
    data = _load_public_polynomials(Path(problem_dir).resolve())
    return _unique_target_terms(
        data, lambda case: tuple(int(part) for part in case["shape"])
    )


def evaluate_macdonald_filling_bijection(
    forward,
    inverse,
    target_terms: Mapping[tuple[int, ...], Sequence[Sequence[int]]],
    order_seed: int | None = None,
) -> dict[str, Any]:
    if not target_terms:
        raise GateError("public target contains no scored cases")
    case_results: list[dict[str, Any]] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for shape in sorted(target_terms, key=lambda value: (sum(value), value), reverse=False):
        expected = Counter(
            {(int(inv), int(maj)): int(coefficient) for inv, maj, coefficient in target_terms[shape]}
        )
        generated: Counter[tuple[int, int]] = Counter()
        first_failure: str | None = None
        fillings = _shuffled_objects(iter_standard_macdonald_fillings(shape), order_generator)
        count = 0
        for filling in fillings:
            count += 1
            image_encoding = forward(filling)
            preimage_encoding = inverse(filling)
            if not is_standard_macdonald_filling(image_encoding):
                first_failure = f"forward produced an invalid filling for shape {shape}"
                break
            if not is_standard_macdonald_filling(preimage_encoding):
                first_failure = f"inverse produced an invalid filling for shape {shape}"
                break
            image = StandardMacdonaldFilling(image_encoding, validate=False)
            preimage = StandardMacdonaldFilling(preimage_encoding, validate=False)
            if image.shape != filling.conjugate_shape or preimage.shape != filling.conjugate_shape:
                first_failure = f"image does not have conjugate shape for {filling.encoding}"
                break
            round_trip = inverse(image)
            reverse_round_trip = forward(preimage)
            if not (
                is_standard_macdonald_filling(round_trip)
                and is_standard_macdonald_filling(reverse_round_trip)
            ):
                first_failure = f"round-trip produced an invalid filling for {filling.encoding}"
                break
            if round_trip != filling.encoding or reverse_round_trip != filling.encoding:
                first_failure = f"round-trip failed for {filling.encoding}"
                break
            if filling.inv() != image.maj() or filling.maj() != image.inv():
                first_failure = f"inv/maj exchange failed for {filling.encoding}"
                break
            if filling.inv() != preimage.maj() or filling.maj() != preimage.inv():
                first_failure = f"inverse inv/maj exchange failed for {filling.encoding}"
                break
            generated[(filling.inv(), image.inv())] += 1
        correct = first_failure is None and generated == expected
        case_results.append(
            {
                "shape": list(shape),
                "count": count,
                "correct": correct,
                "first_failure": first_failure,
                "polynomial_match": generated == expected,
            }
        )
        if not correct:
            break
    return {"passed": all(result["correct"] for result in case_results), "case_results": case_results}


def load_parking_area_dinv_terms(problem_dir) -> dict[int, list[list[int]]]:
    data = _load_public_polynomials(Path(problem_dir).resolve())
    return _unique_target_terms(data, lambda case: int(case["n"]))


def evaluate_parking_area_dinv_bijection(
    forward,
    inverse,
    target_terms: Mapping[int, Sequence[Sequence[int]]],
    order_seed: int | None = None,
) -> dict[str, Any]:
    if not target_terms:
        raise GateError("public target contains no scored cases")
    case_results: list[dict[str, Any]] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for n in sorted(target_terms):
        expected = Counter(
            {(int(area), int(dinv)): int(coefficient) for area, dinv, coefficient in target_terms[n]}
        )
        generated: Counter[tuple[int, int]] = Counter()
        first_failure: str | None = None
        parking_functions = _shuffled_objects(iter_parking_functions(n), order_generator)
        count = 0
        for parking in parking_functions:
            count += 1
            image_encoding = forward(parking)
            preimage_encoding = inverse(parking)
            if not is_parking_function_word(image_encoding):
                first_failure = f"forward produced an invalid parking function at size {n}"
                break
            if not is_parking_function_word(preimage_encoding):
                first_failure = f"inverse produced an invalid parking function at size {n}"
                break
            image = ParkingFunction(image_encoding, validate=False)
            preimage = ParkingFunction(preimage_encoding, validate=False)
            if image.n != n or preimage.n != n:
                first_failure = f"image changed parking-function size at size {n}"
                break
            round_trip = inverse(image)
            reverse_round_trip = forward(preimage)
            if not (
                is_parking_function_word(round_trip)
                and is_parking_function_word(reverse_round_trip)
            ):
                first_failure = f"round-trip produced an invalid parking function for {parking.encoding}"
                break
            if round_trip != parking.encoding or reverse_round_trip != parking.encoding:
                first_failure = f"round-trip failed for {parking.encoding}"
                break
            if parking.area() != image.dinv() or parking.dinv() != image.area():
                first_failure = f"area/dinv exchange failed for {parking.encoding}"
                break
            if parking.area() != preimage.dinv() or parking.dinv() != preimage.area():
                first_failure = f"inverse area/dinv exchange failed for {parking.encoding}"
                break
            generated[(parking.area(), image.area())] += 1
        correct = first_failure is None and generated == expected
        case_results.append(
            {
                "n": n,
                "count": count,
                "correct": correct,
                "first_failure": first_failure,
                "polynomial_match": generated == expected,
            }
        )
        if not correct:
            break
    return {"passed": all(result["correct"] for result in case_results), "case_results": case_results}


def load_graph_sibling_tuft_terms(problem_dir) -> dict[int, dict[str, Any]]:
    problem_dir = Path(problem_dir).resolve()
    polynomials = _load_public_polynomials(problem_dir)
    instances = _load_json_document(problem_dir / "data" / "instances.json")
    if not isinstance(instances, dict):
        raise ValueError("graph instances must contain a JSON object")
    instance_cases = instances.get("cases")
    instance_problem_id = instances.get("problem_id")
    instance_case_count = instances.get("case_count")
    if not isinstance(instance_cases, list) or not instance_cases or (
        instances.get("schema_version") != "0.1"
        or type(instance_problem_id) is not int
        or instance_problem_id != polynomials["problem_id"]
        or instances.get("problem_name") != polynomials["problem_name"]
        or type(instance_case_count) is not int
        or instance_case_count != len(instance_cases)
    ):
        raise ValueError("graph instances do not match the public polynomial target")
    polynomial_by_id = {case["case_id"]: case for case in polynomials["cases"]}
    entries_by_n: dict[int, list[str]] = {}
    seen_case_ids: set[str] = set()
    for case in instance_cases:
        if not isinstance(case, dict):
            raise ValueError("graph instances contain a malformed case")
        case_id = case.get("case_id")
        target = polynomial_by_id.get(case_id)
        n = case.get("n")
        entries = case.get("entries")
        if (
            not isinstance(case_id, str)
            or case_id in seen_case_ids
            or target is None
            or type(n) is not int
            or n < 1
            or target.get("n") != n
            or n in entries_by_n
            or not isinstance(entries, list)
            or not entries
            or type(case.get("count")) is not int
            or case.get("count") != len(entries)
            or target.get("count") != len(entries)
            or sum(term[-1] for term in target["terms"]) != len(entries)
        ):
            raise ValueError("graph instance case does not match its polynomial target")
        encodings: list[str] = []
        seen_encodings: set[str] = set()
        for entry in entries:
            encoding = entry.get("graph") if isinstance(entry, dict) else None
            if (
                not is_connected_graph_encoding(encoding)
                or connected_graph_size(encoding) != n
                or encoding in seen_encodings
            ):
                raise ValueError(f"graph instance {case_id} has an invalid or duplicate encoding")
            graph = ConnectedGraph(encoding, validate=False)
            if (
                type(entry.get("sibling_number")) is not int
                or type(entry.get("tuft_number")) is not int
                or entry.get("sibling_number") != graph.sibling_number()
                or entry.get("tuft_number") != graph.tuft_number()
                or not isinstance(entry.get("reduction"), str)
                or entry.get("reduction") != graph.reduction
            ):
                raise ValueError(f"graph instance {case_id} has incorrect public statistics")
            seen_encodings.add(encoding)
            encodings.append(encoding)
        observed = Counter(
            (entry["sibling_number"], entry["tuft_number"]) for entry in entries
        )
        expected = Counter(
            {(sibling, tuft): coefficient for sibling, tuft, coefficient in target["terms"]}
        )
        if observed != expected:
            raise ValueError(f"graph instance {case_id} does not match its polynomial terms")
        seen_case_ids.add(case_id)
        entries_by_n[n] = encodings
    if seen_case_ids != set(polynomial_by_id):
        raise ValueError("graph instance cases do not match the polynomial cases")
    return {
        int(case["n"]): {
            "terms": [list(term) for term in case["terms"]],
            "graphs": entries_by_n[int(case["n"])],
        }
        for case in polynomials["cases"]
    }


def evaluate_graph_sibling_tuft_bijection(
    forward,
    inverse,
    target_cases: Mapping[int, Mapping[str, Any]],
    order_seed: int | None = None,
) -> dict[str, Any]:
    if not target_cases:
        raise GateError("public target contains no scored cases")
    case_results: list[dict[str, Any]] = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for n in sorted(target_cases):
        case = target_cases[n]
        expected = Counter(
            {
                (int(sibling), int(tuft)): int(coefficient)
                for sibling, tuft, coefficient in case["terms"]
            }
        )
        allowed = frozenset(str(encoding) for encoding in case["graphs"])
        graphs = [ConnectedGraph(encoding, validate=False) for encoding in allowed]
        graphs = _shuffled_objects(graphs, order_generator)
        generated: Counter[tuple[int, int]] = Counter()
        first_failure: str | None = None
        count = 0
        for graph in graphs:
            count += 1
            image_encoding = forward(graph)
            preimage_encoding = inverse(graph)
            if not isinstance(image_encoding, str) or image_encoding not in allowed:
                first_failure = f"forward produced a noncanonical or invalid graph at size {n}"
                break
            if not isinstance(preimage_encoding, str) or preimage_encoding not in allowed:
                first_failure = f"inverse produced a noncanonical or invalid graph at size {n}"
                break
            image = ConnectedGraph(image_encoding, validate=False)
            preimage = ConnectedGraph(preimage_encoding, validate=False)
            round_trip = inverse(image)
            reverse_round_trip = forward(preimage)
            if (
                not isinstance(round_trip, str)
                or not isinstance(reverse_round_trip, str)
                or round_trip not in allowed
                or reverse_round_trip not in allowed
            ):
                first_failure = f"round-trip produced an invalid graph for {graph.encoding}"
                break
            if round_trip != graph.encoding or reverse_round_trip != graph.encoding:
                first_failure = f"round-trip failed for {graph.encoding}"
                break
            if (
                graph.sibling_number() != image.tuft_number()
                or graph.tuft_number() != image.sibling_number()
            ):
                first_failure = f"sibling/tuft exchange failed for {graph.encoding}"
                break
            if (
                graph.sibling_number() != preimage.tuft_number()
                or graph.tuft_number() != preimage.sibling_number()
            ):
                first_failure = f"inverse sibling/tuft exchange failed for {graph.encoding}"
                break
            if image.reduction != graph.reduction or preimage.reduction != graph.reduction:
                first_failure = f"graph reduction was not preserved for {graph.encoding}"
                break
            generated[(graph.sibling_number(), image.sibling_number())] += 1
        correct = first_failure is None and generated == expected
        case_results.append(
            {
                "n": n,
                "count": count,
                "correct": correct,
                "first_failure": first_failure,
                "polynomial_match": generated == expected,
            }
        )
        if not correct:
            break
    return {"passed": all(result["correct"] for result in case_results), "case_results": case_results}


def load_shifted_pq_cases(problem_dir) -> dict[str, dict[str, Any]]:
    problem_dir = Path(problem_dir).resolve()
    data = _load_public_polynomials(problem_dir)
    marginal_data = _load_public_unrefined_marginal(
        problem_dir, specialized_variable="entry_count"
    )
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    result = {}
    for case in data["cases"]:
        case_id = case.get("case_id")
        mu = tuple(case.get("mu", ()))
        content = tuple(case.get("content", ()))
        if (
            not isinstance(case_id, str)
            or case_id in result
            or not mu
            or not content
            or any(type(value) is not int or value < 1 for value in (*mu, *content))
        ):
            raise ValueError("shifted-tableau target contains a malformed case")
        source = list(iter_shifted_setvalued_tableaux("Q", mu, mu, content))
        target = []
        for shape, sign in shifted_extensions(mu):
            tableaux = list(iter_shifted_setvalued_tableaux("P", mu, shape, content))
            (source if sign < 0 else target).extend(tableaux)
        count = case.get("count")
        component_counts = Counter(
            obj.family + ":" + ",".join(map(str, obj.shape)) for obj in source
        )
        expected_components = [
            [key, component_counts[key]] for key in sorted(component_counts)
        ]
        if (
            type(count) is not int
            or count < 1
            or len(source) != count
            or len(target) != count
            or case.get("target_count") != count
            or case.get("source_component_counts") != expected_components
            or case.get("terms") != [[sum(content), count]]
            or case_id not in marginal_cases
            or marginal_cases[case_id].get("mu") != list(mu)
            or marginal_cases[case_id].get("content") != list(content)
            or marginal_cases[case_id].get("count") != count
        ):
            raise ValueError("shifted-tableau fiber does not match its public target")
        result[case_id] = {
            "mu": mu,
            "content": content,
            "source": [obj.encoding for obj in source],
            "target": [obj.encoding for obj in target],
        }
    if not result:
        raise GateError("public target contains no scored cases")
    if set(marginal_cases) != set(result):
        raise ValueError("shifted-tableau q=1 and polynomial cases do not agree")
    return result


def evaluate_shifted_pq_bijection(
    forward,
    inverse,
    target_cases: Mapping[str, Mapping[str, Any]],
    order_seed: int | None = None,
) -> dict[str, Any]:
    if not target_cases:
        raise GateError("public target contains no scored cases")
    case_results = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case_id in sorted(target_cases):
        case = target_cases[case_id]
        source_allowed = frozenset(case["source"])
        target_allowed = frozenset(case["target"])
        source = _shuffled_objects(
            [ShiftedSetValuedTableau(value, validate=False) for value in source_allowed],
            order_generator,
        )
        target = _shuffled_objects(
            [ShiftedSetValuedTableau(value, validate=False) for value in target_allowed],
            order_generator,
        )
        first_failure = None
        for obj in source:
            image_encoding = forward(obj)
            if not isinstance(image_encoding, str) or image_encoding not in target_allowed:
                first_failure = f"forward produced a noncanonical or wrong-side tableau in {case_id}"
                break
            image = ShiftedSetValuedTableau(image_encoding, validate=False)
            round_trip = inverse(image)
            if image.content != obj.content:
                first_failure = f"forward changed content in {case_id}"
                break
            if not isinstance(round_trip, str) or round_trip != obj.encoding:
                first_failure = f"inverse(forward(tableau)) failed in {case_id}"
                break
        if first_failure is None:
            for obj in target:
                preimage_encoding = inverse(obj)
                if not isinstance(preimage_encoding, str) or preimage_encoding not in source_allowed:
                    first_failure = f"inverse produced a noncanonical or wrong-side tableau in {case_id}"
                    break
                preimage = ShiftedSetValuedTableau(preimage_encoding, validate=False)
                reverse_round_trip = forward(preimage)
                if preimage.content != obj.content:
                    first_failure = f"inverse changed content in {case_id}"
                    break
                if not isinstance(reverse_round_trip, str) or reverse_round_trip != obj.encoding:
                    first_failure = f"forward(inverse(tableau)) failed in {case_id}"
                    break
        correct = first_failure is None
        case_results.append(
            {
                "case_id": case_id,
                "count": len(source),
                "correct": correct,
                "first_failure": first_failure,
            }
        )
        if not correct:
            break
    return {"passed": all(case["correct"] for case in case_results), "case_results": case_results}


def load_successive_rank_cases(problem_dir) -> dict[str, dict[str, Any]]:
    problem_dir = Path(problem_dir).resolve()
    data = _load_public_polynomials(problem_dir)
    marginal_data = _load_public_unrefined_marginal(
        problem_dir, specialized_variable="weight"
    )
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    result = {}
    for case in data["cases"]:
        case_id = case.get("case_id")
        modulus = case.get("modulus")
        residue = case.get("residue")
        weight = case.get("weight")
        if (
            not isinstance(case_id, str)
            or case_id in result
            or type(modulus) is not int
            or type(residue) is not int
            or type(weight) is not int
            or weight < 1
            or not 0 < 2 * residue < modulus
        ):
            raise ValueError("successive-rank target contains a malformed case")
        source = iter_successive_rank_partitions("source", modulus, residue, weight)
        target = iter_successive_rank_partitions("target", modulus, residue, weight)
        count = case.get("count")
        if (
            type(count) is not int
            or count < 1
            or len(source) != count
            or len(target) != count
            or case.get("target_count") != count
            or case.get("terms") != [[weight, count]]
            or case_id not in marginal_cases
            or marginal_cases[case_id].get("modulus") != modulus
            or marginal_cases[case_id].get("residue") != residue
            or marginal_cases[case_id].get("weight") != weight
            or marginal_cases[case_id].get("count") != count
        ):
            raise ValueError("successive-rank fiber does not match its public target")
        result[case_id] = {
            "modulus": modulus,
            "residue": residue,
            "weight": weight,
            "source": [obj.encoding for obj in source],
            "target": [obj.encoding for obj in target],
        }
    if not result:
        raise GateError("public target contains no scored cases")
    if set(marginal_cases) != set(result):
        raise ValueError("successive-rank q=1 and polynomial cases do not agree")
    return result


def evaluate_successive_rank_bijection(
    forward,
    inverse,
    target_cases: Mapping[str, Mapping[str, Any]],
    order_seed: int | None = None,
) -> dict[str, Any]:
    if not target_cases:
        raise GateError("public target contains no scored cases")
    case_results = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for case_id in sorted(target_cases):
        case = target_cases[case_id]
        source_allowed = frozenset(case["source"])
        target_allowed = frozenset(case["target"])
        source = _shuffled_objects(
            [SuccessiveRankPartition(value, validate=False) for value in source_allowed],
            order_generator,
        )
        target = _shuffled_objects(
            [SuccessiveRankPartition(value, validate=False) for value in target_allowed],
            order_generator,
        )
        first_failure = None
        for obj in source:
            image_encoding = forward(obj)
            if not isinstance(image_encoding, str) or image_encoding not in target_allowed:
                first_failure = f"forward produced a noncanonical or wrong-side partition in {case_id}"
                break
            image = SuccessiveRankPartition(image_encoding, validate=False)
            if image.weight != obj.weight:
                first_failure = f"forward changed partition weight in {case_id}"
                break
            round_trip = inverse(image)
            if not isinstance(round_trip, str) or round_trip != obj.encoding:
                first_failure = f"inverse(forward(partition)) failed in {case_id}"
                break
        if first_failure is None:
            for obj in target:
                preimage_encoding = inverse(obj)
                if not isinstance(preimage_encoding, str) or preimage_encoding not in source_allowed:
                    first_failure = f"inverse produced a noncanonical or wrong-side partition in {case_id}"
                    break
                preimage = SuccessiveRankPartition(preimage_encoding, validate=False)
                if preimage.weight != obj.weight:
                    first_failure = f"inverse changed partition weight in {case_id}"
                    break
                reverse_round_trip = forward(preimage)
                if not isinstance(reverse_round_trip, str) or reverse_round_trip != obj.encoding:
                    first_failure = f"forward(inverse(partition)) failed in {case_id}"
                    break
        case_results.append(
            {
                "case_id": case_id,
                "count": len(source),
                "correct": first_failure is None,
                "first_failure": first_failure,
            }
        )
        if first_failure is not None:
            break
    return {"passed": all(case["correct"] for case in case_results), "case_results": case_results}


def load_partition_matrix_inversion_cases(problem_dir) -> dict[int, dict[str, Any]]:
    problem_dir = Path(problem_dir).resolve()
    data = _load_public_polynomials(problem_dir)
    marginal_data = _load_public_unrefined_marginal(
        problem_dir, specialized_variable="grading"
    )
    marginal_cases = {case["case_id"]: case for case in marginal_data["cases"]}
    result = {}
    for case in data["cases"]:
        case_id = case.get("case_id")
        n = case.get("n")
        if not isinstance(case_id, str) or type(n) is not int or n in result or n < 2:
            raise ValueError("partition-matrix target contains a malformed case")
        source = iter_improper_partition_matrices(n)
        target = iter_restricted_inversion_sequences(n)
        source_distribution = Counter(obj.grading for obj in source)
        terms = [[grading, source_distribution[grading]] for grading in sorted(source_distribution)]
        count = case.get("count")
        if (
            case_id != f"n{n:02d}"
            or type(count) is not int
            or count < 1
            or len(source) != count
            or len(target) != count
            or case.get("target_count") != count
            or case.get("terms") != terms
            or Counter(obj.grading for obj in target) != source_distribution
            or case_id not in marginal_cases
            or marginal_cases[case_id].get("n") != n
            or marginal_cases[case_id].get("count") != count
        ):
            raise ValueError("partition-matrix fiber does not match its public target")
        result[n] = {
            "source": [obj.encoding for obj in source],
            "target": [obj.encoding for obj in target],
        }
    if not result:
        raise GateError("public target contains no scored cases")
    if set(marginal_cases) != {f"n{n:02d}" for n in result}:
        raise ValueError("partition-matrix q=1 and polynomial cases do not agree")
    return result


def evaluate_partition_matrix_inversion_bijection(
    forward,
    inverse,
    target_cases: Mapping[int, Mapping[str, Any]],
    order_seed: int | None = None,
) -> dict[str, Any]:
    if not target_cases:
        raise GateError("public target contains no scored cases")
    case_results = []
    order_generator = random.Random(order_seed) if order_seed is not None else None
    for n in sorted(target_cases):
        case = target_cases[n]
        source_allowed = frozenset(case["source"])
        target_allowed = frozenset(case["target"])
        source = _shuffled_objects(
            [PartitionMatrixInversion(value, validate=False) for value in source_allowed],
            order_generator,
        )
        target = _shuffled_objects(
            [PartitionMatrixInversion(value, validate=False) for value in target_allowed],
            order_generator,
        )
        first_failure = None
        for obj in source:
            image_encoding = forward(obj)
            if not isinstance(image_encoding, str) or image_encoding not in target_allowed:
                first_failure = f"forward produced a noncanonical or wrong-side object at size {n}"
                break
            image = PartitionMatrixInversion(image_encoding, validate=False)
            if image.grading != obj.grading:
                first_failure = f"forward changed the grading at size {n}"
                break
            round_trip = inverse(image)
            if not isinstance(round_trip, str) or round_trip != obj.encoding:
                first_failure = f"inverse(forward(object)) failed at size {n}"
                break
        if first_failure is None:
            for obj in target:
                preimage_encoding = inverse(obj)
                if not isinstance(preimage_encoding, str) or preimage_encoding not in source_allowed:
                    first_failure = f"inverse produced a noncanonical or wrong-side object at size {n}"
                    break
                preimage = PartitionMatrixInversion(preimage_encoding, validate=False)
                if preimage.grading != obj.grading:
                    first_failure = f"inverse changed the grading at size {n}"
                    break
                reverse_round_trip = forward(preimage)
                if not isinstance(reverse_round_trip, str) or reverse_round_trip != obj.encoding:
                    first_failure = f"forward(inverse(object)) failed at size {n}"
                    break
        case_results.append(
            {"n": n, "count": len(source), "correct": first_failure is None, "first_failure": first_failure}
        )
        if first_failure is not None:
            break
    return {"passed": all(case["correct"] for case in case_results), "case_results": case_results}


_STATISTIC_EVALUATORS = {
    "gpf": evaluate_gpf_polynomial_checks,
    "lgpf": evaluate_lgpf_polynomial_checks,
    "rtt": evaluate_rtt_polynomial_checks,
    "tgt": evaluate_tgt_polynomial_checks,
    "kostka": evaluate_kostka_polynomial_checks,
    "noncrossing": evaluate_public_polynomial_checks,
    "type_b": evaluate_type_b_polynomial_checks,
    "lpp": evaluate_lpp_polynomial_checks,
    "ddyck": evaluate_ddyck_polynomial_checks,
    "lrp": evaluate_lrp_polynomial_checks,
    "mld": evaluate_mld_polynomial_checks,
    "tamari": evaluate_tamari_polynomial_checks,
    "ttree": evaluate_ttree_polynomial_checks,
    "uig": evaluate_uig_polynomial_checks,
    "llt": evaluate_llt_polynomial_checks,
    "involution": evaluate_involution_polynomial_checks,
    "mjack": evaluate_mjack_polynomial_checks,
    "qgamma": evaluate_qgamma_polynomial_checks,
    "promotion": evaluate_promotion_polynomial_checks,
    "kreweras": evaluate_kreweras_polynomial_checks,
    "asm-q": evaluate_asm_q_polynomial_checks,
}
_STATISTIC_KINDS = frozenset(_STATISTIC_EVALUATORS)
_FINGERPRINT_MODULUS = 1 << 128


class _DeterminismViolation(Exception):
    pass


def _canonical_submission_output(kind: str, obj: Any, value: Any) -> Any:
    if kind == "uig":
        return _normalize_composition(value, obj.n)
    return value


def _recording_function(function, label: str, key: bytes, *, repeat: bool, normalize):
    state = {"count": 0, "fingerprint": 0}

    def recorded(obj):
        value = normalize(obj, function(obj))
        if repeat:
            repeated = normalize(obj, function(obj))
            if repeated != value:
                raise _DeterminismViolation(
                    f"{label} returned both {value!r} and {repeated!r} for one object"
                )
        identity = obj if isinstance(obj, str) else getattr(obj, "encoding", repr(obj))
        payload = f"{label}\0{type(obj).__name__}\0{identity}\0{value!r}".encode("utf-8")
        digest = hashlib.blake2b(payload, key=key, digest_size=16).digest()
        state["count"] += 1
        state["fingerprint"] = (
            state["fingerprint"] + int.from_bytes(digest, "big")
        ) % _FINGERPRINT_MODULUS
        return value

    return recorded, state


def _recording_statistic(statistic, kind: str, key: bytes, *, repeat: bool):
    return _recording_function(
        statistic,
        "statistic",
        key,
        repeat=repeat,
        normalize=lambda obj, value: _canonical_submission_output(kind, obj, value),
    )


def _recording_bijection(function, name: str, key: bytes, *, repeat: bool):
    return _recording_function(
        function,
        name,
        key,
        repeat=repeat,
        normalize=lambda _obj, value: value,
    )


def _evaluate_numerical(
    kind,
    functions,
    *,
    problem_dir,
    target_terms,
    order_seed=None,
):
    if kind in _STATISTIC_EVALUATORS:
        return _STATISTIC_EVALUATORS[kind](
            problem_dir=problem_dir,
            statistic=functions["statistic"],
            order_seed=order_seed,
        )
    if kind == "area_bounce":
        return evaluate_area_bounce_bijection(
            functions["forward"], functions["inverse"], target_terms, order_seed
        )
    if kind == "polyomino_area_bounce":
        return evaluate_polyomino_area_bounce_bijection(
            functions["forward"], functions["inverse"], target_terms, order_seed
        )
    if kind == "polyomino_transpose":
        return evaluate_polyomino_transpose_bijection(
            functions["forward"], functions["inverse"], target_terms, order_seed
        )
    if kind == "macdonald_fillings":
        return evaluate_macdonald_filling_bijection(
            functions["forward"], functions["inverse"], target_terms, order_seed
        )
    if kind == "parking_area_dinv":
        return evaluate_parking_area_dinv_bijection(
            functions["forward"], functions["inverse"], target_terms, order_seed
        )
    if kind == "graph_sibling_tuft":
        return evaluate_graph_sibling_tuft_bijection(
            functions["forward"], functions["inverse"], target_terms, order_seed
        )
    if kind == "shifted_pq":
        return evaluate_shifted_pq_bijection(
            functions["forward"], functions["inverse"], target_terms, order_seed
        )
    if kind == "successive_rank":
        return evaluate_successive_rank_bijection(
            functions["forward"], functions["inverse"], target_terms, order_seed
        )
    if kind == "partition_matrix_inversion":
        return evaluate_partition_matrix_inversion_bijection(
            functions["forward"], functions["inverse"], target_terms, order_seed
        )
    raise ValueError(f"unknown numerical evaluation kind: {kind}")


def _numerical_worker(
    kind, source, problem_dir, target_terms, timeout_seconds, max_process_bytes, connection
) -> None:
    try:
        _install_process_limits(
            timeout_seconds=timeout_seconds, max_process_bytes=max_process_bytes
        )
        _install_submission_audit_hook(
            problem_dir=problem_dir if kind in _STATISTIC_KINDS else None
        )
        track_allocations = kind in _STATISTIC_KINDS
        if track_allocations:
            tracemalloc.start()
        functions = load_restricted_functions(source)
        configured_replay_seed = os.environ.get(_REPLAY_SEED_ENV)
        replay_seed = (
            int(configured_replay_seed)
            if configured_replay_seed is not None
            else _derived_run_seed("numerical-replay")
        )
        fingerprint_key = hashlib.sha256(
            f"qtbench-fingerprint:{replay_seed}".encode("ascii")
        ).digest()[:16]
        first_states: dict[str, dict[str, int]] = {}
        if kind in _STATISTIC_KINDS:
            statistic, first_states["statistic"] = _recording_statistic(
                functions["statistic"], kind, fingerprint_key, repeat=False
            )
            functions["statistic"] = statistic
        else:
            for name in ("forward", "inverse"):
                functions[name], first_states[name] = _recording_bijection(
                    functions[name], name, fingerprint_key, repeat=False
                )

        start = time.perf_counter()
        result = _evaluate_numerical(
            kind,
            functions,
            problem_dir=problem_dir,
            target_terms=target_terms,
        )
        determinism = None
        if result["passed"]:
            replay_functions = load_restricted_functions(source)
            replay_states: dict[str, dict[str, int]] = {}
            if kind in _STATISTIC_KINDS:
                replay_functions["statistic"], replay_states["statistic"] = (
                    _recording_statistic(
                        replay_functions["statistic"],
                        kind,
                        fingerprint_key,
                        repeat=True,
                    )
                )
            else:
                for name in ("forward", "inverse"):
                    replay_functions[name], replay_states[name] = _recording_bijection(
                        replay_functions[name], name, fingerprint_key, repeat=True
                    )
            replay_result = _evaluate_numerical(
                kind,
                replay_functions,
                problem_dir=problem_dir,
                target_terms=target_terms,
                order_seed=replay_seed,
            )
            if not replay_result["passed"]:
                raise _DeterminismViolation(
                    "fresh shuffled replay no longer matches the public target"
                )
            if replay_states != first_states:
                raise _DeterminismViolation(
                    "object-to-output assignment changed in a fresh shuffled replay"
                )
            determinism = DeterminismReport(
                checked_objects=sum(state["count"] for state in first_states.values()),
                replayed_calls=2 * sum(
                    state["count"] for state in replay_states.values()
                ),
                fresh_namespaces=2,
                replay_seed=replay_seed,
            )

        elapsed = time.perf_counter() - start
        peak = tracemalloc.get_traced_memory()[1] if track_allocations else None
        _send_to_parent(connection, ("ok", elapsed, peak, result, determinism))
    except _DeterminismViolation as error:
        _send_to_parent(
            connection,
            (
                "determinism",
                f"{error}; diagnostic replay seed {replay_seed} "
                "(the official scored CLI intentionally ignores seed overrides)",
            ),
        )
    except BaseException as error:  # noqa: BLE001 - reported to the parent
        _send_to_parent(connection, ("error", type(error).__name__, str(error)))
    finally:
        connection.close()


def _run_numerical_isolated(
    *, kind, source, problem_dir=None, target_terms=None, timeout_seconds, max_python_bytes, max_process_bytes
) -> tuple[dict[str, Any], DeterminismReport | None, float, int | None]:
    payload = _run_isolated(
        _numerical_worker,
        (kind, source, problem_dir, target_terms, timeout_seconds, max_process_bytes),
        timeout_seconds=timeout_seconds,
        max_process_bytes=max_process_bytes,
        label="numerical evaluation",
    )
    if payload[0] == "determinism":
        raise ResourceGateError(f"determinism gate rejected the submission: {payload[1]}")
    if payload[0] != "ok":
        raise ResourceGateError(f"numerical evaluation raised {payload[1]}: {payload[2]}")
    _, elapsed, peak, result, determinism = payload
    if peak is not None and peak > max_python_bytes:
        raise ResourceGateError(
            f"numerical evaluation allocated {peak} Python bytes, limit is {max_python_bytes}"
        )
    return result, determinism, elapsed, peak


# ---------------------------------------------------------------------------
# Area/bounce identity gate (large-object correctness for bijections)
# ---------------------------------------------------------------------------


def _identity_worker(source, paths, timeout_seconds, max_process_bytes, connection) -> None:
    try:
        _install_process_limits(
            timeout_seconds=timeout_seconds, max_process_bytes=max_process_bytes
        )
        _install_submission_audit_hook()
        tracemalloc.start()
        functions = load_restricted_functions(source)
        forward = functions["forward"]
        inverse = functions["inverse"]
        start = time.perf_counter()
        for path in paths:
            image = forward(path)
            preimage = inverse(path)
            if not isinstance(image, str) or not is_dyck_path(image) or len(image) != len(path):
                _send_to_parent(connection, ("fail", f"forward produced an invalid path for size {len(path) // 2}"))
                return
            if not isinstance(preimage, str) or not is_dyck_path(preimage) or len(preimage) != len(path):
                _send_to_parent(connection, ("fail", f"inverse produced an invalid path for size {len(path) // 2}"))
                return
            if inverse(image) != path or forward(preimage) != path:
                _send_to_parent(connection, ("fail", f"round-trip failed for size {len(path) // 2}"))
                return
            if dyck_area(path) != dyck_bounce(image) or dyck_bounce(path) != dyck_area(image):
                _send_to_parent(connection, ("fail", f"area/bounce exchange failed for size {len(path) // 2}"))
                return
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        _send_to_parent(connection, ("ok", elapsed, peak))
    except BaseException as error:  # noqa: BLE001 - reported to the parent
        _send_to_parent(connection, ("error", type(error).__name__, str(error)))
    finally:
        connection.close()


def run_area_bounce_identity_gate(
    source: str,
    paths: Sequence[str],
    *,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
) -> IdentityReport:
    """Check both area/bounce identities pointwise on large paths under limits.

    The identities are self-checking, so this verifies large-object correctness
    with no target: an enumeration cheat exceeds the resource limits, and any
    other wrong image fails an identity.
    """

    _validate_byte_limit(max_python_bytes, "max_python_bytes")
    payload = _run_isolated(
        _identity_worker,
        (source, list(paths), timeout_seconds, max_process_bytes),
        timeout_seconds=timeout_seconds,
        max_process_bytes=max_process_bytes,
        label="identity gate",
    )
    if payload[0] == "fail":
        raise ResourceGateError(f"identity gate rejected the submission: {payload[1]}")
    if payload[0] != "ok":
        raise ResourceGateError(f"identity gate raised {payload[1]}: {payload[2]}")
    _, elapsed, peak = payload
    if peak > max_python_bytes:
        raise ResourceGateError(
            f"identity gate allocated {peak} Python bytes, limit is {max_python_bytes}"
        )
    return IdentityReport(elapsed_seconds=elapsed, peak_python_bytes=peak, checked_paths=len(paths))


def _polyomino_identity_worker(source, polyominoes, timeout_seconds, max_process_bytes, connection) -> None:
    try:
        _install_process_limits(
            timeout_seconds=timeout_seconds, max_process_bytes=max_process_bytes
        )
        _install_submission_audit_hook()
        tracemalloc.start()
        functions = load_restricted_functions(source)
        forward = functions["forward"]
        inverse = functions["inverse"]
        start = time.perf_counter()
        for polyomino in polyominoes:
            image = forward(polyomino)
            preimage = inverse(polyomino)
            box = polyomino_dimensions(polyomino)
            if (
                not isinstance(image, str)
                or not is_parallelogram_polyomino(image)
                or polyomino_dimensions(image) != box
            ):
                _send_to_parent(connection, ("fail", f"forward produced an invalid polyomino for box {box}"))
                return
            if (
                not isinstance(preimage, str)
                or not is_parallelogram_polyomino(preimage)
                or polyomino_dimensions(preimage) != box
            ):
                _send_to_parent(connection, ("fail", f"inverse produced an invalid polyomino for box {box}"))
                return
            if inverse(image) != polyomino or forward(preimage) != polyomino:
                _send_to_parent(connection, ("fail", f"round-trip failed for box {box}"))
                return
            if polyomino_area(polyomino) != polyomino_bounce(image) or polyomino_bounce(
                polyomino
            ) != polyomino_area(image):
                _send_to_parent(connection, ("fail", f"area/bounce exchange failed for box {box}"))
                return
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        _send_to_parent(connection, ("ok", elapsed, peak))
    except BaseException as error:  # noqa: BLE001 - reported to the parent
        _send_to_parent(connection, ("error", type(error).__name__, str(error)))
    finally:
        connection.close()


def run_polyomino_area_bounce_identity_gate(
    source: str,
    polyominoes: Sequence[str],
    *,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
) -> IdentityReport:
    """Check both area/bounce identities pointwise on large polyominoes.

    The identities are self-checking, so this verifies large-object correctness
    with no target: an enumeration cheat exceeds the resource limits, and any
    other wrong image fails an identity.
    """

    _validate_byte_limit(max_python_bytes, "max_python_bytes")
    payload = _run_isolated(
        _polyomino_identity_worker,
        (source, list(polyominoes), timeout_seconds, max_process_bytes),
        timeout_seconds=timeout_seconds,
        max_process_bytes=max_process_bytes,
        label="identity gate",
    )
    if payload[0] == "fail":
        raise ResourceGateError(f"identity gate rejected the submission: {payload[1]}")
    if payload[0] != "ok":
        raise ResourceGateError(f"identity gate raised {payload[1]}: {payload[2]}")
    _, elapsed, peak = payload
    if peak > max_python_bytes:
        raise ResourceGateError(
            f"identity gate allocated {peak} Python bytes, limit is {max_python_bytes}"
        )
    return IdentityReport(
        elapsed_seconds=elapsed, peak_python_bytes=peak, checked_paths=len(polyominoes)
    )


def _polyomino_transpose_identity_worker(source, polyominoes, timeout_seconds, max_process_bytes, connection) -> None:
    try:
        _install_process_limits(
            timeout_seconds=timeout_seconds, max_process_bytes=max_process_bytes
        )
        _install_submission_audit_hook()
        tracemalloc.start()
        functions = load_restricted_functions(source)
        forward = functions["forward"]
        inverse = functions["inverse"]
        start = time.perf_counter()
        for polyomino in polyominoes:
            image = forward(polyomino)
            preimage = inverse(polyomino)
            m, n = polyomino_dimensions(polyomino)
            transposed = (n, m)
            if (
                not isinstance(image, str)
                or not is_parallelogram_polyomino(image)
                or polyomino_dimensions(image) != transposed
            ):
                _send_to_parent(connection, ("fail", f"forward produced an invalid polyomino for box ({m},{n})"))
                return
            if (
                not isinstance(preimage, str)
                or not is_parallelogram_polyomino(preimage)
                or polyomino_dimensions(preimage) != transposed
            ):
                _send_to_parent(connection, ("fail", f"inverse produced an invalid polyomino for box ({m},{n})"))
                return
            if inverse(image) != polyomino or forward(preimage) != polyomino:
                _send_to_parent(connection, ("fail", f"round-trip failed for box ({m},{n})"))
                return
            if polyomino_area(image) != polyomino_area(polyomino) or polyomino_bounce(
                image
            ) != polyomino_bounce(polyomino):
                _send_to_parent(connection, ("fail", f"area/bounce not preserved for box ({m},{n})"))
                return
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        _send_to_parent(connection, ("ok", elapsed, peak))
    except BaseException as error:  # noqa: BLE001 - reported to the parent
        _send_to_parent(connection, ("error", type(error).__name__, str(error)))
    finally:
        connection.close()


def run_polyomino_transpose_identity_gate(
    source: str,
    polyominoes: Sequence[str],
    *,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
) -> IdentityReport:
    """Check the transpose identities pointwise on large polyominoes.

    The identities (same box transposed, area and bounce preserved, mutually
    inverse) are self-checking, so this verifies large-object correctness with no
    target: an enumeration cheat exceeds the resource limits, and any other wrong
    image fails an identity.
    """

    _validate_byte_limit(max_python_bytes, "max_python_bytes")
    payload = _run_isolated(
        _polyomino_transpose_identity_worker,
        (source, list(polyominoes), timeout_seconds, max_process_bytes),
        timeout_seconds=timeout_seconds,
        max_process_bytes=max_process_bytes,
        label="identity gate",
    )
    if payload[0] == "fail":
        raise ResourceGateError(f"identity gate rejected the submission: {payload[1]}")
    if payload[0] != "ok":
        raise ResourceGateError(f"identity gate raised {payload[1]}: {payload[2]}")
    _, elapsed, peak = payload
    if peak > max_python_bytes:
        raise ResourceGateError(
            f"identity gate allocated {peak} Python bytes, limit is {max_python_bytes}"
        )
    return IdentityReport(
        elapsed_seconds=elapsed, peak_python_bytes=peak, checked_paths=len(polyominoes)
    )


def _macdonald_filling_identity_worker(
    source, fillings, timeout_seconds, max_process_bytes, connection
) -> None:
    try:
        _install_process_limits(timeout_seconds=timeout_seconds, max_process_bytes=max_process_bytes)
        _install_submission_audit_hook()
        tracemalloc.start()
        functions = load_restricted_functions(source)
        forward = functions["forward"]
        inverse = functions["inverse"]
        start = time.perf_counter()
        for filling in fillings:
            image_encoding = forward(filling)
            preimage_encoding = inverse(filling)
            if not is_standard_macdonald_filling(image_encoding):
                _send_to_parent(connection, ("fail", f"forward produced an invalid filling at size {filling.n}"))
                return
            if not is_standard_macdonald_filling(preimage_encoding):
                _send_to_parent(connection, ("fail", f"inverse produced an invalid filling at size {filling.n}"))
                return
            image = StandardMacdonaldFilling(image_encoding, validate=False)
            preimage = StandardMacdonaldFilling(preimage_encoding, validate=False)
            if image.shape != filling.conjugate_shape or preimage.shape != filling.conjugate_shape:
                _send_to_parent(connection, ("fail", f"image shape was not conjugated at size {filling.n}"))
                return
            round_trip = inverse(image)
            reverse_round_trip = forward(preimage)
            if not (
                is_standard_macdonald_filling(round_trip)
                and is_standard_macdonald_filling(reverse_round_trip)
            ):
                _send_to_parent(
                    connection,
                    ("fail", f"round-trip produced an invalid filling at size {filling.n}"),
                )
                return
            if round_trip != filling.encoding or reverse_round_trip != filling.encoding:
                _send_to_parent(connection, ("fail", f"round-trip failed at size {filling.n}"))
                return
            if filling.inv() != image.maj() or filling.maj() != image.inv():
                _send_to_parent(connection, ("fail", f"inv/maj exchange failed at size {filling.n}"))
                return
            if filling.inv() != preimage.maj() or filling.maj() != preimage.inv():
                _send_to_parent(connection, ("fail", f"inverse inv/maj exchange failed at size {filling.n}"))
                return
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        _send_to_parent(connection, ("ok", elapsed, peak))
    except BaseException as error:  # noqa: BLE001 - reported to the parent
        _send_to_parent(connection, ("error", type(error).__name__, str(error)))
    finally:
        connection.close()


def run_macdonald_filling_identity_gate(
    source: str,
    fillings: Sequence[StandardMacdonaldFilling],
    *,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
) -> IdentityReport:
    _validate_byte_limit(max_python_bytes, "max_python_bytes")
    payload = _run_isolated(
        _macdonald_filling_identity_worker,
        (source, list(fillings), timeout_seconds, max_process_bytes),
        timeout_seconds=timeout_seconds,
        max_process_bytes=max_process_bytes,
        label="identity gate",
    )
    if payload[0] == "fail":
        raise ResourceGateError(f"identity gate rejected the submission: {payload[1]}")
    if payload[0] != "ok":
        raise ResourceGateError(f"identity gate raised {payload[1]}: {payload[2]}")
    _, elapsed, peak = payload
    if peak > max_python_bytes:
        raise ResourceGateError(
            f"identity gate allocated {peak} Python bytes, limit is {max_python_bytes}"
        )
    return IdentityReport(elapsed_seconds=elapsed, peak_python_bytes=peak, checked_paths=len(fillings))


def _parking_area_dinv_identity_worker(
    source, parking_functions, timeout_seconds, max_process_bytes, connection
) -> None:
    try:
        _install_process_limits(timeout_seconds=timeout_seconds, max_process_bytes=max_process_bytes)
        _install_submission_audit_hook()
        tracemalloc.start()
        functions = load_restricted_functions(source)
        forward = functions["forward"]
        inverse = functions["inverse"]
        start = time.perf_counter()
        for parking in parking_functions:
            image_encoding = forward(parking)
            preimage_encoding = inverse(parking)
            if not is_parking_function_word(image_encoding):
                _send_to_parent(connection, ("fail", f"forward produced an invalid parking function at size {parking.n}"))
                return
            if not is_parking_function_word(preimage_encoding):
                _send_to_parent(connection, ("fail", f"inverse produced an invalid parking function at size {parking.n}"))
                return
            image = ParkingFunction(image_encoding, validate=False)
            preimage = ParkingFunction(preimage_encoding, validate=False)
            if image.n != parking.n or preimage.n != parking.n:
                _send_to_parent(connection, ("fail", f"image changed size {parking.n}"))
                return
            round_trip = inverse(image)
            reverse_round_trip = forward(preimage)
            if not (
                is_parking_function_word(round_trip)
                and is_parking_function_word(reverse_round_trip)
            ):
                _send_to_parent(
                    connection,
                    (
                        "fail",
                        f"round-trip produced an invalid parking function at size {parking.n}",
                    ),
                )
                return
            if round_trip != parking.encoding or reverse_round_trip != parking.encoding:
                _send_to_parent(connection, ("fail", f"round-trip failed at size {parking.n}"))
                return
            if parking.area() != image.dinv() or parking.dinv() != image.area():
                _send_to_parent(connection, ("fail", f"area/dinv exchange failed at size {parking.n}"))
                return
            if parking.area() != preimage.dinv() or parking.dinv() != preimage.area():
                _send_to_parent(connection, ("fail", f"inverse area/dinv exchange failed at size {parking.n}"))
                return
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        _send_to_parent(connection, ("ok", elapsed, peak))
    except BaseException as error:  # noqa: BLE001 - reported to the parent
        _send_to_parent(connection, ("error", type(error).__name__, str(error)))
    finally:
        connection.close()


def run_parking_area_dinv_identity_gate(
    source: str,
    parking_functions: Sequence[ParkingFunction],
    *,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
) -> IdentityReport:
    _validate_byte_limit(max_python_bytes, "max_python_bytes")
    payload = _run_isolated(
        _parking_area_dinv_identity_worker,
        (source, list(parking_functions), timeout_seconds, max_process_bytes),
        timeout_seconds=timeout_seconds,
        max_process_bytes=max_process_bytes,
        label="identity gate",
    )
    if payload[0] == "fail":
        raise ResourceGateError(f"identity gate rejected the submission: {payload[1]}")
    if payload[0] != "ok":
        raise ResourceGateError(f"identity gate raised {payload[1]}: {payload[2]}")
    _, elapsed, peak = payload
    if peak > max_python_bytes:
        raise ResourceGateError(
            f"identity gate allocated {peak} Python bytes, limit is {max_python_bytes}"
        )
    return IdentityReport(
        elapsed_seconds=elapsed, peak_python_bytes=peak, checked_paths=len(parking_functions)
    )


def _graph_sibling_tuft_identity_worker(
    source, graphs, timeout_seconds, max_process_bytes, connection
) -> None:
    try:
        _install_process_limits(timeout_seconds=timeout_seconds, max_process_bytes=max_process_bytes)
        _install_submission_audit_hook()
        tracemalloc.start()
        functions = load_restricted_functions(source)
        forward = functions["forward"]
        inverse = functions["inverse"]
        start = time.perf_counter()
        by_encoding = {graph.encoding: graph for graph in graphs}
        forced_images: dict[str, str] = {}
        for graph in graphs:
            edge_count = graph.n * (graph.n - 1) // 2
            width = max(1, (edge_count + 3) // 4)
            star = f"{graph.n}:{((1 << (graph.n - 1)) - 1):0{width}x}"
            complete = f"{graph.n}:{((1 << edge_count) - 1):0{width}x}"
            if graph.encoding == star:
                forced_images[star] = complete
            if graph.encoding == complete:
                forced_images[complete] = star
        for graph in graphs:
            image_encoding = forward(graph)
            preimage_encoding = inverse(graph)
            forced_image = forced_images.get(graph.encoding)
            if forced_image is not None:
                if image_encoding != forced_image or preimage_encoding != forced_image:
                    _send_to_parent(connection, ("fail", f"sibling/tuft exchange failed at size {graph.n}"))
                    return
                image = by_encoding.get(forced_image)
                if image is None:
                    image = ConnectedGraph(forced_image, validate=False)
                if inverse(image) != graph.encoding or forward(image) != graph.encoding:
                    _send_to_parent(connection, ("fail", f"round-trip failed at size {graph.n}"))
                    return
                # This exact pair proves reduction preservation without running
                # the general reduction: both reduce to K1 for n > 2, while
                # star and complete coincide for n <= 2.
                continue
            if not is_connected_graph_encoding(image_encoding):
                _send_to_parent(connection, ("fail", f"forward produced an invalid graph at size {graph.n}"))
                return
            if not is_connected_graph_encoding(preimage_encoding):
                _send_to_parent(connection, ("fail", f"inverse produced an invalid graph at size {graph.n}"))
                return
            image = ConnectedGraph(image_encoding, validate=False)
            preimage = ConnectedGraph(preimage_encoding, validate=False)
            if image.n != graph.n or preimage.n != graph.n:
                _send_to_parent(connection, ("fail", f"image changed graph size {graph.n}"))
                return
            round_trip = inverse(image)
            reverse_round_trip = forward(preimage)
            if not (
                isinstance(round_trip, str)
                and isinstance(reverse_round_trip, str)
            ):
                _send_to_parent(connection, ("fail", f"round-trip produced an invalid graph at size {graph.n}"))
                return
            # Equality to the trusted canonical input proves both round-trip
            # outputs canonical without repeating the factorial labeling check.
            if round_trip != graph.encoding or reverse_round_trip != graph.encoding:
                _send_to_parent(connection, ("fail", f"round-trip failed at size {graph.n}"))
                return
            if (
                graph.sibling_number() != image.tuft_number()
                or graph.tuft_number() != image.sibling_number()
            ):
                _send_to_parent(connection, ("fail", f"sibling/tuft exchange failed at size {graph.n}"))
                return
            if (
                graph.sibling_number() != preimage.tuft_number()
                or graph.tuft_number() != preimage.sibling_number()
            ):
                _send_to_parent(connection, ("fail", f"inverse sibling/tuft exchange failed at size {graph.n}"))
                return
            if image.reduction != graph.reduction or preimage.reduction != graph.reduction:
                _send_to_parent(connection, ("fail", f"graph reduction was not preserved at size {graph.n}"))
                return
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        _send_to_parent(connection, ("ok", elapsed, peak))
    except BaseException as error:  # noqa: BLE001 - reported to the parent
        _send_to_parent(connection, ("error", type(error).__name__, str(error)))
    finally:
        connection.close()


def run_graph_sibling_tuft_identity_gate(
    source: str,
    graphs: Sequence[ConnectedGraph],
    *,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
) -> IdentityReport:
    _validate_byte_limit(max_python_bytes, "max_python_bytes")
    payload = _run_isolated(
        _graph_sibling_tuft_identity_worker,
        (source, list(graphs), timeout_seconds, max_process_bytes),
        timeout_seconds=timeout_seconds,
        max_process_bytes=max_process_bytes,
        label="identity gate",
    )
    if payload[0] == "fail":
        raise ResourceGateError(f"identity gate rejected the submission: {payload[1]}")
    if payload[0] != "ok":
        raise ResourceGateError(f"identity gate raised {payload[1]}: {payload[2]}")
    _, elapsed, peak = payload
    if peak > max_python_bytes:
        raise ResourceGateError(
            f"identity gate allocated {peak} Python bytes, limit is {max_python_bytes}"
        )
    return IdentityReport(elapsed_seconds=elapsed, peak_python_bytes=peak, checked_paths=len(graphs))


def _shifted_pq_identity_worker(
    source, tableaux, timeout_seconds, max_process_bytes, connection
) -> None:
    try:
        _install_process_limits(timeout_seconds=timeout_seconds, max_process_bytes=max_process_bytes)
        _install_submission_audit_hook()
        tracemalloc.start()
        functions = load_restricted_functions(source)
        start = time.perf_counter()
        for tableau in tableaux:
            name = "forward" if tableau.side == "source" else "inverse"
            reverse_name = "inverse" if name == "forward" else "forward"
            output = functions[name](tableau)
            if not is_shifted_setvalued_tableau_encoding(output):
                _send_to_parent(connection, ("fail", f"{name} produced a noncanonical tableau"))
                return
            image = ShiftedSetValuedTableau(output, validate=False)
            expected_side = "target" if tableau.side == "source" else "source"
            if image.side != expected_side or image.mu != tableau.mu:
                _send_to_parent(connection, ("fail", f"{name} produced a wrong-side tableau"))
                return
            if image.content != tableau.content:
                _send_to_parent(connection, ("fail", f"{name} changed tableau content"))
                return
            round_trip = functions[reverse_name](image)
            if not isinstance(round_trip, str) or round_trip != tableau.encoding:
                _send_to_parent(connection, ("fail", f"{reverse_name}({name}(tableau)) failed"))
                return
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        _send_to_parent(connection, ("ok", elapsed, peak))
    except BaseException as error:  # noqa: BLE001 - reported to the parent
        _send_to_parent(connection, ("error", type(error).__name__, str(error)))
    finally:
        connection.close()


def run_shifted_pq_identity_gate(
    source: str,
    tableaux: Sequence[ShiftedSetValuedTableau],
    *,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
) -> IdentityReport:
    _validate_byte_limit(max_python_bytes, "max_python_bytes")
    payload = _run_isolated(
        _shifted_pq_identity_worker,
        (source, list(tableaux), timeout_seconds, max_process_bytes),
        timeout_seconds=timeout_seconds,
        max_process_bytes=max_process_bytes,
        label="identity gate",
    )
    if payload[0] == "fail":
        raise ResourceGateError(f"identity gate rejected the submission: {payload[1]}")
    if payload[0] != "ok":
        raise ResourceGateError(f"identity gate raised {payload[1]}: {payload[2]}")
    _, elapsed, peak = payload
    if peak > max_python_bytes:
        raise ResourceGateError(
            f"identity gate allocated {peak} Python bytes, limit is {max_python_bytes}"
        )
    return IdentityReport(
        elapsed_seconds=elapsed, peak_python_bytes=peak, checked_paths=len(tableaux)
    )


def _successive_rank_identity_worker(
    source, partitions, timeout_seconds, max_process_bytes, connection
) -> None:
    try:
        _install_process_limits(timeout_seconds=timeout_seconds, max_process_bytes=max_process_bytes)
        _install_submission_audit_hook()
        tracemalloc.start()
        functions = load_restricted_functions(source)
        start = time.perf_counter()
        for partition in partitions:
            name = "forward" if partition.side == "source" else "inverse"
            reverse_name = "inverse" if name == "forward" else "forward"
            output = functions[name](partition)
            if not is_successive_rank_partition_encoding(output):
                _send_to_parent(connection, ("fail", f"{name} produced a noncanonical partition"))
                return
            image = SuccessiveRankPartition(output, validate=False)
            expected_side = "target" if partition.side == "source" else "source"
            if (
                image.side != expected_side
                or image.modulus != partition.modulus
                or image.residue != partition.residue
            ):
                _send_to_parent(connection, ("fail", f"{name} produced a wrong-side partition"))
                return
            if image.weight != partition.weight:
                _send_to_parent(connection, ("fail", f"{name} changed partition weight"))
                return
            round_trip = functions[reverse_name](image)
            if not is_successive_rank_partition_encoding(round_trip) or round_trip != partition.encoding:
                _send_to_parent(connection, ("fail", f"{reverse_name}({name}(partition)) failed"))
                return
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        _send_to_parent(connection, ("ok", elapsed, peak))
    except BaseException as error:  # noqa: BLE001 - reported to the parent
        _send_to_parent(connection, ("error", type(error).__name__, str(error)))
    finally:
        connection.close()


def run_successive_rank_identity_gate(
    source: str,
    partitions: Sequence[SuccessiveRankPartition],
    *,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
) -> IdentityReport:
    _validate_byte_limit(max_python_bytes, "max_python_bytes")
    payload = _run_isolated(
        _successive_rank_identity_worker,
        (source, list(partitions), timeout_seconds, max_process_bytes),
        timeout_seconds=timeout_seconds,
        max_process_bytes=max_process_bytes,
        label="identity gate",
    )
    if payload[0] == "fail":
        raise ResourceGateError(f"identity gate rejected the submission: {payload[1]}")
    if payload[0] != "ok":
        raise ResourceGateError(f"identity gate raised {payload[1]}: {payload[2]}")
    _, elapsed, peak = payload
    if peak > max_python_bytes:
        raise ResourceGateError(
            f"identity gate allocated {peak} Python bytes, limit is {max_python_bytes}"
        )
    return IdentityReport(
        elapsed_seconds=elapsed, peak_python_bytes=peak, checked_paths=len(partitions)
    )


def _partition_matrix_inversion_identity_worker(
    source, objects, timeout_seconds, max_process_bytes, connection
) -> None:
    try:
        _install_process_limits(timeout_seconds=timeout_seconds, max_process_bytes=max_process_bytes)
        _install_submission_audit_hook()
        tracemalloc.start()
        functions = load_restricted_functions(source)
        start = time.perf_counter()
        for obj in objects:
            name = "forward" if obj.side == "source" else "inverse"
            reverse_name = "inverse" if name == "forward" else "forward"
            output = functions[name](obj)
            if not is_partition_matrix_inversion_encoding(output):
                _send_to_parent(connection, ("fail", f"{name} produced a noncanonical object"))
                return
            image = PartitionMatrixInversion(output, validate=False)
            expected_side = "target" if obj.side == "source" else "source"
            if image.side != expected_side or image.n != obj.n:
                _send_to_parent(connection, ("fail", f"{name} produced a wrong-side object"))
                return
            if image.grading != obj.grading:
                _send_to_parent(connection, ("fail", f"{name} changed the grading"))
                return
            round_trip = functions[reverse_name](image)
            if not is_partition_matrix_inversion_encoding(round_trip) or round_trip != obj.encoding:
                _send_to_parent(connection, ("fail", f"{reverse_name}({name}(object)) failed"))
                return
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        _send_to_parent(connection, ("ok", elapsed, peak))
    except BaseException as error:  # noqa: BLE001 - reported to the parent
        _send_to_parent(connection, ("error", type(error).__name__, str(error)))
    finally:
        connection.close()


def run_partition_matrix_inversion_identity_gate(
    source: str,
    objects: Sequence[PartitionMatrixInversion],
    *,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
) -> IdentityReport:
    _validate_byte_limit(max_python_bytes, "max_python_bytes")
    payload = _run_isolated(
        _partition_matrix_inversion_identity_worker,
        (source, list(objects), timeout_seconds, max_process_bytes),
        timeout_seconds=timeout_seconds,
        max_process_bytes=max_process_bytes,
        label="identity gate",
    )
    if payload[0] == "fail":
        raise ResourceGateError(f"identity gate rejected the submission: {payload[1]}")
    if payload[0] != "ok":
        raise ResourceGateError(f"identity gate raised {payload[1]}: {payload[2]}")
    _, elapsed, peak = payload
    if peak > max_python_bytes:
        raise ResourceGateError(
            f"identity gate allocated {peak} Python bytes, limit is {max_python_bytes}"
        )
    return IdentityReport(elapsed_seconds=elapsed, peak_python_bytes=peak, checked_paths=len(objects))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def _base_result(function_names: Sequence[str]) -> dict[str, Any]:
    return {
        "passed": False,
        "checker_stage": "numerical",
        "checker_version": CHECKER_VERSION,
        "run_seed": _configured_run_seed(),
        "function_names": tuple(function_names),
        "numerical": None,
        "determinism": None,
        "resources": None,
    }


def _require_json_available_integer(value: int, description: Any) -> None:
    """Reject an integer the official JSON encoder cannot render."""

    try:
        str(value)
    except ValueError as error:
        raise ResourceGateError(
            "resource probe returned a nonnegative integer that exceeds the "
            "runtime's integer-to-decimal digit limit for official JSON output "
            f"for {description}"
        ) from error


def _validate_integer_probe_results(
    report: ResourceReport,
    calls: Sequence[tuple[str, tuple[Any, ...]]],
) -> None:
    for result, (_name, arguments) in zip(report.results, calls, strict=True):
        description = getattr(arguments[0], "encoding", arguments[0]) if arguments else None
        if type(result) is not int or result < 0:
            raise ResourceGateError(
                "resource probe returned "
                f"{type(result).__name__}, expected a nonnegative integer "
                f"for {description}"
            )
        _require_json_available_integer(result, description)


def _validate_mjack_probe_results(
    report: ResourceReport,
    calls: Sequence[tuple[str, tuple[Any, ...]]],
) -> None:
    _validate_integer_probe_results(report, calls)
    for result, (_name, arguments) in zip(report.results, calls, strict=True):
        matching = arguments[0]
        if (result == 0) != matching.is_bipartite:
            raise ResourceGateError(
                "resource probe violated the Matchings-Jack zero locus: "
                f"mjack must be zero exactly on bipartite matchings; "
                f"got {result} for {matching.encoding}"
            )


def _validate_pair_probe_results(
    report: ResourceReport,
    calls: Sequence[tuple[str, tuple[Any, ...]]],
) -> None:
    for result, (_name, arguments) in zip(report.results, calls, strict=True):
        description = getattr(arguments[0], "encoding", arguments[0]) if arguments else None
        if (
            type(result) is not tuple
            or len(result) != 2
            or any(type(value) is not int or value < 0 for value in result)
        ):
            raise ResourceGateError(
                "resource probe returned "
                f"{type(result).__name__}, expected a pair of nonnegative "
                f"integers for {description}"
            )
        for value in result:
            _require_json_available_integer(value, description)


def _validate_composition_probe_results(
    report: ResourceReport,
    calls: Sequence[tuple[str, tuple[Any, ...]]],
) -> None:
    for result, (_name, arguments) in zip(report.results, calls, strict=True):
        obj = arguments[0]
        try:
            _normalize_composition(result, obj.n)
        except (TypeError, ValueError) as error:
            raise ResourceGateError(
                f"resource probe returned an invalid composition for {obj.encoding}"
            ) from error


def evaluate_noncrossing_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(partition)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="noncrossing",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="noncrossing")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_type_b_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 10.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(path)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="type_b",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="type_b")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_lpp_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 30.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(polyomino)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="lpp",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="lpp")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_ddyck_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(path)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="ddyck",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="ddyck")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_lrp_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(path)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="lrp",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="lrp")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_mld_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(path)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="mld",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="mld")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_tamari_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(pair)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="tamari",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="tamari")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_ttree_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(tree)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="ttree",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="ttree")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_gpf_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    return _evaluate_gamma_parking_submission(
        kind="gpf",
        source=source,
        probes=probes,
        problem_dir=problem_dir,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
        numerical_timeout_seconds=numerical_timeout_seconds,
        limits=limits,
    )


def evaluate_lgpf_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    return _evaluate_gamma_parking_submission(
        kind="lgpf",
        source=source,
        probes=probes,
        problem_dir=problem_dir,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
        numerical_timeout_seconds=numerical_timeout_seconds,
        limits=limits,
    )


def _evaluate_gamma_parking_submission(
    *,
    kind: str,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int,
    numerical_timeout_seconds: float,
    limits: SourceLimits,
) -> dict[str, Any]:
    """Shared body of the two selected-area gamma-parking-function problems."""
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(selection)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind=kind,
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind=kind)
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_rtt_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(tree)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="rtt",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="rtt")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_tgt_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(tree)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="tgt",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="tgt")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_kostka_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(tableau)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="kostka",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="kostka")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_pair_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_uig_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(graph_permutation)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="uig",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="uig")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_composition_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_llt_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(graph_tableau)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="llt",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="llt")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_kreweras_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(partition)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="kreweras",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="kreweras")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_promotion_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(tableau)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="promotion",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="promotion")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_qgamma_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(permutation)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="qgamma",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="qgamma")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_mjack_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(jack_matching)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="mjack",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="mjack")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_mjack_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_involution_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(involution)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="involution",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="involution")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_asm_q_submission(
    *,
    source: str,
    probes,
    problem_dir,
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 60.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "statistic" not in function_names:
        raise GateError("submission must define statistic(matrix)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="asm-q",
        source=source,
        problem_dir=problem_dir,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    resource_calls = _hardened_probes(_resolve(probes), kind="asm-q")
    resources = run_resource_gate(
        source,
        resource_calls,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    _validate_integer_probe_results(resources, resource_calls)
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": resources,
    }


def evaluate_area_bounce_submission(
    *,
    source: str,
    probes,
    target_terms: Mapping[int, Sequence[Sequence[int]]],
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 10.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "forward" not in function_names or "inverse" not in function_names:
        raise GateError("submission must define forward(path) and inverse(path)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="area_bounce",
        source=source,
        target_terms=target_terms,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    probe_paths = [arguments[0] for _, arguments in _resolve(probes) if arguments]
    identities = run_area_bounce_identity_gate(
        source,
        _hardened_dyck_paths(probe_paths),
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": identities,
    }


def evaluate_polyomino_area_bounce_submission(
    *,
    source: str,
    probes,
    target_terms: Mapping[tuple[int, int], Sequence[Sequence[int]]],
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 10.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "forward" not in function_names or "inverse" not in function_names:
        raise GateError("submission must define forward(polyomino) and inverse(polyomino)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="polyomino_area_bounce",
        source=source,
        target_terms=target_terms,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    probe_polyominoes = [arguments[0] for _, arguments in _resolve(probes) if arguments]
    identities = run_polyomino_area_bounce_identity_gate(
        source,
        _hardened_polyominoes(probe_polyominoes),
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": identities,
    }


def evaluate_polyomino_transpose_submission(
    *,
    source: str,
    probes,
    target_terms: Mapping[tuple[int, int], Sequence[Sequence[int]]],
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 10.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "forward" not in function_names or "inverse" not in function_names:
        raise GateError("submission must define forward(polyomino) and inverse(polyomino)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="polyomino_transpose",
        source=source,
        target_terms=target_terms,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    probe_polyominoes = [arguments[0] for _, arguments in _resolve(probes) if arguments]
    identities = run_polyomino_transpose_identity_gate(
        source,
        _hardened_polyominoes(probe_polyominoes),
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": identities,
    }


def evaluate_macdonald_filling_submission(
    *,
    source: str,
    probes,
    target_terms: Mapping[tuple[int, ...], Sequence[Sequence[int]]],
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 20.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "forward" not in function_names or "inverse" not in function_names:
        raise GateError("submission must define forward(filling) and inverse(filling)")
    check_source_economy(source, limits=limits)

    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="macdonald_fillings",
        source=source,
        target_terms=target_terms,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result

    probe_fillings = [arguments[0] for _, arguments in _resolve(probes) if arguments]
    identities = run_macdonald_filling_identity_gate(
        source,
        _hardened_macdonald_fillings(probe_fillings),
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": identities,
    }


def evaluate_parking_area_dinv_submission(
    *,
    source: str,
    probes,
    target_terms: Mapping[int, Sequence[Sequence[int]]],
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 20.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "forward" not in function_names or "inverse" not in function_names:
        raise GateError("submission must define forward(parking) and inverse(parking)")
    check_source_economy(source, limits=limits)
    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="parking_area_dinv",
        source=source,
        target_terms=target_terms,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result
    probe_parking = [arguments[0] for _, arguments in _resolve(probes) if arguments]
    identities = run_parking_area_dinv_identity_gate(
        source,
        _hardened_parking_functions(probe_parking),
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": identities,
    }


def evaluate_graph_sibling_tuft_submission(
    *,
    source: str,
    probes,
    target_terms: Mapping[int, Mapping[str, Any]],
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 20.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "forward" not in function_names or "inverse" not in function_names:
        raise GateError("submission must define forward(graph) and inverse(graph)")
    check_source_economy(source, limits=limits)
    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="graph_sibling_tuft",
        source=source,
        target_terms=target_terms,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result
    probe_graphs = [arguments[0] for _, arguments in _resolve(probes) if arguments]
    identities = run_graph_sibling_tuft_identity_gate(
        source,
        _hardened_connected_graphs(probe_graphs),
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": identities,
    }


def evaluate_shifted_pq_submission(
    *,
    source: str,
    probes,
    target_terms: Mapping[str, Mapping[str, Any]],
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 20.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "forward" not in function_names or "inverse" not in function_names:
        raise GateError("submission must define forward(tableau) and inverse(tableau)")
    check_source_economy(source, limits=limits)
    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="shifted_pq",
        source=source,
        target_terms=target_terms,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result
    supplied = [arguments[0] for _, arguments in _resolve(probes) if arguments]
    hardened = _hardened_shifted_pq_tableaux(supplied)
    identities = run_shifted_pq_identity_gate(
        source,
        hardened,
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": identities,
    }


def evaluate_successive_rank_submission(
    *,
    source: str,
    probes,
    target_terms: Mapping[str, Mapping[str, Any]],
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 20.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "forward" not in function_names or "inverse" not in function_names:
        raise GateError("submission must define forward(partition) and inverse(partition)")
    check_source_economy(source, limits=limits)
    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="successive_rank",
        source=source,
        target_terms=target_terms,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result
    supplied = [arguments[0] for _, arguments in _resolve(probes) if arguments]
    max_size = max((partition.weight for partition in supplied), default=4)
    sizes = sorted({max(4, max_size // 4), max(4, max_size // 2), max(4, max_size)})
    hardened = [
        partition
        for size in sizes
        for partition in adversarial_successive_rank_partitions(size)
    ]
    identities = run_successive_rank_identity_gate(
        source,
        [*supplied, *hardened],
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": identities,
    }


def evaluate_partition_matrix_inversion_submission(
    *,
    source: str,
    probes,
    target_terms: Mapping[int, Mapping[str, Any]],
    timeout_seconds: float,
    max_python_bytes: int,
    max_process_bytes: int = 256_000_000,
    numerical_timeout_seconds: float = 20.0,
    limits: SourceLimits = SourceLimits(),
) -> dict[str, Any]:
    function_names = check_capability_screen(source)
    if "forward" not in function_names or "inverse" not in function_names:
        raise GateError("submission must define forward(object) and inverse(object)")
    check_source_economy(source, limits=limits)
    numerical, determinism, elapsed, peak = _run_numerical_isolated(
        kind="partition_matrix_inversion",
        source=source,
        target_terms=target_terms,
        timeout_seconds=numerical_timeout_seconds,
        max_python_bytes=max_process_bytes,
        max_process_bytes=max_process_bytes,
    )
    result = _base_result(function_names)
    result["numerical"] = numerical
    result["determinism"] = determinism
    result["numerical_elapsed_seconds"] = elapsed
    result["numerical_peak_python_bytes"] = peak
    if not numerical["passed"]:
        return result
    supplied = [arguments[0] for _, arguments in _resolve(probes) if arguments]
    max_size = max((obj.n for obj in supplied), default=4)
    sizes = sorted({max(4, max_size // 4), max(4, max_size // 2), max(4, max_size)})
    hardened = [
        obj
        for size in sizes
        for obj in adversarial_partition_matrix_inversions(size)
    ]
    identities = run_partition_matrix_inversion_identity_gate(
        source,
        [*supplied, *hardened],
        timeout_seconds=timeout_seconds,
        max_python_bytes=max_python_bytes,
        max_process_bytes=max_process_bytes,
    )
    return {
        **result,
        "passed": True,
        "checker_stage": "complete",
        "resources": identities,
    }
