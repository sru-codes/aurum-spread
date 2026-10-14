# Contributing

Aurum Spread is a Hack in Hills ’26 prototype. Focus contributions on analytical correctness, reproducibility, clear risk communication, and a quiet trader-facing experience.

## Before opening a pull request

1. Create a branch from the latest `main`.
2. Keep one coherent change per pull request.
3. Never commit credentials, private data, downloaded raw market files, `node_modules`, or build output.
4. Label synthetic or illustrative values prominently.
5. Add tests for parsing, normalization, signal timing, and cost logic.
6. Update `CHANGELOG.md` under **Unreleased** for user-visible changes.

## Required checks

```bash
npm ci
npm run build
npm run lint
python3 -m unittest discover -s analytics -v
npm audit --audit-level=high
```

## Research rules

- Preserve actual `expiry_date`; do not silently stitch near-month contracts.
- Validate the returned MCX date against the requested date.
- Use only past information for each walk-forward decision.
- Apply signals no earlier than the following tradable observation.
- Include both legs, relevant costs, thin-day exclusions, and expiry constraints.
- Separate spread-strategy performance from underlying gold-price exposure.
- Treat a “no persistent edge after costs” result as valid.

## Pull requests

Explain the user-visible outcome, data assumptions, tests performed, screenshots for UI changes, and any residual risks. By contributing, you agree that your work is licensed under the repository's MIT License.
