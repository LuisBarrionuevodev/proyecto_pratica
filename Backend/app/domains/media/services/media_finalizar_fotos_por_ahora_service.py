"""Marca un RutaItem FINALIZADO como «fotos pendientes cerradas por ahora» (MEDIA.2C.2)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.database import db
from app.domains.actuaciones.services.completar_trabajo_ruta_item_access import (
    assert_current_user_can_access_ruta_item,
)
from app.domains.rutas_trabajo.services.auth_service import get_current_user_id
from app.models import RutaItem


class FinalizarFotosPorAhoraError(Exception):
    """Error de negocio al finalizar fotos pendientes por ahora."""

    def __init__(self, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.status_code = status_code


def finalizar_fotos_pendientes_por_ahora(ruta_item_id: int) -> dict:
    """
    Registra que el Inspector no subirá más fotos por ahora; idempotente.

    Parámetros:
        ruta_item_id: ítem de ruta objetivo.

    Retorno:
        Dict con ``ruta_item_id`` y ``fotos_pendientes_cerradas_at`` (ISO).

    Errores:
        RutaItemAccessError: 401/403/404 scope.
        FinalizarFotosPorAhoraError: 422 si el trabajo no está cerrado (FINALIZADO).
    """
    item = assert_current_user_can_access_ruta_item(int(ruta_item_id))
    if item.estado_ruta_item != "FINALIZADO":
        raise FinalizarFotosPorAhoraError(
            "Solo se puede finalizar por ahora un trabajo ya guardado (FINALIZADO).",
            status_code=422,
        )
    if item.actuacion_id is None:
        raise FinalizarFotosPorAhoraError(
            "El ítem no tiene actuación asociada.",
            status_code=422,
        )

    if item.fotos_pendientes_cerradas_at is not None:
        return {
            "ruta_item_id": int(item.id),
            "fotos_pendientes_cerradas_at": item.fotos_pendientes_cerradas_at.isoformat(),
            "already_closed": True,
        }

    uid = get_current_user_id()
    now = datetime.now(timezone.utc)
    item.fotos_pendientes_cerradas_at = now
    item.fotos_pendientes_cerradas_by_user_id = int(uid) if uid is not None else None
    item.evidencias_pendientes_abiertas = False
    db.session.commit()

    return {
        "ruta_item_id": int(item.id),
        "fotos_pendientes_cerradas_at": now.isoformat(),
        "already_closed": False,
    }
