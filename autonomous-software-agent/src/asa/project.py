from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .utils import copytree


@dataclass
class ProjectPlan:
    kind: str
    test_commands: list[str]
    run_command: str | None = None


def detect_project(root: Path, job: dict) -> ProjectPlan:
    if job.get("test_commands"):
        return ProjectPlan(job.get("kind", "custom"), list(job["test_commands"]), job.get("run_command"))
    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or list(root.glob("*.py")):
        if (root / "tests").exists() or (root / "pytest.ini").exists():
            return ProjectPlan("python", ["python -m pytest -q"], job.get("run_command"))
        return ProjectPlan("python", ["python -m compileall -q ."], job.get("run_command"))
    if (root / "package.json").exists():
        try:
            package = json.loads((root / "package.json").read_text(encoding="utf-8"))
            scripts = package.get("scripts", {})
        except Exception:
            scripts = {}
        commands = []
        if "test" in scripts and scripts["test"].strip() not in {"", "echo \"Error: no test specified\" && exit 1"}:
            commands.append("npm test")
        if "build" in scripts:
            commands.append("npm run build")
        if not commands:
            commands.append("node --check " + next(iter([str(p.name) for p in root.glob("*.js")]), "index.js"))
        return ProjectPlan("node", commands, job.get("run_command"))
    if list(root.glob("*.html")):
        return ProjectPlan("static-web", [], job.get("run_command"))
    return ProjectPlan("unknown", [], job.get("run_command"))


def acquire_source(job: dict, original_dir: Path) -> None:
    if original_dir.exists():
        shutil.rmtree(original_dir)
    source = job.get("source") or {}
    source_type = source.get("type", "local")
    if source_type == "local":
        src = Path(source["path"]).expanduser().resolve()
        copytree(src, original_dir)
        return
    if source_type == "github":
        url = source["url"]
        branch = source.get("branch")
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd += ["--branch", branch]
        cmd += [url, str(original_dir)]
        subprocess.run(cmd, check=True, text=True, capture_output=True)
        git_dir = original_dir / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)
        return
    raise ValueError(f"Unsupported source type: {source_type}")
