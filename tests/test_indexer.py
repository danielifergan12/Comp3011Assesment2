"""Tests for indexer module."""

from __future__ import annotations

import pytest

from crawler import CrawledPage
from indexer import INDEX_VERSION, Indexer, InvertedIndex, tokenize


def test_tokenize_normalizes_case_and_punctuation() -> None:
    tokens = tokenize("Hello, HELLO! It's me.")

    assert tokens == ["hello", "hello", "it's", "me"]


def test_build_index_tracks_frequency_positions_and_doc_freq() -> None:
    pages = [
        CrawledPage(url="u1", title="t1", text="Good friends are good"),
        CrawledPage(url="u2", title="t2", text="Good choices"),
    ]

    index = Indexer().build_index(pages)

    assert index.terms["good"][0].frequency == 2
    assert index.terms["good"][0].positions == [0, 3]
    assert index.doc_freq["good"] == 2
    assert index.documents[1].token_count == 2


def test_index_roundtrip_serialization() -> None:
    index = InvertedIndex()
    index.add_document(doc_id=0, url="u", title="t", text="alpha beta alpha")

    rebuilt = InvertedIndex.from_dict(index.to_dict())

    assert rebuilt.terms["alpha"][0].frequency == 2
    assert rebuilt.documents[0].title == "t"


def test_index_version_mismatch_raises_error() -> None:
    bad_data = {
        "index_version": INDEX_VERSION + 1,
        "documents": {},
        "doc_freq": {},
        "terms": {},
    }

    with pytest.raises(ValueError):
        InvertedIndex.from_dict(bad_data)
