<div align="center">

# Aurum Spread

**Find the spread. Prove the edge.**

An expiry-aware research terminal for comparing MCX gold futures—built to explain the data, the calculation, and the uncertainty behind every result.

[![Release](https://img.shields.io/github/v/release/sru-codes/aurum-spread?display_name=tag)](https://github.com/sru-codes/aurum-spread/releases)
[![CI](https://github.com/sru-codes/aurum-spread/actions/workflows/ci.yml/badge.svg)](https://github.com/sru-codes/aurum-spread/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-9b7017.svg)](LICENSE.md)
[![Hackathon](https://img.shields.io/badge/Hack%20in%20Hills-'26-20211f.svg)](docs/RESEARCH.md)

<p>
  <a href="#1-what-is-aurum-spread">Overview</a> ·
  <a href="#6-installation">Install</a> ·
  <a href="#10-research-workflow">Research workflow</a> ·
  <a href="#12-api-reference">API</a> ·
  <a href="#15-deployment">Deployment</a> ·
  <a href="docs/RESEARCH.md">Methodology</a>
</p>

</div>

---

## Table of contents

1. [What is Aurum Spread?](#1-what-is-aurum-spread)
2. [Why this project exists](#2-why-this-project-exists)
3. [Features](#3-features)
4. [How it works](#4-how-it-works-architecture)
5. [Requirements](#5-requirements)
6. [Installation](#6-installation)
7. [Project structure](#7-project-structure)
8. [Configuration](#8-configuration)
9. [Run the application](#9-run-the-application)
10. [Research workflow](#10-research-workflow)
11. [Using the dashboard](#11-using-the-dashboard)
12. [API reference](#12-api-reference)
13. [Data sources and methodology](#13-data-sources-and-methodology)
14. [Using the Gold API context feed](#14-using-the-gold-api-context-feed)
15. [Deployment](#15-deployment)
16. [Development](#16-development)
17. [Testing](#17-testing)
18. [Operations and data retention](#18-operations-and-data-retention)
19. [Troubleshooting and FAQ](#19-troubleshooting-and-faq)
20. [Roadmap](#20-roadmap)
21. [Contributing](#21-contributing)
22. [Security and financial disclaimer](#22-security-and-financial-disclaimer)
23. [License and attribution](#23-license-and-attribution)

---

## 1. What is Aurum Spread?

Aurum Spread is a research and education prototype for comparing four MCX gold futures contracts: **GOLDM, GOLDTEN, GOLDGUINEA, and GOLDPETAL**.

Each contract quotes gold differently. A raw price comparison can therefore be misleading: contracts may use different quoted weights and purity, expire on different dates, have different liquidity, and carry different transaction costs. Aurum normalizes the contracts, keeps their expiry identities intact, and shows what remains after those differences are considered.

The project was built for **Hack in Hills ’26 — Problem Statement 03: Commodity Derivatives Intelligence**. It is a research tool, not a broker, order-entry system, investment recommendation, or promise of profit.

## 2. Why this project exists

A screen showing that two gold contracts have different prices does not explain whether the difference is meaningful. Aurum is designed to make that investigation traceable:

| Question | What Aurum does |
|---|---|
| Are the quoted prices comparable? | Converts prices to a fine-gold price per gram using the effective contract quotation basis and purity. |
| Could expiry explain the difference? | Keeps each expiry explicit and separates declared carry adjustment from the residual spread. |
| Is the relationship unusual? | Calculates past-only rolling statistics in a walk-forward sequence. |
| Could it be researched after trading frictions? | Applies liquidity and contract-lifecycle gates and reports hypothetical costs separately. |
| Can the result be checked? | Provides a calculation trace, source lineage, data-quality reports, and downloadable snapshots. |

The product is allowed to conclude **no signal**, **insufficient history**, or **negative after costs**. It does not force a trade idea from the data.

## 3. Features

- **Expiry-aware futures monitor** — choose the instrument pair, exact expiries, lookback, chart range, and historical date.
- **Fine-gold normalization** — effective-dated quotation bases and purity for the target MCX gold contracts.
- **Signal autopsy** — inspect the selected observation, prior-only statistics, carry adjustment, and individual eligibility gates.
- **Walk-forward historical research** — earlier decisions use only information available up to that point; chronological train, validation, and test partitions stay separate.
- **Backtest attribution** — distinguishes gross contract P&L, estimated costs, net performance, residual gold exposure, and unexplained residual.
- **Cost sensitivity** — evaluate how explicit slippage scenarios affect the historical result.
- **Official-data import pipeline** — preserves downloaded MCX files, hashes raw bytes, validates rows, and produces rejection reports and versioned clean data.
- **Supplementary global context** — displays international XAU/USD and USD/INR references through the separate Gold API service. These are not MCX futures prices.
- **Data-source center** — shows mode, provider status, timestamps, provenance, coverage, and limitations.
- **Research exports** — download snapshots and import compatible local snapshots into the dashboard.
- **System, light, and dark appearance** — system theme follows the device; users can also select either theme directly.
- **Railway-ready service** — one container serves the built React application and Python research API.

The public dashboard currently includes an explicitly marked **synthetic demo fixture** so the interface can be explored before real MCX history is imported. It is not empirical market evidence.

## 4. How it works (architecture)

### Historical contract research

```text
Official MCX Bhavcopy CSV
  → preserve exact raw bytes + SHA-256
  → validate date, instrument, OHLC, expiry, and activity
  → accepted/rejected/ignored row report
  → versioned clean daily dataset
  → merge with duplicate-key and hash checks
  → expiry-aware walk-forward research
  → versioned JSON snapshot
  → React dashboard
```

### Supplementary market context

```text
Gold API snapshot (separate service)
  → browser fetch with timeout and schema/unit validation
  → timestamp, unit, date-range, and sequence checks
  → Global Gold and Data Source views
```

MCX futures and international reference prices remain different data types. Gold API observations never replace missing MCX rows and never enter the MCX spread signal calculation.

### Runtime model

In development, Vite serves the web interface and proxies `/api` and `/health` to the Python service on port `8000`. In the Railway container, Caddy serves the production frontend and proxies same-origin API requests to the Python HTTP service. The Python service reads published JSON artifacts and requires a bearer token for mutation routes.

The project uses files and JSON snapshots instead of a database. This keeps imports and outputs inspectable and reproducible for a hackathon prototype. The Aurum Railway volume should be mounted at `/app/data` to preserve uploads and generated artifacts across deployments.

See [Architecture](docs/ARCHITECTURE.md) for data paths, trust boundaries, and storage decisions.

## 5. Requirements

| Requirement | Version / note |
|---|---|
| Node.js | **22.12 or newer** for the installed Vite toolchain |
| npm | Included with Node.js; `npm ci` uses the committed lockfile |
| Python | **3.11 or newer**; core analytics and server use the standard library |
| Git | Required to clone the repository |
| Docker | Optional for reproducing the Railway container locally |
| Outbound HTTPS | Needed for the browser’s Gold API context and optional provider refreshes |
| MCX account / API key | Not required for manual official Bhavcopy downloads |
| Database | Not required |

The Python analytics engine has no third-party runtime dependency. The frontend dependencies are managed by npm.

## 6. Installation

### Option A — Run from source

```bash
git clone https://github.com/sru-codes/aurum-spread.git
cd aurum-spread
npm ci
```

Continue to [Run the application](#9-run-the-application). No API key is needed to explore the demo dashboard.

### Option B — Run the production container

```bash
git clone https://github.com/sru-codes/aurum-spread.git
cd aurum-spread
docker build -t aurum-spread:local .
docker run --rm -e PORT=3000 -p 3000:3000 aurum-spread:local
```

Open <http://localhost:3000/>. Check <http://localhost:3000/health> for the container health response. Docker must be installed and running.

### Option C — Use the hosted dashboard

Open [aurum-spread.up.railway.app](https://aurum-spread.up.railway.app/), scroll through the introduction, then select **Open the panel**. Demo mode is available without an account.

## 7. Project structure

```text
aurum-spread/
├── src/                         # React + TypeScript landing page and dashboard
│   ├── components/ui/            # Checked-in shadcn UI primitives
│   ├── components/               # Dashboard components, including Global Gold
│   ├── hooks/                    # Theme and Gold API state hooks
│   └── lib/                      # Typed data contracts, validation, analytics helpers
├── public/data/                  # Browser-safe demo and fallback context snapshots
├── analytics/                    # Python importer, research engine, providers, and API
│   ├── providers/                # Goldprice.dev, Frankfurter, FRED, and GNews adapters
│   └── test_*.py                 # Python unit and service tests
├── scripts/                      # Authenticated Railway operator CLI
├── docs/                         # Research, architecture, deployment, provider guides
├── .github/workflows/ci.yml      # Frontend, Python, Docker, and runtime checks
├── Dockerfile                    # Production image build
├── Caddyfile                     # Frontend server and API reverse proxy
├── railway.json                  # Railway build, start, and healthcheck configuration
├── package.json                  # Frontend scripts and dependencies
├── .env.example                  # Local environment-variable template
├── CHANGELOG.md                  # Release history
├── CONTRIBUTING.md               # Contribution workflow
├── SECURITY.md                   # Vulnerability reporting and security notes
└── LICENSE.md                    # MIT license
```

### Core Python files

| File | Responsibility |
|---|---|
| `analytics/aurum_spread.py` | Contract specs, normalization, expiry-aware spread, and base calculations. |
| `analytics/pipeline.py` | Raw archive, schema validation, date checks, manifests, clean dataset, and merge. |
| `analytics/research.py` | Walk-forward analysis, eligibility gates, hypothetical backtest, attribution, and sensitivity. |
| `analytics/run_research.py` | Command-line entry point for local research snapshot generation. |
| `analytics/server.py` | Python HTTP API, artifact loading, health route, and authenticated mutations. |
| `analytics/refresh_context.py` | Aurum-side refresh of supported supplementary gold and FX context. |
| `scripts/railway_admin.py` | Bearer-authenticated CLI for imports, merges, research runs, and context refresh. |

## 8. Configuration

Copy `.env.example` to `.env` when you need local settings. Keep secret values in the local shell or server environment. Never commit `.env`, and never put credentials in a `VITE_` variable: Vite embeds `VITE_` values in the public browser bundle.

| Variable | Used by | Purpose |
|---|---|---|
| `VITE_GOLD_API_URL` | Web build | Public read-only Gold API base URL. Defaults to `https://goldapi.up.railway.app`. This is a URL, not a secret. |
| `AURUM_ADMIN_TOKEN` | Aurum Python API | Bearer token required for import, merge, research-run, and context-refresh POST routes. |
| `AURUM_RAILWAY_URL` | Operator CLI | Base URL for the deployed Aurum service, with no trailing slash. |
| `GOLDPRICE_API_KEY` | Aurum context refresh; separately configured in Gold API if needed | Optional server-side key for the goldprice.dev provider. |
| `FRED_API_KEY` | Aurum provider status; separately configured in Gold API if needed | Aurum currently reports whether this is set but does not fetch FRED itself. Gold API may use its own independent key. |
| `GNEWS_API_KEY` | Aurum provider status; separately configured in Gold API if needed | Aurum currently reports whether this is set but does not fetch GNews itself. Gold API may use its own independent key. |
| `AURUM_CACHE_DIR` | Aurum Python refresh | Local cache directory for provider responses; defaults to `.cache/providers`. |
| `PORT` | Container platform | Port provided by Railway to the web process; set automatically in deployment. |

To override the Gold API URL locally, create `.env`:

```dotenv
VITE_GOLD_API_URL=https://goldapi.up.railway.app
```

Restart Vite after changing environment values. The separate [Gold API service](https://github.com/sru-codes/gold-api) has its own environment and secrets; Aurum does not call its protected refresh endpoint.

## 9. Run the application

Start the Python API and Vite in separate terminal windows from the repository root.

**Terminal 1 — Python API:**

```bash
npm run backend
```

The service listens on `http://127.0.0.1:8000` by default.

**Terminal 2 — React application:**

```bash
npm run dev
```

Open the local URL printed by Vite, usually <http://localhost:5173/>. Vite proxies `/api/*` and `/health` to the Python service. If the Python process is stopped, published research data may be unavailable; the browser can still attempt the independent public Gold API context feed.

To build and serve the frontend production bundle locally:

```bash
npm run build
npm run preview
```

Vite prints the preview URL. The preview server serves the built frontend; it does not replace the separate Python API process for local API routes.

## 10. Research workflow

### Step 1 — Download an official MCX Bhavcopy

Use the [official MCX Bhavcopy page](https://www.mcxindia.com/market-data/bhavcopy) and download the CSV for the trading date. Do not edit or re-save the rows. Keep the exact file; the importer archives and hashes its bytes.

### Step 2 — Import and validate the daily file

For a local import:

```bash
python3 analytics/pipeline.py ~/Downloads/BhavCopy.csv \
  --requested-date 15/10/2026 \
  --workspace .
```

The requested date must match the date reported by the export. Inspect the generated report under `data/reports/`. Rejected target rows prevent a clean daily dataset from being published; missing sessions are reported, never filled.

### Step 3 — Merge validated days

Validated daily files can be merged using the Python pipeline. The merge checks dataset identity and hashes and fails on duplicate contract keys. A contract observation is identified by **trading date + symbol + expiry date**; different expiries are never collapsed into one row.

Daily clean files follow the pattern `data/clean/<dataset-id>.observations.v1.json`. For example, merge two accepted files into one history file with:

```bash
python3 -c "from analytics.pipeline import merge_clean_datasets; merge_clean_datasets(['data/clean/<first-dataset-id>.observations.v1.json', 'data/clean/<second-dataset-id>.observations.v1.json'], 'data/clean/mcx-history.json')"
```

Replace the two dataset ID placeholders with the IDs printed by the importer. The output path is your choice; use the same path in the next step.

For the hosted service, use the Railway operator CLI below. It returns dataset IDs from accepted imports; only merge the IDs you intend to analyze.

### Step 4 — Run a specific contract pair

For the merged local dataset:

```bash
python3 analytics/run_research.py data/clean/mcx-history.json \
  --candidate GOLDTEN --candidate-expiry 2026-10-30 \
  --reference GOLDM --reference-expiry 2026-11-05 \
  --lookback 40 --annual-carry-bps 0 \
  --output public/data/research/goldten-goldm.v1.json
```

Replace the example dates with actual expiries present in your dataset. `--annual-carry-bps 0` means that no nonzero carry estimate was supplied; it does **not** mean carry is absent.

### Step 5 — Inspect the result

Load the generated snapshot in the dashboard or publish it through the hosted service. Review the selected-date calculation trace, contract lifecycle, liquidity, data quality, transaction-cost assumptions, and verdict together. A z-score or large spread is not by itself a trade recommendation.

More detail, equations, and backtest assumptions are in [Research methodology](docs/RESEARCH.md) and the [Analytics guide](analytics/README.md).

## 11. Using the dashboard

1. Open the landing page and choose **Open the panel**.
2. In **Futures monitor**, select the candidate and reference contracts, exact expiries, lookback, chart range, and historical date.
3. Review the normalized series and residual spread. Check source mode before interpreting results: the included fixture is synthetic demo data until official MCX exports are imported and analyzed.
4. Open **Signal autopsy** to inspect the calculation trace and each eligibility gate for the selected date. A withheld signal is a valid outcome.
5. Use **Attribution laboratory** to inspect gross P&L, estimated costs, net results, gold exposure, residual attribution, drawdown, and sensitivity scenarios.
6. Open **Global gold** for international XAU/USD, USD/INR, and converted context. These references are not domestic MCX futures prices.
7. Open **Data sources** to review provider state, observation timestamps, source limitations, and data provenance.
8. Use **Export selected run** to download the selected research snapshot. Use **Import snapshot** to inspect a compatible local snapshot in the browser.
9. Use **Refresh view** to request the latest published research/context view. It does not import CSV files or force upstream provider refreshes.
10. Cycle the theme control between **System**, **Light**, and **Dark**.

Dashboard calculations read the loaded, validated artifact. Missing data remains missing; the application does not silently invent or fill market records.

## 12. API reference

Base URL in local development: `http://localhost:8000`. The production site exposes these through its same-origin proxy. Responses are JSON.

### Read-only GET routes

| Route | Purpose |
|---|---|
| `GET /health` | Service and storage health. |
| `GET /api/health` | Alias for the health response. |
| `GET /api/research` | Current published research artifact, or the clearly marked demo fallback when no verified artifact exists. |
| `GET /api/context` | Current published supplementary context artifact or fallback. |

### Authenticated POST routes

All mutation routes require `Authorization: Bearer <AURUM_ADMIN_TOKEN>`.

| Route | Purpose |
|---|---|
| `POST /api/mcx/import?requested_date_ddmmyyyy=DD/MM/YYYY` | Upload and validate one official MCX CSV. |
| `POST /api/mcx/merge` | Merge accepted dataset IDs into a validated dataset. |
| `POST /api/research/run` | Generate and publish a research snapshot for an explicit pair and expiry selection. |
| `POST /api/context/refresh` | Refresh the supported Aurum-side gold/FX context providers server-side. |

Unknown routes return a JSON `404`. Unauthorized mutations return `401`. Validation errors include a structured error code and message. Read-only public routes do not require the admin token.

Check service health:

```bash
curl --fail https://aurum-spread.up.railway.app/health
```

Inspect the current research mode:

```bash
curl --fail https://aurum-spread.up.railway.app/api/research | jq '.mode'
```

Never put the bearer token in a browser bundle or public URL.

## 13. Data sources and methodology

### MCX Bhavcopy — primary historical source

Official MCX downloaded exports are the accepted source for GOLDM, GOLDTEN, GOLDGUINEA, and GOLDPETAL. Aurum does not use an undocumented MCX endpoint or replace missing MCX records with another provider.

The importer preserves raw bytes, retrieval metadata, a SHA-256 checksum, effective specification identity, and row-level validation results. It validates requested versus returned date, target contract type, OHLC, volume/open interest, quotation basis, purity, expiry, and duplicate keys. It reports ignored non-target rows separately from rejected target rows.

The following units matter:

```text
fine-gold price per gram = contract close ÷ quoted grams ÷ purity fraction
```

Quotation basis and trading unit are not interchangeable. Lot size is used for sizing and P&L. Contract specifications are effective-dated and selected using the actual contract expiry.

### Expiry and statistics

Every record keeps its actual expiry. Estimated carry is declared separately from the residual spread. Rolling statistics use prior observations only; the current date’s observation cannot leak into the training window. Walk-forward splits remain chronological. No missing observation is forward-filled or backfilled.

### Backtesting boundaries

Backtest prices and sizes represent the actual selected futures contracts. Hypothetical next-session close assumptions, slippage, brokerage/fees, funding, liquidity constraints, and lifecycle limits are documented and itemized. Settlement/close values are not guaranteed fills; daily volume does not prove available depth. The output reports gross and net performance, costs, gold-market exposure, and unexplained residual separately.

See [Research methodology](docs/RESEARCH.md) for formulas and detailed limitations. See [Data providers](docs/DATA_PROVIDERS.md) for provider setup and coverage boundaries.

## 14. Using the Gold API context feed

Aurum can read the public, versioned snapshot from [`sru-codes/gold-api`](https://github.com/sru-codes/gold-api):

```bash
curl --fail https://goldapi.up.railway.app/health
curl --fail https://goldapi.up.railway.app/api/v1/snapshot | jq '.mode, .sections.gold.data, .sections.fx.data'
```

The browser requests `GET /api/v1/snapshot` from `VITE_GOLD_API_URL`. The Aurum client validates snapshot version metadata, explicit gold units, positive prices, FX pair, closed OHLC bars, chronological unique daily dates, advertised bar range, optional macro dates, and HTTPS news URLs. Failed refreshes do not erase the last successfully loaded snapshot during that session.

The panel may show international spot, USD/INR reference FX, closed daily XAU/USD bars, provider health, and optional dated macro/news context if the Gold API service publishes them. Gold converted to INR per gram is a contextual calculation—not MCX settlement, GST-inclusive retail price, or executable quote. News and macro context do not enter the MCX signal engine.

The Gold API service is separately deployed and has its own environment and refresh schedule. Aurum’s **Refresh view** only requests its latest published snapshot; it does not call the protected Gold API refresh route. If the service is unavailable, the dashboard degrades gracefully and keeps the MCX research path independent.

See the [Gold API repository](https://github.com/sru-codes/gold-api) and [Data provider guide](docs/DATA_PROVIDERS.md).

## 15. Deployment

### Railway (connected GitHub deployment)

The Aurum service builds from this repository’s root `Dockerfile`. Pushes to the connected branch trigger Railway’s deployment pipeline.

1. Create or connect a Railway service to `sru-codes/aurum-spread`.
2. Use the repository-root `Dockerfile` and generate a public domain.
3. Add a Railway volume mounted at **`/app/data`**. Without it the service can run, but uploads and generated data are ephemeral and can be lost on redeploy.
4. Set `AURUM_ADMIN_TOKEN` in Railway Variables to a long random secret. Generate a local value with `openssl rand -hex 32`; do not commit or expose it in a `VITE_` variable.
5. Add optional server-side provider variables only when needed.
6. Deploy and verify `/health`, `/api/research`, and the browser dashboard.

Detailed setup and operator commands are in [Railway deployment](docs/DEPLOYMENT.md). Railway storage configuration requires access to the Railway project and cannot be created by a Git push alone.

### Upload MCX data to the hosted service

Set the deployed URL and token in your local shell. The token prompt avoids putting the secret directly in shell history:

```bash
export AURUM_RAILWAY_URL="https://<your-aurum-domain>"
read -rsp 'Aurum admin token: ' AURUM_ADMIN_TOKEN
export AURUM_ADMIN_TOKEN
echo
```

Import a CSV using its actual requested trading date:

```bash
python3 scripts/railway_admin.py import ./BhavCopy.csv --date 15/10/2026
```

Use the accepted dataset IDs returned by the command:

```bash
python3 scripts/railway_admin.py merge '<dataset-id-1>' '<dataset-id-2>'
```

Run research for explicit expiries that exist in your imported data:

```bash
python3 scripts/railway_admin.py run \
  --candidate GOLDTEN --candidate-expiry 2026-10-30 \
  --reference GOLDM --reference-expiry 2026-11-05 \
  --lookback 40 --annual-carry-bps 0
```

Use the CLI help for options:

```bash
python3 scripts/railway_admin.py --help
python3 scripts/railway_admin.py run --help
```

The dashboard can then reload the published artifact with **Refresh view**. It does not automatically import your local files.

## 16. Development

Install the locked frontend dependencies and run the app as described above. For Python work, no third-party package installation is required for the analytics tests.

Useful commands:

```bash
npm run dev                 # Vite development server
npm run backend             # Python HTTP API
npm run build               # TypeScript check + production bundle
npm run lint                # Oxlint
npm test                    # Browser-facing data-contract tests
python3 -m unittest discover -s analytics -v
```

The built frontend and Python backend are intentionally separate in local development. The container entrypoint supervises both services for Railway. See [Contributing](CONTRIBUTING.md) before opening a pull request.

## 17. Testing

Run all standard checks from the project root:

```bash
npm ci
npm run build
npm run lint
npm test
python3 -m unittest discover -s analytics -v
```

The frontend tests validate research/context JSON contracts and Gold API payload parsing. Python tests cover:

- malformed dates, row schemas, OHLC and liquidity validation;
- duplicate contracts, simultaneous expiries, and missing sessions;
- raw-file hashes, idempotent imports, clean-data publication, and merge refusal;
- unit and purity normalization and effective-dated specifications;
- past-only walk-forward statistics and chronological partitions;
- contract lifecycle and liquidity gates;
- actual-contract hypothetical P&L, cost attribution, drawdown, and sensitivity;
- provider caching, retries, rate limits, auth failures, date alignment, and no-look-ahead rules;
- API health, demo fallback, authenticated mutation routes, and an end-to-end import/research workflow.

Automated tests use fixtures and do not establish that real MCX history has been imported. CI also builds the Docker image and runs a container health smoke test.

## 18. Operations and data retention

- **Market-data acquisition:** official MCX exports are downloaded manually. Automated undocumented MCX retrieval is not part of this application.
- **Raw data:** local `data/raw/` files are ignored by Git. Preserve original files alongside manifests and validation reports for auditability.
- **Published artifacts:** research and context snapshots are versioned JSON. Railway reads persistent published files under `/app/data` when present and uses packaged fallbacks otherwise.
- **Provider refresh:** the Aurum Python context refresh supports goldprice.dev and Frankfurter. FRED/GNews keys are currently reported as configured/unconfigured by Aurum but those providers are not fetched by Aurum itself. The separate Gold API may independently provide macro/news context.
- **Gold API fetch:** the browser reads a public snapshot; it never receives server credentials and does not trigger upstream refresh.
- **Failure isolation:** provider errors are surfaced as unavailable/partial states. Missing values are not fabricated.
- **Scale:** file-backed snapshots fit the single-service hackathon prototype. Use a shared database/object store only if multi-instance writes or larger concurrent workloads become a real requirement.

## 19. Troubleshooting and FAQ

| Symptom | Likely cause | What to do |
|---|---|---|
| The research view is unavailable locally | Python API is not running | Start `npm run backend` in a second terminal and retry. |
| Global Gold is unavailable | Gold API service/network is unavailable, or response validation failed | Check the public `/health` and `/api/v1/snapshot` endpoints; confirm `VITE_GOLD_API_URL`; restart Vite after changing `.env`. MCX research remains independent. |
| Gold API displays `PARTIAL` or `DEGRADED` | One or more upstream sections are unavailable or stale | Inspect provider status and timestamps. Partial context is not evidence of a current MCX price. |
| MCX import is rejected | Export date mismatch, malformed row, unsupported instrument type, or invalid target contract data | Read the row-level report; verify the requested date and keep the original export unchanged. |
| Merge fails on duplicate keys | Imported datasets contain the same date/symbol/expiry observation | Select a non-overlapping set of accepted daily datasets; do not drop expiry identity to bypass the error. |
| Dashboard says synthetic demo | No verified historical MCX research artifact has been published | Import official MCX exports, merge accepted days, run research, and refresh the dashboard. |
| Hosted uploads disappear after redeploy | Persistent volume missing or mounted at the wrong path | Attach a Railway volume at `/app/data`; redeploy and verify `/health` storage status. |
| Railway admin call returns `401` | Missing/incorrect bearer token | Confirm `AURUM_ADMIN_TOKEN` matches the service variable and is exported in the local CLI shell. Never put it in the URL. |
| A signal is withheld | Insufficient history, lifecycle, liquidity, data-quality, or cost gate failed | Inspect Signal Autopsy. “No signal” is intentional and should not be overridden by guesswork. |

## 20. Roadmap

The next work should preserve the project’s data-integrity boundaries:

1. Collect and audit official MCX exports with the effective specification source documents.
2. Publish reproducible historical datasets and demonstrate the entire raw-to-verdict lineage.
3. Validate cost, lifecycle, and liquidity assumptions against documented exchange/broker rules.
4. Expand integration-state and visual regression coverage for responsive dashboard flows.
5. Consider persistent database storage only when file-backed artifacts no longer meet actual needs.

No roadmap item should imply live execution, guaranteed fills, or profitable trading.

## 21. Contributing

Issues and pull requests are welcome for parser correctness, research reproducibility, accessible UI, documentation, and test coverage.

Before submitting:

1. Create a branch from the latest `main`.
2. Keep the change focused and include regression tests where applicable.
3. Never commit credentials, `.env`, raw private data, `node_modules`, or build output.
4. Label synthetic or illustrative values clearly; do not present them as exchange observations.
5. Update `CHANGELOG.md` under **Unreleased** for user-visible changes.
6. Run the checks listed in [Testing](#17-testing) and state which ones you ran.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the project rules. Contributions are released under the repository’s MIT license.

## 22. Security and financial disclaimer

Do not include API keys, bearer tokens, or sensitive datasets in issues or pull requests. Report vulnerabilities through GitHub’s **Security → Advisories → Report a vulnerability** flow. See [SECURITY.md](SECURITY.md) for supported versions and reporting guidance.

Aurum Spread is an educational research prototype. It does not place orders, connect to a broker, promise execution, or provide personalized financial advice. Historical prices and hypothetical fills do not guarantee future results. Synthetic demo fixtures are not empirical market data. Always verify the source, timestamp, contract specification, and assumptions before relying on an analysis.

## 23. License and attribution

- **License:** [MIT](LICENSE.md)
- **Repository:** [sru-codes/aurum-spread](https://github.com/sru-codes/aurum-spread)
- **Project:** Hack in Hills ’26 — Problem Statement 03, Commodity Derivatives Intelligence
- **Primary market-data source:** [MCX Bhavcopy](https://www.mcxindia.com/market-data/bhavcopy)
- **Supplementary gold/FX context:** [Gold API](https://github.com/sru-codes/gold-api), [goldprice.dev](https://goldprice.dev/), and [Frankfurter](https://frankfurter.dev/)

Provider attribution and licensing limitations are documented in [Data providers](docs/DATA_PROVIDERS.md). International spot and reference FX are contextual inputs, not substitutes for official MCX contract observations.
