# Architecture

## Data paths

```text
Official MCX Bhavcopy CSV
  → immutable raw archive + SHA-256
  → strict row validation + rejection report
  → versioned daily clean JSON
  → hash-verified historical merge
  → expiry-aware walk-forward engine
  → versioned research snapshot
  → React dashboard

Supplementary APIs
  → provider-specific Python adapter
  → bounded retry + disk cache + schema validation
  → explicit unit/time normalization
  → contextual snapshot
  → React Global Gold / Data Source views
```

MCX observations and contextual API observations never share an implicit price type. MCX rows are domestic exchange futures contracts identified by trading date, symbol, and expiry. Goldprice.dev observations are international XAU/USD spot references; Frankfurter observations are daily reference FX. Context providers cannot replace a missing MCX record.

## Runtime model

The deployable application is a static Vite build served by Caddy on Railway. Python jobs run before deployment or as an explicit refresh job and publish immutable JSON snapshots under `public/data/`. API secrets are read only by Python from environment variables and are never exposed through `VITE_` variables or browser bundles.

The dashboard can also load a generated research snapshot from the user's machine. It does not send the file to a server. Official raw CSV validation remains a Python pipeline responsibility so browser code cannot create a false `VERIFIED HISTORICAL` claim.

## Storage decision

Filesystem JSON is intentional for the hackathon prototype:

- raw data and every derived artifact can be hashed and inspected;
- research runs are deterministic and Git-friendly where licensing permits;
- no database or cloud account is required for judging;
- idempotency is enforced by dataset IDs and duplicate contract keys.

SQLite is the appropriate next step only when the historical archive or concurrent refresh jobs outgrow immutable snapshot files.

## Trust boundaries

- `data/raw/` is local and ignored by Git; exact raw files must be retained with the research run.
- `data/manifests/`, `data/reports/`, and `data/clean/` hold generated lineage artifacts.
- `public/data/` contains browser-safe snapshots and no credentials.
- synthetic fixtures live only in explicitly named test/demo paths and can never be loaded as verified imports.
- FRED and news context are excluded from signals unless a separate point-in-time method is designed and validated.
