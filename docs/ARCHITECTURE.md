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

Independent Gold API service
  → scheduled goldprice.dev / Frankfurter / optional FRED and GNews refresh
  → versioned public read-only snapshot (`/api/v1/snapshot`)
  → TypeScript schema validation in the browser
  → Global Gold / Data Source context panels
```

MCX observations and contextual API observations never share an implicit price type. MCX rows are domestic exchange futures contracts identified by trading date, symbol, and expiry. Goldprice.dev observations are international XAU/USD spot references; Frankfurter observations are daily reference FX. Context providers cannot replace a missing MCX record.

The separately deployed [`sru-codes/gold-api`](https://github.com/sru-codes/gold-api) service is an optional-at-runtime read-only context feed. The dashboard fetches its versioned snapshot directly from `VITE_GOLD_API_URL` (default `https://goldapi.up.railway.app`), validates the shape and units, and refreshes its view on a one-minute interval. It does not send credentials, trigger the service's refresh route, or pass international prices into the MCX research engine. An unavailable or malformed feed leaves the MCX monitor intact and falls back to Aurum's last published context when possible.

## Runtime model

The deployable application runs Caddy and a dependency-free Python HTTP API in one Railway container. Caddy serves the Vite build and proxies same-origin API requests. The API reads immutable demo/context artifacts from the image until new snapshots are published, then reads the current versions from `/app/data/published/`. A Railway volume mounted at `/app/data` preserves raw MCX files, manifests, validation reports, clean datasets, caches, and generated snapshots across deployments. API secrets are read only by Python from Railway variables and never appear in browser bundles.

The dashboard can also load a generated research snapshot from the user's machine; that file remains in the browser. Server-side writes use bearer authentication (`AURUM_ADMIN_TOKEN`) and are operated through `scripts/railway_admin.py`. Official raw CSV validation remains a Python pipeline responsibility. Research publication requires a hash-verified clean dataset and records its lineage.

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
