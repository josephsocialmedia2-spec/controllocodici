from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .utils import is_within


class RepairError(RuntimeError):
    pass


@dataclass
class RepairProposal:
    files: dict[str, str]
    reason: str = ""
    requires_user_choice: bool = False
    choices: list[str] = field(default_factory=list)
    confidence: float = 1.0


class RepairBackend:
    def propose(self, prompt: str, project_root: Path, failures: list[dict], iteration: int) -> RepairProposal:
        raise NotImplementedError


class OllamaBackend(RepairBackend):
    def __init__(self, model: str = "qwen2.5-coder:7b", base_url: str = "http://127.0.0.1:11434", timeout: int = 180):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _collect_context(self, root: Path, max_chars: int = 70000) -> str:
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
        user = f"""ITERATION {iteration}
FAILURES:
{json.dumps(failures, ensure_ascii=False, indent=2)}

PROJECT FILES:{context}

DECISION POLICY:
- Act autonomously when the root cause and a safe correction are reasonably determinable.
- Respect the client's stated goal, requested changes and acceptance criteria in the system instructions above.
- Do not change unrelated working behavior.
- Ask for a user decision ONLY when two or more materially different solutions satisfy the request and choosing one changes functionality, cost, privacy, external services, irreversible data handling, or user-facing behavior.
- Do NOT ask the user to choose routine implementation details, libraries, refactors, bug fixes, file paths or other technical decisions you can test yourself.
- If no code change is necessary, return an empty files object.
- confidence is 0.0 to 1.0 and must reflect confidence that the proposed edit is the correct minimal next action.

Return ONLY JSON with this schema:
{{"reason":"...","requires_user_choice":false,"choices":[],"confidence":0.95,"files":{{"relative/path.ext":"complete replacement content"}}}}
Never use absolute paths."""
        payload = {"model": self.model, "stream": False, "format": "json", "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": user}]}
        try:
            response = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RepairError(
                f"Motore AI Ollama non raggiungibile su {self.base_url}. "
                f"Verificare che Ollama sia installato, attivo e che il modello {self.model} sia disponibile."
            ) from exc
        try:
            raw = response.json().get("message", {}).get("content", "{}")
            data = json.loads(raw)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise RepairError("Ollama ha restituito una risposta non valida") from exc
        files = data.get("files") or {}
        if not isinstance(files, dict):
            raise RepairError("Backend returned invalid files mapping")
        choices = data.get("choices") or []
        if not isinstance(choices, list):
            choices = []
        try:
            confidence = max(0.0, min(1.0, float(data.get("confidence", 1.0))))
        except (TypeError, ValueError):
            confidence = 0.5
        return RepairProposal(
            {str(k): str(v) for k, v in files.items()},
            str(data.get("reason", "")),
            bool(data.get("requires_user_choice", False)),
            [str(x) for x in choices],
            confidence,
        )


class DeterministicSelfTestBackend(RepairBackend):
    def propose(self, prompt: str, project_root: Path, failures: list[dict], iteration: int) -> RepairProposal:
        target = project_root / "main.py"
        if target.exists():
            return RepairProposal({"main.py": "print('self-test-ok')\n"}, "Repair intentional syntax error", confidence=1.0)
        return RepairProposal({}, "No repair", confidence=1.0)


def apply_proposal(root: Path, proposal: RepairProposal) -> list[str]:
    changed = []
    for rel, content in proposal.files.items():
        target = (root / rel).resolve()
        if not is_within(target, root):
            raise RepairError(f"Rejected path outside workspace: {rel}")
        if ".git" in target.parts:
            raise RepairError(f"Rejected protected Git metadata path: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        changed.append(rel)
    return changed
