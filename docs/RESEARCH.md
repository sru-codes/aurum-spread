# Commodity Derivatives Intelligence — research blueprint

## Product thesis

MCX lists economically similar gold exposure in several denominations. Their raw quoted prices are not directly comparable because quotation bases, purity, expiry calendars, liquidity, and lot notionals differ. Aurum Spread converts each observation to a consistent fine-gold unit and asks two separate questions:

1. Is the relationship statistically unusual relative to information available at that time?
2. Is the deviation large and liquid enough to be economically actionable after costs?

This separation is the product's main advantage. Most dashboards stop at question one.

## Primary users

- Bullion traders and jewellers choosing the most efficient hedge denomination
- Commodity research desks monitoring fragmented contract liquidity
- Brokers and risk teams explaining cross-contract basis moves
- Quant researchers testing market-efficiency hypotheses

The hackathon MVP is an intelligence product, not an automated trading system.

## Official evidence

- [MCX Daily Bhavcopy](https://www.mcxindia.com/market-data/bhavcopy) exposes date, instrument, commodity, expiry, OHLC, previous close, volume, value, and open interest. MCX states that data is available from November 2003.
- [MCX Gold product and current contract specifications](https://www.mcxindia.com/products/bullion/gold) lists Gold Mini, Gold Ten, Gold Guinea, and Gold Petal and links the effective specification PDFs.
- [MCX Datafeed overview](https://www.mcxindia.com/technology/datafeed) describes end-of-day Bhavcopy as contract-wise OHLC, volume, value, and open interest.

Always retain the exact specification PDF or circular effective for the historical contract being tested. Product rules can change.

## Contract normalization

| Symbol | Trading unit | Price quoted per | Purity | Current last-trading-day rule |
|---|---:|---:|---:|---|
| GOLDM | 100g | 10g | 995 | 5th calendar day, or preceding working day |
| GOLDTEN | 10g | 10g | 999 | Last calendar day, or preceding working day |
| GOLDGUINEA | 8g | 8g | 999 | Last calendar day, or preceding working day |
| GOLDPETAL | 1g | 1g | 999 | Last calendar day, or preceding working day |

All four current specifications use compulsory delivery and a staggered tender period covering the last three trading days, including expiry. The research gate uses a configurable conservative calendar-day buffer because a verified historical exchange-session calendar has not yet been imported. It must not claim exact tender-session eligibility until that calendar is present.

Specifications are selected by contract expiry from an effective-dated registry: GOLDM March 2025, November 2025, May 2026, and August 2026; GOLDTEN April 2025, November 2025, and July 2026; GOLDGUINEA January 2025, December 2025, and July 2026; GOLDPETAL April 2025, December 2025, and July 2026. Each version retains the official MCX PDF link where available. The [MCX bullion product page](https://www.mcxindia.com/en/products/bullion/gold) is the index for current documents and can change; verify an applicable circular and source PDF before extending the registry to a new historical period.

For each close:

```text
fine_price_per_gram = close / quoted_grams / purity_fraction
lot_notional = close × trading_unit_grams / quoted_grams
relative_spread_bps = (candidate_fine_price / reference_fine_price − 1) × 10,000
```

Do not divide GOLDM's price by its 100g trading unit. Its displayed price is quoted per 10g.

## Data pipeline

1. Acquire the raw daily Bhavcopy export and store it unchanged with retrieval timestamp and SHA-256 checksum.
2. Validate that the returned `Date` equals the requested date. Requests use `DD/MM/YYYY`; responses can use `MM/DD/YYYY`.
3. Trim padded symbols and parse compact expiry values such as `04SEP2026`.
4. Filter futures observations for the four target symbols.
5. Identify every record by `(trading_date, symbol, expiry_date)`. A symbol-only join fails closed when multiple expiries exist.
6. Compute days to expiry and reject entries that cannot exit before tender/expiry restrictions.
7. Normalize close prices and compute pair spreads.
8. Record data-quality flags instead of silently imputing suspicious observations.

The importer consumes an official downloaded CSV and never falls back to a third-party data source. It archives the raw bytes first, verifies SHA-256, and emits an accepted/rejected validation report. Clean daily outputs can be merged only after their content hashes and specification hashes pass verification; duplicate contract keys abort the merge. Legacy binary `.xls` files currently require a lossless CSV export, while the original file is retained with the research run.

Automated MCX access was blocked by the exchange edge service from the build environment on 14 October 2026. Therefore this repository currently contains no verified historical observations, and no synthetic record is labeled empirical.

## Signal design

For each pair, use a rolling training window ending at `t−1`:

```text
z_t = (spread_t − mean(spread[t−window:t])) / stdev(spread[t−window:t])
```

Candidate rule set:

- Observe at `|z| ≥ 2.0`
- Exit at `|z| ≤ 0.5`
- No entry if either leg fails minimum volume/open-interest thresholds
- No entry inside the contract-specific expiry buffer
- No alert unless expected convergence exceeds fees, taxes, slippage, and a safety buffer
- Apply a signal no earlier than the next session in the backtest
- Treat a zero-variance training window as statistically undefined, not as a forced signal

Thresholds must be chosen on training data and frozen before the holdout period.

## Walk-forward validation

- Split chronologically; never shuffle time-series rows.
- Partition chronologically into 60% training, 20% validation, and a final untouched 20% test set.
- Refit rolling statistics only from past observations.
- Price P&L using the actual contracts held, not a gold index.
- Use integer futures lots. The implemented hedge chooses one lot of the larger contract and the nearest whole number of smaller-contract lots, then reports remaining fine-gold exposure.
- Charge brokerage, exchange/regulatory fees, slippage, and funding separately on the two-leg notional.
- Stress slippage at explicit 1, 2, 5, and 10 basis-point scenarios by default.
- Report performance by pair and liquidity regime to expose concentration.

The P&L identity is checked daily:

```text
gross contract P&L
  = relative convergence P&L
  + residual fine-gold exposure P&L
  + unexplained numerical/model residual

net P&L
  = gross contract P&L
  − brokerage − fees − slippage − funding
```

The unexplained component is retained even when it is near zero; the system does not silently force the attribution to balance.

Required output metrics: eligible days and trades; gross convergence; explicit costs and net return; maximum drawdown; hit rate; holding period; turnover; residual gold beta; and sensitivity excluding the thinnest observations.

## Risks and honest limitations

- Official settlement or closing values are not necessarily executable fills.
- Daily volume does not reveal the quantity available at a price.
- Different expiry dates contain legitimate carry and calendar effects; not every spread is mispricing.
- GOLDTEN has a shorter history beginning in its 2025 listing period.
- Taxes, brokerage, exchange fees, impact, margin funding, and delivery/tender constraints can erase a paper edge.
- Historical contract specifications must be versioned; using today's rules for old contracts can introduce errors.
- The current dashboard values are synthetic fixtures and prove interaction and methodology only.
- The carry adjustment is a declared annualized configuration input, not an estimated fact. A zero setting means “no carry estimate supplied,” not “carry does not exist.”
- The close-plus-slippage model is hypothetical. Bhavcopy volume is an activity measure, not proof that the modeled integer-lot spread could be filled.

## MVP acceptance criteria

- Import at least one year of official rows for every available target contract.
- Produce a reproducible cleaned dataset plus a rejected-row report.
- Show one fully traced signal from raw rows to final decision.
- Demonstrate that changing costs can convert an alert into “no trade.”
- Run a frozen holdout and show attribution independent of gold direction.
- Export a judge-readable research snapshot.

## Work plan

1. **Data:** collect and checksum official exports; verify effective contract specifications.
2. **Research:** profile missingness, liquidity, roll behavior, and normalized spreads.
3. **Model:** freeze eligibility, scoring, cost, and exit rules.
4. **Validation:** run chronological holdout and sensitivity tests.
5. **Product:** replace synthetic fixtures with generated JSON from the Python pipeline.
6. **Presentation:** populate the supplied deck using `docs/PITCH_DECK.md` and record a 90-second demo path.

