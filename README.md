# Aurum Spread

[![Release](https://img.shields.io/github/v/release/sru-codes/aurum-spread?display_name=tag)](https://github.com/sru-codes/aurum-spread/releases)
[![CI](https://github.com/sru-codes/aurum-spread/actions/workflows/ci.yml/badge.svg)](https://github.com/sru-codes/aurum-spread/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-9b7017.svg)](LICENSE.md)
[![Hackathon](https://img.shields.io/badge/Hack%20in%20Hills-'26-20211f.svg)](docs/RESEARCH.md)

**Find the spread. Prove the edge.**

Aurum Spread is a research and education prototype for comparing MCX gold futures. It helps users understand why two gold contracts can have different prices, and whether any remaining difference looks unusual after accounting for quoted weight, purity, expiry, liquidity, and estimated costs.

It is built for **Hack in Hills ’26 — Problem Statement 03: Commodity Derivatives Intelligence**. It is not a broker, trading system, investment recommendation, or promise of profit.

## Start here

You can explore the dashboard in demo mode without an account or API key:

1. Open the [Aurum Spread website](https://aurum-spread.up.railway.app/).
2. Scroll through the short introduction, then choose **Open the panel**.
3. In **Futures monitor**, select a contract pair, expiry, lookback, chart range, and historical date. Read the calculation trace and eligibility gates together; a large spread alone is not a signal.
4. Visit **Global gold** for international spot and currency context. Those reference prices are not MCX futures prices.
5. Visit **Data sources** to see source health, dates, provenance, and limitations. The currently included research fixture is labeled synthetic demo data.
6. Use **Export selected run** to download the visible research snapshot, or **Import snapshot** to inspect a locally generated JSON snapshot.

The theme control cycles between **System**, **Light**, and **Dark**. The system setting follows your device. All controls are research-only; the application cannot place orders.

## What the dashboard shows

- **Futures monitor:** expiry-aware pair selection, fine-gold normalization, residual spread chart, and historical walk-forward calculations.
- **Signal autopsy:** selected-date calculation trace, past-only z-score, lifecycle and liquidity context, and each eligibility gate.
- **Attribution laboratory:** gross and net hypothetical results, costs, gold exposure, drawdown, and test-period slippage scenarios.
- **Global gold:** supplemental XAU/USD spot, USD/INR reference rates, and international gold converted to INR per gram. These values are explicitly separate from MCX futures.
- **Data sources:** source status, latest observations, import lineage, known limits, and data mode.
- **Methodology:** the normalization, carry, walk-forward, and backtest assumptions in plain language.

The chart and metrics always come from the loaded artifact or the connected context API. If a source is missing, the dashboard shows an unavailable state; it does not fill gaps with invented market observations.

## How the comparison works

The first step is to convert each contract’s close into a comparable price per gram of fine gold:

```text
fine-gold price per gram = contract close ÷ quoted grams ÷ purity fraction
```

GOLDM is quoted per 10 g at 995 purity. GOLDTEN, GOLDGUINEA, and GOLDPETAL have their own effective-dated contract specifications and quotation bases. Contract lot size is used for sizing and P&L—not as a substitute for the quoted-price basis.

The research engine keeps the actual expiry attached to each observation, separates estimated carry from the remaining spread, computes statistics from prior sessions, and applies eligibility gates before assigning a verdict. Backtest prices are hypothetical next-session closes with documented costs, not guaranteed executable fills. A valid result may be **no signal** or negative performance.

See [Research methodology](docs/RESEARCH.md) for formulas, limitations, and official MCX references.

## Data sources and trust boundaries

### MCX futures — authoritative contract data

Official MCX Bhavcopy exports are the only accepted source for the target futures contracts: GOLDM, GOLDTEN, GOLDGUINEA, and GOLDPETAL. Download the daily export from the [MCX Bhavcopy page](https://www.mcxindia.com/market-data/bhavcopy) and import the CSV without editing its rows. The importer preserves the original bytes, records a SHA-256 hash and retrieval details, validates the requested trading date, and writes a row-level report.

**The included market-history fixture is synthetic.** It is provided for demonstrating the interface and must not be described as observed MCX performance. A verified historical dashboard requires official exports to be imported and a research snapshot to be generated from the resulting clean dataset.

### Gold API — international context only

The dashboard reads the public snapshot from [`gold-api`](https://github.com/sru-codes/gold-api), deployed at [`goldapi.up.railway.app`](https://goldapi.up.railway.app/). It supplies XAU/USD spot, USD/INR reference FX, closed daily gold bars, provider health, and optional macro/news context. Its values are labeled international references and never replace a missing MCX futures observation or enter the MCX spread signal.

The read-only API base can be set with `VITE_GOLD_API_URL`. The default is the deployed service URL. Do not put private credentials in any `VITE_` variable: Vite publishes those values in the browser bundle. Gold API’s optional FRED, GNews, and goldprice.dev credentials belong only in that service’s server-side environment. Its refresh route is not called by the Aurum browser.

Goldprice.dev attribution is displayed in the dashboard. The upstream free service may be delayed; read the latest timestamp and staleness status rather than treating it as an executable quote. See [Data providers](docs/DATA_PROVIDERS.md) and the [Gold API repository](https://github.com/sru-codes/gold-api) for provider details.

## Run Aurum locally

### Requirements

- Node.js **22 or newer** (Vite 8 requires a current Node release)
- Python **3.11 or newer**
- Git

The core analytics and HTTP service use Python’s standard library. The web interface uses React, TypeScript, Vite, and the shadcn components already checked into this repository.

### Install and start

```bash
git clone https://github.com/sru-codes/aurum-spread.git
cd aurum-spread
npm ci
```

Open two terminal windows in the project directory.

Terminal 1 — start the Python API:

```bash
npm run backend
```

Terminal 2 — start the web application:

```bash
npm run dev
```

Open the local URL printed by Vite, usually <http://localhost:5173/>. The Vite development server forwards `/api` and `/health` requests to the local Python service on port 8000. If the Python service is stopped, the research panel will show that its research artifact is unavailable; the browser can still read the public Gold API context.

To point the browser at a different Gold API deployment, create a local `.env` file (ignored by Git) and set its public base URL:

```dotenv
VITE_GOLD_API_URL=https://goldapi.up.railway.app
```

Restart Vite after changing `.env`. This variable is a public URL, not a secret.

## Import official MCX data

1. Download the official date-wise Bhavcopy CSV from MCX. Keep the downloaded file unchanged.
2. Run the importer with the trading date requested, in `DD/MM/YYYY` format:

   ```bash
   python3 analytics/pipeline.py ~/Downloads/BhavCopy.csv \
     --requested-date 15/10/2026 \
     --workspace .
   ```

3. Check the command result and `data/reports/` for accepted, rejected, and ignored rows. A rejected import does not create a clean dataset.
4. Preserve `data/raw/`, the manifest, and validation report together. Raw market files are excluded from Git; the clean-data manifest records their hashes and provenance.
5. Merge accepted daily datasets and run research for explicit contract symbols and expiries. The hosted workflow below provides the supported operator commands.

The official export date must match the requested date. Contract identity includes trading date, symbol, and expiry, so a different expiry cannot silently overwrite another. Missing sessions are left missing rather than filled in. More details and examples are in the [analytics guide](analytics/README.md).

## Use the hosted Railway research service

The Aurum application and `gold-api` are two separate Railway services. Aurum reads Gold API’s public, read-only endpoints; market context can fail without preventing the MCX research service from loading. For MCX imports and research publication, the Aurum service needs a persistent volume mounted at `/app/data` and an `AURUM_ADMIN_TOKEN` configured in Railway Variables.

Set the Aurum URL and token in your **local shell only**. Never paste the token in a command that will be committed or put it in a `VITE_` variable:

```bash
export AURUM_RAILWAY_URL="https://<your-aurum-domain>"
read -rsp 'Aurum admin token: ' AURUM_ADMIN_TOKEN
export AURUM_ADMIN_TOKEN
echo
```

Upload each official CSV with the date printed on the export:

```bash
python3 scripts/railway_admin.py import ./BhavCopy.csv --date 15/10/2026
```

Use the returned dataset IDs to merge accepted imports, then run the research engine for a specific pair and expiry dates:

```bash
# Replace both quoted values with the exact dataset IDs returned by your imports.
python3 scripts/railway_admin.py merge 'PASTE_DATASET_ID_1' 'PASTE_DATASET_ID_2'

python3 scripts/railway_admin.py run \
  --candidate GOLDTEN --candidate-expiry 2026-10-30 \
  --reference GOLDM --reference-expiry 2026-11-05 \
  --lookback 40 --annual-carry-bps 0
```

After the run completes, open `/dashboard` and choose **Refresh view**. The button reloads published research and the latest Gold API snapshot; it does not import files or force upstream provider refreshes. Operator access and endpoint details are in [Railway deployment](docs/DEPLOYMENT.md).

## Configuration

| Variable | Used by | Purpose |
|---|---|---|
| `VITE_GOLD_API_URL` | Aurum web build | Public base URL for the read-only Gold API; defaults to `https://goldapi.up.railway.app`. |
| `AURUM_ADMIN_TOKEN` | Aurum Python API | Protects MCX upload, merge, research, and context-refresh routes. Keep server-side and in the local operator shell only. |
| `AURUM_RAILWAY_URL` | Operator CLI | HTTPS URL for the Aurum service used by `scripts/railway_admin.py`. |
| `GOLDPRICE_API_KEY` | Gold API service | Optional server-side key for its goldprice.dev provider. |
| `FRED_API_KEY` | Gold API service | Optional server-side FRED key for macro context. |
| `GNEWS_API_KEY` | Gold API service | Optional server-side GNews key for news context. |

See [.env.example](.env.example) for Aurum’s local environment template. Gold API has a separate environment template in its own repository. **Never commit real tokens, passwords, or provider keys.**

## Tests and checks

From the repository root:

```bash
npm run build
npm run lint
npm test
python3 -m unittest discover -s analytics -v
```

`npm test` checks browser-facing data contracts. Python tests cover the importer, research engine, provider adapters, and API behavior. Some provider checks use fixtures and do not make network requests. A successful test run does not mean that official MCX history has been imported.

Optional local container check, when Docker is installed:

```bash
docker build -t aurum-spread:local .
docker run --rm -e PORT=3000 -p 3000:3000 aurum-spread:local
```

Then open <http://localhost:3000/> and check <http://localhost:3000/health>.

## Deployments and releases

Railway builds Aurum from the repository’s `Dockerfile`; pushes to the connected GitHub branch trigger deployment. The image serves the frontend and Python API in one service. Add a persistent volume mounted at `/app/data` to retain uploaded MCX files and generated outputs. Gold API is a separate Railway project and is configured independently.

Before releasing, run the checks above and review [CHANGELOG.md](CHANGELOG.md). Versions follow [Semantic Versioning](docs/VERSIONING.md). See [Security](SECURITY.md) to report a vulnerability and [Contributing](CONTRIBUTING.md) for project contribution expectations.

## Repository map

```text
src/                    React + TypeScript landing page and dashboard
src/components/ui/      shadcn UI primitives
src/lib/                browser data contracts, validation, and formatting
analytics/              Python MCX importer, research engine, API, and tests
data/                   dataset lineage and local processing outputs
public/data/             browser-safe demo and fallback context artifacts
scripts/                Railway operator CLI
docs/                   methodology, architecture, providers, and deployment
.github/workflows/       automated build, lint, test, and runtime checks
```

## Current status and limitations

- The public dashboard’s included historical research data is explicitly **synthetic demo data** until real MCX exports are uploaded and validated.
- MCX history must be obtained from official downloaded exports; Aurum does not rely on an undocumented automated endpoint.
- Gold API provides contextual international gold, FX, optional macro, and optional news data. These observations do not replace MCX futures.
- International spot and reference FX are not executable prices. The market may be delayed, unavailable, or stale; inspect the timestamp and status.
- Settlement/close values are not guaranteed fills. The backtest uses stated hypothetical fill and cost assumptions and may produce negative or inconclusive results.
- There is no broker integration, live order placement, or personalized financial advice.

## Project details

- **Repository:** [`sru-codes/aurum-spread`](https://github.com/sru-codes/aurum-spread)
- **Product:** Aurum Spread
- **Tagline:** Find the spread. Prove the edge.
- **License:** MIT — see [LICENSE.md](LICENSE.md)
