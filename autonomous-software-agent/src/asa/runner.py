from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path


BLOCKED_TOKENS = {
    "format", "diskpart", "shutdown", "reboot", "bcdedit", "cipher /w",
    "reg delete", "reg add", "net user", "net localgroup", "takeown",
    "icacls", "rm -rf /", "del /s /q c:\\", "remove-item -recurse c:\\",
}


@dataclass
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False

    def to_dict(self):
        return asdict(self)


def command_is_safe(command: str) -> bool:
    low = command.lower().strip()
    if any(token in low for token in BLOCKED_TOKENS):
        return False
    return True


def run_command(command: str, cwd: Path, timeout: int = 300, env: dict | None = None) -> CommandResult:
    if not command_is_safe(command):
        return CommandResult(command, 126, "", "Command blocked by safety policy", 0.0)
    started = time.monotonic()
    merged_env = os.environ.copy()
    if env:
        merged_env.update({str(k): str(v) for k, v in env.items()})
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=merged_env,
        )
        return CommandResult(command, proc.returncode, proc.stdout[-20000:], proc.stderr[-20000:], time.monotonic() - started)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(command, 124, (exc.stdout or "")[-20000:] if isinstance(exc.stdout, str) else "", (exc.stderr or "")[-20000:] if isinstance(exc.stderr, str) else "Timed out", time.monotonic() - started, True)
