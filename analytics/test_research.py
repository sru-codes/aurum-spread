import unittest
from datetime import date, timedelta

from aurum_spread import normalize_row
from research import (
    CostModel,
    ResearchConfig,
    build_research_snapshot,
    build_spread_series,
    cost_sensitivity,
    integer_hedge_ratio,
    simulate_contracts,
)


class ResearchTests(unittest.TestCase):
    def observation(self, day: date, symbol: str, expiry: date, close: float, volume: int = 100, oi: int = 500):
        close_text = f"{close:.2f}"
        return normalize_row({
            "Date": day.strftime("%m/%d/%Y"),
            "Instrument Name": "FUTCOM",
            "Symbol": symbol,
            "Expiry Date": expiry.strftime("%d%b%Y").upper(),
            "Open": close_text,
            "High": close_text,
            "Low": close_text,
            "Close": close_text,
            "Previous Close": close_text,
            "Vol (Lots)": str(volume),
            "OI (Lots)": str(oi),
        })

    def series(self, count: int = 30, shock_index: int | None = None, zero_volume_index: int | None = None):
        start = date(2026, 8, 3)
        candidate_expiry = date(2026, 10, 30)
        reference_expiry = date(2026, 11, 5)
        observations = []
        for index in range(count):
            day = start + timedelta(days=index)
            baseline = 100_000 + index * 50
            # Small alternating basis noise gives the trailing estimator a
            # non-zero variance. The unusual point is large enough to cross
            # the z gate without being an artificial one-day market shock.
            basis_offset = 20 if index % 2 else -20
            shock = 80 if index == shock_index else basis_offset
            volume = 0 if index == zero_volume_index else 100
            observations.extend([
                self.observation(day, "GOLDTEN", candidate_expiry, baseline + shock, volume),
                self.observation(day, "GOLDM", reference_expiry, baseline, volume),
            ])
        return observations, candidate_expiry, reference_expiry

    def config(self):
        return ResearchConfig(
            lookback_sessions=5,
            minimum_training_sessions=5,
            entry_z=2,
            exit_z=0.5,
            minimum_volume_lots=10,
            minimum_open_interest_lots=50,
            minimum_days_to_expiry=7,
            maximum_expiry_gap_days=45,
            annual_carry_bps=500,
        )

    def test_carry_is_separated_from_residual_and_partitions_are_chronological(self) -> None:
        observations, candidate_expiry, reference_expiry = self.series()
        points = build_spread_series(
            observations, "GOLDTEN", candidate_expiry, "GOLDM", reference_expiry, self.config()
        )
        self.assertAlmostEqual(points[0].expiry_carry_bps, 500 * -6 / 365)
        self.assertAlmostEqual(points[0].residual_spread_bps, points[0].raw_spread_bps - points[0].expiry_carry_bps)
        labels = [point.partition for point in points]
        self.assertEqual(labels[:18], ["train"] * 18)
        self.assertEqual(labels[18:24], ["validation"] * 6)
        self.assertEqual(labels[24:], ["test"] * 6)

    def test_walk_forward_signal_does_not_use_current_shock(self) -> None:
        observations, candidate_expiry, reference_expiry = self.series(shock_index=8)
        points = build_spread_series(
            observations, "GOLDTEN", candidate_expiry, "GOLDM", reference_expiry, self.config()
        )
        self.assertGreater(points[8].zscore or 0, 2)
        self.assertLess(points[8].trailing_mean_bps or 0, points[8].residual_spread_bps)

    def test_liquidity_and_lifecycle_gates_withhold_signal(self) -> None:
        observations, candidate_expiry, reference_expiry = self.series(zero_volume_index=8)
        points = build_spread_series(
            observations, "GOLDTEN", candidate_expiry, "GOLDM", reference_expiry, self.config()
        )
        self.assertEqual(points[8].liquidity_state, "no-volume")
        self.assertFalse(points[8].eligible)
        self.assertEqual(points[8].verdict, "NO_SIGNAL")

    def test_integer_lots_preserve_and_report_residual_gold_exposure(self) -> None:
        ratio = integer_hedge_ratio("GOLDTEN", "GOLDM", date(2026, 10, 30))
        self.assertEqual(ratio.candidate_lots, 10)
        self.assertEqual(ratio.reference_lots, 1)
        self.assertNotEqual(ratio.net_fine_gold_grams, 0)

    def test_simulation_uses_actual_prices_and_cost_attribution(self) -> None:
        observations, candidate_expiry, reference_expiry = self.series(shock_index=8)
        config = self.config()
        points = build_spread_series(
            observations, "GOLDTEN", candidate_expiry, "GOLDM", reference_expiry, config
        )
        costs = CostModel(0.5, 0.35, 2.0, 800)
        result = simulate_contracts(points, config, costs)
        self.assertGreaterEqual(result.trades, 1)
        self.assertGreater(result.brokerage_inr, 0)
        self.assertGreater(result.fees_inr, 0)
        self.assertGreater(result.slippage_inr, 0)
        self.assertGreaterEqual(result.funding_inr, 0)
        self.assertAlmostEqual(
            result.gross_pnl_inr,
            result.relative_convergence_pnl_inr + result.gold_exposure_pnl_inr + result.unexplained_residual_pnl_inr,
            places=7,
        )

    def test_cost_sensitivity_and_snapshot_are_deterministic(self) -> None:
        observations, candidate_expiry, reference_expiry = self.series(shock_index=8)
        config = self.config()
        points = build_spread_series(
            observations, "GOLDTEN", candidate_expiry, "GOLDM", reference_expiry, config
        )
        costs = CostModel()
        simulation = simulate_contracts(points, config, costs)
        sensitivity = cost_sensitivity(points, config, costs, [1, 2, 5])
        self.assertGreaterEqual(sensitivity[0]["net_pnl_inr"], sensitivity[-1]["net_pnl_inr"])
        first = build_research_snapshot(points, simulation, config, costs, {"raw_sha256": "abc"}, sensitivity)
        second = build_research_snapshot(points, simulation, config, costs, {"raw_sha256": "abc"}, sensitivity)
        self.assertEqual(first["content_sha256"], second["content_sha256"])

    def test_insufficient_history_never_forces_a_signal(self) -> None:
        observations, candidate_expiry, reference_expiry = self.series(count=4, shock_index=3)
        points = build_spread_series(
            observations, "GOLDTEN", candidate_expiry, "GOLDM", reference_expiry, self.config()
        )
        self.assertTrue(all(point.zscore is None for point in points))
        self.assertTrue(all(point.verdict == "NO_SIGNAL" for point in points))

    def test_end_of_contract_observations_are_ineligible(self) -> None:
        start = date(2026, 10, 25)
        candidate_expiry = date(2026, 10, 30)
        reference_expiry = date(2026, 11, 5)
        observations = []
        for index in range(5):
            day = start + timedelta(days=index)
            observations.extend([
                self.observation(day, "GOLDTEN", candidate_expiry, 100_000 + index),
                self.observation(day, "GOLDM", reference_expiry, 100_000 + index),
            ])
        config = ResearchConfig(
            lookback_sessions=2,
            minimum_training_sessions=2,
            minimum_days_to_expiry=7,
        )
        points = build_spread_series(
            observations, "GOLDTEN", candidate_expiry, "GOLDM", reference_expiry, config
        )
        self.assertTrue(all(not point.eligible for point in points))
        self.assertTrue(all(point.verdict == "NO_SIGNAL" for point in points))


if __name__ == "__main__":
    unittest.main()
