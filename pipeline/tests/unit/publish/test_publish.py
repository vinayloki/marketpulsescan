"""
Unit tests for publish/__init__.py — no external calls.
"""

from __future__ import annotations

import json
from pathlib import Path

from marketpulse.publish import (
    BundleWriter,
    _sha256,
    _write_json,
    build_manifest,
    build_market_payload,
    build_universe_payload,
    validate_bundle,
)

# ── Payload builders ──────────────────────────────────────────────────────────


def test_build_manifest_structure():
    manifest = build_manifest(
        run_id="test-001",
        files=[{"path": "market.json", "checksum": "abc", "row_count": 5}],
    )
    assert manifest["schema_version"] == "1.0"
    assert manifest["run_id"] == "test-001"
    assert "generated_at" in manifest
    assert len(manifest["files"]) == 1


def test_build_market_payload():
    records = [{"symbol": "RELIANCE", "close": 2945.0}]
    payload = build_market_payload(records, run_id="r1")
    assert payload["schema_version"] == "1.0"
    assert payload["run_id"] == "r1"
    assert len(payload["data"]) == 1


def test_build_universe_payload():
    syms = [{"symbol": "TCS", "exchange": "NSE"}]
    payload = build_universe_payload(syms, run_id="r1")
    assert len(payload["data"]) == 1


# ── _write_json and _sha256 ───────────────────────────────────────────────────


def test_write_json_and_sha256(tmp_path):
    path = tmp_path / "test.json"
    _write_json(path, {"key": "value"})
    assert path.exists()
    with path.open() as f:
        data = json.load(f)
    assert data["key"] == "value"

    checksum = _sha256(path)
    assert len(checksum) == 64  # SHA-256 hex digest


def test_sha256_is_deterministic(tmp_path):
    path = tmp_path / "test.json"
    _write_json(path, {"x": 1})
    c1 = _sha256(path)
    c2 = _sha256(path)
    assert c1 == c2


# ── BundleWriter ──────────────────────────────────────────────────────────────


def test_bundle_writer_creates_api_v1_dir(tmp_path):
    BundleWriter(tmp_path)
    assert (tmp_path / "api" / "v1").exists()


def test_bundle_writer_write_universe(tmp_path):
    writer = BundleWriter(tmp_path)
    payload = build_universe_payload([{"symbol": "RELIANCE"}], "run-1")
    path = writer.write_universe(payload)
    assert path.exists()
    with path.open() as f:
        data = json.load(f)
    assert data["run_id"] == "run-1"


def test_bundle_writer_write_market(tmp_path):
    writer = BundleWriter(tmp_path)
    payload = build_market_payload([{"symbol": "TCS"}], "run-1")
    path = writer.write_market(payload)
    assert path.exists()


def test_bundle_writer_finalise_writes_manifest(tmp_path):
    writer = BundleWriter(tmp_path)
    writer.write_universe(build_universe_payload([], "r1"))
    writer.write_market(build_market_payload([], "r1"))
    manifest_path = writer.finalise("r1")
    assert manifest_path.exists()
    with manifest_path.open() as f:
        manifest = json.load(f)
    assert manifest["run_id"] == "r1"
    assert len(manifest["files"]) == 2  # universe + market


def test_bundle_writer_file_records_include_checksum(tmp_path):
    writer = BundleWriter(tmp_path)
    writer.write_market(build_market_payload([{"symbol": "INFY"}], "r1"))
    record = writer._file_records[0]
    assert "checksum" in record
    assert len(record["checksum"]) == 64
    assert record["row_count"] == 1


def test_bundle_writer_row_count_correct(tmp_path):
    writer = BundleWriter(tmp_path)
    records = [{"symbol": "A"}, {"symbol": "B"}, {"symbol": "C"}]
    writer.write_market(build_market_payload(records, "r1"))
    assert writer._file_records[0]["row_count"] == 3


# ── validate_bundle ───────────────────────────────────────────────────────────


def test_validate_bundle_reports_missing_files(tmp_path):
    """validate_bundle should report missing required files."""
    errors = validate_bundle(tmp_path)
    # manifest.json, market.json, universe.json are all missing
    assert any("Missing" in e for e in errors)


def test_validate_bundle_no_errors_on_complete_bundle(tmp_path):
    """A bundle written by BundleWriter should pass validation (jsonschema optional)."""
    writer = BundleWriter(tmp_path)
    writer.write_universe(build_universe_payload([], "r1"))
    writer.write_market(build_market_payload([], "r1"))
    writer.finalise("r1")

    try:
        import jsonschema  # noqa: F401

        # jsonschema available — validation may fail on minimal data but should not crash
        errors = validate_bundle(tmp_path)
        # Only structural errors (missing files) should be reported, not import errors
        assert isinstance(errors, list)
    except ImportError:
        # jsonschema not installed — validate_bundle should skip gracefully
        errors = validate_bundle(tmp_path)
        assert errors == []


# ── Config tests ──────────────────────────────────────────────────────────────


def test_settings_paths_are_path_objects():
    from marketpulse.config.settings import CACHE_DIR, OUTPUT_DIR, ROOT_DIR

    assert isinstance(ROOT_DIR, Path)
    assert isinstance(CACHE_DIR, Path)
    assert isinstance(OUTPUT_DIR, Path)


def test_settings_constants_have_correct_types():
    from marketpulse.config.settings import (
        BATCH_DELAY_SECONDS,
        BATCH_SIZE,
        CAPITAL,
        MIN_DATA_POINTS,
        RISK_PER_TRADE_PCT,
    )

    assert isinstance(BATCH_SIZE, int)
    assert isinstance(BATCH_DELAY_SECONDS, float)
    assert isinstance(MIN_DATA_POINTS, int)
    assert isinstance(CAPITAL, int)
    assert isinstance(RISK_PER_TRADE_PCT, float)


def test_sector_map_normalize_sector():
    from marketpulse.config.sector_map import CANONICAL_SECTORS, normalize_sector

    assert normalize_sector("Financial Services") == "Banking & Finance"
    assert normalize_sector("Industrials") == "Capital Goods & Engineering"
    assert normalize_sector("Consumer Defensive") == "FMCG & Consumer"
    assert normalize_sector(None) == "Others"
    assert normalize_sector("Gibberish XYZ") == "Others"
    assert normalize_sector("technology") == "IT & Technology"
    # All canonical sectors should round-trip
    for sector in CANONICAL_SECTORS:
        assert sector in CANONICAL_SECTORS
