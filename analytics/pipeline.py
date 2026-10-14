"""Official-export ingestion, lineage, and deterministic JSON publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Sequence

from aurum_spread import CONTRACT_SPECS, IngestionResult, Observation, ingest_csv


SCHEMA_VERSION = "1.0.0"
ENGINE_VERSION = "0.2.0"
OFFICIAL_BHAVCOPY_URL = "https://www.mcxindia.com/market-data/bhavcopy"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_default(value: object) -> str:
    if isinstance(value, (datetime, Decimal)):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()  # type: ignore[no-any-return]
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(value, default=_json_default, sort_keys=True, separators=(",", ":"))


def specification_hash() -> str:
    payload = {
        symbol: [asdict(version) for version in versions]
        for symbol, versions in sorted(CONTRACT_SPECS.items())
    }
    return sha256_bytes(canonical_json(payload).encode("utf-8"))


def _observation_json(item: Observation) -> dict[str, Any]:
    return {
        "trading_date": item.trading_date.isoformat(),
        "symbol": item.symbol,
        "expiry_date": item.expiry_date.isoformat(),
        "instrument_name": item.instrument_name,
        "open": str(item.open),
        "high": str(item.high),
        "low": str(item.low),
        "close": str(item.close),
        "previous_close": str(item.previous_close) if item.previous_close is not None else None,
        "volume_lots": item.volume,
        "open_interest_lots": item.open_interest,
        "fine_gold_price_per_gram": str(item.fine_gold_price),
        "lot_notional_inr": str(item.lot_notional),
        "specification_effective_from": item.specification_effective_from.isoformat(),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, default=_json_default, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ingest_official_export(
    source_path: str | Path,
    requested_date: str,
    workspace: str | Path,
    *,
    retrieved_at: datetime | None = None,
    source_url: str = OFFICIAL_BHAVCOPY_URL,
) -> dict[str, Any]:
    """Archive and validate a manually downloaded official MCX CSV export.

    The raw file is copied byte-for-byte before parsing. A rejected import gets
    a validation report and manifest, but no cleaned dataset is published.
    """
    source = Path(source_path)
    if source.suffix.lower() != ".csv":
        raise ValueError("Only MCX CSV exports are accepted; re-export legacy .xls files as CSV without editing rows")
    raw_bytes = source.read_bytes()
    source_sha256 = sha256_bytes(raw_bytes)
    timestamp = (retrieved_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    timestamp_text = timestamp.isoformat().replace("+00:00", "Z")
    dataset_id = f"mcx-{requested_date.replace('/', '')}-{source_sha256[:12]}"
    root = Path(workspace)
    raw_path = root / "data" / "raw" / dataset_id / source.name
    raw_path.parent.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source, raw_path)
    if sha256_bytes(raw_path.read_bytes()) != source_sha256:
        raise RuntimeError("Archived raw file failed byte-for-byte hash verification")

    result: IngestionResult = ingest_csv(raw_path, requested_date=requested_date)
    status = "accepted" if result.valid and result.observations else "rejected"
    report = {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "status": status,
        "rows_seen": result.rows_seen,
        "rows_accepted": len(result.observations),
        "rows_ignored_non_target_symbols": result.rows_ignored,
        "issues": [asdict(issue) for issue in result.issues],
        "policy": {
            "missing_values_imputed": False,
            "duplicate_contract_keys_allowed": False,
            "instrument_required": "FUTCOM",
            "identity_fields": ["trading_date", "symbol", "expiry_date"],
        },
    }
    report_path = root / "data" / "reports" / f"{dataset_id}.validation.json"
    _write_json(report_path, report)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "engine_version": ENGINE_VERSION,
        "dataset_id": dataset_id,
        "status": status,
        "mode": "VERIFIED_HISTORICAL" if status == "accepted" else "REJECTED_IMPORT",
        "source": {
            "provider": "Multi Commodity Exchange of India (MCX)",
            "url": source_url,
            "requested_date_ddmmyyyy": requested_date,
            "retrieved_at_utc": timestamp_text,
            "original_filename": source.name,
            "archived_relative_path": raw_path.relative_to(root).as_posix(),
            "sha256": source_sha256,
            "bytes": len(raw_bytes),
        },
        "configuration": {
            "contract_specifications_sha256": specification_hash(),
            "symbols": sorted(CONTRACT_SPECS),
        },
        "validation_report": report_path.relative_to(root).as_posix(),
    }
    manifest_path = root / "data" / "manifests" / f"{dataset_id}.manifest.json"
    _write_json(manifest_path, manifest)

    cleaned_path: Path | None = None
    if status == "accepted":
        cleaned = {
            "schema_version": SCHEMA_VERSION,
            "engine_version": ENGINE_VERSION,
            "dataset_id": dataset_id,
            "mode": "VERIFIED_HISTORICAL",
            "lineage": {
                "raw_sha256": source_sha256,
                "contract_specifications_sha256": specification_hash(),
                "manifest": manifest_path.relative_to(root).as_posix(),
            },
            "observations": [_observation_json(item) for item in result.observations],
        }
        cleaned["content_sha256"] = sha256_bytes(canonical_json(cleaned).encode("utf-8"))
        cleaned_path = root / "data" / "clean" / f"{dataset_id}.observations.v1.json"
        _write_json(cleaned_path, cleaned)

    return {
        "dataset_id": dataset_id,
        "status": status,
        "raw_path": raw_path,
        "manifest_path": manifest_path,
        "report_path": report_path,
        "cleaned_path": cleaned_path,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Archive and validate an official MCX Bhavcopy CSV export")
    parser.add_argument("source", type=Path, help="Downloaded MCX CSV export")
    parser.add_argument("--requested-date", required=True, help="Requested MCX date in DD/MM/YYYY")
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    result = ingest_official_export(args.source, args.requested_date, args.workspace)
    print(json.dumps({key: str(value) if isinstance(value, Path) else value for key, value in result.items()}, indent=2))
    return 0 if result["status"] == "accepted" else 2


if __name__ == "__main__":
    raise SystemExit(main())
