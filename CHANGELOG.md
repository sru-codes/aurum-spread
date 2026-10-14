# Changelog

All notable changes to Aurum Spread are documented here. The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) while it evolves as a hackathon prototype.

## [Unreleased]

### Added

- Expiry-safe contract keys and explicit multi-expiry pairing
- Strict MCX CSV validation with immutable raw archives, SHA-256 lineage, manifests, and rejected-row reports
- Effective-expiry contract specification registry for all four target gold futures
- Hash-verified daily-dataset merge and deterministic research snapshot generation
- Trailing-only spread, liquidity, market-state, eligibility, carry, and lifecycle analysis
- Chronological train/validation/test labels and next-session research simulation
- Integer-lot contract P&L with convergence, gold exposure, unexplained residual, and itemized cost attribution
- Slippage sensitivity scenarios and expanded regression coverage

### Remaining

- Import and freeze an official MCX historical sample (automated access is blocked in the current environment)
- Connect generated research snapshots to every dashboard control and chart
- Add a verified historical exchange-session calendar for exact tender-period gating

## [0.1.0] — 2026-10-14

### Added

- Interactive relative-value monitor for GOLDM, GOLDTEN, GOLDGUINEA, and GOLDPETAL
- Purity and quotation-base normalization
- Statistical, lifecycle, liquidity, and transaction-cost signal gates
- Synthetic, explicitly labeled demonstration dataset
- Walk-forward Python analytics with lagged signals and five automated tests
- Methodology, official-data notes, research blueprint, and pitch-deck outline
- shadcn UI primitives and restrained React Bits motion with reduced-motion support
- Docker/Caddy deployment configuration for Railway
- Security, contribution, licensing, and release policies

### Known limitations

- Visible market values and performance metrics are synthetic demonstration fixtures
- No live or automated MCX data connector is included yet
- No order routing or execution functionality is provided

[Unreleased]: https://github.com/sru-codes/aurum-spread/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sru-codes/aurum-spread/releases/tag/v0.1.0
