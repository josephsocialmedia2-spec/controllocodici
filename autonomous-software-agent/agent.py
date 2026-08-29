from __future__ import annotations
import argparse
import json
import os
import shlex
import shutil
import smtplib
import subprocess
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path

@dataclass
class ClientRequest:
    goal: str
    instructions: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    max_iterations: int = 6

@dataclass
class Change:
    path: str
    old: str
    new: str
    reason: str

@dataclass
class Proposal:
    summary: str
    changes: list[Change] = field(default_factory=list)
    requires_user_choice: bool = False
    choices: list[str] = field(default_factory=list)
    confidence: float = 0.0

class SafeWorkspace:
    def resolve(self, root: Path, relative: str) -> Path:
        rel = Path(relative)
        if rel.is_absolute():
            raise ValueError("Percorsi assoluti non ammessi")
        target = (root / rel).resolve()
        rr = root.resolve()
        if target != rr and rr not in target.parents:
            raise ValueError("Modifica fuori dal workspace bloccata")
        if ".git" in target.parts:
            raise ValueError("Metadati Git protetti")
        return target

    def validate(self, root: Path, changes: list[Change]) -> None:
        for change in changes:
            p = self.resolve(root, change.path)
            if not p.is_file():
                raise ValueError(f"File inesistente: {change.path}")
            if change.old not in p.read_text(encoding="utf-8"):
                raise ValueError(f"Testo da sostituire non trovato: {change.path}")

class Runner:
    def detect(self, root: Path) -> list[str]:
        run_json = root / "run.json"
        if run_json.exists():
            cmd = json.loads(run_json.read_text(encoding="utf-8")).get("command")
            if isinstance(cmd, list) and cmd:
                return [str(x) for x in cmd]
            if isinstance(cmd, str) and cmd.strip():
                return shlex.split(cmd, posix=False)
        if (root / "main.py").exists():
            return ["python", "main.py"]
        if (root / "app.py").exists():
            return ["python", "app.py"]
        if (root / "package.json").exists():
            return ["npm", "test"]
        raise FileNotFoundError("Entry point non riconosciuto. Aggiungere run.json.")

    def run(self, command: list[str], cwd: Path, timeout: int = 180) -> dict:
        started = time.perf_counter()
        p = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return {"command": command, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr, "duration_s": time.perf_counter() - started}

class DeterministicProvider:
    def propose(self, root: Path, request: ClientRequest, run: dict) -> Proposal:
        if "NameError: name 'mesage' is not defined" in run["stderr"]:
            return Proposal(summary="Correzione typo verificata dal traceback", changes=[Change("main.py", "mesage", "message", "NameError verificato")], confidence=0.99)
        return Proposal("Nessuna correzione deterministica disponibile")

class OllamaProvider:
    def __init__(self):
        self.model = os.getenv("AUTOFIX_OLLAMA_MODEL", "qwen2.5-coder:7b")
        self.endpoint = os.getenv("AUTOFIX_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")

    def collect(self, root: Path) -> dict[str, str]:
        allowed = {".py", ".js", ".ts", ".html", ".css", ".json", ".bat", ".ps1", ".md"}
        result = {}
        for p in root.rglob("*"):
            if len(result) >= 16:
                break
            if p.is_file() and p.suffix.lower() in allowed and ".git" not in p.parts:
                try:
                    text = p.read_text(encoding="utf-8")
                except Exception:
                    continue
                if len(text) <= 80000:
                    result[str(p.relative_to(root))] = text
        return result

    def propose(self, root: Path, request: ClientRequest, run: dict) -> Proposal:
        schema = {"summary": "", "requires_user_choice": False, "choices": [], "confidence": 0.0, "changes": [{"path": "file.py", "old": "exact text", "new": "replacement", "reason": ""}]}
        prompt = (
            "Sei il motore di riparazione di un agente software autonomo. "
            "Applica autonomamente la soluzione quando causa e correzione sono verificabili. "
            "Chiedi una decisione SOLO quando esistono alternative con effetti sostanzialmente diversi. "
            "Non cambiare funzioni non richieste. OLD deve essere testo esatto presente nel file.\n\n"
            f"OBIETTIVO CLIENTE: {request.goal}\n"
            f"ISTRUZIONI CLIENTE: {request.instructions}\n"
            f"CRITERI DI ACCETTAZIONE: {request.acceptance}\n"
            f"EXIT CODE: {run['returncode']}\n"
            f"STDOUT:\n{run['stdout'][-12000:]}\n"
            f"STDERR:\n{run['stderr'][-12000:]}\n"
            f"FILE:\n{json.dumps(self.collect(root), ensure_ascii=False)[:120000]}\n"
            f"Rispondi esclusivamente con JSON valido nel formato: {json.dumps(schema, ensure_ascii=False)}"
        )
        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False, "format": "json"}).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as response:
            raw = json.loads(response.read().decode("utf-8"))
        data = json.loads(raw.get("response", "{}"))
        return Proposal(summary=str(data.get("summary", "")), changes=[Change(**x) for x in data.get("changes", [])], requires_user_choice=bool(data.get("requires_user_choice", False)), choices=[str(x) for x in data.get("choices", [])], confidence=float(data.get("confidence", 0.0)))

def desktop_notification(title: str, message: str) -> None:
    if os.name != "nt":
        return
    safe_title = title.replace("'", "''")
    safe_message = message.replace("'", "''")
    ps = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.BalloonTipTitle = '{safe_title}'
$n.BalloonTipText = '{safe_message}'
$n.Visible = $true
$n.ShowBalloonTip(8000)
Start-Sleep -Seconds 9
$n.Dispose()
"""
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps])
    except Exception:
        pass

def email_notification(program: str, message: str) -> bool:
    host = os.getenv("AUTOFIX_SMTP_HOST")
    user = os.getenv("AUTOFIX_SMTP_USER")
    password = os.getenv("AUTOFIX_SMTP_PASSWORD")
    recipient = os.getenv("AUTOFIX_EMAIL_TO")
    if not all([host, user, password, recipient]):
        return False
    mail = EmailMessage()
    mail["From"] = user
    mail["To"] = recipient
    mail["Subject"] = f"{program} è pronto"
    mail.set_content(message)
    with smtplib.SMTP_SSL(host, int(os.getenv("AUTOFIX_SMTP_PORT", "465")), timeout=30) as smtp:
        smtp.login(user, password)
        smtp.send_message(mail)
    return True

class Controller:
    def __init__(self, provider):
        self.provider = provider
        self.runner = Runner()
        self.safe = SafeWorkspace()

    def qa(self, root: Path, request: ClientRequest, run: dict) -> tuple[bool, float, list[str]]:
        reasons = []
        score = 60.0 if run["returncode"] == 0 else 0.0
        if run["returncode"] != 0:
            reasons.append(f"Exit code {run['returncode']}")
        for rel in request.expected_outputs:
            p = root / rel
            if p.is_file() and p.stat().st_size > 0:
                score += 30.0 / max(1, len(request.expected_outputs))
            else:
                reasons.append(f"Output mancante o vuoto: {rel}")
        if "traceback" not in (run["stdout"] + "\n" + run["stderr"]).lower():
            score += 10.0
        passed = run["returncode"] == 0 and not any(x.startswith("Output") for x in reasons)
        return passed, min(score, 100.0), reasons

    def process(self, project: Path, session: Path, request: ClientRequest) -> dict:
        original, work, best, logs = (session / x for x in ("ORIGINAL", "WORK", "BEST", "LOGS"))
        session.mkdir(parents=True, exist_ok=True)
        logs.mkdir(exist_ok=True)
        if not original.exists():
            shutil.copytree(project, original)
        if work.exists():
            shutil.rmtree(work)
        shutil.copytree(original, work)
        if not best.exists():
            shutil.copytree(original, best)
        command = self.runner.detect(work)
        best_score = -1.0
        records = []
        stagnant = 0
        status = "BLOCKED"
        note = ""
        for iteration in range(1, request.max_iterations + 1):
            run = self.runner.run(command, work)
            passed, score, reasons = self.qa(work, request, run)
            record = {"iteration": iteration, "returncode": run["returncode"], "duration_s": run["duration_s"], "score": score, "reasons": reasons, "stderr": run["stderr"][-4000:], "changes": []}
            records.append(record)
            if score > best_score:
                if best.exists():
                    shutil.rmtree(best)
                shutil.copytree(work, best)
                best_score = score
                stagnant = 0
            else:
                stagnant += 1
            if passed:
                status = "READY"
                note = "Programma verificato e pronto"
                break
            proposal = self.provider.propose(work, request, run)
            record["proposal"] = proposal.summary
            if proposal.requires_user_choice or (proposal.changes and proposal.confidence < 0.55):
                status = "NEEDS_DECISION"
                note = proposal.summary
                if proposal.choices:
                    note += " | " + " / ".join(proposal.choices)
                break
            if not proposal.changes:
                status = "PARTIAL" if best_score >= 60 else "BLOCKED"
                note = "Nessuna ulteriore correzione sicura disponibile"
                break
            self.safe.validate(work, proposal.changes)
            for change in proposal.changes:
                path = self.safe.resolve(work, change.path)
                current = path.read_text(encoding="utf-8")
                path.write_text(current.replace(change.old, change.new, 1), encoding="utf-8")
                record["changes"].append(change.path)
            if stagnant >= 3:
                status = "PARTIAL"
                note = "Arresto automatico: tre iterazioni senza miglioramento"
                break
        report = {"status": status, "best_score": best_score, "note": note, "records": records}
        (logs / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        if status == "READY":
            desktop_notification("Programma pronto", note)
            email_notification(project.name, note)
        return report

def self_test() -> int:
    base = Path(tempfile.mkdtemp(prefix="autofix-selftest-"))
    project = base / "project"
    project.mkdir()
    (project / "main.py").write_text('message = "OK"\nprint(mesage)\n', encoding="utf-8")
    request = ClientRequest(goal="Il programma deve stampare OK", max_iterations=3)
    report = Controller(DeterministicProvider()).process(project, base / "session", request)
    best_text = (base / "session" / "BEST" / "main.py").read_text(encoding="utf-8")
    ok = report["status"] == "READY" and "print(message)" in best_text
    print(json.dumps({"ok": ok, **report}, ensure_ascii=False))
    return 0 if ok else 1

def watch(root: Path) -> None:
    inbox, sessions, ready = (root / x for x in ("INBOX", "SESSIONS", "READY"))
    for p in (inbox, sessions, ready):
        p.mkdir(parents=True, exist_ok=True)
    controller = Controller(OllamaProvider())
    while True:
        for job in sorted(inbox.iterdir()):
            if not job.is_dir() or (job / ".processing").exists():
                continue
            request_file = job / "request.json"
            project = job / "project"
            if not request_file.exists() or not project.exists():
                continue
            (job / ".processing").write_text("1", encoding="utf-8")
            request = ClientRequest(**json.loads(request_file.read_text(encoding="utf-8")))
            report = controller.process(project, sessions / job.name, request)
            if report["status"] == "READY":
                target = ready / job.name
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(sessions / job.name / "BEST", target)
        time.sleep(5)

def main() -> None:
    parser = argparse.ArgumentParser(prog="AutonomousSoftwareAgent")
    sub = parser.add_subparsers(dest="command", required=True)
    runp = sub.add_parser("run")
    runp.add_argument("project")
    runp.add_argument("request")
    runp.add_argument("--session", default=".autofix-session")
    runp.add_argument("--provider", choices=["ollama", "deterministic"], default="ollama")
    watchp = sub.add_parser("watch")
    watchp.add_argument("root")
    sub.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "self-test":
        raise SystemExit(self_test())
    if args.command == "watch":
        watch(Path(args.root))
        return
    request = ClientRequest(**json.loads(Path(args.request).read_text(encoding="utf-8")))
    provider = OllamaProvider() if args.provider == "ollama" else DeterministicProvider()
    report = Controller(provider).process(Path(args.project), Path(args.session), request)
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report["status"] == "READY" else 2)

if __name__ == "__main__":
    main()
