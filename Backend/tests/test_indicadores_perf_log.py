"""Tests de logging de performance de indicadores."""

from __future__ import annotations

import logging

from app.domains.indicadores.utils.indicadores_perf_log import (
    log_indicadores_endpoint,
    log_indicadores_query,
)


def test_perf_logs_noop_when_disabled(monkeypatch, caplog):
    monkeypatch.delenv("PERF_LOG", raising=False)
    caplog.set_level(logging.INFO)
    log_indicadores_endpoint(
        "ejecutivo",
        total_ms=10.0,
        desde="2026-01-01",
        hasta="2026-01-31",
    )
    log_indicadores_query("riesgo.top_rubros", 5.0)
    assert not any("[PERF][indicadores]" in r.message for r in caplog.records)


def test_perf_logs_emit_when_enabled(monkeypatch, caplog):
    monkeypatch.setenv("PERF_LOG", "1")
    caplog.set_level(logging.INFO)
    log_indicadores_endpoint(
        "productividad",
        total_ms=123.4,
        desde="2026-01-01",
        hasta="2026-01-31",
        distrito_id=2,
        inspector_id=None,
    )
    log_indicadores_query("productividad.realizadas", 42.0)
    messages = [r.message for r in caplog.records]
    assert any("[PERF][indicadores][productividad] total=123.4ms" in m for m in messages)
    assert any("[PERF][indicadores][productividad.realizadas] query=42.0ms" in m for m in messages)
