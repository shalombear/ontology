# Benchmark Results (v1)

This report covers tests S1-S4 for ZIM path-resolution caching, compared with the v0 baseline. Raw measurements are recorded in [results.csv](results.csv).

## Results

### Execution Time and Peak Python Memory

| Test | Seed | Depth | v0 elapsed (seconds) | v1 elapsed (seconds) | Elapsed time reduction | v0 peak Python memory (MiB) | v1 peak Python memory (MiB) |
|---|---|---:|---:|---:|---:|---:|---:|
| S1 | Alphabet | 3 | 511.65 | 439.23 | 14.15% | 33.54 | 35.04 |
| S2 | Alphabet | 4 | 28,015.76 | 23,471.03 | 16.22% | 108.45 | 143.44 |
| S3 | Mathematics | 3 | 1,070.83 | 906.28 | 15.37% | 30.28 | 30.02 |
| S4 | Mathematics | 4 | 67,248.22 | 47,655.21 | 29.14% | 162.31 | 223.92 |

Peak Python memory covers allocations tracked by `tracemalloc`.

### ZIM Operations

| Test | v0 operations | v1 operations | Reduction | v1 ZIM time (seconds) |
|---|---:|---:|---:|---:|
| S1 | 132,618 | 61,409 | 53.69% | 102.42 |
| S2 | 7,020,731 | 1,991,388 | 71.64% | 3,218.20 |
| S3 | 296,587 | 142,989 | 51.79% | 243.62 |
| S4 | 14,451,137 | 3,329,772 | 76.96% | 6,590.24 |

Operations include instrumented entry lookups, existence checks, redirect retrievals, and content retrievals; their individual costs differ.

### SQL Operations

| Test | Reads | Writes | Read time (seconds) | Write time (seconds) | Transaction time (seconds) |
|---|---:|---:|---:|---:|---:|
| S1 | 434 | 1,078 | 0.54 | 13.36 | 15.82 |
| S2 | 31,324 | 78,289 | 36.86 | 816.30 | 993.84 |
| S3 | 998 | 2,488 | 1.29 | 33.07 | 39.37 |
| S4 | 76,555 | 191,357 | 86.08 | 1,833.36 | 2,234.50 |

Read and write counts match v0. Transaction time includes reads and writes within write transactions; these timings should not be added together.

### HTML Parsing and Link Processing

| Test | v0 parse time (seconds) | v1 parse time (seconds) | v0 link-processing time (seconds) | v1 link-processing time (seconds) |
|---|---:|---:|---:|---:|
| S1 | 76.88 | 71.90 | 418.71 | 351.10 |
| S2 | 3,485.33 | 3,417.67 | 23,316.42 | 18,957.78 |
| S3 | 148.02 | 141.41 | 889.49 | 723.80 |
| S4 | 7,802.60 | 7,454.36 | 56,946.56 | 37,705.76 |

Link-processing time includes HTML cleanup, link extraction, child ZIM operations, and redirect resolution. It overlaps with ZIM time and refresh parsing time; these timings should not be added together.

### Timing Summary

| Test | Mean ZIM operation (ms) | ZIM share of elapsed time | Parsing share | Link-processing share | SQL transaction share |
|---|---:|---:|---:|---:|---:|
| S1 | 1.668 | 23.32% | 16.37% | 79.93% | 3.60% |
| S2 | 1.616 | 13.71% | 14.56% | 80.77% | 4.23% |
| S3 | 1.704 | 26.88% | 15.60% | 79.87% | 4.34% |
| S4 | 1.979 | 13.83% | 15.64% | 79.12% | 4.69% |

All values refer to v1. Timing regions overlap, so percentages should not be summed. Mean ZIM operation time combines operation types with different costs.

### Granular v1.1 Link-Processing Measurements

A separate manual v1.1 test of Alphabet at depth 3 produced the following measurements:

| Stage | Time (seconds) | Share of measured link-processing time |
|---|---:|---:|
| Exclusion selection and removal | 256.59 | 70.47% |
| Anchor finding and filtering | 1.29 | 0.36% |
| Path construction | 0.14 | 0.04% |
| Child resolution | 106.09 | 29.14% |
| Total | 364.12 | 100.00% |

Percentages are rounded independently. These measurements are separate from the v1 S1-S4 results.

## Analysis

### Effect of Path-Resolution Caching

v1 reduced elapsed time by 14.15% to 29.14% across S1 through S4. ZIM operation counts fell by 51.79% to 76.96%, consistent with avoiding repeated resolution of previously encountered paths.

Peak Python memory rose by 32.26% in S2 and 37.96% in S4, the two depth 4 tests, while changing by less than 5% in either depth 3 test.

### Remaining Costs

Link processing accounted for 79.12-80.77% of v1 elapsed time. Although its absolute duration decreased in every test, it remained the largest measured region.

HTML parsing accounted for 14.56-16.37% of elapsed time, while SQL transactions accounted for 3.60-4.69%. SQL read and write counts were unchanged from v0.

These measurements supported investigating link processing before database optimization. However, its timer includes exclusion, link extraction, child ZIM operations, and redirect resolution; the aggregate measurements could not identify which component should be optimized next.

### Granular Link-Processing Analysis

In a separate v1.1 test of Alphabet at depth 3, we measured exclusion selection and removal at 256.59 seconds, or 70.47% of link-processing time. Child resolution ranked second at 106.09 seconds, or 29.14%.

We prioritized exclusion based on these measurements. Through code inspection, we identified an opportunity to combine exclusion and link extraction into one traversal that skips excluded subtrees, avoiding CSS selection and subtree destruction.

## Conclusions

The tests demonstrated that with path-resolution caching, we reduced elapsed time by 14.15-29.14% across S1-S4.

For v2, we selected a single traversal that skips excluded subtrees and collects eligible links directly. We will compare its runtime and extracted paths with the existing implementation to evaluate performance and correctness.