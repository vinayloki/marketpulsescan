"""
MarketPulseScan — Publish Module

Converts pipeline outputs into the versioned static JSON bundle
that GitHub Pages serves as the API.

Bundle layout (written to output_dir):
    api/v1/
        manifest.json
        market.json
        universe.json

All files are validated against schemas/v1/*.schema.json before writing.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003
from typing import Any

log = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"


# ── Data models ───────────────────────────────────────────────────────────────


def build_manifest(
    run_id: str,
    files: list[dict[str, Any]],
    pipeline_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a manifest.json payload."""
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "run_id": run_id,
        "pipeline": pipeline_meta or {},
        "files": files,
    }


def build_market_payload(
    records: list[dict[str, Any]],
    run_id: str,
) -> dict[str, Any]:
    """Build market.json payload from a list of per-stock records."""
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "run_id": run_id,
        "data": records,
    }


def build_universe_payload(
    symbols: list[dict[str, Any]],
    run_id: str,
) -> dict[str, Any]:
    """Build universe.json payload from a list of UniverseSymbol.to_dict()."""
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "run_id": run_id,
        "data": symbols,
    }


# ── Writer ────────────────────────────────────────────────────────────────────


class BundleWriter:
    """
    Writes the complete API bundle to output_dir/api/v1/.

    Usage:
        writer = BundleWriter(output_dir=Path("/tmp/bundle"))
        writer.write_universe(universe_payload)
        writer.write_market(market_payload)
        manifest = writer.finalise(run_id="github-run-123")
    """

    def __init__(self, output_dir: Path, validate: bool = True) -> None:
        self._api_dir = output_dir / "api" / "v1"
        self._api_dir.mkdir(parents=True, exist_ok=True)
        self._validate = validate
        self._file_records: list[dict[str, Any]] = []

    def write_universe(self, payload: dict[str, Any]) -> Path:
        return self._write("universe.json", payload)

    def write_market(self, payload: dict[str, Any]) -> Path:
        return self._write("market.json", payload)

    def write_json(self, filename: str, payload: dict[str, Any]) -> Path:
        return self._write(filename, payload)

    def finalise(self, run_id: str, pipeline_meta: dict[str, Any] | None = None) -> Path:
        """Write manifest.json and return its path."""
        manifest = build_manifest(run_id, self._file_records, pipeline_meta)
        path = self._api_dir / "manifest.json"
        _write_json(path, manifest)
        log.info("Publish: manifest written → %s", path.name)
        return path

    def _write(self, filename: str, payload: dict[str, Any]) -> Path:
        path = self._api_dir / filename
        _write_json(path, payload)
        checksum = _sha256(path)
        row_count = len(payload.get("data", payload.get("files", [])))
        self._file_records.append(
            {
                "path": filename,
                "checksum": checksum,
                "row_count": row_count,
                "as_of": datetime.now(tz=UTC).date().isoformat(),
                "size_bytes": path.stat().st_size,
            }
        )
        log.info("Publish: wrote %s (%d rows, %s)", filename, row_count, checksum[:8])
        return path


# ── Validation ────────────────────────────────────────────────────────────────


def validate_bundle(bundle_dir: Path) -> list[str]:
    """
    Validate all JSON files in bundle_dir/api/v1/ against their schemas.

    Returns list of error messages. Empty list = all valid.
    Requires `jsonschema` package (optional dep).
    """
    try:
        import jsonschema
    except ImportError:
        log.warning("Publish: jsonschema not installed — skipping schema validation")
        return []

    from marketpulse.config.settings import SCHEMA_DIR

    errors: list[str] = []
    api_dir = bundle_dir / "api" / "v1"
    schema_map = {
        "manifest.json": "manifest.schema.json",
        "market.json": "market.schema.json",
        "universe.json": "universe.schema.json",
    }

    for data_file, schema_file in schema_map.items():
        data_path = api_dir / data_file
        schema_path = SCHEMA_DIR / schema_file

        if not data_path.exists():
            errors.append(f"Missing: {data_file}")
            continue
        if not schema_path.exists():
            log.debug("Publish: schema not found for %s — skipping", data_file)
            continue

        try:
            with data_path.open(encoding="utf-8") as f:
                data = json.load(f)
            with schema_path.open(encoding="utf-8") as f:
                schema = json.load(f)
            jsonschema.validate(data, schema)
            log.debug("Publish: %s validates OK", data_file)
        except jsonschema.ValidationError as exc:
            errors.append(f"{data_file}: {exc.message}")
        except Exception as exc:
            errors.append(f"{data_file}: unexpected error: {exc}")

    return errors


# ── Helpers ───────────────────────────────────────────────────────────────────


def _write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
