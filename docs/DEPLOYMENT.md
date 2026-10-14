# Deploying to Railway

The repository uses a multi-stage Docker build. Node builds the Vite application, then Caddy serves the immutable `dist` output. Railway terminates TLS and injects `PORT` at runtime.

## GitHub deployment

1. In Railway, create a project and choose **Deploy from GitHub repo**.
2. Select `sru-codes/aurum-spread`.
3. Railway detects the root `Dockerfile` and builds it.
4. Open the service settings and generate a public domain.
5. Verify `https://<domain>/health` returns `ok` and the root page loads.
6. Add the public URL to the GitHub repository About section.

No application secrets are required for the synthetic MVP. If future browser configuration is needed, only variables prefixed with `VITE_` are compiled into the frontend; therefore they must never contain secrets.

## Local production test

```bash
docker build -t aurum-spread:0.1.0 .
docker run --rm -e PORT=3000 -p 3000:3000 aurum-spread:0.1.0
curl --fail http://localhost:3000/health
```

The production server provides gzip/Zstandard compression, a health endpoint, conservative security headers, and SPA fallback routing.
