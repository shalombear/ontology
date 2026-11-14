# Benchmark Results (v0)

This report covers baseline tests S1-S4. Raw measurements are recorded in [results.csv](results.csv).

## Results

### Baseline

#### Total Execution Time
| Test | Seed | Depth | Elapsed time (seconds) |
|---|---|---:|---:|
| S1 | Alphabet | 3 | 511.65 |
| S2 | Alphabet | 4 | 28,015.76 |
| S3 | Mathematics | 3 | 1,070.83 |
| S4 | Mathematics | 4 | 67,248.22 |

#### ZIM Operations
| Test | Operations | ZIM time (seconds) | Mean per operation (ms) | Share of elapsed time |
|---|---:|---:|---:|---:|
| S1 | 132,618 | 159.61 | 1.204 | 31.20% |
| S2 | 7,020,731 | 11,632.57 | 1.657 | 41.52% |
| S3 | 296,587 | 394.37 | 1.330 | 36.83% |
| S4 | 14,451,137 | 23,916.93 | 1.655 | 35.57% |

#### SQL Operations

| Test | Reads | Writes | Read time (seconds) | Write time (seconds) | Transaction time (seconds) | Transaction share of elapsed time |
|---|---:|---:|---:|---:|---:|---:|
| S1 | 434 | 1,078 | 0.58 | 13.85 | 16.32 | 3.19% |
| S2 | 31,324 | 78,289 | 39.18 | 972.59 | 1,146.96 | 4.09% |
| S3 | 998 | 2,488 | 1.31 | 32.30 | 33.50 | 3.13% |
| S4 | 76,555 | 191,357 | 101.93 | 2,232.94 | 2,326.41 | 3.46% |

Read and write counts represent instrumented statement executions, not rows.
Transaction time includes reads and writes within write transactions; these timings should not be added together.

#### HTML Parsing and Link Processing

| Test | Parse time (seconds) | Link-processing time (seconds) |
|---|---:|---:|
| S1 | 76.88 | 418.71 |
| S2 | 3,485.33 | 23,316.42 |
| S3 | 148.02 | 889.49 |
| S4 | 7,802.60 | 56,946.56 |

Link-processing time includes HTML cleanup, link extraction, child ZIM operations, and redirect resolution. It overlaps with ZIM time and redirect parsing time; these timings should not be added together.

#### Traversal, Cache, and Resources

| Test | Articles expanded | Edges processed | Frontier sizes by depth | SQLite cache hits | SQLite cache misses | Peak Python memory (MiB) | Database size (bytes) |
|---|---:|---:|---|---:|---:|---:|---:|
| S1 | 215 | 36,693 | 1: 1; 2: 214 | 0 | 215 | 33.54 | 2,207,744 |
| S2 | 15,671 | 2,060,873 | 1: 1; 2: 214; 3: 15,456 | 0 | 15,671 | 108.45 | 109,596,672 |
| S3 | 497 | 86,122 | 1: 1; 2: 496 | 0 | 497 | 30.28 | 5,578,752 |
| S4 | 38,293 | 4,247,882 | 1: 1; 2: 496; 3: 37,796 | 0 | 38,293 | 162.31 | 209,268,736 |

Frontier sizes cover processed depths only. Peak Python memory excludes allocations not tracked by `tracemalloc`.

## Analysis

### ZIM and SQL Costs

Across the four baseline runs, measured ZIM operations accounted for 31.20-41.52% of elapsed time, compared with 3.13-4.09% for SQL transactions. Separately measured SQL read time remained below 0.2% in every run, although some reads overlap with transaction time.

Measured ZIM time substantially exceeded time spent in instrumented SQL operations, supporting its selection as an optimization target.
### HTML Parsing and Link Processing

Link processing accounted for approximately 81.8-84.7% of elapsed time across the four runs. This interval includes HTML cleanup, link extraction, child ZIM operations, and redirect resolution.

The measurements locate most execution time within link processing, but do not fully distinguish the contributions of its individual steps.

### Growth with Traversal Depth

Increasing maximum depth from 3 to 4 increased the number of expanded articles approximately 73-fold for Alphabet and 77-fold for Mathematics. Elapsed time increased approximately 55-fold and 63-fold, respectively.

Runtime grew less than the expanded-article count for both seeds. Per-article costs vary with content size, outgoing links, and resolution work; these two depths do not establish a general scaling law.

### Average ZIM Operation Time

Mean ZIM operation time increased with depth for both seeds. Because the metric combines different operation types, this increase cannot be attributed specifically to slower path lookups.

### Computational Complexity

Let:

- L = total child-path occurrences processed across expanded articles, after per-article deduplication.
- R = average number of entries examined per resolution without caching.
- N = number of entries in the ZIM archive.
- U = number of distinct paths encountered across those resolution chains, including intermediate redirect targets.

Using O(log N) as an upper bound for each entry lookup, uncached lookup work is:

    O(L * R * log N)

With caching, each distinct path is resolved once. Subsequent occurrences use expected constant-time dictionary lookups, giving:

    O(L + U * log N)

This model assumes successful, terminating resolution and bounded path lengths. It excludes content reading and parsing. Native redirects need not perform binary search at every step; unsuccessful lookups remain uncached.

The potential saving comes from avoiding repeated resolution. Since the baseline does not measure U or R, the model explains the optimization mechanism without predicting its speedup.
### SQLite Cache Behavior

All four runs recorded zero SQLite cache hits: every expanded article required ZIM extraction. These runs therefore do not measure the benefit of reusing previously stored article relationships.

### Measurement Limitations

Each configuration has one recorded run, so run-to-run variability has not been established.

Matching traversal counts across versions can identify some regressions, but equal counts alone do not establish identical graph contents.

Timings were collected with performance instrumentation and `tracemalloc` enabled. They describe instrumented execution and may differ from uninstrumented runtime.

## Conclusions

ZIM operations were a substantially larger measured cost than SQL operations. Code inspection identified repeated path lookups and redirect resolution when different articles linked to the same target.

Path-resolution caching was therefore selected for v1. It reuses resolved destinations within each run, trading additional memory for fewer ZIM operations.