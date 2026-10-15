"""Generate the explicitly synthetic UI fixture through the real engine."""

from __future__ import annotations

import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from aurum_spread import Observation, normalize_row
from pipeline import ENGINE_VERSION, SCHEMA_VERSION, canonical_json, sha256_bytes
from research import (
    CostModel,
    ResearchConfig,
    build_research_snapshot,
    build_spread_series,
    cost_sensitivity,
    simulate_contracts,
)


EXPIRIES = {
    "GOLDM": date(2026, 11, 5),
    "GOLDTEN": date(2026, 10, 30),
    "GOLDGUINEA": date(2026, 10, 30),
    "GOLDPETAL": date(2026, 10, 30),
}
QUOTE_GRAMS = {"GOLDM": 10, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}
PURITY = {"GOLDM": 0.995, "GOLDTEN": 0.999, "GOLDGUINEA": 0.999, "GOLDPETAL": 0.999}
VOLUME_BASE = {"GOLDM": 14_000, "GOLDTEN": 1_400, "GOLDGUINEA": 430, "GOLDPETAL": 2_100}
OI_BASE = {"GOLDM": 32_000, "GOLDTEN": 4_800, "GOLDGUINEA": 1_700, "GOLDPETAL": 7_000}


def sessions(end: date, count: int) -> list[date]:
    values = []
    day = end
    while len(values) < count:
        if day.weekday() < 5:
            values.append(day)
        day -= timedelta(days=1)
    return sorted(values)


def make_observations() -> list[Observation]:
    output: list[Observation] = []
    offsets = {"GOLDM": 0.0, "GOLDTEN": 2.5, "GOLDGUINEA": -2.0, "GOLDPETAL": 1.0}
    for index, day in enumerate(sessions(date(2026, 10, 14), 90)):
        fine_reference = 12_150 + index * 3.2 + math.sin(index / 6) * 22
        for symbol in EXPIRIES:
            cycle = math.sin(index / (5.5 + len(symbol) / 10)) * (4 + len(symbol) / 5)
            terminal = 0.0
            if index >= 82:
                terminal = (index - 81) * offsets[symbol]
            spread_bps = cycle + terminal
            fine_price = fine_reference * (1 + spread_bps / 10_000)
            close = fine_price * QUOTE_GRAMS[symbol] * PURITY[symbol]
            intraday = close * 0.0008
            volume = VOLUME_BASE[symbol] + int(80 * math.sin(index / 4))
            oi = OI_BASE[symbol] + index * 5
            output.append(normalize_row({
                "Date": day.isoformat(),
                "Instrument Name": "FUTCOM",
                "Symbol": symbol,
                "Expiry Date": EXPIRIES[symbol].isoformat(),
                "Open": f"{close - intraday / 3:.2f}",
                "High": f"{close + intraday:.2f}",
                "Low": f"{close - intraday:.2f}",
                "Close": f"{close:.2f}",
                "Previous Close": f"{close - 5:.2f}",
                "Vol (Lots)": str(max(1, volume)),
                "OI (Lots)": str(oi),
            }))
    return output


def snapshot_for(
    observations: list[Observation], candidate: str, lookback: int
) -> dict:
    config = ResearchConfig(
        lookback_sessions=lookback,
        minimum_training_sessions=lookback,
        minimum_volume_lots=10,
        minimum_open_interest_lots=50,
        minimum_days_to_expiry=7,
        maximum_expiry_gap_days=45,
        annual_carry_bps=600,
    )
    costs = CostModel()
    points = build_spread_series(
        observations, candidate, EXPIRIES[candidate], "GOLDM", EXPIRIES["GOLDM"], config
    )
    simulation = simulate_contracts(points, config, costs)
    sensitivity = cost_sensitivity(points, config, costs, (1.0, 2.0, 5.0, 10.0))
    snapshot = build_research_snapshot(
        points, simulation, config, costs,
        {
            "fixture": "analytics/generate_demo.py",
            "classification": "deterministic synthetic fixture; not market evidence",
        },
        sensitivity,
    )
    snapshot["mode"] = "DEMO"
    snapshot["pair"] = {
        "candidate_symbol": candidate,
        "candidate_expiry": EXPIRIES[candidate].isoformat(),
        "reference_symbol": "GOLDM",
        "reference_expiry": EXPIRIES["GOLDM"].isoformat(),
    }
    snapshot.pop("content_sha256", None)
    snapshot["content_sha256"] = sha256_bytes(canonical_json(snapshot).encode())
    return snapshot


def build_bundle() -> dict:
    observations = make_observations()
    latest = max(item.trading_date for item in observations)
    contracts = []
    for symbol in EXPIRIES:
        item = next(row for row in reversed(observations) if row.symbol == symbol)
        contracts.append({
            "symbol": symbol,
            "trading_date": item.trading_date.isoformat(),
            "expiry_date": item.expiry_date.isoformat(),
            "close": str(item.close),
            "fine_gold_price_per_gram": str(item.fine_gold_price),
            "volume_lots": item.volume,
            "open_interest_lots": item.open_interest,
            "days_to_expiry": item.days_to_expiry,
            "trading_unit_grams": {"GOLDM": 100, "GOLDTEN": 10, "GOLDGUINEA": 8, "GOLDPETAL": 1}[symbol],
            "quoted_grams": QUOTE_GRAMS[symbol],
            "purity": PURITY[symbol],
        })
    analyses = {}
    for candidate in ("GOLDTEN", "GOLDGUINEA", "GOLDPETAL"):
        pair = f"{candidate}/GOLDM"
        analyses[pair] = {str(window): snapshot_for(observations, candidate, window) for window in (20, 40, 60)}
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "mode": "DEMO",
        "generated_at_utc": datetime(2026, 10, 14, 18, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "latest_observation_date": latest.isoformat(),
        "disclaimer": "Deterministic synthetic fixture for product demonstration. Not empirical MCX evidence.",
        "contracts": contracts,
        "analyses": analyses,
    }
    bundle["content_sha256"] = sha256_bytes(canonical_json(bundle).encode())
    return bundle


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "public" / "data" / "demo-research.v1.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build_bundle(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(target)
