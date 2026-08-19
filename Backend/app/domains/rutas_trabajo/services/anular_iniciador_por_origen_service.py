from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.database import db
from app.domains.rutas_trabajo.services.iniciador_policy_service import is_estado_activo
from app.domains.rutas_trabajo.services.ruta_pool_dia_eligibility_service import (
    iniciador_en_ruta_no_borrador_activa,
    ruta_item_bloquea_nueva_planificacion,
)
from app.models import IniciadorRuta, RutaItem, RutaPoolDia, RutaTrabajo

TipoOrigenAnulacion = Literal["RELEVAMIENTO", "DENUNCIA"]

_MSG_INICIADOR_EN_USO = (
    "No se puede eliminar porque el iniciador ya fue utilizado en una ruta o actuación."
)

_ESTADOS_INICIADOR_BLOQUEAN = frozenset({"CUMPLIDO", "EN_EJECUCION"})


class IniciadorOrigenEnUsoError(ValueError):
    """El iniciador vinculado al origen ya fue utilizado operativamente."""


def _filtro_origen(tipo_origen: TipoOrigenAnulacion, origen_id: int):
    if tipo_origen == "RELEVAMIENTO":
        return (
            IniciadorRuta.relevamiento_id == int(origen_id),
            IniciadorRuta.tipo_iniciador == "RELEVAMIENTO",
        )
    return (
        IniciadorRuta.denuncia_id == int(origen_id),
        IniciadorRuta.tipo_iniciador == "DENUNCIA",
    )


def _iniciador_bloquea_anulacion(iniciador: IniciadorRuta) -> bool:
    """
    True si el iniciador no puede darse de baja por uso operativo.

    Permite PENDIENTE/PLANIFICADO sin OT ni actuación, incluso en ruta BORRADOR.
    """
    if iniciador.actuacion_id is not None:
        return True

    estado = (iniciador.estado_iniciador or "").strip().upper()
    if estado in _ESTADOS_INICIADOR_BLOQUEAN:
        return True

    if iniciador_en_ruta_no_borrador_activa(int(iniciador.id)) is not None:
        return True

    items_activos = (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id == int(iniciador.id),
            RutaItem.deleted_at.is_(None),
        )
        .all()
    )
    for item in items_activos:
        if item.orden_trabajo_id is not None:
            return True
        if item.actuacion_id is not None:
            return True
        if (item.estado_ejecucion or "").strip().upper() == "REALIZADO":
            return True
        ruta = item.ruta_trabajo or RutaTrabajo.query.get(item.ruta_trabajo_id)
        estado_ruta = (ruta.estado_ruta or "").strip().upper() if ruta else ""
        if estado_ruta != "BORRADOR" and ruta_item_bloquea_nueva_planificacion(item):
            return True

    return False


def _soft_delete_items_borrador_por_iniciador(iniciador_id: int, now: datetime) -> None:
    """Soft delete de ítems abiertos en rutas BORRADOR vinculados al iniciador."""
    items = (
        RutaItem.query.join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.iniciador_ruta_id == int(iniciador_id),
            RutaItem.deleted_at.is_(None),
            RutaTrabajo.estado_ruta == "BORRADOR",
        )
        .all()
    )
    for item in items:
        item.deleted_at = now
        item.orden_trabajo_id = None
        db.session.add(item)


def _descartar_pools_activos_por_iniciador(iniciador_id: int, now: datetime) -> None:
    """Marca como DESCARTADO el pool activo del iniciador (EN_POOL / ASIGNADO_A_RUTA)."""
    pools = (
        RutaPoolDia.query.filter(
            RutaPoolDia.iniciador_ruta_id == int(iniciador_id),
            RutaPoolDia.deleted_at.is_(None),
            RutaPoolDia.estado.in_(("EN_POOL", "ASIGNADO_A_RUTA")),
        )
        .all()
    )
    for pool in pools:
        pool.estado = "DESCARTADO"
        pool.deleted_at = now
        pool.updated_at = now
        db.session.add(pool)


def _anular_iniciador(iniciador: IniciadorRuta, *, now: datetime, cerrado_motivo: str) -> None:
    """Limpia pool/ruta borrador y marca el iniciador como ANULADO."""
    _soft_delete_items_borrador_por_iniciador(int(iniciador.id), now)
    _descartar_pools_activos_por_iniciador(int(iniciador.id), now)

    iniciador.deleted_at = now
    if is_estado_activo(iniciador.estado_iniciador):
        iniciador.estado_iniciador = "ANULADO"
    iniciador.cerrado_at = iniciador.cerrado_at or now
    iniciador.cerrado_motivo = iniciador.cerrado_motivo or cerrado_motivo
    iniciador.updated_at = now
    db.session.add(iniciador)


def anular_iniciadores_por_origen(
    *,
    tipo_origen: TipoOrigenAnulacion,
    origen_id: int,
    cerrado_motivo: str,
) -> int:
    """
    Anula iniciadores activos vinculados a un relevamiento o denuncia eliminados desde CRUD.

    Parámetros:
        tipo_origen: ``RELEVAMIENTO`` o ``DENUNCIA``.
        origen_id: PK del origen.
        cerrado_motivo: motivo persistido en ``cerrado_motivo`` (p. ej. SOFT_DELETE_DENUNCIA).

    Retorno:
        Cantidad de iniciadores anulados.

    Errores:
        IniciadorOrigenEnUsoError: uso operativo (ruta publicada, OT, actuación, CUMPLIDO).
    """
    filtro_id, filtro_tipo = _filtro_origen(tipo_origen, origen_id)
    iniciadores_activos = (
        IniciadorRuta.query.filter(
            filtro_id,
            filtro_tipo,
            IniciadorRuta.deleted_at.is_(None),
        )
        .order_by(IniciadorRuta.id.asc())
        .all()
    )

    if not iniciadores_activos:
        ultimo = (
            IniciadorRuta.query.filter(filtro_id, filtro_tipo)
            .order_by(IniciadorRuta.id.desc())
            .first()
        )
        if ultimo is not None and _iniciador_bloquea_anulacion(ultimo):
            raise IniciadorOrigenEnUsoError(_MSG_INICIADOR_EN_USO)
        return 0

    for iniciador in iniciadores_activos:
        if _iniciador_bloquea_anulacion(iniciador):
            raise IniciadorOrigenEnUsoError(_MSG_INICIADOR_EN_USO)

    now = datetime.utcnow()
    for iniciador in iniciadores_activos:
        _anular_iniciador(iniciador, now=now, cerrado_motivo=cerrado_motivo)

    return len(iniciadores_activos)
