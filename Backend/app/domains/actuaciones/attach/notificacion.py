from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Actuaciones, Notificacion
from app.utils.actas import acta_6
from app.domains.actuaciones.domains.catalogs.motivo import get_motivo_o_falla


def attach_notificacion(actuacion: Actuaciones, data: Optional[Dict[str, Any]]) -> None:
    """
    Adjunta (upsert) el acta de Notificación a una Actuación.

    Comportamiento (sin cambiar lógica):
    - Identifica la notificación por `(numero_acta, anio)` donde `anio` se toma de la `actuacion`.
    - Si `actuacion.notificacion_id` existe:
        - Actualiza esa notificación, validando que el `(numero_acta, anio)` no pertenezca a otra notificación.
    - Si `actuacion.notificacion_id` NO existe:
        - Busca por `(numero_acta, anio)`; si no existe, crea una mínima con `mes=actuacion.mes`.
    - Si viene la key `"motivos"` (aunque sea `[]`), se refleja en `noti.motivos` validando catálogo (`Motivo`).
    - Regla de negocio: una Notificación NO puede estar asociada a otra actuación del mismo `(anio, tipo)`.

    Args:
        actuacion: Actuación destino (debe tener `id`, `anio`, `mes` y opcionalmente `tipo`).
        data: dict opcional con `acta_num` y opcionalmente `motivos`.

    Returns:
        None

    Raises:
        ValueError: si el acta de notificación ya está asociada a otra actuación.
        ValueError: si algún motivo no existe en catálogo (propaga `get_motivo_o_falla`).
    """
    if not data:
        return

    acta_num = acta_6(data.get("acta_num"))
    if not acta_num:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    # 1) si ya tiene notificación asociada, actualizamos esa
    if actuacion.notificacion_id:
        noti = Notificacion.query.get(actuacion.notificacion_id)
        if noti:
            existente = Notificacion.query.filter_by(numero_acta=acta_num, anio=anio).first()
            if existente and existente.id != noti.id:
                raise ValueError("Acta de notificación ya asociada a otra actuación.")

            noti.numero_acta = acta_num
            noti.anio = anio
            noti.mes = mes

            # 👇 clave: si viene el campo (aunque sea []), lo reflejamos
            if "motivos" in data:
                motivos = data.get("motivos") or []
                noti.motivos = [get_motivo_o_falla(m) for m in motivos]

            db.session.add(noti)
            return

    # 2) si no tenía, buscamos por acta+anio
    noti = Notificacion.query.filter_by(numero_acta=acta_num, anio=anio).first()
    if not noti:
        noti = Notificacion(numero_acta=acta_num, anio=anio, mes=mes)
        db.session.add(noti)
        db.session.flush()

    if "motivos" in data:
        motivos = data.get("motivos") or []
        noti.motivos = [get_motivo_o_falla(m) for m in motivos]
        db.session.flush()  # 👈 útil para ver inserts antes del commit

    if actuacion.tipo is not None:
        existe_mismo_tipo = (
            Actuaciones.query.filter(
                Actuaciones.id != actuacion.id,
                Actuaciones.anio == anio,
                Actuaciones.tipo == actuacion.tipo,
                Actuaciones.notificacion_id == noti.id,
            ).first()
        )
        if existe_mismo_tipo:
            raise ValueError(
                f"La Notificación {acta_num}/{anio} ya está asociada a otra actuación del mismo tipo ({actuacion.tipo})."
            )

    actuacion.notificacion_id = noti.id
