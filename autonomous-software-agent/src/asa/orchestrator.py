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
    def __init__(self, home: Path, repair_backend: RepairBackend | None = None, master_prompt: str = "", max_iterations: int = 6):
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

    def _request_fields(self, job: dict) -> tuple[str, list[str], list[str]]:
        goal = str(job.get("goal") or job.get("request") or "").strip()
        instructions = job.get("instructions") or job.get("changes") or []
        acceptance = job.get("acceptance") or job.get("acceptance_criteria") or []
        if isinstance(instructions, str): instructions = [instructions]
        if isinstance(acceptance, str): acceptance = [acceptance]
        return goal, [str(x) for x in instructions], [str(x) for x in acceptance]

    def _client_prompt(self, job: dict) -> str:
        goal, instructions, acceptance = self._request_fields(job)
        return (
            self.master_prompt
            + "\n\nCLIENT REQUEST — HIGHEST PRIORITY WITHIN SAFE PROJECT SCOPE:\n"
            + f"GOAL: {goal or 'Restore and improve the software while preserving working behavior.'}\n"
            + "REQUESTED CHANGES:\n" + "\n".join(f"- {x}" for x in instructions)
            + "\nACCEPTANCE CRITERIA:\n" + "\n".join(f"- {x}" for x in acceptance)
            + "\nA green baseline does NOT mean the client request is complete. Inspect the code and implement the requested change when it is not already satisfied. Do not reinterpret a clear client requirement as optional. Prefer autonomous tested implementation. Ask only for a materially consequential unresolved choice."
        )

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
        goal, instructions, acceptance = self._request_fields(job)
        explicit_request = bool(goal or instructions or acceptance)
        request_evaluated = False
        request_no_change_needed = False
        revision = 0
        history = []
        best_key = (-1, -1)
        best_score = -1
        best_revision = -1
        stagnant = 0
        decision = None
        client_prompt = self._client_prompt(job)
        max_iterations = max(1, int(job.get("max_iterations", self.max_iterations)))
        for iteration in range(max_iterations + 1):
            results, passed = self._run_plan(work, job)
            score = self._score(results)
            current_key = (score, revision)
            changed = []
            reason = "Baseline" if iteration == 0 else "Retest"
            if current_key > best_key:
                best_key = current_key
                best_score = score
                best_revision = revision
                copytree(work, best)
                stagnant = 0
            else:
                stagnant += 1
            item = IterationResult(iteration, score, passed, results, changed, reason)
            history.append(item)
            write_json(logs / f"iteration-{iteration:02d}.json", item.__dict__)

            need_request_review = explicit_request and not request_evaluated
            if passed and not need_request_review:
                break
            if iteration >= max_iterations or stagnant >= 3:
                break

            failures = [r for r in results if r["exit_code"] != 0]
            proposal = self.repair_backend.propose(client_prompt, work, failures, iteration + 1)
            request_evaluated = request_evaluated or need_request_review

            if proposal.requires_user_choice or (proposal.files and proposal.confidence < float(job.get("minimum_autonomous_confidence", 0.55))):
                decision = {"reason": proposal.reason, "choices": proposal.choices, "confidence": proposal.confidence}
                item.reason = "Decisione cliente necessaria: " + proposal.reason
                write_json(logs / f"iteration-{iteration:02d}.json", item.__dict__)
                break

            if not proposal.files:
                item.reason = proposal.reason or "Nessuna modifica necessaria o nessuna correzione sicura determinabile"
                if need_request_review and passed:
                    request_no_change_needed = True
                write_json(logs / f"iteration-{iteration:02d}.json", item.__dict__)
                break

            item.changed_files = apply_proposal(work, proposal)
            revision += 1
            item.reason = proposal.reason
            write_json(logs / f"iteration-{iteration:02d}.json", item.__dict__)

        final_results, final_passed = self._run_plan(best, job)
        request_satisfied = (not explicit_request) or request_no_change_needed or best_revision > 0
        if decision:
            status = "NEEDS_DECISION"
        elif final_passed and request_satisfied:
            status = "OK"
        elif best_score > 0:
            status = "PARZIALE"
        else:
            status = "BLOCCATO"
        report = {
            "status": status,
            "job": job_name,
            "type": job.get("type", "software"),
            "run_root": str(run_root),
            "best": str(best),
            "output": str(output),
            "best_score": best_score,
            "best_revision": best_revision,
            "request_evaluated": request_evaluated,
            "request_satisfied": request_satisfied,
            "final_test_results": final_results,
            "iterations": [h.__dict__ for h in history],
            "decision": decision,
        }
        write_json(run_root / "report.json", report)
        return report
