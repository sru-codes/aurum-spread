import csv
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date
from io import StringIO
from pathlib import Path

from server import create_server


class RailwayApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "workspace"
        self.static = Path(self.temp.name) / "static"
        self.static.mkdir()
        (self.static / "demo-research.v1.json").write_text('{"mode":"DEMO"}', encoding="utf-8")
        (self.static / "context.v1.json").write_text('{"mode":"SUPPLEMENTARY_REFERENCE"}', encoding="utf-8")
        self.server = create_server("127.0.0.1", 0, workspace=self.root, static_data=self.static, admin_token="test-secret")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method: str, path: str, body: bytes | None = None, *, headers: dict[str, str] | None = None):
        request = urllib.request.Request(self.base + path, data=body, method=method, headers=headers or {})
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        return response.status, json.loads(response.read().decode("utf-8"))

    def test_health_and_demo_fallback_artifacts(self) -> None:
        status, health = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(health["service"], "aurum-spread-python")
        status, research = self.request("GET", "/api/research")
        self.assertEqual(status, 200)
        self.assertEqual(research["mode"], "DEMO")
        status, context = self.request("GET", "/api/context")
        self.assertEqual(status, 200)
        self.assertEqual(context["mode"], "SUPPLEMENTARY_REFERENCE")

    def test_mutations_require_a_bearer_token(self) -> None:
        status, payload = self.request("POST", "/api/context/refresh", b"{}", headers={"Content-Type": "application/json"})
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "unauthorized")

    def test_csv_import_merge_and_research_run_end_to_end(self) -> None:
        dataset_ids = []
        sessions = [date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 5), date(2026, 10, 6),
                    date(2026, 10, 7), date(2026, 10, 8), date(2026, 10, 9), date(2026, 10, 12)]
        for index, trading_day in enumerate(sessions):
            rows = []
            for symbol, expiry, close, activity in (
                ("GOLDTEN", "30OCT2026", 130000 + index * 40 + (index % 3) * 12, 1200),
                ("GOLDM", "05NOV2026", 129000 + index * 38, 14000),
            ):
                rows.append({
                    "Date": trading_day.strftime("%m/%d/%Y"),
                    "Instrument Name": "FUTCOM",
                    "Symbol": symbol,
                    "Expiry Date": expiry,
                    "Open": str(close - 10),
                    "High": str(close + 20),
                    "Low": str(close - 20),
                    "Close": str(close),
                    "Previous Close": str(close - 8),
                    "Vol (Lots)": str(activity),
                    "OI (Lots)": "5000",
                })
            buffer = StringIO()
            writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
            payload = buffer.getvalue().encode("utf-8")
            headers = {
                "Authorization": "Bearer test-secret",
                "Content-Type": "text/csv",
                "X-Filename": "fixture.csv",
            }
            day_text = trading_day.strftime("%d/%m/%Y")
            status, imported = self.request("POST", f"/api/mcx/import?requested_date_ddmmyyyy={day_text}", payload, headers=headers)
            self.assertEqual(status, 201, imported)
            dataset_ids.append(imported["dataset_id"])

        status, merged = self.request(
            "POST", "/api/mcx/merge",
            json.dumps({"dataset_ids": dataset_ids}).encode(),
            headers={"Authorization": "Bearer test-secret", "Content-Type": "application/json"},
        )
        self.assertEqual(status, 200, merged)
        self.assertEqual(merged["observations"], len(sessions) * 2)

        status, research = self.request(
            "POST", "/api/research/run",
            json.dumps({
                "dataset_id": "current",
                "candidate": "GOLDTEN",
                "candidate_expiry": "2026-10-30",
                "reference": "GOLDM",
                "reference_expiry": "2026-11-05",
                "lookback_sessions": 2,
                "annual_carry_bps": 0,
            }).encode(),
            headers={"Authorization": "Bearer test-secret", "Content-Type": "application/json"},
        )
        self.assertEqual(status, 200, research)
        self.assertEqual(research["mode"], "VERIFIED_HISTORICAL")
        status, published = self.request("GET", "/api/research")
        self.assertEqual(status, 200)
        self.assertEqual(published["mode"], "VERIFIED_HISTORICAL")
        self.assertEqual(published["lineage"]["dataset_id"], merged["dataset_id"])


if __name__ == "__main__":
    unittest.main()
