"""Small authenticated HTTP API for running Aurum research on Railway."""

from __future__ import annotations

import hmac
import json
import logging
import os
import re
import tempfile
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from typing import Any

from aurum_spread import CONTRACT_SPECS, DataQualityError
from pipeline import ENGINE_VERSION, ingest_official_export, merge_clean_datasets
from refresh_context import build_context_snapshot
from run_research import generate_snapshot


LOGGER = logging.getLogger("aurum.api")
MAX_BODY_BYTES = 100 * 1024 * 1024
DATASET_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9-]{0,100}$")
ALLOWED_SYMBOLS = frozenset(CONTRACT_SPECS)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    content_type = handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise ApiError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "content_type", "Expected application/json")
    size = _body_size(handler)
    if size > 1024 * 1024:
        raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body_too_large", "JSON request exceeds 1 MiB")
    try:
        value = json.loads(handler.rfile.read(size).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_json", "Request body is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_json", "Request body must be a JSON object")
    return value


def _body_size(handler: BaseHTTPRequestHandler) -> int:
    value = handler.headers.get("Content-Length")
    if value is None:
        raise ApiError(HTTPStatus.LENGTH_REQUIRED, "content_length", "Content-Length is required")
    try:
        size = int(value)
    except ValueError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "content_length", "Invalid Content-Length") from exc
    if size < 0:
        raise ApiError(HTTPStatus.BAD_REQUEST, "content_length", "Invalid Content-Length")
    if size > MAX_BODY_BYTES:
        raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body_too_large", "CSV upload exceeds 100 MiB")
    return size


def _dataset_file(workspace: Path, dataset_id: str) -> Path:
    if not DATASET_ID_RE.fullmatch(dataset_id):
        raise ApiError(HTTPStatus.BAD_REQUEST, "dataset_id", "Invalid dataset_id")
    if dataset_id == "current":
        return workspace / "data" / "clean" / "current.observations.v1.json"
    return workspace / "data" / "clean" / f"{dataset_id}.observations.v1.json"


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", f"{key} must be a non-empty string")
    return value.strip()


def _expiry(payload: dict[str, Any], key: str) -> date:
    value = _required_string(payload, key)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_date", f"{key} must use YYYY-MM-DD") from exc


def create_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    *,
    workspace: str | Path | None = None,
    static_data: str | Path | None = None,
    admin_token: str | None = None,
) -> ThreadingHTTPServer:
    root = Path(workspace or os.getenv("AURUM_WORKSPACE", Path(__file__).resolve().parents[1])).resolve()
    static_root = Path(static_data) if static_data else Path(os.getenv("AURUM_STATIC_DATA_DIR", "/srv/data"))
    if not static_root.exists():
        static_root = root / "public" / "data"
    token = admin_token if admin_token is not None else os.getenv("AURUM_ADMIN_TOKEN", "")

    class Handler(BaseHTTPRequestHandler):
        server_version = "AurumSpreadAPI/0.3.0"
        sys_version = ""

        def log_message(self, format: str, *args: object) -> None:
            LOGGER.info("%s - %s", self.address_string(), format % args)

        def _send_json(self, status: int, payload: Any) -> None:
            body = _json_bytes(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _error(self, error: ApiError) -> None:
            self._send_json(error.status, {"error": {"code": error.code, "message": str(error)}})

        def _admin(self) -> None:
            if not token:
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "admin_not_configured", "AURUM_ADMIN_TOKEN is not configured")
            supplied = self.headers.get("Authorization", "")
            expected = f"Bearer {token}"
            if not hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")):
                raise ApiError(HTTPStatus.UNAUTHORIZED, "unauthorized", "A valid bearer token is required")

        def _read_artifact(self, preferred: Path, fallback_name: str) -> None:
            source = preferred if preferred.is_file() else static_root / fallback_name
            if not source.is_file():
                raise ApiError(HTTPStatus.NOT_FOUND, "artifact_unavailable", "No artifact has been published yet")
            try:
                payload = json.loads(source.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                LOGGER.exception("Could not read published artifact %s", source)
                raise ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "artifact_invalid", "Published artifact could not be read") from exc
            self._send_json(HTTPStatus.OK, payload)

        def do_GET(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            if path == "/health" or path == "/api/health":
                try:
                    (root / "data").mkdir(parents=True, exist_ok=True)
                    writable = os.access(root / "data", os.W_OK)
                except OSError:
                    writable = False
                self._send_json(HTTPStatus.OK, {
                    "status": "ok",
                    "service": "aurum-spread-python",
                    "engine_version": ENGINE_VERSION,
                    "storage_writable": writable,
                    "persistent_volume_attached": bool(os.getenv("RAILWAY_VOLUME_MOUNT_PATH")),
                })
                return
            if path == "/api/research":
                self._read_artifact(root / "data" / "published" / "research.v1.json", "demo-research.v1.json")
                return
            if path == "/api/context":
                self._read_artifact(root / "data" / "published" / "context.v1.json", "context.v1.json")
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": {"code": "not_found", "message": "Unknown API route"}})

        def do_POST(self) -> None:  # noqa: N802
            try:
                self._admin()
                path = urlsplit(self.path)
                if path.path == "/api/mcx/import":
                    self._import_csv(parse_qs(path.query, strict_parsing=True))
                elif path.path == "/api/mcx/merge":
                    self._merge()
                elif path.path == "/api/research/run":
                    self._run_research()
                elif path.path == "/api/context/refresh":
                    self._refresh_context()
                else:
                    raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "Unknown API route")
            except ApiError as exc:
                self._error(exc)
            except (DataQualityError, ValueError) as exc:
                self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": {"code": "validation_failed", "message": str(exc)}})
            except Exception:
                LOGGER.exception("Unhandled API request failure")
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": {"code": "internal_error", "message": "Request failed; inspect service logs using the request timestamp"}})

        def _import_csv(self, query: dict[str, list[str]]) -> None:
            requested_values = query.get("requested_date_ddmmyyyy", [])
            if len(requested_values) != 1:
                raise ApiError(HTTPStatus.BAD_REQUEST, "requested_date", "Provide one requested_date_ddmmyyyy query parameter")
            requested_date = requested_values[0]
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type not in {"text/csv", "application/csv", "application/octet-stream"}:
                raise ApiError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "content_type", "Upload an official CSV as text/csv")
            filename = Path(self.headers.get("X-Filename", "bhavcopy.csv")).name
            if not filename.lower().endswith(".csv") or filename in {".", ".."}:
                raise ApiError(HTTPStatus.BAD_REQUEST, "filename", "X-Filename must be a .csv filename")
            size = _body_size(self)
            if size == 0:
                raise ApiError(HTTPStatus.BAD_REQUEST, "empty_upload", "CSV upload is empty")
            body = self.rfile.read(size)
            with tempfile.TemporaryDirectory(prefix="aurum-upload-") as temp_dir:
                source = Path(temp_dir) / filename
                source.write_bytes(body)
                result = ingest_official_export(source, requested_date, root)
            report = json.loads(result["report_path"].read_text(encoding="utf-8"))
            self._send_json(HTTPStatus.CREATED if result["status"] == "accepted" else HTTPStatus.UNPROCESSABLE_ENTITY, {
                "dataset_id": result["dataset_id"],
                "status": result["status"],
                "manifest": str(result["manifest_path"].relative_to(root)),
                "validation_report": report,
            })

        def _merge(self) -> None:
            payload = _read_json(self)
            ids = payload.get("dataset_ids")
            if not isinstance(ids, list) or not ids or any(not isinstance(item, str) for item in ids):
                raise ApiError(HTTPStatus.BAD_REQUEST, "dataset_ids", "dataset_ids must be a non-empty array of IDs")
            paths = [_dataset_file(root, item) for item in ids]
            missing = [str(path.name) for path in paths if not path.is_file()]
            if missing:
                raise ApiError(HTTPStatus.NOT_FOUND, "dataset_missing", f"Clean dataset not found: {', '.join(missing)}")
            output = root / "data" / "clean" / "current.observations.v1.json"
            merged = merge_clean_datasets(paths, output)
            self._send_json(HTTPStatus.OK, {
                "dataset_id": merged["dataset_id"],
                "content_sha256": merged["content_sha256"],
                "observations": len(merged["observations"]),
                "output": str(output.relative_to(root)),
            })

        def _run_research(self) -> None:
            payload = _read_json(self)
            candidate = _required_string(payload, "candidate").upper()
            reference = _required_string(payload, "reference").upper()
            if candidate not in ALLOWED_SYMBOLS or reference not in ALLOWED_SYMBOLS or candidate == reference:
                raise ApiError(HTTPStatus.BAD_REQUEST, "symbol_pair", "Choose two distinct supported MCX gold futures")
            try:
                lookback = int(payload.get("lookback_sessions", 40))
                carry = float(payload.get("annual_carry_bps", 0))
            except (TypeError, ValueError) as exc:
                raise ApiError(HTTPStatus.BAD_REQUEST, "configuration", "Invalid lookback or carry configuration") from exc
            if not 2 <= lookback <= 500 or not 0 <= carry <= 100_000:
                raise ApiError(HTTPStatus.BAD_REQUEST, "configuration", "lookback must be 2–500 sessions; carry must be 0–100000 bps")
            dataset_id = payload.get("dataset_id", "current")
            if not isinstance(dataset_id, str):
                raise ApiError(HTTPStatus.BAD_REQUEST, "dataset_id", "dataset_id must be a string")
            clean_path = _dataset_file(root, dataset_id)
            if not clean_path.is_file():
                raise ApiError(HTTPStatus.NOT_FOUND, "dataset_missing", f"Clean dataset not found: {clean_path.name}")
            output = root / "data" / "published" / "research.v1.json"
            snapshot = generate_snapshot(
                clean_path,
                candidate=candidate,
                candidate_expiry=_expiry(payload, "candidate_expiry"),
                reference=reference,
                reference_expiry=_expiry(payload, "reference_expiry"),
                lookback=lookback,
                annual_carry_bps=carry,
                output=output,
            )
            self._send_json(HTTPStatus.OK, {
                "content_sha256": snapshot["content_sha256"],
                "mode": snapshot["mode"],
                "series_points": len(snapshot["series"]),
                "output": str(output.relative_to(root)),
            })

        def _refresh_context(self) -> None:
            payload = _read_json(self)
            if payload:
                raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_request", "Context refresh does not accept request fields")
            cache_dir = root / "data" / ".cache" / "providers"
            snapshot = build_context_snapshot(cache_dir)
            output = root / "data" / "published" / "context.v1.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            self._send_json(HTTPStatus.OK, {
                "content_sha256": snapshot["content_sha256"],
                "generated_at_utc": snapshot["generated_at_utc"],
                "providers": snapshot["providers"],
                "output": str(output.relative_to(root)),
            })

    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    port = int(os.getenv("AURUM_INTERNAL_PORT", "8000"))
    server = create_server(port=port)
    LOGGER.info("Aurum Spread API listening on port %s", port)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
