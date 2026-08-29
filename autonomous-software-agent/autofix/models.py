from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

@dataclass
class ClientRequest:
    goal: str
    instructions: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    max_iterations: int = 6
    ask_only_when_needed: bool = True

@dataclass
class RunResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_s: float

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

@dataclass
class QAResult:
    passed: bool
    score: float
    reasons: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)

@dataclass
class IterationRecord:
    iteration: int
    run: RunResult
    qa: QAResult
    proposal_summary: str = ""
    applied_changes: list[str] = field(default_factory=list)

@dataclass
class ProjectState:
    project_dir: Path
    original_dir: Path
    work_dir: Path
    best_dir: Path
    output_dir: Path
    logs_dir: Path
    best_score: float = -1.0
    records: list[IterationRecord] = field(default_factory=list)
    status: str = "NEW"
    note: str = ""
