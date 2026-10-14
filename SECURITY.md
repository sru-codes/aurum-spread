# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | Yes |
| Earlier prototypes | No |

## Reporting a vulnerability

Please do not disclose a vulnerability in a public issue. Use GitHub's **Security → Advisories → Report a vulnerability** flow for this repository.

Include:

- the affected version or commit;
- reproduction steps or a minimal proof of concept;
- likely impact;
- any suggested mitigation;
- whether the issue may expose credentials, user data, or deployment infrastructure.

The maintainers will acknowledge a complete report as soon as reasonably possible, validate it, and coordinate a fix before public disclosure. This is a hackathon project maintained on a best-effort basis and does not promise a commercial response SLA.

## Scope

Security reports may cover the web application, analytics parser, dependency chain, Docker/Caddy deployment, or CI configuration. Incorrect market signals, methodology disagreements, and data-quality concerns belong in normal GitHub issues unless they also create a security impact.

## Secrets

Never commit API keys, access tokens, credentials, raw private datasets, or `.env` files. If a secret is exposed, revoke it first, then remove it from the repository and deployment environment. Rewriting Git history is not a substitute for revocation.

## Financial disclaimer

Aurum Spread is a research prototype. It does not execute orders, guarantee fills, or provide investment advice. Exchange settlement values and synthetic demo data must not be represented as executable market prices.
