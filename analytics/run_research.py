"""Regenerate a versioned research snapshot from a validated clean dataset."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from aurum_spread import DataQualityError, Observation, normalize_row
from pipeline import canonical_json, sha256_bytes
from research import (
    CostModel,
    ResearchConfig,
    build_research_snapshot,
    build_spread_series,
    cost_sensitivity,
    simulate_contracts,
    write_research_snapshot,
)


def _verify_content_hash(payload: dict[str, Any]) -> None:
    claimed = payload.get("content_sha256")
    without_hash = {key: value for key, value in payload.items() if key != "content_sha256"}
    actual = sha256_bytes(canonical_json(without_hash).encode("utf-8"))
    if claimed != actual:
        raise DataQualityError(f"Clean dataset content hash mismatch: expected {claimed!r}, computed {actual}")


def load_clean_dataset(path: str | Path) -> tuple[list[Observation], dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("mode") != "VERIFIED_HISTORICAL":
        raise DataQualityError("Research runner accepts only VERIFIED_HISTORICAL cleaned datasets")
    _verify_content_hash(payload)
    observations = []
    for item in payload.get("observations", []):
        observations.append(normalize_row({
            "Date": item["trading_date"],
            "Instrument Name": item["instrument_name"],
            "Symbol": item["symbol"],
            "Expiry Date": item["expiry_date"],
            "Open": item["open"],
            "High": item["high"],
            "Low": item["low"],
            "Close": item["close"],
            "Previous Close": item.get("previous_close") or "",
            "Vol (Lots)": str(item["volume_lots"]),
            "OI (Lots)": str(item["open_interest_lots"]),
        }))
    if not observations:
        raise DataQualityError("Clean dataset has no observations")
    return observations, payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run expiry-aware Aurum Spread research")
    parser.add_argument("clean_dataset", type=Path)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--candidate-expiry", type=date.fromisoformat, required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--reference-expiry", type=date.fromisoformat, required=True)
    parser.add_argument("--lookback", type=int, default=40)
    parser.add_argument("--annual-carry-bps", type=float, default=0.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    observations, clean = load_clean_dataset(args.clean_dataset)
    config = ResearchConfig(
        lookback_sessions=args.lookback,
        minimum_training_sessions=args.lookback,
        annual_carry_bps=args.annual_carry_bps,
    )
    costs = CostModel()
    points = build_spread_series(
        observations,
        args.candidate.upper(),
        args.candidate_expiry,
        args.reference.upper(),
        args.reference_expiry,
        config,
    )
    if not points:
        raise DataQualityError("Selected contracts have no common trading sessions")
    simulation = simulate_contracts(points, config, costs)
    sensitivity = cost_sensitivity(points, config, costs, (1.0, 2.0, 5.0, 10.0))
    snapshot = build_research_snapshot(
        points,
        simulation,
        config,
        costs,
        {
            "dataset_id": clean["dataset_id"],
            "source_lineage": clean["lineage"],
            "clean_content_sha256": clean["content_sha256"],
        },
        sensitivity,
    )
    write_research_snapshot(args.output, snapshot)
    print(json.dumps({"output": str(args.output), "content_sha256": snapshot["content_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
