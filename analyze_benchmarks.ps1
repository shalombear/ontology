
$ErrorActionPreference = "Stop"

$directory = Join-Path $PSScriptRoot "benchmarks"
$csv = Join-Path $directory "results.csv"
$report = Join-Path $directory "benchmark_results.md"

$baseline = "v0"
$results = @(Import-Csv $csv)

$metrics = @(
    "elapsed_seconds",
    "peak_python_mib",
    "database_bytes",
    "zim_operations",
    "cache_hits",
    "cache_misses",
    "articles_visited",
    "edges_processed",
    "sql_reads",
    "sql_writes",
    "zim_time",
    "parse_time",
    "sql_read_time",
    "sql_write_time",
    "sql_transaction_time",
    "link_processing_time"
)

if (-not ($results.version -contains $baseline)) {
    throw "Baseline version $baseline not found."
}

$duplicates = @(
    $results |
        Group-Object version, test_id |
        Where-Object { $_.Count -gt 1 }
)

if ($duplicates.Count -gt 0) {
    throw "Duplicate version/test records found in results.csv."
}

# Versions follow their first appearance in the CSV.
# Run each version's benchmark suite before starting the next.

$versions = @(
    $results.version |
        Select-Object -Unique
)

$lines = @(
    "# Benchmark Results",
    "",
    "Baseline: $baseline",
    ""
)

function Compare-Versions {
    param(
        [string]$Before,
        [string]$After,
        [string]$Comparison
    )

    $oldRows = @(
        $results | Where-Object { $_.version -eq $Before }
    )

    $newRows = @(
        $results | Where-Object { $_.version -eq $After }
    )

    $tests = @(
        @($oldRows.test_id) + @($newRows.test_id) |
            Sort-Object -Unique
    )

    $script:lines += "### $Comparison`: $Before vs $After"
    $script:lines += ""

    foreach ($test in $tests) {
        $old = @(
            $oldRows | Where-Object { $_.test_id -eq $test }
        )

        $new = @(
            $newRows | Where-Object { $_.test_id -eq $test }
        )

        $script:lines += "#### $test"
        $script:lines += ""

        if ($old.Count -eq 0) {
            $script:lines += "Missing result for $Before."
            $script:lines += ""
            continue
        }

        if ($new.Count -eq 0) {
            $script:lines += "Missing result for $After."
            $script:lines += ""
            continue
        }

        $script:lines += (
            "| Metric | $Before | $After | Change (%) |"
        )
        $script:lines += "|---|---:|---:|---:|"

        foreach ($metric in $metrics) {
            $a = [double]::Parse(
                $old[0].$metric,
                [cultureinfo]::InvariantCulture
            )

            $b = [double]::Parse(
                $new[0].$metric,
                [cultureinfo]::InvariantCulture
            )

            $change = if ($a -eq 0) {
                if ($b -eq 0) {
                    "0.00%"
                } else {
                    "N/A"
                }
            } else {
                "{0:+0.00;-0.00;0.00}%" -f (
                    100 * ($b - $a) / $a
                )
            }

            $script:lines += (
                "| $metric | $a | $b | $change |"
            )
        }

        $script:lines += ""
    }
}

for ($i = 1; $i -lt $versions.Count; $i++) {
    $current = $versions[$i]
    $previous = $versions[$i - 1]

    $lines += "## Version $current"
    $lines += ""

    Compare-Versions `
        -Before $baseline `
        -After $current `
        -Comparison "Cumulative"

    if ($previous -ne $baseline) {
        Compare-Versions `
            -Before $previous `
            -After $current `
            -Comparison "Incremental"
    }
}

$lines | Set-Content $report -Encoding UTF8

Write-Host "Generated $report"
