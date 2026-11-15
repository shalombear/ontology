# Wikipedia ZIM Knowledge Graph Crawler

This is a Python-based crawler for extracting Wikipedia article relationships from an offline ZIM archive and constructing a persistent knowledge graph using breadth-first search (BFS).

## Overview

This project explores the construction of navigable knowledge graphs from Wikipedia's internal hyperlink structure.

Starting from a specified Wikipedia article, the crawler traverses internal links breadth-first, identifies related articles, and stores the resulting directed graph in a SQLite database.

The architecture supports multiple independent seed articles, configurable traversal depths, and reuse of previously extracted article relationships.

The current implementation provides functional crawling, persistent graph storage, performance instrumentation, automated benchmark execution, and CSV result collection. Baseline evaluation, comparative analysis, and subsequent optimization remain development objectives.

## Features

- Offline Wikipedia extraction using `libzim`.
- HTML parsing using BeautifulSoup.
- Breadth-first traversal of article relationships.
- Configurable seed articles and maximum traversal depth.
- Internal hyperlink extraction and deduplication.
- Wikipedia redirect resolution, including HTML meta-refresh redirects.
- In-memory caching of resolved article paths within each crawler execution.
- Filtering of navigational elements, references, and other non-content HTML.
- Persistent article and directed-edge storage.
- Support for multiple seed articles and overlapping traversal graphs.
- Tracking of article discovery depth and expansion status for each seed.
- Reuse of previously scanned article relationships.
- SQLite storage through SQLAlchemy.
- Performance instrumentation for ZIM operations, HTML parsing, link processing, and SQLite reads, writes, and transactions.
- Tracking of cache hits, cache misses, visited articles, processed edges, and BFS frontier sizes.
- Measurement of total execution time, peak Python memory allocation, and SQLite database size.
- Automated benchmark execution using `runtest.bat`.
- Controlled SQLite database resets between benchmark test cases.
- CSV persistence of benchmark measurements, test identifiers, and optimization versions.
- Automated cross-version benchmark analysis, comparing cumulative gains against v0 and incremental changes against the preceding version.

## Architecture

The project consists of two Python modules, a Windows batch script, and a PowerShell benchmark analyzer:
### `runscript.py`

Implements the crawling workflow:

1. Open the Wikipedia ZIM archive.
2. Accept a seed article, maximum traversal depth, and optional benchmark version and test identifier.
3. Extract and resolve internal article links. 
4. Traverse the resulting graph using BFS. 
5. Read previously stored relationships when available.
6. Persist newly discovered articles and edges.
7. Track traversal state independently for each seed.
8. Collect performance metrics for extraction, traversal, database operations, memory usage, and execution time.
9. Append benchmark measurements to the results CSV.

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

### `runtest.bat`

Automates the benchmark suite across multiple traversal configurations.

1. Accept an optimization version identifier or retrieve the current Git commit hash.
2. Execute 10 benchmark test cases comprising 16 crawler executions.
3. Reset the SQLite database between independent test cases.
4. Preserve database state between consecutive crawls within paired tests.
5. Pass the version and test identifier to `runscript.py`.
6. Stop execution if a test fails.

### `analyze_benchmarks.ps1`

Analyzes benchmark measurements collected in
`benchmarks/results.csv`.

1. Read benchmark results across optimization versions.
2. Match executions by test identifier.
3. Compare each version against the v0 baseline.
4. Compare each version against its immediate predecessor.
5. Calculate absolute measurements and percentage changes.
6. Report missing test results and reject duplicate records.
7. Generate `benchmarks/benchmark_results.md`.

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
    ├── analyze_benchmarks.ps1
    ├── benchmarks/
    │   ├── results.csv
    │   ├── v0_benchmark_results.md
    │   └── benchmark_results.md
    ├── database.py
    ├── runscript.py
    ├── runtest.bat
    └── README.md
```

The Wikipedia ZIM archive and SQLite database reside outside the Git repository and are not version-controlled.

Benchmark findings and optimization decisions will be documented in `benchmarks/report.md`. The analyzer will generate `benchmarks/benchmark_results.md` when comparative data across versions is available.

## Requirements

Initial development environment:

- Python 3.9.6
- SQLAlchemy 2.0
- libzim Python bindings
- BeautifulSoup4

Additional dependencies may be required depending on the development environment.

## Current Status

**Instrumented and benchmark-enabled prototype**

Core extraction, traversal, persistence, performance instrumentation, automated benchmark execution, CSV result collection, and comparative benchmark analysis have been implemented. Baseline testing and validation of cross-version comparisons remain pending.
The project remains under active development and is not considered production-ready.

Current limitations:

- Functional correctness has not been comprehensively validated.
- Automated benchmarking and comparative analysis are implemented, but cross-version performance results have not yet been validated.
- Error handling and recovery require further hardening.
- Database and traversal performance have not been optimized.
- Scalability at greater graph depths remains to be established.

Preliminary execution has demonstrated shallow and deeper crawls, but these observations do not constitute a validated benchmark suite.

## Development Roadmap

1. Establish reproducible functional tests.
2. Establish reproducible benchmark baselines and validate cross-version performance comparisons.
3. Improve error handling and recovery.
4. Optimize extraction and database operations.
5. Evaluate performance across multiple seeds and traversal depths.
6. Investigate alternative graph storage and query architectures where justified by benchmark results.
