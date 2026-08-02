from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

SAMPLE_RATE = 16_000


@dataclass(frozen=True)
class AudioDevice:
    index: int
    name: str
    label: str
    is_loopback: bool = False


def _soundcard():
    try:
        import soundcard as sc
    except ImportError as exc:
        raise RuntimeError("Libreria SoundCard non installata. Esegui INSTALLA_E_AVVIA.bat.") from exc
    return sc


def _all_microphones():
    sc = _soundcard()
    try:
        return list(sc.all_microphones(include_loopback=True))
    except TypeError:
        return list(sc.all_microphones())


def _normal_microphone_ids() -> set[str]:
    sc = _soundcard()
    try:
        return {str(item.id) for item in sc.all_microphones(include_loopback=False)}
    except TypeError:
        return {str(item.id) for item in sc.all_microphones()}


def _is_virtual_customer_device(name: str) -> bool:
    lowered = name.casefold()
    keywords = ("voicemeeter", "cable", "stereo mix", "mixaggio stereo", "phone link", "collegamento al telefono", "monitor", "loopback", "what u hear")
    return any(keyword in lowered for keyword in keywords)


def list_devices() -> tuple[list[AudioDevice], list[AudioDevice]]:
    devices = _all_microphones()
    normal_ids = _normal_microphone_ids()
    microphones: list[AudioDevice] = []
    preferred_customer: list[AudioDevice] = []
    fallback_customer: list[AudioDevice] = []

    for index, device in enumerate(devices):
        name = str(getattr(device, "name", f"Dispositivo {index}"))
        device_id = str(getattr(device, "id", index))
        is_loopback = device_id not in normal_ids or "loopback" in name.casefold()
        kind = "LOOPBACK" if is_loopback else "INGRESSO"
        item = AudioDevice(index=index, name=name, label=f"[{kind}] {name}", is_loopback=is_loopback)
        if not is_loopback:
            microphones.append(item)
        if is_loopback or _is_virtual_customer_device(name):
            preferred_customer.append(item)
        else:
            fallback_customer.append(item)

    preferred_indices = {item.index for item in preferred_customer}
    customer_devices = preferred_customer + [item for item in fallback_customer if item.index not in preferred_indices]
    if not microphones:
        microphones = [item for item in customer_devices if not item.is_loopback]
    if not customer_devices:
        customer_devices = list(microphones)
    return microphones, customer_devices


def default_indices() -> tuple[int | None, int | None]:
    microphones, customer_devices = list_devices()
    sc = _soundcard()
    default_mic_index: int | None = None
    try:
        default_mic = sc.default_microphone()
        default_id = str(default_mic.id)
        for index, device in enumerate(_all_microphones()):
            if str(device.id) == default_id:
                default_mic_index = index
                break
    except Exception:
        pass
    if default_mic_index is None and microphones:
        default_mic_index = microphones[0].index

    preferred_order = ("voicemeeter aux output", "voicemeeter output", "cable output", "phone link", "collegamento al telefono", "stereo mix", "mixaggio stereo", "loopback", "monitor")
    default_customer: int | None = None
    for keyword in preferred_order:
        match = next((item for item in customer_devices if keyword in item.name.casefold()), None)
        if match:
            default_customer = match.index
            break
    if default_customer is None and customer_devices:
        default_customer = customer_devices[0].index
    return default_mic_index, default_customer


class AudioCapture:
    def __init__(self, device_index: int, submit_callback: Callable[[bytes], None], level_callback: Callable[[float], None], error_callback: Callable[[str], None], label: str, chunk_ms: int = 100) -> None:
        self.device_index = int(device_index)
        self.submit_callback = submit_callback
        self.level_callback = level_callback
        self.error_callback = error_callback
        self.label = label
        self.chunk_ms = max(40, min(500, int(chunk_ms)))
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._pause_event.clear()
        self._thread = threading.Thread(target=self._run, name=f"AudioCapture-{self.label}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.clear()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def pause(self) -> None:
        self._pause_event.set()

    def resume(self) -> None:
        self._pause_event.clear()

    def _run(self) -> None:
        try:
            import numpy as np
            devices = _all_microphones()
            if self.device_index < 0 or self.device_index >= len(devices):
                raise RuntimeError(f"Indice audio non valido ({self.device_index}). Apri CONFIGURAZIONE e seleziona di nuovo il dispositivo.")
            microphone = devices[self.device_index]
            frames = max(640, int(SAMPLE_RATE * self.chunk_ms / 1000))
            with microphone.recorder(samplerate=SAMPLE_RATE, channels=None, blocksize=frames * 2) as recorder:
                while not self._stop_event.is_set():
                    if self._pause_event.is_set():
                        self.level_callback(0.0)
                        time.sleep(0.05)
                        continue
                    data = recorder.record(numframes=frames)
                    array = np.asarray(data, dtype=np.float32)
                    if array.size == 0:
                        continue
                    mono = np.mean(array, axis=1) if array.ndim == 2 else array.reshape(-1)
                    mono = np.nan_to_num(mono, nan=0.0, posinf=0.0, neginf=0.0)
                    mono = np.clip(mono, -1.0, 1.0)
                    level = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
                    pcm16 = (mono * 32767.0).astype("<i2", copy=False).tobytes()
                    self.level_callback(level)
                    self.submit_callback(pcm16)
        except Exception as exc:
            self.error_callback(f"{self.label}: {exc}")
