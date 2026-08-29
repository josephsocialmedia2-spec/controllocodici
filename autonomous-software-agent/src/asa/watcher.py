from __future__ import annotations

import shutil
import time
import zipfile
from pathlib import Path

from .notifications import notify
from .orchestrator import Orchestrator
from .utils import read_json, safe_name

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def _safe_extract(zf: zipfile.ZipFile, destination: Path) -> None:
    root = destination.resolve()
    for member in zf.infolist():
        target = (destination / member.filename).resolve()
        if target != root and root not in target.parents:
            raise RuntimeError(f"ZIP non sicuro: percorso fuori workspace ({member.filename})")
    zf.extractall(destination)


def _effective_root(root: Path) -> Path:
    entries = [p for p in root.iterdir() if p.name not in {"__MACOSX"} and not p.name.startswith(".")]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return root


def _looks_like_book(path: Path) -> bool:
    files = [p for p in path.iterdir() if p.is_file() and not p.name.startswith(".")]
    images = [p for p in files if p.suffix.lower() in IMAGE_EXTS]
    non_images = [p for p in files if p.suffix.lower() not in IMAGE_EXTS and p.name != "job.json"]
    return len(images) >= 1 and not non_images


def load_job(path: Path) -> dict:
    job_file = path / "job.json"
    if job_file.exists():
        return read_json(job_file)
    if _looks_like_book(path):
        return {
            "name": path.name,
            "type": "book",
            "source": {"type": "local", "path": str(path)},
            "synthesize_audio": True,
        }
    return {"name": path.name, "type": "software", "source": {"type": "local", "path": str(path)}}


def watch(home: Path, orchestrator: Orchestrator, config: dict, once: bool = False, interval: int = 5):
    inbox, processed, needs_decision, failed, temp = [home / x for x in ["INBOX", "PROCESSED", "NEEDS_DECISION", "FAILED", "TEMP"]]
    for p in (inbox, processed, needs_decision, failed, temp):
        p.mkdir(parents=True, exist_ok=True)
    while True:
        candidates = [p for p in inbox.iterdir() if not p.name.startswith(".")]
        for item in candidates:
            source = item
            extracted = None
            try:
                if item.is_file() and item.suffix.lower() == ".zip":
                    extracted = temp / safe_name(item.stem)
                    if extracted.exists():
                        shutil.rmtree(extracted)
                    extracted.mkdir(parents=True)
                    with zipfile.ZipFile(item) as zf:
                        _safe_extract(zf, extracted)
                    source = _effective_root(extracted)
                if not source.is_dir():
                    continue
                job = load_job(source)
                report = orchestrator.process(job, source_override=source if job.get("source", {}).get("type", "local") == "local" else None)
                status = report.get("status")
                if status == "OK":
                    destination_root = processed
                    title = "Programma pronto"
                    message = f"{job.get('name', item.stem)}: pronto e verificato. Risultati: {report.get('run_root')}"
                elif status == "NEEDS_DECISION":
                    destination_root = needs_decision
                    decision = report.get("decision") or {}
                    choices = " | ".join(decision.get("choices") or [])
                    title = "Decisione necessaria"
                    message = f"{job.get('name', item.stem)}: {decision.get('reason', '')}" + (f". Opzioni: {choices}" if choices else "")
                else:
                    destination_root = failed
                    title = "Programma da verificare"
                    message = f"{job.get('name', item.stem)}: {status}. Risultati: {report.get('run_root')}"
                destination = destination_root / f"{safe_name(item.stem)}-{int(time.time())}"
                if item.is_dir():
                    shutil.move(str(item), str(destination))
                else:
                    shutil.move(str(item), str(destination.with_suffix(item.suffix)))
                notify(config, title, message)
            except Exception as exc:
                notify(config, "Errore Autonomous Software Agent", f"{item.name}: {exc}")
            finally:
                if extracted and extracted.exists():
                    shutil.rmtree(extracted, ignore_errors=True)
        if once:
            return
        time.sleep(interval)
