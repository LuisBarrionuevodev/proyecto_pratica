"""
GEO-GOOGLE.1.1 — tests del script diag_geo_google_1 (sin llamadas reales a APIs).
"""

from __future__ import annotations

import importlib.util
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "diag_geo_google_1.py"


def _load_diag_module():
    spec = importlib.util.spec_from_file_location("diag_geo_google_1", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def diag():
    return _load_diag_module()


def test_missing_google_key_exits_cleanly(diag, monkeypatch):
    """A: falta GOOGLE_MAPS_API_KEY → mensaje controlado."""
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GEOCODING_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        diag._require_google_api_key()
    assert exc.value.code == 1


def test_manual_mode_does_not_build_dataset(diag, monkeypatch):
    """B: una dirección manual no usa selector DB."""
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key-not-logged")
    fake_row = {
        "input": "Corrientes 500",
        "status": "OK",
        "lat": -26.82,
        "lng": -65.20,
        "location_type": "ROOFTOP",
        "place_id": "pid",
        "partial_match": False,
        "latency_ms": 10.0,
        "formatted_address": "Corrientes 500",
    }
    with patch.object(diag, "_geocode_google_address", return_value=fake_row) as mock_geo:
        with patch.object(diag, "_build_dataset") as mock_dataset:
            rows, summary = diag._run_manual_addresses(
                ["Corrientes 500, San Miguel de Tucumán, Tucumán, Argentina"],
                "test-key-not-logged",
                google_only=True,
            )
    mock_dataset.assert_not_called()
    mock_geo.assert_called_once()
    assert len(rows) == 1
    assert summary["total"] == 1


def test_five_manual_addresses_processed(diag, monkeypatch):
    """C: cinco direcciones → procesa exactamente cinco."""
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    addresses = [f"Direccion {i}, San Miguel de Tucumán, Tucumán, Argentina" for i in range(5)]
    with patch.object(
        diag,
        "_geocode_google_address",
        side_effect=[
            {
                "input": a,
                "status": "OK",
                "lat": -26.0,
                "lng": -65.0,
                "location_type": "ROOFTOP",
                "partial_match": False,
                "latency_ms": 1.0,
            }
            for a in addresses
        ],
    ):
        rows, summary = diag._run_manual_addresses(addresses, "test-key", google_only=True)
    assert len(rows) == 5
    assert summary["total"] == 5
    assert summary["ok"] == 5


def test_more_than_ten_addresses_rejected(diag):
    """D: >10 direcciones → rechazado."""
    addresses = [f"addr{i}" for i in range(11)]
    with pytest.raises(SystemExit) as exc:
        diag._validate_manual_address_count(addresses)
    assert exc.value.code == 1


def test_google_only_skips_geoapify(diag, monkeypatch):
    """E: --google-only → Geoapify no es llamado."""
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    with patch.object(
        diag,
        "_geocode_google_address",
        return_value={"input": "x", "status": "OK", "latency_ms": 1.0, "location_type": "ROOFTOP"},
    ):
        with patch.object(diag, "_request_geoapify_timed") as mock_geoapify:
            diag._run_manual_addresses(["Calle 1"], "test-key", google_only=True)
    mock_geoapify.assert_not_called()


def test_parse_google_ok_response(diag):
    """F: respuesta OK parsea lat/lng/place_id/location_type."""
    raw = {
        "status": "OK",
        "results": [
            {
                "formatted_address": "Corrientes 500, T4000 San Miguel de Tucumán, Argentina",
                "place_id": "ChIJtest",
                "geometry": {
                    "location": {"lat": -26.8229733, "lng": -65.2026602},
                    "location_type": "ROOFTOP",
                },
            }
        ],
    }
    norm = diag._normalize_google_result(raw, "Corrientes 500")
    assert norm["status"] == "OK"
    assert norm["lat"] == -26.8229733
    assert norm["lng"] == -65.2026602
    assert norm["place_id"] == "ChIJtest"
    assert norm["location_type"] == "ROOFTOP"
    assert diag._display_status(norm) == "OK"


def test_zero_results_does_not_break(diag):
    """G: ZERO_RESULTS no rompe."""
    raw = {"status": "ZERO_RESULTS", "results": []}
    norm = diag._normalize_google_result(raw, "Calle Inexistente 99999")
    assert norm["status"] == "ZERO_RESULTS"
    assert norm["lat"] is None
    assert diag._display_status(norm) == "ZERO_RESULTS"


def test_zero_results_via_geocode_address(diag, monkeypatch):
    """G: ZERO_RESULTS vía _geocode_google_address."""
    monkeypatch.setattr(
        diag,
        "_request_google",
        lambda _q, _k: (
            {
                "status": "ZERO_RESULTS",
                "lat": None,
                "lng": None,
                "place_id": None,
                "formatted_address": None,
                "location_type": None,
                "partial_match": None,
                "query": "x",
            },
            5.0,
        ),
    )
    row = diag._geocode_google_address("x", "secret-key-abc")
    assert row["status"] == "ZERO_RESULTS"


def test_key_never_in_output(diag, monkeypatch, capsys):
    """H: la key nunca aparece en output."""
    secret = "AIzaSyD_secret_key_12345"
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", secret)
    with patch.object(
        diag,
        "_request_google",
        side_effect=urllib_error_raising(secret),
    ):
        row = diag._geocode_google_address("Calle 1", secret)
    captured = capsys.readouterr()
    diag._print_manual_address_result(row)
    out = captured.out + str(row)
    assert secret not in out
    assert "AIzaSyD" not in out


def urllib_error_raising(secret: str):
    def _raise(_q, _k):
        raise urllib.error.URLError(f"connection failed key={secret}")

    return _raise


def test_redact_secret(diag):
    """H: redact elimina secretos de mensajes."""
    msg = diag._redact_secret("failed url key=ABC123", "ABC123")
    assert "ABC123" not in msg
    assert "***" in msg


def test_request_denied_error_kind(diag, monkeypatch):
    """Errores Google API distinguibles."""
    monkeypatch.setattr(
        diag,
        "_request_google",
        lambda _q, _k: (
            {
                "status": "REQUEST_DENIED",
                "lat": None,
                "lng": None,
                "place_id": None,
                "formatted_address": None,
                "location_type": None,
                "partial_match": None,
                "query": "x",
            },
            3.0,
        ),
    )
    row = diag._geocode_google_address("x", "k")
    assert row["status"] == "ERROR"
    assert row["error_kind"] == "REQUEST_DENIED"
