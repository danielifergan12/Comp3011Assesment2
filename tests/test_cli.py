"""Tests for CLI module."""

from __future__ import annotations

from typing import Iterator

import main
from crawler import CrawledPage
from indexer import InvertedIndex


class StubStorage:
    """Test double for index storage."""

    def __init__(self, index: InvertedIndex | None = None) -> None:
        self._index = index
        self.saved: InvertedIndex | None = None

    def save(self, index: InvertedIndex) -> None:
        self.saved = index

    def load(self) -> InvertedIndex:
        if self._index is None:
            raise FileNotFoundError("missing")
        return self._index


class StubCrawler:
    """Returns static pages for build tests."""

    def __init__(
        self,
        base_url: str,
        max_pages: int | None = None,
        progress_callback=None,
    ) -> None:
        self.base_url = base_url
        self.max_pages = max_pages
        self.progress_callback = progress_callback

    def crawl(self) -> list[CrawledPage]:
        if self.progress_callback is not None:
            self.progress_callback(1, "u")
        return [CrawledPage(url="u", title="t", text="alpha beta")]


def test_print_requires_loaded_index(capsys) -> None:
    cli = main.SearchToolCLI()
    cli._print_term(["good"])

    captured = capsys.readouterr()
    assert "No index loaded" in captured.out


def test_print_usage_message(capsys) -> None:
    cli = main.SearchToolCLI()
    cli.index = InvertedIndex()

    cli._print_term([])

    captured = capsys.readouterr()
    assert "Usage: print <word>" in captured.out


def test_find_empty_query_message(capsys) -> None:
    idx = InvertedIndex()
    idx.add_document(0, "u", "t", "alpha")
    cli = main.SearchToolCLI()
    cli.index = idx

    cli._find([])

    captured = capsys.readouterr()
    assert "cannot be empty" in captured.out.lower()


def test_find_no_index_loaded(capsys) -> None:
    cli = main.SearchToolCLI()

    cli._find(["alpha"])

    captured = capsys.readouterr()
    assert "No index loaded" in captured.out


def test_find_no_matches(capsys) -> None:
    idx = InvertedIndex()
    idx.add_document(0, "u", "t", "alpha")
    cli = main.SearchToolCLI()
    cli.index = idx

    cli._find(["missing"])

    captured = capsys.readouterr()
    assert "No matching pages found" in captured.out


def test_load_reports_failure(capsys) -> None:
    cli = main.SearchToolCLI()
    cli.storage = StubStorage(index=None)

    cli._load()

    captured = capsys.readouterr()
    assert "Load failed" in captured.out


def test_load_success(capsys) -> None:
    idx = InvertedIndex()
    idx.add_document(0, "u", "t", "alpha")
    cli = main.SearchToolCLI()
    cli.storage = StubStorage(index=idx)

    cli._load()

    captured = capsys.readouterr()
    assert "Load complete" in captured.out


def test_dispatch_unknown_command(capsys) -> None:
    cli = main.SearchToolCLI()

    cli._dispatch("unknown")

    captured = capsys.readouterr()
    assert "Unknown command" in captured.out


def test_build_command_with_stub_crawler(monkeypatch, capsys) -> None:
    cli = main.SearchToolCLI()
    storage = StubStorage()
    cli.storage = storage
    monkeypatch.setattr(main, "Crawler", StubCrawler)

    cli._build()

    captured = capsys.readouterr()
    assert "Build started successfully" in captured.out
    assert "Build progress: crawled_pages=1" in captured.out
    assert "Crawl finished successfully" in captured.out
    assert "Build complete" in captured.out
    assert storage.saved is not None
    assert "alpha" in storage.saved.terms


def test_run_loop_exit(capsys, monkeypatch) -> None:
    cli = main.SearchToolCLI()
    inputs: Iterator[str] = iter(["exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    cli.run()

    captured = capsys.readouterr()
    assert "Commands:" in captured.out
    assert "Exiting." in captured.out


def test_run_loop_handles_blank_and_unknown(capsys, monkeypatch) -> None:
    cli = main.SearchToolCLI()
    inputs: Iterator[str] = iter(["", "   ", "wat", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    cli.run()

    captured = capsys.readouterr()
    assert "Unknown command: wat" in captured.out
    assert "Exiting." in captured.out


def test_run_loop_handles_eof(capsys, monkeypatch) -> None:
    cli = main.SearchToolCLI()

    def raise_eof(_: str) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)

    cli.run()

    captured = capsys.readouterr()
    assert "Exiting." in captured.out


def test_print_command_dispatches_to_engine(capsys) -> None:
    idx = InvertedIndex()
    idx.add_document(0, "u", "t", "alpha alpha beta")
    cli = main.SearchToolCLI()
    cli.index = idx

    cli._dispatch("print alpha")

    captured = capsys.readouterr()
    assert "Term: alpha" in captured.out
    assert "freq=2" in captured.out


def test_find_command_prints_results(capsys) -> None:
    idx = InvertedIndex()
    idx.add_document(0, "u0", "Title Zero", "good friends good")
    idx.add_document(1, "u1", "Title One", "good")
    cli = main.SearchToolCLI()
    cli.index = idx

    cli._dispatch("find good")

    captured = capsys.readouterr()
    assert "doc_id=0" in captured.out
    assert "doc_id=1" in captured.out
    assert "score=" in captured.out


def test_main_entrypoint_runs_cli(monkeypatch) -> None:
    called: list[bool] = []

    class FakeCLI:
        def run(self) -> None:
            called.append(True)

    monkeypatch.setattr(main, "SearchToolCLI", FakeCLI)
    main.main()

    assert called == [True]
