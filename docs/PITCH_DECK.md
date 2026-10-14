# Eight-slide pitch content

This outline maps directly to the supplied Hack in Hills PowerPoint template.

## 1 — Team

- Team name: **Aurum Labs** (replace if needed)
- Product: **Aurum Spread**
- Add member names and ownership: data/research, frontend/product, backend/pipeline, pitch/business

## 2 — Problem statement & theme

**Problem:** The same underlying gold trades through MCX contracts with different denomination, purity, expiry, and liquidity. Raw prices are incomparable, and apparent arbitrage can disappear after carry and costs.

**Impact:** Traders lack a quiet, defensible tool that distinguishes statistical anomalies from executable opportunities.

**Theme alignment:** India public-data intelligence, commodity-market transparency, and rigorous financial analytics.

## 3 — Solution

**Aurum Spread** normalizes all four gold contracts to rupees per gram of fine gold, tracks actual expiries, scores dislocations without look-ahead, and applies liquidity, lifecycle, and cost gates before alerting.

Key features:

- Cross-contract relative-value monitor
- Explainable “why no trade” decision engine
- Expiry-aware contract lifecycle controls
- Cost-aware walk-forward testing
- Performance attribution separated from the gold market

Unique value: it optimizes for trustworthy silence, not daily signals.

## 4 — Architecture

```text
MCX Bhavcopy + specification versions
              ↓
raw archive → validation → expiry-preserving normalized observations
              ↓
rolling spread model → eligibility and cost gates → signal ledger
              ↓
walk-forward engine → attributed metrics → React dashboard/export
```

Stack: Python analytics, CSV/Parquet research store, React + TypeScript + Vite, shadcn UI, React Bits motion. No paid data API required for the prototype.

## 5 — Market research / analysis

Target users: bullion traders, jewellers, commodity desks, brokers, risk teams, and quantitative researchers.

Beachhead: research and hedge-selection dashboard for Indian bullion-market participants.

Revenue options:

- Professional alerts and historical analytics subscription
- Broker/desk API and white-label dashboard
- Contract-liquidity and execution-quality research reports

Do not invent a market-size number for the pitch. Use a sourced top-down estimate or present interviewed-user evidence.

## 6 — Future scope

- Live broker-market-depth integration for executable pricing
- Carry model using interest, storage, tax, and delivery effects
- Silver and base-metal denomination families
- Regime-aware liquidity forecasts
- Team alerts, audit exports, and enterprise risk integration

## 7 — Extra / optional

Show the strongest evidence:

- Raw MCX row → normalization → pair spread → z-score → four gates → final decision
- Cost sensitivity at 1×, 1.5×, and 2×
- A case where an exciting statistical signal correctly becomes “no trade”
- Reproducibility hash and rejected-row count

## 8 — Thank you

**Find the spread. Prove the edge.**

Close with a QR code to the live prototype and repository, plus a research-use disclaimer.
