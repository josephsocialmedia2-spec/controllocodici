from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from asa.notifications import notify
from asa.orchestrator import Orchestrator
from asa.repair import OllamaBackend
from asa.selftest import run_self_test
from asa.utils import app_home, read_json
from asa.watcher import watch


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base / relative


def load_config(home: Path, explicit: str | None = None) -> dict:
    path = Path(explicit).expanduser().resolve() if explicit else home / "config.json"
    if path.exists():
        return read_json(path)
    template = resource_path("config.default.json")
    config = read_json(template) if template.exists() else {
        "max_iterations": 6,
        "ollama": {"model": "qwen2.5-coder:7b", "base_url": "http://127.0.0.1:11434", "timeout": 180},
        "email": {"provider": "outlook", "to": "agenzia.realmediapro@gmail.com"},
    }
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


def ensure_layout(home: Path):
    for name in ["INBOX", "PROCESSED", "NEEDS_DECISION", "FAILED", "RUNS", "TEMP"]:
        (home / name).mkdir(parents=True, exist_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Autonomous Software Agent")
    parser.add_argument("--home")
    parser.add_argument("--config")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--job")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--notify-ready", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        ok = run_self_test()
        print("SELF_TEST_OK" if ok else "SELF_TEST_FAILED")
        return 0 if ok else 1
    home = Path(args.home).expanduser().resolve() if args.home else app_home()
    ensure_layout(home)
    config = load_config(home, args.config)
    if args.notify_ready:
        notify(config, "Programma pronto", "Autonomous Software Agent è installato e operativo sul PC.")
        return 0
    prompt_path = resource_path("prompts/master.txt")
    master_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else "Repair software minimally and verify results."
    ollama = config.get("ollama", {})
    backend = OllamaBackend(ollama.get("model", "qwen2.5-coder:7b"), ollama.get("base_url", "http://127.0.0.1:11434"), int(ollama.get("timeout", 180)))
    orchestrator = Orchestrator(home, backend, master_prompt, int(config.get("max_iterations", 6)))
    if args.job:
        job = read_json(Path(args.job).expanduser().resolve())
        report = orchestrator.process(job)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if report["status"] == "OK":
            title = "Programma pronto"
        elif report["status"] == "NEEDS_DECISION":
            title = "Decisione necessaria"
        else:
            title = "Programma da verificare"
        notify(config, title, f"{report['job']}: {report['status']}")
        return 0 if report["status"] == "OK" else 2
    watch(home, orchestrator, config, once=args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
