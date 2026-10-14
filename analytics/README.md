# Analytics core

This dependency-free Python module covers the parts of the prototype where silent errors are most dangerous:

- MCX response-date validation (`DD/MM/YYYY` request versus `MM/DD/YYYY` response)
- padded-symbol and compact-expiry parsing
- contract-specific quotation-base and purity normalization
- expiry-preserving observations
- lagged walk-forward z-scores
- one-session-delayed, transaction-cost-aware spread backtests

Run the tests from this directory:

```bash
python3 -m unittest -v
```

The module intentionally accepts downloaded CSV input instead of depending on an undocumented website endpoint. Raw files should be stored outside version control and checksummed before processing.
