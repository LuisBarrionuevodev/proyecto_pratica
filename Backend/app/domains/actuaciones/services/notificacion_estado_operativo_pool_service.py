"""Estado operativo read-only pool/ruta para bandejas operativas (OPER-RUTA.3 / OPER-RUTA.4)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import joinedload

from app.models import IniciadorRuta, RutaItem, RutaPoolDia, RutaTrabajo

_ESTADOS_POOL_ACTIVOS = ("EN_POOL", "ASIGNADO_A_RUTA")
_ESTADOS_RUTA_PUBLICADA = ("PUBLICADA", "EN_CURSO", "CERRADA")
_ESTADOS_RUTA_ITEM_ABIERTOS = ("PENDIENTE_ASIGNACION", "ASIGNADO", "EN_PROCESO")
_ESTADOS_INICIADOR_RESUELTO = ("CUMPLIDO", "CANCELADO", "ANULADO")


def _empty_ctx() -> dict[str, Any]:
    return {
        "estado_operativo_pool": "no_elegible",
        "pool_status": None,
        "ruta_status": None,
        "ruta_trabajo_id": None,
        "ruta_item_id": None,
        "iniciador_id": None,
    }


def _resolver_estado_desde_iniciador(
    ini: IniciadorRuta,
    pool_rows: list[RutaPoolDia],
    ruta_items: list[RutaItem],
) -> dict[str, Any]:
    """
    Deriva estado operativo read-only para un iniciador.

    Parámetros:
        ini: iniciador de reinspección por notificación.
        pool_rows: filas activas de pool para ese iniciador (0..n).
        ruta_items: ítems activos de ruta para ese iniciador.

    Retorno:
        Fragmento DTO con ``estado_operativo_pool`` y refs de pool/ruta.
    """
    ctx = _empty_ctx()
    ctx["iniciador_id"] = int(ini.id)

    if (ini.estado_iniciador or "").upper() in _ESTADOS_INICIADOR_RESUELTO:
        ctx["estado_operativo_pool"] = "resuelto"
        return ctx

    for item in ruta_items:
        if item.deleted_at is not None:
            continue
        if (item.estado_ruta_item or "").upper() == "FINALIZADO" and (
            (item.estado_ejecucion or "").upper() == "REALIZADO"
        ):
            ctx["estado_operativo_pool"] = "resuelto"
            ctx["ruta_item_id"] = int(item.id)
            ctx["ruta_trabajo_id"] = item.ruta_trabajo_id
            if item.ruta_trabajo:
                ctx["ruta_status"] = item.ruta_trabajo.estado_ruta
            return ctx

    for item in ruta_items:
        if item.deleted_at is not None:
            continue
        if (item.estado_ruta_item or "").upper() not in _ESTADOS_RUTA_ITEM_ABIERTOS:
            continue
        ruta = item.ruta_trabajo
        if ruta is None:
            continue
        estado_ruta = (ruta.estado_ruta or "").upper()
        ctx["ruta_item_id"] = int(item.id)
        ctx["ruta_trabajo_id"] = int(ruta.id)
        ctx["ruta_status"] = ruta.estado_ruta
        if estado_ruta in _ESTADOS_RUTA_PUBLICADA:
            ctx["estado_operativo_pool"] = "en_ruta_publicada"
            return ctx
        if estado_ruta == "BORRADOR":
            ctx["estado_operativo_pool"] = "en_ruta_borrador"
            return ctx

    for pool in pool_rows:
        if pool.deleted_at is not None:
            continue
        if pool.estado == "ASIGNADO_A_RUTA":
            ctx["pool_status"] = pool.estado
            ctx["ruta_trabajo_id"] = pool.ruta_trabajo_id
            ctx["ruta_item_id"] = pool.ruta_item_id
            ctx["estado_operativo_pool"] = "en_ruta_borrador"
            if pool.ruta_trabajo:
                ctx["ruta_status"] = pool.ruta_trabajo.estado_ruta
            return ctx

    for pool in pool_rows:
        if pool.deleted_at is not None:
            continue
        if pool.estado == "EN_POOL":
            ctx["pool_status"] = pool.estado
            ctx["estado_operativo_pool"] = "en_pool"
            return ctx

    if (ini.estado_iniciador or "").upper() == "PENDIENTE":
        ctx["estado_operativo_pool"] = "pendiente"
    return ctx


def build_estado_operativo_pool_por_iniciador(
    iniciador_ids: list[int],
) -> dict[int, dict[str, Any]]:
    """
    Mapa batch iniciador_id → contexto operativo pool/ruta.

    Parámetros:
        iniciador_ids: ids de iniciadores a enriquecer.

    Retorno:
        Dict por iniciador con campos read-only para UI.
    """
    ids = sorted({int(i) for i in iniciador_ids if i})
    if not ids:
        return {}

    inis = (
        IniciadorRuta.query.filter(IniciadorRuta.id.in_(ids))
        .options(joinedload(IniciadorRuta.domicilio))
        .all()
    )
    ini_by_id = {int(i.id): i for i in inis}

    pool_rows = (
        RutaPoolDia.query.filter(
            RutaPoolDia.iniciador_ruta_id.in_(ids),
            RutaPoolDia.deleted_at.is_(None),
            RutaPoolDia.estado.in_(_ESTADOS_POOL_ACTIVOS),
        )
        .options(joinedload(RutaPoolDia.ruta_trabajo))
        .order_by(RutaPoolDia.id.desc())
        .all()
    )
    pools_by_ini: dict[int, list[RutaPoolDia]] = {}
    for row in pool_rows:
        if row.iniciador_ruta_id is None:
            continue
        pools_by_ini.setdefault(int(row.iniciador_ruta_id), []).append(row)

    items = (
        RutaItem.query.filter(
            RutaItem.iniciador_ruta_id.in_(ids),
            RutaItem.deleted_at.is_(None),
        )
        .options(joinedload(RutaItem.ruta_trabajo))
        .order_by(RutaItem.id.desc())
        .all()
    )
    items_by_ini: dict[int, list[RutaItem]] = {}
    for item in items:
        if item.iniciador_ruta_id is None:
            continue
        items_by_ini.setdefault(int(item.iniciador_ruta_id), []).append(item)

    out: dict[int, dict[str, Any]] = {}
    for ini_id in ids:
        ini = ini_by_id.get(ini_id)
        if ini is None:
            out[ini_id] = _empty_ctx()
            continue
        out[ini_id] = _resolver_estado_desde_iniciador(
            ini,
            pools_by_ini.get(ini_id, []),
            items_by_ini.get(ini_id, []),
        )
    return out


def enrich_pendiente_notificacion_row(
    row: dict[str, Any],
    *,
    estado_map: dict[int, dict[str, Any]] | None,
    force_no_elegible: bool = False,
) -> dict[str, Any]:
    """
    Agrega campos operativos read-only a una fila de bandeja notificación.

    Parámetros:
        row: DTO base del presenter.
        estado_map: mapa batch por iniciador_id.
        force_no_elegible: True para tabs en plazo/por vencer sin iniciador de visita.

    Retorno:
        Misma fila enriquecida (mutación in-place + retorno).
    """
    if force_no_elegible:
        row.update(_empty_ctx())
        row["estado_operativo_pool"] = "no_elegible"
        return row

    ini_id = row.get("iniciador_id")
    if ini_id is None:
        row.update(_empty_ctx())
        return row

    ctx = (estado_map or {}).get(int(ini_id)) or _empty_ctx()
    row.update(ctx)
    return row


# Alias genérico para bandejas de comprobación (OPER-RUTA.4).
enrich_pendiente_operativo_row = enrich_pendiente_notificacion_row
