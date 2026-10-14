"""Walk-forward spread research with contract-price P&L attribution."""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Sequence

from aurum_spread import Observation, contract_spec, pair_by_contract, spread_bps
from pipeline import ENGINE_VERSION, SCHEMA_VERSION, canonical_json, sha256_bytes


@dataclass(frozen=True)
class ResearchConfig:
    lookback_sessions: int = 40
    minimum_training_sessions: int = 40
    entry_z: float = 2.0
    exit_z: float = 0.5
    minimum_volume_lots: int = 10
    minimum_open_interest_lots: int = 50
    minimum_days_to_expiry: int = 7
    maximum_expiry_gap_days: int = 45
    annual_carry_bps: float = 0.0
    train_fraction: float = 0.60
    validation_fraction: float = 0.20

    def validate(self) -> None:
        if self.lookback_sessions < 2:
            raise ValueError("lookback_sessions must be at least 2")
        if self.minimum_training_sessions < 2:
            raise ValueError("minimum_training_sessions must be at least 2")
        if self.minimum_training_sessions > self.lookback_sessions:
            raise ValueError("minimum_training_sessions cannot exceed lookback_sessions")
        if self.entry_z <= self.exit_z or self.exit_z < 0:
            raise ValueError("require entry_z > exit_z >= 0")
        if min(self.minimum_volume_lots, self.minimum_open_interest_lots) < 0:
            raise ValueError("liquidity thresholds cannot be negative")
        if self.minimum_days_to_expiry < 0 or self.maximum_expiry_gap_days < 0:
            raise ValueError("expiry thresholds cannot be negative")
        if not 0 < self.train_fraction < 1 or not 0 < self.validation_fraction < 1:
            raise ValueError("partition fractions must be between zero and one")
        if self.train_fraction + self.validation_fraction >= 1:
            raise ValueError("train and validation fractions must leave an untouched test partition")


@dataclass(frozen=True)
class CostModel:
    brokerage_bps: float = 0.5
    exchange_and_regulatory_fees_bps: float = 0.35
    slippage_bps: float = 2.0
    annual_funding_bps: float = 800.0

    def validate(self) -> None:
        if min(asdict(self).values()) < 0:
            raise ValueError("cost assumptions cannot be negative")


@dataclass(frozen=True)
class GateResult:
    name: str
    passed: bool
    observed: str
    threshold: str


@dataclass(frozen=True)
class SpreadPoint:
    trading_date: date
    candidate: Observation
    reference: Observation
    raw_spread_bps: float
    expiry_carry_bps: float
    residual_spread_bps: float
    zscore: float | None
    trailing_mean_bps: float | None
    trailing_stdev_bps: float | None
    liquidity_state: str
    market_state: str
    gates: tuple[GateResult, ...]
    eligible: bool
    verdict: str
    partition: str


@dataclass(frozen=True)
class HedgeRatio:
    candidate_lots: int
    reference_lots: int
    candidate_fine_grams: Decimal
    reference_fine_grams: Decimal
    net_fine_gold_grams: Decimal


@dataclass(frozen=True)
class DailyAttribution:
    trading_date: date
    position: int
    gross_pnl_inr: float
    relative_convergence_pnl_inr: float
    gold_exposure_pnl_inr: float
    unexplained_residual_pnl_inr: float
    brokerage_inr: float
    fees_inr: float
    slippage_inr: float
    funding_inr: float
    net_pnl_inr: float
    action: str


@dataclass(frozen=True)
class SimulationResult:
    hedge_ratio: HedgeRatio
    daily: tuple[DailyAttribution, ...]
    trades: int
    gross_pnl_inr: float
    relative_convergence_pnl_inr: float
    gold_exposure_pnl_inr: float
    unexplained_residual_pnl_inr: float
    brokerage_inr: float
    fees_inr: float
    slippage_inr: float
    funding_inr: float
    net_pnl_inr: float
    max_drawdown_inr: float


def _partition_labels(length: int, train_fraction: float, validation_fraction: float) -> list[str]:
    train_end = math.floor(length * train_fraction)
    validation_end = train_end + math.floor(length * validation_fraction)
    return [
        "train" if index < train_end else "validation" if index < validation_end else "test"
        for index in range(length)
    ]


def _trailing_stats(values: Sequence[float], index: int, window: int, minimum: int) -> tuple[float | None, float | None, float | None]:
    start = max(0, index - window)
    training = values[start:index]
    if len(training) < minimum:
        return None, None, None
    mean = statistics.mean(training)
    deviation = statistics.stdev(training)
    # A zero-variance history does not define a z-score. Failing closed is
    # safer than turning any later movement into an arbitrary forced signal.
    score = None if math.isclose(deviation, 0.0) else (values[index] - mean) / deviation
    return mean, deviation, score


def _liquidity_state(pairs: Sequence[tuple[Observation, Observation]], index: int, window: int) -> str:
    candidate, reference = pairs[index]
    current = min(candidate.volume, reference.volume)
    prior = [min(left.volume, right.volume) for left, right in pairs[max(0, index - window):index]]
    if current == 0:
        return "no-volume"
    if len(prior) < 5:
        return "unclassified"
    median = statistics.median(prior)
    if median == 0:
        return "recovering" if current > 0 else "no-volume"
    ratio = current / median
    if ratio < 0.25:
        return "thin"
    if ratio > 2.0:
        return "active"
    return "normal"


def _market_state(values: Sequence[float], index: int, window: int) -> str:
    start = max(1, index - window)
    prior_changes = [values[i] - values[i - 1] for i in range(start, index)]
    if len(prior_changes) < 5 or index == 0:
        return "unclassified"
    volatility = statistics.stdev(prior_changes)
    latest_change = abs(values[index] - values[index - 1])
    if math.isclose(volatility, 0.0):
        return "stable"
    if latest_change > 3 * volatility:
        return "shock"
    if latest_change > 1.5 * volatility:
        return "volatile"
    return "stable"


def build_spread_series(
    observations: Iterable[Observation],
    candidate_symbol: str,
    candidate_expiry: date,
    reference_symbol: str,
    reference_expiry: date,
    config: ResearchConfig,
) -> list[SpreadPoint]:
    """Create an expiry-specific series using trailing-only classifications."""
    config.validate()
    pairs = pair_by_contract(
        observations, candidate_symbol, candidate_expiry, reference_symbol, reference_expiry
    )
    raw = [spread_bps(candidate, reference) for candidate, reference in pairs]
    expiry_gap_days = (candidate_expiry - reference_expiry).days
    carry = config.annual_carry_bps * expiry_gap_days / 365.0
    residuals = [value - carry for value in raw]
    partitions = _partition_labels(len(pairs), config.train_fraction, config.validation_fraction)
    points: list[SpreadPoint] = []
    for index, (candidate, reference) in enumerate(pairs):
        mean, deviation, score = _trailing_stats(
            residuals, index, config.lookback_sessions, config.minimum_training_sessions
        )
        liquidity_state = _liquidity_state(pairs, index, config.lookback_sessions)
        market_state = _market_state(residuals, index, config.lookback_sessions)
        minimum_dte = min(candidate.days_to_expiry, reference.days_to_expiry)
        gates = (
            GateResult(
                "training_history",
                score is not None,
                str(min(index, config.lookback_sessions)),
                f">={config.minimum_training_sessions} prior sessions",
            ),
            GateResult(
                "volume",
                min(candidate.volume, reference.volume) >= config.minimum_volume_lots,
                str(min(candidate.volume, reference.volume)),
                f">={config.minimum_volume_lots} lots on both legs",
            ),
            GateResult(
                "open_interest",
                min(candidate.open_interest, reference.open_interest) >= config.minimum_open_interest_lots,
                str(min(candidate.open_interest, reference.open_interest)),
                f">={config.minimum_open_interest_lots} lots on both legs",
            ),
            GateResult(
                "contract_lifecycle",
                minimum_dte > config.minimum_days_to_expiry,
                f"{minimum_dte} calendar days",
                f">{config.minimum_days_to_expiry}; avoids delivery window",
            ),
            GateResult(
                "expiry_alignment",
                abs(expiry_gap_days) <= config.maximum_expiry_gap_days,
                f"{abs(expiry_gap_days)} calendar days",
                f"<={config.maximum_expiry_gap_days}",
            ),
            GateResult(
                "market_state",
                market_state != "shock",
                market_state,
                "not shock",
            ),
        )
        eligible = all(gate.passed for gate in gates)
        if not eligible or score is None or abs(score) < config.entry_z:
            verdict = "NO_SIGNAL"
        elif score > 0:
            verdict = "SHORT_CANDIDATE_LONG_REFERENCE"
        else:
            verdict = "LONG_CANDIDATE_SHORT_REFERENCE"
        points.append(
            SpreadPoint(
                trading_date=candidate.trading_date,
                candidate=candidate,
                reference=reference,
                raw_spread_bps=raw[index],
                expiry_carry_bps=carry,
                residual_spread_bps=residuals[index],
                zscore=score,
                trailing_mean_bps=mean,
                trailing_stdev_bps=deviation,
                liquidity_state=liquidity_state,
                market_state=market_state,
                gates=gates,
                eligible=eligible,
                verdict=verdict,
                partition=partitions[index],
            )
        )
    return points


def integer_hedge_ratio(
    candidate_symbol: str,
    reference_symbol: str,
    candidate_expiry: date,
    reference_expiry: date | None = None,
) -> HedgeRatio:
    """Choose practical integer lots by setting one lot of the larger contract."""
    candidate_spec = contract_spec(candidate_symbol, candidate_expiry)
    reference_spec = contract_spec(reference_symbol, reference_expiry or candidate_expiry)
    candidate_fine = candidate_spec.trading_unit_grams * candidate_spec.purity
    reference_fine = reference_spec.trading_unit_grams * reference_spec.purity
    if candidate_fine <= reference_fine:
        reference_lots = 1
        candidate_lots = max(1, round(reference_fine / candidate_fine))
    else:
        candidate_lots = 1
        reference_lots = max(1, round(candidate_fine / reference_fine))
    candidate_total = candidate_fine * candidate_lots
    reference_total = reference_fine * reference_lots
    return HedgeRatio(
        candidate_lots,
        reference_lots,
        candidate_total,
        reference_total,
        candidate_total - reference_total,
    )


def _leg_notional(point: SpreadPoint, ratio: HedgeRatio) -> float:
    return float(
        point.candidate.lot_notional * ratio.candidate_lots
        + point.reference.lot_notional * ratio.reference_lots
    )


def simulate_contracts(
    points: Sequence[SpreadPoint], config: ResearchConfig, costs: CostModel
) -> SimulationResult:
    """Simulate next-session decisions using actual contract closes and sizes."""
    config.validate()
    costs.validate()
    if not points:
        raise ValueError("at least one spread point is required")
    ratio = integer_hedge_ratio(
        points[0].candidate.symbol,
        points[0].reference.symbol,
        points[0].candidate.expiry_date,
        points[0].reference.expiry_date,
    )
    position = 0
    trades = 0
    totals = {key: 0.0 for key in (
        "gross", "relative", "gold", "residual", "brokerage", "fees", "slippage", "funding"
    )}
    equity = peak = 0.0
    max_drawdown = 0.0
    daily: list[DailyAttribution] = []
    for index in range(1, len(points)):
        previous = points[index - 1]
        current = points[index]
        candidate_change = current.candidate.fine_gold_price - previous.candidate.fine_gold_price
        reference_change = current.reference.fine_gold_price - previous.reference.fine_gold_price
        candidate_pnl = Decimal(position) * ratio.candidate_fine_grams * candidate_change
        reference_pnl = -Decimal(position) * ratio.reference_fine_grams * reference_change
        gross = float(candidate_pnl + reference_pnl)
        relative = float(Decimal(position) * ratio.candidate_fine_grams * (candidate_change - reference_change))
        gold = float(Decimal(position) * ratio.net_fine_gold_grams * reference_change)
        residual = gross - relative - gold
        totals["gross"] += gross
        totals["relative"] += relative
        totals["gold"] += gold
        totals["residual"] += residual

        funding = 0.0
        if position:
            elapsed_days = max(1, (current.trading_date - previous.trading_date).days)
            funding = _leg_notional(previous, ratio) * costs.annual_funding_bps / 10_000 * elapsed_days / 365
            totals["funding"] += funding

        prior_score = previous.zscore
        target = position
        if not previous.eligible or prior_score is None:
            target = 0
        elif position == 0 and prior_score >= config.entry_z:
            target = -1
        elif position == 0 and prior_score <= -config.entry_z:
            target = 1
        elif position != 0 and abs(prior_score) <= config.exit_z:
            target = 0
        action = "HOLD"
        brokerage = fees = slippage = 0.0
        if target != position:
            turnover = _leg_notional(current, ratio) * abs(target - position)
            brokerage = turnover * costs.brokerage_bps / 10_000
            fees = turnover * costs.exchange_and_regulatory_fees_bps / 10_000
            slippage = turnover * costs.slippage_bps / 10_000
            totals["brokerage"] += brokerage
            totals["fees"] += fees
            totals["slippage"] += slippage
            if position == 0 and target:
                trades += 1
                action = "ENTER_LONG_SPREAD" if target > 0 else "ENTER_SHORT_SPREAD"
            elif target == 0:
                action = "EXIT"
            else:
                action = "REVERSE"
            position = target
        day_cost = brokerage + fees + slippage + funding
        net = gross - day_cost
        equity += net
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        daily.append(
            DailyAttribution(
                current.trading_date, position, gross, relative, gold, residual,
                brokerage, fees, slippage, funding, net, action,
            )
        )

    if position:
        last = points[-1]
        turnover = _leg_notional(last, ratio) * abs(position)
        brokerage = turnover * costs.brokerage_bps / 10_000
        fees = turnover * costs.exchange_and_regulatory_fees_bps / 10_000
        slippage = turnover * costs.slippage_bps / 10_000
        totals["brokerage"] += brokerage
        totals["fees"] += fees
        totals["slippage"] += slippage
        terminal_cost = brokerage + fees + slippage
        equity -= terminal_cost
        max_drawdown = max(max_drawdown, peak - equity)
        if daily:
            last_day = daily[-1]
            daily[-1] = DailyAttribution(
                last_day.trading_date, 0, last_day.gross_pnl_inr,
                last_day.relative_convergence_pnl_inr, last_day.gold_exposure_pnl_inr,
                last_day.unexplained_residual_pnl_inr,
                last_day.brokerage_inr + brokerage, last_day.fees_inr + fees,
                last_day.slippage_inr + slippage, last_day.funding_inr,
                last_day.net_pnl_inr - terminal_cost,
                "FORCED_EXIT_END_OF_SAMPLE",
            )

    total_cost = totals["brokerage"] + totals["fees"] + totals["slippage"] + totals["funding"]
    return SimulationResult(
        ratio, tuple(daily), trades, totals["gross"], totals["relative"], totals["gold"],
        totals["residual"], totals["brokerage"], totals["fees"], totals["slippage"],
        totals["funding"], totals["gross"] - total_cost, max_drawdown,
    )


def cost_sensitivity(
    points: Sequence[SpreadPoint], config: ResearchConfig, base: CostModel,
    slippage_scenarios_bps: Sequence[float],
) -> list[dict[str, float]]:
    results: list[dict[str, float]] = []
    for slippage in slippage_scenarios_bps:
        model = CostModel(
            base.brokerage_bps,
            base.exchange_and_regulatory_fees_bps,
            slippage,
            base.annual_funding_bps,
        )
        result = simulate_contracts(points, config, model)
        results.append({
            "slippage_bps": slippage,
            "gross_pnl_inr": result.gross_pnl_inr,
            "total_cost_inr": result.gross_pnl_inr - result.net_pnl_inr,
            "net_pnl_inr": result.net_pnl_inr,
        })
    return results


def _serializable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {key: _serializable(item) for key, item in asdict(value).items()}
    if isinstance(value, (tuple, list)):
        return [_serializable(item) for item in value]
    if isinstance(value, dict):
        return {key: _serializable(item) for key, item in value.items()}
    return value


def build_research_snapshot(
    points: Sequence[SpreadPoint], simulation: SimulationResult, config: ResearchConfig,
    costs: CostModel, lineage: dict[str, Any], sensitivity: Sequence[dict[str, float]],
) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "mode": "VERIFIED_HISTORICAL",
        "lineage": lineage,
        "configuration": _serializable(config),
        "cost_assumptions": _serializable(costs),
        "methodology": {
            "signal_information_lag": "decision at t uses observations through t; hypothetical fill is close at t+1",
            "missing_observations": "not imputed",
            "fill_assumption": "hypothetical next-session close plus explicit slippage; not a claim of executable depth",
            "settlement_prices": "not treated as executable fills",
            "position_sizing": "integer lots minimizing fine-gold exposure with one lot of the larger contract",
            "model_selection": "configuration fixed before untouched test partition evaluation",
        },
        "series": _serializable(points),
        "simulation": _serializable(simulation),
        "cost_sensitivity": _serializable(sensitivity),
    }
    snapshot["content_sha256"] = sha256_bytes(canonical_json(snapshot).encode("utf-8"))
    return snapshot


def write_research_snapshot(path: str | Path, snapshot: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
