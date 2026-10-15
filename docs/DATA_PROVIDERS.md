# Data-provider setup

Provider capabilities and limits were verified against their official documentation on 14 October 2026.

## MCX India — authoritative futures source

- Source: [MCX Bhavcopy](https://www.mcxindia.com/market-data/bhavcopy)
- Authentication: none for manual exports
- Role: authoritative GOLDM, GOLDTEN, GOLDGUINEA, and GOLDPETAL contract observations
- Current limitation: MCX's edge service blocked automated access from the build environment. Download the official CSV manually and run `analytics/pipeline.py`. No third-party substitute is accepted as verified MCX history.

## goldprice.dev — supplementary international gold

- Documentation: [goldprice.dev API](https://goldprice.dev/docs/api-reference)
- Environment variable: optional `GOLDPRICE_API_KEY`
- Keyless limits: 10 requests/minute and 100/hour per IP; price is 15 minutes delayed
- Free key: 5,000 calls/month and 10 requests/minute
- Free history: most recent 30 days of daily XAU/USD bars
- Deeper history: Basic has one year; Plus/Pro have daily XAU back to 1996
- Attribution: Free commercial use requires a visible goldprice.dev credit; redistribution/resale is not included
- Product boundary: XAU/USD spot is contextual. It is not an MCX futures close or settlement.

The adapter rejects unexpected units or contract types, preserves `computed_at`, `is_stale`, and source metadata, excludes forming bars, and converts one troy ounce using exactly `31.1034768` grams.

## Frankfurter — supplementary reference FX

- Documentation: [Frankfurter v2](https://frankfurter.dev/)
- Authentication: none
- Limits: no monthly/daily quota; public requests are abuse-rate-limited
- Coverage: daily data from official/central-bank sources, with broad history back to 1948 depending on currency/provider
- Storage: local caching is explicitly encouraged
- Product boundary: rates are reference mid-market/blended observations, not executable FX quotes

The adapter preserves both requested and effective dates. Historical joins are exact-date only: a missing holiday observation remains missing and is never silently filled or sourced from a future date.

## FRED — optional macro context

- Documentation: [FRED API](https://fred.stlouisfed.org/docs/api/fred/)
- Environment variable: `FRED_API_KEY`
- Status in this repository: adapter implemented; not live-verified because no credential was supplied
- Point-in-time rule: requests pin the FRED real-time period to the research `as_of` date. Observation/revision dates after that cutoff are rejected.

Only economically motivated series should be configured, such as a documented interest-rate or inflation reference. Correlation must not be presented as causation.

## GNews — optional event context

- Documentation: [GNews API](https://docs.gnews.io/)
- Environment variable: `GNEWS_API_KEY`
- Free tier: 100 requests/day, 10 articles/request, last 30 days, 12-hour delay, truncated content
- Status in this repository: adapter implemented; not live-verified because no credential was supplied

Headlines are displayed as dated context only. The adapter rejects articles published after a historical cutoff, and news never enters the quantitative signal engine.

## Refresh

Copy `.env.example` to `.env` for your local secret manager or export variables in the shell. Do not put secrets in a `VITE_` variable.

```bash
python3 analytics/refresh_context.py \
  --output public/data/context.v1.json \
  --cache-dir .cache/providers
```

The command succeeds with partial provider availability and records each provider's health. It never invents a missing observation. On Railway, the authenticated `refresh-context` operator command refreshes providers server-side and publishes the resulting snapshot to the persistent volume. The dashboard's refresh button fetches the current API artifacts; it does not expose credentials or trigger an unauthenticated provider call.
