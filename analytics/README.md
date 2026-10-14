# Analytics core

This dependency-free Python module covers the parts of the prototype where silent errors are most dangerous:

- MCX response-date validation (`DD/MM/YYYY` request versus `MM/DD/YYYY` response)
- padded-symbol and compact-expiry parsing
- contract-specific quotation-base and purity normalization
- contract identity keyed by trading date, symbol, and expiry date
- specification versions selected by effective contract-expiry date
- lagged walk-forward z-scores
- one-session-delayed, transaction-cost-aware spread backtests
- byte-preserving raw archives, SHA-256 lineage, validation reports, and versioned cleaned JSON

Run the tests from this directory:

```bash
cd analytics
python3 -m unittest discover -v
```

## Import an official MCX export

Download a date-wise CSV from the [official MCX Bhavcopy page](https://www.mcxindia.com/market-data/bhavcopy), then run:

```bash
python3 analytics/pipeline.py ~/Downloads/BhavCopy.csv \
  --requested-date 14/10/2026 \
  --workspace .
```

The importer copies the original bytes into `data/raw/<dataset-id>/` before parsing, verifies the archive hash, and writes:

- `data/manifests/*.manifest.json` — source URL, UTC retrieval time, filename, byte size, raw SHA-256, specification hash, and validation-report link
- `data/reports/*.validation.json` — accepted, ignored, and rejected row counts with row-level reasons
- `data/clean/*.observations.v1.json` — only when every targeted row passes validation

`data/raw/` is ignored by Git to avoid redistributing exchange data; it must be retained with the research run. Manifests and validation reports are designed to be committed. A rejected import never produces a clean dataset.

The site blocks automated retrieval in some environments, including the current build environment. The pipeline therefore consumes a user-downloaded official export instead of hiding a third-party fallback. Legacy binary `.xls` files must be exported to CSV without altering rows; the original `.xls` should still be retained alongside the run by the researcher.

## Build a historical research snapshot

Merge validated daily outputs with `pipeline.merge_clean_datasets`, then run an explicit contract pair:

```bash
python3 analytics/run_research.py data/clean/mcx-history-….json \
  --candidate GOLDTEN --candidate-expiry 2026-10-30 \
  --reference GOLDM --reference-expiry 2026-11-05 \
  --lookback 40 --annual-carry-bps 0 \
  --output public/data/research/goldten-goldm.v1.json
```

The output is deterministic and self-hashed. It contains raw spread, declared carry adjustment, residual spread, trailing-only statistics, every eligibility gate, chronological partition labels, integer hedge sizes, actual-contract P&L, itemized costs, gold exposure, unexplained residual, drawdown, and cost sensitivity.
