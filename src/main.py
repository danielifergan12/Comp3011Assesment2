"""CLI entry point for the COMP3011 search tool.

Provides an interactive shell with the four commands mandated by the
coursework brief: ``build``, ``load``, ``print``, and ``find``. The shell
also accepts ``exit`` / ``quit`` and Ctrl-D (EOF) for a clean exit.
"""

from __future__ import annotations

from pathlib import Path

from crawler import Crawler
from indexer import Indexer, InvertedIndex
from search import SearchEngine
from storage import IndexStorage

BASE_URL = "https://quotes.toscrape.com/"
INDEX_PATH = Path("data/index.json")


class SearchToolCLI:
    """Interactive shell exposing build/load/print/find commands."""

    def __init__(self) -> None:
        self.storage = IndexStorage(INDEX_PATH)
        self.index: InvertedIndex | None = None

    def run(self) -> None:
        print("COMP3011 Search Tool. Commands: build, load, print <word>, find <terms>, exit")
        while True:
            try:
                raw = input("> ").strip()
            except EOFError:
                print("\nExiting.")
                return

            if not raw:
                continue

            if raw in {"exit", "quit"}:
                print("Exiting.")
                return

            self._dispatch(raw)

    def _dispatch(self, raw: str) -> None:
        command, *args = raw.split()
        if command == "build":
            self._build()
        elif command == "load":
            self._load()
        elif command == "print":
            self._print_term(args)
        elif command == "find":
            self._find(args)
        else:
            print(f"Unknown command: {command}")

    def _build(self) -> None:
        print("Building index (full crawl)...")
        print("Build started successfully. Crawling in progress...")

        def on_progress(crawled_count: int, latest_url: str) -> None:
            # Frequent but compact progress output for long polite crawls.
            if crawled_count == 1 or crawled_count % 10 == 0:
                print(
                    f"Build progress: crawled_pages={crawled_count} latest={latest_url}"
                )

        crawler = Crawler(base_url=BASE_URL, progress_callback=on_progress)
        pages = crawler.crawl()
        print(f"Crawl finished successfully. Total pages crawled: {len(pages)}")
        indexer = Indexer()
        self.index = indexer.build_index(pages)
        self.storage.save(self.index)
        print(
            f"Build complete: pages={len(self.index.documents)} terms={len(self.index.terms)} saved={INDEX_PATH}"
        )

    def _load(self) -> None:
        try:
            self.index = self.storage.load()
        except (FileNotFoundError, ValueError) as exc:
            print(f"Load failed: {exc}")
            return
        print(
            f"Load complete: pages={len(self.index.documents)} terms={len(self.index.terms)} from={INDEX_PATH}"
        )

    def _print_term(self, args: list[str]) -> None:
        if self.index is None:
            print("No index loaded. Run build or load first.")
            return
        if not args:
            print("Usage: print <word> [<word> ...]")
            return
        engine = SearchEngine(self.index)
        print(engine.print_term(" ".join(args)))

    def _find(self, args: list[str]) -> None:
        if self.index is None:
            print("No index loaded. Run build or load first.")
            return
        query = " ".join(args)
        engine = SearchEngine(self.index)
        try:
            results = engine.find(query)
        except ValueError as exc:
            print(str(exc))
            return

        if not results:
            print("No matching pages found.")
            return

        for result in results:
            print(
                f"doc_id={result.doc_id} score={result.score} title={result.title} url={result.url}"
            )


def main() -> None:
    """Run the interactive shell."""
    SearchToolCLI().run()


if __name__ == "__main__":
    main()
