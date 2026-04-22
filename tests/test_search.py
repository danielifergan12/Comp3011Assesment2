"""Tests for search module."""

from __future__ import annotations

import pytest

from indexer import InvertedIndex
from search import SearchEngine


@pytest.fixture
def engine() -> SearchEngine:
    index = InvertedIndex()
    index.add_document(0, "u1", "Title 1", "good friends good")
    index.add_document(1, "u2", "Title 2", "good habits")
    index.add_document(2, "u3", "Title 3", "friends forever")
    return SearchEngine(index)


def test_print_term_found(engine: SearchEngine) -> None:
    output = engine.print_term("Good")

    assert "Term: good" in output
    assert "doc_freq=2" in output
    assert "doc_id=0" in output
    assert "doc_id=1" in output


def test_print_term_missing(engine: SearchEngine) -> None:
    assert "not found" in engine.print_term("missing")


def test_print_term_multi_word_shows_stats_for_each(engine: SearchEngine) -> None:
    output = engine.print_term("good missing friends")

    assert "Term: good" in output
    assert "Term: friends" in output
    assert "Term 'missing' not found in index." in output


def test_find_single_word(engine: SearchEngine) -> None:
    results = engine.find("good")

    assert [result.doc_id for result in results] == [0, 1]
    assert results[0].score > results[1].score


def test_find_multi_word_and_semantics(engine: SearchEngine) -> None:
    results = engine.find("good friends")

    assert [result.doc_id for result in results] == [0]


def test_find_empty_query_raises(engine: SearchEngine) -> None:
    with pytest.raises(ValueError):
        engine.find("   ")


def test_find_unknown_terms_returns_empty(engine: SearchEngine) -> None:
    assert engine.find("unknown") == []
