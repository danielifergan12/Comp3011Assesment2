"""Tests for storage module."""

from __future__ import annotations

from pathlib import Path

import pytest

from indexer import InvertedIndex
from storage import IndexStorage


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    storage = IndexStorage(path)
    index = InvertedIndex()
    index.add_document(0, "u", "t", "alpha alpha")

    storage.save(index)
    loaded = storage.load()

    assert path.exists()
    assert loaded.terms["alpha"][0].frequency == 2


def test_load_missing_file_raises(tmp_path: Path) -> None:
    storage = IndexStorage(tmp_path / "missing.json")

    with pytest.raises(FileNotFoundError):
        storage.load()
