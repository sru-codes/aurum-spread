"""Authenticated CLI for Railway imports, merges, research runs, and refreshes."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _base_url() -> str:
    value = os.getenv("AURUM_RAILWAY_URL", "").strip().rstrip("/")
    if not value:
        raise SystemExit("Set AURUM_RAILWAY_URL to the deployed HTTPS service URL")
    parts = urllib.parse.urlsplit(value)
    local_http = parts.scheme == "http" and parts.hostname in {"localhost", "127.0.0.1", "::1"}
    if parts.scheme != "https" and not local_http:
        raise SystemExit("AURUM_RAILWAY_URL must use HTTPS (HTTP is allowed only for loopback testing)")
    return value


def _post(path: str, payload: bytes, content_type: str, extra_headers: dict[str, str] | None = None) -> int:
    token = os.getenv("AURUM_ADMIN_TOKEN", "")
    if not token:
        raise SystemExit("Set AURUM_ADMIN_TOKEN in your local environment; do not put it in the repository")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": content_type}
    headers.update(extra_headers or {})
    request = urllib.request.Request(_base_url() + path, data=payload, headers=headers, method="POST")
    try:
        response = urllib.request.urlopen(request, timeout=180)
    except urllib.error.HTTPError as exc:
        response = exc
    except OSError as exc:
        raise SystemExit(f"Railway request failed: {exc}") from exc
    body = response.read().decode("utf-8", errors="replace")
    try:
        print(json.dumps(json.loads(body), indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        print(body)
    return 0 if 200 <= response.status < 300 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    import_parser = sub.add_parser("import", help="upload one official MCX CSV Bhavcopy")
    import_parser.add_argument("csv", type=Path)
    import_parser.add_argument("--date", required=True, help="Requested trading date in DD/MM/YYYY")

    merge_parser = sub.add_parser("merge", help="merge imported daily dataset IDs")
    merge_parser.add_argument("dataset_ids", nargs="+")

    run_parser = sub.add_parser("run", help="run expiry-selected historical research")
    run_parser.add_argument("--dataset-id", default="current")
    run_parser.add_argument("--candidate", required=True)
    run_parser.add_argument("--candidate-expiry", required=True)
    run_parser.add_argument("--reference", required=True)
    run_parser.add_argument("--reference-expiry", required=True)
    run_parser.add_argument("--lookback", type=int, default=40)
    run_parser.add_argument("--annual-carry-bps", type=float, default=0.0)

    sub.add_parser("refresh-context", help="refresh Goldprice.dev and Frankfurter reference artifacts")
    args = parser.parse_args()

    if args.command == "import":
        if args.csv.suffix.lower() != ".csv":
            raise SystemExit("Only official .csv exports are accepted; convert legacy .xls without altering rows")
        query = urllib.parse.urlencode({"requested_date_ddmmyyyy": args.date})
        return _post(
            f"/api/mcx/import?{query}", args.csv.read_bytes(), "text/csv",
            {"X-Filename": args.csv.name},
        )
    if args.command == "merge":
        payload = json.dumps({"dataset_ids": args.dataset_ids}).encode()
        return _post("/api/mcx/merge", payload, "application/json")
    if args.command == "run":
        payload = json.dumps({
            "dataset_id": args.dataset_id,
            "candidate": args.candidate,
            "candidate_expiry": args.candidate_expiry,
            "reference": args.reference,
            "reference_expiry": args.reference_expiry,
            "lookback_sessions": args.lookback,
            "annual_carry_bps": args.annual_carry_bps,
        }).encode()
        return _post("/api/research/run", payload, "application/json")
    return _post("/api/context/refresh", b"{}", "application/json")


if __name__ == "__main__":
    raise SystemExit(main())
