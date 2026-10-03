from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile

import pytest

from qtbench_inference.sandbox import find_codex, probe_sandbox


@pytest.mark.skipif(
    os.environ.get("QTBENCH_LIVE_SANDBOX_SMOKE") != "1",
    reason="set QTBENCH_LIVE_SANDBOX_SMOKE=1 for the no-network Codex sandbox probe",
)
def test_live_codex_sandbox_denies_outside_files_and_network() -> None:
    base = Path.home() / ".qtbench-inference-test"
    base.mkdir(mode=0o700, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="sandbox-", dir=base))
    try:
        workspace = root / "w"
        workspace.mkdir()
        denied = root / "outside.txt"
        denied.write_text("secret\n", encoding="utf-8")
        probe_sandbox(find_codex(), workspace, denied)
    finally:
        shutil.rmtree(root)
