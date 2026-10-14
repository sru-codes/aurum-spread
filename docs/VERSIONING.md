# Versioning and releases

Aurum Spread uses Semantic Versioning: `MAJOR.MINOR.PATCH`.

- **PATCH** — compatible fixes, documentation corrections, and methodology clarifications that do not change output interpretation.
- **MINOR** — new compatible product or research capabilities, new contract families, or materially expanded analytics.
- **MAJOR** — incompatible data schemas, signal semantics, API contracts, or research assumptions.

Versions below `1.0.0` are hackathon-stage releases. A minor version may still change internal APIs, but the changelog must describe the impact.

## Release checklist

1. Pull and reconcile the latest `origin/main`.
2. Confirm the worktree contains no credentials or raw private data.
3. Move completed items from **Unreleased** into the new changelog version.
4. Update `package.json` and `package-lock.json` to the same version.
5. Run the frontend build, lint, Python tests, and high-severity dependency audit.
6. Build the production Docker image when Docker is available.
7. Commit and push `main` without rewriting history.
8. Create an annotated `vX.Y.Z` tag on the verified commit and push it.
9. Publish a GitHub Release using the matching changelog section.
10. Deploy that exact commit to Railway and verify `/health` plus the public page.
