"""Search and query utilities for the inverted index.

Exposes the ``SearchEngine`` class which implements the two query-time
commands required by the coursework brief:

* ``print <word>`` — shows per-document statistics for a term.
* ``find <term1> <term2> ...`` — returns documents containing **all**
  query terms (AND semantics), ranked by summed term frequency.

All matching is case-insensitive and uses the same tokenizer as the
indexer so that query terms normalize identically to indexed terms.
"""

from __future__ import annotations

from dataclasses import dataclass

from indexer import InvertedIndex, tokenize


@dataclass(frozen=True)
class SearchResult:
    """A scored search result document."""

    doc_id: int
    url: str
    title: str
    score: int


class SearchEngine:
    """Executes print/find operations on an in-memory index."""

    def __init__(self, index: InvertedIndex) -> None:
        self.index = index

    def print_term(self, term: str) -> str:
        tokens = tokenize(term)
        if not tokens:
            return "Please provide a non-empty word for print."

        sections: list[str] = []
        for normalized in tokens:
            postings = self.index.terms.get(normalized)
            if not postings:
                sections.append(f"Term '{normalized}' not found in index.")
                continue
            lines = [
                f"Term: {normalized} (doc_freq={self.index.doc_freq.get(normalized, 0)})"
            ]
            for doc_id in sorted(postings):
                posting = postings[doc_id]
                doc = self.index.documents[doc_id]
                lines.append(
                    f"- doc_id={doc_id} freq={posting.frequency} "
                    f"positions={posting.positions} url={doc.url}"
                )
            sections.append("\n".join(lines))
        return "\n\n".join(sections)

    def find(self, query: str) -> list[SearchResult]:
        tokens = tokenize(query)
        if not tokens:
            raise ValueError("Query cannot be empty.")

        posting_sets = [set(self.index.terms.get(token, {}).keys()) for token in tokens]
        if not posting_sets:
            return []

        matched_doc_ids = set.intersection(*posting_sets) if posting_sets else set()
        results: list[SearchResult] = []
        for doc_id in matched_doc_ids:
            score = 0
            for token in tokens:
                score += self.index.terms[token][doc_id].frequency
            doc = self.index.documents[doc_id]
            results.append(
                SearchResult(doc_id=doc_id, url=doc.url, title=doc.title, score=score)
            )

        return sorted(results, key=lambda item: (-item.score, item.url))
