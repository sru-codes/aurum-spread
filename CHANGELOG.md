# Changelog

All notable changes to Aurum Spread are documented here. The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) while it evolves as a hackathon prototype.

## [Unreleased]

### Added

- GitHub Actions CI for frontend/Python tests and Railway image runtime smoke tests

### Remaining

- Import and freeze an official MCX historical sample; none was supplied or accessible in the current environment
- Add a verified historical exchange-session calendar for exact tender-period gating

## [0.3.0] — 2026-10-15

### Added

- Python HTTP API for official MCX CSV imports, clean-dataset merges, expiry-aware research runs, and contextual provider refreshes
- Bearer-token protection for all data-mutating API routes; read-only dashboard artifact endpoints
- Railway container runtime supervises the Python API and Caddy in one service and exposes health/storage status
- Operator CLI for uploading source CSVs and invoking hosted data workflows without placing secrets in the frontend
- Idempotent re-import of an identical raw source without overwriting or duplicating it
- Railway deployment guide covering persistent volume mount, secret setup, operation, and limitations

### Verification status

- Local API integration tests exercise demo artifact serving, bearer authorization, and import → merge → research artifact flow
- The repository workspace is not linked to a Railway project, so deployment and production health have not been verified from this environment
- No official MCX file is bundled; real research mode requires an operator-supplied official export

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
- Railway data persistence requires the service volume to be attached at `/app/data`; hosted deployment must be verified in the Railway project
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

[Unreleased]: https://github.com/sru-codes/aurum-spread/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/sru-codes/aurum-spread/releases/tag/v0.3.0
[0.2.0]: https://github.com/sru-codes/aurum-spread/releases/tag/v0.2.0
[0.1.0]: https://github.com/sru-codes/aurum-spread/releases/tag/v0.1.0
