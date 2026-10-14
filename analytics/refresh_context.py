"""Refresh a static, attributed supplementary-market context snapshot."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

from pipeline import ENGINE_VERSION, SCHEMA_VERSION, canonical_json, sha256_bytes
from providers.base import JsonHttpClient, ProviderError
from providers.frankfurter import FrankfurterAdapter, usd_ounce_to_inr_gram
from providers.goldprice import GoldPriceAdapter


def _decimal_string(value: Decimal) -> str:
    return format(value, "f")


def build_context_snapshot(cache_dir: str | Path, *, now: datetime | None = None) -> dict[str, Any]:
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    today = current.date()
    providers: list[dict[str, Any]] = []
    international: dict[str, Any] = {}

    gold = None
    try:
        gold_client = JsonHttpClient("goldprice.dev", cache_dir)
        gold = GoldPriceAdapter(gold_client, os.getenv("GOLDPRICE_API_KEY") or None).fetch_spot()
        providers.append({
            "id": "goldprice.dev",
            "status": "stale" if gold.is_stale else "available",
            "last_successful_update": gold.retrieved_at_utc,
            "latest_observation": gold.computed_at_utc.isoformat(),
            "authentication": "optional API key; keyless is 15-minute delayed",
            "coverage": "Free: latest spot and 30 days of daily XAU/USD bars",
            "limitations": "International reference spot, not MCX futures; free commercial use requires visible attribution",
        })
        international.update({
            "gold_spot": {
                "price_usd_per_troy_ounce": _decimal_string(gold.price_usd_per_troy_ounce),
                "price_usd_per_gram": _decimal_string(gold.price_usd_per_gram),
                "computed_at_utc": gold.computed_at_utc.isoformat(),
                "is_stale": gold.is_stale,
                "sources": list(gold.sources),
                "source_url": gold.source_url,
            }
        })
    except ProviderError as exc:
        providers.append({
            "id": "goldprice.dev", "status": "error", "error_code": exc.code,
            "last_successful_update": None, "latest_observation": None,
            "authentication": "optional API key", "coverage": "unavailable in this refresh",
            "limitations": str(exc),
        })

    fx = None
    try:
        fx_client = JsonHttpClient("frankfurter", cache_dir)
        fx = FrankfurterAdapter(fx_client).fetch_rate(today, "USD", "INR")
        providers.append({
            "id": "frankfurter", "status": "available",
            "last_successful_update": fx.retrieved_at_utc,
            "latest_observation": fx.effective_date.isoformat(),
            "authentication": "none",
            "coverage": "Daily reference rates; historical coverage varies by contributing official source",
            "limitations": "Reference mid-market/blended rate, not an executable FX quote",
        })
        international["usd_inr"] = {
            "rate": _decimal_string(fx.rate),
            "requested_date": today.isoformat(),
            "effective_date": fx.effective_date.isoformat(),
            "source_url": fx.source_url,
        }
    except ProviderError as exc:
        providers.append({
            "id": "frankfurter", "status": "error", "error_code": exc.code,
            "last_successful_update": None, "latest_observation": None,
            "authentication": "none", "coverage": "unavailable in this refresh",
            "limitations": str(exc),
        })

    if gold and fx:
        international["gold_reference_inr_per_gram"] = {
            "value": _decimal_string(usd_ounce_to_inr_gram(gold.price_usd_per_troy_ounce, fx.rate)),
            "calculation": "XAU/USD per troy ounce × USD/INR ÷ 31.1034768",
            "gold_timestamp_utc": gold.computed_at_utc.isoformat(),
            "fx_effective_date": fx.effective_date.isoformat(),
            "classification": "contextual reference; not an MCX settlement or executable price",
        }

    providers.extend([
        {
            "id": "fred", "status": "not_configured" if not os.getenv("FRED_API_KEY") else "configured_not_refreshed",
            "last_successful_update": None, "latest_observation": None,
            "authentication": "FRED_API_KEY required server-side",
            "coverage": "Optional point-in-time macroeconomic observations",
            "limitations": "Not used in signals; revision/vintage handling required",
        },
        {
            "id": "gnews", "status": "not_configured" if not os.getenv("GNEWS_API_KEY") else "configured_not_refreshed",
            "last_successful_update": None, "latest_observation": None,
            "authentication": "GNEWS_API_KEY required server-side",
            "coverage": "Free: 100 requests/day, 10 articles/request, last 30 days, 12-hour delay",
            "limitations": "Context only; never enters quantitative signal formation",
        },
    ])
    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "generated_at_utc": current.isoformat().replace("+00:00", "Z"),
        "mode": "SUPPLEMENTARY_REFERENCE",
        "providers": providers,
        "international": international,
    }
    snapshot["content_sha256"] = sha256_bytes(canonical_json(snapshot).encode("utf-8"))
    return snapshot


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh supplementary reference-market snapshot")
    parser.add_argument("--output", type=Path, default=Path("public/data/context.v1.json"))
    parser.add_argument("--cache-dir", type=Path, default=Path(os.getenv("AURUM_CACHE_DIR", ".cache/providers")))
    args = parser.parse_args(argv)
    snapshot = build_context_snapshot(args.cache_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "content_sha256": snapshot["content_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
