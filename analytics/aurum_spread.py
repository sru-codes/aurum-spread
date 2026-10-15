"""Auditable, expiry-aware primitives for Aurum Spread research.

The module deliberately has no third-party dependencies. Monetary inputs use
``Decimal`` until a statistic requires floating-point arithmetic. No importer
function fills a missing value or chooses an expiry implicitly.
"""

from __future__ import annotations

import csv
import math
import re
import statistics
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Mapping, Sequence


class DataQualityError(ValueError):
    """Raised when exchange data cannot be used without ambiguity."""


class AmbiguousContractError(DataQualityError):
    """Raised when a symbol has multiple expiries and none was selected."""


@dataclass(frozen=True)
class ContractSpec:
    symbol: str
    trading_unit_grams: Decimal
    quoted_grams: Decimal
    purity: Decimal
    last_trading_day_rule: str
    tender_period_sessions: int
    effective_expiry_from: date
    source_url: str


MCX_GOLD_PAGE = "https://www.mcxindia.com/products/bullion/gold"

# MCX labels specification documents "<month> contract onwards", so versions
# are selected by contract expiry. Earlier GOLDTEN observations are rejected.
CONTRACT_SPECS: dict[str, tuple[ContractSpec, ...]] = {
    "GOLDM": (
        ContractSpec(
            "GOLDM", Decimal("100"), Decimal("10"), Decimal("0.995"),
            "5th calendar day, or preceding working day", 3,
            date(2025, 3, 1),
            "https://www.mcxindia.com/products/bullion/gold-mini",
        ),
        ContractSpec(
            "GOLDM", Decimal("100"), Decimal("10"), Decimal("0.995"),
            "5th calendar day, or preceding working day", 3,
            date(2025, 11, 1),
            "https://www.mcxindia.com/docs/default-source/products/contract-specification/gold-mini/gold-mini-november-2025-contract-onwardsfc22554857fb64e3bdfdff00007acb35.pdf",
        ),
        ContractSpec(
            "GOLDM", Decimal("100"), Decimal("10"), Decimal("0.995"),
            "5th calendar day, or preceding working day", 3,
            date(2026, 5, 1),
            "https://www.mcxindia.com/docs/default-source/products/contract-specification/gold-mini/gold-mini-may-2026-contract-onwards.pdf",
        ),
        ContractSpec(
            "GOLDM", Decimal("100"), Decimal("10"), Decimal("0.995"),
            "5th calendar day, or preceding working day", 3,
            date(2026, 8, 1),
            "https://www.mcxindia.com/docs/default-source/about-us/gold-mini-august-2026-contract-onwards8a79913a-e8de-4136-9f0b-25d31dc163c4.pdf",
        ),
    ),
    "GOLDTEN": (
        ContractSpec(
            "GOLDTEN", Decimal("10"), Decimal("10"), Decimal("0.999"),
            "last calendar day, or preceding working day", 3,
            date(2025, 4, 1),
            "https://www.mcxindia.com/docs/default-source/products/contract-specification/gold-ten/gold-ten-april-2025-contract-onwards7fb63e4857fb64e3bdfdff00007acb3580008247-f6c1-4a56-be21-ac18ff0bdbe4.pdf",
        ),
        ContractSpec(
            "GOLDTEN", Decimal("10"), Decimal("10"), Decimal("0.999"),
            "last calendar day, or preceding working day", 3,
            date(2025, 11, 1),
            "https://www.mcxindia.com/docs/default-source/products/contract-specification/gold-ten/gold-ten-november-2025-contract-onwards9a08564857fb64e3bdfdff00007acb35.pdf",
        ),
        ContractSpec(
            "GOLDTEN", Decimal("10"), Decimal("10"), Decimal("0.999"),
            "last calendar day, or preceding working day", 3,
            date(2026, 7, 1),
            "https://www.mcxindia.com/docs/default-source/about-us/gold-ten-july-2026-contract-onwards.pdf",
        ),
    ),
    "GOLDGUINEA": (
        ContractSpec(
            "GOLDGUINEA", Decimal("8"), Decimal("8"), Decimal("0.999"),
            "last calendar day, or preceding working day", 3,
            date(2025, 1, 1),
            "https://www.mcxindia.com/docs/default-source/products/contract-specification/gold-guinea/gold-guinea-january-2025-contract-onwards8992f3f6-d244-425a-9a53-66d94500bb34.pdf",
        ),
        ContractSpec(
            "GOLDGUINEA", Decimal("8"), Decimal("8"), Decimal("0.999"),
            "last calendar day, or preceding working day", 3,
            date(2025, 12, 1),
            "https://www.mcxindia.com/docs/default-source/products/contract-specification/gold-guinea/gold-guinea-december-2025-contract-onwardsdc22554857fb64e3bdfdff00007acb35.pdf",
        ),
        ContractSpec(
            "GOLDGUINEA", Decimal("8"), Decimal("8"), Decimal("0.999"),
            "last calendar day, or preceding working day", 3,
            date(2026, 7, 1),
            "https://www.mcxindia.com/docs/default-source/about-us/gold-guinea-july-2026-contract-onwards.pdf",
        ),
    ),
    "GOLDPETAL": (
        ContractSpec(
            "GOLDPETAL", Decimal("1"), Decimal("1"), Decimal("0.999"),
            "last calendar day, or preceding working day", 3,
            date(2025, 4, 1),
            "https://www.mcxindia.com/docs/default-source/products/contract-specification/gold-petal/gold-petal-april-2025-contracts-onwards4b958087-3b38-44b0-abc2-30acd903c1ad.pdf",
        ),
        ContractSpec(
            "GOLDPETAL", Decimal("1"), Decimal("1"), Decimal("0.999"),
            "last calendar day, or preceding working day", 3,
            date(2025, 12, 1),
            "https://www.mcxindia.com/docs/default-source/products/contract-specification/gold-petal/gold-petal-december-2025-contracts-onwards7a08564857fb64e3bdfdff00007acb35.pdf",
        ),
        ContractSpec(
            "GOLDPETAL", Decimal("1"), Decimal("1"), Decimal("0.999"),
            "last calendar day, or preceding working day", 3,
            date(2026, 7, 1),
            "https://www.mcxindia.com/docs/default-source/about-us/gold-petal-july-2026-contract-onwards.pdf",
        ),
    ),
}

# Compatibility view: latest known specification for each symbol.
CONTRACTS = {symbol: versions[-1] for symbol, versions in CONTRACT_SPECS.items()}


def contract_spec(symbol: str, expiry_date: date) -> ContractSpec:
    symbol = symbol.strip().upper()
    versions = CONTRACT_SPECS.get(symbol)
    if not versions:
        raise DataQualityError(f"Unsupported symbol: {symbol!r}")
    applicable = [item for item in versions if item.effective_expiry_from <= expiry_date]
    if not applicable:
        raise DataQualityError(
            f"No verified {symbol} specification applies to expiry {expiry_date.isoformat()}"
        )
    return max(applicable, key=lambda item: item.effective_expiry_from)


@dataclass(frozen=True, order=True)
class ContractKey:
    trading_date: date
    symbol: str
    expiry_date: date


@dataclass(frozen=True)
class Observation:
    trading_date: date
    expiry_date: date
    symbol: str
    instrument_name: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    previous_close: Decimal | None
    volume: int
    open_interest: int
    fine_gold_price: Decimal
    lot_notional: Decimal
    specification_effective_from: date

    @property
    def key(self) -> ContractKey:
        return ContractKey(self.trading_date, self.symbol, self.expiry_date)

    @property
    def days_to_expiry(self) -> int:
        return (self.expiry_date - self.trading_date).days


@dataclass(frozen=True)
class ValidationIssue:
    row_number: int
    code: str
    message: str


@dataclass(frozen=True)
class IngestionResult:
    observations: tuple[Observation, ...]
    issues: tuple[ValidationIssue, ...]
    rows_seen: int
    rows_ignored: int

    @property
    def valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class BacktestResult:
    gross_bps: float
    cost_bps: float
    net_bps: float
    trades: int
    max_drawdown_bps: float


def _column_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.strip().lower())


def _first(row: Mapping[str, str], *keys: str, required: bool = True) -> str | None:
    normalized = {_column_key(key): value for key, value in row.items() if key is not None}
    for key in keys:
        value = normalized.get(_column_key(key))
        if value not in (None, ""):
            return str(value).strip()
    if required:
        raise DataQualityError(f"Missing required column; expected one of {keys}")
    return None


def parse_response_date(value: str) -> date:
    """Parse the MCX date-wise response date (normally MM/DD/YYYY)."""
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
    try:
        requested = datetime.strptime(requested_ddmmyyyy, "%d/%m/%Y").date()
    except ValueError as exc:
        raise DataQualityError(f"Unsupported requested date: {requested_ddmmyyyy!r}") from exc
    if requested != returned:
        raise DataQualityError(
            f"MCX returned {returned.isoformat()} for requested {requested.isoformat()}; "
            "refusing a potentially stale fallback response"
        )


def _decimal(value: str, field: str) -> Decimal:
    try:
        result = Decimal(value.replace(",", "").strip())
    except (InvalidOperation, AttributeError) as exc:
        raise DataQualityError(f"{field} is not numeric: {value!r}") from exc
    if not result.is_finite():
        raise DataQualityError(f"{field} must be finite")
    return result


def _whole_number(value: str, field: str) -> int:
    number = _decimal(value, field)
    if number != number.to_integral_value():
        raise DataQualityError(f"{field} must be a whole number, got {value!r}")
    return int(number)


def normalize_row(row: Mapping[str, str], requested_date: str | None = None) -> Observation:
    symbol_value = _first(row, "Symbol", "Commodity")
    assert symbol_value is not None
    symbol = symbol_value.strip().upper()
    instrument_value = _first(row, "InstrumentName", "Instrument Name", "Instrument")
    assert instrument_value is not None
    instrument_name = instrument_value.strip().upper()
    if instrument_name != "FUTCOM":
        raise DataQualityError(
            f"Unsupported instrument {instrument_name!r}; only FUTCOM futures are accepted"
        )

    date_value = _first(row, "Date")
    expiry_value = _first(row, "ExpiryDate", "Expiry Date")
    assert date_value is not None and expiry_value is not None
    trading_date = parse_response_date(date_value)
    if requested_date:
        validate_requested_date(requested_date, trading_date)
    expiry_date = parse_expiry(expiry_value)
    if expiry_date < trading_date:
        raise DataQualityError("ExpiryDate precedes the trading Date")
    spec = contract_spec(symbol, expiry_date)

    close_value = _first(row, "Close")
    open_value = _first(row, "Open")
    high_value = _first(row, "High")
    low_value = _first(row, "Low")
    volume_value = _first(row, "Volume", "Vol(Lots)", "Vol (Lots)")
    oi_value = _first(row, "OpenInterest", "OI(Lots)", "OI (Lots)")
    assert all(value is not None for value in (close_value, open_value, high_value, low_value, volume_value, oi_value))
    close = _decimal(close_value, "Close")
    opening = _decimal(open_value, "Open")
    high = _decimal(high_value, "High")
    low = _decimal(low_value, "Low")
    volume = _whole_number(volume_value, "Volume")
    open_interest = _whole_number(oi_value, "OpenInterest")
    previous_value = _first(row, "PreviousClose", "Previous Close", "PCP", required=False)
    previous_close = _decimal(previous_value, "PreviousClose") if previous_value is not None else None

    if min(opening, high, low, close) <= 0:
        raise DataQualityError("OHLC prices must be positive")
    if low > high or not low <= opening <= high or not low <= close <= high:
        raise DataQualityError("OHLC values are internally inconsistent")
    if previous_close is not None and previous_close <= 0:
        raise DataQualityError("PreviousClose must be positive")
    if volume < 0 or open_interest < 0:
        raise DataQualityError("Volume and OpenInterest cannot be negative")

    fine_gold_price = close / spec.quoted_grams / spec.purity
    lot_notional = close * spec.trading_unit_grams / spec.quoted_grams
    return Observation(
        trading_date=trading_date,
        expiry_date=expiry_date,
        symbol=symbol,
        instrument_name=instrument_name,
        open=opening,
        high=high,
        low=low,
        close=close,
        previous_close=previous_close,
        volume=volume,
        open_interest=open_interest,
        fine_gold_price=fine_gold_price,
        lot_notional=lot_notional,
        specification_effective_from=spec.effective_expiry_from,
    )


def ingest_csv(path: str | Path, requested_date: str | None = None) -> IngestionResult:
    """Validate an official MCX CSV export without silently dropping bad rows."""
    observations: list[Observation] = []
    issues: list[ValidationIssue] = []
    seen: dict[ContractKey, Observation] = {}
    rows_seen = 0
    rows_ignored = 0
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise DataQualityError("CSV has no header row")
        for row_number, row in enumerate(reader, start=2):
            rows_seen += 1
            raw_symbol = (_first(row, "Symbol", "Commodity", required=False) or "").strip().upper()
            if raw_symbol not in CONTRACT_SPECS:
                rows_ignored += 1
                continue
            try:
                item = normalize_row(row, requested_date=requested_date)
                if item.key in seen:
                    previous = seen[item.key]
                    code = "duplicate_identical" if previous == item else "duplicate_conflict"
                    raise DataQualityError(f"Duplicate contract key {item.key} ({code})")
                seen[item.key] = item
                observations.append(item)
            except DataQualityError as exc:
                issues.append(ValidationIssue(row_number, "invalid_row", str(exc)))
    observations.sort(key=lambda item: item.key)
    return IngestionResult(tuple(observations), tuple(issues), rows_seen, rows_ignored)


def load_csv(path: str | Path, requested_date: str | None = None) -> list[Observation]:
    """Strict compatibility loader; raise if any targeted row fails validation."""
    result = ingest_csv(path, requested_date=requested_date)
    if result.issues:
        details = "; ".join(f"row {issue.row_number}: {issue.message}" for issue in result.issues)
        raise DataQualityError(details)
    return list(result.observations)


def spread_bps(candidate: Observation, reference: Observation) -> float:
    if candidate.trading_date != reference.trading_date:
        raise DataQualityError("Spread legs must share a trading date")
    return float((candidate.fine_gold_price / reference.fine_gold_price - Decimal("1")) * Decimal("10000"))


def walk_forward_zscores(values: Sequence[float], window: int = 40) -> list[float | None]:
    """Score value t using values [t-window, t), never value t itself."""
    if window < 2:
        raise ValueError("window must be at least 2")
    scores: list[float | None] = []
    for index, value in enumerate(values):
        if not math.isfinite(value):
            raise ValueError("values must be finite; missing observations cannot be imputed")
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
    """Legacy spread-unit test harness with next-session execution.

    Production research uses contract-price P&L. This helper remains for
    regression tests and charges the terminal close before final drawdown.
    """
    if len(spreads) != len(scores):
        raise ValueError("spreads and scores must have equal length")
    gates = list(eligible) if eligible is not None else [True] * len(spreads)
    if len(gates) != len(spreads):
        raise ValueError("eligible must have equal length")
    if cost_per_position_change_bps < 0:
        raise ValueError("cost cannot be negative")
    position = 0
    gross = 0.0
    costs = 0.0
    trades = 0
    peak = 0.0
    max_drawdown = 0.0
    for index in range(1, len(spreads)):
        gross += position * (spreads[index] - spreads[index - 1])
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
        equity = gross - costs
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)
    if position:
        costs += abs(position) * cost_per_position_change_bps
        equity = gross - costs
        max_drawdown = min(max_drawdown, equity - peak)
    return BacktestResult(gross, costs, gross - costs, trades, abs(max_drawdown))


def pair_by_contract(
    observations: Iterable[Observation],
    candidate: str,
    candidate_expiry: date,
    reference: str,
    reference_expiry: date,
) -> list[tuple[Observation, Observation]]:
    """Pair two explicitly identified expiries on common trading dates."""
    by_key = {item.key: item for item in observations}
    dates = sorted({item.trading_date for item in observations})
    return [
        (
            by_key[ContractKey(day, candidate, candidate_expiry)],
            by_key[ContractKey(day, reference, reference_expiry)],
        )
        for day in dates
        if ContractKey(day, candidate, candidate_expiry) in by_key
        and ContractKey(day, reference, reference_expiry) in by_key
    ]


def pair_by_date(
    observations: Iterable[Observation], candidate: str, reference: str
) -> list[tuple[Observation, Observation]]:
    """Pair symbols only when each has exactly one expiry in the dataset."""
    items = list(observations)
    candidate_expiries = {item.expiry_date for item in items if item.symbol == candidate}
    reference_expiries = {item.expiry_date for item in items if item.symbol == reference}
    if len(candidate_expiries) != 1 or len(reference_expiries) != 1:
        raise AmbiguousContractError(
            "Explicit candidate and reference expiries are required when a symbol has zero or multiple expiries"
        )
    return pair_by_contract(
        items, candidate, next(iter(candidate_expiries)), reference, next(iter(reference_expiries))
    )


def missing_expected_sessions(
    observations: Iterable[Observation], expected_sessions: Sequence[date]
) -> tuple[date, ...]:
    """Report absent sessions; callers supply an exchange calendar explicitly."""
    observed = {item.trading_date for item in observations}
    return tuple(day for day in expected_sessions if day not in observed)
