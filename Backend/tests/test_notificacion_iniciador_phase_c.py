"""
Fase C: sync desacoplado de GETs; camino canónico CLI / flask; compatibilidad env opcional.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from app.domains.actuaciones.schemas.pendientes_filters import ActuacionesPendientesFilters
from app.domains.actuaciones.services.notificacion_iniciador_service import (
    SyncReinspeccionNotificacionOutcome,
    materializacion_notificacion_vencida_on_read_enabled,
)


def test_run_sync_pipeline_incluye_metricas_fase_c(monkeypatch):
    from app.domains.actuaciones.pipelines import sync_notificaciones_vencidas as pipe

    monkeypatch.setattr(
        pipe,
        "sync_iniciadores_reinspeccion_notificacion",
        lambda: SyncReinspeccionNotificacionOutcome(
            created=2,
            eligible_notificaciones=5,
            skipped_already_blocking=1,
            collisions_idempotent=0,
        ),
    )
    m = pipe.run_sync_notificaciones_vencidas()
    assert m["status"] == "ok"
    assert m["created"] == 2
    assert m["eligible_notificaciones"] == 5
    assert m["skipped_already_blocking"] == 1
    assert m["collisions_idempotent"] == 0
    assert "elapsed_ms" in m


def test_get_pendientes_notificacion_no_llama_sync_por_defecto(client, monkeypatch, auth_headers):
    mock_sync = MagicMock()
    monkeypatch.setattr(
        "app.domains.actuaciones.services.notificacion_iniciador_service.sync_iniciadores_reinspeccion_notificacion",
        mock_sync,
    )
    monkeypatch.setattr(
        "app.domains.actuaciones.routes.pendientes_notificacion.list_reinspeccion_notificacion_operativas",
        lambda: [],
    )
    r = client.get("/actuaciones/pendientes-notificacion", headers=auth_headers)
    assert r.status_code == 200
    mock_sync.assert_not_called()


def test_get_pendientes_summary_no_llama_sync_por_defecto(app, monkeypatch):
    mock_sync = MagicMock()
    monkeypatch.setattr(
        "app.domains.actuaciones.services.pendientes_service.sync_iniciadores_reinspeccion_notificacion",
        mock_sync,
    )
    monkeypatch.setattr(
        "app.domains.actuaciones.services.pendientes_service.list_reinspeccion_notificacion_operativas",
        lambda: [],
    )
    with app.app_context():
        from app.domains.actuaciones.services.pendientes_service import get_pendientes_summary

        get_pendientes_summary(
            ActuacionesPendientesFilters.model_validate(
                {"desde": date(2026, 3, 1), "hasta": date(2026, 3, 31)}
            )
        )
    mock_sync.assert_not_called()


def test_sync_on_read_env_llama_sync_en_pendientes_notificacion(client, monkeypatch, auth_headers):
    monkeypatch.setenv("SYNC_NOTIFICACIONES_VENCIDAS_ON_READ", "1")
    assert materializacion_notificacion_vencida_on_read_enabled() is True

    mock_sync = MagicMock(
        return_value=SyncReinspeccionNotificacionOutcome(0, 0, 0, 0),
    )
    monkeypatch.setattr(
        "app.domains.actuaciones.routes.pendientes_notificacion.sync_iniciadores_reinspeccion_notificacion",
        mock_sync,
    )
    monkeypatch.setattr(
        "app.domains.actuaciones.routes.pendientes_notificacion.list_reinspeccion_notificacion_operativas",
        lambda: [],
    )
    client.get("/actuaciones/pendientes-notificacion", headers=auth_headers)
    mock_sync.assert_called_once()


def test_flask_cli_sync_notificaciones_vencidas(app, monkeypatch):
    monkeypatch.setattr(
        "app.domains.actuaciones.pipelines.sync_notificaciones_vencidas.run_sync_notificaciones_vencidas",
        lambda: {
            "status": "ok",
            "created": 0,
            "eligible_notificaciones": 0,
            "skipped_already_blocking": 0,
            "collisions_idempotent": 0,
            "elapsed_ms": 1.0,
            "started_at": "2026-01-01T00:00:00+00:00",
        },
    )
    runner = app.test_cli_runner()
    result = runner.invoke(args=["sync-notificaciones-vencidas"])
    assert result.exit_code == 0
    assert "ok" in result.output
