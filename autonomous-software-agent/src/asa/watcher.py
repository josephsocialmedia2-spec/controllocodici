from __future__ import annotations

import shutil
import time
import zipfile
from pathlib import Path

from .notifications import notify
from .orchestrator import Orchestrator
from .utils import read_json, safe_name


def load_job(path: Path) -> dict:
    job_file = path / "job.json"
    if job_file.exists(): return read_json(job_file)
    return {"name": path.name, "type": "software", "source": {"type": "local", "path": str(path)}}


def watch(home: Path, orchestrator: Orchestrator, config: dict, once: bool = False, interval: int = 5):
    inbox, processed, failed, temp = [home / x for x in ["INBOX", "PROCESSED", "FAILED", "TEMP"]]
    for p in (inbox, processed, failed, temp): p.mkdir(parents=True, exist_ok=True)
    while True:
        candidates = [p for p in inbox.iterdir() if not p.name.startswith(".")]
        for item in candidates:
            source = item; extracted = None
            try:
                if item.is_file() and item.suffix.lower() == ".zip":
                    extracted = temp / safe_name(item.stem)
                    if extracted.exists(): shutil.rmtree(extracted)
                    extracted.mkdir(parents=True)
                    with zipfile.ZipFile(item) as zf: zf.extractall(extracted)
                    source = extracted
                if not source.is_dir(): continue
                job = load_job(source)
                report = orchestrator.process(job, source_override=source if job.get("source", {}).get("type", "local") == "local" else None)
                ok = report.get("status") == "OK"; destination_root = processed if ok else failed; destination = destination_root / f"{safe_name(item.stem)}-{int(time.time())}"
                if item.is_dir(): shutil.move(str(item), str(destination))
                else: shutil.move(str(item), str(destination.with_suffix(item.suffix)))
                title = "Programma pronto" if ok else "Programma da verificare"; message = f"{job.get('name', item.stem)}: {report.get('status')}. Risultati: {report.get('run_root')}"; notify(config, title, message)
            except Exception as exc:
                notify(config, "Errore Autonomous Software Agent", f"{item.name}: {exc}")
            finally:
                if extracted and extracted.exists(): shutil.rmtree(extracted, ignore_errors=True)
        if once: return
        time.sleep(interval)
