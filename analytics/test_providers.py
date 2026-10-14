import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from providers.base import JsonHttpClient, ProviderError, TransportResponse
from providers.frankfurter import FrankfurterAdapter, FxRate, align_fx_past_only, usd_ounce_to_inr_gram
from providers.fred import FredAdapter
from providers.gnews import GNewsAdapter
from providers.goldprice import GoldPriceAdapter, TROY_OUNCE_GRAMS


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append((url, headers, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def response(status: int, payload, headers=None):
    return TransportResponse(status, headers or {}, json.dumps(payload).encode())


class ProviderTests(unittest.TestCase):
    def client(self, provider, directory, transport, **kwargs):
        return JsonHttpClient(provider, directory, transport=transport, clock=lambda: 1_797_000_000, **kwargs)

    def test_cache_prevents_duplicate_network_request(self) -> None:
        transport = FakeTransport([response(200, {"value": 1})])
        with tempfile.TemporaryDirectory() as directory:
            client = self.client("test", directory, transport)
            first = client.get_json("https://example.test/value", ttl_seconds=60)
            second = client.get_json("https://example.test/value", ttl_seconds=60)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(first.cache_status, "miss")
        self.assertEqual(second.cache_status, "hit")

    def test_rate_limit_uses_retry_after_and_then_succeeds(self) -> None:
        sleeps = []
        transport = FakeTransport([
            response(429, {"error": "rate"}, {"Retry-After": "2"}),
            response(200, {"ok": True}),
        ])
        with tempfile.TemporaryDirectory() as directory:
            client = self.client("test", directory, transport, sleeper=sleeps.append, max_retries=1)
            result = client.get_json("https://example.test/value")
        self.assertEqual(result.payload, {"ok": True})
        self.assertEqual(sleeps, [2.0])

    def test_authentication_failure_is_not_retried(self) -> None:
        transport = FakeTransport([response(401, {"error": "bad key"})])
        with tempfile.TemporaryDirectory() as directory:
            client = self.client("test", directory, transport, max_retries=3)
            with self.assertRaises(ProviderError) as caught:
                client.get_json("https://example.test/value")
        self.assertEqual(caught.exception.code, "authentication_failed")
        self.assertEqual(len(transport.calls), 1)

    def test_gold_spot_validates_units_and_converts_troy_ounces(self) -> None:
        payload = {"symbols": [{
            "symbol": "XAU", "quote_currency": "USD", "unit": "troy_ounce",
            "contract_type": "spot", "price": "3100", "is_stale": True,
            "computed_at": "2026-10-14T10:00:00Z", "sources": [],
        }]}
        transport = FakeTransport([response(200, payload)])
        with tempfile.TemporaryDirectory() as directory:
            spot = GoldPriceAdapter(self.client("goldprice.dev", directory, transport)).fetch_spot()
        self.assertEqual(spot.price_usd_per_gram, Decimal("3100") / TROY_OUNCE_GRAMS)
        self.assertTrue(spot.is_stale)

    def test_gold_partial_or_wrong_schema_fails(self) -> None:
        payload = {"symbols": [{
            "symbol": "XAU", "quote_currency": "USD", "unit": "gram",
            "contract_type": "spot", "price": "100", "computed_at": "2026-10-14T10:00:00Z",
        }]}
        with tempfile.TemporaryDirectory() as directory:
            adapter = GoldPriceAdapter(self.client("goldprice.dev", directory, FakeTransport([response(200, payload)])))
            with self.assertRaises(ProviderError):
                adapter.fetch_spot()

    def test_frankfurter_preserves_effective_date_and_rejects_future(self) -> None:
        good = {"date": "2026-10-13", "base": "USD", "quote": "INR", "rate": 95.53}
        future = {"date": "2026-10-15", "base": "USD", "quote": "INR", "rate": 95.53}
        with tempfile.TemporaryDirectory() as directory:
            first = FrankfurterAdapter(self.client("frankfurter", directory, FakeTransport([response(200, good)])))
            rate = first.fetch_rate(date(2026, 10, 14))
            second = FrankfurterAdapter(self.client("frankfurter", Path(directory) / "future", FakeTransport([response(200, future)])))
            with self.assertRaises(ProviderError):
                second.fetch_rate(date(2026, 10, 14))
        self.assertEqual(rate.effective_date, date(2026, 10, 13))

    def test_alignment_does_not_forward_fill_or_look_forward(self) -> None:
        item = FxRate(date(2026, 10, 13), "USD", "INR", Decimal("95"), "now", "url", "miss")
        aligned = align_fx_past_only([date(2026, 10, 13), date(2026, 10, 14)], [item])
        self.assertIs(aligned[date(2026, 10, 13)], item)
        self.assertIsNone(aligned[date(2026, 10, 14)])
        self.assertAlmostEqual(usd_ounce_to_inr_gram(Decimal("3100"), Decimal("90")), Decimal("3100") * Decimal("90") / TROY_OUNCE_GRAMS)

    def test_optional_providers_require_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = self.client("optional", directory, FakeTransport([]))
            with self.assertRaisesRegex(ProviderError, "FRED_API_KEY"):
                FredAdapter(client, None).fetch_series("DGS10", date(2026, 1, 1), date(2026, 1, 2), as_of=date(2026, 1, 3))
            with self.assertRaisesRegex(ProviderError, "GNEWS_API_KEY"):
                GNewsAdapter(client, None).search(
                    "gold", datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 2, tzinfo=timezone.utc)
                )

    def test_gnews_rejects_article_after_historical_cutoff(self) -> None:
        payload = {"articles": [{
            "title": "Gold", "url": "https://example.test", "publishedAt": "2026-01-03T00:00:00Z",
            "source": {"name": "Example"}, "description": "Context",
        }]}
        with tempfile.TemporaryDirectory() as directory:
            adapter = GNewsAdapter(self.client("gnews", directory, FakeTransport([response(200, payload)])), "secret")
            with self.assertRaises(ProviderError) as caught:
                adapter.search(
                    "gold",
                    datetime(2026, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 2, tzinfo=timezone.utc),
                )
        self.assertEqual(caught.exception.code, "future_observation")


if __name__ == "__main__":
    unittest.main()
