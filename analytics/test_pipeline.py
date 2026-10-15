import csv
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pipeline import ingest_official_export, merge_clean_datasets


class PipelineTests(unittest.TestCase):
    def write_export(self, path: Path, *, duplicate: bool = False) -> bytes:
        row = {
            "Date": "10/14/2026",
            "Instrument Name": "FUTCOM",
            "Symbol": " GOLDTEN ",
            "Expiry Date": "29OCT2026",
            "Open": "125400",
            "High": "125600",
            "Low": "125300",
            "Close": "125506",
            "Previous Close": "125390",
            "Vol (Lots)": "1200",
            "OI (Lots)": "4500",
        }
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(row))
            writer.writeheader()
            writer.writerow(row)
            if duplicate:
                writer.writerow(row)
        return path.read_bytes()

    def test_preserves_raw_hash_and_publishes_versioned_clean_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "official.csv"
            raw = self.write_export(source)
            workspace = root / "workspace"
            result = ingest_official_export(
                source,
                "14/10/2026",
                workspace,
                retrieved_at=datetime(2026, 10, 14, 18, 30, tzinfo=timezone.utc),
            )
            manifest = json.loads(result["manifest_path"].read_text())
            cleaned = json.loads(result["cleaned_path"].read_text())
            archived = result["raw_path"].read_bytes()
        expected_hash = hashlib.sha256(raw).hexdigest()
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(archived, raw)
        self.assertEqual(manifest["source"]["sha256"], expected_hash)
        self.assertEqual(manifest["source"]["retrieved_at_utc"], "2026-10-14T18:30:00Z")
        self.assertEqual(cleaned["mode"], "VERIFIED_HISTORICAL")
        self.assertEqual(cleaned["observations"][0]["expiry_date"], "2026-10-29")

    def test_reimport_of_same_source_reuses_raw_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "official.csv"
            self.write_export(source)
            workspace = root / "workspace"
            first = ingest_official_export(source, "14/10/2026", workspace)
            second = ingest_official_export(source, "14/10/2026", workspace)
            raw_files = list((workspace / "data" / "raw").rglob("*.csv"))
        self.assertEqual(first["dataset_id"], second["dataset_id"])
        self.assertEqual(len(raw_files), 1)

    def test_rejected_import_gets_report_but_no_clean_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "duplicate.csv"
            self.write_export(source, duplicate=True)
            result = ingest_official_export(source, "14/10/2026", root / "workspace")
            report = json.loads(result["report_path"].read_text())
        self.assertEqual(result["status"], "rejected")
        self.assertIsNone(result["cleaned_path"])
        self.assertEqual(report["rows_accepted"], 1)
        self.assertEqual(len(report["issues"]), 1)

    def test_empty_target_import_explains_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "no-target.csv"
            self.write_export(source)
            source.write_text(source.read_text().replace("GOLDTEN", "SILVER"), encoding="utf-8")
            result = ingest_official_export(source, "14/10/2026", root / "workspace")
            report = json.loads(result["report_path"].read_text())
        self.assertEqual(result["status"], "rejected")
        self.assertIsNone(result["cleaned_path"])
        self.assertEqual(report["issues"][0]["code"], "no_target_rows")

    def test_refuses_non_csv_without_archiving_or_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "official.xls"
            source.write_bytes(b"not a csv")
            with self.assertRaises(ValueError):
                ingest_official_export(source, "14/10/2026", Path(directory) / "workspace")

    def test_merge_refuses_duplicate_contract_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "official.csv"
            self.write_export(source)
            first = ingest_official_export(source, "14/10/2026", root / "one")
            second = ingest_official_export(source, "14/10/2026", root / "two")
            with self.assertRaisesRegex(ValueError, "Duplicate observation"):
                merge_clean_datasets(
                    [first["cleaned_path"], second["cleaned_path"]], root / "merged.json"
                )


if __name__ == "__main__":
    unittest.main()
