import json
import zipfile
from pathlib import Path

import pytest

from asa.watcher import _looks_like_book, _move_failed_item, _safe_extract


def test_image_only_folder_is_book(tmp_path: Path):
    (tmp_path / "001.jpg").write_bytes(b"fake")
    (tmp_path / "002.png").write_bytes(b"fake")
    assert _looks_like_book(tmp_path) is True


def test_mixed_project_is_not_auto_book(tmp_path: Path):
    (tmp_path / "001.jpg").write_bytes(b"fake")
    (tmp_path / "main.py").write_text("print('x')\n", encoding="utf-8")
    assert _looks_like_book(tmp_path) is False


def test_zip_path_traversal_is_blocked(tmp_path: Path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../escape.txt", "blocked")
    destination = tmp_path / "out"
    destination.mkdir()
    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(RuntimeError):
            _safe_extract(zf, destination)
    assert not (tmp_path / "escape.txt").exists()


def test_failed_folder_is_removed_from_inbox_and_gets_error_report(tmp_path: Path):
    inbox = tmp_path / "INBOX"
    failed = tmp_path / "FAILED"
    inbox.mkdir()
    failed.mkdir()
    item = inbox / "cliente"
    item.mkdir()
    (item / "main.py").write_text("print('x')\n", encoding="utf-8")

    moved = _move_failed_item(item, failed, RuntimeError("Ollama non raggiungibile"))

    assert moved is not None
    assert not item.exists()
    assert moved.exists()
    report = json.loads((moved / "error.json").read_text(encoding="utf-8"))
    assert report["status"] == "FAILED"
    assert "Ollama non raggiungibile" in report["error"]
