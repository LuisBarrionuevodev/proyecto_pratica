"""F3.6a: post-commit Cargar actuación alinea materialización REINSPECCION_NOTIFICACION con sync canónico."""

from __future__ import annotations

from app.domains.actuaciones.services.notificacion_iniciador_service import (
    SyncReinspeccionNotificacionOutcome,
)


def test_cargar_actuacion_canal_post_hook_invoca_sync(monkeypatch):
    calls: list[int] = []

    def _spy() -> SyncReinspeccionNotificacionOutcome:
        calls.append(1)
        return SyncReinspeccionNotificacionOutcome(
            created=0,
            eligible_notificaciones=0,
            skipped_already_blocking=0,
            collisions_idempotent=0,
            revoked=0,
        )

    monkeypatch.setattr(
        "app.domains.actuaciones.services.cargar_actuacion_post_commit.sync_iniciadores_reinspeccion_notificacion",
        _spy,
    )
    from app.domains.actuaciones.services.cargar_actuacion_post_commit import (
        ejecutar_sync_reinspeccion_notificacion_post_cargar_actuacion_canal,
    )

    ejecutar_sync_reinspeccion_notificacion_post_cargar_actuacion_canal()
    assert calls == [1]
