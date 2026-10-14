import csv
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from aurum_spread import (
    AmbiguousContractError,
    ContractKey,
    DataQualityError,
    backtest_spread,
    contract_spec,
    ingest_csv,
    missing_expected_sessions,
    normalize_row,
    pair_by_contract,
    pair_by_date,
    spread_bps,
    walk_forward_zscores,
)


class AurumSpreadTests(unittest.TestCase):
    def row(
        self,
        symbol: str = "GOLDTEN",
        close: str = "125506",
        expiry: str | None = None,
        **overrides: str,
    ) -> dict[str, str]:
        expiry = expiry or ("05NOV2026" if symbol == "GOLDM" else "29OCT2026")
        values = {
            "Instrument Name": "FUTCOM",
            "Symbol": f" {symbol} ",
            "Date": "10/14/2026",
            "ExpiryDate": expiry,
            "Open": close,
            "High": close,
            "Low": close,
            "Close": close,
            "Previous Close": close,
            "Vol (Lots)": "1,200",
            "OI (Lots)": "4,500",
        }
        values.update(overrides)
        return values

    def observation(self, symbol: str, expiry: str, close: str = "125000"):
        return normalize_row(self.row(symbol, close, expiry))

    def test_normalizes_price_padded_symbol_and_exact_units(self) -> None:
        item = normalize_row(self.row(), requested_date="14/10/2026")
        self.assertEqual(item.symbol, "GOLDTEN")
        self.assertEqual(item.trading_date, date(2026, 10, 14))
        self.assertEqual(item.fine_gold_price, Decimal("125506") / Decimal("10") / Decimal("0.999"))
        self.assertEqual(item.lot_notional, Decimal("125506"))

    def test_rejects_stale_fallback_date_and_malformed_request(self) -> None:
        with self.assertRaises(DataQualityError):
            normalize_row(self.row(), requested_date="15/10/2026")
        with self.assertRaises(DataQualityError):
            normalize_row(self.row(), requested_date="2026-10-14")

    def test_rejects_malformed_dates(self) -> None:
        with self.assertRaises(DataQualityError):
            normalize_row(self.row(Date="14/10/2026"))
        with self.assertRaises(DataQualityError):
            normalize_row(self.row(ExpiryDate="OCTOBER"))
        with self.assertRaises(DataQualityError):
            normalize_row(self.row(ExpiryDate="01OCT2026"))

    def test_rejects_options_and_non_integral_activity(self) -> None:
        with self.assertRaises(DataQualityError):
            normalize_row(self.row(**{"Instrument Name": "OPTFUT"}))
        with self.assertRaises(DataQualityError):
            normalize_row(self.row(**{"Vol (Lots)": "1.5"}))

    def test_rejects_invalid_ohlc_and_negative_liquidity(self) -> None:
        with self.assertRaises(DataQualityError):
            normalize_row(self.row(Open="126000", High="125900"))
        with self.assertRaises(DataQualityError):
            normalize_row(self.row(**{"OI (Lots)": "-1"}))

    def test_specifications_have_effective_dates_and_goldten_floor(self) -> None:
        current = contract_spec("GOLDM", date(2026, 11, 5))
        self.assertEqual(current.trading_unit_grams, Decimal("100"))
        self.assertEqual(current.quoted_grams, Decimal("10"))
        self.assertEqual(current.purity, Decimal("0.995"))
        with self.assertRaises(DataQualityError):
            contract_spec("GOLDTEN", date(2025, 3, 31))

    def test_spread_is_purity_adjusted(self) -> None:
        mini = normalize_row(self.row("GOLDM", "124862"))
        ten = normalize_row(self.row("GOLDTEN", "125506"))
        expected = ((125506 / 10 / 0.999) / (124862 / 10 / 0.995) - 1) * 10_000
        self.assertAlmostEqual(spread_bps(ten, mini), expected)

    def test_walk_forward_excludes_current_value_and_rejects_missing(self) -> None:
        scores = walk_forward_zscores([0, 1, 2, 3, 100], window=4)
        self.assertIsNone(scores[3])
        self.assertGreater(scores[4], 50)
        with self.assertRaises(ValueError):
            walk_forward_zscores([1, float("nan"), 2], window=2)

    def test_multiple_expiries_never_overwrite_each_other(self) -> None:
        items = [
            self.observation("GOLDTEN", "29OCT2026"),
            self.observation("GOLDTEN", "30NOV2026", "126000"),
            self.observation("GOLDM", "05NOV2026", "124000"),
        ]
        self.assertEqual(len({item.key for item in items}), 3)
        with self.assertRaises(AmbiguousContractError):
            pair_by_date(items, "GOLDTEN", "GOLDM")
        pairs = pair_by_contract(
            items,
            "GOLDTEN",
            date(2026, 10, 29),
            "GOLDM",
            date(2026, 11, 5),
        )
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][0].key, ContractKey(date(2026, 10, 14), "GOLDTEN", date(2026, 10, 29)))

    def test_csv_ingestion_reports_duplicates_instead_of_hiding_them(self) -> None:
        row = self.row()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bhavcopy.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(row))
                writer.writeheader()
                writer.writerow(row)
                writer.writerow(row)
            result = ingest_csv(path, requested_date="14/10/2026")
        self.assertEqual(len(result.observations), 1)
        self.assertEqual(len(result.issues), 1)
        self.assertIn("duplicate_identical", result.issues[0].message)

    def test_missing_sessions_are_reported_not_filled(self) -> None:
        items = [self.observation("GOLDTEN", "29OCT2026")]
        missing = missing_expected_sessions(items, [date(2026, 10, 13), date(2026, 10, 14)])
        self.assertEqual(missing, (date(2026, 10, 13),))

    def test_backtest_applies_signal_next_session_and_closes_at_end(self) -> None:
        spreads = [0, 1, 10, 8, 4, 1]
        scores = [None, 0.2, 2.5, 1.5, 0.4, 0.1]
        result = backtest_spread(spreads, scores, cost_per_position_change_bps=1)
        self.assertEqual(result.trades, 1)
        self.assertEqual(result.cost_bps, 2)
        self.assertGreater(result.net_bps, 0)
        self.assertGreaterEqual(result.max_drawdown_bps, 0)

    def test_zero_liquidity_is_preserved_for_later_eligibility_gates(self) -> None:
        item = normalize_row(self.row(**{"Vol (Lots)": "0", "OI (Lots)": "0"}))
        self.assertEqual(item.volume, 0)
        self.assertEqual(item.open_interest, 0)


if __name__ == "__main__":
    unittest.main()
