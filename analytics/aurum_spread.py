"""Core, dependency-free analytics for the Aurum Spread prototype."""

from __future__ import annotations

import csv
import math
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Sequence


class DataQualityError(ValueError):
    """Raised when an exchange row cannot be used without ambiguity."""


@dataclass(frozen=True)
class ContractSpec:
    symbol: str
    trading_unit_grams: float
    quoted_grams: float
    purity: float
    expiry_window: str


CONTRACTS = {
    "GOLDM": ContractSpec("GOLDM", 100, 10, 0.995, "3rd–5th"),
    "GOLDTEN": ContractSpec("GOLDTEN", 10, 10, 0.999, "27th–31st"),
    "GOLDGUINEA": ContractSpec("GOLDGUINEA", 8, 8, 0.999, "27th–31st"),
    "GOLDPETAL": ContractSpec("GOLDPETAL", 1, 1, 0.999, "27th–31st"),
}


@dataclass(frozen=True)
class Observation:
    trading_date: date
    expiry_date: date
    symbol: str
    close: float
    volume: int
    open_interest: int
    fine_gold_price: float
    lot_notional: float

    @property
    def days_to_expiry(self) -> int:
        return (self.expiry_date - self.trading_date).days


@dataclass(frozen=True)
class BacktestResult:
    gross_bps: float
    cost_bps: float
    net_bps: float
    trades: int
    max_drawdown_bps: float


def _first(row: dict[str, str], *keys: str) -> str:
    normalized = {key.strip().lower().replace(" ", ""): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(key.lower().replace(" ", ""))
        if value not in (None, ""):
            return str(value).strip()
    raise DataQualityError(f"Missing required column; expected one of {keys}")


def parse_response_date(value: str) -> date:
    """MCX response dates are normally MM/DD/YYYY; ISO is accepted for fixtures."""
    for pattern in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), pattern).date()
        except ValueError:
            pass
    raise DataQualityError(f"Unsupported response Date: {value!r}")


def parse_expiry(value: str) -> date:
    for pattern in ("%d%b%Y", "%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip().upper(), pattern).date()
        except ValueError:
            pass
    raise DataQualityError(f"Unsupported ExpiryDate: {value!r}")


def validate_requested_date(requested_ddmmyyyy: str, returned: date) -> None:
    requested = datetime.strptime(requested_ddmmyyyy, "%d/%m/%Y").date()
    if requested != returned:
        raise DataQualityError(
            f"MCX returned {returned.isoformat()} for requested {requested.isoformat()}; "
            "refusing a potentially stale fallback response"
        )


def normalize_row(row: dict[str, str], requested_date: str | None = None) -> Observation:
    symbol = _first(row, "Symbol", "Commodity").upper()
    if symbol not in CONTRACTS:
        raise DataQualityError(f"Unsupported symbol: {symbol!r}")
    spec = CONTRACTS[symbol]
    trading_date = parse_response_date(_first(row, "Date"))
    if requested_date:
        validate_requested_date(requested_date, trading_date)
    expiry_date = parse_expiry(_first(row, "ExpiryDate", "Expiry Date"))
    close = float(_first(row, "Close", "SettlementPrice", "Settlement Price").replace(",", ""))
    volume = int(float(_first(row, "Volume", "Vol(Lots)", "Vol (Lots)").replace(",", "")))
    open_interest = int(float(_first(row, "OpenInterest", "OI(Lots)", "OI (Lots)").replace(",", "")))
    if close <= 0 or volume < 0 or open_interest < 0:
        raise DataQualityError("Close must be positive and activity fields cannot be negative")
    fine_gold_price = close / spec.quoted_grams / spec.purity
    lot_notional = close * spec.trading_unit_grams / spec.quoted_grams
    return Observation(trading_date, expiry_date, symbol, close, volume, open_interest, fine_gold_price, lot_notional)


def load_csv(path: str | Path, requested_date: str | None = None) -> list[Observation]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        observations = []
        for row in rows:
            symbol = (row.get("Symbol") or row.get("Commodity") or "").strip().upper()
            if symbol in CONTRACTS:
                observations.append(normalize_row(row, requested_date))
    return observations


def spread_bps(candidate: Observation, reference: Observation) -> float:
    if candidate.trading_date != reference.trading_date:
        raise DataQualityError("Spread legs must share a trading date")
    return (candidate.fine_gold_price / reference.fine_gold_price - 1.0) * 10_000


def walk_forward_zscores(values: Sequence[float], window: int = 40) -> list[float | None]:
    """Score value t using values [t-window, t), never value t itself."""
    if window < 2:
        raise ValueError("window must be at least 2")
    scores: list[float | None] = []
    for index, value in enumerate(values):
        if index < window:
            scores.append(None)
            continue
        training = values[index - window:index]
        deviation = statistics.stdev(training)
        scores.append(0.0 if math.isclose(deviation, 0.0) else (value - statistics.mean(training)) / deviation)
    return scores


def backtest_spread(
    spreads: Sequence[float],
    scores: Sequence[float | None],
    eligible: Sequence[bool] | None = None,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
    cost_per_position_change_bps: float = 6.0,
) -> BacktestResult:
    """Close-to-close research backtest with signals applied one session later."""
    if len(spreads) != len(scores):
        raise ValueError("spreads and scores must have equal length")
    gates = list(eligible) if eligible is not None else [True] * len(spreads)
    if len(gates) != len(spreads):
        raise ValueError("eligible must have equal length")
    position = 0
    gross = 0.0
    costs = 0.0
    trades = 0
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for index in range(1, len(spreads)):
        gross += position * (spreads[index] - spreads[index - 1])
        equity = gross - costs
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)
        prior_score = scores[index - 1]
        target = position
        if not gates[index - 1] or prior_score is None:
            target = 0
        elif position == 0 and prior_score >= entry_z:
            target = -1
        elif position == 0 and prior_score <= -entry_z:
            target = 1
        elif position != 0 and abs(prior_score) <= exit_z:
            target = 0
        if target != position:
            costs += abs(target - position) * cost_per_position_change_bps
            if position == 0 and target != 0:
                trades += 1
            position = target
    net = gross - costs
    return BacktestResult(gross, costs, net, trades, max_drawdown)


def pair_by_date(observations: Iterable[Observation], candidate: str, reference: str) -> list[tuple[Observation, Observation]]:
    by_key = {(item.trading_date, item.symbol): item for item in observations}
    dates = sorted({item.trading_date for item in observations})
    return [(by_key[(day, candidate)], by_key[(day, reference)]) for day in dates if (day, candidate) in by_key and (day, reference) in by_key]

