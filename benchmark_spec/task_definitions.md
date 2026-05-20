# Benchmark Task Definitions

## Canonical schema

Each implementation should normalize the raw CSV into:
- symbol
- date
- open
- high
- low
- close
- volume

## Tasks

### parse_only
Read and validate rows.

### summary
Group by symbol and compute row count, average close, min close, max close, total volume.

### analytics
For each symbol sorted by date compute daily return, 7-day moving average, 30-day moving average.

### top_movers
Find top 20 symbols by largest gain, largest loss, and highest average volume.

## Benchmark rules
- Same raw file
- Same logical outputs
- Multiple runs
- Median runtime for reporting
