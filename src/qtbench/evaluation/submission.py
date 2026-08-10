from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path

from qtbench.combinatorics import NoncrossingPartition


StatisticFunction = Callable[[NoncrossingPartition], int]


def load_statistic_function(path: str | Path, *, function_name: str = "statistic") -> StatisticFunction:
    """Load trusted Python in the caller's process without a sandbox or limits."""
    module_path = Path(path).resolve()
    if not module_path.exists():
        raise FileNotFoundError(module_path)

    spec = importlib.util.spec_from_file_location("qtbench_submission", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    previous_module = sys.modules.get(spec.name)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        candidate = getattr(module, function_name, None)
        if candidate is None or not callable(candidate):
            raise AttributeError(
                f"{module_path} must define callable {function_name}(partition)"
            )
    finally:
        if previous_module is None:
            sys.modules.pop(spec.name, None)
        else:
            sys.modules[spec.name] = previous_module
    return candidate
