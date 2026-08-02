from __future__ import annotations

import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
MODELS = BASE / "models"
MODEL_NAME = "vosk-model-small-it-0.22"
MODEL_DIR = MODELS / MODEL_NAME
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"


def validate_model(path: Path) -> bool:
    required = (path / "am" / "final.mdl", path / "conf" / "mfcc.conf", path / "conf" / "model.conf")
    return all(item.exists() for item in required)


def reporthook(block_number: int, block_size: int, total_size: int) -> None:
    downloaded = block_number * block_size
    if total_size > 0:
        percent = min(100, int(downloaded * 100 / total_size))
        print(f"\rDownload modello italiano: {percent:3d}%", end="", flush=True)
    else:
        print(f"\rScaricati {downloaded // 1024 // 1024} MB", end="", flush=True)


def main() -> int:
    MODELS.mkdir(parents=True, exist_ok=True)
    if validate_model(MODEL_DIR):
        print(f"Modello già installato: {MODEL_DIR}")
        return 0
    print("F1 Assistente Telefonico Offline")
    print("Download del modello italiano Vosk, circa 48 MB.")
    print(MODEL_URL)
    print()
    with tempfile.TemporaryDirectory(prefix="f1_vosk_") as temporary_folder:
        archive = Path(temporary_folder) / f"{MODEL_NAME}.zip"
        try:
            urllib.request.urlretrieve(MODEL_URL, archive, reporthook)
            print("\nEstrazione del modello...")
            with zipfile.ZipFile(archive) as source:
                source.extractall(MODELS)
        except Exception as exc:
            print(f"\nERRORE: download o estrazione non riusciti: {exc}", file=sys.stderr)
            return 1
    if not validate_model(MODEL_DIR):
        shutil.rmtree(MODEL_DIR, ignore_errors=True)
        print("ERRORE: il modello scaricato non contiene i file richiesti.", file=sys.stderr)
        return 1
    print(f"Modello installato correttamente in:\n{MODEL_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
