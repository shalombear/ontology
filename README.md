# Wikipedia ZIM Knowledge Graph Crawler

This is a Python-based crawler for extracting Wikipedia article relationships from an offline ZIM archive and constructing a persistent knowledge graph using breadth-first search (BFS).

## Overview

This project explores the construction of navigable knowledge graphs from Wikipedia's internal hyperlink structure.

Starting from a specified Wikipedia article, the crawler traverses internal links breadth-first, identifies related articles, and stores the resulting directed graph in a SQLite database.

The architecture supports multiple independent seed articles, configurable traversal depths, and reuse of previously extracted article relationships.

The current implementation provides functional crawling, persistent graph storage, and performance instrumentation. Reproducible benchmarking and subsequent optimization remain development objectives.
## Features

- Offline Wikipedia extraction using `libzim`.
- HTML parsing using BeautifulSoup.
- Breadth-first traversal of article relationships.
- Configurable seed articles and maximum traversal depth.
- Internal hyperlink extraction and deduplication.
- Wikipedia redirect resolution, including HTML meta-refresh redirects.
- Filtering of navigational elements, references, and other non-content HTML.
- Persistent article and directed-edge storage.
- Support for multiple seed articles and overlapping traversal graphs.
- Tracking of article discovery depth and expansion status for each seed.
- Reuse of previously scanned article relationships.
- SQLite storage through SQLAlchemy.
- Performance instrumentation for ZIM operations, HTML parsing, link processing, and SQLite reads, writes, and transactions.
- Tracking of cache hits, cache misses, visited articles, processed edges, and BFS frontier sizes.
- Measurement of total execution time, peak Python memory allocation, and SQLite database size.

## Architecture

The project consists of two Python modules:

### `runscript.py`

Implements the crawling workflow:

1. Open the Wikipedia ZIM archive.
2. Accept a seed article and maximum traversal depth.
3. Resolve the seed article.
4. Retrieve and parse its HTML content.
5. Extract and resolve internal article links.
6. Traverse the resulting graph using BFS.
7. Read previously stored relationships when available.
8. Persist newly discovered articles and edges.
9. Track traversal state independently for each seed.
10. 10. Collect performance metrics for extraction, traversal, database operations, memory usage, and execution time.

### `database.py`

Defines the SQLite database connection and relational schema using SQLAlchemy.

The database contains four tables:

| Table | Purpose |
|---|---|
| `articles` | Stores unique article paths and scanning status. |
| `edges` | Stores directed parent-child article relationships. |
| `seeds` | Registers traversal seeds and their maximum depths. |
| `seed_nodes` | Tracks article discovery depth and expansion state for each seed. |

Article relationships are stored globally, while traversal depth and expansion status are maintained independently for each seed.

This design permits overlapping crawls without unnecessarily repeating previously completed article extraction.

## Project Structure

```text
projects/
├── data/
│   ├── wiki/
│   │   └── wikipedia_en_all_nopic_2026-06.zim
│   └── db/
│       └── wikipull.db
└── ontology/
    ├── .gitignore
    ├── database.py
    ├── runscript.py
    └── README.md
```

The Wikipedia archive and SQLite database reside outside the Git repository and are not version-controlled.

## Requirements

Initial development environment:

- Python 3.9.6
- SQLAlchemy 2.0
- libzim Python bindings
- BeautifulSoup4

Additional dependencies may be required depending on the development environment.

## Current Status

**Instrumented prototype**

Core extraction, traversal, persistence, and performance instrumentation have been implemented. Benchmark reporting, automated test execution, and performance comparisons remain pending.
The project remains under active development and is not considered production-ready.

Current limitations:

- Functional correctness has not been comprehensively validated.
- Performance instrumentation is implemented, but benchmark results are not yet systematically collected or compared.
- Benchmark metrics are collected in memory but are not yet reported or persisted to disk.
- Error handling and recovery require further hardening.
- Database and traversal performance have not been optimized.
- Scalability at greater graph depths remains to be established.

Preliminary execution has demonstrated shallow and deeper crawls, but these observations do not constitute a validated benchmark suite.

## Development Roadmap

1. Establish reproducible functional tests.
2. Complete benchmark reporting, automated execution, and reproducible baseline testing.
3. Improve error handling and recovery.
4. Optimize extraction and database operations.
5. Evaluate performance across multiple seeds and traversal depths.
6. Investigate alternative graph storage and query architectures where justified by benchmark results.
