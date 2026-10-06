"""Idempotencia del POST cerrar Completar trabajo (V1.1-MEDIA.2B)."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from sqlalchemy.orm import joinedload, selectinload

from app.database import db
from app.domains.actuaciones.presenters.completar_trabajo_presenters import ruta_item_completar_trabajo_to_row
from app.domains.actuaciones.schemas.completar_trabajo_cierre_completo_in import (
    CompletarTrabajoCierreCompletoIn,
)
from app.domains.actuaciones.services.completar_trabajo_cierre_service import (
    cerrar_completar_trabajo_por_ruta_item,
)
from app.domains.media.services.media_ruta_item_resumen_service import build_media_resumen_ruta_item
from app.models import (
    Actuaciones,
    CompletarTrabajoCierreIdempotency,
    Domicilio,
    IniciadorRuta,
    Relevamiento,
    RutaGrupo,
    RutaGrupoInspector,
    RutaItem,
)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.I,
)


def _normalize_idempotency_key(raw: str | None) -> str | None:
    key = (raw or "").strip()
    if not key:
        return None
    if not _UUID_RE.match(key):
        raise ValueError("idempotency_key inválida (se espera UUID).")
    return key.lower()


def digest_cierre_payload(payload: CompletarTrabajoCierreCompletoIn) -> str:
    """Hash estable del body de cierre para detectar reutilización conflictiva de clave."""
    data = payload.model_dump(mode="json", exclude_none=True)
    data.pop("idempotency_key", None)
    data.pop("evidencias_pendientes_al_cierre", None)
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_ruta_item_for_presenter(ruta_item_id: int) -> RutaItem:
    item = (
        RutaItem.query.filter(RutaItem.id == ruta_item_id)
        .options(
            joinedload(RutaItem.actuacion).selectinload(Actuaciones.inspector),
            joinedload(RutaItem.actuacion).joinedload(Actuaciones.orden_trabajo),
            joinedload(RutaItem.actuacion).joinedload(Actuaciones.domicilio).joinedload(Domicilio.rubro),
            joinedload(RutaItem.actuacion).joinedload(Actuaciones.domicilio).joinedload(Domicilio.contribuyente),
            joinedload(RutaItem.iniciador_ruta).joinedload(IniciadorRuta.domicilio).joinedload(Domicilio.rubro),
            joinedload(RutaItem.iniciador_ruta).joinedload(IniciadorRuta.relevamiento).joinedload(Relevamiento.rubro),
            joinedload(RutaItem.ruta_grupo)
            .selectinload(RutaGrupo.grupo_inspectores)
            .joinedload(RutaGrupoInspector.inspector),
        )
        .first()
    )
    if not item:
        raise LookupError("Ruta ítem no encontrado")
    return item


def _presenter_row(item: RutaItem) -> dict[str, Any]:
    return ruta_item_completar_trabajo_to_row(item)


def _register_idempotency(
    *,
    ruta_item_id: int,
    idempotency_key: str,
    payload_digest: str,
    user_id: int,
) -> None:
    db.session.add(
        CompletarTrabajoCierreIdempotency(
            ruta_item_id=int(ruta_item_id),
            idempotency_key=idempotency_key,
            payload_digest=payload_digest,
            created_by_user_id=int(user_id),
        )
    )
    db.session.commit()


def cerrar_completar_trabajo_idempotente(
    *,
    ruta_item_id: int,
    payload: CompletarTrabajoCierreCompletoIn,
    ejecutado_por_user_id: int,
) -> dict[str, Any]:
    """
    Cierra el trabajo o devuelve la fila canónica si la clave ya fue procesada.

    Parámetros:
        ruta_item_id: ítem ancla.
        payload: cierre validado (puede incluir idempotency_key).
        ejecutado_por_user_id: usuario autenticado.

    Retorno:
        Dict presenter de fila Completar trabajo con media_resumen.

    Errores:
        LookupError, ValueError: mismos que cierre + conflicto de idempotency_key.
    """
    idem_key = _normalize_idempotency_key(getattr(payload, "idempotency_key", None))
    payload_digest = digest_cierre_payload(payload) if idem_key else None
    marcar_evidencias = bool(getattr(payload, "evidencias_pendientes_al_cierre", False))

    if idem_key:
        item_locked = (
            RutaItem.query.filter(RutaItem.id == ruta_item_id)
            .with_for_update()
            .first()
        )
        if not item_locked:
            raise LookupError("Ruta ítem no encontrado")

        existing = (
            CompletarTrabajoCierreIdempotency.query.filter_by(
                ruta_item_id=int(ruta_item_id),
                idempotency_key=idem_key,
            )
            .with_for_update()
            .first()
        )
        if existing:
            if existing.payload_digest != payload_digest:
                raise ValueError(
                    "La idempotency_key ya fue usada con un cuerpo distinto para este trabajo."
                )
            db.session.rollback()
            return _presenter_row(_load_ruta_item_for_presenter(ruta_item_id))

        if item_locked.estado_ruta_item == "FINALIZADO":
            _register_idempotency(
                ruta_item_id=ruta_item_id,
                idempotency_key=idem_key,
                payload_digest=payload_digest,
                user_id=ejecutado_por_user_id,
            )
            return _presenter_row(_load_ruta_item_for_presenter(ruta_item_id))

        db.session.rollback()

    row = cerrar_completar_trabajo_por_ruta_item(
        ruta_item_id=ruta_item_id,
        payload=payload,
        ejecutado_por_user_id=ejecutado_por_user_id,
        evidencias_pendientes_abiertas=marcar_evidencias,
    )

    if idem_key and payload_digest:
        try:
            _register_idempotency(
                ruta_item_id=ruta_item_id,
                idempotency_key=idem_key,
                payload_digest=payload_digest,
                user_id=ejecutado_por_user_id,
            )
        except Exception:
            db.session.rollback()
            return row

    media_resumen = build_media_resumen_ruta_item(int(ruta_item_id))
    return {**row, "media_resumen": media_resumen}

