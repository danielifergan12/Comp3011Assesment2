# COMP3011 Coursework 2 — Search Engine Tool

A command-line search engine for [`https://quotes.toscrape.com/`](https://quotes.toscrape.com/).
It crawls the target website politely, builds an inverted index of every word
occurrence, persists the index to disk, and answers single- and multi-word
queries against it.

## 1. Project overview

This repository is my submission for the COMP3011 "Web Services and Web Data"
Coursework 2. The four commands required by the brief are implemented as a
single interactive shell:

| Command          | Effect                                                                       |
|------------------|------------------------------------------------------------------------------|
| `build`          | Crawl the site, build the inverted index, save it to `data/index.json`.      |
| `load`           | Load a previously built index from `data/index.json` into memory.            |
| `print <word>`   | Print per-document postings (frequency + positions) for one or more words.   |
| `find <terms>`   | Return every page containing **all** query terms (AND semantics).            |

Case is ignored throughout — `Good` and `good` are the same term.

## 2. Repository layout

```
CourseAssignment2/
├── src/
│   ├── crawler.py       # Polite, domain-restricted BFS crawler
│   ├── indexer.py       # Tokenizer + inverted-index data model
│   ├── storage.py       # JSON persistence with schema versioning
│   ├── search.py        # print / find query engine
│   └── main.py          # Interactive CLI entry point
├── tests/
│   ├── conftest.py
│   ├── test_crawler.py
│   ├── test_indexer.py
│   ├── test_storage.py
│   ├── test_search.py
│   ├── test_cli.py
│   └── test_integration.py   # end-to-end build → save → load → find
├── data/
│   └── index.json       # Pre-built index (produced by `build`)
├── docs/
│   ├── demo_checklist.md
│   └── genai_usage.md   # GenAI declaration and critical reflection
├── requirements.txt
└── README.md
```

This matches the structure suggested in the assessment brief (page 8).

## 3. Architecture & design decisions

### Crawler — `src/crawler.py`

* **Breadth-first traversal** from the configured base URL, visiting only URLs
  whose scheme is `http`/`https`, whose netloc matches the base domain, and
  whose URL still starts with the base URL prefix.
* **Politeness window** of at least 6 seconds between successive requests, as
  required by the brief. Implemented with injected `sleep_func` and
  `monotonic_func` so timing is deterministically testable.
* **Explicit `User-Agent`** so the site owner can identify and contact us.
* **URL normalization** strips the fragment, query string, and trailing slash
  to avoid re-fetching the same logical page.
* **Defensive error handling**: any `requests.RequestException` is caught, the
  URL is skipped, and the crawl continues.

### Indexer — `src/indexer.py`

The inverted index is represented as three dictionaries:

```python
terms:      dict[str, dict[int, Posting]]   # term -> doc_id -> posting
documents:  dict[int, DocumentMeta]         # doc_id -> metadata
doc_freq:   dict[str, int]                  # term -> number of docs it appears in
```

Each `Posting` stores `frequency` and a list of `positions` (0-indexed token
offsets), which satisfies the brief's requirement to record "statistics (e.g.
frequency, position, etc) of each word in each page."

Why dictionaries of dictionaries?

* **O(1) average-case lookup** of a term's posting list, and **O(1)** lookup
  of a specific document's stats within that list — making both `print` and
  `find` fast even on larger corpora.
* **Efficient multi-word AND queries** via set intersection of posting keys
  (see `SearchEngine.find`).
* **Extensible**: `doc_freq` and per-document `token_count` are stored so that
  TF-IDF or BM25 ranking could be added later without re-indexing.

Tokenization uses the regex `[a-zA-Z0-9']+` so contractions like `it's` stay
whole, then lowercases each token to give case-insensitive matching.

### Storage — `src/storage.py`

A single JSON file at `data/index.json`, as allowed by the brief. An
`index_version` field is embedded in the payload and validated on load; an
incompatible schema raises `ValueError` with a clear message.

### Search — `src/search.py`

* `print_term` walks every query token, prints the posting list per document,
  and explicitly reports any tokens that are absent from the index.
* `find` tokenizes the query, computes the set intersection of each token's
  posting-doc keys (AND semantics), and ranks results by **summed term
  frequency**, with URL as a deterministic tiebreak. An empty query raises a
  `ValueError` that the CLI turns into a friendly message.

### CLI — `src/main.py`

A minimal, dependency-free shell that dispatches on the first whitespace
token. It handles blank input, unknown commands, Ctrl-D/EOF, and printing
before an index is loaded, all without crashing.

## 4. Setup

### 1) Create and activate a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

## 5. Usage

Run the CLI:

```bash
python3 src/main.py
```

Example session:

```text
COMP3011 Search Tool. Commands: build, load, print <word>, find <terms>, exit
> build
Build complete: pages=<depends on crawl> terms=<depends on crawl> saved=data/index.json
> load
Load complete: pages=<same as built index> terms=<same as built index> from=data/index.json
> print nonsense
Term: nonsense (doc_freq=1)
- doc_id=12 freq=1 positions=[218] url=https://quotes.toscrape.com/page/3
> find indifference
doc_id=7 score=1 title=Quotes to Scrape url=https://quotes.toscrape.com/page/2
> find good friends
doc_id=0 score=3 title=Quotes to Scrape url=https://quotes.toscrape.com
> exit
Exiting.
```

All four commands — `build`, `load`, `print`, `find` — are demonstrated in the
accompanying video.

## 6. Testing

Run the test suite with coverage:

```bash
python3 -m pytest --disable-warnings --cov=src --cov-report=term-missing
```

### Current status

* **37 tests, all passing**
* **98% line coverage for `src/`** (measured on Python 3.9.6):

  | Module           | Coverage |
  |------------------|---------:|
  | `src/crawler.py` |  98%     |
  | `src/indexer.py` | 100%     |
  | `src/main.py`    |  96%     |
  | `src/search.py`  |  96%     |
  | `src/storage.py` | 100%     |
  | **Total**        | **98%**  |

### Testing strategy

* **Unit tests** for every module (`test_crawler.py`, `test_indexer.py`,
  `test_storage.py`, `test_search.py`).
* **Mocked network + mocked clock** so crawler politeness and error handling
  can be verified deterministically without hitting the real website.
* **CLI dispatcher tests** (`test_cli.py`) cover every command, blank input,
  unknown input, EOF, and the entry-point function.
* **End-to-end integration test** (`test_integration.py`) runs the real
  crawler (against a fake session), real indexer, real storage, and real
  search engine in one pipeline — build → save → load → find.

### Edge cases covered

* Crawler handles request failures and returns `[]` when nothing can be
  fetched.
* URLs are normalised so `/page/1/?q=abc#sec` is the same as `/page/1`.
* External domains and `ftp://`-style URLs are rejected.
* Empty queries raise a clear error; missing terms return "no match" rather
  than crashing.
* An incompatible `index_version` on disk raises `ValueError` at load time.
* Missing index files raise `FileNotFoundError`, surfaced by the CLI as
  `Load failed: ...`.

## 7. Error handling

The implementation aims to fail softly wherever a user or the network can
misbehave:

| Failure mode                         | Behaviour                                        |
|--------------------------------------|--------------------------------------------------|
| Network request fails mid-crawl      | URL skipped, crawl continues                     |
| External / non-HTTP link found       | Ignored via `_is_allowed_url`                    |
| `load` before `build`                | `Load failed: Index file does not exist at …`    |
| `print` / `find` before `load`       | `No index loaded. Run build or load first.`      |
| Empty `find` query                   | `Query cannot be empty.`                         |
| Unknown command                      | `Unknown command: <token>`                       |
| Ctrl-D at the prompt                 | Clean exit with `Exiting.`                       |
| Incompatible index schema on disk    | `ValueError` with expected-vs-actual version     |

## 8. Rubric alignment (self-assessment)

| Criterion (weight)                          | Where it lives                                               |
|---------------------------------------------|--------------------------------------------------------------|
| Crawling Implementation (10%)               | `src/crawler.py` + `tests/test_crawler.py`                   |
| Indexing Implementation (10%)               | `src/indexer.py` + `tests/test_indexer.py`                   |
| Storage & Retrieval (8%)                    | `src/storage.py` + `tests/test_storage.py`                   |
| Search Functionality (12%)                  | `src/search.py` + `tests/test_search.py`                     |
| Testing & Test Coverage (20%)               | 37 tests, 98% coverage, integration + unit + CLI             |
| Code Quality & Documentation (10%)          | Modular code, type hints, docstrings, this README            |
| Version Control (5%)                        | Incremental Git history with scoped commits                  |
| GenAI Critical Evaluation (15%)             | [`docs/genai_usage.md`](docs/genai_usage.md)                 |
| Video Demonstration (10%)                   | 5-minute video (link submitted via Minerva)                  |

## 9. Dependencies

* `requests`
* `beautifulsoup4`
* `pytest`
* `pytest-cov`

## 10. Known limitations

* Ranking is deterministic summed-frequency, not TF-IDF/BM25.
* The search matches individual tokens with AND semantics, not exact phrase
  or proximity search.
* The crawler does not currently parse `robots.txt`; it relies on the mandated
  6-second politeness window and a descriptive `User-Agent`.

## 11. GenAI usage

See [`docs/genai_usage.md`](docs/genai_usage.md) for a declaration of the
GenAI tools used during development, specific examples of helpful and
unhelpful suggestions, and a reflection on the learning impact.
