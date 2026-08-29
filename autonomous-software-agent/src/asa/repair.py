from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import requests

from .utils import is_within


class RepairError(RuntimeError):
    pass


@dataclass
class RepairProposal:
    files: dict[str, str]
    reason: str = ""


class RepairBackend:
    def propose(self, prompt: str, project_root: Path, failures: list[dict], iteration: int) -> RepairProposal:
        raise NotImplementedError


class OllamaBackend(RepairBackend):
    def __init__(self, model: str = "qwen2.5-coder:7b", base_url: str = "http://127.0.0.1:11434", timeout: int = 180):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _collect_context(self, root: Path, max_chars: int = 50000) -> str:
        parts = []
        used = 0
        allowed = {".py", ".js", ".ts", ".html", ".css", ".json", ".toml", ".yaml", ".yml", ".ps1", ".bat", ".md", ".txt"}
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in allowed:
                continue
            if any(part in {".git", "node_modules", ".venv", "dist", "build"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            chunk = f"\n--- FILE: {path.relative_to(root)} ---\n{text}\n"
            if used + len(chunk) > max_chars:
                break
            parts.append(chunk)
            used += len(chunk)
        return "".join(parts)

    def propose(self, prompt: str, project_root: Path, failures: list[dict], iteration: int) -> RepairProposal:
        context = self._collect_context(project_root)
        user = f"""ITERATION {iteration}\nFAILURES:\n{json.dumps(failures, ensure_ascii=False, indent=2)}\n\nPROJECT FILES:{context}\n\nReturn ONLY JSON with this schema: {{\"reason\":\"...\",\"files\":{{\"relative/path.ext\":\"complete replacement content\"}}}}. Modify the minimum files necessary. Never use absolute paths."""
        payload = {"model": self.model, "stream": False, "format": "json", "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": user}]}
        response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json().get("message", {}).get("content", "{}")
        data = json.loads(raw)
        files = data.get("files") or {}
        if not isinstance(files, dict):
            raise RepairError("Backend returned invalid files mapping")
        return RepairProposal({str(k): str(v) for k, v in files.items()}, str(data.get("reason", "")))


class DeterministicSelfTestBackend(RepairBackend):
    def propose(self, prompt: str, project_root: Path, failures: list[dict], iteration: int) -> RepairProposal:
        target = project_root / "main.py"
        if target.exists():
            return RepairProposal({"main.py": "print('self-test-ok')\n"}, "Repair intentional syntax error")
        return RepairProposal({}, "No repair")


def apply_proposal(root: Path, proposal: RepairProposal) -> list[str]:
    changed = []
    for rel, content in proposal.files.items():
        target = (root / rel).resolve()
        if not is_within(target, root):
            raise RepairError(f"Rejected path outside workspace: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        changed.append(rel)
    return changed
