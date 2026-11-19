# Benchmark Results (v3)

This report covers tests S1-S4 for selective HTML tree construction, compared with v2 and the v0 baseline. Raw measurements are recorded in [results.csv](results.csv).

## Results

### Total Execution Time

| Test | Seed | Depth | v0 elapsed (s) | v2 elapsed (s) | v3 elapsed (s) | Saved vs. v2 (s) | Reduction from v2 | Reduction from v0 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| S1 | Alphabet | 3 | 511.65 | 193.56 | 169.99 | 23.57 | 12.18% | 66.78% |
| S2 | Alphabet | 4 | 28,015.76 | 7,842.07 | 6,638.25 | 1,203.82 | 15.35% | 76.31% |
| S3 | Mathematics | 3 | 1,070.83 | 416.72 | 374.70 | 42.02 | 10.08% | 65.01% |
| S4 | Mathematics | 4 | 67,248.22 | 16,864.53 | 13,109.88 | 3,754.65 | 22.26% | 80.51% |

### HTML Parsing

| Test | v2 parsing (s) | v3 parsing (s) | Parsing time reduction |
|---|---:|---:|---:|
| S1 | 74.42 | 45.85 | 38.39% |
| S2 | 3,513.40 | 2,193.27 | 37.57% |
| S3 | 141.37 | 90.20 | 36.20% |
| S4 | 7,597.17 | 4,814.35 | 36.63% |

### Share of Elapsed Time (v3)

| Test | ZIM | HTML parsing | Link processing | SQL transactions |
|---|---:|---:|---:|---:|
| S1 | 62.03% | 26.97% | 63.01% | 9.60% |
| S2 | 49.72% | 33.04% | 49.36% | 16.01% |
| S3 | 64.60% | 24.07% | 65.31% | 10.15% |
| S4 | 40.53% | 36.72% | 39.94% | 21.32% |

The timers overlap.

## Analysis

### Effect of Selective Tree Construction

Version v3 uses BeautifulSoup’s `SoupStrainer` to build a tree for the article container, avoiding Python object creation for elements outside it. If the selective parse cannot locate the article body, the crawler parses the full document to diagnose the missing container.

Across the tests, version v3 saved between 36.20% and 38.39% of the time v2 spent parsing HTML.

### Remaining Costs

HTML parsing still accounted for 33.04% of elapsed time in S2 and 36.72% in S4. ZIM operations and link processing each had larger reported shares in both tests. Those timers overlap because link processing includes some ZIM operations.

## Conclusion

Version v3 reduced total suite runtime by 19.84% relative to v2. Parsing still took roughly one third of elapsed time in both depth-4 tests. Additional time can possibly be saved by eliminating BeautifulSoup from the workflow altogether, which we will test.