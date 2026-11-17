# Benchmark Results (v2)

This report covers tests S1 through S4 for v2 of the Wikipedia ZIM crawler. In v2, a single traversal skips excluded HTML subtrees and collects eligible links. The report compares v2 with v1 and the v0 baseline, then uses the measured costs to select the next optimization target. Raw measurements are recorded in [results.csv](results.csv).

## Results

### Total Execution Time

| Test | Seed | Depth | v0 elapsed (seconds) | v1 elapsed (seconds) | v2 elapsed (seconds) | Reduction from v1 | Reduction from v0 |
|---|---|---:|---:|---:|---:|---:|---:|
| S1 | Alphabet | 3 | 511.65 | 439.23 | 193.56 | 55.93% | 62.17% |
| S2 | Alphabet | 4 | 28,015.76 | 23,471.03 | 7,842.07 | 66.59% | 72.01% |
| S3 | Mathematics | 3 | 1,070.83 | 906.28 | 416.72 | 54.02% | 61.08% |
| S4 | Mathematics | 4 | 67,248.22 | 47,655.21 | 16,864.53 | 64.61% | 74.92% |

### ZIM Operations

| Test | v1 operations | v2 operations | Reduction from v1 | v1 ZIM time (seconds) | v2 ZIM time (seconds) | Change in ZIM time |
|---|---:|---:|---:|---:|---:|---:|
| S1 | 61,409 | 42,354 | 31.03% | 102.42 | 100.95 | −1.43% |
| S2 | 1,991,388 | 1,370,338 | 31.19% | 3,218.20 | 3,217.57 | −0.02% |
| S3 | 142,989 | 98,240 | 31.30% | 243.62 | 233.19 | −4.28% |
| S4 | 3,329,772 | 2,297,870 | 30.99% | 6,590.24 | 6,868.84 | +4.23% |

### SQL Operations

| Test | Reads | Writes | Read time (seconds) | Write time (seconds) | Transaction time (seconds) |
|---|---:|---:|---:|---:|---:|
| S1 | 434 | 1,078 | 0.54 | 13.36 | 15.86 |
| S2 | 31,324 | 78,289 | 38.15 | 850.01 | 1,028.99 |
| S3 | 998 | 2,488 | 1.25 | 31.56 | 37.88 |
| S4 | 76,555 | 191,357 | 85.62 | 1,805.90 | 2,212.86 |

SQL transaction time overlaps with read and write time, so the three timings are not additive.

### HTML Parsing and Link Processing

| Test | v1 parse time (seconds) | v2 parse time (seconds) | Change in parse time | v1 link-processing time (seconds) | v2 link-processing time (seconds) | Change in link-processing time |
|---|---:|---:|---:|---:|---:|---:|
| S1 | 71.90 | 74.42 | +3.50% | 351.10 | 102.88 | -70.70% |
| S2 | 3,417.67 | 3,513.40 | +2.80% | 18,957.78 | 3,199.85 | -83.12% |
| S3 | 141.41 | 141.37 | -0.02% | 723.80 | 236.27 | -67.36% |
| S4 | 7,454.36 | 7,597.17 | +1.92% | 37,705.76 | 6,795.93 | -81.98% |

Parsing and link-processing times overlap and are not additive.

### Timing Summary

| Test | Mean ZIM operation time (ms) | ZIM operations (% of elapsed time) | HTML parsing (% of elapsed time) | Link processing (% of elapsed time) | SQL transactions (% of elapsed time) |
|---|---:|---:|---:|---:|---:|
| S1 | 2.384 | 52.16% | 38.45% | 53.15% | 8.19% |
| S2 | 2.348 | 41.03% | 44.80% | 40.80% | 13.12% |
| S3 | 2.374 | 55.96% | 33.93% | 56.70% | 9.09% |
| S4 | 2.989 | 40.73% | 45.05% | 40.30% | 13.12% |

Timing regions overlap, so the percentages are not additive.

### Peak Python Memory

| Test | v0 peak (MiB) | v1 peak (MiB) | v2 peak (MiB) |
|---|---:|---:|---:|
| S1 | 33.54 | 35.04 | 35.59 |
| S2 | 108.45 | 143.44 | 134.93 |
| S3 | 30.28 | 30.02 | 38.14 |
| S4 | 162.31 | 223.92 | 235.30 |

Peak Python memory covers allocations tracked by `tracemalloc`.

## Analysis

### Reduction in ZIM Operations

Version v2 removed redundant ZIM existence checks, reducing call counts by about 31% in every test. The checks were inexpensive, so measured ZIM time changed little.

### Effect of the Single Traversal

Version v2 extracts links and skips excluded subtrees in a single pass. This avoids the separate work of finding and removing excluded elements. Link processing took less than a third as long as in v1 in every test, accounting for most of the observed runtime savings.

### Remaining Costs

HTML parsing took about 45% of elapsed time in both depth 4 tests, making it the largest measured cost in those runs. Its duration changed little from v1 to v2, but it now accounts for a larger share of runtime because link processing is faster.

## Conclusion

Version v3 should prioritize HTML parsing. It accounted for about 45% of elapsed time in both depth 4 tests, the largest measured cost in those runs. The HTML tree construction and article-container lookup will be measured separately to determine where to focus the optimization.