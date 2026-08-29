from __future__ import annotations

import json
import os
import re
import subprocess
import wave
from collections import Counter
from pathlib import Path

from .utils import natural_key, write_json

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def _extract_rapidocr(result):
    if result is None:
        return []
    if hasattr(result, "txts"):
        txts = list(result.txts or [])
        scores = list(getattr(result, "scores", []) or [])
        return [(t, float(scores[i]) if i < len(scores) else 1.0) for i, t in enumerate(txts)]
    if hasattr(result, "to_json"):
        try:
            data = result.to_json()
            if isinstance(data, str):
                data = json.loads(data)
            lines = data.get("data") or data.get("result") or []
            out = []
            for item in lines:
                text = item.get("txt") or item.get("text") or ""
                score = item.get("score", 1.0)
                if text:
                    out.append((text, float(score)))
            if out:
                return out
        except Exception:
            pass
    if isinstance(result, tuple) and len(result) >= 1:
        result = result[0]
    if isinstance(result, list):
        out = []
        for item in result:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                out.append((str(item[1]), float(item[2])))
        return out
    return []


def clean_faithful(lines: list[str]) -> str:
    cleaned = []
    for line in lines:
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            cleaned.append(line)
    text = "\n".join(cleaned)
    text = re.sub(r"(?<=\w)-\n(?=[a-zàèéìòù])", "", text)
    return text.strip()


def clean_for_tts(text: str, recurring_headers: set[str] | None = None) -> str:
    recurring_headers = recurring_headers or set()
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            out.append("")
            continue
        if s in recurring_headers:
            continue
        if re.fullmatch(r"\d{1,4}", s):
            continue
        s = re.sub(r"\s+", " ", s)
        out.append(s)
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def recurring_headers(page_texts: list[str]) -> set[str]:
    candidates = []
    for text in page_texts:
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        candidates.extend(lines[:2])
        candidates.extend(lines[-2:])
    counts = Counter(candidates)
    threshold = max(3, max(1, len(page_texts) // 3))
    return {line for line, count in counts.items() if count >= threshold and len(line) < 100}


def _sapi_to_wav(text: str, output: Path, rate: int = 0) -> None:
    if os.name != "nt":
        raise RuntimeError("Windows SAPI TTS is available only on Windows")
    safe_text = text.replace("'", "''")
    safe_out = str(output).replace("'", "''")
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Rate={int(rate)}; $s.SetOutputToWaveFile('{safe_out}'); "
        f"$s.Speak('{safe_text}'); $s.Dispose();"
    )
    subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], check=True, capture_output=True, text=True, timeout=180)


def _merge_wavs(paths: list[Path], output: Path) -> None:
    if not paths:
        return
    params = None
    frames = []
    expected = None
    for path in paths:
        with wave.open(str(path), "rb") as w:
            current = w.getparams()
            signature = (current.nchannels, current.sampwidth, current.framerate, current.comptype)
            if params is None:
                params = current
                expected = signature
            elif signature != expected:
                raise RuntimeError("Audio segment formats differ")
            frames.append(w.readframes(w.getnframes()))
    with wave.open(str(output), "wb") as out:
        out.setparams(params)
        for block in frames:
            out.writeframes(block)


def run_book_pipeline(input_dir: Path, output_dir: Path, synthesize_audio: bool = True) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    images = sorted([p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS], key=natural_key)
    if not images:
        raise RuntimeError("No book images found")
    from rapidocr import RapidOCR
    engine = RapidOCR()
    page_texts = []
    page_reports = []
    low_conf = 0
    for idx, image in enumerate(images, 1):
        result = engine(str(image))
        pairs = _extract_rapidocr(result)
        lines = []
        for text, score in pairs:
            if score < 0.55:
                lines.append(f"[DA VERIFICARE] {text}")
                low_conf += 1
            else:
                lines.append(text)
        faithful = clean_faithful(lines)
        page_texts.append(faithful)
        page_reports.append({"page": idx, "file": image.name, "lines": len(lines), "low_confidence": sum(1 for x in lines if x.startswith("[DA VERIFICARE]"))})
    faithful_all = "\n\n".join(page_texts).strip() + "\n"
    headers = recurring_headers(page_texts)
    tts_text = clean_for_tts(faithful_all, headers) + "\n"
    (output_dir / "testo_ocr_fedele.txt").write_text(faithful_all, encoding="utf-8")
    (output_dir / "testo_tts_pulito.txt").write_text(tts_text, encoding="utf-8")
    write_json(output_dir / "report_ocr.json", {"pages": page_reports, "recurring_headers_removed": sorted(headers), "low_confidence_lines": low_conf})
    audio_segments = []
    audio_error = None
    if synthesize_audio and os.name == "nt":
        seg_dir = output_dir / "audio_segmenti"
        seg_dir.mkdir(exist_ok=True)
        chunks = [x.strip() for x in re.split(r"\n\n+", tts_text) if x.strip()]
        for idx, chunk in enumerate(chunks, 1):
            path = seg_dir / f"segmento_{idx:04d}.wav"
            _sapi_to_wav(chunk, path)
            if not path.exists() or path.stat().st_size <= 44:
                raise RuntimeError(f"Invalid audio segment {path.name}")
            audio_segments.append(path)
        if audio_segments:
            _merge_wavs(audio_segments, output_dir / "audiolibro_finale.wav")
    elif synthesize_audio:
        audio_error = "Audio synthesis skipped: Windows SAPI unavailable on this platform"
    qa = {"status": "OK" if page_texts and tts_text.strip() else "PARZIALE", "pages": len(images), "characters_faithful": len(faithful_all), "characters_tts": len(tts_text), "low_confidence_lines": low_conf, "audio_segments": len(audio_segments), "audio_error": audio_error}
    write_json(output_dir / "report_finale_qa.json", qa)
    return qa
