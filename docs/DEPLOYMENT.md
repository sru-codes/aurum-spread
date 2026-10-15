# Railway deployment

Aurum Spread is one Railway web service built from the repository `Dockerfile`. The image builds the React app, then runs Caddy and the Python API in the same container. Caddy serves the UI, forwards `/api/*` and `/health` to Python, and forwards Railway's injected `PORT` to the web listener.

## Create or connect the service

1. In Railway, create a project and add a service from the GitHub repository `sru-codes/aurum-spread` (or connect the repository to an existing service).
2. Ensure the service uses the root `Dockerfile` and its repository root is this project.
3. Generate a public domain for the service.
4. Add a Railway volume mounted at `/app/data`. Raw uploads, validation reports, normalized datasets, cache entries, and published snapshots live there. Without the volume, filesystem writes are ephemeral and can disappear on redeploy. Railway volumes are runtime mounts and must be attached to the service; this repository cannot create one without access to your Railway project.
5. Set `AURUM_ADMIN_TOKEN` to a long random secret in Railway Variables. For example, generate a value locally with `openssl rand -hex 32`, then paste it into Railway—never commit it or put it in a `VITE_` variable.
6. Add optional provider credentials only if needed: `FRED_API_KEY` and `GNEWS_API_KEY`. Goldprice.dev credentials are optional according to the provider configuration; see [DATA_PROVIDERS.md](DATA_PROVIDERS.md).
7. Deploy and verify `https://<your-domain>/health` and `https://<your-domain>/api/research`.

Railway injects `PORT` for the public web process. Its healthcheck accepts a successful HTTP response; this project configures `/health`, which returns JSON including Python service health, engine version, and storage writability. The API also reports whether Railway provided a volume mount path. See [Railway healthchecks](https://docs.railway.com/deployments/healthchecks) and [Railway volumes](https://docs.railway.com/volumes).

## Use the hosted Python service

Keep `AURUM_ADMIN_TOKEN` in your local shell and set the deployed URL (no trailing slash):

```bash
export AURUM_RAILWAY_URL="https://<your-domain>"
read -rsp 'Railway admin token: ' AURUM_ADMIN_TOKEN; export AURUM_ADMIN_TOKEN; echo
```

Upload each official MCX CSV with the trading date printed on that file:

```bash
python3 scripts/railway_admin.py import ./bhavcopy.csv --date 15/10/2026
```

The importer responds with a dataset ID and validation report. Preserve each accepted ID, then merge the desired set of daily imports. Do not merge two files that contain duplicate contract/date/expiry keys:

```bash
python3 scripts/railway_admin.py merge mcx-history-<id1> mcx-history-<id2>
```

Run research against an explicit pair of expiries, then check `/api/research` for the published artifact:

```bash
python3 scripts/railway_admin.py run \
  --candidate GOLDTEN --candidate-expiry 2026-10-30 \
  --reference GOLDM --reference-expiry 2026-11-05 \
  --lookback 40 --annual-carry-bps 0
```

For supplementary context, run `python3 scripts/railway_admin.py refresh-context`. It refreshes supported provider data; unavailable providers remain clearly marked unavailable. These commands upload and calculate only the data you provide; there is no undocumented automated MCX download and no synthetic backfill.

GET routes `/api/health`, `/api/research`, and `/api/context` are public read-only endpoints. All POST routes require `Authorization: Bearer <AURUM_ADMIN_TOKEN>`. The browser dashboard only reads the published artifacts; it does not receive the admin token and cannot trigger imports or refreshes.

## Local production checks

```bash
npm ci
npm run build
npm run lint
npm test
python3 -m unittest discover -s analytics -v
```

If Docker is available, build and run the same image layout used by Railway:

```bash
docker build -t aurum-spread:0.3.0 .
docker run --rm -e PORT=3000 -p 3000:3000 aurum-spread:0.3.0
curl --fail http://localhost:3000/health
```

The API binds internally to port 8000; do not expose that port publicly. The entrypoint supervises the API and Caddy so a failed child process stops the container and lets Railway restart it.

## Limits and operational notes

- A real MCX export must be uploaded before the research endpoint can publish verified historical mode. The static demo is explicitly marked demo and remains available as a fallback.
- Attach the volume at exactly `/app/data`; this path contains all mutable service state.
- The single-container setup is appropriate for the hackathon prototype. It is not horizontally scalable because local files and published artifacts are shared only through that service's mounted volume.
- Rotate any token that has ever been pasted into chat, shell history, logs, or source control.
- There is no broker execution, order placement, guaranteed fill model, or claim that a historical result predicts future returns.
