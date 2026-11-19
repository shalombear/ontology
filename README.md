# Wikipedia ZIM Knowledge Graph Crawler

This is a Python-based crawler for extracting Wikipedia article relationships from an offline ZIM archive and constructing a persistent knowledge graph using breadth-first search (BFS).

## Overview

This project explores the construction of navigable knowledge graphs from Wikipedia's internal hyperlink structure.

Starting from a specified Wikipedia article, the crawler traverses internal links breadth-first, identifies related articles, and stores the resulting directed graph in a SQLite database.

The architecture supports multiple independent seed articles, configurable traversal depths, and reuse of previously extracted article relationships.

The current implementation provides functional crawling, persistent graph storage, performance instrumentation, automated benchmark execution, and CSV result collection. Initial baseline testing and comparative performance analysis are complete. Implemented optimizations include path-resolution caching, single-pass link extraction that skips excluded HTML subtrees, and selective HTML tree construction using BeautifulSoup’s SoupStrainer.

## Features

- Offline Wikipedia article extraction from ZIM archives.
- Breadth-first traversal with configurable seed article and depth.
- Internal hyperlink extraction and deduplication, with filtering of navigational elements, references, and other non-content HTML.
- Wikipedia redirect resolution, including HTML meta-refresh redirects.
- Persistent article and directed-edge storage in SQLite.
- Support for overlapping seed graphs with independent discovery-depth and expansion tracking.
- Reuse of previously extracted article relationships.
 
## Benchmarking

- Performance instrumentation for ZIM operations, HTML parsing, link processing, and database operations.
- Tracking of traversal counts, database cache usage, execution time, peak Python memory allocation, and database size.
- Automated benchmark execution with controlled database resets.
- CSV recording of benchmark measurements, test identifiers, and optimization versions.
- Automated cross-version analysis comparing each version with both the original baseline and its immediate predecessor.

## Architecture

The project consists of two Python modules, a Windows batch script, and a PowerShell benchmark analyzer:

### `runscript.py`

Implements the crawling workflow:

1. Open the Wikipedia ZIM archive.
2. Accept a seed article, maximum traversal depth, and optional benchmark version and test identifier.
3. Resolve the seed article and initialize its traversal state.
4. Traverse articles breadth-first, reusing stored relationships when available.
5. For unscanned articles, collect internal links in a single traversal that skips excluded HTML subtrees, then resolve their destinations.
6. Persist article relationships and update discovery depth and expansion status for the current seed. 
7. Collect performance metrics for extraction, traversal, database operations, memory usage, and execution time.
8. Append benchmark measurements to the results CSV.

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
2. Run the configured benchmark cases.
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
    │   ├── v1_benchmark_results.md 
    │   ├── v2_benchmark_results.md
    │   ├── v3_benchmark_results.md  
    │   └── benchmark_results.md
    ├── database.py
    ├── runscript.py
    ├── runtest.bat
    └── README.md
```

The Wikipedia ZIM archive and SQLite database reside outside the Git repository and are not version-controlled.

Benchmark findings and optimization decisions are documented in version-specific reports under `benchmarks/`. The analyzer generates `benchmarks/benchmark_results.md` from the recorded measurements.

## Requirements

- Python 3.9.6
- SQLAlchemy 2.0
- libzim
- lxml

## Current Status

Core extraction, traversal, persistence, performance instrumentation, automated benchmark execution, CSV result collection, and comparative benchmark analysis have been implemented. Comparative benchmarking for S1 through S4 is complete through v3.

The project remains under active development and is not considered production-ready.

## Current limitations:

- Functional correctness has not been comprehensively validated.
- Cross-version comparisons cover tests S1-S4; the remaining benchmark cases and repeated measurements are pending.
- Error handling and recovery require further hardening.
- Database operations and BFS traversal are candidates for further optimization.
- Scalability at greater graph depths remains to be established.

## Development Roadmap

1. Establish reproducible functional tests.
2. Complete the remaining benchmark cases and repeat measurements to assess variability and validate cross-version performance comparisons.
3. Improve error handling and recovery.
4. Optimize extraction and database operations.
5. Evaluate performance across multiple seeds and traversal depths.
6. Investigate alternative graph storage and query architectures where justified by benchmark results.
