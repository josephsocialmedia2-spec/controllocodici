from __future__ import annotations

import tempfile
from pathlib import Path

from .orchestrator import Orchestrator
from .repair import DeterministicSelfTestBackend


def run_self_test() -> bool:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); project = root / "broken"; project.mkdir()
        (project / "main.py").write_text("print('broken'\n", encoding="utf-8")
        job = {"name": "self-test", "type": "software", "source": {"type": "local", "path": str(project)}, "test_commands": ["python -m py_compile main.py"]}
        orchestrator = Orchestrator(root / "agent", DeterministicSelfTestBackend(), "self-test", max_iterations=2)
        report = orchestrator.process(job)
        return report.get("status") == "OK" and (Path(report["best"]) / "main.py").read_text(encoding="utf-8") == "print('self-test-ok')\n"
