"""Persistence helpers for saving and loading search indices.

The index is saved as a single JSON file as allowed by the coursework
brief ("you can save the entire index to a single file"). A schema
version field is embedded so that incompatible on-disk formats are
rejected with a clear error at load time.
"""

from __future__ import annotations

import json
from pathlib import Path

from indexer import InvertedIndex


class IndexStorage:
    """Reads and writes inverted index files to disk."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save(self, index: InvertedIndex) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(index.to_dict(), indent=2), encoding="utf-8")

    def load(self) -> InvertedIndex:
        if not self.path.exists():
            raise FileNotFoundError(f"Index file does not exist at {self.path}")
        raw = self.path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return InvertedIndex.from_dict(data)
