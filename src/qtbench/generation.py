"""Helpers for executing trusted public data-generation code."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import sys
from types import ModuleType


_MISSING = object()


def load_trusted_oracle(path: str | Path) -> ModuleType:
    """Load the oracle at exactly ``path``.

    Warning: the file is trusted and executes as arbitrary Python in the caller's
    process, without sandboxing or resource limits.
    """
    module_path = Path(path).resolve()
    if not module_path.is_file():
        raise FileNotFoundError(module_path)

    path_digest = hashlib.sha256(os.fsencode(module_path)).hexdigest()
    module_name = f"_qtbench_trusted_oracle_{path_digest}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load oracle from {module_path}")

    module = importlib.util.module_from_spec(spec)
    previous_module = sys.modules.get(module_name, _MISSING)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous_module is _MISSING:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module
    return module
