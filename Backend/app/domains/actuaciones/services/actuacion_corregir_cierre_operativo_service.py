"""
Corrección de cierre operativo desde el CRUD de Actuaciones.

Cuando el usuario borra una contraproducencia reencolable y carga actas, sincroniza
``Actuaciones``, ``RutaItem`` e ``IniciadorRuta`` en la misma transacción que el PUT.
"""

from __future__ import annotations

from datetime import datetime

from app.database import db
from app.models import Actuaciones, IniciadorRuta, RutaItem, RutaTrabajo

MSG_REINGRESO_EN_RUTA = (
    "Esta contraproducencia ya generó un reingreso a ruta. "
    "Revisá la ruta asociada antes de corregir la actuación."
)

from app.domains.actuaciones.services.actuacion_reencolado_service import (
    cancelar_reintentos_posteriores_planificados,
    motivo_bloqueo_intento_posterior_item,
    resolver_item_e_iniciador,
)

_ESTADOS_RUTA_ITEM_ABIERTOS = ("PENDIENTE_ASIGNACION", "ASIGNADO", "EN_PROCESO")


class CorregirCierreOperativoError(ValueError):
    """Bloqueo de negocio al intentar limpiar contraproducencia con reingreso en uso."""


def _resolver_item_e_iniciador(act: Actuaciones) -> tuple[RutaItem | None, IniciadorRuta | None]:
    """Alias interno: ver ``resolver_item_e_iniciador`` en ``actuacion_reencolado_service``."""
    return resolver_item_e_iniciador(act)


def assert_puede_limpiar_contraproducencia(
    act: Actuaciones,
    *,
    item: RutaItem | None = None,
    ini: IniciadorRuta | None = None,
) -> tuple[RutaItem | None, IniciadorRuta | None]:
    """
    Valida que se pueda corregir el cierre operativo limpiando contraproducencia.

    Parámetros:
        act: actuación con contraproducencia previa.
        item: ítem de ruta opcional (se resuelve si no se pasa).
        ini: iniciador opcional (se resuelve si no se pasa).

    Retorno:
        Tupla (item, ini) resuelta.

    Errores:
        CorregirCierreOperativoError: reintento posterior iniciado o finalizado.
        ValueError: cierre definitivo no corregible desde este flujo.
    """
    if not (act.contraproducencia or "").strip():
        raise ValueError("La actuación no tiene contraproducencia para limpiar.")

    if item is None and ini is None:
        item, ini = _resolver_item_e_iniciador(act)

    if ini is not None and ini.estado_iniciador == "CERRADO_NO_EXISTE_LOCAL":
        raise ValueError(
            "No se puede corregir una actuación cerrada como «no existe local» desde Actuaciones."
        )

    if ini is not None and item is not None:
        posteriores = (
            RutaItem.query.filter(
                RutaItem.iniciador_ruta_id == ini.id,
                RutaItem.id > item.id,
                RutaItem.deleted_at.is_(None),
            )
            .order_by(RutaItem.id.asc())
            .all()
        )
        for posterior in posteriores:
            motivo = motivo_bloqueo_intento_posterior_item(posterior)
            if motivo:
                raise CorregirCierreOperativoError(motivo)

    return item, ini


def _sacar_de_rutas_borrador(
    ini: IniciadorRuta,
    *,
    excluir_item_id: int | None,
    now: datetime,
) -> None:
    """
    Soft-delete de ítems abiertos del iniciador en rutas BORRADOR (reingreso aún no publicado).

    Parámetros:
        ini: iniciador reencolado.
        excluir_item_id: ítem de la actuación original (no se toca).
        now: timestamp para ``deleted_at``.
    """
    q = (
        RutaItem.query.join(RutaTrabajo, RutaItem.ruta_trabajo_id == RutaTrabajo.id)
        .filter(
            RutaItem.iniciador_ruta_id == ini.id,
            RutaItem.deleted_at.is_(None),
            RutaItem.estado_ruta_item.in_(_ESTADOS_RUTA_ITEM_ABIERTOS),
            RutaTrabajo.estado_ruta == "BORRADOR",
        )
    )
    if excluir_item_id is not None:
        q = q.filter(RutaItem.id != int(excluir_item_id))
    for bi in q.all():
        bi.deleted_at = now
        db.session.add(bi)


def aplicar_sincronizacion_tras_limpiar_contraproducencia(
    act: Actuaciones,
    *,
    item: RutaItem | None,
    ini: IniciadorRuta | None,
    now: datetime | None = None,
) -> None:
    """
    Alinea estado operativo tras visita realizada (contraproducencia limpia).

    Parámetros:
        act: actuación ya mutada en sesión (contraproducencia None).
        item: ítem de ruta de la visita corregida.
        ini: iniciador asociado.
        now: timestamp UTC naive; default ``datetime.utcnow()``.

    Side effects:
        Modifica ``item`` e ``ini`` en la sesión actual; no hace commit.
    """
    ts = now or datetime.utcnow()

    if item is not None:
        item.estado_ejecucion = "REALIZADO"
        item.estado_ruta_item = "FINALIZADO"
        item.motivo_no_realizado = None
        db.session.add(item)

    if ini is None:
        return

    _sacar_de_rutas_borrador(ini, excluir_item_id=item.id if item else None, now=ts)
    if item is not None:
        try:
            cancelar_reintentos_posteriores_planificados(
                ini,
                item_origen_id=int(item.id),
                now=ts,
            )
        except ValueError as exc:
            raise CorregirCierreOperativoError(str(exc)) from exc

    if ini.estado_iniciador in ("PENDIENTE", "EN_EJECUCION"):
        ini.estado_iniciador = "CUMPLIDO"
        ini.cerrado_at = None
        ini.cerrado_motivo = None
    elif ini.estado_iniciador != "CUMPLIDO":
        ini.estado_iniciador = "CUMPLIDO"
        ini.cerrado_at = None
        ini.cerrado_motivo = None

    ini.updated_at = ts
    db.session.add(ini)
