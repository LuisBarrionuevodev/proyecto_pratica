from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models import IniciadorRuta, RutaGrupo, RutaItem, RutaTrabajo

from .auth_service import get_current_user_id_or_fallback


def _get_ruta_borrador_or_fail(ruta_id: int) -> RutaTrabajo:
    ruta = RutaTrabajo.query.get(ruta_id)
    if not ruta:
        raise LookupError("Ruta de trabajo no encontrada")
    if ruta.estado_ruta != "BORRADOR":
        raise RuntimeError("La ruta debe estar en BORRADOR")
    return ruta


def _get_grupo_activo_or_fail(*, ruta_id: int, grupo_id: int) -> RutaGrupo:
    grupo = RutaGrupo.query.filter(
        RutaGrupo.id == grupo_id,
        RutaGrupo.ruta_trabajo_id == ruta_id,
        RutaGrupo.deleted_at.is_(None),
    ).first()
    if not grupo:
        raise LookupError("Grupo no encontrado para la ruta indicada")
    return grupo


def _get_item_activo_or_fail(*, ruta_id: int, item_id: int) -> RutaItem:
    item = RutaItem.query.filter(
        RutaItem.id == item_id,
        RutaItem.ruta_trabajo_id == ruta_id,
        RutaItem.deleted_at.is_(None),
    ).first()
    if not item:
        raise LookupError("Item no encontrado para la ruta indicada")
    return item


def assign_iniciadores_to_grupo(*, ruta_id: int, grupo_id: int, iniciador_ids: list[int]) -> list[RutaItem]:
    """
    Asigna iniciadores a grupo creando/reactivando RutaItem en estado ASIGNADO.

    Reglas:
    - operación transaccional total (si falla uno, rollback completo).
    - iniciador asignable: PENDIENTE + not deleted + sin item activo en ruta BORRADOR.
    - si existe item soft-deleted para misma (ruta, iniciador), se reactiva.
    """
    _get_ruta_borrador_or_fail(ruta_id)
    _get_grupo_activo_or_fail(ruta_id=ruta_id, grupo_id=grupo_id)

    now = datetime.utcnow()
    user_id = get_current_user_id_or_fallback()

    initiators = (
        IniciadorRuta.query.filter(IniciadorRuta.id.in_(iniciador_ids))
        .with_for_update()
        .all()
    )
    found_ids = {i.id for i in initiators}
    missing = [iid for iid in iniciador_ids if iid not in found_ids]
    if missing:
        raise LookupError(f"Iniciadores inexistentes: {missing}")

    by_id = {i.id: i for i in initiators}
    for iniciador_id in iniciador_ids:
        iniciador = by_id[iniciador_id]
        if iniciador.deleted_at is not None:
            raise RuntimeError(f"El iniciador {iniciador_id} está eliminado")
        if iniciador.estado_iniciador != "PENDIENTE":
            raise RuntimeError(f"El iniciador {iniciador_id} no está en estado PENDIENTE")

        active_item = (
            RutaItem.query.join(RutaTrabajo, RutaTrabajo.id == RutaItem.ruta_trabajo_id)
            .filter(
                RutaItem.iniciador_ruta_id == iniciador_id,
                RutaItem.deleted_at.is_(None),
                RutaTrabajo.estado_ruta == "BORRADOR",
            )
            .first()
        )
        if active_item:
            raise RuntimeError(
                f"El iniciador {iniciador_id} ya está asignado en una ruta activa"
            )

    affected_items: list[RutaItem] = []
    try:
        for iniciador_id in iniciador_ids:
            existing = RutaItem.query.filter(
                RutaItem.ruta_trabajo_id == ruta_id,
                RutaItem.iniciador_ruta_id == iniciador_id,
            ).first()

            if existing:
                existing.ruta_grupo_id = grupo_id
                existing.estado_ruta_item = "ASIGNADO"
                existing.deleted_at = None
                item = existing
            else:
                item = RutaItem(
                    ruta_trabajo_id=ruta_id,
                    ruta_grupo_id=grupo_id,
                    iniciador_ruta_id=iniciador_id,
                    estado_ruta_item="ASIGNADO",
                    created_by_user_id=user_id,
                )
                db.session.add(item)

            by_id[iniciador_id].estado_iniciador = "PLANIFICADO"
            by_id[iniciador_id].updated_at = now
            affected_items.append(item)

        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise RuntimeError("No se pudo completar la asignación bulk de iniciadores") from exc
    except Exception:
        db.session.rollback()
        raise

    return affected_items


def move_ruta_item(*, ruta_id: int, item_id: int, target_grupo_id: int) -> RutaItem:
    """
    Mueve un item activo entre grupos de la misma ruta BORRADOR.
    """
    _get_ruta_borrador_or_fail(ruta_id)
    item = _get_item_activo_or_fail(ruta_id=ruta_id, item_id=item_id)
    _get_grupo_activo_or_fail(ruta_id=ruta_id, grupo_id=target_grupo_id)

    item.ruta_grupo_id = target_grupo_id
    db.session.commit()
    return item


def soft_delete_ruta_item(*, ruta_id: int, item_id: int) -> RutaItem:
    """
    Soft delete de item y rollback de iniciador a PENDIENTE.
    """
    _get_ruta_borrador_or_fail(ruta_id)
    item = _get_item_activo_or_fail(ruta_id=ruta_id, item_id=item_id)

    iniciador = IniciadorRuta.query.get(item.iniciador_ruta_id)
    if not iniciador:
        raise LookupError("Iniciador de ruta no encontrado para el item")

    now = datetime.utcnow()
    item.deleted_at = now
    iniciador.estado_iniciador = "PENDIENTE"
    iniciador.updated_at = now
    db.session.commit()
    return item


def soft_delete_grupo(*, ruta_id: int, grupo_id: int) -> dict:
    """
    Soft delete de grupo y de sus items activos, devolviendo iniciadores a PENDIENTE.
    """
    _get_ruta_borrador_or_fail(ruta_id)
    grupo = _get_grupo_activo_or_fail(ruta_id=ruta_id, grupo_id=grupo_id)

    now = datetime.utcnow()
    active_items = (
        RutaItem.query.filter(
            RutaItem.ruta_grupo_id == grupo_id,
            RutaItem.ruta_trabajo_id == ruta_id,
            RutaItem.deleted_at.is_(None),
        )
        .with_for_update()
        .all()
    )

    iniciador_ids = [item.iniciador_ruta_id for item in active_items]
    iniciadores = (
        IniciadorRuta.query.filter(IniciadorRuta.id.in_(iniciador_ids)).all()
        if iniciador_ids
        else []
    )
    iniciadores_by_id = {i.id: i for i in iniciadores}

    try:
        grupo.deleted_at = now
        for item in active_items:
            item.deleted_at = now
            iniciador = iniciadores_by_id.get(item.iniciador_ruta_id)
            if iniciador:
                iniciador.estado_iniciador = "PENDIENTE"
                iniciador.updated_at = now
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return {"grupo_id": grupo.id, "items_soft_deleted": len(active_items)}
