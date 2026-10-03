from __future__ import annotations

from pathlib import Path
import shutil
import sys
import tempfile

import pytest


INFERENCE_ROOT = Path(__file__).resolve().parents[1]
if str(INFERENCE_ROOT) not in sys.path:
    sys.path.insert(0, str(INFERENCE_ROOT))


@pytest.fixture
def private_tmp_path():
    base = Path.home() / ".qtbench-inference-unit-tests"
    base.mkdir(mode=0o700, exist_ok=True)
    base.chmod(0o700)
    path = Path(tempfile.mkdtemp(prefix="case-", dir=base))
    try:
        yield path
    finally:
        shutil.rmtree(path)
