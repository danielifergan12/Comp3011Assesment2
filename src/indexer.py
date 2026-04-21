"""Indexer and in-memory inverted index models.

Data model rationale:

* ``terms[token][doc_id] -> Posting`` gives O(1) average-case lookup of a
  term's posting list, and O(1) lookup of a specific document's stats
  within that list (useful for scoring).
* ``Posting`` stores ``frequency`` (number of occurrences in the doc)
  and ``positions`` (0-indexed token offsets). The brief requires word
  statistics ("frequency, position, etc") so both are persisted.
* ``doc_freq[token]`` is maintained alongside postings so IDF-style
  extensions can be added without re-scanning the index.
* ``documents[doc_id]`` stores per-document metadata (``url``, ``title``,
  ``token_count``) for display and potential length-normalised ranking.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from crawler import CrawledPage

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9']+")
INDEX_VERSION = 1


@dataclass
class Posting:
    """A posting entry for one term in one document."""

    doc_id: int
    frequency: int = 0
    positions: list[int] = field(default_factory=list)


@dataclass
class DocumentMeta:
    """Metadata for a crawled document."""

    doc_id: int
    url: str
    title: str
    token_count: int


@dataclass
class InvertedIndex:
    """Stores documents and postings for searchable terms."""

    terms: dict[str, dict[int, Posting]] = field(default_factory=dict)
    documents: dict[int, DocumentMeta] = field(default_factory=dict)
    doc_freq: dict[str, int] = field(default_factory=dict)
    index_version: int = INDEX_VERSION

    def add_document(self, doc_id: int, url: str, title: str, text: str) -> None:
        tokens = tokenize(text)
        self.documents[doc_id] = DocumentMeta(
            doc_id=doc_id,
            url=url,
            title=title,
            token_count=len(tokens),
        )

        seen_terms: set[str] = set()
        for position, token in enumerate(tokens):
            postings = self.terms.setdefault(token, {})
            posting = postings.get(doc_id)
            if posting is None:
                posting = Posting(doc_id=doc_id)
                postings[doc_id] = posting
            posting.frequency += 1
            posting.positions.append(position)
            if token not in seen_terms:
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1
                seen_terms.add(token)

    def to_dict(self) -> dict[str, Any]:
        """Serialize index into a JSON-compatible dictionary."""
        return {
            "index_version": self.index_version,
            "documents": {
                str(doc_id): asdict(meta) for doc_id, meta in self.documents.items()
            },
            "doc_freq": self.doc_freq,
            "terms": {
                term: {
                    str(doc_id): {
                        "doc_id": posting.doc_id,
                        "frequency": posting.frequency,
                        "positions": posting.positions,
                    }
                    for doc_id, posting in postings.items()
                }
                for term, postings in self.terms.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InvertedIndex":
        """Deserialize index from JSON-compatible dictionary."""
        version = data.get("index_version")
        if version != INDEX_VERSION:
            raise ValueError(
                f"Unsupported index_version={version}; expected {INDEX_VERSION}."
            )

        index = cls(index_version=version)
        for doc_id_str, meta_data in data.get("documents", {}).items():
            doc_id = int(doc_id_str)
            index.documents[doc_id] = DocumentMeta(**meta_data)

        index.doc_freq = {str(k): int(v) for k, v in data.get("doc_freq", {}).items()}

        for term, postings_data in data.get("terms", {}).items():
            postings: dict[int, Posting] = {}
            for doc_id_str, posting_data in postings_data.items():
                doc_id = int(doc_id_str)
                postings[doc_id] = Posting(
                    doc_id=int(posting_data["doc_id"]),
                    frequency=int(posting_data["frequency"]),
                    positions=[int(pos) for pos in posting_data["positions"]],
                )
            index.terms[term] = postings
        return index


class Indexer:
    """Builds an inverted index from crawled pages."""

    def build_index(self, pages: list[CrawledPage]) -> InvertedIndex:
        index = InvertedIndex()
        for doc_id, page in enumerate(pages):
            index.add_document(doc_id=doc_id, url=page.url, title=page.title, text=page.text)
        return index


def tokenize(text: str) -> list[str]:
    """Convert raw text into normalized, case-insensitive tokens."""
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]
