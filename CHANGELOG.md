# Changelog

All notable changes to Aurum Spread are documented here. The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) while it evolves as a hackathon prototype.

## [Unreleased]

### Remaining

- Import and freeze an official MCX historical sample; none was supplied or accessible in the current environment
- Add a verified historical exchange-session calendar for exact tender-period gating

## [0.2.0] — 2026-10-15

### Added

- Official MCX CSV archive, requested-date validation, raw SHA-256 manifest, rejected-row report, and idempotent clean-dataset merge
- Supplementary Goldprice.dev and Frankfurter provider adapters with caching, bounded retries, explicit units, and date-safe alignment
- Optional server-side FRED and GNews adapters, excluded from quantitative signals
- Versioned research snapshots and a deterministic synthetic fixture generator
- Interactive dashboard controls, historical time-machine, imported snapshot support, dark mode, source center, and downloadable snapshots
- Separate test-partition P&L attribution and cost sensitivity, effective-dated contract specifications, and typed frontend contracts
- Expanded Python and frontend regression tests plus provider, architecture, and deployment guides

### Known limitations

- No official MCX historical file is included; the default dashboard remains labeled synthetic `DEMO`
- Railway serves static artifacts; imports, research generation, and provider refresh are explicit Python jobs, not on-demand backend endpoints
- Exchange-session tender lifecycle is approximated with a conservative calendar-day buffer pending a verified historical exchange calendar
- FRED and GNews need credentials and were not refreshed; Goldprice.dev history beyond its free window may require a paid plan

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

[Unreleased]: https://github.com/sru-codes/aurum-spread/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/sru-codes/aurum-spread/releases/tag/v0.2.0
[0.1.0]: https://github.com/sru-codes/aurum-spread/releases/tag/v0.1.0
