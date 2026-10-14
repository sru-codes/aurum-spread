import unittest
from datetime import date

from aurum_spread import (
    DataQualityError,
    backtest_spread,
    normalize_row,
    spread_bps,
    walk_forward_zscores,
)


class AurumSpreadTests(unittest.TestCase):
    def row(self, symbol: str, close: str) -> dict[str, str]:
        return {
            "Symbol": f" {symbol} ",
            "Date": "10/14/2026",
            "ExpiryDate": "29OCT2026" if symbol != "GOLDM" else "05NOV2026",
            "Close": close,
            "Volume": "1,200",
            "OpenInterest": "4,500",
        }

    def test_normalizes_price_and_padded_symbol(self) -> None:
        item = normalize_row(self.row("GOLDTEN", "125506"), requested_date="14/10/2026")
        self.assertEqual(item.symbol, "GOLDTEN")
        self.assertEqual(item.trading_date, date(2026, 10, 14))
        self.assertAlmostEqual(item.fine_gold_price, 125506 / 10 / 0.999)

    def test_rejects_stale_fallback_date(self) -> None:
        with self.assertRaises(DataQualityError):
            normalize_row(self.row("GOLDTEN", "125506"), requested_date="15/10/2026")

    def test_spread_is_purity_adjusted(self) -> None:
        mini = normalize_row(self.row("GOLDM", "124862"))
        ten = normalize_row(self.row("GOLDTEN", "125506"))
        expected = ((125506 / 10 / 0.999) / (124862 / 10 / 0.995) - 1) * 10_000
        self.assertAlmostEqual(spread_bps(ten, mini), expected)

    def test_walk_forward_excludes_current_value(self) -> None:
        scores = walk_forward_zscores([0, 1, 2, 3, 100], window=4)
        self.assertIsNone(scores[3])
        self.assertGreater(scores[4], 50)

    def test_backtest_applies_signal_on_next_session(self) -> None:
        spreads = [0, 1, 10, 8, 4, 1]
        scores = [None, 0.2, 2.5, 1.5, 0.4, 0.1]
        result = backtest_spread(spreads, scores, cost_per_position_change_bps=1)
        self.assertEqual(result.trades, 1)
        self.assertGreater(result.net_bps, 0)


if __name__ == "__main__":
    unittest.main()

