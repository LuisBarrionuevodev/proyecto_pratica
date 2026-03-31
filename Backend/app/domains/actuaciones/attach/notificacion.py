from __future__ import annotations

from typing import Any, Dict, Optional

from app.database import db
from app.models import Actuaciones, Notificacion
from app.utils.actas import acta_6
from app.domains.actuaciones.catalogs.motivo import get_motivo_o_falla
from app.domains.actuaciones.services.notificacion_timing_service import inicializar_timing_notificacion

_MSG_NOTIF_MOTIVO = "La notificación requiere al menos un motivo."


def _notificacion_exige_al_menos_un_motivo(noti: Notificacion) -> None:
    rel = getattr(noti, "motivos", None) or []
    if len(rel) < 1:
        raise ValueError(_MSG_NOTIF_MOTIVO)


def attach_notificacion(actuacion: Actuaciones, data: Optional[Dict[str, Any]]) -> None:
    """
    Adjunta el acta de Notificación a una Actuación.

    Reglas:
    - Unicidad lógica del acta: `(numero_acta, anio)`.
    - No se reutiliza una fila `Notificacion` ya existente para enganchar otra actuación:
      si el par ya existe en BD y esta actuación aún no tenía la suya, es conflicto.
    - Si `actuacion.notificacion_id` ya apunta a una fila, solo se actualiza esa misma fila
      (misma actuación editando su acta), sin tomar prestada otra fila por número/año.

    Con acta de notificación persistida, debe haber **al menos un motivo** en catálogo.

    Args:
        actuacion: Actuación destino (debe tener `id`, `anio`, `mes` y opcionalmente `tipo`).
        data: dict opcional con `acta_num` y opcionalmente `motivos`.

    Returns:
        None

    Raises:
        ValueError: conflicto de acta ya existente / ya vinculada a otra actuación.
        ValueError: si algún motivo no existe en catálogo (propaga `get_motivo_o_falla`).
        ValueError: si hay acta y cero motivos.
    """
    if not data:
        return

    acta_num = acta_6(data.get("acta_num"))
    if not acta_num:
        return

    anio = actuacion.anio
    mes = actuacion.mes

    # 1) Ya tiene notificación asociada: solo actualizar esa fila (no reutilizar otra por número/año).
    if actuacion.notificacion_id:
        noti = db.session.get(Notificacion, actuacion.notificacion_id)
        if noti:
            otra_misma_clave = db.session.query(Notificacion).filter_by(numero_acta=acta_num, anio=anio).first()
            if otra_misma_clave and otra_misma_clave.id != noti.id:
                raise ValueError(
                    f"La Notificación {acta_num}/{anio} ya existe y está asociada a otra actuación."
                )

            if noti.deleted_at is not None:
                noti.deleted_at = None
            noti.numero_acta = acta_num
            noti.anio = anio
            noti.mes = mes
            inicializar_timing_notificacion(noti, fecha_notificacion=actuacion.fecha)

            if "motivos" in data:
                motivos = data.get("motivos") or []
                noti.motivos = [get_motivo_o_falla(m) for m in motivos]
            _notificacion_exige_al_menos_un_motivo(noti)

            db.session.add(noti)
            actuacion.notificacion_id = noti.id
            return

    # 2) Primera asociación: crear acta nueva; no reenganchar fila existente.
    if db.session.query(Notificacion).filter_by(numero_acta=acta_num, anio=anio).first():
        raise ValueError(
            f"La Notificación {acta_num}/{anio} ya existe y está asociada a otra actuación."
        )

    noti = Notificacion(numero_acta=acta_num, anio=anio, mes=mes)
    inicializar_timing_notificacion(noti, fecha_notificacion=actuacion.fecha)
    db.session.add(noti)
    db.session.flush()

    actuacion.notificacion_id = noti.id

    if "motivos" not in data:
        raise ValueError(_MSG_NOTIF_MOTIVO)
    motivos = data.get("motivos") or []
    noti.motivos = [get_motivo_o_falla(m) for m in motivos]
    db.session.flush()
    _notificacion_exige_al_menos_un_motivo(noti)

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
                f"La Notificación {acta_num}/{anio} ya existe y está asociada a otra actuación."
            )
