from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def archive_root() -> Path:
    documents = Path.home() / "Documents"
    if os.name == "nt" and not documents.exists():
        documents = Path.home() / "Documenti"
    return documents / "F1 Assistente Telefonico" / "Chiamate"


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9À-ÿ_-]+", "_", value.strip())
    return cleaned.strip("_")[:60] or "Contatto"


class CallSession:
    def __init__(self, contact: str, phone: str, city: str, script: str, base_dir: Path | None = None) -> None:
        self.contact = contact
        self.phone = phone
        self.city = city
        self.script = script
        self.started_at = datetime.now()
        self.finished_at: datetime | None = None
        self.turns: list[dict[str, Any]] = []
        self.suggestions: list[dict[str, Any]] = []
        self.base_dir = Path(base_dir) if base_dir is not None else archive_root()
        day_folder = self.started_at.strftime("%Y-%m-%d")
        session_name = f"{self.started_at:%H%M%S}_{_slug(contact)}"
        self.folder = self.base_dir / day_folder / session_name
        self.folder.mkdir(parents=True, exist_ok=True)
        self._write_snapshot()

    def add_turn(self, speaker: str, text: str) -> None:
        if not text.strip():
            return
        self.turns.append({"timestamp": datetime.now().isoformat(timespec="seconds"), "speaker": speaker, "text": text.strip()})
        self._write_snapshot()

    def add_suggestion(self, text: str, category: str) -> None:
        if not text.strip():
            return
        if self.suggestions and self.suggestions[-1]["text"] == text.strip():
            return
        self.suggestions.append({"timestamp": datetime.now().isoformat(timespec="seconds"), "category": category, "text": text.strip()})
        self._write_snapshot()

    def finish(self, outcome: str = "", notes: str = "") -> Path:
        if self.finished_at is None:
            self.finished_at = datetime.now()
        payload = self._payload(outcome, notes)
        (self.folder / "sessione.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._write_transcript(payload)
        self._write_summary(payload)
        (self.folder / "sessione_in_corso.json").unlink(missing_ok=True)
        return self.folder

    def _payload(self, outcome: str = "", notes: str = "") -> dict[str, Any]:
        return {
            "contact": self.contact,
            "phone": self.phone,
            "city": self.city,
            "script": self.script,
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "finished_at": self.finished_at.isoformat(timespec="seconds") if self.finished_at else None,
            "outcome": outcome,
            "notes": notes,
            "turns": self.turns,
            "suggestions": self.suggestions,
        }

    def _write_snapshot(self) -> None:
        path = self.folder / "sessione_in_corso.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self._payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    def _write_transcript(self, payload: dict[str, Any]) -> None:
        lines = [
            "F1 IMMOBILIARE — TRASCRIZIONE TELEFONATA",
            "=" * 52,
            f"Contatto: {self.contact}",
            f"Telefono: {self.phone}",
            f"Comune: {self.city}",
            f"Script: {self.script}",
            f"Inizio: {payload['started_at']}",
            f"Fine: {payload['finished_at'] or ''}",
            "",
        ]
        for turn in self.turns:
            timestamp = str(turn["timestamp"])[11:19]
            lines.extend([f"[{timestamp}] {turn['speaker']}: {turn['text']}", ""])
        (self.folder / "trascrizione.txt").write_text("\n".join(lines), encoding="utf-8")

    def _write_summary(self, payload: dict[str, Any]) -> None:
        customer_turns = sum(1 for turn in self.turns if turn["speaker"] == "CLIENTE")
        joseph_turns = sum(1 for turn in self.turns if turn["speaker"] == "JOSEPH")
        categories: dict[str, int] = {}
        for suggestion in self.suggestions:
            category = str(suggestion["category"])
            categories[category] = categories.get(category, 0) + 1
        category_lines = [f"- {key}: {value}" for key, value in sorted(categories.items())]
        lines = [
            "RIEPILOGO TECNICO DELLA CHIAMATA",
            "=" * 38,
            f"Contatto: {self.contact}",
            f"Comune: {self.city}",
            f"Interventi cliente: {customer_turns}",
            f"Interventi Joseph: {joseph_turns}",
            f"Suggerimenti generati: {len(self.suggestions)}",
            "",
            "Categorie rilevate:",
            *(category_lines or ["- Nessuna categoria rilevata"]),
            "",
            f"Esito: {payload.get('outcome', '')}",
            f"Note: {payload.get('notes', '')}",
        ]
        (self.folder / "riepilogo.txt").write_text("\n".join(lines), encoding="utf-8")
