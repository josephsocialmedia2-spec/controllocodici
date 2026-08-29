import zipfile
from pathlib import Path

import pytest

from asa.watcher import _looks_like_book, _safe_extract


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
