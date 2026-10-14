# Aurum Spread

[![Release](https://img.shields.io/github/v/release/sru-codes/aurum-spread?display_name=tag)](https://github.com/sru-codes/aurum-spread/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-9b7017.svg)](LICENSE.md)
[![Hackathon](https://img.shields.io/badge/Hack%20in%20Hills-'26-20211f.svg)](docs/RESEARCH.md)

A research-grade relative-value monitor for MCX gold futures, built for the **Commodity Derivatives Intelligence** track at **Hack in Hills ’26**. It compares GOLDM, GOLDTEN, GOLDGUINEA, and GOLDPETAL after correcting for quotation base and purity, then decides whether a statistical dislocation survives liquidity and transaction-cost constraints.

The central product decision is deliberate: **a large spread is not automatically a trade**. Aurum Spread can surface an anomaly while withholding an alert when estimated execution costs consume the expected convergence.

## What is working

- Responsive React dashboard with pair and lookback controls
- Contract-level normalization and eligibility display
- Explainable signal gates: statistics, expiry, liquidity, and costs
- Walk-forward attribution view separating gross convergence from costs
- Methodology and official-data notes inside the product
- Dependency-free Python analytics with automated tests
- shadcn primitives installed through the shadcn MCP registry
- React Bits `FadeContent` with reduced-motion handling

The visible market observations and backtest summary are clearly labeled synthetic demo data. They must not be presented as empirical MCX results.

## Run locally

Requirements: Node.js 20+ and Python 3.11+.

```bash
npm install
npm run dev
```

Production checks:

```bash
npm run build
npm run lint
cd analytics
python3 -m unittest discover -s analytics -v
npm audit --audit-level=high
```

## Deploy on Railway

The repository includes a production multi-stage Docker build. Node compiles the Vite application and Caddy serves the static output using Railway's injected `PORT`, SPA fallback, compression, security headers, and `/health` endpoint.

Connect `sru-codes/aurum-spread` from Railway's **Deploy from GitHub repo** flow, then generate a public domain. No application secrets are required for the synthetic MVP. See [the deployment guide](docs/DEPLOYMENT.md).

## Repository map

```text
src/                    React product prototype
  components/ui/        shadcn registry components
  components/           React Bits component
  data/demo.ts           explicitly synthetic UI fixture
  lib/analytics.ts       browser-side normalization helpers
analytics/              auditable Python research core and tests
docs/RESEARCH.md         data, methodology, risks, and build plan
docs/PITCH_DECK.md       content mapped to the supplied 8-slide template
docs/DEPLOYMENT.md       Railway deployment and verification
docs/VERSIONING.md       Semantic Versioning and release procedure
components.json          shadcn + React Bits registry configuration
SECURITY.md              private reporting and project security scope
CHANGELOG.md             released and planned capabilities
```

## Core formula

```text
fine_gold_price = close_price / quoted_grams / purity_fraction
spread_bps = (candidate_fine_price / reference_fine_price - 1) × 10,000
```

GOLDM is quoted per 10g at 995 purity. GOLDTEN is quoted per 10g at 999 purity; GOLDGUINEA per 8g at 999; GOLDPETAL per 1g at 999. Trading-unit size is used for position sizing and notional, not for normalizing the quoted price.

## Research boundaries

- Track each contract by its actual expiry date; never backtest a stitched near-month series as though it were one instrument.
- Compute every signal from information available before that decision.
- Treat settlement prices as reference values rather than guaranteed fills.
- Treat volume as activity rather than displayed market depth.
- Report gross convergence, costs, net performance, and gold beta separately.
- A finding that no persistent edge survives costs is a valid result.

See [docs/RESEARCH.md](docs/RESEARCH.md) for the full methodology and official sources.

## Project status

Current release: **v0.1.0 — Research Prototype**.

The dashboard and analytical mechanics are functional, but the displayed observations remain synthetic until the official MCX import and frozen historical holdout are completed. See the [changelog](CHANGELOG.md), [versioning policy](docs/VERSIONING.md), [security policy](SECURITY.md), and [contribution guide](CONTRIBUTING.md).

## Name

**Repository:** `aurum-spread`  
**Product:** Aurum Spread  
**Tagline:** Find the spread. Prove the edge.

This is a research prototype, not investment advice or an order-execution system.

