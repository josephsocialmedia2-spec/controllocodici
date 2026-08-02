from __future__ import annotations

import json
import queue
import threading
from typing import Callable


class OfflineTranscriber:
    def __init__(self, model, speaker: str, partial_callback: Callable[[str, str], None], final_callback: Callable[[str, str], None], error_callback: Callable[[str, str], None], sample_rate: int = 16_000) -> None:
        self.model = model
        self.speaker = speaker
        self.partial_callback = partial_callback
        self.final_callback = final_callback
        self.error_callback = error_callback
        self.sample_rate = sample_rate
        self._queue: queue.Queue[bytes | None] = queue.Queue(maxsize=200)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_partial = ""

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name=f"Vosk-{self.speaker}", daemon=True)
        self._thread.start()

    def submit(self, pcm16: bytes) -> None:
        if not pcm16 or self._stop_event.is_set():
            return
        try:
            self._queue.put_nowait(pcm16)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(pcm16)
            except queue.Full:
                pass

    def stop(self) -> None:
        self._stop_event.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    @staticmethod
    def _extract(payload: str, field: str) -> str:
        try:
            data = json.loads(payload)
            return str(data.get(field, "")).strip()
        except (json.JSONDecodeError, TypeError):
            return ""

    def _run(self) -> None:
        try:
            from vosk import KaldiRecognizer
            recognizer = KaldiRecognizer(self.model, self.sample_rate)
            recognizer.SetWords(True)
            while not self._stop_event.is_set():
                try:
                    audio = self._queue.get(timeout=0.25)
                except queue.Empty:
                    continue
                if audio is None:
                    break
                if recognizer.AcceptWaveform(audio):
                    text = self._extract(recognizer.Result(), "text")
                    self._last_partial = ""
                    if text:
                        self.final_callback(self.speaker, text)
                else:
                    partial = self._extract(recognizer.PartialResult(), "partial")
                    if partial and partial != self._last_partial:
                        self._last_partial = partial
                        self.partial_callback(self.speaker, partial)
            final = self._extract(recognizer.FinalResult(), "text")
            if final:
                self.final_callback(self.speaker, final)
        except Exception as exc:
            self.error_callback(self.speaker, str(exc))
