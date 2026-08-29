from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from .book_pipeline import run_book_pipeline
from .project import acquire_source, detect_project
from .repair import RepairBackend, OllamaBackend, apply_proposal
from .runner import run_command
from .utils import copytree, safe_name, write_json


@dataclass
class IterationResult:
    iteration: int
    score: int
    passed: bool
    commands: list[dict]
    changed_files: list[str]
    reason: str


class Orchestrator:
    def __init__(self, home: Path, repair_backend: RepairBackend | None = None, master_prompt: str = "", max_iterations: int = 3):
        self.home = home; self.repair_backend = repair_backend or OllamaBackend(); self.master_prompt = master_prompt; self.max_iterations = max_iterations

    def _score(self, results: list[dict], output_ok: bool = True) -> int:
        if not results: return 100 if output_ok else 0
        passed = sum(1 for r in results if r["exit_code"] == 0)
        return int((passed / len(results)) * 90 + (10 if output_ok else 0))

    def _run_plan(self, work: Path, job: dict) -> tuple[list[dict], bool]:
        plan = detect_project(work, job)
        results = [run_command(cmd, work, int(job.get("timeout", 300))).to_dict() for cmd in plan.test_commands]
        passed = all(r["exit_code"] == 0 for r in results) if results else True
        if passed and plan.run_command and job.get("verify_run", False):
            r = run_command(plan.run_command, work, int(job.get("run_timeout", 120))).to_dict(); results.append(r); passed = passed and r["exit_code"] == 0
        return results, passed

    def process(self, job: dict, source_override: Path | None = None) -> dict:
        job_name = safe_name(job.get("name") or f"job-{int(time.time())}")
        run_root = self.home / "RUNS" / f"{job_name}-{time.strftime('%Y%m%d-%H%M%S')}"
        original, work, best, output, logs = [run_root / x for x in ["ORIGINAL", "WORK", "BEST", "OUTPUT", "LOGS"]]
        for p in (run_root, output, logs): p.mkdir(parents=True, exist_ok=True)
        if job.get("type") == "book":
            input_path = source_override or Path(job["source"]["path"]).expanduser().resolve()
            qa = run_book_pipeline(input_path, output, bool(job.get("synthesize_audio", True)))
            report = {"status": qa["status"], "job": job_name, "type": "book", "run_root": str(run_root), "output": str(output), "qa": qa}; write_json(run_root / "report.json", report); return report
        if source_override: copytree(source_override, original)
        else: acquire_source(job, original)
        copytree(original, work)
        history = []; best_score = -1; stagnant = 0
        for iteration in range(self.max_iterations + 1):
            results, passed = self._run_plan(work, job); score = self._score(results); changed = []; reason = "Baseline" if iteration == 0 else "Retest"
            if score > best_score: best_score = score; copytree(work, best); stagnant = 0
            else: stagnant += 1
            item = IterationResult(iteration, score, passed, results, changed, reason); history.append(item); write_json(logs / f"iteration-{iteration:02d}.json", item.__dict__)
            if passed or iteration >= self.max_iterations or stagnant >= 3: break
            failures = [r for r in results if r["exit_code"] != 0]
            proposal = self.repair_backend.propose(self.master_prompt, work, failures, iteration + 1)
            item.changed_files = apply_proposal(work, proposal); item.reason = proposal.reason; write_json(logs / f"iteration-{iteration:02d}.json", item.__dict__)
        final_results, final_passed = self._run_plan(best, job)
        status = "OK" if final_passed else ("PARZIALE" if best_score > 0 else "BLOCCATO")
        report = {"status": status, "job": job_name, "type": job.get("type", "software"), "run_root": str(run_root), "best": str(best), "output": str(output), "best_score": best_score, "final_test_results": final_results, "iterations": [h.__dict__ for h in history]}; write_json(run_root / "report.json", report); return report
